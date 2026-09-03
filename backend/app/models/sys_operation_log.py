"""系统操作日志表 sys_operation_log：不可修改、不可删除，审计溯源，永久留存"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysOperationLog(Base):
    __tablename__ = "sys_operation_log"
    __table_args__ = (
        Index("idx_oper_user_id", "oper_user_id"),
        Index("idx_related_project_id", "related_project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    oper_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="操作人ID")
    oper_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="操作时间")
    oper_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="操作类型枚举（见 Database.md 清单）")
    oper_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="变更简要描述（人类可读）")
    related_project_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="null=全局操作；不为空代表归属某个项目"
    )
