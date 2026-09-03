"""附件表 attachment：本地磁盘存储 uploads/YYYYMMDD/UUID_原始文件名；仅上传本人可删除"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Attachment(Base):
    __tablename__ = "attachment"
    __table_args__ = (
        Index("idx_project_id", "project_id"),
        Index("idx_project_node_id", "project_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键自增")
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属项目ID")
    project_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="所属节点ID")
    file_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, comment="服务器本地磁盘完整路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="文件大小（byte）")
    upload_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="上传人ID")
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), comment="上传时间")
