"""AI 助手模块 DTO（V1.4.8）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class ChatStreamRequest(CamelModel):
    """发起对话（流式）入参：conversationId 为空则新建会话"""

    conversation_id: int | None = Field(default=None)
    message: str = Field(..., min_length=1, max_length=4000)


class ConversationItem(CamelModel):
    id: int
    title: str
    pinned: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationRenameRequest(CamelModel):
    """重命名会话入参"""

    title: str = Field(..., min_length=1, max_length=128)


class ConversationPinRequest(CamelModel):
    """置顶/取消置顶入参"""

    pinned: bool = Field(...)


class AiMessageItem(CamelModel):
    id: int
    role: str
    content: str
    sources: list[dict] = []
    created_at: datetime | None = None


class AiConfigOut(CamelModel):
    """AI 配置出参：api_key 脱敏返回"""

    system_prompt: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    max_tokens: int


class AiConfigUpdateRequest(CamelModel):
    """AI 配置更新入参：api_key 传脱敏值（含 ****）表示不修改"""

    system_prompt: str = Field(..., min_length=1, max_length=4000)
    model: str = Field(..., min_length=1, max_length=64)
    api_key: str = Field(default="")
    base_url: str = Field(..., min_length=1, max_length=256)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
