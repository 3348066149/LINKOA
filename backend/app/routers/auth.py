"""登录模块路由（Api.md 第 1 章）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.schemas import LoginRequest, UpdateMyPwdRequest
from app.services import user_service
from app.utils.exceptions import ok

router = APIRouter()


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    return ok(user_service.login(db, req).model_dump(by_alias=True))


@router.post("/user/updateMyPwd")
def update_my_pwd(
    req: UpdateMyPwdRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.update_my_pwd(db, current_user, req)
    return ok(None)
