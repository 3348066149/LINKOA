"""用户管理 DTO（Api.md 第 2 章，仅管理员）

V1.4：部门仅组织归属，权限由用户自身角色（role）决定。
"""
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class SysUserCreateRequest(CamelModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    real_name: str = Field(..., min_length=1, max_length=64)
    # 内部员工：dept_id（组织归属）+ role（普通/管理员，V1.4.2 起两类）
    # 客户账号：category_id（绑定客户单位/公司，role 固定为「客户」）
    dept_id: int | None = Field(None, gt=0)
    role: Literal["普通", "管理员"] | None = None
    customer_id: int | None = Field(None, gt=0)  # 历史兼容字段，V1.4.15 起新建客户账号不再使用
    category_id: int | None = Field(None, gt=0)


class SysUserUpdateRequest(CamelModel):
    """编辑用户：可改所属部门 + 角色 + 真实姓名（账号不可改，密码走重置）"""

    id: int = Field(..., gt=0)
    real_name: str = Field(..., min_length=1, max_length=64)
    dept_id: int | None = Field(None, gt=0)
    role: Literal["普通", "管理员"] | None = None


class ResetPwdRequest(CamelModel):
    user_id: int = Field(..., gt=0)
    new_password: str = Field(..., min_length=1, max_length=128)


class SetEnableRequest(CamelModel):
    user_id: int = Field(..., gt=0)
    is_enable: Literal[0, 1]


class DeleteUserRequest(CamelModel):
    user_id: int = Field(..., gt=0)


class SysUserItem(CamelModel):
    """用户列表项（密码不返回前端，V1.4.21）"""

    id: int
    username: str
    real_name: str
    role: str
    dept_id: int | None = None
    dept_name: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    is_enable: int
    # V1.4.6 登录防暴力破解：账号是否处于锁定状态（管理员可手动解锁）
    is_locked: bool = False


class UnlockUserRequest(CamelModel):
    """管理员手动解锁账号"""

    user_id: int = Field(..., gt=0)
