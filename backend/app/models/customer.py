"""客户分类表 customer_category + 客户表 customer"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.timeutil import beijing_now


class CustomerCategory(Base):
    """客户分类：分类下存在客户时禁止删除（后端 400 拦截）"""

    __tablename__ = "customer_category"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    category_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="分类名称")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )


class Customer(Base):
    """客户：存在关联项目时禁止删除（后端 400 拦截）"""

    __tablename__ = "customer"
    __table_args__ = (Index("idx_category_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="关联客户分类ID（逻辑关联，无物理外键）")
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="客户名称")
    contact: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="联系方式（电话/微信/邮箱）")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="客户备注（对接人、合作信息）")
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="卡片封面图相对路径（uploads/cover 下）")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=beijing_now, onupdate=beijing_now, comment="更新时间"
    )
