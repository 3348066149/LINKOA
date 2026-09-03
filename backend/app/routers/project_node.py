"""项目画布节点路由（Api.md 第 8 章，全部角色；归档拦截在 Service 层）"""
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_not_customer
from app.schemas import (
    BatchPositionRequest,
    FormValueSaveRequest,
    NodeAddRequest,
    NodeDeleteRequest,
    NodeUpdateRequest,
)
from app.services import node_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/formImage/upload")
def upload_form_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_not_customer()),
):
    """节点表单「上传图像」字段：jpg/png/webp ≤5MB，返回相对路径（V1.4.3）"""
    path = node_service.upload_form_image(file)
    return ok({"imagePath": path})


@router.post("/add")
def node_add(
    req: NodeAddRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    return ok({"id": node_service.node_add(db, current_user, req)})


@router.post("/update")
def node_update(
    req: NodeUpdateRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    node_service.node_update(db, current_user, req)
    return ok(None)


@router.post("/batchUpdatePositions")
def batch_update_positions(
    req: BatchPositionRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    node_service.batch_update_positions(db, current_user, req)
    return ok(None)


@router.post("/delete")
def node_delete(
    req: NodeDeleteRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    node_service.node_delete(db, current_user, req.node_id)
    return ok(None)


@router.get("/getForm/{projectNodeId}")
def get_form(
    projectNodeId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fields = node_service.get_form(db, projectNodeId)
    return ok({"fields": [f.model_dump(by_alias=True) for f in fields]})


@router.post("/saveFormValue")
def save_form_value(
    req: FormValueSaveRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    node_service.save_form_value(db, current_user, req)
    return ok(None)
