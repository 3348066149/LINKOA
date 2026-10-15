"""用户与登录 Service"""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CustomerCategory, SysDept, SysUser
from app.schemas import (
    LoginData,
    LoginRequest,
    ResetPwdRequest,
    SetEnableRequest,
    SysUserCreateRequest,
    SysUserItem,
    SysUserUpdateRequest,
    UpdateMyPwdRequest,
    UserInfo,
)
from app.services import log_service
from app.utils.exceptions import BusinessException
from app.utils.jwt import create_token
from app.utils.password import hash_password, is_hashed, verify_password


def _user_info(db: Session, user: SysUser) -> UserInfo:
    """组装登录用户信息：内部员工带部门名，客户账号直接带所属公司名（V1.4.15 起不溯源对接人）"""
    dept_name = None
    company_name = None
    if user.dept_id:
        dept = db.get(SysDept, user.dept_id)
        dept_name = dept.dept_name if dept else None
    if user.category_id:
        cat = db.get(CustomerCategory, user.category_id)
        company_name = cat.category_name if cat else None
    return UserInfo(
        id=user.id, username=user.username, real_name=user.real_name, role=user.role,
        dept_id=user.dept_id, dept_name=dept_name,
        customer_id=user.customer_id, customer_name=None,
        category_id=user.category_id, company_name=company_name,
    )


