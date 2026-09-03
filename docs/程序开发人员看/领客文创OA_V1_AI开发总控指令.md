# 青岛领客文化传播｜项目流程管理 OA V1.4.16 全栈开发总控指令 (Master Prompt)

> **给 AI 编程助手（Cursor / Claude / Copilot / 豆包）的指令**：  
> 请严格根据同目录下的文档完成全栈项目的完整代码实现：
>
> - `领客文创OA_V1_PRD.md` — 产品需求 + 技术规范 + 前端布局
> - `领客文创OA_V1_Database.md` — 23张表结构（含 sys_dept/sys_role/project_contact_rel/ai_config/ai_conversation/ai_message）+ 索引 + 模板实例化规则
> - `青岛领客文创OA_V1_后端接口清单.md` — 接口完整入参/返回/业务规则
> - `领客文创OA_启动与使用指南.md` — 启动方式、数据库切换、模块使用说明
> - `领客文创OA_V1_数据库互转与MySQL部署指南.md` — SQLite/MySQL 互转与服务器部署
>
> 不得擅自删减业务规则，不得遗漏异常边界处理。本文件是总控入口，具体细节以文档为准。
>
> **工程约束（V1.4.4 起硬性要求）**：
>
> 1. **禁止在代码或配置中出现任何机器相关的绝对路径**（如 `C:/Users/xxx/...`）。所有路径一律相对写法，由代码按 `__file__` 解析为项目内绝对路径——保证项目文件夹复制到任意机器可直接运行。
> 2. **数据库结构靠启动期自愈迁移升级**（`auto_add_missing_columns`），新增模型列时**不要**写手工迁移脚本给用户执行。需要按业务规则回填存量数据的（如 V1.4.7 `_migrate_project_category`），追加到 `main.py` 的启动迁移函数里，保持幂等。

---

## 一、技术栈与依赖（精确到库）

### 后端依赖（requirements.txt）

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
PyJWT>=2.8.0
PyMySQL>=1.1.0
cryptography>=42.0.0
openpyxl>=3.1.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
```

- SQLAlchemy 使用 **2.0 Declarative Base** 风格
- Pydantic 使用 **V2** 语法（`model_config`、`Field`、`@field_validator`）
- 数据库默认 **SQLite**（无需驱动，随项目走），也支持 MySQL（驱动 PyMySQL 同步）；连接串由 `.env` 的 `DB_URL` 决定
- Excel 导出用 **OpenPyXL**
- JWT 用 **PyJWT**

### 前端依赖（package.json）

```
vue@^3.4.0
vue-router@^4.3.0
pinia@^2.1.0
element-plus@^2.6.0
@vue-flow/core@^1.33.0
@vue-flow/background@^1.3.0
@vue-flow/controls@^1.1.0
@vue-flow/minimap@^1.5.0
axios@^1.6.0
```

---

## 二、工程配置红线

### 后端

1. **服务端口**：`8000`
2. **CORS**：开发环境允许 `http://localhost:5173`，生产环境按需配置
3. **静态挂载**（`app/main.py`）：
   - 挂载 `/uploads` → `./uploads/` 目录（附件访问）
   - 生产环境挂载 `/` → `frontend/dist/`，**SPA 路由回退**：未匹配路径返回 `index.html`（避免刷新前端路由 404）
4. **全局异常捕获**：
   - 自定义 `BusinessException`（code + msg），全局异常处理器统一返回 `{code, msg, data:null}`
   - 未捕获异常返回 500，不暴露堆栈信息
5. **JWT**：密钥从 `.env` 读取（`JWT_SECRET`），过期时间 24 小时，算法 HS256
6. **依赖注入**：`get_db()` 提供数据库会话，`get_current_user()` 解析 token 返回当前用户

### 前端

1. **开发端口**：`5173`
2. **Vite proxy**（`vite.config.js`）：开发环境将 `/api` 和 `/uploads` 转发到 `http://localhost:8000`
3. **Axios 拦截器**：
   - 请求拦截：自动注入 `Authorization: Bearer <token>`
   - 响应拦截：`code === 200` 返回 `data`；`code !== 200` 用 `ElMessage.error(msg)` 弹窗；`code === 401` 清除 token + Pinia，跳转 `/login`
