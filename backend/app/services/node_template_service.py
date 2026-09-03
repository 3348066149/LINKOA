"""节点模板 Service：管理员 CRUD；读取全角色（画布节点库数据源）"""
import json
import os
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NodeTemplate
from app.schemas import NodeTemplateAddRequest, NodeTemplateItem, NodeTemplateUpdateRequest
from app.services import log_service
from app.utils.exceptions import BusinessException

MAX_ICON_SIZE = 1 * 1024 * 1024  # 自定义图标 ≤1MB
ALLOWED_ICON_EXT = {".jpg", ".jpeg", ".png", ".svg"}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
UPLOAD_ROOT = os.path.join(BASE_DIR, settings.UPLOAD_DIR)


def upload_icon(file: UploadFile) -> str:
    """自定义节点图标上传：jpg/png/svg ≤1MB，返回相对 uploads/ 路径（V1.4.3）"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_ICON_EXT:
        raise BusinessException(400, "仅支持 jpg/png/svg 格式的图标")
    save_dir = os.path.join(UPLOAD_ROOT, "node_icon")
    os.makedirs(save_dir, exist_ok=True)
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, save_name)
    size = 0
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ICON_SIZE:
                    raise BusinessException(400, "图标大小超过 1MB 上限")
                f.write(chunk)
    except BusinessException:
        try:
            if os.path.isfile(save_path):
                os.remove(save_path)
        except OSError:
            pass
        raise
    return f"node_icon/{save_name}"


def _to_item(t: NodeTemplate) -> NodeTemplateItem:
    try:
        fields = json.loads(t.form_fields) if t.form_fields else []
    except (json.JSONDecodeError, TypeError):
        fields = []
    return NodeTemplateItem(
        id=t.id, node_title=t.node_title, node_remark=t.node_remark,
        icon=t.icon, sort=t.sort, form_fields=fields,
    )


def list_all(db: Session) -> list[NodeTemplateItem]:
    rows = db.execute(
        select(NodeTemplate).order_by(NodeTemplate.sort, NodeTemplate.id)
    ).scalars().all()
    return [_to_item(t) for t in rows]


def add(db: Session, operator_id: int, req: NodeTemplateAddRequest) -> int:
    t = NodeTemplate(
        node_title=req.node_title,
        node_remark=req.node_remark,
        icon=req.icon,
        sort=req.sort,
        form_fields=json.dumps([f.model_dump(by_alias=True) for f in req.form_fields], ensure_ascii=False) if req.form_fields else None,
    )
    db.add(t)
    db.flush()
    log_service.add_log(db, operator_id, "node_template_create", f"新增节点模板：{req.node_title}")
    db.commit()
    return t.id


def update(db: Session, operator_id: int, req: NodeTemplateUpdateRequest) -> None:
    t = db.get(NodeTemplate, req.id)
    if t is None:
        raise BusinessException(400, "节点模板不存在")
    t.node_title = req.node_title
    t.node_remark = req.node_remark
    t.icon = req.icon
    t.sort = req.sort
    t.form_fields = json.dumps([f.model_dump(by_alias=True) for f in req.form_fields], ensure_ascii=False) if req.form_fields else None
    log_service.add_log(db, operator_id, "node_template_update", f"修改节点模板：{req.node_title}")
    db.commit()


def delete(db: Session, operator_id: int, template_id: int) -> None:
    """物理删除节点模板；不影响已生成的流程模板与项目节点（值拷贝解绑）"""
    t = db.get(NodeTemplate, template_id)
    if t is None:
        raise BusinessException(400, "节点模板不存在")
    title = t.node_title
    db.delete(t)
    log_service.add_log(db, operator_id, "node_template_delete", f"删除节点模板：{title}")
    db.commit()
