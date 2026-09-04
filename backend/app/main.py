"""FastAPI 入口：CORS、静态挂载、异常注册、路由注册"""
import mimetypes
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# 修复 Windows MIME 类型：部分 Windows 注册表把 .js/.css/.json 标为 text/plain，
# Python mimetypes 在 Windows 上会读注册表，导致浏览器拒绝加载前端模块脚本
# （报错：Failed to load module script ... MIME type "text/plain"）。
# 显式覆盖后，任何机器都不依赖注册表。
# ---------------------------------------------------------------------------
mimetypes.init()
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/x-icon", ".ico")

from app.config import settings
from app.utils.exceptions import register_exception_handlers

# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------
from app.routers import (  # noqa: E402
    ai, attachment, auth, comment, customer, customer_category, evaluation,
    flow_template, flow_template_edge, message, node_template, project, project_node,
    project_node_edge, report, sys_dept, sys_operation_log, sys_role, sys_user,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
UPLOAD_PATH = os.path.join(BASE_DIR, settings.UPLOAD_DIR)
FRONTEND_DIST = os.path.join(BASE_DIR, "..", "frontend", "dist")


class ForceStaticFiles(StaticFiles):
    """静态文件挂载：强制覆盖常见前端资源 MIME 类型。

    部分 Windows 机器的注册表把 .js/.css/.json 标为 text/plain（IE 时代残留），
    即使上面已 add_type 覆盖，一旦其他库重新触发 mimetypes.init() 覆盖就会丢失，
    浏览器会拒绝加载 module script（MIME type "text/plain"）。
    这里直接在响应层强制设置，不依赖 mimetypes 全局状态，任何机器都稳定。
    """

    FORCE_MIME = {
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ttf": "font/ttf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".gif": "image/gif",
    }

    def get_response(self, path: str, scope):
        response = super().get_response(path, scope)
        if isinstance(response, FileResponse):
            mime = self.FORCE_MIME.get(os.path.splitext(path)[1].lower())
            if mime:
                response.headers["content-type"] = f"{mime}; charset=utf-8"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保附件目录存在
    os.makedirs(UPLOAD_PATH, exist_ok=True)
    # SQLite：首次启动自动建表 + 初始 admin（幂等）
    init_database()
    yield


def _migrate_project_category() -> None:
    """V1.4.7 结构迁移（幂等）：客户分类=客户单位、客户=对接人。

    老数据 project.customer_id 指向 customer（老语义"客户"）：
      1. category_id 为空的项目，按老 customer 的 category_id 回填归属单位；
      2. 没有任何对接人关联的项目，把老 customer 作为首位对接人补进 project_contact_rel，
         并同步 project.customer_id，保证门户可见性与卡片显示不回退。
    """
    from sqlalchemy import select

    from app.database import SessionLocal, engine
    from app.models import Customer, Project, ProjectContactRel

    from sqlalchemy import inspect
    if not inspect(engine).has_table("project") or not inspect(engine).has_table("project_contact_rel"):
        return

    db = SessionLocal()
    try:
        projects = db.execute(select(Project).where(Project.category_id.is_(None))).scalars().all()
        for p in projects:
            cust = db.get(Customer, p.customer_id)
            if cust is None:
                continue
            p.category_id = cust.category_id
            exists = db.execute(
                select(ProjectContactRel.id).where(ProjectContactRel.project_id == p.id)
            ).scalars().first()
            if exists is None:
                db.add(ProjectContactRel(project_id=p.id, customer_id=cust.id))
        db.commit()
    finally:
        db.close()


def _migrate_user_category_id() -> None:
    """V1.4.15 结构迁移（幂等）：客户账号从"绑定对接人"改为"绑定客户单位"。

    存量客户账号（role=客户 且 customer_id 非空 且 category_id 为空）按
    customer.category_id 回填 category_id；customer_id 字段保留（历史兼容），
    之后隔离逻辑一律以 category_id 为准。重复执行不会二次回填。
    """
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import Customer, SysUser

    db = SessionLocal()
    try:
        users = db.execute(
            select(SysUser).where(
                SysUser.role == "客户",
                SysUser.customer_id.is_not(None),
                SysUser.category_id.is_(None),
            )
        ).scalars().all()
        changed = 0
        for u in users:
            cust = db.get(Customer, u.customer_id)
            if cust is not None and cust.category_id is not None:
                u.category_id = cust.category_id
                changed += 1
        if changed:
            db.commit()
    finally:
        db.close()


DEFAULT_AI_SYSTEM_PROMPT = (
    "你是「青青侠」，青岛领客文化传播有限公司的吉祥物与智能助手，"
    "性格亲切、元气满满，喜欢用可爱的语气交流。\n"
    "你的职责：帮助公司内部员工和客户解答问题，内容可涉及项目进度、客户信息、"
    "流程节点等系统内业务，也可以日常闲聊。\n"
    "回答要求：\n"
    "1. 业务问题仅基于系统提供的项目数据回答，绝不编造不存在的数据；\n"
    "2. 客户账号只能访问其所属公司的项目信息，绝不透露其他公司的任何数据；\n"
    "3. 回答简洁清晰，可用 Markdown 排版（列表、加粗、表格），但不要过度；\n"
    "4. 用中文回答，语气轻松友好。"
)


def _init_ai_config() -> None:
    """V1.4.8：首次启动写入 AI 默认配置（幂等）。

    ai_config 表为空时，用 .env 里的 AI_API_KEY / AI_BASE_URL / AI_MODEL 初始化一条，
    并内置默认「青青侠」卖萌人设 system prompt。之后运行时以数据库为准，
    管理员面板可改（改的是数据库，无需重启）。
    """
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import AiConfig

    db = SessionLocal()
    try:
        config = db.execute(select(AiConfig).order_by(AiConfig.id)).scalars().first()
        if config is not None:
            # V1.4.10：弃用模型自动升级（幂等）。deepseek-chat / deepseek-reasoner
            # 已于 2026/07/24 弃用，统一升级为 deepseek-v4-flash。
            if config.model in ("deepseek-chat", "deepseek-reasoner"):
                config.model = "deepseek-v4-flash"
                db.commit()
            return
        db.add(
            AiConfig(
                system_prompt=DEFAULT_AI_SYSTEM_PROMPT,
                model=settings.AI_MODEL,
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
                temperature=0.7,
                max_tokens=2048,
            )
        )
        db.commit()
    finally:
        db.close()


def init_database() -> None:
    """SQLite 首次启动自动建表 + 创建初始管理员 admin/admin123 + 预置内置部门（幂等，可重复调用）"""
    from sqlalchemy import select

    from app.database import Base, SessionLocal, auto_add_missing_columns, engine, prepare_sqlite_indexes
    from app.models import SysUser  # 触发 models 注册，确保全部表进入 metadata

    if settings.DB_URL.startswith("sqlite"):
        prepare_sqlite_indexes()
    Base.metadata.create_all(bind=engine)
    # 老库自动补齐模型新增列（如 node_template.icon），避免 "no such column" 内部错误
    auto_add_missing_columns()
    # V1.4.7 存量迁移：project 归属从"客户"改为"客户单位"，补 category_id 与对接人关联（幂等）
    _migrate_project_category()
    # V1.4.15 存量迁移：客户账号改为绑定客户单位，按老 customer_id 回填 category_id（幂等）
    _migrate_user_category_id()
    # V1.4.8：AI 助手默认配置初始化（幂等）
    _init_ai_config()
    db = SessionLocal()
    try:
        exists = db.execute(select(SysUser.id).where(SysUser.username == "admin")).scalars().first()
        if exists is None:
            db.add(SysUser(username="admin", password="admin123", real_name="管理员", role="管理员", is_enable=1))
            db.commit()
        # 预置内置部门：研发部/设计部/市场部（幂等）
        from app.services import dept_service
        dept_service.init_default_depts(db)
        # V1.4 存量迁移：老数据部门权限模板 → 用户角色，然后清空部门 role
        dept_service.migrate_dept_role_to_user(db)
        # V1.4.2 角色简化：设计师/设计总监/行政 → 普通
        dept_service.migrate_legacy_roles(db)
        # V1.4.14：启动期自动预置基础节点 + 布展搭建节点 + 3 套流程模板（幂等）
        from app.services import template_service
        template_service.init_default_node_templates(db)
        template_service.init_default_flow_templates(db)
    finally:
        db.close()


app = FastAPI(title="领客文创OA", version="1.4.17", lifespan=lifespan)

# CORS：开发环境放行前端 5173 端口
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理（统一 {code, msg, data}）
register_exception_handlers(app)

# 附件静态资源挂载：/uploads -> ./uploads/
# 注意：目录必须在 mount 之前就存在（StaticFiles 构造函数会校验目录），
# 不能只依赖 lifespan —— mount 是模块加载期执行的，早于服务启动。
os.makedirs(UPLOAD_PATH, exist_ok=True)
app.mount("/uploads", ForceStaticFiles(directory=UPLOAD_PATH), name="uploads")

# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api", tags=["登录"])
app.include_router(sys_user.router, prefix="/api/sysUser", tags=["用户管理"])
app.include_router(sys_dept.router, prefix="/api/sysDept", tags=["部门管理"])
app.include_router(sys_role.router, prefix="/api/sysRole", tags=["自定义角色"])
app.include_router(customer_category.router, prefix="/api/customerCategory", tags=["客户分类"])
app.include_router(customer.router, prefix="/api/customer", tags=["客户库"])
app.include_router(flow_template.router, prefix="/api/flowTemplate", tags=["流程模板"])
app.include_router(flow_template_edge.router, prefix="/api/flowTemplateEdge", tags=["模板连线"])
app.include_router(node_template.router, prefix="/api/nodeTemplate", tags=["节点模板"])
app.include_router(project.router, prefix="/api/project", tags=["项目"])
app.include_router(project_node.router, prefix="/api/projectNode", tags=["项目节点"])
app.include_router(project_node_edge.router, prefix="/api/projectNodeEdge", tags=["项目节点连线"])
app.include_router(attachment.router, prefix="/api/attachment", tags=["附件"])
app.include_router(comment.router, prefix="/api/comment", tags=["评论"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["客户评价"])
app.include_router(message.router, prefix="/api/message", tags=["消息中心"])
app.include_router(sys_operation_log.router, prefix="/api/sysOperationLog", tags=["审计日志"])
app.include_router(report.router, prefix="/api/report", tags=["报表导出"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI助手"])


@app.get("/api/health")
def health():
    return {"code": 200, "msg": "", "data": "ok"}


# ---------------------------------------------------------------------------
# 生产环境：托管前端 dist，SPA 路由回退（未匹配路径返回 index.html）
# 注意：该兜底路由必须注册在最后，且仅拦截非 /api、非 /uploads 路径
# ---------------------------------------------------------------------------
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", ForceStaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # 静态文件存在则直接返回，否则回退 index.html（避免刷新前端路由 404）
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
