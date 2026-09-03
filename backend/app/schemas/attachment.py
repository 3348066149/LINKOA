"""附件 DTO（Api.md 第 10 章）"""
from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class AttachmentDeleteRequest(CamelModel):
    attachment_id: int = Field(..., gt=0)


class AttachmentUploadData(CamelModel):
    """上传成功返回"""

    id: int
    file_name: str
    file_path: str
    file_size: int


class AttachmentItem(CamelModel):
    id: int
    file_name: str
    file_size: int
    upload_user_id: int
    upload_user_name: str | None = None
    create_time: datetime | None = None


class FileItem(CamelModel):
    """文件管理页：某项目下的附件（含所属节点标题）"""

    id: int
    file_name: str
    file_size: int
    project_id: int
    project_node_id: int
    node_title: str | None = None
    upload_user_id: int
    upload_user_name: str | None = None
    create_time: datetime | None = None
