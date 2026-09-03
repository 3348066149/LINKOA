"""客户满意度评价路由（V1.4.17）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_not_customer, require_roles
from app.schemas import EvaluationSubmitRequest, ReflectionSaveRequest
from app.services import evaluation_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/submit")
def evaluation_submit(
    req: EvaluationSubmitRequest,
    current_user: dict = Depends(require_roles("客户")),
    db: Session = Depends(get_db),
):
    """客户提交评价：三项 1~5 星 + 备注，提交后锁定不可改"""
    return ok(evaluation_service.submit(db, current_user, req).model_dump(by_alias=True))


@router.get("/{projectId}")
def evaluation_get(
    projectId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询评价：客户返回公开 DTO（无 reflection），内部返回 Detail DTO（含 reflection）"""
    data = evaluation_service.get(db, projectId, current_user)
    if data is None:
        return ok(None)
    return ok(data.model_dump(by_alias=True))


@router.post("/reflection")
def evaluation_reflection(
    req: ReflectionSaveRequest,
    current_user: dict = Depends(require_not_customer()),
    db: Session = Depends(get_db),
):
    """内部写反思（覆盖式），客户不可见"""
    evaluation_service.save_reflection(db, current_user, req)
    return ok(None)
