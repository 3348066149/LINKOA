"""部门表 sys_dept：内置部门（研发部/设计部/市场部，带权限模板 role）+ 客户部门

- dept_type='internal'：内部员工部门，role 字段为该部门的默认权限（设计师/行政/设计总监）
- dept_type='customer'：客户部门，customer_id 关联客户，该部门下账号 role 恒为「客户」（只读）
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysDept(Base):
    __tablename__ = "sys_dept"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    dept_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="部门名称，唯一")
    dept_type: Mapped[str] = mapped_column(String(16), nullable=False, default="internal", comment="internal 内置员工部门 / customer 客户部门")
    role: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="内部部门默认权限角色：设计师/行政/设计总监")
    customer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="客户部门关联的客户ID（customer.id）")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
