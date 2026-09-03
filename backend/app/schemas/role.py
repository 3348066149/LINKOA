"""自定义角色 DTO（仅管理员）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class RoleAddRequest(CamelModel):
    role_name: str = Field(..., min_length=1, max_length=32)


class RoleDeleteRequest(CamelModel):
    id: int = Field(..., gt=0)


class RoleItem(CamelModel):
    id: int
    role_name: str
    user_count: int = 0  # 使用该角色的用户数（删除时用于占用拦截提示）
    create_time: datetime | None = None
