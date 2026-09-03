"""客户分类路由（Api.md 第 3 章）：查询全角色，写操作仅管理员/行政"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import CategoryAddRequest, CategoryUpdateRequest, IdRequest
from app.services import customer_service
from app.utils.exceptions import ok

router = APIRouter()

WRITE_ROLES = ("管理员",)


@router.get("/list")
def category_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = customer_service.category_list(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/add")
def category_add(
    req: CategoryAddRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return ok({"id": customer_service.category_add(db, current_user["id"], req)})


@router.post("/update")
def category_update(
    req: CategoryUpdateRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    customer_service.category_update(db, current_user["id"], req)
    return ok(None)


@router.post("/delete")
def category_delete(
    req: IdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    customer_service.category_delete(db, current_user["id"], req.id)
    return ok(None)