4. **路由守卫**：未登录跳 `/login`；无权限菜单不显示，直接输 URL 跳首页
5. **Pinia**：`userStore`（token + userInfo 持久化到 localStorage）、`messageStore`（未读数）

---

## 三、关键业务逻辑避坑红线（必须严格执行）

> 以下是最容易出错的 7 个点，AI 生成代码时必须逐条对照。详细规则见三份文档。

### 1. 模板实例化时的连线 ID 映射（最核心）

- 复制模板创建新项目时，新节点会生成全新自增 ID
- 后端 Service 层必须在内存中维护 `Map<old_template_node_id, new_project_node_id>`
- 插入 `project_node_edge` 连线时，强制将 `source_node_id` / `target_node_id` 重映射为新节点 ID 后再插入
- 全部在一个数据库事务内完成

### 2. 删除防误删与级联事务

- **删除客户单位（V1.4.7 原"客户分类"）**：先查 customer 表（存在对接人）与 project.category_id（存在项目），任一关联则返回 400
- **删除对接人（V1.4.7 原"客户"）**：先查 project.customer_id 与 project_contact_rel，存在关联项目则返回 400
- **删除项目**：已归档项目返回 400 "已归档项目请先取消归档后再删除"；进行中项目单事务级联删除节点、连线、表单值、附件（含磁盘文件）、评论、设计师关联、项目消息
- **删除节点**：单事务级联删除该节点的出入连线、表单值；节点下附件不自动删（保留在项目中）
- **用户默认仅启用/停用；管理员可物理删除**（不能删自己、不能删初始 admin）；删除后历史关联保留 user_id、姓名兜底"已删除用户"

### 3. 归档状态全局硬拦截

- 项目状态为「已归档」时，除查询接口外，所有写入操作统一返回 400 "项目已归档，禁止修改任何内容"
- 前端画布设置 `nodesDraggable="false" nodesConnectable="false"`，表单全部 `disabled`
- 建议在 Service 层封装 `check_project_archived(project_id)` 统一校验

### 4. 附件与评论删除权限隔离

- 删除附件：`attachment.upload_user_id == current_user.id` 或 `current_user.role == "管理员"` 可删，否则返回 403 "无权删除他人附件"
- 删除评论：强制校验 `comment.create_user_id == current_user.id`，否则返回 403 "无权删除他人评论"
- 归档项目禁止附件和评论的增删

### 5. 消息中心自动通知

- 触发事件：节点新增/修改/删除、表单填写修改、发表评论
- 推送范围：项目创建人（`create_user_id`）+ 项目关联设计师（`project_designer_rel`），**排除操作人自己**
- 批量写入 `message` 表，`is_read=0`，携带 `project_id`（前端点击跳转用）
- 消息内容模板见 Api.md 附录

### 6. 统一响应与错误码

```json
{ "code": 200, "msg": "", "data": {} }
```

| code | 含义             |
| ---- | -------------- |
| 200  | 成功             |
| 400  | 参数错误 / 业务规则不满足 |
| 401  | 未登录 / token 失效 |
| 403  | 无权限            |
| 500  | 服务器内部错误        |

### 7. 画布坐标与批量更新

- 节点坐标用 `decimal(10,2)`（pos_x, pos_y），支持浮点数，避免缩放拖拽后重绘抖动
- 前端拖拽结束后**防抖**调用批量更新接口 `POST /api/projectNode/batchUpdatePositions`（入参 `[{id, posX, posY}]`），不要每次移动都发单条请求
- 批量更新不触发消息推送（仅坐标变化）

### 8. 节点模板库与表单定义收口（V1.3/V1.4）

- 画布（项目与流程模板）**只能从节点模板库（node_template）选类型新增节点**，不允许自由创建节点类型
- **表单定义唯一来源是节点模板库**：节点模板的 form_fields（JSON 数组）在节点实例化时值拷贝到 project_node_form_value（含下拉选项 select_options 冗余）
- 流程模板是**纯流程编排**（节点 + 连线），不存表单；flow_template_node 通过 node_template_id 关联节点模板
- 节点新增接口 `POST /api/projectNode/add` 入参必填 `nodeTemplateId`，标题/备注/表单均取自节点模板

