"""客户审核节点路由（V1.4.19）"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models import Project, ProjectNode
from app.schemas.review import ReviewSubmitRequest
from app.services import review_service
from app.utils.exceptions import BusinessException, ok

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_ROOT = os.path.join(BASE_DIR, settings.UPLOAD_DIR)


@router.post("/submit")
def review_submit(
    req: ReviewSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review_service.submit_review(db, current_user, req)
    return ok(None)


@router.get("/pending")
def review_pending(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(review_service.list_pending_reviews(db, current_user))


@router.post("/reset")
def review_reset(
    req: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员重置审核结果（V1.4.20），body: {projectNodeId}"""
    if current_user.get("role") not in ("管理员", "设计师"):
        raise BusinessException(403, "仅管理员可重置审核")
    review_service.reset_review(db, current_user, int(req["projectNodeId"]))
    return ok(None)


@router.post("/upload")
def review_upload(
    file: UploadFile = File(...),
    projectNodeId: int = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """客户审核反馈图片上传（V1.4.20）：仅客户账号、节点必须是待审审核节点、归属本客户单位

    注意：multipart 字段名必须是 camelCase 的 projectNodeId —— 与前端 el-upload 的
    :data="{projectNodeId: ...}" 以及其它上传接口（attachment/customer/project cover）保持一致。
    V1.4.21 修复：此前声明为 project_node_id，前端传 projectNodeId 会触发 422，
    被全局处理器包成 HTTP 200 + code=400「请求参数错误」，客户点上传后毫无反应。
    """
    if current_user.get("role") != "客户":
        raise BusinessException(403, "仅客户账号可上传")
    node = db.get(ProjectNode, projectNodeId)
    if node is None or not node.is_review or node.review_result:
        raise BusinessException(400, "节点不存在或已完成审核")
    project = db.get(Project, node.project_id)
    if project is None:
        raise BusinessException(400, "项目不存在")
    cat_id = current_user.get("category_id")
    if not cat_id or project.category_id != cat_id:
        raise BusinessException(403, "无权上传该项目")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise BusinessException(400, "仅支持 jpg/png/webp/gif 图片")
    date_dir = datetime.now().strftime("%Y%m%d")
    save_dir = os.path.join(UPLOAD_ROOT, date_dir)
    os.makedirs(save_dir, exist_ok=True)
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, save_name)
    size = 0
    with open(save_path, "wb") as f:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > 5 * 1024 * 1024:
                f.close()
                os.remove(save_path)
                raise BusinessException(400, "图片不能超过 5MB")
            f.write(chunk)
    return ok({"path": f"{date_dir}/{save_name}"})
