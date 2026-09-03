"""自定义角色 Service（仅管理员）：列表 / 添加 / 删除（占用拦截）"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SysRole, SysUser
from app.schemas import RoleAddRequest, RoleItem
from app.services import log_service
from app.utils.exceptions import BusinessException

# 内置角色：不可作为自定义角色名创建、删除
BUILTIN_ROLES = ("管理员", "行政", "设计总监", "设计师")


def _role_user_count(db: Session, role_name: str) -> int:
    return db.execute(
        select(func.count(SysUser.id)).where(SysUser.role == role_name)
    ).scalar_one()


def list_roles(db: Session) -> list[RoleItem]:
    """自定义角色列表（含每个角色当前使用人数）"""
    roles = db.execute(select(SysRole).order_by(SysRole.id)).scalars().all()
    return [
        RoleItem(
            id=r.id, role_name=r.role_name,
            user_count=_role_user_count(db, r.role_name),
            create_time=r.create_time,
        )
        for r in roles
    ]


def add_role(db: Session, operator_id: int, req: RoleAddRequest) -> int:
    name = req.role_name.strip()
    if not name:
        raise BusinessException(400, "角色名称不能为空")
    if name in BUILTIN_ROLES:
        raise BusinessException(400, f"「{name}」是内置角色，无需重复创建")
    exists = db.execute(select(SysRole.id).where(SysRole.role_name == name)).scalars().first()
    if exists is not None:
        raise BusinessException(400, f"角色「{name}」已存在")
    role = SysRole(role_name=name)
    db.add(role)
    db.flush()
    log_service.add_log(db, operator_id, "role_add", f"新增自定义角色：{name}")
    db.commit()
    return role.id


def delete_role(db: Session, operator_id: int, role_id: int) -> None:
    role = db.get(SysRole, role_id)
    if role is None:
        raise BusinessException(400, "角色不存在")
    if role.role_name in BUILTIN_ROLES:
        raise BusinessException(400, "内置角色禁止删除")
    used = _role_user_count(db, role.role_name)
    if used > 0:
        raise BusinessException(400, f"角色「{role.role_name}」正在被 {used} 个用户使用，请先修改这些用户的角色再删除")
    name = role.role_name
    db.delete(role)
    log_service.add_log(db, operator_id, "role_delete", f"删除自定义角色：{name}")
    db.commit()


def is_valid_role(db: Session, role_name: str) -> bool:
    """校验角色名是否可用：内置角色 或 已存在的自定义角色"""
    if role_name in BUILTIN_ROLES:
        return True
    exists = db.execute(select(SysRole.id).where(SysRole.role_name == role_name)).scalars().first()
    return exists is not None
