"""评论路由（Api.md 第 11 章，全部角色；权限/归档规则在 Service 层）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_not_customer
from app.schemas import CommentAddRequest, CommentDeleteRequest
from app.services import comment_service
from app.utils.exceptions import ok

router = APIRouter()


@router.get("/list")
def comment_list(
    projectId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = comment_service.comment_list(db, projectId)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/add")
def comment_add(
    req: CommentAddRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    return ok({"id": comment_service.comment_add(db, current_user, req)})


@router.post("/delete")
def comment_delete(
    req: CommentDeleteRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    comment_service.comment_delete(db, current_user, req.comment_id)
    return ok(None)