def _locked_remain_minutes(user: SysUser) -> int:
    """返回账号剩余锁定分钟数（0 表示未锁定或已到期）"""
    if user.locked_until is None:
        return 0
    remain = (user.locked_until - datetime.now()).total_seconds()
    if remain <= 0:
        return 0
    return max(1, int(remain // 60) + (1 if remain % 60 else 0))


def login(db: Session, req: LoginRequest) -> LoginData:
    """登录（V1.4.6 防暴力破解）

    规则：账号存在且密码错误时累加失败次数，达到 LOGIN_MAX_FAIL 次锁定
    LOGIN_LOCK_MINUTES 分钟；登录成功清零计数与锁定；锁定期间不再比较密码。
    账号不存在时不累加（无从累加），仅返回通用错误提示，避免账号枚举。
    """
    user = db.execute(select(SysUser).where(SysUser.username == req.username)).scalars().first()

    if user is not None:
        # 1) 锁定检查（到期自动解锁）
        remain = _locked_remain_minutes(user)
        if remain > 0:
            raise BusinessException(
                400, f"账号已锁定，请 {remain} 分钟后重试，或联系管理员解锁"
            )
        if user.locked_until is not None:
            # 锁定已到期，清理锁定状态
            user.locked_until = None
            user.login_fail_count = 0

        # 2) 密码校验（bcrypt；老明文密码首次登录自动升级成哈希）
        if not verify_password(req.password, user.password):
            user.login_fail_count = (user.login_fail_count or 0) + 1
            left = settings.LOGIN_MAX_FAIL - user.login_fail_count
            if left <= 0:
                user.locked_until = datetime.now() + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
                db.commit()
                log_service.add_log(
                    db, user.id, "user_login_lock",
                    f"{user.username} 连续登录失败 {settings.LOGIN_MAX_FAIL} 次，账号锁定 "
                    f"{settings.LOGIN_LOCK_MINUTES} 分钟",
                )
                db.commit()
                raise BusinessException(
                    400,
                    f"密码错误次数过多，账号已锁定 {settings.LOGIN_LOCK_MINUTES} 分钟，"
                    f"或联系管理员解锁",
                )
            db.commit()
            raise BusinessException(400, f"账号或密码错误，还可尝试 {left} 次")

        # 老明文密码升级成 bcrypt 哈希（一次性平滑迁移）
        if not is_hashed(user.password):
            user.password = hash_password(req.password)

        # 3) 密码正确：检查启用状态
        if user.is_enable != 1:
            raise BusinessException(400, "账号已停用，请联系管理员")

        # 4) 成功：清零失败计数与锁定
        user.login_fail_count = 0
        user.locked_until = None
        token = create_token(user.id, user.token_version or 1)
        log_service.add_log(db, user.id, "user_login", f"{user.real_name} 登录系统")
        db.commit()
        return LoginData(token=token, user_info=_user_info(db, user))

    raise BusinessException(400, "账号或密码错误")


def unlock_user(db: Session, operator_id: int, user_id: int) -> None:
    """管理员手动解锁账号（清零失败次数与锁定时间）"""
    user = db.get(SysUser, user_id)
    if user is None:
        raise BusinessException(400, "用户不存在")
    if not user.locked_until and not user.login_fail_count:
        raise BusinessException(400, "该账号未被锁定")
    user.login_fail_count = 0
    user.locked_until = None
    log_service.add_log(db, operator_id, "user_unlock", f"管理员解锁账号 {user.username}")
    db.commit()


def update_my_pwd(db: Session, current_user: dict, req: UpdateMyPwdRequest) -> None:
    user = db.get(SysUser, current_user["id"])
    if user is None or not verify_password(req.old_password, user.password):
        raise BusinessException(400, "原密码错误")
    user.password = hash_password(req.new_password)
    # 改密码后旧 token 立即失效
    user.token_version = (user.token_version or 1) + 1
    db.commit()


def list_users(db: Session) -> list[SysUserItem]:
    """全部用户（密码不再返回前端，仅管理员可见）"""
    users = db.execute(select(SysUser).order_by(SysUser.id)).scalars().all()
    dept_map = {d.id: d.dept_name for d in db.execute(select(SysDept)).scalars().all()}
    cat_map = {c.id: c.category_name for c in db.execute(select(CustomerCategory)).scalars().all()}
    return [
        SysUserItem(
            id=u.id, username=u.username,
            real_name=u.real_name, role=u.role,
            dept_id=u.dept_id, dept_name=dept_map.get(u.dept_id) if u.dept_id else None,
            customer_id=u.customer_id,
            customer_name=None,
            category_id=u.category_id,
            category_name=cat_map.get(u.category_id) if u.category_id else None,
            is_enable=u.is_enable,
            is_locked=_locked_remain_minutes(u) > 0,
        )
        for u in users
    ]


def create_user(db: Session, operator_id: int, req: SysUserCreateRequest) -> int:
    """V1.4.15：客户账号绑定客户单位（公司）
    - 内部员工：dept_id + role（普通/管理员 二选一）
    - 客户账号：category_id（role 固定为客户，只读）
    两者互斥，至少传一个。
    """
    if (req.dept_id is None) == (req.category_id is None):
        raise BusinessException(400, "请选择部门（内部员工）或客户单位（客户账号），二选一")
    exists = db.execute(select(SysUser.id).where(SysUser.username == req.username)).scalars().first()
    if exists is not None:
        raise BusinessException(400, "登录账号已存在")

    if req.dept_id is not None:
        dept = db.get(SysDept, req.dept_id)
        if dept is None:
            raise BusinessException(400, "部门不存在")
        if dept.dept_type != "internal":
            raise BusinessException(400, "客户部门下只能创建客户账号")
        if not req.role:
            raise BusinessException(400, "请为账号分配角色（普通/管理员）")
        user = SysUser(
            username=req.username, password=hash_password(req.password),
            real_name=req.real_name, role=req.role, dept_id=req.dept_id, is_enable=1,
        )
        dept_label = f"{dept.dept_name}/{req.role}"
    else:
        cat = db.get(CustomerCategory, req.category_id)
        if cat is None:
            raise BusinessException(400, "客户单位不存在")
        user = SysUser(
            username=req.username, password=hash_password(req.password),
            real_name=req.real_name, role="客户", category_id=req.category_id, is_enable=1,
        )
        dept_label = cat.category_name

    db.add(user)
    db.flush()
    log_service.add_log(db, operator_id, "user_create", f"创建用户：{user.real_name}（{req.username}，{dept_label}）")
    db.commit()
    return user.id


def update_user(db: Session, operator_id: int, req: SysUserUpdateRequest) -> None:
    """编辑用户（V1.4）：改所属部门 + 角色 + 姓名；账号不可改、密码走重置。
    客户账号不可编辑（角色/部门固定），仅允许改姓名。
    """
    user = db.get(SysUser, req.id)
    if user is None:
        raise BusinessException(400, "用户不存在")
    if user.role == "客户":
        if req.dept_id is not None or req.role is not None:
            raise BusinessException(400, "客户账号不参与部门与角色分配")
        user.real_name = req.real_name
        log_service.add_log(db, operator_id, "user_update", f"修改客户账号姓名：{req.real_name}")
        db.commit()
        return
    if req.dept_id is None:
        raise BusinessException(400, "请选择所属部门")
    if not req.role:
        raise BusinessException(400, "请为账号分配角色（普通/管理员）")
    dept = db.get(SysDept, req.dept_id)
    if dept is None:
        raise BusinessException(400, "部门不存在")
    old_dept = db.get(SysDept, user.dept_id).dept_name if user.dept_id else None
    old_role = user.role
    user.real_name = req.real_name
    user.dept_id = req.dept_id
    user.role = req.role
    log_service.add_log(
        db, operator_id, "user_update",
        f"修改用户：{user.real_name}（部门 {old_dept or '无'}→{dept.dept_name}，角色 {old_role}→{req.role}）",
    )
    db.commit()


def reset_pwd(db: Session, operator_id: int, req: ResetPwdRequest) -> None:
    user = db.get(SysUser, req.user_id)
    if user is None:
        raise BusinessException(400, "用户不存在")
    user.password = hash_password(req.new_password)
    # 重置密码后旧 token 立即失效
    user.token_version = (user.token_version or 1) + 1
    db.commit()


def set_enable(db: Session, operator_id: int, req: SetEnableRequest) -> None:
    user = db.get(SysUser, req.user_id)
    if user is None:
        raise BusinessException(400, "用户不存在")
    if user.id == operator_id:
        raise BusinessException(400, "不能停用自己的账号")
    user.is_enable = req.is_enable
    oper_type = "user_enable" if req.is_enable == 1 else "user_disable"
    action = "启用" if req.is_enable == 1 else "停用"
    log_service.add_log(db, operator_id, oper_type, f"{action}账号：{user.real_name}（{user.username}）")
    db.commit()


def delete_user(db: Session, operator_id: int, user_id: int) -> None:
    """物理删除用户（V1.3 新增，覆盖 PRD 原"仅启停"约定）

    保护规则：不能删除自己；不能删除初始管理员 admin。
    历史项目/日志中的关联保留原 user_id，展示层姓名为空时显示"已删除用户"。
    """
    user = db.get(SysUser, user_id)
    if user is None:
        raise BusinessException(400, "用户不存在")
    if user.id == operator_id:
        raise BusinessException(400, "不能删除自己的账号")
    if user.username == "admin":
        raise BusinessException(400, "初始管理员账号禁止删除")
    name = f"{user.real_name}（{user.username}）"
    db.delete(user)
    log_service.add_log(db, operator_id, "user_delete", f"删除用户：{name}")
    db.commit()
