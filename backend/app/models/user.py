"""用户表 sys_user：内置角色 + 部门 + 客户账号；不做物理删除，仅启用/停用（V1.3 支持物理删除）"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysUser(Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="登录账号，唯一")
    password: Mapped[str] = mapped_column(String(128), nullable=False, comment="明文密码，内网使用")
    real_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="真实姓名")
    role: Mapped[str] = mapped_column(String(32), nullable=False, comment="角色：管理员/行政/设计总监/设计师/客户")
    dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="所属部门ID（sys_dept.id，客户账号为空）")
    customer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="历史兼容字段：V1.4.15 起客户账号改用 category_id 绑定公司，此字段仅存量保留")
    category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="客户账号绑定的客户单位ID（customer_category.id，仅 role=客户，V1.4.15）")
    is_enable: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, comment="0停用，1启用")
    login_fail_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0,
        comment="连续登录失败次数（成功即清零；V1.4.6 防暴力破解）"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True,
        comment="锁定截止时间（超过该时间自动解锁；V1.4.6 防暴力破解）"
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
