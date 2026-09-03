"""报表导出路由（Api.md 第 14 章，管理员/行政/设计总监）"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.schemas import ReportExportQuery
from app.services import excel_service

router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/exportProject")
def export_project(
    query: ReportExportQuery = Depends(),
    current_user: dict = Depends(require_roles("管理员")),
    db: Session = Depends(get_db),
):
    content, filename = excel_service.export_projects(db, query)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
