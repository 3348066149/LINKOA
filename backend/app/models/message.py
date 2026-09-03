"""消息表 message：推送范围=项目创建人+关联设计师（排除操作人）；携带 project_id 供前端跳转"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (
        Index("idx_receive_user_id", "receive_user_id"),
        Index("idx_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    receive_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="接收消息用户ID")
    project_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联项目ID（用于前端点击跳转，可空）")
    msg_type: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="消息类型：node_create / node_update / node_delete / form_update / comment_create"
    )
    msg_content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息简要内容（人类可读文案）")
    is_read: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="0未读，1已读")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="消息生成时间")
