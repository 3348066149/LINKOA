"""模板节点连线路由（Api.md 第 6 章，管理员/行政/设计总监）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import IdRequest, TemplateEdgeAddRequest
from app.services import template_service
from app.utils.exceptions import ok

router = APIRouter(dependencies=[Depends(require_roles("管理员"))])


@router.post("/add")
def edge_add(
    req: TemplateEdgeAddRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok({"id": template_service.edge_add(db, current_user["id"], req)})


@router.post("/delete")
def edge_delete(
    req: IdRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template_service.edge_delete(db, current_user["id"], req.id)
    return ok(None)