---

## 四、标准代码生成步骤（按顺序执行）

### 第 1 步：数据库初始化

- **默认 SQLite**：后端启动时用 SQLAlchemy `Base.metadata.create_all` 自动建 **23 张表** + 初始管理员 `admin / admin123`（无需手写 SQL）
- 如需 MySQL：改 `.env` 的 `DB_URL`，同样 `create_all` 自动建表（`init.sql` 可作为 MySQL 手动建表参考）
- SQLite 注意：索引名需全库唯一，代码须给索引名加表名前缀（见 Database.md）
- 23 张表（含 2 张连线表 + 1 张节点模板表 + 1 张项目-对接人关联表 + 3 张 AI 助手表），无物理外键，索引见 Database.md

### 第 2 步：后端基础层

```
app/config.py          # 环境变量配置（DB_URL、JWT_SECRET、UPLOAD_DIR）
app/database.py        # SQLAlchemy engine、SessionLocal、Base
app/dependencies.py    # get_db()、get_current_user()
app/utils/jwt.py       # JWT 签发与校验
app/utils/exceptions.py # BusinessException + 全局异常处理器
app/main.py            # FastAPI 实例、CORS、静态挂载、异常注册、路由注册
```

### 第 3 步：后端 ORM 模型（app/models/）

按 Database.md 生成 23 个模型类，字段名与表结构严格对应。

### 第 4 步：后端 Pydantic DTO（app/schemas/）

按 Api.md 每个接口的入参/返回生成对应的 Request / Response 模型。

### 第 5 步：后端业务逻辑（app/services/）

重点实现：

- `template_service.py` — 模板实例化（ID 映射 + 值拷贝，单事务）
- `project_service.py` — 项目级联删除、归档校验
- `node_service.py` — 节点级联删连线、批量坐标更新
- `message_service.py` — 消息自动生成（推送范围过滤）
- `file_service.py` — 文件上传（日期隔离 + UUID）、删除磁盘文件
- `excel_service.py` — 项目列表导出
- `ai_service.py` — AI 助手会话/消息 CRUD + 流式对话编排（SSE），配合 `services/llm/`（Provider 抽象 + DeepSeek 实现 + 结构化知识库注入）

### 第 6 步：后端路由（app/routers/）

按 Api.md 18 个模块生成路由，每个路由调用对应 Service，统一返回格式。

### 第 7 步：前端基础框架

```
src/utils/request.js   # Axios 实例 + 拦截器
src/utils/auth.js      # token 存取
src/stores/user.js     # Pinia 用户状态
src/stores/message.js  # 消息未读数
src/router/index.js    # 路由定义 + 守卫
src/layouts/MainLayout.vue  # 顶部主导航 + 用户下拉（V1.4 去掉侧边栏）
src/App.vue
src/main.js
vite.config.js         # proxy 配置
```

### 第 8 步：前端公共组件

```
src/components/FlowCanvas.vue       # @vue-flow 封装（自定义节点、工具条、小地图）
src/components/CustomFlowNode.vue   # 文创卡片节点（序号+标题+徽章+备注摘要）
src/components/DynamicForm.vue      # 动态表单渲染器（根据 field_type 渲染输入框/文本域/下拉）
```

### 第 9 步：前端页面

按 PRD.md 第 9 章页面清单生成全部页面，重点是：

- `views/dashboard/Index.vue` — 首页（创建项目卡片 + 最近项目）
- `views/project/Detail.vue` — 画布详情页（顶部栏 + 左侧画布 + 右侧双态面板）
- `views/template/Edit.vue` — 模板画布编辑页（纯流程编排，整图提交保存）
- `views/files/Index.vue` — 文件管理页（左项目右文件）

---

## 五、交付物清单

### 后端（backend/）

- [x] init.sql（19张表 + 初始数据，含 sys_dept/sys_role；V1.2 起全部完成）
- [x] requirements.txt
- [x] .env.example
- [x] app/ 全部分层代码（config / database / dependencies / models / schemas / services / routers / utils / main）
- [x] README.md（启动说明：创建数据库、执行 init.sql、配置 .env、pip install、uvicorn 启动）

### 前端（frontend/）

