"""流程模板 DTO（Api.md 第 5、6 章）：整图提交 / 整图全量覆盖"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import CamelModel


class TemplateFormFieldIn(CamelModel):
    """模板表单字段定义（入参）：新增不带 id，更新可带 id（整图覆盖时仅溯源）"""

    id: int | None = None
    field_label: str = Field(..., min_length=1, max_length=128)
    # V1.4.3 扩展 image（上传图像）/ link（链接）
    field_type: Literal["text_single", "text_multi", "select", "image", "link"]
    select_options: list[str] | None = None  # 下拉选项数组；非下拉为 null
    sort: int = 0

    @field_validator("select_options")
    @classmethod
    def select_must_have_options(cls, v, info):
        if info.data.get("field_type") == "select" and not v:
            raise ValueError("下拉单选字段必须提供选项")
        return v


class TemplateNodeIn(CamelModel):
    """模板节点（入参）：带 id=已有节点更新，不带 id=新增；表单定义来自 node_template_id"""

    id: int | None = None
    node_template_id: int | None = None
    node_title: str = Field(..., min_length=1, max_length=128)
    node_remark: str | None = None
    sort: int = 0
    pos_x: Decimal = Decimal("0.00")
    pos_y: Decimal = Decimal("0.00")
    form_fields: list[TemplateFormFieldIn] = []


class TemplateEdgeIn(CamelModel):
    """模板连线（入参）：整图提交时 source/target 为节点在 nodes 数组中的序号或已有节点ID"""

    id: int | None = None
    source_node_id: int = Field(..., gt=0)
    target_node_id: int = Field(..., gt=0)
    label: str | None = Field(default=None, max_length=128)


class TemplateAddRequest(CamelModel):
    template_name: str = Field(..., min_length=1, max_length=128)
    nodes: list[TemplateNodeIn] = []
    edges: list[TemplateEdgeIn] = []


class TemplateUpdateRequest(CamelModel):
    """整图全量覆盖：单事务内先删后插"""

    id: int = Field(..., gt=0)
    template_name: str = Field(..., min_length=1, max_length=128)
    nodes: list[TemplateNodeIn] = []
    edges: list[TemplateEdgeIn] = []


# ---- 出参 ----

class TemplateListItem(CamelModel):
    id: int
    template_name: str
    create_user_name: str | None = None
    create_time: datetime | None = None


class TemplateFormFieldOut(CamelModel):
    id: int
    field_label: str
    field_type: str
    select_options: list[str] | None = None
    sort: int


class TemplateNodeOut(CamelModel):
    id: int
    node_template_id: int | None = None
    node_title: str
    node_remark: str | None = None
    sort: int
    pos_x: Decimal
    pos_y: Decimal
    form_fields: list[TemplateFormFieldOut] = []


class TemplateEdgeOut(CamelModel):
    id: int
    source_node_id: int
    target_node_id: int
    label: str | None = None


class TemplateDetail(CamelModel):
    id: int
    template_name: str
    nodes: list[TemplateNodeOut] = []
    edges: list[TemplateEdgeOut] = []


# ---- 模板连线独立接口 ----

class TemplateEdgeAddRequest(CamelModel):
    template_id: int = Field(..., gt=0)
    source_node_id: int = Field(..., gt=0)
    target_node_id: int = Field(..., gt=0)
    label: str | None = Field(default=None, max_length=128)
