"""项目节点连线路由（Api.md 第 9 章，全部角色；归档拦截在 Service 层）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_not_customer
from app.schemas import IdRequest, ProjectEdgeAddRequest
from app.services import node_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/add")
def edge_add(
    req: ProjectEdgeAddRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    return ok({"id": node_service.edge_add(db, current_user, req)})


@router.post("/delete")
def edge_delete(
    req: IdRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    node_service.edge_delete(db, current_user, req.id)
    return ok(None)