- [x] package.json
- [x] vite.config.js（proxy 配置）
- [x] src/ 全部代码（api / utils / stores / router / layouts / components / views）
- [x] README.md（启动说明：npm install、npm run dev、npm run build）

---

## 六、AI 生成时的自检清单

生成完成后，逐条自检：

- [ ] 模板实例化是否实现了 ID 映射？连线的 source/target 是否重映射？
- [x] 删除客户单位/对接人时是否先查关联数据并拦截？（V1.4.7 已实现：单位查 customer 与 project.category_id；对接人查 project.customer_id 与 project_contact_rel）
- [ ] 删除项目时是否单事务级联删除所有子数据 + 磁盘附件文件？
- [ ] 删除节点时是否级联删除出入连线？
- [ ] 已归档项目的所有写入接口是否统一拦截？
- [ ] 附件/评论删除是否校验了本人权限？
- [ ] 消息推送是否排除了操作人自己？
- [ ] 节点坐标是否用 decimal(10,2)？是否有批量更新接口？
- [ ] 所有接口是否统一返回 `{code, msg, data}`？
- [ ] 前端 Axios 拦截器是否处理了 401 跳登录？
- [ ] 生产环境是否配置了 SPA 路由回退？
- [ ] 全局异常是否统一捕获，不暴露堆栈？

---

## 七、版本迭代记录（2026-09-01）

- **V1.2（基线，9 步全部完成）**：16 表 + 后端全层 + 前端全部页面，真库端到端联调通过。
- **V1.3（UI 优化 + 新增模块）**：设计 Token/响应式/交互体验/性能可访问性 4 阶段；节点模板库（node_template + form_fields）；项目封面；自定义角色（sys_role）；404 页、消息轮询等。
- **V1.4（部门体系 + 客户门户）**：新增 `sys_dept`（部门仅组织分组）；客户账号（一客户多账号，登录进入独立只读门户，项目列表/详情客户隔离、写操作 403 硬拦截）；项目列表 `progressPercent` 进度占比；`require_not_customer` 依赖。
- **V1.4.1（部门-角色解耦）**：部门不再携带权限（role 列保留弃用）；建用户 = 选部门 + 分配角色；新增 `POST /api/sysUser/update` 编辑用户；启动幂等迁移 `migrate_dept_role_to_user`。
- **V1.4.2（角色简化）**：内部员工角色仅「普通 / 管理员」；业务写权限全部收敛为仅管理员；迁移 `migrate_legacy_roles`（设计师/设计总监/行政 → 普通，admin 强制管理员）。
- **V1.4.3（节点图标 + 表单图像/链接 + 登录页）**：`node_template.icon`/`project_node.icon`（预设 20 图标 + 自定义上传 `node_icon/`）；表单字段类型 `image`/`link`（`formImage/upload` → `node_form/`）；登录页大改版、全站品牌 LINK；数据库曾迁至 `C:/Users/Administrator/.workbuddy/linkoa-data/app.db`（V1.4.4 已迁回项目内）。
- **V1.4.4（便携化 + 结构自愈 + 缺陷修复）**：
  - **路径便携化**：`.env` 的 `DB_URL` 改为 `sqlite:///./linkoa.db`，数据库回到项目内 `backend/linkoa.db`；清理 `switch_db.py`/`migrate_*.py`/测试脚本中全部旧机器绝对路径，项目文件夹复制到任意 Windows 机器（装了 Python）双击 `start.bat` 即可运行。
  - **启动期结构自愈迁移**：`app/database.py` 新增 `auto_add_missing_columns()`，`main.py` 启动流程在 `create_all` 前调用；自动比对 ORM 模型与实际库列，缺失列 `ALTER TABLE ADD COLUMN` 补齐。修复了老库缺 `node_template.icon`/`project_node.icon` 导致编辑流程/节点模板 500 的问题，同类问题不再复发。
  - **连线端点校验修复**：模板连线与项目连线原用「集合长度 = 2」判断，节点自环时被误报「连线引用了不存在的节点」；改为按端点存在性逐个校验。
  - **审计补全**：模板连线接口原写死操作人 0 且无日志，改为传真实用户并写审计日志。
  - **图片上传加固**：新增 `app/utils/images.py` 魔数校验，项目/客户封面上传校验真实文件头（jpg/png/webp），伪造 Content-Type 的文件返回 400。
  - **回归体系**：新增 `backend/tests/full_flow_check.py`，走真实 HTTP 覆盖 17 个模块 68 项断言。
