"""操作审计日志 Service：日志只写不改不删；全局分页查询 + 项目内查询"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SysOperationLog, SysUser
from app.schemas import LogGlobalQuery, LogItem, PageResult


def add_log(
    db: Session,
    oper_user_id: int,
    oper_type: str,
    oper_desc: str,
    related_project_id: int | None = None,
) -> None:
    """写入一条操作日志（不 commit，由调用方事务统一提交）"""
    db.add(
        SysOperationLog(
            oper_user_id=oper_user_id,
            oper_type=oper_type,
            oper_desc=oper_desc,
            related_project_id=related_project_id,
        )
    )


def global_list(db: Session, query: LogGlobalQuery) -> PageResult[LogItem]:
    """全局审计日志分页（管理员/行政/设计总监），支持操作人/时间范围/类型筛选"""
    stmt = (
        select(SysOperationLog, SysUser.real_name.label("oper_user_name"))
        .outerjoin(SysUser, SysUser.id == SysOperationLog.oper_user_id)
        .order_by(SysOperationLog.id.desc())
    )
    count_stmt = select(SysOperationLog.id)
    if query.oper_user_id:
        stmt = stmt.where(SysOperationLog.oper_user_id == query.oper_user_id)
        count_stmt = count_stmt.where(SysOperationLog.oper_user_id == query.oper_user_id)
    if query.oper_type:
        stmt = stmt.where(SysOperationLog.oper_type == query.oper_type)
        count_stmt = count_stmt.where(SysOperationLog.oper_type == query.oper_type)
    if query.start_time:
        stmt = stmt.where(SysOperationLog.oper_time >= query.start_time)
        count_stmt = count_stmt.where(SysOperationLog.oper_time >= query.start_time)
    if query.end_time:
        stmt = stmt.where(SysOperationLog.oper_time <= query.end_time)
        count_stmt = count_stmt.where(SysOperationLog.oper_time <= query.end_time)

    total = len(db.execute(count_stmt).scalars().all())
    rows = db.execute(stmt.offset((query.page_num - 1) * query.page_size).limit(query.page_size)).all()
    items = [
        LogItem(
            id=log.id,
            oper_user_id=log.oper_user_id,
            oper_user_name=oper_user_name or "已删除用户",
            oper_time=log.oper_time,
            oper_type=log.oper_type,
            oper_desc=log.oper_desc,
            related_project_id=log.related_project_id,
        )
        for log, oper_user_name in rows
    ]
    return PageResult[LogItem](items=items, total=total, page_num=query.page_num, page_size=query.page_size)


def project_log(db: Session, project_id: int) -> list[LogItem]:
    """项目内操作记录（全部角色，按时间倒序，不分页）"""
    stmt = (
        select(SysOperationLog, SysUser.real_name.label("oper_user_name"))
        .outerjoin(SysUser, SysUser.id == SysOperationLog.oper_user_id)
        .where(SysOperationLog.related_project_id == project_id)
        .order_by(SysOperationLog.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        LogItem(
            id=log.id,
            oper_user_id=log.oper_user_id,
            oper_user_name=oper_user_name or "已删除用户",
            oper_time=log.oper_time,
            oper_type=log.oper_type,
            oper_desc=log.oper_desc,
            related_project_id=log.related_project_id,
        )
        for log, oper_user_name in rows
    ]
