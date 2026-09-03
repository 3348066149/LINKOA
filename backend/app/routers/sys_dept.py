"""部门路由（V1.3 新增，仅管理员）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import DeptAddRequest, DeptDeleteRequest, DeptUpdateRequest
from app.services import dept_service
from app.utils.exceptions import ok

# 路由级统一鉴权：仅管理员
router = APIRouter(dependencies=[Depends(require_roles("管理员"))])


@router.get("/list")
def list_depts(db: Session = Depends(get_db)):
    items = dept_service.list_depts(db)
    return ok([i.model_dump(by_alias=True) for i in items])


@router.post("/add")
def add_dept(
    req: DeptAddRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dept_id = dept_service.add_dept(db, current_user["id"], req)
    return ok({"deptId": dept_id})


@router.post("/update")
def update_dept(
    req: DeptUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dept_service.update_dept(db, current_user["id"], req)
    return ok(None)


@router.post("/delete")
def delete_dept(
    req: DeptDeleteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dept_service.delete_dept(db, current_user["id"], req.id)
    return ok(None)