- **V1.4.5（品牌与文案统一 + 前端缺陷修复）**：
  - **品牌统一**：登录页改为 logo 图（`frontend/public/link-icon.png`）+「青岛领客文化传播有限公司」，去掉 LINK 大字与「IP 文创项目流程管理系统」标语；顶部导航与窄屏抽屉去掉 Brush 图标仅保留 LINK 文字；浏览器标签页标题改为 `页面 - 领客文创`；客户门户页头改为 logo 小图 +「领客文化 · 客户门户」；工作台欢迎语改为「开始管理你的项目」。
  - **放大镜修复**：`DynamicForm.vue` 中图片悬停遮罩的 ZoomIn 图标只有 `@click.stop` 未绑处理函数，导致点击无反应；改为给 `el-image` 加函数 ref 存入 `imageRefs[fieldId]`，点击时调用 `imageRefs[id]?.showPreview()`。
  - **构建清理**：`vite.config.js` 的 `emptyOutDir: false` 导致 dist 累积多次历史构建产物，改为全量清理后重建。
- **V1.4.6（登录安全增强 + 登录页体验优化）**：
  - **防暴力破解**：`SysUser` 新增 `login_fail_count` / `locked_until` 两列（启动期 `auto_add_missing_columns` 自动补列）；`user_service.login` 连续失败 5 次锁定 10 分钟，登录成功清零，锁定期间拒绝登录；账号不存在时不累加（防枚举）。新增 `POST /api/sysUser/unlock` 管理员手动解锁接口。
  - **登录页（前端）**：`views/login/Index.vue` 重写——左右分栏品牌区 + 登录卡；错误改为表单内联提示（不再全局 alert）；密码显隐、记住账号仅存用户名；输入框聚焦/错误态高亮；页脚版权/版本号；移动端上下布局。`utils/request.js` 新增 `{ silent: true }` 跳过全局错误弹窗。
  - **用户管理**：账号锁定态显示「已锁定」标签与「解锁」按钮。
- **V1.4.7（客户单位/对接人模型 + 门户重构 + 节点顺序修复）**：
  - **数据模型**：`Project` 新增 `category_id`（归属客户单位）+ 新表 `project_contact_rel`（项目-对接人多对多）；`project.customer_id` 语义变为「首位对接人」（兼容保留）。启动期新增幂等迁移 `_migrate_project_category()`：为 `category_id` 为空的历史项目按老客户回填单位并补关联记录。
  - **接口**：`project/create`、`project/updateBase` 入参改为 `categoryId`（必填）+ `contactCustomerIds`（必填 ≥1，须属该单位）；`project/list` 支持 `categoryId`/`createTimeStart`/`createTimeEnd` 筛选；`project/detail` 返回 `contactList` 且节点按 `posX→posY→sort→id` 排序；`report/exportProject` 筛选由 `customerId` 改 `categoryId`，导出列改为「项目名称/客户单位/客户对接人/参与设计师/立项时间/预计结束时间/项目状态」；登录返回 `companyName`。
  - **前端**：项目列表/详情新建编辑弹窗改为「选客户单位 → 多选对接人」两级联动；客户库文案整体改为「客户单位/对接人」；用户管理客户账号按单位分组选对接人。
  - **客户门户**：去节点进度/总进度，卡片与详情改为展示客户单位、我方设计师、客户对接人、立项时间、预计结束时间 + 倒计时；新增项目名称搜索、进行中/已结项（已归档）筛选、立项时间范围筛选；门户按客户单位隔离（可见同单位全部项目）；顶栏展示公司名。
  - **回归**：`full_flow_check.py` 升级至 84 项断言（新增单位/对接人字段、门户隔离、门户筛选、节点按画布位置排序校验）。
