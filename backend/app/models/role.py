"""自定义角色表 sys_role：管理员自定义业务角色（如研发人员），供建用户时选择

权限语义：自定义角色登录后拥有与「设计师」相同的权限（全部查询 + 节点/表单/评论/附件等登录即可的操作）。
"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SysRole(Base):
    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    role_name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="角色名称，唯一")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
