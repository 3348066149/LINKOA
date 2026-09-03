"""客户库路由（Api.md 第 4 章）：查询全角色，写操作仅管理员/行政"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import (
    CustomerAddRequest,
    CustomerCoverRemoveRequest,
    CustomerListQuery,
    CustomerUpdateRequest,
    IdRequest,
)
from app.services import customer_service
from app.utils.exceptions import ok

router = APIRouter()

WRITE_ROLES = ("管理员",)


@router.get("/list")
def customer_list(
    query: CustomerListQuery = Depends(),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(customer_service.customer_list(db, query).model_dump(by_alias=True))


@router.get("/detail/{id}")
def customer_detail(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(customer_service.customer_detail(db, id).model_dump(by_alias=True))


@router.post("/add")
def customer_add(
    req: CustomerAddRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return ok({"id": customer_service.customer_add(db, current_user["id"], req)})


@router.post("/update")
def customer_update(
    req: CustomerUpdateRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    customer_service.customer_update(db, current_user["id"], req)
    return ok(None)


@router.post("/delete")
def customer_delete(
    req: IdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    customer_service.customer_delete(db, current_user["id"], req.id)
    return ok(None)


@router.post("/cover/upload")
def customer_cover_upload(
    file: UploadFile = File(...),
    customerId: int = Form(...),
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    cover_path = customer_service.cover_upload(db, current_user, customerId, file)
    return ok({"coverImage": cover_path})


@router.post("/cover/remove")
def customer_cover_remove(
    req: CustomerCoverRemoveRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    customer_service.cover_remove(db, current_user, req.customer_id)
    return ok(None)