- **V1.4.8（AI 助手「青青侠」）**：
  - **数据模型**：新增 `ai_config`（AI 全局配置，单行：system_prompt/model/api_key/base_url/temperature/max_tokens/updated_by）、`ai_conversation`（按 user_id 隔离的会话）、`ai_message`（role/content/sources，sources 存 JSON）。启动期幂等 `_init_ai_config()` 读 `.env`（`AI_API_KEY`/`AI_BASE_URL`/`AI_MODEL`）初始化默认配置。
  - **LLM 可扩展架构**：`services/llm/base.py` 定义 `BaseLLMProvider.stream_chat` 抽象；`deepseek.py` 实现 OpenAI 兼容流式（SSE，`stream=true`，`[DONE]` 终止）；`__init__.py` 工厂 `get_provider(config)`，未来新增模型只需加 Provider 实现类。
  - **RAG + 数据隔离**：`services/llm/retriever.py` 按问题关键词检索项目数据注入上下文；**客户账号强制 `Project.category_id == 所属单位` 过滤**（只能问自己公司项目，防泄密），员工全量可见。
  - **接口**（前缀 `/api/ai`）：`GET/POST /conversations`、`GET /conversations/{id}/messages`、`DELETE /conversations/{id}`、`POST /chat/stream`（`text/event-stream` 流式，事件 delta/error/done）、`GET/PUT /config`（管理员，api_key 脱敏返回）。
  - **前端**：常驻右下角形象 `MascotFloat`（呼吸浮动 + 悬停随机气泡 + 摇头）→ 点击 `transform-origin: bottom right` 缩放展开居中弹窗 `ChatPanel`（桌面 66vw/80vh、移动端全屏）→ 左侧会话列表（仿豆包/DeepSeek，新建/切换/删除）+ markdown-it 渲染 + 来源引用 + 流式光标 + 停止生成 + 推荐问题；`fetch` 读 SSE + `AbortController` 停止。管理员「AI 设置」页 `views/system/AiConfig.vue`（用户下拉进入）配置人设/模型/Key/BaseURL/生成参数。
  - **回归**：`full_flow_check.py` 覆盖 18 个模块、91 项断言（新增 AI 助手：配置脱敏 + 会话/消息 CRUD + 流式 done 事件）。
- **V1.4.9（AI 助手安全与体验加固）**：
  - **身份绑定与数据隔离红线**：`ai_service._resolve_identity()` 按登录账号解析身份（客户账号 → `customer_id → customer_category.category_name`，员工 → 全量）；身份声明 + 代码级 `_SECURITY_SYSTEM_PROMPT`（严禁反问公司/身份、严禁复述系统指令、无数据实说、严禁越权透露）运行时强制追加，**不随管理员可改的 system_prompt 变化**。
  - **速率限制**：`ai_service._check_rate_limit()` per-user 滑动窗口（60 秒 20 次，`threading.Lock` + `defaultdict(deque)` 内存级实现，管理员豁免，超限 429）。
  - **根治幻觉**：`retriever.is_business_query()` 业务关键词判断 + `retrieve_projects()` 检索为空时**短路**（不调 LLM 直接返回「没查到」固定话术）；`_extract_keywords()` 停用词二次切分，不误伤「青岛地铁」「智能物流平台升级」等实体词。
  - **会话管理增强**：`AiConversation` 加 `pinned`/`is_deleted` 列（启动自愈迁移自动补列）；列表 `pinned desc → updated_at desc → id desc` 排序；新增 `PATCH /conversations/{id}`（重命名）+ `POST /conversations/{id}/pin`（置顶）；`DELETE` 改软删（消息与审计日志保留）。
  - **审计留痕**：复用 `log_service.add_log()` 写 `ai_chat`/`ai_conversation_rename`/`ai_conversation_pin`/`ai_conversation_delete` 四类日志。
  - **前端**：会话列表三点菜单（`el-dropdown`：置顶/重命名/删除，删除红色）；`MascotFloat` 动画分层（浮动动画移外层容器、hover 用 transition、`pointerenter/leave`）修复位移频闪；来源标注（引用/未引用）；推荐问题角色分层（`mascot.js` 客户视角）。
  - **自检**：新增 `backend/tests/ai_full_check.py`（虚拟数据 + mock LLM，23 项，覆盖隔离/防幻觉/审计/限流/软删/关键词）+ `backend/tests/mock_llm.py`（OpenAI 兼容 SSE mock，供回归免真实 API）。
