"""客户满意度评价 DTO（V1.4.17）

出参拆分：
- EvaluationPublicOut：公开字段（客户/内部通用，不含 reflection）；
- EvaluationDetailOut：内部字段（含 reflection / reflection_user_name / reflection_time）。
"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class EvaluationSubmitRequest(CamelModel):
    """客户提交评价入参：三项必填（1~5），备注选填"""

    project_id: int = Field(..., gt=0)
    design_score: int = Field(..., ge=1, le=5)
    service_score: int = Field(..., ge=1, le=5)
    product_score: int = Field(..., ge=1, le=5)
    customer_remark: str | None = Field(None, max_length=2000)


class ReflectionSaveRequest(CamelModel):
    """内部写反思入参（覆盖式）"""

    project_id: int = Field(..., gt=0)
    reflection: str = Field(..., min_length=1, max_length=5000)


class EvaluationPublicOut(CamelModel):
    """评价公开出参：客户与内部通用，不含反思"""

    design_score: int
    service_score: int
    product_score: int
    customer_remark: str | None = None
    evaluate_time: datetime | None = None


class EvaluationDetailOut(EvaluationPublicOut):
    """评价内部出参：仅内部接口返回，含反思"""

    reflection: str | None = None
    reflection_user_name: str | None = None
    reflection_time: datetime | None = None
