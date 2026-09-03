# 青岛领客文化传播｜项目流程管理 OA 后端

FastAPI + SQLAlchemy 2.0，服务端口 8000。**数据库默认 SQLite**（文件位于项目根 `data/linkoa.db`（本地与 Docker 共用，备份只拷 data/），相对路径配置，随文件夹迁移），也支持 MySQL（改 `.env` 的 `DB_URL` 即可）。

## 启动步骤

```bash
# 1. 创建虚拟环境（首次）
python -m venv .venv

# 2. 安装依赖
.venv/Scripts/python -m pip install -r backend/requirements.txt   # Windows
# .venv/bin/python -m pip install -r backend/requirements.txt     # Linux/Mac

# 3. 启动（首次启动自动建表 + 创建 admin/admin123 + 预置内置部门 + 执行存量迁移）
cd backend
../.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> Windows 用户直接双击项目根目录的 `start.bat` 即可（自动建 venv、装依赖、启动）；停止用 `stop.bat`。Linux / macOS 运行项目根目录的 `start.sh` 等价一键启动（先 `chmod +x start.sh`），停止用 `stop.sh`。

- 数据库文件：`data/linkoa.db`（项目根 `data/`，SQLite，V1.4.18 起本地与 Docker 统一指向；`.env` 的 `DB_URL=sqlite:///./../data/linkoa.db` 为相对 `backend/` 的写法，由 `config.py` 按 `__file__` 解析为绝对路径，**备份/搬家只拷 `data/` 一个文件夹**）
- 接口文档（Swagger）：http://localhost:8000/docs
- 健康检查：`GET /api/health`
- 附件目录：`data/uploads/`（与数据库同目录，随项目走：`cover/` 封面、`node_icon/` 节点图标、`node_form/` 节点表单图像、`YYYYMMDD/` 附件）

## 数据库说明（SQLite / MySQL 双支持，可切换）

| 数据库 | 适用场景 | DB_URL |
|---|---|---|
| **SQLite**（默认） | 单机 / 便携 / 单人使用 | `sqlite:///./../data/linkoa.db`（项目根 data/） |
| **MySQL** | 多用户并发协作 | `mysql+pymysql://root:pwd@localhost:3306/linkoa?charset=utf8mb4` |

一键切换（需重启后端）与数据迁移：

```bash
python switch_db.py sqlite   # 切到 SQLite
python switch_db.py mysql    # 切到 MySQL
python migrate_mysql_to_sqlite.py   # MySQL → SQLite
python migrate_sqlite_to_mysql.py   # SQLite → MySQL
```

- 首次启动自动建表 + 创建初始管理员 `admin / admin123` + 预置内置部门（研发部/设计部/市场部）
- 启动时幂等执行存量迁移：V1.4 部门权限模板 → 用户角色；V1.4.2 老角色（设计师/设计总监/行政）→ 普通（admin 强制保持管理员）；V1.4.7 `_migrate_project_category()` 为历史项目回填客户单位并补对接人关联
- **V1.4.4 起结构自愈**：启动时 `auto_add_missing_columns()` 比对 ORM 模型与实际库结构，缺失列自动 `ALTER TABLE ADD COLUMN` 补齐（SQLite / MySQL 均生效）。模型加列后无需手写迁移 SQL，启动一次即升级；仅补列，不改列类型、不删列。

## 版本特性（V1.4.18）

- **Docker 部署目录化（V1.4.18）**：Docker 相关文件统一收进项目根 `docker/` 目录（Dockerfile / docker-compose.yml / docker-compose.mysql.yml / docker-entrypoint.sh / 部署指南 docker/README.md），部署时进入 `docker/` 目录执行 `docker compose up -d --build` 即可；容器数据挂载到项目根 `data/`。本版本为部署与文档整理，**功能与接口无变更**。