- **V1.4.10（AI 联网搜索）**：
  - **开关**：`ChatStreamRequest` 加 `web_search`（bool，默认 false），`chat/stream` 入参 `webSearch`；前端 `ChatInput` 加「联网搜索」胶囊开关，`api/ai.js`/`stores/ai.js` 透传。
  - **双路径**：`DeepSeekProvider.stream_chat(..., web_search)` 分流——`web_search=False` 走原 `/chat/completions`；`True` 走 **Responses API**（`{base_url}/responses`），请求体 `instructions`（合并 system）+ `input`（对话 item）+ `tools=[{"type":"web_search"}]` + `tool_choice: auto` + `max_output_tokens`；解析 SSE 事件 `response.output_text.delta`（取 `delta` 字段），结束事件 `response.completed/incomplete/failed`（无 `[DONE]`）。
  - **模型升级**：`deepseek-chat`/`deepseek-reasoner` 已于 2026/07/24 弃用 → 升级 `deepseek-v4-flash`（Responses API 支持 web_search）。改 `config.py` 默认值、`models/ai.py` 默认值、`.env`；`_init_ai_config()` 幂等回填存量 `deepseek-chat|deepseek-reasoner` → `deepseek-v4-flash`。
  - **安全边界**：联网仅补最新/公开信息；`_build_messages` 联网时追加提示「内部项目/客户/进度仍以本地为准，禁止用联网结果编造业务数据」；业务短路逻辑（本地无数据）不受联网开关影响。
  - **自检**：`ai_full_check.py` 增补联网搜索用例（mock LLM 校验 webSearch 分流与 Responses 请求体）；`full_flow_check.py` 回归。
- **V1.4.11（AI 助手 BUG 修复与健壮性）**：
  - **三点菜单层级 BUG 修复**：`ConversationList.vue` 的 `el-dropdown` 由 `:teleported="false"` 改 teleport 到 body；`AiAssistant.vue` 面板 `z-index` 由 2100/2090 降至 1950（低于 Element Plus 弹层默认 2000），根治删除/重命名下拉、tooltip、`ElMessageBox` 被面板遮挡「看不见」的 BUG；移动端 `.conv-more` 由 `display:none`（仅 hover 显示）改常驻，触屏可点出三点菜单。
  - **移动端适配**：`ChatPanel.vue` 抽屉内执行删除/重命名后自动关闭面板；`100vh`→`100dvh` 修复 iOS Safari 地址栏导致的面板溢出。
  - **输入法组词误发（严重）**：`ChatInput.vue` 发送由 `@keydown.enter.exact.prevent` 改监听 `keyup` + `e.isComposing` 判断，避免中文选词时按 Enter 直接把半成品句子发出去。
  - **滚动与流式**：`MessageList.vue` 滚动监听由仅依赖「最后一条内容」改依赖 `messages.length`（切换会话/流式增量稳定滚到底）；`stores/ai.js` 的 `openConversation`/`removeConversation` 增加 `stopStreaming()` 调用，切换或删除会话时中断当前流式请求，修复 `streaming` 卡死导致输入框长期禁用。
  - **文件删除健壮性**：`file_service.remove_disk_file` 的 `except OSError` 改 `except Exception`，物理文件删除失败不阻断业务（DB 字段先更新再删文件）。
  - **回归脚本自愈**：`full_flow_check.py` 的 `check()` 加 `resp.json()` 解析保护（空响应不再崩溃中断）；新增表驱动前置清理（依赖倒序），可重复运行自愈残留，修复「残留累积→重名冲突→再崩溃」死循环。
  - **自检**：`ai_full_check.py` 28 项 + `full_flow_check.py` 91 项全绿；版本号 V1.4.11。
