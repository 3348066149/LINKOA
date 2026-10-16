"""项目画布节点 Service：节点级联删连线、批量坐标更新、表单值全量覆盖"""
import json
import os
import uuid

from fastapi import UploadFile
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ProjectNode,
    ProjectNodeEdge,
    ProjectNodeFormValue,
)
from app.schemas import (
    BatchPositionRequest,
    FormFieldOut,
    FormValueSaveRequest,
    NodeAddRequest,
    NodeUpdateRequest,
    ProjectEdgeAddRequest,
)
from app.services import log_service, message_service, project_service
from app.utils.exceptions import BusinessException

MAX_FORM_FILE_SIZE = 100 * 1024 * 1024  # 单文件 100MB（与报错文案保持一致）
FORBIDDEN_FORM_EXT = {
    ".exe", ".bat", ".cmd", ".ps1", ".sh", ".html", ".htm",
    ".js", ".mjs", ".svg", ".php", ".asp", ".aspx", ".jsp",
    ".dll", ".so", ".msi", ".com", ".scr", ".jar",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
UPLOAD_ROOT = os.path.join(BASE_DIR, settings.UPLOAD_DIR)


def save_upload(file: UploadFile, subdir: str, *, unique_prefix: bool = True) -> str:
    """通用分块落盘：返回相对 uploads/ 的路径（供节点表单/客户反馈共用）

    - 拒绝可执行/脚本类扩展名（黑名单，大小写不敏感）
    - 文件名先 basename 化，防路径穿越；再可选加 uuid 前缀防重名覆盖
    - 分块读取，累计超限即删文件抛业务异常，不留半截文件
    """
    raw_name = os.path.basename(file.filename or "") or "file"
    ext = os.path.splitext(raw_name)[1].lower()
    if ext in FORBIDDEN_FORM_EXT:
        raise BusinessException(400, f"禁止上传 {ext} 类型文件")
    if not ext:
        raise BusinessException(400, "文件缺少扩展名，无法识别类型")

    save_dir = os.path.join(UPLOAD_ROOT, subdir)
    os.makedirs(save_dir, exist_ok=True)
    save_name = f"{uuid.uuid4().hex}_{raw_name}" if unique_prefix else raw_name
    save_path = os.path.join(save_dir, save_name)

    size = 0
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FORM_FILE_SIZE:
                    f.close()
                    _remove_file(save_path)
                    raise BusinessException(
                        400, f"文件大小超过 {MAX_FORM_FILE_SIZE // (1024 * 1024)}MB 上限")
                f.write(chunk)
    except BusinessException:
        _remove_file(save_path)
        raise
    except OSError:
        _remove_file(save_path)
        raise BusinessException(500, "文件保存失败")

    if size == 0:
        _remove_file(save_path)
        raise BusinessException(400, "上传文件内容为空")

    return f"{subdir}/{save_name}"


def upload_form_image(file: UploadFile) -> str:
    """节点表单上传字段（设计师/员工侧）：支持所有文件类型，返回相对 uploads/ 的路径"""
    return save_upload(file, "node_form")


def _remove_file(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


def _get_node_and_project(db: Session, node_id: int) -> tuple[ProjectNode, object]:
    node = db.get(ProjectNode, node_id)
    if node is None:
        raise BusinessException(400, "节点不存在")
    project = project_service.get_project_or_400(db, node.project_id)
    return node, project


def _load_options(raw: str | None) -> list[str] | None:
    """安全解析下拉选项 JSON；解析失败返回 None"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def copy_node_template_form(db: Session, project_node_id: int, form_fields_json: str | None) -> None:
    """把节点模板的 form_fields JSON 值拷贝为 project_node_form_value 记录（含下拉选项冗余）

    表单定义唯一来源是节点模板库（node_template.form_fields），
    项目节点实例化时值拷贝为填写值记录，字段结构不可再改。
    """
    if not form_fields_json:
        return
    try:
        fields = json.loads(form_fields_json)
    except (json.JSONDecodeError, TypeError):
        return
    for f in fields:
        if not isinstance(f, dict):
            continue
        # 兼容 camelCase（seed 脚本/前端）与 snake_case（model_dump 默认）两种键名
        label = f.get("fieldLabel") or f.get("field_label") or ""
        ftype = f.get("fieldType") or f.get("field_type") or "text_single"
        opts = f.get("selectOptions") or f.get("select_options")
        db.add(
            ProjectNodeFormValue(
                project_node_id=project_node_id,
                template_node_form_id=None,  # 来源是节点模板，非流程模板表单
                field_label=label,
                field_type=ftype,
                select_options=json.dumps(opts, ensure_ascii=False) if opts else None,
                field_value=None,
                create_user_id=None,
            )
        )


def node_add(db: Session, operator: dict, req: NodeAddRequest) -> int:
    """新增节点：只能从节点模板库选择（V1.3），标题/备注/表单字段均取自节点模板"""
    project = project_service.get_project_or_400(db, req.project_id)
    project_service.check_project_archived(project)

    from app.models import NodeTemplate  # 避免循环导入
    tpl = db.get(NodeTemplate, req.node_template_id)
    if tpl is None:
        raise BusinessException(400, "节点模板不存在，请从节点库中选择节点")

    node = ProjectNode(
        project_id=project.id,
        node_title=tpl.node_title,
        node_remark=tpl.node_remark,
        icon=tpl.icon,
        sort=req.sort,
        pos_x=req.pos_x,
        pos_y=req.pos_y,
        is_review=bool(tpl.is_review),
        review_options=tpl.review_options,
        client_review_fields=tpl.client_review_fields,
        create_user_id=operator["id"],
    )
    db.add(node)
    db.flush()
    copy_node_template_form(db, node.id, tpl.form_fields)
    log_service.add_log(db, operator["id"], "node_create", f"新增节点：{tpl.node_title}", related_project_id=project.id)
    message_service.push(db, project, operator["id"], operator["real_name"], "node_create", node_title=tpl.node_title)
    db.commit()
    return node.id


def node_update(db: Session, operator: dict, req: NodeUpdateRequest) -> None:
    node, project = _get_node_and_project(db, req.id)
    project_service.check_project_archived(project)

    node.node_title = req.node_title
    node.node_remark = req.node_remark
    node.sort = req.sort
    node.pos_x = req.pos_x
    node.pos_y = req.pos_y
    log_service.add_log(db, operator["id"], "node_update", f"修改节点：{req.node_title}", related_project_id=project.id)
    message_service.push(db, project, operator["id"], operator["real_name"], "node_update", node_title=req.node_title)
    db.commit()


def batch_update_positions(db: Session, operator: dict, req: BatchPositionRequest) -> None:
    """拖拽防抖批量更新坐标：单事务；仅坐标变化，不触发消息推送、不写操作日志"""
    project = project_service.get_project_or_400(db, req.project_id)
    project_service.check_project_archived(project)

    node_ids = [p.id for p in req.positions]
    existing = set(
        db.execute(
            select(ProjectNode.id).where(ProjectNode.project_id == project.id, ProjectNode.id.in_(node_ids))
        ).scalars().all()
    )
    for p in req.positions:
        if p.id not in existing:
            raise BusinessException(400, "节点不存在或不属于当前项目")
        node = db.get(ProjectNode, p.id)
        node.pos_x = p.pos_x
        node.pos_y = p.pos_y
    db.commit()


def node_delete(db: Session, operator: dict, node_id: int) -> None:
    """单事务级联删除：节点 + 出入连线 + 表单填写值；附件保留在项目中"""
    node, project = _get_node_and_project(db, node_id)
    project_service.check_project_archived(project)

    title = node.node_title
    db.execute(
        delete(ProjectNodeEdge).where(
            or_(ProjectNodeEdge.source_node_id == node_id, ProjectNodeEdge.target_node_id == node_id)
        )
    )
    db.execute(delete(ProjectNodeFormValue).where(ProjectNodeFormValue.project_node_id == node_id))
    db.delete(node)
    log_service.add_log(db, operator["id"], "node_delete", f"删除节点：{title}", related_project_id=project.id)
    message_service.push(db, project, operator["id"], operator["real_name"], "node_delete", node_title=title)
    db.commit()


def get_form(db: Session, project_node_id: int) -> list[FormFieldOut]:
    """节点表单定义 + 已填值；无表单记录（旧临时节点）返回空数组

    select_options 已冗余在 project_node_form_value.select_options（V1.3），直接读取。
    """
    node = db.get(ProjectNode, project_node_id)
    if node is None:
        raise BusinessException(400, "节点不存在")

    rows = db.execute(
        select(ProjectNodeFormValue)
        .where(ProjectNodeFormValue.project_node_id == project_node_id)
        .order_by(ProjectNodeFormValue.id)
    ).scalars().all()

    return [
        FormFieldOut(
            id=r.id,
            field_label=r.field_label,
            field_type=r.field_type,
            select_options=_load_options(r.select_options),
            sort=0,
            field_value=r.field_value,
            update_time=r.update_time,
            side=r.side or "designer",
        )
        for r in rows
    ]


def save_form_value(db: Session, operator: dict, req: FormValueSaveRequest) -> None:
    """全量覆盖保存，后提交覆盖先提交"""
    node, project = _get_node_and_project(db, req.project_node_id)
    project_service.check_project_archived(project)

    value_ids = [v.id for v in req.form_value_list]
    existing = {
        r.id: r
        for r in db.execute(
            select(ProjectNodeFormValue).where(
                ProjectNodeFormValue.project_node_id == node.id,
                ProjectNodeFormValue.id.in_(value_ids),
            )
        ).scalars().all()
    } if value_ids else {}

    for v in req.form_value_list:
        row = existing.get(v.id)
        if row is None:
            raise BusinessException(400, "表单字段不存在或不属于当前节点")
        row.field_value = v.field_value
        row.create_user_id = operator["id"]

    log_service.add_log(db, operator["id"], "node_form_value_update", f"填写节点表单：{node.node_title}", related_project_id=project.id)
    message_service.push(db, project, operator["id"], operator["real_name"], "form_update", node_title=node.node_title)
    db.commit()


# ---- 项目节点连线 ----

def edge_add(db: Session, operator: dict, req: ProjectEdgeAddRequest) -> int:
    project = project_service.get_project_or_400(db, req.project_id)
    project_service.check_project_archived(project)

    node_ids = set(
        db.execute(
            select(ProjectNode.id).where(
                ProjectNode.project_id == project.id,
                ProjectNode.id.in_([req.source_node_id, req.target_node_id]),
            )
        ).scalars().all()
    )
    # 注意：source == target（自环连线）时集合只有 1 个元素，仍合法；
    # 必须按"端点是否都存在"判断，不能用 len(node_ids) != 2（会误杀自环连线）
    required = {req.source_node_id, req.target_node_id}
    if not required.issubset(node_ids):
        raise BusinessException(400, "连线引用了不存在的节点")
    edge = ProjectNodeEdge(
        project_id=project.id,
        source_node_id=req.source_node_id,
        target_node_id=req.target_node_id,
        label=req.label,
    )
    db.add(edge)
    db.flush()
    db.commit()
    return edge.id


def edge_delete(db: Session, operator: dict, edge_id: int) -> None:
    edge = db.get(ProjectNodeEdge, edge_id)
    if edge is None:
        raise BusinessException(400, "连线不存在")
    project = project_service.get_project_or_400(db, edge.project_id)
    project_service.check_project_archived(project)
    db.delete(edge)
    db.commit()
