"""报表导出 DTO（Api.md 第 14 章）"""
from datetime import datetime
from typing import Literal

from app.schemas.common import CamelModel


class ReportExportQuery(CamelModel):
    """导出项目列表 Excel 筛选条件（全部可选）"""

    project_status: Literal["进行中", "已归档"] | None = None
    category_id: int | None = None  # 客户单位（V1.4.7）
    start_time: datetime | None = None
    end_time: datetime | None = None
