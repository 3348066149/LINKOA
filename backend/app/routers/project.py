"""项目基础路由（Api.md 第 7 章）：查询全角色，写操作管理员/行政/设计总监"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_roles
from app.schemas import ProjectCreateRequest, ProjectIdRequest, ProjectListQuery, ProjectUpdateBaseRequest
from app.services import project_service
from app.utils.exceptions import ok

router = APIRouter()

WRITE_ROLES = ("管理员",)


@router.post("/create")
def project_create(
    req: ProjectCreateRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return ok({"projectId": project_service.project_create(db, current_user["id"], req)})


@router.get("/list")
def project_list(
    query: ProjectListQuery = Depends(),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 客户账号：只返回自己所属客户单位名下的项目（V1.4.7）
    return ok(project_service.project_list(db, query, current_user).model_dump(by_alias=True))


@router.get("/detail/{projectId}")
def project_detail(
    projectId: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 客户账号：校验项目归属（只能看自己所属单位的项目）
    return ok(project_service.project_detail(db, projectId, current_user).model_dump(by_alias=True))


@router.post("/updateBase")
def project_update_base(
    req: ProjectUpdateBaseRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    project_service.project_update_base(db, current_user["id"], req)
    return ok(None)


@router.post("/cover/upload")
def project_cover_upload(
    file: UploadFile = File(...),
    projectId: int = Form(...),
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    cover_path = project_service.cover_upload(db, current_user, projectId, file)
    return ok({"coverImage": cover_path})


@router.post("/cover/remove")
def project_cover_remove(
    req: ProjectIdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    project_service.cover_remove(db, current_user, req.project_id)
    return ok(None)


@router.post("/archive")
def project_archive(
    req: ProjectIdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    project_service.project_archive(db, current_user["id"], req.project_id)
    return ok(None)


@router.post("/unArchive")
def project_unarchive(
    req: ProjectIdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    project_service.project_unarchive(db, current_user["id"], req.project_id)
    return ok(None)


@router.post("/delete")
def project_delete(
    req: ProjectIdRequest,
    current_user: dict = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    project_service.project_delete(db, current_user["id"], req.project_id)
    return ok(None)
