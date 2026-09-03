"""第5步 Service 层检查点脚本（SQLite 内存库端到端验证核心业务规则）

运行：cd backend && python tests/check_step5_services.py
覆盖红线：
1. 模板实例化 ID 映射（连线 source/target 重映射）
2. 删除防误删（分类/客户/已归档项目）
3. 归档全局硬拦截
4. 附件/评论删除权限隔离（403）
5. 消息推送排除操作人
6. 节点删除级联删连线
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Message, NodeTemplate, ProjectDesignerRel, ProjectNode, ProjectNodeEdge,
    ProjectNodeFormValue, SysUser,
)
from app.schemas import (
    CategoryAddRequest, CommentAddRequest, CustomerAddRequest, NodeAddRequest,
    ProjectCreateRequest, ProjectIdRequest, TemplateAddRequest,
)
from app.services import (
    comment_service, customer_service, node_service, project_service, template_service,
)
from app.utils.exceptions import BusinessException

engine = create_engine("sqlite:///:memory:")
Session = sessionmaker(bind=engine)

# SQLite 要求索引名全库唯一（MySQL 仅表内唯一），测试环境将索引名加上表名前缀
for _table in Base.metadata.tables.values():
    for _idx in _table.indexes:
        _idx.name = f"{_table.name}_{_idx.name}"

Base.metadata.create_all(engine)
db = Session()

PASSED = 0


def check(name: str, cond: bool):
    global PASSED
    assert cond, f"FAILED: {name}"
    PASSED += 1
    print(f"  PASS {name}")


def expect_400(name: str, fn, msg_part: str = ""):
    try:
        fn()
    except BusinessException as e:
        check(f"{name} (code={e.code})", e.code == 400 and (not msg_part or msg_part in e.msg))
        return
    raise AssertionError(f"FAILED: {name} 未抛 400")


def expect_403(name: str, fn, msg_part: str = ""):
    try:
        fn()
    except BusinessException as e:
        check(f"{name} (code={e.code})", e.code == 403 and (not msg_part or msg_part in e.msg))
        return
    raise AssertionError(f"FAILED: {name} 未抛 403")


# ---- 种子数据 ----
admin = SysUser(username="admin", password="admin123", real_name="管理员", role="管理员", is_enable=1)
designer = SysUser(username="zhangsan", password="123456", real_name="张三", role="设计师", is_enable=1)
db.add_all([admin, designer])
db.flush()
# V1.3：节点只能从节点模板库创建，表单定义唯一来源是节点模板库
nt_req = NodeTemplate(node_title="需求对齐", node_remark="确认需求", sort=1,
                      form_fields=json.dumps([{"fieldLabel": "需求描述", "fieldType": "text_multi", "selectOptions": None, "sort": 1}], ensure_ascii=False))
nt_design = NodeTemplate(node_title="IP设计输出", node_remark="输出设计稿", sort=2, form_fields=None)
node_tpl = NodeTemplate(node_title="打样制作", node_remark="制作实物样品", sort=3, form_fields=None)
db.add_all([nt_req, nt_design, node_tpl])
db.flush()
ADMIN = {"id": admin.id, "real_name": admin.real_name}
DESIGNER = {"id": designer.id, "real_name": designer.real_name}

cat_id = customer_service.category_add(db, admin.id, CategoryAddRequest(category_name="政府客户"))
cus_id = customer_service.customer_add(db, admin.id, CustomerAddRequest(category_id=cat_id, customer_name="青岛博物馆", remark="李主任"))

print("== 1. 模板整图提交 ==")
tpl_id = template_service.template_add(db, admin.id, TemplateAddRequest.model_validate({
    "templateName": "标准IP设计流程",
    "nodes": [
        {"nodeTemplateId": nt_req.id, "nodeTitle": "需求对齐", "sort": 1, "posX": 100, "posY": 200},
        {"nodeTemplateId": nt_design.id, "nodeTitle": "IP设计输出", "sort": 2, "posX": 400, "posY": 200},
    ],
    "edges": [{"sourceNodeId": 1, "targetNodeId": 2, "label": ""}],  # 1 基序号引用
}))
detail = template_service.template_detail(db, tpl_id)
check("模板节点数=2", len(detail.nodes) == 2)
check("模板连线数=1", len(detail.edges) == 1)
check("连线端点已映射为真实节点ID",
      detail.edges[0].source_node_id == detail.nodes[0].id and detail.edges[0].target_node_id == detail.nodes[1].id)
check("节点已关联节点模板（node_template_id）",
      detail.nodes[0].node_template_id == nt_req.id and detail.nodes[1].node_template_id == nt_design.id)

print("== 2. 模板实例化：ID 重映射（最核心） ==")
tpl_node_ids = {n.id for n in detail.nodes}
pid = project_service.project_create(db, admin.id, ProjectCreateRequest.model_validate({
    "projectName": "熊猫IP设计项目", "customerId": cus_id,
    "designerRelUserIdList": [designer.id], "templateId": tpl_id,
}))
pd = project_service.project_detail(db, pid)
check("项目状态=进行中", pd.project_status == "进行中")
check("拷贝节点数=2", len(pd.nodes) == 2)
check("拷贝连线数=1", len(pd.edges) == 1)
proj_node_ids = {n.id for n in pd.nodes}
node_by_sort = {n.sort: n for n in pd.nodes}
check("连线端点重映射到项目新节点且拓扑保持（需求对齐 -> IP设计输出）",
      pd.edges[0].source_node_id == node_by_sort[1].id
      and pd.edges[0].target_node_id == node_by_sort[2].id
      and node_by_sort[1].node_title == "需求对齐" and node_by_sort[2].node_title == "IP设计输出")
check("连线端点属于项目节点集合", pd.edges[0].source_node_id in proj_node_ids and pd.edges[0].target_node_id in proj_node_ids)
fv = db.execute(select(ProjectNodeFormValue)).scalars().all()
check("表单定义从节点模板拷贝为填写值记录（field_value 初始为空）", len(fv) == 1 and fv[0].field_value is None)
check("表单字段冗余 field_label 正确", fv[0].field_label == "需求描述")
check("参与设计师已关联", pd.designer_list[0].real_name == "张三")

# 深度解绑：删除模板不影响已创建的历史项目
template_service.template_delete(db, admin.id, tpl_id)
pd2 = project_service.project_detail(db, pid)
check("删除模板后历史项目节点/连线不受影响（深度解绑）", len(pd2.nodes) == 2 and len(pd2.edges) == 1)
check("删除模板后项目表单填写值保留", len(db.execute(select(ProjectNodeFormValue)).scalars().all()) == 1)

print("== 3. 消息推送：排除操作人 ==")
node_id = node_service.node_add(db, DESIGNER, NodeAddRequest.model_validate({
    "projectId": pid, "nodeTemplateId": node_tpl.id, "posX": 300, "posY": 300}))
check("节点标题/备注取自节点模板", db.get(ProjectNode, node_id).node_title == "打样制作")
# 未预设的节点模板禁止创建
expect_400("未预设节点模板禁止创建", lambda: node_service.node_add(
    db, DESIGNER, NodeAddRequest.model_validate({"projectId": pid, "nodeTemplateId": 999})), "节点模板不存在")
msgs = db.execute(select(Message)).scalars().all()
check("张三操作后仅 admin 收到消息（排除操作人）", len(msgs) == 1 and msgs[0].receive_user_id == admin.id)
check("消息类型 node_create + 文案模板正确",
      msgs[0].msg_type == "node_create" and "张三 在项目「熊猫IP设计项目」中新增了节点：打样制作" == msgs[0].msg_content)
check("消息携带 project_id", msgs[0].project_id == pid)

print("== 4. 归档全局硬拦截 ==")
project_service.project_archive(db, admin.id, pid)
expect_400("归档后禁止新增节点", lambda: node_service.node_add(
    db, DESIGNER, NodeAddRequest.model_validate({"projectId": pid, "nodeTemplateId": node_tpl.id})), "项目已归档")
expect_400("归档后禁止删除节点", lambda: node_service.node_delete(db, DESIGNER, node_id), "项目已归档")
expect_400("归档后禁止发表评论", lambda: comment_service.comment_add(
    db, DESIGNER, CommentAddRequest.model_validate({"projectId": pid, "content": "hi"})), "项目已归档")
expect_400("已归档项目禁止直接删除", lambda: project_service.project_delete(db, admin.id, pid), "已归档项目请先取消归档")
project_service.project_unarchive(db, admin.id, pid)
check("取消归档后状态=进行中", project_service.project_detail(db, pid).project_status == "进行中")

print("== 5. 删除防误删 ==")
expect_400("分类下存在客户禁止删除", lambda: customer_service.category_delete(db, admin.id, cat_id), "该分类下存在客户")
expect_400("客户存在关联项目禁止删除", lambda: customer_service.customer_delete(db, admin.id, cus_id), "该客户存在关联项目")

print("== 6. 评论权限隔离 ==")
cid = comment_service.comment_add(db, DESIGNER, CommentAddRequest.model_validate({"projectId": pid, "content": "这个方案不错，建议调整配色方案"}))
expect_403("非本人删除评论 403", lambda: comment_service.comment_delete(db, ADMIN, cid), "无权删除他人评论")
comment_service.comment_delete(db, DESIGNER, cid)
check("本人删除评论成功", True)

print("== 7. 节点删除级联删连线 ==")
edge_cnt_before = len(db.execute(select(ProjectNodeEdge).where(ProjectNodeEdge.project_id == pid)).scalars().all())
first_node_id = pd.edges[0].source_node_id
node_service.node_delete(db, ADMIN, first_node_id)
edge_cnt_after = len(db.execute(select(ProjectNodeEdge).where(ProjectNodeEdge.project_id == pid)).scalars().all())
check(f"删除节点后出入连线级联删除（{edge_cnt_before}->{edge_cnt_after}）", edge_cnt_after == 0)

print("== 8. 项目级联删除 ==")
project_service.project_delete(db, admin.id, pid)
check("项目节点已清空", len(db.execute(select(ProjectNode).where(ProjectNode.project_id == pid)).scalars().all()) == 0)
check("表单值已清空", len(db.execute(select(ProjectNodeFormValue)).scalars().all()) == 0)
check("消息已清空", len(db.execute(select(Message).where(Message.project_id == pid)).scalars().all()) == 0)
check("设计师关联已清空", len(db.execute(select(ProjectDesignerRel).where(ProjectDesignerRel.project_id == pid)).scalars().all()) == 0)

print(f"\n全部检查点通过：{PASSED} 项")
