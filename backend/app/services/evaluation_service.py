"""客户满意度评价 Service：提交（一次性锁定）、查询、反思（覆盖式）"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProjectEvaluation, SysUser
from app.schemas import (
    EvaluationDetailOut,
    EvaluationPublicOut,
    EvaluationSubmitRequest,
    ReflectionSaveRequest,
)
from app.services import message_service, project_service
from app.utils.exceptions import BusinessException


def _to_public(e: ProjectEvaluation) -> EvaluationPublicOut:
    """公开 DTO：不含 reflection，客户/内部通用"""
    return EvaluationPublicOut(
        design_score=e.design_score,
        service_score=e.service_score,
        product_score=e.product_score,
        customer_remark=e.customer_remark,
        evaluate_time=e.evaluate_time,
    )


def _to_detail(db: Session, e: ProjectEvaluation) -> EvaluationDetailOut:
    """内部 DTO：含反思（客户不可见），反思人姓名兜底"已删除用户" """
    name = None
    if e.reflection_user_id is not None:
        u = db.get(SysUser, e.reflection_user_id)
        name = u.real_name if u else "已删除用户"
    return EvaluationDetailOut(
        design_score=e.design_score,
        service_score=e.service_score,
        product_score=e.product_score,
        customer_remark=e.customer_remark,
        evaluate_time=e.evaluate_time,
        reflection=e.reflection,
        reflection_user_name=name,
        reflection_time=e.reflection_time,
    )


def submit(db: Session, current_user: dict, req: EvaluationSubmitRequest) -> EvaluationPublicOut:
    """客户提交评价：校验归属/已归档/未评价，落库 + 推送消息，一次性锁定"""
    project = project_service.get_project_or_400(db, req.project_id)

    cat_id = current_user.get("category_id")
    if not cat_id or project.category_id != cat_id:
        raise BusinessException(403, "无权评价该项目")
    if project.project_status != "已归档":
        raise BusinessException(400, "项目尚未归档，暂不能评价")

    existing = db.execute(
        select(ProjectEvaluation).where(ProjectEvaluation.project_id == req.project_id)
    ).scalars().first()
    if existing is not None:
        raise BusinessException(400, "该项目已评价，不可重复提交")

    evaluation = ProjectEvaluation(
        project_id=req.project_id,
        design_score=req.design_score,
        service_score=req.service_score,
        product_score=req.product_score,
        customer_remark=req.customer_remark,
        evaluate_user_id=current_user["id"],
        evaluate_time=datetime.now(),
    )
    db.add(evaluation)
    db.flush()

    # 不 commit，随提交事务统一提交
    message_service.push_evaluation_create(db, project)

    db.commit()
    db.refresh(evaluation)
    return _to_public(evaluation)


def get(db: Session, project_id: int, current_user: dict) -> EvaluationPublicOut | EvaluationDetailOut | None:
    """查询评价：客户校验单位隔离且只返回公开字段；内部返回含反思的 Detail；无评价返回 None"""
    project = project_service.get_project_or_400(db, project_id)

    is_customer = current_user.get("role") == "客户"
    if is_customer:
        cat_id = current_user.get("category_id")
        if not cat_id or project.category_id != cat_id:
            raise BusinessException(403, "无权查看该项目的评价")

    evaluation = db.execute(
        select(ProjectEvaluation).where(ProjectEvaluation.project_id == project_id)
    ).scalars().first()
    if evaluation is None:
        return None

    if is_customer:
        return _to_public(evaluation)
    return _to_detail(db, evaluation)


def save_reflection(db: Session, current_user: dict, req: ReflectionSaveRequest) -> None:
    """内部写反思（覆盖式）：所有内部员工可写；评价不存在时报错"""
    evaluation = db.execute(
        select(ProjectEvaluation).where(ProjectEvaluation.project_id == req.project_id)
    ).scalars().first()
    if evaluation is None:
        raise BusinessException(400, "客户尚未评价，暂不能填写反思")

    evaluation.reflection = req.reflection
    evaluation.reflection_user_id = current_user["id"]
    evaluation.reflection_time = datetime.now()
    db.commit()