- **部门与角色解耦**：`sys_dept` 仅组织分组（不携带权限）；权限由用户自身角色决定（普通/管理员；客户账号独立只读）。
- **客户门户（V1.4.7 重构）**：客户登录进入独立只读门户，按**所属客户单位**隔离（可见同单位全部项目）；不展示节点进度/总进度，改为立项时间 + 预计结束时间 + 倒计时；支持项目名搜索、进行中/已结项筛选、立项时间范围筛选；已归档展示为「已结项」。
- **节点图标**：`node_template.icon` 预设图标名或自定义上传路径（`POST /api/nodeTemplate/icon/upload`）；项目节点冗余拷贝（`project_node.icon`），画布与节点库显示。
- **表单字段类型**：`text_single / text_multi / select / image（上传图像）/ link（链接）`；`POST /api/projectNode/formImage/upload` 上传节点表单图像。
- **连线与上传加固（V1.4.4）**：连线端点校验改为按端点存在性判断（修复自环被误报「节点不存在」）；连线接口记录真实操作人并写审计日志；图片上传增加文件头魔数校验（jpg/png/webp），伪造扩展名的文件被拒绝。
- **登录防暴力破解（V1.4.6）**：`SysUser` 新增 `login_fail_count` / `locked_until`；连续失败 5 次锁定 10 分钟，登录成功清零，锁定期间拒绝登录；账号不存在不累加（防枚举）。新增 `POST /api/sysUser/unlock` 管理员手动解锁。
- **客户单位/对接人模型（V1.4.7）**：`Project.category_id`（归属单位）+ `project_contact_rel`（对接人多对多，全量覆盖）；`customer_id` 语义变更为首位对接人。项目新建/编辑入参 `categoryId + contactCustomerIds`；列表支持单位/立项时间筛选；详情节点按画布位置（posX→posY→sort→id）排序；登录返回 `companyName`。
- **AI 助手「青青侠」（V1.4.8）**：新增 `ai_config` / `ai_conversation` / `ai_message` 三张表；LLM 抽象层 `services/llm/`（`BaseLLMProvider` + `DeepSeekProvider` + `get_provider` 工厂），可扩展接入多模型；结构化文本知识库全量注入项目数据上下文，**客户账号按 `category_id` 强制隔离**（只能问自己公司项目）；`POST /api/ai/chat/stream` 走 SSE 流式（事件 delta/error/done）；管理员 `GET/PUT /api/ai/config` 配置人设/模型/Key/BaseURL/生成参数（api_key 脱敏）。
- **AI 助手安全加固（V1.4.9）**：身份绑定与数据隔离红线（按账号自动注入身份、代码级安全 prompt 强制追加、严禁反问公司/身份）；per-user 滑动窗口限流（60 秒 20 次，管理员豁免）；知识库为空时短路返回固定话术、不调 LLM 防幻觉；会话置顶/重命名/软删（`AiConversation.pinned`/`is_deleted` 列 + `PATCH /conversations/{id}` + `POST /conversations/{id}/pin`）；AI 对话审计留痕（`ai_chat`/`ai_conversation_*` 四类日志）。
- **模型升级（V1.4.10）**：模型从已弃用的 `deepseek-chat` 升级为 `deepseek-v4-flash`（`.env` / `ai_config` 默认值 + 启动幂等回填 `deepseek-chat|deepseek-reasoner` → `deepseek-v4-flash`）。
- **健壮性修复（V1.4.11）**：`file_service.remove_disk_file` 由只捕获 `OSError` 改为捕获 `Exception`——文件被占用、权限不足或运行环境给 `os.remove` 挂了删除钩子时，可能抛出非 `OSError` 的异常，一旦冒泡会让调用方接口直接 500（即使数据库记录已正确更新）；孤儿文件最多是磁盘垃圾，不应让用户看到 500。自检脚本 `tests/full_flow_check.py` 增加**前置清理**（按 `全流程测试` 前缀自愈删除历史残留，保证可重复运行）与 `check()` 的非 JSON 响应保护（避免单点崩溃导致末尾清理不执行、残留越积越多）。
- **CRUD 未保存数据丢失修复（V1.4.12）**：前端 `DynamicForm` 组件新增 `isDirty` 脏检测（对比初始快照）；项目详情页 `views/project/Detail.vue` 在切换节点、点画布空白/面板关闭、新增节点、归档前及路由离开守卫 `onBeforeRouteLeave` 处统一拦截未保存修改，弹出「保存 / 放弃修改 / 取消」三态确认（基于 Element Plus `distinguishCancelAndClose`），杜绝编辑中切换节点导致表单被静默覆盖。纯前端交互修复，后端接口契约无变化。
- **客户账号改绑客户单位（V1.4.15）**：`sys_user` 新增 `category_id` 列（绑定 `customer_category.id`），`customer_id` 列保留为历史兼容；`SysUserCreateRequest` 新增 `category_id`、`SysUserItem`/`UserInfo` 新增 `category_id`/`category_name`；`user_service.create_user` 客户分支改为校验客户单位并按 `category_id` 落库，`_user_info` 直接由 `category_id` 取 `company_name`，`list_users` 展示公司名；三处隔离逻辑（`project_service._resolve_user_category_id` / `retriever._resolve_user_category_id` / `ai_service._resolve_identity`）直接 `current_user["category_id"]` 取值，不再溯源对接人；`dependencies.get_current_user` SQL 列清单补 `category_id`；`main.py` 新增 `_migrate_user_category_id()` 幂等回填存量客户账号的 `category_id`。
- **AI 助手数据供给改造（V1.4.16）**：去掉「中文关键词切分 + SQL LIKE 匹配」与「联网搜索」，改为**结构化文本知识库全量注入**。`services/llm/retriever.py` 重写为 `build_knowledge_base(db, current_user) -> (context, sources)`——每次提问实时读库，把当前用户可见的**全部项目**（进行中 + 已归档，已归档标注「已结项」）渲染成固定模板文本（项目名称 / 客户单位 / 对接人 / 我方负责人·设计师 / 立项时间 / 预计结束时间 / 项目状态），对接人/设计师用 `IN_` 批量查询避免 N+1；**客户账号 SQL 层 `WHERE category_id == 所属单位` 精确隔离，员工全量**。`ai_service.chat_stream` 知识库为空时短路返回固定话术（不调 LLM）；`_build_messages` 知识库拼在 system 层（每次请求重建只发一次，历史层仅存问答文本不重复注入）。`deepseek.py` 删除 `/responses` 联网路径仅留 `/chat/completions`；`base.py`/`schemas/ai.py`/`routers/ai.py` 摘除 `web_search` 契约。接口与库结构无变化。

