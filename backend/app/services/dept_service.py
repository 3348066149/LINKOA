"""部门 Service（仅管理员）：列表（含人数）/ 添加 / 重命名 / 删除（占用拦截）

V1.4 起部门仅做人员组织分组，不携带权限模板。权限由用户自身的 role 决定。
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SysDept, SysUser
from app.schemas import DeptAddRequest, DeptItem, DeptUpdateRequest
from app.services import log_service
from app.utils.exceptions import BusinessException

# 系统预置的内置部门（启动幂等初始化，V1.4 起不再绑定权限模板）
DEFAULT_INTERNAL_DEPTS = ["研发部", "设计部", "市场部"]


def list_depts(db: Session) -> list[DeptItem]:
    depts = db.execute(select(SysDept).order_by(SysDept.id)).scalars().all()
    return [
        DeptItem(
            id=d.id, dept_name=d.dept_name, dept_type=d.dept_type,
            user_count=_dept_user_count(db, d.id),
            create_time=d.create_time,
        )
        for d in depts
    ]


def _dept_user_count(db: Session, dept_id: int) -> int:
    return db.execute(
        select(func.count(SysUser.id)).where(SysUser.dept_id == dept_id)
    ).scalar_one()


def add_dept(db: Session, operator_id: int, req: DeptAddRequest) -> int:
    name = req.dept_name.strip()
    if not name:
        raise BusinessException(400, "部门名称不能为空")
    exists = db.execute(select(SysDept.id).where(SysDept.dept_name == name)).scalars().first()
    if exists is not None:
        raise BusinessException(400, f"部门「{name}」已存在")
    dept = SysDept(dept_name=name, dept_type=req.dept_type)
    db.add(dept)
    db.flush()
    log_service.add_log(db, operator_id, "dept_add", f"新增部门：{name}")
    db.commit()
    return dept.id


def update_dept(db: Session, operator_id: int, req: DeptUpdateRequest) -> None:
    dept = db.get(SysDept, req.id)
    if dept is None:
        raise BusinessException(400, "部门不存在")
    name = req.dept_name.strip()
    if not name:
        raise BusinessException(400, "部门名称不能为空")
    dup = db.execute(
        select(SysDept.id).where(SysDept.dept_name == name, SysDept.id != dept.id)
    ).scalars().first()
    if dup is not None:
        raise BusinessException(400, f"部门「{name}」已存在")
    dept.dept_name = name
    log_service.add_log(db, operator_id, "dept_update", f"修改部门：{name}")
    db.commit()


def delete_dept(db: Session, operator_id: int, dept_id: int) -> None:
    dept = db.get(SysDept, dept_id)
    if dept is None:
        raise BusinessException(400, "部门不存在")
    used = _dept_user_count(db, dept_id)
    if used > 0:
        raise BusinessException(400, f"部门「{dept.dept_name}」下还有 {used} 个用户，请先调整这些用户的部门再删除")
    name = dept.dept_name
    db.delete(dept)
    log_service.add_log(db, operator_id, "dept_delete", f"删除部门：{name}")
    db.commit()


def init_default_depts(db: Session) -> None:
    """启动幂等初始化内置部门（研发部/设计部/市场部，不带权限模板）"""
    for name in DEFAULT_INTERNAL_DEPTS:
        exists = db.execute(select(SysDept.id).where(SysDept.dept_name == name)).scalars().first()
        if exists is None:
            db.add(SysDept(dept_name=name, dept_type="internal"))
    db.commit()


def migrate_dept_role_to_user(db: Session) -> None:
    """V1.4 存量迁移（幂等）：老数据部门绑定权限 → 权限赋给用户角色

    1. 遍历非客户账号用户，若其部门还带着权限模板（role），将该模板写入用户 role。
    2. 清空所有部门的 role 字段（部门不再携带权限）。
    仅当部门 role 非空时执行，迁移完成后 role 恒为 NULL，重复执行无副作用。
    """
    depts = {d.id: d for d in db.execute(select(SysDept)).scalars().all()}
    dirty = False
    for u in db.execute(select(SysUser)).scalars().all():
        if u.role == "客户" or u.dept_id is None:
            continue
        d = depts.get(u.dept_id)
        if d is not None and d.role:
            u.role = d.role
            dirty = True
    for d in depts.values():
        if d.role:
            d.role = None
            dirty = True
    if dirty:
        db.commit()


LEGACY_ROLES = ("设计师", "设计总监", "行政")


def migrate_legacy_roles(db: Session) -> None:
    """V1.4.2 角色简化迁移（幂等）：设计师/设计总监/行政 → 普通

    客户账号（role=客户）保持不变；初始管理员 admin 强制保持「管理员」，防止误降级。
    """
    changed = 0
    for u in db.execute(select(SysUser)).scalars().all():
        if u.username == "admin" and u.role != "管理员":
            u.role = "管理员"
            changed += 1
            continue
        if u.role in LEGACY_ROLES:
            u.role = "普通"
            changed += 1
    if changed:
        log_service.add_log(db, 0, "role_migrate", f"角色简化迁移：{changed} 个账号角色调整")
        db.commit()
