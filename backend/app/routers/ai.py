"""AI 助手路由（V1.4.8）：会话 CRUD + 流式对话 + 管理员 AI 配置"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import (
    AiConfigUpdateRequest,
    ChatStreamRequest,
    ConversationPinRequest,
    ConversationRenameRequest,
)
from app.services import ai_service
from app.utils.exceptions import ok

router = APIRouter()


@router.get("/conversations")
def conversation_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = ai_service.list_conversations(db, current_user["id"])
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/conversations")
def conversation_create(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok({"id": ai_service.create_conversation(db, current_user["id"])})


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = ai_service.get_messages(db, current_user["id"], conversation_id)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.patch("/conversations/{conversation_id}")
def conversation_rename(
    conversation_id: int,
    req: ConversationRenameRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai_service.rename_conversation(db, current_user["id"], conversation_id, req.title)
    return ok(None)


@router.post("/conversations/{conversation_id}/pin")
def conversation_pin(
    conversation_id: int,
    req: ConversationPinRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai_service.set_conversation_pin(db, current_user["id"], conversation_id, req.pinned)
    return ok(None)


@router.delete("/conversations/{conversation_id}")
def conversation_delete(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ai_service.delete_conversation(db, current_user["id"], conversation_id)
    return ok(None)


@router.post("/chat/stream")
def chat_stream(
    req: ChatStreamRequest,
    current_user: dict = Depends(get_current_user),
):
    generator = ai_service.chat_stream(current_user, req.conversation_id, req.message)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/config")
def get_config(
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    return ok(ai_service.get_ai_config(db).model_dump(by_alias=True))


@router.put("/config")
def update_config(
    req: AiConfigUpdateRequest,
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    ai_service.update_ai_config(db, current_user["id"], req)
    return ok(None)
