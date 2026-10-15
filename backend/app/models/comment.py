"""评论表 comment：项目级评论；仅发布本人可删除；归档项目禁止增删"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.timeutil import beijing_now


class Comment(Base):
    __tablename__ = "comment"
    __table_args__ = (Index("idx_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="项目ID")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")
    create_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="评论人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=beijing_now, comment="评论时间")
