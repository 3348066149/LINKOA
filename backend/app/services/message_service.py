"""消息中心 Service：自动通知 + 本人消息查询

推送范围红线：项目创建人 + 项目所有关联设计师，**自动排除操作人自己**。

消息降噪（V1.4.21）：消息中心只承载**关键事件**，常规操作不再产生消息通知 ——
  - 关键（生成消息）：comment_create 新评论 / customer_review 客户审核提交 / evaluation_create 客户评价
  - 常规（不生成消息）：node_create 节点新增 / node_update 节点修改 / node_delete 节点删除 / form_update 表单填写
常规操作并非不记录：`sys_operation_log` 审计日志全量留痕（谁在何时改了什么），
需要追溯时到「系统管理 → 日志」查，不必刷屏消息中心。
调用方（node_service 等）的 push() 调用**保留不动**，策略只在本文件收敛一处，便于日后调整。
"""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Message, Project, ProjectDesignerRel, SysUser
from app.schemas import MessageItem, MessageListQuery, PageResult
from app.utils.exceptions import BusinessException

# 关键通知白名单：只有这些类型会真正落库 + 默认展示 + 计入未读数
NOTIFY_TYPES: tuple[str, ...] = ("comment_create", "customer_review", "evaluation_create")
# 常规操作类型：保留识别能力（含历史数据），默认不展示、可开关查看
ROUTINE_TYPES: tuple[str, ...] = ("node_create", "node_update", "node_delete", "form_update")


def _recipients(db: Session, project: Project, operator_id: int) -> set[int]:
    """计算推送范围：创建人 + 关联设计师 - 操作人；过滤已删除用户避免孤儿消息（V1.3）"""
    ids = {project.create_user_id}
    rel_user_ids = db.execute(
        select(ProjectDesignerRel.user_id).where(ProjectDesignerRel.project_id == project.id)
    ).scalars().all()
    ids.update(rel_user_ids)
    ids.discard(operator_id)
    if not ids:
        return ids
    existing = set(db.execute(select(SysUser.id).where(SysUser.id.in_(ids))).scalars().all())
    return ids & existing


def push(
    db: Session,
    project: Project,
    operator_id: int,
    operator_name: str,
    msg_type: str,
    node_title: str | None = None,
    comment_content: str | None = None,
) -> None:
    """按模板批量写入消息（不 commit，由调用方事务统一提交）

    V1.4.21 降噪：常规操作（节点增删改 / 表单填写）在此直接返回、不再生成消息；
    文案模板保留，日后若要重新启用，把类型加回 NOTIFY_TYPES 即可。
    """
    if msg_type in ROUTINE_TYPES:
        return
    pname = project.project_name
    if msg_type == "node_create":
        content = f"{operator_name} 在项目「{pname}」中新增了节点：{node_title}"
    elif msg_type == "node_update":
        content = f"{operator_name} 在项目「{pname}」中修改了节点：{node_title}"
    elif msg_type == "node_delete":
        content = f"{operator_name} 在项目「{pname}」中删除了节点：{node_title}"
    elif msg_type == "form_update":
        content = f"{operator_name} 在项目「{pname}」的「{node_title}」中填写了表单"
    elif msg_type == "comment_create":
        preview = (comment_content or "")[:20]
        content = f"{operator_name} 在项目「{pname}」中发表了评论：{preview}..."
    elif msg_type == "customer_review":
        content = f"{operator_name} 在项目「{pname}」的「{node_title}」完成审核：{comment_content}"
    else:
        raise BusinessException(400, f"未知消息类型: {msg_type}")

    for uid in _recipients(db, project, operator_id):
        db.add(
            Message(
                receive_user_id=uid,
                project_id=project.id,
                msg_type=msg_type,
                msg_content=content,
                is_read=0,
            )
        )


def push_evaluation_create(db: Session, project: Project) -> None:
    """客户提交评价后通知：创建人 + 关联设计师 + 全部 role=管理员（不 commit，随调用方事务提交）

    操作人为客户，不在「创建人/设计师/管理员」集合内，故无需显式排除操作人。
    """
    ids = _recipients(db, project, operator_id=-1)  # -1 不会命中任何用户，等价于不排除操作人
    admin_ids = db.execute(select(SysUser.id).where(SysUser.role == "管理员")).scalars().all()
    ids.update(admin_ids)
    if not ids:
        return
    existing = set(db.execute(select(SysUser.id).where(SysUser.id.in_(ids))).scalars().all())
    content = f"客户已对项目「{project.project_name}」提交满意度评价"
    for uid in ids & existing:
        db.add(
            Message(
                receive_user_id=uid,
                project_id=project.id,
                msg_type="evaluation_create",
                msg_content=content,
                is_read=0,
            )
        )


def my_list(db: Session, user_id: int, query: MessageListQuery) -> PageResult[MessageItem]:
    """本人消息分页，支持已读/未读筛选

    V1.4.21：默认只返回关键通知；`includeRoutine=true` 时才把常规操作的历史消息一并带出。
    """
    conds = [Message.receive_user_id == user_id]
    if not query.include_routine:
        conds.append(Message.msg_type.in_(NOTIFY_TYPES))
    if query.is_read is not None:
        conds.append(Message.is_read == query.is_read)

    total = db.execute(select(func.count()).select_from(Message).where(*conds)).scalar_one()
    rows = db.execute(
        select(Message).where(*conds).order_by(Message.id.desc())
        .offset((query.page_num - 1) * query.page_size).limit(query.page_size)
    ).scalars().all()
    items = [
        MessageItem(
            id=m.id,
            project_id=m.project_id,
            msg_type=m.msg_type,
            msg_content=m.msg_content,
            is_read=m.is_read,
            create_time=m.create_time,
        )
        for m in rows
    ]
    return PageResult[MessageItem](items=items, total=total, page_num=query.page_num, page_size=query.page_size)


def unread_count(db: Session, user_id: int) -> int:
    """未读数只统计关键通知 —— 与消息中心的默认展示保持一致，
    否则铃铛出现「有红点但列表是空的」（V1.4.21）。"""
    return db.execute(
        select(func.count()).select_from(Message).where(
            Message.receive_user_id == user_id,
            Message.is_read == 0,
            Message.msg_type.in_(NOTIFY_TYPES),
        )
    ).scalar_one()


def mark_read(db: Session, user_id: int, message_id: int) -> None:
    """标为已读，仅本人消息可操作"""
    msg = db.get(Message, message_id)
    if msg is None:
        raise BusinessException(400, "消息不存在")
    if msg.receive_user_id != user_id:
        raise BusinessException(403, "无权操作他人消息")
    msg.is_read = 1
    db.commit()


def mark_read_all(
    db: Session, user_id: int, project_id: int | None = None, include_routine: bool = False
) -> int:
    """一键全部已读：本人未读消息，返回标记数量

    V1.4.21：
    - 传 project_id 时只标记该项目的消息（消息中心按项目分组后的「本项目全部已读」）
    - include_routine=False（默认）时不动常规操作消息，与消息中心默认展示口径一致，
      避免出现「页面只看到 11 条、提示却说标记了 81 条」
    """
    conds = [Message.receive_user_id == user_id, Message.is_read == 0]
    if project_id is not None:
        conds.append(Message.project_id == project_id)
    if not include_routine:
        conds.append(Message.msg_type.in_(NOTIFY_TYPES))
    result = db.execute(update(Message).where(*conds).values(is_read=1))
    db.commit()
    return result.rowcount or 0
