"""操作审计日志 DTO（Api.md 第 13 章，只读无增删改）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel, PageQuery


class LogGlobalQuery(PageQuery):
    oper_user_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    oper_type: str | None = None


class LogItem(CamelModel):
    id: int
    oper_user_id: int
    oper_user_name: str | None = None
    oper_time: datetime | None = None
    oper_type: str
    oper_desc: str | None = None
    related_project_id: int | None = None
