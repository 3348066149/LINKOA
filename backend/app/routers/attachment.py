"""附件路由（Api.md 第 10 章，全部角色；权限/归档规则在 Service 层）"""
from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_not_customer
from app.schemas import AttachmentDeleteRequest
from app.services import file_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/upload")
def upload(
    file: UploadFile,
    projectId: int = Form(...),
    projectNodeId: int = Form(...),
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    data = file_service.upload(db, current_user, projectId, projectNodeId, file)
    return ok(data.model_dump(by_alias=True))


@router.get("/list")
def list_by_node(
    projectNodeId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = file_service.list_by_node(db, projectNodeId)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.get("/listByProject")
def list_by_project(
    projectId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = file_service.list_by_project(db, projectId)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/delete")
def delete_attachment(
    req: AttachmentDeleteRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    file_service.delete_attachment(db, current_user, req.attachment_id)
    return ok(None)


@router.get("/download/{attachmentId}")
def download(
    attachmentId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_path, file_name = file_service.get_download_info(db, attachmentId)
    return FileResponse(path=file_path, filename=file_name)
