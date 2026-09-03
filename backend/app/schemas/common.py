"""通用 DTO：分页结构、通用 ID 入参、基类配置

全部模型开启 camelCase 别名：Python 侧用 snake_case 字段名，
序列化/反序列化时与接口文档的 camelCase 入参出参自动对应。
"""
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """基类：camelCase 别名 + 允许按字段名赋值"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class IdRequest(CamelModel):
    """通用删除/详情入参：{ "id": 1 }"""

    id: int = Field(..., gt=0)


class PageQuery(CamelModel):
    """分页查询参数基类（含通用排序，字段白名单由各 Service 校验）"""

    page_num: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=200)
    sort_field: str | None = None  # 排序字段（camelCase，Service 侧白名单映射）
    sort_order: Literal["asc", "desc"] | None = None  # 排序方向


class PageResult(CamelModel, Generic[T]):
    """分页返回结构：{items, total, pageNum, pageSize}"""

    items: list[T] = []
    total: int = 0
    page_num: int = 1
    page_size: int = 10