- **V1.4.12（CRUD 未保存数据丢失修复）**：
  - **根因**：全站此前无离开守卫/未保存提示；项目详情页编辑节点 A 表单后直接点节点 B，`onNodeClick` 重设 `formFields` 触发 `DynamicForm` 的 `watch(props.fields)` 重置 `values`，A 的未保存编辑被静默覆盖丢失。
  - **`DynamicForm.vue`**：新增 `initialSnapshot` ref + `isDirty` computed（对比初始快照判断脏）；`defineExpose({ collect, isDirty, markClean })`，`markClean()` 保存成功后重置基准，避免保存后重复弹提示。
  - **`views/project/Detail.vue`**：新增 `guardUnsaved(message, confirmText)` 统一拦截，基于 Element Plus `distinguishCancelAndClose` 区分三态（confirm=保存并继续 / cancel=放弃修改 / X·ESC=中止）；在 `onNodeClick`（切节点）、`onDeselect`（点画布空白+面板关闭按钮）、`onAddPreset`/`onAddConnected`（新增节点）、`onArchive`（归档前）四处调用；并新增 `onBeforeRouteLeave` 页面级离开守卫；`saveSelectedNode()` 与 `onSaveForm()` 保存后调 `markClean()` 清脏。
  - **验证**：`vite build` 成功；停后端→重建→重启（8000 监听，HTTP 200）。纯前端交互修复，后端契约无变化。
- **V1.4.13（AI 助手检索与富上下文优化）**：
  - **根因**：`retriever._extract_keywords` 停用词表不全，意图功能词（关于/找/看下/按/时间/排序…）与实体词粘死或冒充关键词 → LIKE 落空；且关键词落空后不回退全量列表 → 触发「没查到」短路。上下文只拼 7 个字段，答不了进度/负责人/倒计时/紧急度。
  - **修复**：`retriever.py` 补全停用词表 + 新增 `_detect_intent`（查实体/全局列表/统计三类）+ 关键词落空回退「全量进行中列表」+ `_compute_stats`（总数/今年立项数/进行中数/已归档数）+ `_build_rich_context`（负责人=我方设计师、当前节点+进度%、剩余/逾期天数、紧急度排序）。
  - **红线不变**：客户账号按 `category_id == 本人所属单位` 隔离；`ai_service` 的 `if not context and is_business_query` 防幻觉短路保留。
  - **验证**：QA 独立验证 7 条全过 + 新增 `tests/qa_retriever_verify.py`（32 项）+ `ai_full_check.py` 30 项 + `full_flow_check.py` 91 项全绿。纯后端改动，前端与库结构无变化。
- **V1.4.16（AI 助手数据供给改造：关键词检索 → 结构化知识库全量注入）**：
  - **动机**：原「中文关键词切分 + SQL LIKE 匹配」检索一旦用户表达的意思不在关键词内就落空 → 回答为空/被「没查到」短路；「联网搜索」亦非内部业务数据所需。
  - **数据供给重构**：`services/llm/retriever.py` 整体重写为 `build_knowledge_base(db, current_user) -> (context, sources)`——每次提问实时读库，把当前用户可见的**全部项目**（进行中 + 已归档，已归档标注「已结项」）渲染成固定模板文本（项目名称 / 客户单位 / 对接人 / 我方负责人·设计师 / 立项时间 / 预计结束时间 / 项目状态）注入大模型；对接人/设计师 `IN_` 批量查询避免 N+1；时间空显示「未设置」、设计师空「未分配」、对接人空回退首位再「未设置」。
  - **数据隔离红线**：`build_knowledge_base` 内**客户账号 SQL 层 `WHERE Project.category_id == 所属单位` 精确过滤**（只注入本公司项目），员工全量注入。
  - **编排层**：`ai_service.chat_stream` 改为「`build_knowledge_base` → 知识库为空短路返回固定话术（不调 LLM）→ `_build_messages` 拼入 system 层 → `provider.stream_chat`」；知识库拼在 system 层（每次请求重建只发一次），历史层仅存问答文本，连续多轮不重复注入。
  - **摘联网**：`deepseek.py` 删除 `/responses` 路径仅留 `/chat/completions`；`base.py` 抽象 `stream_chat` 去掉 `web_search`；`schemas/ai.py` 的 `ChatStreamRequest`、`routers/ai.py` 的 `chat_stream` 摘除 `web_search`；前端 `ChatInput/ChatPanel/stores/api` 移除「联网搜索」开关与 `webSearch` 透传。
  - **自检**：`qa_retriever_verify.py` 重写为 `build_knowledge_base` 行为证明（30 项）+ `ai_full_check.py` 19 项 + `full_flow_check.py` 92 项全绿。接口与库结构无变化。
