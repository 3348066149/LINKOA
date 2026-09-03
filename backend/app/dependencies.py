"""依赖注入：get_db()、get_current_user()"""
from typing import Generator

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.utils.exceptions import BusinessException
from app.utils.jwt import decode_token


def get_db() -> Generator[Session, None, None]:
    """提供数据库会话：异常时自动回滚，请求结束自动关闭"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    """解析 Authorization: Bearer <token>，返回当前登录用户

    返回 dict：{id, username, real_name, role, is_enable}
    校验失败抛 401；账号被停用抛 400。
    """
    if not authorization.startswith("Bearer "):
        raise BusinessException(401, "未登录或登录状态无效")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise BusinessException(401, "未登录或登录状态无效")

    user_id = decode_token(token)

    row = db.execute(
        text("SELECT id, username, real_name, role, dept_id, customer_id, category_id, is_enable FROM sys_user WHERE id = :uid"),
        {"uid": user_id},
    ).mappings().first()
    if row is None:
        raise BusinessException(401, "未登录或登录状态无效")
    if row["is_enable"] != 1:
        raise BusinessException(400, "账号已停用，请联系管理员")
    return dict(row)


def require_roles(*roles: str):
    """角色校验依赖工厂：当前用户角色不在允许列表内时抛 403

    用法：current_user: dict = Depends(require_roles("管理员", "行政"))
    """

    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise BusinessException(403, "无权限执行该操作")
        return current_user

    return checker


def require_not_customer():
    """客户账号只读拦截：客户只能查看进度，禁止任何写操作（节点/表单/评论/附件）

    与 require_roles 不同：不限定具体角色，仅排除「客户」，因此自定义部门新角色自动放行。
    """

    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] == "客户":
            raise BusinessException(403, "客户账号为只读权限，禁止修改")
        return current_user

    return checker
