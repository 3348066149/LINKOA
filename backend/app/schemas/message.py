"""消息中心 DTO（Api.md 第 12 章）"""
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, PageQuery


class MessageListQuery(PageQuery):
    is_read: Literal[0, 1] | None = None


class MessageReadRequest(CamelModel):
    message_id: int = Field(..., gt=0)


class MessageItem(CamelModel):
    id: int
    project_id: int | None = None
    msg_type: str
    msg_content: str
    is_read: int
    create_time: datetime | None = None
