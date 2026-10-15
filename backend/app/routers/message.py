"""消息中心路由（Api.md 第 12 章，登录用户）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.schemas import MessageListQuery, MessageReadAllRequest, MessageReadRequest
from app.services import message_service
from app.utils.exceptions import ok

router = APIRouter()


@router.get("/myList")
def my_list(
    query: MessageListQuery = Depends(),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(message_service.my_list(db, current_user["id"], query).model_dump(by_alias=True))


@router.get("/unreadCount")
def unread_count(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """顶部栏铃铛未读红点（PRD 9.3 主布局需要）"""
    return ok({"count": message_service.unread_count(db, current_user["id"])})


@router.post("/read")
def mark_read(
    req: MessageReadRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message_service.mark_read(db, current_user["id"], req.message_id)
    return ok(None)


@router.post("/readAll")
def mark_read_all(
    req: MessageReadAllRequest | None = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一键已读：body 可选（不传=全部；传 projectId=只标记该项目；includeRoutine=连常规消息一起标记）"""
    if req is None:
        count = message_service.mark_read_all(db, current_user["id"])
    else:
        count = message_service.mark_read_all(db, current_user["id"], req.project_id, req.include_routine)
    return ok({"count": count})
