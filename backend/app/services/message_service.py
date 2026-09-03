"""消息中心 Service：自动通知 + 本人消息查询

推送范围红线：项目创建人 + 项目所有关联设计师，**自动排除操作人自己**。
触发事件：node_create / node_update / node_delete / form_update / comment_create。
"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Message, Project, ProjectDesignerRel, SysUser
from app.schemas import MessageItem, MessageListQuery, PageResult
from app.utils.exceptions import BusinessException


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
    """按模板批量写入消息（不 commit，由调用方事务统一提交）"""
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
    """本人消息分页，支持已读/未读筛选"""
    stmt = select(Message).where(Message.receive_user_id == user_id).order_by(Message.id.desc())
    if query.is_read is not None:
        stmt = stmt.where(Message.is_read == query.is_read)

    total = len(db.execute(select(Message.id).where(Message.receive_user_id == user_id)).scalars().all())
    if query.is_read is not None:
        total = len(
            db.execute(
                select(Message.id).where(Message.receive_user_id == user_id, Message.is_read == query.is_read)
            ).scalars().all()
        )
    rows = db.execute(stmt.offset((query.page_num - 1) * query.page_size).limit(query.page_size)).scalars().all()
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
    return len(
        db.execute(
            select(Message.id).where(Message.receive_user_id == user_id, Message.is_read == 0)
        ).scalars().all()
    )


def mark_read(db: Session, user_id: int, message_id: int) -> None:
    """标为已读，仅本人消息可操作"""
    msg = db.get(Message, message_id)
    if msg is None:
        raise BusinessException(400, "消息不存在")
    if msg.receive_user_id != user_id:
        raise BusinessException(403, "无权操作他人消息")
    msg.is_read = 1
    db.commit()


def mark_read_all(db: Session, user_id: int) -> int:
    """一键全部已读：本人全部未读消息，返回标记数量"""
    result = db.execute(
        update(Message)
        .where(Message.receive_user_id == user_id, Message.is_read == 0)
        .values(is_read=1)
    )
    db.commit()
    return result.rowcount or 0
