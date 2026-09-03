"""预置「标准IP设计流程」8 阶段模板（幂等：存在则整图覆盖更新，不存在则创建）

运行：cd backend && python seed_template.py
流程：立项登记 → 需求对齐 → IP设计输出 → 方案内部评审 → 打样制作 → 实物生产 → 验收 → 项目归档
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import FlowTemplate, NodeTemplate
from app.schemas import TemplateAddRequest, TemplateUpdateRequest
from app.services import template_service

import json

TEMPLATE_NAME = "标准IP设计流程"
ADMIN_ID = 1  # 初始 admin

# 8 个阶段（2 行 × 4 列布局）；表单字段同时用于预置节点模板库（seed_node_templates）与标准流程模板
STAGES = [
    ("立项登记", "登记项目基础信息，确认立项", [
        ("立项编号", "text_single", None),
        ("项目背景", "text_multi", None),
    ]),
    ("需求对齐", "与客户确认需求细节与交付标准", [
        ("需求描述", "text_multi", None),
        ("优先级", "select", ["高", "中", "低"]),
    ]),
    ("IP设计输出", "输出 IP 形象设计方案与设计稿", [
        ("设计说明", "text_multi", None),
        ("设计稿版本", "text_single", None),
    ]),
    ("方案内部评审", "内部评审设计方案，输出评审结论", [
        ("评审结论", "select", ["通过", "修改后通过", "不通过"]),
        ("评审意见", "text_multi", None),
    ]),
    ("打样制作", "制作实物样品，确认工艺效果", [
        ("打样数量", "text_single", None),
        ("打样备注", "text_multi", None),
    ]),
    ("实物生产", "批量生产，跟进生产进度与质量", [
        ("生产数量", "text_single", None),
        ("供应商", "text_single", None),
    ]),
    ("验收", "客户验收，确认交付结果", [
        ("验收结论", "select", ["合格", "不合格"]),
        ("验收备注", "text_multi", None),
    ]),
    ("项目归档", "资料整理归档，项目收尾", [
        ("归档备注", "text_multi", None),
    ]),
]


def build_graph(title_to_id: dict) -> dict:
    nodes = []
    for i, (title, remark, _fields) in enumerate(STAGES):
        row, col = divmod(i, 4)
        nodes.append({
            "nodeTemplateId": title_to_id.get(title),
            "nodeTitle": title,
            "nodeRemark": remark,
            "sort": i + 1,
            "posX": 80 + col * 280,
            "posY": 120 + row * 280,
        })
    # 顺序连线，端点用 nodes 数组 1 基序号
    edges = [
        {"sourceNodeId": i, "targetNodeId": i + 1, "label": ""}
        for i in range(1, len(STAGES))
    ]
    return {"nodes": nodes, "edges": edges}


def seed_node_templates(db) -> dict:
    """幂等预置节点模板库（8 个标准阶段），已存在的按标题跳过；返回 title -> id 映射"""
    title_to_id = {
        nt.node_title: nt.id
        for nt in db.execute(select(NodeTemplate)).scalars().all()
    }
    created = 0
    for i, (title, remark, fields) in enumerate(STAGES):
        if title in title_to_id:
            continue
        nt = NodeTemplate(
            node_title=title,
            node_remark=remark,
            sort=i + 1,
            form_fields=json.dumps(
                [{"fieldLabel": label, "fieldType": ftype, "selectOptions": opts, "sort": j + 1}
                 for j, (label, ftype, opts) in enumerate(fields)],
                ensure_ascii=False,
            ) if fields else None,
        )
        db.add(nt)
        db.flush()
        title_to_id[title] = nt.id
        created += 1
    db.commit()
    print(f"节点模板库：新增 {created} 个，共 {len(title_to_id)} 个")
    return title_to_id


def main():
    db = SessionLocal()
    try:
        title_to_id = seed_node_templates(db)
        graph = build_graph(title_to_id)
        tpl = db.execute(
            select(FlowTemplate).where(FlowTemplate.template_name == TEMPLATE_NAME)
        ).scalars().first()
        if tpl:
            template_service.template_update(
                db, ADMIN_ID,
                TemplateUpdateRequest.model_validate({"id": tpl.id, "templateName": TEMPLATE_NAME, **graph}),
            )
            print(f"已更新模板 id={tpl.id}「{TEMPLATE_NAME}」：8 节点 / 7 连线")
        else:
            new_id = template_service.template_add(
                db, ADMIN_ID,
                TemplateAddRequest.model_validate({"templateName": TEMPLATE_NAME, **graph}),
            )
            print(f"已创建模板 id={new_id}「{TEMPLATE_NAME}」：8 节点 / 7 连线")
    finally:
        db.close()


if __name__ == "__main__":
    main()
