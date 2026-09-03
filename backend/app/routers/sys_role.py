"""自定义角色路由（V1.3 新增，仅管理员）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import RoleAddRequest, RoleDeleteRequest
from app.services import role_service
from app.utils.exceptions import ok

# 路由级统一鉴权：仅管理员
router = APIRouter(dependencies=[Depends(require_roles("管理员"))])


@router.get("/list")
def list_roles(db: Session = Depends(get_db)):
    items = role_service.list_roles(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/add")
def add_role(
    req: RoleAddRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_id = role_service.add_role(db, current_user["id"], req)
    return ok({"roleId": role_id})


@router.post("/delete")
def delete_role(
    req: RoleDeleteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自定义角色：有用户占用时拦截（提示先改用户角色）"""
    role_service.delete_role(db, current_user["id"], req.id)
    return ok(None)
