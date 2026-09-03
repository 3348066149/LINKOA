"""流程模板 Service：整图提交 / 整图全量覆盖 / 模板实例化（ID 映射，最核心）

连线端点解析约定：整图提交时，edge 的 source_node_id / target_node_id
优先匹配入参节点自带的 id；匹配不到时按 nodes 数组的 1 基序号解析
（前端 vue-flow 对新建节点通常使用临时 id，保存时按序号引用）。
"""
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    FlowTemplate,
    FlowTemplateNode,
    FlowTemplateNodeEdge,
    FlowTemplateNodeForm,
    NodeTemplate,
    SysUser,
)
from app.schemas import (
    TemplateAddRequest,
    TemplateDetail,
    TemplateEdgeAddRequest,
    TemplateEdgeOut,
    TemplateListItem,
    TemplateNodeOut,
    TemplateUpdateRequest,
)
from app.services import log_service
from app.utils.exceptions import BusinessException


def template_list(db: Session) -> list[TemplateListItem]:
    stmt = (
        select(FlowTemplate, SysUser.real_name.label("create_user_name"))
        .outerjoin(SysUser, SysUser.id == FlowTemplate.create_user_id)
        .order_by(FlowTemplate.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        TemplateListItem(id=t.id, template_name=t.template_name, create_user_name=name or "已删除用户", create_time=t.create_time)
        for t, name in rows
    ]


def template_detail(db: Session, template_id: int) -> TemplateDetail:
    tpl = db.get(FlowTemplate, template_id)
    if tpl is None:
        raise BusinessException(400, "流程模板不存在")

    nodes = db.execute(
        select(FlowTemplateNode).where(FlowTemplateNode.template_id == template_id).order_by(FlowTemplateNode.sort, FlowTemplateNode.id)
    ).scalars().all()

    edges = db.execute(
        select(FlowTemplateNodeEdge).where(FlowTemplateNodeEdge.template_id == template_id).order_by(FlowTemplateNodeEdge.id)
    ).scalars().all()

    return TemplateDetail(
        id=tpl.id,
        template_name=tpl.template_name,
        nodes=[
            TemplateNodeOut(
                id=n.id, node_template_id=n.node_template_id, node_title=n.node_title, node_remark=n.node_remark,
                sort=n.sort, pos_x=n.pos_x, pos_y=n.pos_y, form_fields=[],
            )
            for n in nodes
        ],
        edges=[
            TemplateEdgeOut(id=e.id, source_node_id=e.source_node_id, target_node_id=e.target_node_id, label=e.label)
            for e in edges
        ],
    )


def _save_graph(db: Session, template_id: int, req: TemplateAddRequest | TemplateUpdateRequest) -> None:
    """单事务内写入 nodes + edges，维护临时引用 -> 新节点ID 的映射（V1.3：纯流程，不存表单定义）"""
    # 1. 插入节点，建立映射：入参节点 id（若有）或 1 基序号 -> 新节点ID
    key_to_new_id: dict[int, int] = {}
    for idx, node_in in enumerate(req.nodes, start=1):
        node = FlowTemplateNode(
            template_id=template_id,
            node_template_id=node_in.node_template_id,
            node_title=node_in.node_title,
            node_remark=node_in.node_remark,
            sort=node_in.sort,
            pos_x=node_in.pos_x,
            pos_y=node_in.pos_y,
        )
        db.add(node)
        db.flush()
        key_to_new_id[idx] = node.id
        if node_in.id is not None:
            key_to_new_id[node_in.id] = node.id

    # 2. 插入连线，端点重映射
    for e_in in req.edges:
        source = key_to_new_id.get(e_in.source_node_id)
        target = key_to_new_id.get(e_in.target_node_id)
        if source is None or target is None:
            raise BusinessException(400, "连线引用了不存在的节点")
        db.add(
            FlowTemplateNodeEdge(
                template_id=template_id, source_node_id=source, target_node_id=target, label=e_in.label or None
            )
        )


def template_add(db: Session, operator_id: int, req: TemplateAddRequest) -> int:
    """新增模板（整图提交，单事务）"""
    tpl = FlowTemplate(template_name=req.template_name, create_user_id=operator_id)
    db.add(tpl)
    db.flush()
    _save_graph(db, tpl.id, req)
    log_service.add_log(db, operator_id, "template_create", f"新增流程模板：{req.template_name}")
    db.commit()
    return tpl.id


def template_update(db: Session, operator_id: int, req: TemplateUpdateRequest) -> None:
    """修改模板（整图全量覆盖：单事务内先删后插）"""
    tpl = db.get(FlowTemplate, req.id)
    if tpl is None:
        raise BusinessException(400, "流程模板不存在")

    node_ids = db.execute(
        select(FlowTemplateNode.id).where(FlowTemplateNode.template_id == req.id)
    ).scalars().all()
    if node_ids:
        db.execute(delete(FlowTemplateNodeForm).where(FlowTemplateNodeForm.template_node_id.in_(node_ids)))
    db.execute(delete(FlowTemplateNodeEdge).where(FlowTemplateNodeEdge.template_id == req.id))
    db.execute(delete(FlowTemplateNode).where(FlowTemplateNode.template_id == req.id))

    tpl.template_name = req.template_name
    db.flush()
    _save_graph(db, tpl.id, req)
    log_service.add_log(db, operator_id, "template_update", f"修改流程模板：{req.template_name}")
    db.commit()


def template_delete(db: Session, operator_id: int, template_id: int) -> None:
    """删除模板（物理删除，单事务级联；与项目深度解绑不影响历史项目）"""
    tpl = db.get(FlowTemplate, template_id)
    if tpl is None:
        raise BusinessException(400, "流程模板不存在")
    node_ids = db.execute(
        select(FlowTemplateNode.id).where(FlowTemplateNode.template_id == template_id)
    ).scalars().all()
    if node_ids:
        db.execute(delete(FlowTemplateNodeForm).where(FlowTemplateNodeForm.template_node_id.in_(node_ids)))
    db.execute(delete(FlowTemplateNodeEdge).where(FlowTemplateNodeEdge.template_id == template_id))
    db.execute(delete(FlowTemplateNode).where(FlowTemplateNode.template_id == template_id))
    name = tpl.template_name
    db.delete(tpl)
    log_service.add_log(db, operator_id, "template_delete", f"删除流程模板：{name}")
    db.commit()


# ---- 模板连线独立接口 ----

def edge_add(db: Session, operator_id: int, req: TemplateEdgeAddRequest) -> int:
    node_ids = set(
        db.execute(
            select(FlowTemplateNode.id).where(
                FlowTemplateNode.template_id == req.template_id,
                FlowTemplateNode.id.in_([req.source_node_id, req.target_node_id]),
            )
        ).scalars().all()
    )
    # 注意：source == target（自环连线）时集合只有 1 个元素，仍合法；
    # 必须按"端点是否都存在"判断，不能用 len(node_ids) != 2（会误杀自环连线）
    required = {req.source_node_id, req.target_node_id}
    if not required.issubset(node_ids):
        raise BusinessException(400, "连线引用了不存在的节点")
    edge = FlowTemplateNodeEdge(
        template_id=req.template_id,
        source_node_id=req.source_node_id,
        target_node_id=req.target_node_id,
        label=req.label,
    )
    db.add(edge)
    db.flush()
    log_service.add_log(db, operator_id, "template_edge_create", f"新增模板连线：{req.source_node_id} -> {req.target_node_id}")
    db.commit()
    return edge.id


def edge_delete(db: Session, operator_id: int, edge_id: int) -> None:
    edge = db.get(FlowTemplateNodeEdge, edge_id)
    if edge is None:
        raise BusinessException(400, "连线不存在")
    db.delete(edge)
    log_service.add_log(db, operator_id, "template_edge_delete", f"删除模板连线：{edge.source_node_id} -> {edge.target_node_id}")
    db.commit()


# ---------------------------------------------------------------------------
# 启动期预置（幂等）：基础节点 + 布展搭建节点 + 3 套流程模板（V1.4.14）
# ---------------------------------------------------------------------------

BUZHAN_TITLE = "布展搭建"
BUZHAN_REMARK = "展会/活动项目的现场布展与搭建环节"
BUZHAN_SORT = 11  # 追加到现有节点类型之后
BUZHAN_FORM_FIELDS = [
    {"fieldLabel": "布展进度", "fieldType": "select", "selectOptions": ["未开始", "进行中", "已完成"], "sort": 1},
    {"fieldLabel": "现场负责人", "fieldType": "text_single", "selectOptions": None, "sort": 2},
    {"fieldLabel": "布展备注", "fieldType": "text_multi", "selectOptions": None, "sort": 3},
]

# 三套流程模板的节点序列（按 node_title 表达，运行时映射为真实 node_template_id）
DEFAULT_TEMPLATES: list[tuple[str, list[str]]] = [
    ("IP 文创产品开发", ["立项登记", "需求对齐", "IP设计输出", "方案内部评审", "打样制作", "实物生产", "验收", "项目归档"]),
    ("平面视觉设计", ["立项登记", "需求对齐", "IP设计输出", "方案内部评审", "验收", "项目归档"]),
    ("展会活动项目", ["立项登记", "需求对齐", "IP设计输出", "方案内部评审", "打样制作", BUZHAN_TITLE, "验收", "项目归档"]),
]

# 8 个基础节点模板（立项登记 → 项目归档）。V1.4.14 修复：全新空库首次启动时，
# 流程模板预置依赖这 8 个基础节点已存在；此前它们只在 legacy seed_template.py
# 里创建，未接入启动路径，导致空库启动抛 RuntimeError。
BASE_NODE_TEMPLATES: list[tuple[str, str, list[tuple[str, str, list[str] | None]]]] = [
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


def init_default_node_templates(db: Session) -> None:
    """幂等，启动期自动预置 8 个基础节点模板（V1.4.14）。

    全新空库首次启动时，init_default_flow_templates 依赖这 8 个基础节点
    （立项登记/需求对齐/IP设计输出/方案内部评审/打样制作/实物生产/验收/项目归档）
    已存在，否则会抛 RuntimeError。本函数按 node_title 幂等补建缺失节点
    （sort 1..8，icon=None），再统一 commit。
    """
    existing_titles = set(db.execute(select(NodeTemplate.node_title)).scalars().all())
    for i, (title, remark, fields) in enumerate(BASE_NODE_TEMPLATES, start=1):
        if title in existing_titles:
            continue
        db.add(
            NodeTemplate(
                node_title=title,
                node_remark=remark,
                icon=None,
                sort=i,
                form_fields=json.dumps(
                    [{"fieldLabel": label, "fieldType": ftype, "selectOptions": opts, "sort": j}
                     for j, (label, ftype, opts) in enumerate(fields, start=1)],
                    ensure_ascii=False,
                ),
            )
        )
    db.commit()


def init_default_flow_templates(db: Session) -> None:
    """幂等，启动期自动预置 3 套流程模板 + 布展搭建节点（V1.4.14）。

    1. 若 node_template 无「布展搭建」，则新增（icon=None、sort=11、camelCase form_fields）；
    2. 按 node_title 映射各流程节点到真实 node_template.id（不硬编码自增 ID）；
    3. 逐套模板幂等写入 flow_template + flow_template_node + 顺序链式连线；
    4. 函数内统一 commit（与 _init_ai_config / init_default_depts 风格一致）。
    """
    # 1. 布展搭建节点类型（幂等）
    buzhan = db.execute(
        select(NodeTemplate).where(NodeTemplate.node_title == BUZHAN_TITLE)
    ).scalars().first()
    if buzhan is None:
        buzhan = NodeTemplate(
            node_title=BUZHAN_TITLE,
            node_remark=BUZHAN_REMARK,
            icon=None,
            sort=BUZHAN_SORT,
            form_fields=json.dumps(BUZHAN_FORM_FIELDS, ensure_ascii=False),
        )
        db.add(buzhan)
        db.flush()  # 立即拿到自增 id，后续模板节点要引用

    # 2. node_title -> node_template.id 映射（含刚就绪的布展搭建）
    titles = {title for _, seq in DEFAULT_TEMPLATES for title in seq}
    rows = db.execute(
        select(NodeTemplate.id, NodeTemplate.node_title).where(NodeTemplate.node_title.in_(titles))
    ).all()
    title_to_id = {row[1]: row[0] for row in rows}
    missing = titles - set(title_to_id)
    if missing:
        raise RuntimeError(f"缺少节点模板 {sorted(missing)}，无法预置流程模板")

    # 3. 逐套模板幂等写入（节点 + 顺序链式连线）
    for name, seq in DEFAULT_TEMPLATES:
        exists = db.execute(
            select(FlowTemplate).where(FlowTemplate.template_name == name)
        ).scalars().first()
        if exists is not None:
            continue

        tpl = FlowTemplate(template_name=name, create_user_id=1)
        db.add(tpl)
        db.flush()  # 立即拿到自增 id，后续节点要引用

        node_ids: list[int] = []
        for idx, title in enumerate(seq):
            sort = idx + 1  # 从 1 开始
            node = FlowTemplateNode(
                template_id=tpl.id,
                node_template_id=title_to_id[title],
                node_title=title,
                node_remark=None,
                sort=sort,
                pos_x=(sort - 1) * 220,  # 从左到右等距排布，单行
                pos_y=0,
            )
            db.add(node)
            db.flush()  # 立即拿到自增 id，后续连线要引用
            node_ids.append(node.id)

        # 顺序链式连线 1→2→3→…→N
        for i in range(len(node_ids) - 1):
            db.add(
                FlowTemplateNodeEdge(
                    template_id=tpl.id,
                    source_node_id=node_ids[i],
                    target_node_id=node_ids[i + 1],
                    label=None,
                )
            )

    db.commit()
