"""节点模板 DTO（V1.3 新增）"""
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class NodeTemplateFieldIn(CamelModel):
    field_label: str = Field(..., min_length=1, max_length=128)
    # V1.4.3 扩展 image（上传图像）/ link（链接）
    field_type: Literal["text_single", "text_multi", "select", "image", "link"]
    select_options: list[str] | None = None
    sort: int = 0

    @field_validator("select_options")
    @classmethod
    def select_must_have_options(cls, v, info):
        if info.data.get("field_type") == "select" and not v:
            raise ValueError("下拉单选字段必须提供选项")
        return v


class NodeTemplateAddRequest(CamelModel):
    node_title: str = Field(..., min_length=1, max_length=128)
    node_remark: str | None = None
    # 节点图标：预设图标组件名（如 Picture）或以 uploads/ 开头的自定义图标路径
    icon: str | None = Field(None, max_length=512)
    sort: int = 0
    form_fields: list[NodeTemplateFieldIn] = []
    is_review: bool = False
    review_options: list[str] | None = None
    # V1.4.20：客户审核反馈字段
    client_review_fields: list[NodeTemplateFieldIn] = []


class NodeTemplateUpdateRequest(CamelModel):
    id: int = Field(..., gt=0)
    node_title: str = Field(..., min_length=1, max_length=128)
    node_remark: str | None = None
    icon: str | None = Field(None, max_length=512)
    sort: int = 0
    form_fields: list[NodeTemplateFieldIn] = []
    is_review: bool = False
    review_options: list[str] | None = None
    client_review_fields: list[NodeTemplateFieldIn] = []


class NodeTemplateItem(CamelModel):
    id: int
    node_title: str
    node_remark: str | None = None
    icon: str | None = None
    sort: int
    form_fields: list[NodeTemplateFieldIn] = []
    is_review: bool = False
    review_options: list[str] | None = None
    client_review_fields: list[NodeTemplateFieldIn] = []
