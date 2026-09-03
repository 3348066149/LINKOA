"""登录模块 DTO（Api.md 第 1 章）"""
from pydantic import Field

from app.schemas.common import CamelModel


class LoginRequest(CamelModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UpdateMyPwdRequest(CamelModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)


class UserInfo(CamelModel):
    id: int
    username: str
    real_name: str
    role: str
    dept_id: int | None = None
    dept_name: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    category_id: int | None = None  # 客户账号绑定的客户单位ID（V1.4.15 起直接由 category_id 取公司）
    company_name: str | None = None  # 客户账号所属公司（客户单位）名（V1.4.7）


class LoginData(CamelModel):
    token: str
    user_info: UserInfo
