"""项目环节表 project_stage（V1.4.19）：替代原来的单一 expect_time，支持多环节倒计时"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.timeutil import beijing_now


class ProjectStage(Base):
    """项目环节：管理员自定义的阶段节点（如「IP设计截止」「打样制作」）。

    - plan_time：预计时间（必填），卡片倒计时基于此计算
    - actual_time：实际完成时间（可空），管理员手动填写；为空 = 该环节进行中
    - 卡片倒计时规则：取 actual_time 为空的第一条环节，按其 plan_time 算
    """

    __tablename__ = "project_stage"
    __table_args__ = (
        Index("idx_stage_project", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属项目ID")
    stage_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="环节名称（如 IP设计截止）")
    plan_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预计时间")
    actual_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际完成时间（管理员手动填，空=进行中）")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="排序")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )
