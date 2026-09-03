"""评论 Service：项目级评论，仅发布本人可删，归档禁止增删"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Comment, SysUser
from app.schemas import CommentAddRequest, CommentItem
from app.services import log_service, message_service, project_service
from app.utils.exceptions import BusinessException


def comment_list(db: Session, project_id: int) -> list[CommentItem]:
    """项目评论列表，按时间倒序，不分页"""
    stmt = (
        select(Comment, SysUser.real_name.label("create_user_name"))
        .outerjoin(SysUser, SysUser.id == Comment.create_user_id)
        .where(Comment.project_id == project_id)
        .order_by(Comment.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        CommentItem(
            id=c.id, project_id=c.project_id, content=c.content,
            create_user_id=c.create_user_id, create_user_name=name or "已删除用户", create_time=c.create_time,
        )
        for c, name in rows
    ]


def comment_add(db: Session, operator: dict, req: CommentAddRequest) -> int:
    project = project_service.get_project_or_400(db, req.project_id)
    project_service.check_project_archived(project)

    comment = Comment(project_id=project.id, content=req.content, create_user_id=operator["id"])
    db.add(comment)
    db.flush()
    log_service.add_log(db, operator["id"], "comment_create", f"发表评论：{req.content[:50]}", related_project_id=project.id)
    message_service.push(
        db, project, operator["id"], operator["real_name"], "comment_create", comment_content=req.content
    )
    db.commit()
    return comment.id


def comment_delete(db: Session, operator: dict, comment_id: int) -> None:
    """仅发布本人可删（403）；归档项目禁止删除"""
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise BusinessException(400, "评论不存在")

    project = project_service.get_project_or_400(db, comment.project_id)
    project_service.check_project_archived(project)

    if comment.create_user_id != operator["id"]:
        raise BusinessException(403, "无权删除他人评论")

    preview = comment.content[:50]
    db.delete(comment)
    log_service.add_log(db, operator["id"], "comment_delete", f"删除评论：{preview}", related_project_id=comment.project_id)
    db.commit()
