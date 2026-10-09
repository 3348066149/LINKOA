"""项目 Service：模板实例化（ID 重映射）、归档硬拦截、级联删除"""
import os
import uuid
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Attachment,
    Comment,
    Customer,
    CustomerCategory,
    FlowTemplate,
    FlowTemplateNode,
    FlowTemplateNodeEdge,
    Message,
    Project,
    ProjectContactRel,
    ProjectDesignerRel,
    ProjectEvaluation,
    ProjectNode,
    ProjectNodeEdge,
    ProjectNodeFormValue,
    SysUser,
)
from app.schemas import (
    ContactItem,
    DesignerItem,
    EvaluationPublicOut,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectEdgeOut,
    ProjectListItem,
    ProjectListQuery,
    ProjectNodeBrief,
    ProjectUpdateBaseRequest,
    PageResult,
)
from app.services import file_service, log_service
from app.utils.exceptions import BusinessException


def get_project_or_400(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise BusinessException(400, "项目不存在")
    return project


def check_project_archived(project: Project) -> None:
    """归档状态全局硬拦截：已归档项目除查询外一切写入返回 400"""
    if project.project_status == "已归档":
        raise BusinessException(400, "项目已归档，禁止修改任何内容")


# ---------------------------------------------------------------------------
# 模板实例化（最核心）：值拷贝 + 节点ID重映射，全部在一个事务内
# ---------------------------------------------------------------------------

def _instantiate_from_template(db: Session, project: Project, template_id: int, operator_id: int) -> None:
    tpl = db.get(FlowTemplate, template_id)
    if tpl is None:
        raise BusinessException(400, "所选流程模板不存在")

    tpl_nodes = db.execute(
        select(FlowTemplateNode).where(FlowTemplateNode.template_id == template_id).order_by(FlowTemplateNode.sort, FlowTemplateNode.id)
    ).scalars().all()

    # 1. 拷贝节点，维护 Map<old_template_node_id, new_project_node_id> + node_template_id 映射
    id_map: dict[int, int] = {}
    node_tpl_map: dict[int, int | None] = {}
    # V1.4.3：溯源节点模板图标（flow_template_node 不冗余存 icon）
    ntid_list = [tn.node_template_id for tn in tpl_nodes if tn.node_template_id]
    icons_by_tpl: dict[int, str | None] = {}
    if ntid_list:
        from app.models import NodeTemplate as _NT
        icons_by_tpl = {
            nt.id: nt.icon
            for nt in db.execute(select(_NT).where(_NT.id.in_(ntid_list))).scalars().all()
        }
    for tn in tpl_nodes:
        node = ProjectNode(
            project_id=project.id,
            node_title=tn.node_title,
            node_remark=tn.node_remark,
            icon=icons_by_tpl.get(tn.node_template_id) if tn.node_template_id else None,
            sort=tn.sort,
            pos_x=tn.pos_x,
            pos_y=tn.pos_y,
            create_user_id=operator_id,
        )
        db.add(node)
        db.flush()
        id_map[tn.id] = node.id
        node_tpl_map[node.id] = tn.node_template_id

    # 2. 拷贝连线：source/target 强制重映射为新节点ID
    tpl_edges = db.execute(
        select(FlowTemplateNodeEdge).where(FlowTemplateNodeEdge.template_id == template_id)
    ).scalars().all()
    for te in tpl_edges:
        source = id_map.get(te.source_node_id)
        target = id_map.get(te.target_node_id)
        if source is None or target is None:
            continue  # 模板数据异常时跳过孤儿连线，不产生脏引用
        db.add(
            ProjectNodeEdge(project_id=project.id, source_node_id=source, target_node_id=target, label=te.label)
        )

    # 3. 从节点模板库拷贝表单字段 -> 填写值表（V1.3：表单定义唯一来源是节点模板）
    tpl_ids = [ntid for ntid in node_tpl_map.values() if ntid]
    forms_by_tpl: dict[int, str | None] = {}
    if tpl_ids:
        from app.models import NodeTemplate  # 延迟导入避免循环
        forms_by_tpl = {
            nt.id: nt.form_fields
            for nt in db.execute(select(NodeTemplate).where(NodeTemplate.id.in_(tpl_ids))).scalars().all()
        }
    from app.services.node_service import copy_node_template_form  # 延迟导入避免循环

    for new_node_id, ntid in node_tpl_map.items():
        if ntid:
            copy_node_template_form(db, new_node_id, forms_by_tpl.get(ntid))


def _resolve_user_category_id(db: Session, current_user: dict) -> int | None:
    """客户账号 → 其绑定的客户单位ID（V1.4.15：直接由 category_id 取，不再溯源对接人）"""
    return current_user.get("category_id")


def _validate_category_and_contacts(db: Session, category_id: int, contact_ids: list[int]) -> list[Customer]:
    """校验客户单位存在、对接人非空且全部属于该单位（V1.4.7）"""
    if db.get(CustomerCategory, category_id) is None:
        raise BusinessException(400, "客户单位不存在")
    if not contact_ids:
        raise BusinessException(400, "请至少选择一位客户对接人")
    contacts = db.execute(
        select(Customer).where(Customer.id.in_(dict.fromkeys(contact_ids)))
    ).scalars().all()
    found = {c.id for c in contacts}
    missing = [cid for cid in dict.fromkeys(contact_ids) if cid not in found]
    if missing:
        raise BusinessException(400, "所选客户对接人不存在")
    wrong = [c for c in contacts if c.category_id != category_id]
    if wrong:
        raise BusinessException(400, "对接人必须属于所选客户单位")
    # 保持入参顺序
    by_id = {c.id: c for c in contacts}
    return [by_id[cid] for cid in dict.fromkeys(contact_ids)]


def project_create(db: Session, operator_id: int, req: ProjectCreateRequest) -> int:
    contacts = _validate_category_and_contacts(db, req.category_id, req.contact_customer_ids)

    project = Project(
        project_name=req.project_name,
        category_id=req.category_id,
        customer_id=contacts[0].id,
        project_desc=req.project_desc,
        start_time=req.start_time,
        expect_time=req.expect_time,
        create_time=req.create_time or datetime.now(),
        project_status="进行中",
        create_user_id=operator_id,
    )
    db.add(project)
    db.flush()

    # 参与设计师关联（仅溯源展示，不做权限控制）
    for uid in dict.fromkeys(req.designer_rel_user_id_list):
        db.add(ProjectDesignerRel(project_id=project.id, user_id=uid))

    # 客户对接人关联（V1.4.7，仅展示，不做权限控制）
    for c in contacts:
        db.add(ProjectContactRel(project_id=project.id, customer_id=c.id))

    # 选择模板时执行实例化（值拷贝 + ID 重映射）
    if req.template_id:
        _instantiate_from_template(db, project, req.template_id, operator_id)

    log_service.add_log(db, operator_id, "project_create", f"新建项目：{req.project_name}", related_project_id=project.id)
    db.commit()
    return project.id


def _designer_names(db: Session, project_ids: list[int]) -> dict[int, str]:
    """批量取项目参与设计师姓名，顿号分隔；用户已删除时兜底"已删除用户"（V1.3）"""
    if not project_ids:
        return {}
    stmt = (
        select(ProjectDesignerRel.project_id, SysUser.real_name)
        .outerjoin(SysUser, SysUser.id == ProjectDesignerRel.user_id)
        .where(ProjectDesignerRel.project_id.in_(project_ids))
        .order_by(ProjectDesignerRel.id)
    )
    names: dict[int, list[str]] = {}
    for pid, real_name in db.execute(stmt).all():
        names.setdefault(pid, []).append(real_name or "已删除用户")
    return {pid: "、".join(ns) for pid, ns in names.items()}


def _contact_names(db: Session, project_ids: list[int]) -> dict[int, str]:
    """批量取项目客户对接人姓名，顿号分隔（V1.4.7）"""
    if not project_ids:
        return {}
    stmt = (
        select(ProjectContactRel.project_id, Customer.customer_name)
        .outerjoin(Customer, Customer.id == ProjectContactRel.customer_id)
        .where(ProjectContactRel.project_id.in_(project_ids))
        .order_by(ProjectContactRel.id)
    )
    names: dict[int, list[str]] = {}
    for pid, cname in db.execute(stmt).all():
        names.setdefault(pid, []).append(cname or "已删除对接人")
    return {pid: "、".join(ns) for pid, ns in names.items()}


def _evaluation_map(db: Session, project_ids: list[int]) -> dict[int, EvaluationPublicOut]:
    """批量取项目客户评价（公开字段），一次 IN 查询防 N+1；无评价的项目不出现在返回 dict"""
    if not project_ids:
        return {}
    stmt = select(ProjectEvaluation).where(ProjectEvaluation.project_id.in_(project_ids))
    result: dict[int, EvaluationPublicOut] = {}
    for e in db.execute(stmt).scalars().all():
        result[e.project_id] = EvaluationPublicOut(
            design_score=e.design_score,
            service_score=e.service_score,
            product_score=e.product_score,
            customer_remark=e.customer_remark,
            evaluate_time=e.evaluate_time,
        )
    return result


def project_list(db: Session, query: ProjectListQuery, current_user: dict | None = None) -> PageResult[ProjectListItem]:
    stmt = (
        select(
            Project,
            CustomerCategory.category_name.label("company_name"),
            Customer.customer_name.label("first_contact_name"),
        )
        .outerjoin(CustomerCategory, CustomerCategory.id == Project.category_id)
        .outerjoin(Customer, Customer.id == Project.customer_id)
    )
    count_stmt = select(Project.id)

    # 客户账号：只能看到自己所属客户单位名下的全部项目（按单位隔离，V1.4.7）
    if current_user and current_user.get("role") == "客户":
        cat_id = _resolve_user_category_id(db, current_user)
        if not cat_id:
            return PageResult[ProjectListItem](items=[], total=0, page_num=query.page_num, page_size=query.page_size)
        stmt = stmt.where(Project.category_id == cat_id)
        count_stmt = count_stmt.where(Project.category_id == cat_id)

    # 排序白名单（camelCase 入参 → ORM 列），非法/未传时回退 id 倒序
    sort_map = {
        "projectName": Project.project_name,
        "createTime": Project.create_time,
        "expectTime": Project.expect_time,
        "projectStatus": Project.project_status,
    }
    order_col = sort_map.get(query.sort_field or "")
    if order_col is not None:
        stmt = stmt.order_by(
            order_col.asc() if query.sort_order == "asc" else order_col.desc(),
            Project.id.desc(),
        )
    else:
        stmt = stmt.order_by(Project.id.desc())
    if query.project_name:
        like = f"%{query.project_name}%"
        stmt = stmt.where(Project.project_name.like(like))
        count_stmt = count_stmt.where(Project.project_name.like(like))
    if query.category_id:
        stmt = stmt.where(Project.category_id == query.category_id)
        count_stmt = count_stmt.where(Project.category_id == query.category_id)
    if query.project_status:
        stmt = stmt.where(Project.project_status == query.project_status)
        count_stmt = count_stmt.where(Project.project_status == query.project_status)
    if query.create_time_start:
        stmt = stmt.where(Project.create_time >= query.create_time_start)
        count_stmt = count_stmt.where(Project.create_time >= query.create_time_start)
    if query.create_time_end:
        stmt = stmt.where(Project.create_time <= query.create_time_end)
        count_stmt = count_stmt.where(Project.create_time <= query.create_time_end)

    total = len(db.execute(count_stmt).scalars().all())
    rows = db.execute(stmt.offset((query.page_num - 1) * query.page_size).limit(query.page_size)).all()
    name_map = _designer_names(db, [p.id for p, _, _ in rows])
    contact_map = _contact_names(db, [p.id for p, _, _ in rows])
    progress_map = _project_progress_map(db, [p.id for p, _, _ in rows])
    evaluation_map = _evaluation_map(db, [p.id for p, _, _ in rows])
    items = [
        ProjectListItem(
            id=p.id, project_name=p.project_name,
            category_id=p.category_id, company_name=company_name,
            customer_id=p.customer_id, customer_name=first_contact_name,
            contact_names=contact_map.get(p.id, ""),
            designer_names=name_map.get(p.id, ""),
            create_time=p.create_time, start_time=p.start_time, expect_time=p.expect_time,
            cover_image=p.cover_image,
            progress_percent=progress_map.get(p.id, 0),
            project_status=p.project_status,
            evaluation=evaluation_map.get(p.id),
        )
        for p, company_name, first_contact_name in rows
    ]
    return PageResult[ProjectListItem](items=items, total=total, page_num=query.page_num, page_size=query.page_size)


def _project_progress_map(db: Session, project_ids: list[int]) -> dict[int, int]:
    """节点进度占比：已填表单节点数 / 全部节点数（客户门户用）"""
    if not project_ids:
        return {}
    node_total: dict[int, int] = dict(
        db.execute(
            select(ProjectNode.project_id, func.count(ProjectNode.id))
            .where(ProjectNode.project_id.in_(project_ids))
            .group_by(ProjectNode.project_id)
        ).all()
    )
    if not node_total:
        return {}
    filled: dict[int, int] = dict(
        db.execute(
            select(ProjectNode.project_id, func.count(func.distinct(ProjectNodeFormValue.project_node_id)))
            .join(ProjectNode, ProjectNode.id == ProjectNodeFormValue.project_node_id)
            .where(
                ProjectNode.project_id.in_(project_ids),
                ProjectNodeFormValue.field_value.isnot(None),
                ProjectNodeFormValue.field_value != "",
            )
            .group_by(ProjectNode.project_id)
        ).all()
    )
    return {
        pid: min(100, round((filled.get(pid, 0) / cnt) * 100))
        for pid, cnt in node_total.items()
    }


def project_detail(db: Session, project_id: int, current_user: dict | None = None) -> ProjectDetail:
    project = get_project_or_400(db, project_id)
    # 客户账号归属校验：只能查看自己所属客户单位名下的项目（V1.4.7 按单位隔离）
    if current_user and current_user.get("role") == "客户":
        cat_id = _resolve_user_category_id(db, current_user)
        if not cat_id or project.category_id != cat_id:
            raise BusinessException(403, "无权查看该项目的进度")
    category = db.get(CustomerCategory, project.category_id) if project.category_id else None
    customer = db.get(Customer, project.customer_id)
    create_user = db.get(SysUser, project.create_user_id)

    designers = db.execute(
        select(ProjectDesignerRel.user_id, SysUser.real_name)
        .outerjoin(SysUser, SysUser.id == ProjectDesignerRel.user_id)
        .where(ProjectDesignerRel.project_id == project_id)
        .order_by(ProjectDesignerRel.id)
    ).all()

    contacts = db.execute(
        select(ProjectContactRel.customer_id, Customer.customer_name)
        .outerjoin(Customer, Customer.id == ProjectContactRel.customer_id)
        .where(ProjectContactRel.project_id == project_id)
        .order_by(ProjectContactRel.id)
    ).all()

    # 节点顺序（V1.4.7 修复）：按画布位置从左到右、从上到下，
    # 避免"删除节点后重新添加（sort 取当前最大值+1）导致客户时间线顺序错乱"
    nodes = db.execute(
        select(ProjectNode)
        .where(ProjectNode.project_id == project_id)
        .order_by(ProjectNode.pos_x, ProjectNode.pos_y, ProjectNode.sort, ProjectNode.id)
    ).scalars().all()
    node_ids = [n.id for n in nodes]
    form_node_ids: set[int] = set()
    form_filled_node_ids: set[int] = set()
    if node_ids:
        form_node_ids = set(
            db.execute(
                select(ProjectNodeFormValue.project_node_id)
                .where(ProjectNodeFormValue.project_node_id.in_(node_ids))
                .distinct()
            ).scalars().all()
        )
        # 已填值的节点：field_value 非空
        form_filled_node_ids = set(
            db.execute(
                select(ProjectNodeFormValue.project_node_id)
                .where(
                    ProjectNodeFormValue.project_node_id.in_(node_ids),
                    ProjectNodeFormValue.field_value.isnot(None),
                    ProjectNodeFormValue.field_value != "",
                )
                .distinct()
            ).scalars().all()
        )

    # 节点附件数
    attachment_count_map: dict[int, int] = {}
    if node_ids:
        attachment_count_map = {
            pid: cnt
            for pid, cnt in db.execute(
                select(Attachment.project_node_id, func.count(Attachment.id))
                .where(Attachment.project_node_id.in_(node_ids))
                .group_by(Attachment.project_node_id)
            ).all()
        }

    edges = db.execute(
        select(ProjectNodeEdge).where(ProjectNodeEdge.project_id == project_id).order_by(ProjectNodeEdge.id)
    ).scalars().all()

    evaluation = db.execute(
        select(ProjectEvaluation).where(ProjectEvaluation.project_id == project_id)
    ).scalars().first()

    return ProjectDetail(
        id=project.id,
        project_name=project.project_name,
        category_id=project.category_id,
        company_name=category.category_name if category else None,
        customer_id=project.customer_id,
        customer_name=customer.customer_name if customer else None,
        project_desc=project.project_desc,
        start_time=project.start_time,
        expect_time=project.expect_time,
        cover_image=project.cover_image,
        project_status=project.project_status,
        create_user_name=create_user.real_name if create_user else "已删除用户",
        create_time=project.create_time,
        designer_list=[DesignerItem(user_id=uid, real_name=name or "已删除用户") for uid, name in designers],
        contact_list=[ContactItem(customer_id=cid, customer_name=cname or "已删除对接人") for cid, cname in contacts],
        nodes=[
            ProjectNodeBrief(
                id=n.id, node_title=n.node_title, node_remark=n.node_remark, icon=n.icon,
                sort=n.sort, pos_x=n.pos_x, pos_y=n.pos_y,
                has_form=n.id in form_node_ids,
                form_filled=n.id in form_filled_node_ids,
                attachment_count=attachment_count_map.get(n.id, 0),
                create_time=n.create_time,
                update_time=n.update_time,
            )
            for n in nodes
        ],
        edges=[
            ProjectEdgeOut(id=e.id, source_node_id=e.source_node_id, target_node_id=e.target_node_id, label=e.label)
            for e in edges
        ],
        evaluation=EvaluationPublicOut(
            design_score=evaluation.design_score,
            service_score=evaluation.service_score,
            product_score=evaluation.product_score,
            customer_remark=evaluation.customer_remark,
            evaluate_time=evaluation.evaluate_time,
        ) if evaluation else None,
    )


def project_update_base(db: Session, operator_id: int, req: ProjectUpdateBaseRequest) -> None:
    project = get_project_or_400(db, req.id)
    check_project_archived(project)
    contacts = _validate_category_and_contacts(db, req.category_id, req.contact_customer_ids)

    project.project_name = req.project_name
    project.category_id = req.category_id
    project.customer_id = contacts[0].id
    project.project_desc = req.project_desc
    project.start_time = req.start_time
    project.expect_time = req.expect_time
    if req.create_time is not None:
        project.create_time = req.create_time

    # 参与设计师全量覆盖（先删后插）
    db.execute(delete(ProjectDesignerRel).where(ProjectDesignerRel.project_id == project.id))
    for uid in dict.fromkeys(req.designer_rel_user_id_list):
        db.add(ProjectDesignerRel(project_id=project.id, user_id=uid))

    # 客户对接人全量覆盖（先删后插，V1.4.7）
    db.execute(delete(ProjectContactRel).where(ProjectContactRel.project_id == project.id))
    for c in contacts:
        db.add(ProjectContactRel(project_id=project.id, customer_id=c.id))

    log_service.add_log(db, operator_id, "project_update", f"修改项目基础信息：{req.project_name}", related_project_id=project.id)
    db.commit()


def project_archive(db: Session, operator_id: int, project_id: int) -> None:
    project = get_project_or_400(db, project_id)
    if project.project_status == "已归档":
        raise BusinessException(400, "项目已是归档状态")
    project.project_status = "已归档"
    log_service.add_log(db, operator_id, "project_archive", f"归档项目：{project.project_name}", related_project_id=project.id)
    db.commit()


def project_unarchive(db: Session, operator_id: int, project_id: int) -> None:
    project = get_project_or_400(db, project_id)
    if project.project_status != "已归档":
        raise BusinessException(400, "项目未归档")
    project.project_status = "进行中"
    log_service.add_log(db, operator_id, "project_unarchive", f"取消归档项目：{project.project_name}", related_project_id=project.id)
    db.commit()


def project_delete(db: Session, operator_id: int, project_id: int) -> None:
    """物理删除：单事务级联删除全部子数据 + 磁盘附件文件；审计日志永久留存"""
    project = get_project_or_400(db, project_id)
    if project.project_status == "已归档":
        raise BusinessException(400, "已归档项目请先取消归档后再删除")

    node_ids = db.execute(select(ProjectNode.id).where(ProjectNode.project_id == project_id)).scalars().all()

    # 磁盘附件文件同步删除（先收集路径，数据库删成功后再删文件）
    attachments = db.execute(
        select(Attachment).where(Attachment.project_id == project_id)
    ).scalars().all()
    # 相对路径需拼 UPLOAD_ROOT 才能定位磁盘文件（否则按 CWD 解析，删不掉孤儿文件）
    file_paths = [
        a.file_path if (a.file_path and os.path.isabs(a.file_path))
        else os.path.join(file_service.UPLOAD_ROOT, (a.file_path or "").replace("/", os.sep))
        for a in attachments
    ]
    # 项目封面图一并清理，避免残留孤儿文件
    if project.cover_image:
        file_paths.append(
            os.path.join(file_service.UPLOAD_ROOT, project.cover_image.replace("/", os.sep))
        )

    db.execute(delete(Attachment).where(Attachment.project_id == project_id))
    db.execute(delete(Comment).where(Comment.project_id == project_id))
    db.execute(delete(Message).where(Message.project_id == project_id))
    db.execute(delete(ProjectDesignerRel).where(ProjectDesignerRel.project_id == project_id))
    db.execute(delete(ProjectContactRel).where(ProjectContactRel.project_id == project_id))
    db.execute(delete(ProjectEvaluation).where(ProjectEvaluation.project_id == project_id))
    db.execute(delete(ProjectNodeEdge).where(ProjectNodeEdge.project_id == project_id))
    if node_ids:
        db.execute(delete(ProjectNodeFormValue).where(ProjectNodeFormValue.project_node_id.in_(node_ids)))
    db.execute(delete(ProjectNode).where(ProjectNode.project_id == project_id))

    pname = project.project_name
    db.delete(project)
    # 删除日志：related_project_id 保留已删项目ID，永久留存
    log_service.add_log(db, operator_id, "project_delete", f"删除项目：{pname}", related_project_id=project_id)
    db.commit()

    for path in file_paths:
        file_service.remove_disk_file(path)


# ---- 卡片封面图 ----

COVER_MAX_SIZE = 5 * 1024 * 1024  # 5MB
COVER_ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def cover_upload(db: Session, operator: dict, project_id: int, file: UploadFile) -> str:
    """上传项目卡片封面图：存 uploads/cover/，返回可直连的相对路径"""
    project = get_project_or_400(db, project_id)
    check_project_archived(project)

    ext = COVER_ALLOWED_TYPES.get(file.content_type or "")
    if ext is None:
        raise BusinessException(400, "封面图仅支持 jpg / png / webp 格式")

    # 魔数校验（V1.4.4）：Content-Type 可伪造，按文件头判断真实图片内容
    from app.utils.images import is_valid_image, read_image_head
    if not is_valid_image(read_image_head(file)):
        raise BusinessException(400, "文件内容不是有效的图片（jpg/png/webp）")

    save_dir = os.path.join(file_service.UPLOAD_ROOT, "cover")
    os.makedirs(save_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "cover")
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, save_name)

    size = 0
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > COVER_MAX_SIZE:
                    raise BusinessException(400, "封面图大小不能超过 5MB")
                f.write(chunk)
    except BusinessException:
        file_service.remove_disk_file(save_path)
        raise
    except OSError:
        file_service.remove_disk_file(save_path)
        raise BusinessException(500, "封面图写入失败")

    # 删除旧封面磁盘文件（忽略失败）
    if project.cover_image:
        file_service.remove_disk_file(os.path.join(file_service.UPLOAD_ROOT, project.cover_image.replace("/", os.sep)))

    project.cover_image = f"cover/{save_name}"
    log_service.add_log(db, operator["id"], "project_cover_upload", f"上传项目封面图：{safe_name}", related_project_id=project_id)
    db.commit()
    return project.cover_image


def cover_remove(db: Session, operator: dict, project_id: int) -> None:
    """移除项目卡片封面图"""
    project = get_project_or_400(db, project_id)
    check_project_archived(project)
    if not project.cover_image:
        return
    old = project.cover_image
    project.cover_image = None
    log_service.add_log(db, operator["id"], "project_cover_remove", "移除项目封面图", related_project_id=project_id)
    db.commit()
    file_service.remove_disk_file(os.path.join(file_service.UPLOAD_ROOT, old.replace("/", os.sep)))
