"""评论 DTO（Api.md 第 11 章）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class CommentAddRequest(CamelModel):
    project_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1)


class CommentDeleteRequest(CamelModel):
    comment_id: int = Field(..., gt=0)


class CommentItem(CamelModel):
    id: int
    project_id: int
    content: str
    create_user_id: int
    create_user_name: str | None = None
    create_time: datetime | None = None
