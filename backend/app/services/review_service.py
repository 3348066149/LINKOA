"""客户审核 service（V1.4.19）"""
import json

from sqlalchemy.orm import Session

from app.models import Project, ProjectNode
from app.schemas.review import ReviewSubmitRequest
from app.services import log_service, message_service
from app.utils.exceptions import BusinessException
from app.utils.timeutil import beijing_now


def _parse_options(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return [str(x) for x in v] if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def submit_review(db: Session, customer_user: dict, req: ReviewSubmitRequest) -> None:
    """客户提交审核：
    - 节点必须是审核节点（is_review=True）
    - 选项必须在节点 review_options 内
    - 必须是本客户单位名下项目
    - 已审核过的节点不能重复提交（锁定）
    """
    node = db.get(ProjectNode, req.project_node_id)
    if node is None:
        raise BusinessException(400, "节点不存在")
    project = db.get(Project, node.project_id)
    if project is None:
        raise BusinessException(400, "所属项目不存在")

    # 客户账号归属校验
    if customer_user.get("role") != "客户":
        raise BusinessException(403, "仅客户账号可执行审核")
    cat_id = customer_user.get("category_id")
    if not cat_id or project.category_id != cat_id:
        raise BusinessException(403, "无权审核该项目")

    if not node.is_review:
        raise BusinessException(400, "该节点不是审核节点")

    options = _parse_options(node.review_options)
    if req.option not in options:
        raise BusinessException(400, f"审核选项无效，可选值：{' / '.join(options)}")

    if node.review_result:
        raise BusinessException(400, "该节点已审核，不可重复提交")

    result = {
        "option": req.option,
        "comment": req.comment or "",
        "time": beijing_now().strftime("%Y-%m-%d %H:%M:%S"),
        "reviewer": customer_user.get("real_name") or "",
    }
    node.review_result = json.dumps(result, ensure_ascii=False)

    # V1.4.20：保存客户反馈字段值
    from app.models import ProjectNodeFormValue
    for f in req.feedback_fields:
        if f.field_value is None or f.field_value == "":
            continue
        db.add(ProjectNodeFormValue(
            project_node_id=node.id,
            field_label=f.field_label,
            field_type=f.field_type,
            field_value=f.field_value,
            side="client",
            create_user_id=customer_user["id"],
        ))

    log_service.add_log(db, customer_user["id"], "customer_review",
                        f"客户审核节点「{node.node_title}」：{req.option}",
                        related_project_id=project.id)
    # 给我方设计师推送消息
    message_service.push(db, project, customer_user["id"], customer_user.get("real_name", "客户"),
                        "customer_review", node_title=node.node_title, comment_content=req.option)
    db.commit()


def reset_review(db: Session, operator: dict, project_node_id: int) -> None:
    """管理员重置客户审核结果：清 review_result + 删 side=client 反馈值，客户可重新提交（V1.4.20）"""
    from sqlalchemy import delete
    from app.models import ProjectNodeFormValue
    node = db.get(ProjectNode, project_node_id)
    if node is None:
        raise BusinessException(400, "节点不存在")
    if not node.is_review:
        raise BusinessException(400, "该节点不是审核节点")
    project = db.get(Project, node.project_id)
    node.review_result = None
    db.execute(delete(ProjectNodeFormValue).where(
        ProjectNodeFormValue.project_node_id == project_node_id,
        ProjectNodeFormValue.side == "client",
    ))
    log_service.add_log(db, operator["id"], "customer_review_reset",
                        f"重置客户审核：{node.node_title}",
                        related_project_id=project.id if project else None)
    db.commit()


def list_pending_reviews(db: Session, customer_user: dict) -> list[dict]:
    """客户门户首页：返回该客户单位下所有"待审核"节点列表（按项目分组）"""
    cat_id = customer_user.get("category_id")
    if not cat_id:
        return []
    from app.models import Project as _P
    from sqlalchemy import select
    rows = db.execute(
        select(ProjectNode, _P)
        .join(_P, _P.id == ProjectNode.project_id)
        .where(
            ProjectNode.is_review.is_(True),
            ProjectNode.review_result.is_(None),
            _P.category_id == cat_id,
        )
        .order_by(_P.id, ProjectNode.sort, ProjectNode.id)
    ).all()
    result = []
    for node, project in rows:
        try:
            client_fields = json.loads(node.client_review_fields) if node.client_review_fields else []
        except (json.JSONDecodeError, TypeError):
            client_fields = []
        result.append({
            "projectId": project.id,
            "projectName": project.project_name,
            "projectStatus": project.project_status,
            "nodeId": node.id,
            "nodeTitle": node.node_title,
            "icon": node.icon,
            "reviewOptions": _parse_options(node.review_options),
            "clientReviewFields": client_fields,
        })
    return result
