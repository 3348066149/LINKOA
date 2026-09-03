"""客户分类 + 客户库 Service（删除防误删：先查关联再拦截）"""
import os
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, CustomerCategory, Project, ProjectContactRel
from app.schemas import (
    CategoryAddRequest,
    CategoryItem,
    CategoryUpdateRequest,
    CustomerAddRequest,
    CustomerDetail,
    CustomerItem,
    CustomerListQuery,
    CustomerUpdateRequest,
    PageResult,
)
from app.services import file_service, log_service
from app.utils.exceptions import BusinessException


# ---- 客户分类 ----

def category_list(db: Session) -> list[CategoryItem]:
    rows = db.execute(select(CustomerCategory).order_by(CustomerCategory.id)).scalars().all()
    return [CategoryItem(id=c.id, category_name=c.category_name, create_time=c.create_time) for c in rows]


def category_add(db: Session, operator_id: int, req: CategoryAddRequest) -> int:
    cat = CustomerCategory(category_name=req.category_name)
    db.add(cat)
    db.flush()
    log_service.add_log(db, operator_id, "category_create", f"新增客户分类：{req.category_name}")
    db.commit()
    return cat.id


def category_update(db: Session, operator_id: int, req: CategoryUpdateRequest) -> None:
    cat = db.get(CustomerCategory, req.id)
    if cat is None:
        raise BusinessException(400, "客户分类不存在")
    cat.category_name = req.category_name
    log_service.add_log(db, operator_id, "category_update", f"修改客户分类：{req.category_name}")
    db.commit()


def category_delete(db: Session, operator_id: int, category_id: int) -> None:
    cat = db.get(CustomerCategory, category_id)
    if cat is None:
        raise BusinessException(400, "客户单位不存在")
    # 删除防误删：单位下存在对接人则拦截
    exists = db.execute(select(Customer.id).where(Customer.category_id == category_id)).scalars().first()
    if exists is not None:
        raise BusinessException(400, "该单位下存在对接人，无法删除")
    # 单位被项目直接引用（V1.4.7）
    proj = db.execute(select(Project.id).where(Project.category_id == category_id)).scalars().first()
    if proj is not None:
        raise BusinessException(400, "该单位存在关联项目，无法删除")
    name = cat.category_name
    db.delete(cat)
    log_service.add_log(db, operator_id, "category_delete", f"删除客户单位：{name}")
    db.commit()


# ---- 客户 ----

def customer_list(db: Session, query: CustomerListQuery) -> PageResult[CustomerItem]:
    stmt = (
        select(Customer, CustomerCategory.category_name.label("category_name"))
        .outerjoin(CustomerCategory, CustomerCategory.id == Customer.category_id)
    )
    # 排序白名单（camelCase 入参 → ORM 列），非法/未传时回退 id 倒序
    sort_map = {
        "customerName": Customer.customer_name,
        "createTime": Customer.create_time,
        "categoryName": CustomerCategory.category_name,
    }
    order_col = sort_map.get(query.sort_field or "")
    if order_col is not None:
        stmt = stmt.order_by(
            order_col.asc() if query.sort_order == "asc" else order_col.desc(),
            Customer.id.desc(),
        )
    else:
        stmt = stmt.order_by(Customer.id.desc())
    count_stmt = select(Customer.id)
    if query.category_id:
        stmt = stmt.where(Customer.category_id == query.category_id)
        count_stmt = count_stmt.where(Customer.category_id == query.category_id)
    if query.customer_name:
        like = f"%{query.customer_name}%"
        stmt = stmt.where(Customer.customer_name.like(like))
        count_stmt = count_stmt.where(Customer.customer_name.like(like))

    total = len(db.execute(count_stmt).scalars().all())
    rows = db.execute(stmt.offset((query.page_num - 1) * query.page_size).limit(query.page_size)).all()
    items = [
        CustomerItem(
            id=c.id, category_id=c.category_id, category_name=category_name,
            customer_name=c.customer_name, contact=c.contact, remark=c.remark,
            cover_image=c.cover_image, create_time=c.create_time,
        )
        for c, category_name in rows
    ]
    return PageResult[CustomerItem](items=items, total=total, page_num=query.page_num, page_size=query.page_size)


