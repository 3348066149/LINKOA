"""客户分类 + 客户库 DTO（Api.md 第 3、4 章）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel, PageQuery


# ---- 客户分类 ----

class CategoryAddRequest(CamelModel):
    category_name: str = Field(..., min_length=1, max_length=128)


class CategoryUpdateRequest(CamelModel):
    id: int = Field(..., gt=0)
    category_name: str = Field(..., min_length=1, max_length=128)


class CategoryItem(CamelModel):
    id: int
    category_name: str
    create_time: datetime | None = None


# ---- 客户 ----

class CustomerListQuery(PageQuery):
    category_id: int | None = None
    customer_name: str | None = None  # 模糊搜索


class CustomerAddRequest(CamelModel):
    category_id: int = Field(..., gt=0)
    customer_name: str = Field(..., min_length=1, max_length=128)
    contact: str | None = Field(None, max_length=128)
    remark: str | None = None


class CustomerUpdateRequest(CamelModel):
    id: int = Field(..., gt=0)
    category_id: int = Field(..., gt=0)
    customer_name: str = Field(..., min_length=1, max_length=128)
    contact: str | None = Field(None, max_length=128)
    remark: str | None = None


class CustomerItem(CamelModel):
    id: int
    category_id: int
    category_name: str | None = None
    customer_name: str
    contact: str | None = None
    remark: str | None = None
    cover_image: str | None = None
    create_time: datetime | None = None


class CustomerDetail(CamelModel):
    id: int
    category_id: int
    customer_name: str
    contact: str | None = None
    remark: str | None = None
    cover_image: str | None = None


class CustomerCoverRemoveRequest(CamelModel):
    customer_id: int = Field(..., gt=0)
