"""消息中心 DTO（Api.md 第 12 章）"""
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, PageQuery


class MessageListQuery(PageQuery):
    is_read: Literal[0, 1] | None = None
    # V1.4.21 消息降噪：默认只返回关键通知（审核/评价/评论）；
    # 传 true 时把常规操作（节点增删改、表单填写）的历史消息一并带出
    include_routine: bool = False


class MessageReadRequest(CamelModel):
    message_id: int = Field(..., gt=0)


class MessageReadAllRequest(CamelModel):
    """一键已读入参（V1.4.21）

    - 不传 projectId：全部项目
    - 传 projectId：只标记该项目的消息
    - includeRoutine：是否连同「常规操作」消息一起标记（默认 false，与消息中心默认展示口径一致，
      避免出现「只看到 11 条却说标记了 81 条」）
    """

    project_id: int | None = Field(None, gt=0)
    include_routine: bool = False


class MessageItem(CamelModel):
    id: int
    project_id: int | None = None
    msg_type: str
    msg_content: str
    is_read: int
    create_time: datetime | None = None
