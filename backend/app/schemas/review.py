"""客户审核节点（V1.4.19）：客户提交审核结果，提交后锁定"""
import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class ReviewFeedbackFieldIn(CamelModel):
    """客户审核时填写的反馈字段值（V1.4.20）"""
    field_label: str = Field(..., min_length=1, max_length=128)
    field_type: Literal["text_single", "text_multi", "image"]
    field_value: str | None = None  # 图片填 uploads/xxx.jpg 相对路径


class ReviewSubmitRequest(CamelModel):
    """客户提交审核"""
    project_node_id: int = Field(..., gt=0)
    option: str = Field(..., min_length=1, max_length=64, description="客户选择的选项文字（必须在节点 review_options 内）")
    comment: str | None = Field(None, max_length=1000, description="批注")
    feedback_fields: list[ReviewFeedbackFieldIn] = []


class ReviewResultOut(CamelModel):
    """节点上已有的审核结果"""
    option: str
    comment: str | None = None
    time: datetime.datetime | None = None