def customer_detail(db: Session, customer_id: int) -> CustomerDetail:
    c = db.get(Customer, customer_id)
    if c is None:
        raise BusinessException(400, "客户不存在")
    return CustomerDetail(
        id=c.id, category_id=c.category_id, customer_name=c.customer_name,
        contact=c.contact, remark=c.remark, cover_image=c.cover_image,
    )


def customer_add(db: Session, operator_id: int, req: CustomerAddRequest) -> int:
    if db.get(CustomerCategory, req.category_id) is None:
        raise BusinessException(400, "客户分类不存在")
    c = Customer(category_id=req.category_id, customer_name=req.customer_name, contact=req.contact, remark=req.remark)
    db.add(c)
    db.flush()
    log_service.add_log(db, operator_id, "customer_create", f"新增客户：{req.customer_name}")
    db.commit()
    return c.id


def customer_update(db: Session, operator_id: int, req: CustomerUpdateRequest) -> None:
    c = db.get(Customer, req.id)
    if c is None:
        raise BusinessException(400, "客户不存在")
    if db.get(CustomerCategory, req.category_id) is None:
        raise BusinessException(400, "客户分类不存在")
    c.category_id = req.category_id
    c.customer_name = req.customer_name
    c.contact = req.contact
    c.remark = req.remark
    log_service.add_log(db, operator_id, "customer_update", f"修改客户：{req.customer_name}")
    db.commit()


def customer_delete(db: Session, operator_id: int, customer_id: int) -> None:
    c = db.get(Customer, customer_id)
    if c is None:
        raise BusinessException(400, "对接人不存在")
    # 删除防误删：对接人被项目引用则拦截（V1.4.7 兼容老数据的 customer_id 引用与新关联表）
    exists = db.execute(select(Project.id).where(Project.customer_id == customer_id)).scalars().first()
    rel = db.execute(select(ProjectContactRel.id).where(ProjectContactRel.customer_id == customer_id)).scalars().first()
    if exists is not None or rel is not None:
        raise BusinessException(400, "该对接人存在关联项目，无法删除")
    name = c.customer_name
    db.delete(c)
    log_service.add_log(db, operator_id, "customer_delete", f"删除对接人：{name}")
    db.commit()


# ---- 客户卡片封面图 ----

COVER_MAX_SIZE = 5 * 1024 * 1024  # 5MB
COVER_ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def _get_customer_or_400(db: Session, customer_id: int) -> Customer:
    c = db.get(Customer, customer_id)
    if c is None:
        raise BusinessException(400, "客户不存在")
    return c


def cover_upload(db: Session, operator: dict, customer_id: int, file: UploadFile) -> str:
    """上传客户卡片封面图：存 uploads/cover/，返回可直连的相对路径"""
    customer = _get_customer_or_400(db, customer_id)

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
    if customer.cover_image:
        file_service.remove_disk_file(os.path.join(file_service.UPLOAD_ROOT, customer.cover_image.replace("/", os.sep)))

    customer.cover_image = f"cover/{save_name}"
    log_service.add_log(db, operator["id"], "customer_cover_upload", f"上传客户封面图：{safe_name}")
    db.commit()
    return customer.cover_image


def cover_remove(db: Session, operator: dict, customer_id: int) -> None:
    """移除客户卡片封面图"""
    customer = _get_customer_or_400(db, customer_id)
    if not customer.cover_image:
        return
    old = customer.cover_image
    customer.cover_image = None
    log_service.add_log(db, operator["id"], "customer_cover_remove", "移除客户封面图")
    db.commit()
    file_service.remove_disk_file(os.path.join(file_service.UPLOAD_ROOT, old.replace("/", os.sep)))
