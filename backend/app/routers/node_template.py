"""节点模板路由（V1.3 新增）：读取全角色（画布节点库），写操作仅管理员"""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import IdRequest, NodeTemplateAddRequest, NodeTemplateUpdateRequest
from app.services import node_template_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/icon/upload")
def upload_icon(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_roles("管理员")),
):
    """自定义节点图标上传：jpg/png/svg ≤1MB，返回相对路径（V1.4.3）"""
    path = node_template_service.upload_icon(file)
    return ok({"iconPath": path})


@router.get("/list")
def list_all(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = node_template_service.list_all(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/add")
def add(
    req: NodeTemplateAddRequest,
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    return ok({"id": node_template_service.add(db, current_user["id"], req)})


@router.post("/update")
def update(
    req: NodeTemplateUpdateRequest,
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    node_template_service.update(db, current_user["id"], req)
    return ok(None)


@router.post("/delete")
def delete(
    req: IdRequest,
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    node_template_service.delete(db, current_user["id"], req.id)
    return ok(None)
