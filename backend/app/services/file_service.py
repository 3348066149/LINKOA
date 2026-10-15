"""附件 Service：日期隔离 + UUID 存储、单文件 1G 上限、仅上传本人可删"""
import os
import uuid
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment, Project, ProjectNode, SysUser
from app.schemas import AttachmentItem, AttachmentUploadData, FileItem
from app.services import log_service, project_service
from app.utils.exceptions import BusinessException

MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 单文件最大 1G

# 扩展名黑名单：禁止可执行脚本/HTML/可执行文件上传，防存储型 XSS 与木马
FORBIDDEN_EXT = {
    ".html", ".htm", ".svg", ".xhtml",
    ".js", ".mjs", ".cjs",
    ".exe", ".dll", ".so", ".bin",
    ".sh", ".bat", ".cmd", ".ps1", ".msi",
    ".php", ".asp", ".aspx", ".jsp",
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
UPLOAD_ROOT = os.path.join(BASE_DIR, settings.UPLOAD_DIR)


def remove_disk_file(file_path: str) -> None:
    """删除磁盘文件，失败不阻塞业务流程（记录警告即可）。"""
    try:
        if file_path and os.path.isfile(file_path):
            os.remove(file_path)
    except Exception as exc:  # noqa: BLE001 - 有意吞掉
        print(f"[WARN] 删除物理文件失败，忽略：{file_path} -> {type(exc).__name__}: {exc}")


def _check_category_scope(db: Session, project: Project, operator: dict) -> None:
    """客户账号数据隔离：客户只能访问自己 category_id 下的项目附件。"""
    if operator.get("role") != "客户":
        return
    if project.category_id is None or project.category_id != operator.get("category_id"):
        raise BusinessException(403, "无权访问该项目附件")


def _get_project_or_400(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise BusinessException(400, "项目不存在")
    return project


def upload(db: Session, operator: dict, project_id: int, project_node_id: int, file: UploadFile) -> AttachmentUploadData:
    project = project_service.get_project_or_400(db, project_id)
    project_service.check_project_archived(project)

    node = db.get(ProjectNode, project_node_id)
    if node is None or node.project_id != project_id:
        raise BusinessException(400, "节点不存在或不属于当前项目")

    # 存储路径：uploads/YYYYMMDD/UUID_原始文件名（日期隔离 + UUID 防重名）
    date_dir = datetime.now().strftime("%Y%m%d")
    save_dir = os.path.join(UPLOAD_ROOT, date_dir)
    os.makedirs(save_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "unnamed")

    # 扩展名黑名单：禁止上传脚本/HTML/可执行文件
    ext = os.path.splitext(safe_name)[1].lower()
    if ext in FORBIDDEN_EXT:
        raise BusinessException(400, f"禁止上传 {ext} 类型文件（安全限制）")

    save_name = f"{uuid.uuid4().hex}_{safe_name}"
    save_path = os.path.join(save_dir, save_name)

    size = 0
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)  # 1MB 分块读写，支持大文件
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise BusinessException(400, "文件大小超过 1G 上限")
                f.write(chunk)
    except BusinessException:
        remove_disk_file(save_path)
        raise
    except OSError:
        remove_disk_file(save_path)
        raise BusinessException(500, "文件写入失败")

    attachment = Attachment(
        project_id=project_id,
        project_node_id=project_node_id,
        file_name=safe_name,
        # 数据库存相对路径（相对 uploads/ 根目录），保证项目整体拷贝移植后仍可定位文件
        file_path=os.path.join(date_dir, save_name),
        file_size=size,
        upload_user_id=operator["id"],
    )
    db.add(attachment)
    db.flush()
    log_service.add_log(db, operator["id"], "attachment_upload", f"上传附件：{safe_name}（节点：{node.node_title}）", related_project_id=project_id)
    db.commit()
    return AttachmentUploadData(id=attachment.id, file_name=safe_name, file_path=save_path, file_size=size)


def list_by_node(db: Session, project_node_id: int, operator: dict) -> list[AttachmentItem]:
    node = db.get(ProjectNode, project_node_id)
    if node is None:
        return []
    project = _get_project_or_400(db, node.project_id)
    _check_category_scope(db, project, operator)
    stmt = (
        select(Attachment, SysUser.real_name.label("upload_user_name"))
        .outerjoin(SysUser, SysUser.id == Attachment.upload_user_id)
        .where(Attachment.project_node_id == project_node_id)
        .order_by(Attachment.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        AttachmentItem(
            id=a.id, file_name=a.file_name, file_size=a.file_size,
            upload_user_id=a.upload_user_id, upload_user_name=name or "已删除用户", create_time=a.create_time,
        )
        for a, name in rows
    ]


def list_by_project(db: Session, project_id: int, operator: dict) -> list[FileItem]:
    """文件管理页：某项目下的全部附件（含所属节点标题，节点已删则 node_title 为空）"""
    project = _get_project_or_400(db, project_id)
    _check_category_scope(db, project, operator)
    stmt = (
        select(Attachment, ProjectNode.node_title, SysUser.real_name.label("upload_user_name"))
        .outerjoin(ProjectNode, ProjectNode.id == Attachment.project_node_id)
        .outerjoin(SysUser, SysUser.id == Attachment.upload_user_id)
        .where(Attachment.project_id == project_id)
        .order_by(Attachment.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        FileItem(
            id=a.id, file_name=a.file_name, file_size=a.file_size,
            project_id=a.project_id, project_node_id=a.project_node_id,
            node_title=node_title, upload_user_id=a.upload_user_id,
            upload_user_name=name or "已删除用户", create_time=a.create_time,
        )
        for a, node_title, name in rows
    ]


def delete_attachment(db: Session, operator: dict, attachment_id: int) -> None:
    """上传本人或管理员可删；归档项目禁止删除；同步删除磁盘文件（V1.4 管理员可删任意文件）"""
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise BusinessException(400, "附件不存在")

    project = project_service.get_project_or_400(db, attachment.project_id)
    project_service.check_project_archived(project)

    if attachment.upload_user_id != operator["id"] and operator["role"] != "管理员":
        raise BusinessException(403, "无权删除他人附件")

    file_path = attachment.file_path
    file_name = attachment.file_name
    db.delete(attachment)
    log_service.add_log(db, operator["id"], "attachment_delete", f"删除附件：{file_name}", related_project_id=attachment.project_id)
    db.commit()
    # DB 里存的是相对 uploads/ 的相对路径（如 20260831/uuid.pdf），必须拼上 UPLOAD_ROOT 才能定位真实文件；
    # 否则 remove_disk_file 会按 CWD 解析，永远删不掉磁盘上的孤儿文件。兼容历史绝对路径。
    if file_path and not os.path.isabs(file_path):
        file_path = os.path.join(UPLOAD_ROOT, file_path)
    remove_disk_file(file_path)


def get_download_info(db: Session, attachment_id: int, operator: dict) -> tuple[str, str]:
    """返回 (磁盘绝对路径, 原始文件名)，由路由层返回文件流；兼容历史绝对路径"""
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise BusinessException(400, "附件不存在")
    project = _get_project_or_400(db, attachment.project_id)
    _check_category_scope(db, project, operator)
    path = attachment.file_path
    if not os.path.isabs(path):
        path = os.path.join(UPLOAD_ROOT, path)
    if not os.path.isfile(path):
        raise BusinessException(400, "文件已丢失")
    return path, attachment.file_name