## 目录结构

```
app/
├── main.py            # FastAPI 入口：CORS、/uploads 挂载、SPA 回退、异常注册、路由注册、启动迁移
├── config.py          # 环境变量（DB_URL / JWT_SECRET / UPLOAD_DIR / CORS）
├── database.py        # engine / SessionLocal / Base
├── dependencies.py    # get_db / get_current_user / require_roles / require_not_customer
├── models/            # 13 个模型文件（23 张表，V1.4.8 新增 ai_config/ai_conversation/ai_message）
├── schemas/           # Pydantic V2 DTO（camelCase 别名）
├── services/          # 业务逻辑（模板实例化 ID 映射、级联删除、消息推送、权限迁移、AI 流式对话等）
├── routers/           # 18 个模块路由
└── utils/             # JWT / 全局异常
tests/                 # 各版本自检脚本（见下）
```

## 自检脚本

> **测试现状（V1.4.18 实测）**：`full_flow_check.py` 全流程回归 **92/92 通过**、`check_cover_api.py` **7/7 通过**、`check_customer_cover_api.py` **9/9 通过**。下列历史检查点脚本部分因接口演进（V1.4.7 客户单位 / V1.4.15 用户绑定单位 / V1.4.17 部门角色解耦）后未同步更新，**仅存档**，运行可能报错。

```bash
# ---- 当前有效（实测通过）----
python tests/full_flow_check.py             # ✅ 全流程回归（需后端已启动，92/92 通过）
python tests/check_cover_api.py             # ✅ 项目封面（7/7 通过）
python tests/check_customer_cover_api.py    # ✅ 客户封面（9/9 通过）

# ---- 历史检查点（接口演进后未同步，仅存档）----
python tests/check_step5_services.py        # ⚠️ Service 层检查点（V1.4.4 时代）
python tests/check_step6_api.py             # ⚠️ API 层检查点（需 httpx）
python tests/check_dept_client_api.py       # ⚠️ 部门体系 + 客户门户
python tests/check_dept_role_split.py       # ⚠️ 部门-角色解耦
python tests/check_role_simple.py           # ⚠️ 角色二分
python tests/check_role_api.py              # ⚠️ 角色 API
python tests/check_node_icon_form.py        # ⚠️ 节点图标 + 表单（HTTP 版）
python tests/check_icon_form_tc.py          # ⚠️ 节点图标 + 表单（TestClient 版）
```

> 说明：`full_flow_check.py` 走真实 HTTP 请求，需先启动后端（默认 `http://127.0.0.1:8000`），会自动清理以「全流程测试」为前缀的数据。

## 统一约定

- 返回格式：`{code, msg, data}`，HTTP 状态固定 200，业务码在 body.code
- 错误码：200 成功 / 400 业务拦截 / 401 未登录 / 403 无权限 / 500 服务器错误
- 鉴权：请求头 `Authorization: Bearer <token>`，JWT HS256，24 小时过期
- 已归档项目除查询外一切写入返回 400
