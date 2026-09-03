"""AI 知识库构建（检索方式改造）：结构化文本知识库 + 全量注入。

把每个项目渲染成一条完整文本，实时读库拼装成知识库全文，供 AI 助手每次提问
无条件注入到 system prompt。数据隔离在 SQL 层完成：

- 内部员工（role != "客户"）：注入系统内全部项目（进行中 + 已归档）；
- 客户（role == "客户"）：仅注入 Project.category_id == current_user.category_id
  的项目；客户 category_id 缺失 → 返回空知识库。

不含进度百分比、当前节点、交付紧迫度/逾期天数等字段（相关实现已随改造删除）。
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    CustomerCategory,
    Project,
    ProjectContactRel,
    ProjectDesignerRel,
    SysUser,
)


def _scope_category_id(current_user: dict) -> int | None:
    """客户账号返回其 category_id（用于 WHERE 隔离）；内部员工返回 None（全量）。"""
    if current_user.get("role") == "客户":
        return current_user.get("category_id")
    return None


def _format_date(value) -> str:
    """datetime → 'YYYY-MM-DD'；None/空 → '未设置'。"""
    if not value:
        return "未设置"
    return value.strftime("%Y-%m-%d")


def _status_label(status: str | None) -> str:
    """'进行中'→'进行中'；'已归档'→'已结项'；其他/空→原值或'未知'。"""
    if status == "已归档":
        return "已结项"
    if status == "进行中":
        return "进行中"
    return status or "未知"


def _join_names(names: list[str], fallback: str) -> str:
    """非空列表用 '、' 拼接，空列表返回 fallback。"""
    return "、".join(names) if names else fallback


def _fetch_projects(db: Session, category_id: int | None) -> list[tuple[Project, str | None, str | None]]:
    """主查询：返回 (Project, 客户单位名, 首位对接人名)，最新在前。

    - 不按 project_status 过滤：进行中 + 已归档全量入知识库；
    - 客户隔离在 SQL 层完成（WHERE category_id = :cat_id），不靠 Python 过滤。
    """
    stmt = (
        select(Project, CustomerCategory.category_name, Customer.customer_name)
        .outerjoin(CustomerCategory, CustomerCategory.id == Project.category_id)
        .outerjoin(Customer, Customer.id == Project.customer_id)
    )
    if category_id is not None:
        stmt = stmt.where(Project.category_id == category_id)
    stmt = stmt.order_by(Project.create_time.desc(), Project.id.desc())
    return db.execute(stmt).all()


def _fetch_contacts(db: Session, project_ids: list[int]) -> dict[int, list[str]]:
    """批量取对接人（project_contact_rel → customer.customer_name），避免 N+1。"""
    if not project_ids:
        return {}
    rows = db.execute(
        select(ProjectContactRel.project_id, Customer.customer_name)
        .join(Customer, Customer.id == ProjectContactRel.customer_id)
        .where(ProjectContactRel.project_id.in_(project_ids))
        .order_by(ProjectContactRel.id)
    ).all()
    mapping: dict[int, list[str]] = {}
    for pid, name in rows:
        mapping.setdefault(pid, []).append(name)
    return mapping


def _fetch_designers(db: Session, project_ids: list[int]) -> dict[int, list[str]]:
    """批量取我方设计师/负责人（project_designer_rel → sys_user.real_name），避免 N+1。"""
    if not project_ids:
        return {}
    rows = db.execute(
        select(ProjectDesignerRel.project_id, SysUser.real_name)
        .join(SysUser, SysUser.id == ProjectDesignerRel.user_id)
        .where(ProjectDesignerRel.project_id.in_(project_ids))
        .order_by(ProjectDesignerRel.id)
    ).all()
    mapping: dict[int, list[str]] = {}
    for pid, name in rows:
        mapping.setdefault(pid, []).append(name)
    return mapping


def build_knowledge_base(db: Session, current_user: dict) -> tuple[str, list[dict]]:
    """实时现算结构化知识库（每次提问调用，不做缓存/快照）。

    返回：
        context : str         知识库全文（含表头 + 每项目一行）
        sources : list[dict]  来源列表 [{id, projectName}]（范围内全部项目）

    隔离口径：
        - 内部员工（role != "客户"）→ 全量项目
        - 客户（role == "客户"）  → 仅 Project.category_id == current_user["category_id"]
    """
    is_customer = current_user.get("role") == "客户"
    category_id = _scope_category_id(current_user)

    # 客户账号 category_id 缺失 → 等同「无数据」，返回空知识库，由上层短路。
    if is_customer and not category_id:
        return "", []

    rows = _fetch_projects(db, category_id)
    if not rows:
        return "", []

    project_ids = [p.id for p, _, _ in rows]
    contacts_map = _fetch_contacts(db, project_ids)
    designers_map = _fetch_designers(db, project_ids)

    lines: list[str] = []
    sources: list[dict] = []
    for p, company_name, first_contact_name in rows:
        project_name = (p.project_name or "").strip() or "未命名项目"
        company = company_name or "未设置"
        contact_names = contacts_map.get(p.id) or []
        # 对接人：rel 多人拼接优先；为空回退 Project.customer_id 首位对接人；再空「未设置」
        contact_desc = _join_names(contact_names, first_contact_name or "未设置")
        designer_names = designers_map.get(p.id) or []
        designer_desc = _join_names(designer_names, "未分配")
        create_date = _format_date(p.create_time)
        expect_date = _format_date(p.expect_time)
        status_label = _status_label(p.project_status)
        lines.append(
            f"- 项目【{project_name}】｜客户单位：{company}｜对接人：{contact_desc}｜"
            f"我方负责人/设计师：{designer_desc}｜立项时间：{create_date}｜"
            f"预计结束时间：{expect_date}｜项目状态：{status_label}"
        )
        sources.append({"id": p.id, "projectName": project_name})

    context = (
        "系统内项目知识库（每条一行，仅据此回答项目/客户相关的业务问题，严禁编造）：\n"
        + "\n".join(lines)
    )
    return context, sources
