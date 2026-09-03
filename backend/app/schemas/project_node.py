"""项目画布节点 + 连线 + 表单 DTO（Api.md 第 8、9 章）"""
from decimal import Decimal

from pydantic import Field

from app.schemas.common import CamelModel


class NodeAddRequest(CamelModel):
    """新增节点：只能从节点模板库选择（V1.3 起强制 nodeTemplateId，禁止自由创建节点类型）"""

    project_id: int = Field(..., gt=0)
    node_template_id: int = Field(..., gt=0)
    sort: int = 0
    pos_x: Decimal = Decimal("0.00")
    pos_y: Decimal = Decimal("0.00")


class NodeUpdateRequest(CamelModel):
    id: int = Field(..., gt=0)
    node_title: str = Field(..., min_length=1, max_length=128)
    node_remark: str | None = None
    sort: int = 0
    pos_x: Decimal = Decimal("0.00")
    pos_y: Decimal = Decimal("0.00")


class NodeDeleteRequest(CamelModel):
    node_id: int = Field(..., gt=0)


class PositionItem(CamelModel):
    id: int = Field(..., gt=0)
    pos_x: Decimal
    pos_y: Decimal


class BatchPositionRequest(CamelModel):
    """拖拽防抖批量更新坐标：不触发消息推送"""

    project_id: int = Field(..., gt=0)
    positions: list[PositionItem] = Field(..., min_length=1)


# ---- 节点表单 ----

class FormFieldValueItem(CamelModel):
    """保存表单时的单条字段值"""

    id: int = Field(..., gt=0)  # project_node_form_value.id
    field_value: str | None = None


class FormValueSaveRequest(CamelModel):
    """全量覆盖保存，后提交覆盖先提交"""

    project_node_id: int = Field(..., gt=0)
    form_value_list: list[FormFieldValueItem] = []


class FormFieldOut(CamelModel):
    """节点表单定义 + 已填值（出参）"""

    id: int
    field_label: str
    field_type: str
    select_options: list[str] | None = None
    sort: int = 0
    field_value: str | None = None


# ---- 项目节点连线 ----

class ProjectEdgeAddRequest(CamelModel):
    project_id: int = Field(..., gt=0)
    source_node_id: int = Field(..., gt=0)
    target_node_id: int = Field(..., gt=0)
    label: str | None = Field(default=None, max_length=128)
