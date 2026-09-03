"""用户管理路由（Api.md 第 2 章，仅管理员）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import (
    DeleteUserRequest,
    ResetPwdRequest,
    SetEnableRequest,
    SysUserCreateRequest,
    SysUserUpdateRequest,
    UnlockUserRequest,
)
from app.services import user_service
from app.utils.exceptions import ok

# 路由级统一鉴权：仅管理员
router = APIRouter(dependencies=[Depends(require_roles("管理员"))])


@router.get("/list")
def list_users(db: Session = Depends(get_db)):
    items = user_service.list_users(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/create")
def create_user(
    req: SysUserCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user_service.create_user(db, current_user["id"], req)
    return ok({"userId": user_id})


@router.post("/update")
def update_user(
    req: SysUserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑用户（V1.4）：改部门/角色/姓名；客户账号仅能改姓名"""
    user_service.update_user(db, current_user["id"], req)
    return ok(None)


@router.post("/resetPwd")
def reset_pwd(
    req: ResetPwdRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.reset_pwd(db, current_user["id"], req)
    return ok(None)


@router.post("/setEnable")
def set_enable(
    req: SetEnableRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.set_enable(db, current_user["id"], req)
    return ok(None)


@router.post("/unlock")
def unlock_user(
    req: UnlockUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """手动解锁账号（V1.4.6）：清零登录失败次数与锁定时间，用于误锁后即时恢复"""
    user_service.unlock_user(db, current_user["id"], req.user_id)
    return ok(None)


@router.post("/delete")
def delete_user(
    req: DeleteUserRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除用户（V1.3）：不能删自己、不能删初始 admin"""
    user_service.delete_user(db, current_user["id"], req.user_id)
    return ok(None)
