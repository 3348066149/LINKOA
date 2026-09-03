"""流程模板路由（Api.md 第 5 章）：查询全角色，写操作管理员/行政/设计总监"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import IdRequest, TemplateAddRequest, TemplateUpdateRequest
from app.services import template_service
from app.utils.exceptions import ok

router = APIRouter()

WRITE_ROLES = ("管理员",)


@router.get("/list")
def template_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = template_service.template_list(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.get("/detail/{id}")
def template_detail(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(template_service.template_detail(db, id).model_dump(by_alias=True))


@router.post("/add")
def template_add(
    req: TemplateAddRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return ok({"id": template_service.template_add(db, current_user["id"], req)})


@router.post("/update")
def template_update(
    req: TemplateUpdateRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    template_service.template_update(db, current_user["id"], req)
    return ok(None)


@router.post("/delete")
def template_delete(
    req: IdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    template_service.template_delete(db, current_user["id"], req.id)
    return ok(None)
