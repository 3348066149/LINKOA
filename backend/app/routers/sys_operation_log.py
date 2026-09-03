"""操作审计日志路由（Api.md 第 13 章，只读）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import LogGlobalQuery
from app.services import log_service
from app.utils.exceptions import ok

router = APIRouter()


@router.get("/globalList")
def global_list(
    query: LogGlobalQuery = Depends(),
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    return ok(log_service.global_list(db, query).model_dump(by_alias=True))


@router.get("/projectLog")
def project_log(
    projectId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = log_service.project_log(db, projectId)
    return ok([i.model_dump(by_alias=True) for i in items])
