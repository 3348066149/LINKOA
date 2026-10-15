"""项目表 project + 项目-设计师关联表 project_designer_rel"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.timeutil import beijing_now


class Project(Base):
    """项目：状态 进行中 / 已归档；已归档全部只读；已归档须先取消归档才能删除

    V1.4.7 结构调整：客户分类=客户单位（公司），customer 表条目=单位下的对接人。
    category_id 归属客户单位；customer_id 保留为首位对接人（兼容老数据/报表）；
    全部对接人见 project_contact_rel 关联表。
    """

    __tablename__ = "project"
    __table_args__ = (
        Index("idx_customer_id", "customer_id"),
        Index("idx_category_id", "category_id"),
        Index("idx_project_status", "project_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="项目名称")
    category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="归属客户单位ID（customer_category.id，V1.4.7）")
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="首位对接人ID（customer.id，V1.4.7 起语义为对接人）")
    project_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="项目开始时间（可编辑）")
    expect_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="预计时间（截止）")
    project_status: Mapped[str] = mapped_column(String(32), nullable=False, default="进行中", comment="进行中 / 已归档")
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="卡片封面图相对路径（uploads/ 下）")
    create_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="创建人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )


class ProjectDesignerRel(Base):
    """项目-设计师关联：仅溯源展示，不做权限控制；一个项目可关联多个设计师"""

    __tablename__ = "project_designer_rel"
    __table_args__ = (
        Index("idx_project_id", "project_id"),
        Index("idx_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="项目ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="设计师用户ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")


class ProjectContactRel(Base):
    """项目-客户对接人关联（V1.4.7）：对接人 = 客户单位（customer_category）下的 customer 条目"""

    __tablename__ = "project_contact_rel"
    __table_args__ = (
        Index("idx_pcr_project_id", "project_id"),
        Index("idx_pcr_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="项目ID")
    customer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="对接人ID（customer.id）")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
