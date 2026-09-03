"""部门 DTO（仅管理员）

V1.4 起部门仅做人员组织分组，不再携带权限模板（role 字段保留兼容，恒为 NULL）。
"""
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel

# 用户角色可选范围（V1.4.2 简化为两类）。客户角色由客户账号自动获得，不在此列。
USER_ROLE_CHOICES = ("普通", "管理员")


class DeptAddRequest(CamelModel):
    dept_name: str = Field(..., min_length=1, max_length=64)
    dept_type: Literal["internal", "customer"] = "internal"


class DeptUpdateRequest(CamelModel):
    id: int = Field(..., gt=0)
    dept_name: str = Field(..., min_length=1, max_length=64)


class DeptDeleteRequest(CamelModel):
    id: int = Field(..., gt=0)


class DeptItem(CamelModel):
    id: int
    dept_name: str
    dept_type: str
    user_count: int = 0  # 该部门下的用户数
    create_time: datetime | None = None
