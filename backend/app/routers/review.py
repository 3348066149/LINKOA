"""客户审核节点路由（V1.4.19）"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Project, ProjectNode
from app.schemas.review import ReviewSubmitRequest
from app.services import node_service, review_service
from app.utils.exceptions import BusinessException, ok

router = APIRouter()


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
    """客户审核反馈文件上传（V1.4.20 起，V1.4.22 放开多类型）

    仅客户账号、节点必须是待审审核节点、归属本客户单位。
    客户反馈现支持图片/PDF/视频/Office 等任意类型（与设计师侧一致），
    因此与节点表单上传共用 node_service.save_upload，落盘目录统一为 node_form/。

    注意：multipart 字段名必须是 camelCase 的 projectNodeId —— 与前端以及其它上传接口
    （attachment/customer/project cover）保持一致。V1.4.21 修复：此前声明为 project_node_id，
    前端传 projectNodeId 会触发 422，被全局处理器包成 HTTP 200 + code=400「请求参数错误」，
    客户点上传后毫无反应。
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

    path = node_service.save_upload(file, "node_form")
    return ok({"path": path})
