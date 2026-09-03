# LINKOA 项目长期记忆

## 路径规范（用户明确要求）
- 所有启动/配置路径必须用**相对路径**，禁止写死绝对路径。`backend/.env` 的 `DB_URL` 用 `sqlite:///./linkoa.db`，config.py 自动转成 backend/ 下绝对路径。曾因 .env 残留旧机器绝对路径导致启动报 `sqlite3.OperationalError`，已修。

## 品牌规范
- 公司全称「青岛领客文化传播有限公司」（登录页主标题）；标签页标题后缀「领客文创」；顶栏保留「LINK」纯文字（无图标）；客户门户「领客文化 · 客户门户」。logo=`frontend/public/link-icon.png`。**严禁**再用「IP 文创项目流程管理系统」作系统名/标语。

## 版本与文档
- 当前版本 **V1.4.16**（AI 助手数据供给改造，见下）。每次改动后需同步 **8 份 MD**：README(根)、backend/README、frontend/README、启动与使用指南、后端接口清单、PRD、Database、MySQL 互转与部署指南、AI 开发总控指令（实际 9 个文件）。
- 文档/代码版本、DB 路径、品牌文案三者一致；改后 grep `Administrator` / `IP 文创项目流程管理系统` / `LINK · 客户门户` 校验无残留。
- **升版版本号散落点**：`frontend/src/views/login/Index.vue`(`const version`)、`backend/app/main.py`(`FastAPI(version=...)`)、8 份 MD 标题与正文。grep 旧值（如 `1.4.15`）校验收口。
- 数据库结构升级靠启动期自愈迁移（`database.py auto_add_missing_columns`），新增模型列不写手工迁移脚本；需按业务回填存量的追加到 `main.py` 启动迁移函数（幂等）。

## 客户数据模型
- **customer_category=客户单位(公司)，customer=对接人(人)**；项目归属单位存 `project.category_id`，对接人多对多存 `project_contact_rel`，`project.customer_id`=首位对接人（兼容）。
- 项目 create/updateBase 入参：`categoryId`(必填)+`contactCustomerIds`(必填≥1)。**字段命名坑**：后端必须叫 `contact_customer_ids`（camelCase=contactCustomerIds）。
- 门户隔离按**客户单位**：客户账号看同单位全部项目；门户不展示节点进度，展示立项时间+预计结束时间+倒计时；已归档→「已结项」；登录返回 companyName。
- 节点时间线按画布位置排序 `pos_x→pos_y→sort→id`。
- **客户账号绑公司（V1.4.15）**：`sys_user.category_id` 直绑公司，`customer_id` 兼容保留；隔离逻辑直取 `category_id` 不再溯源对接人。

## AI 助手「青青侠」核心架构
- 三张表：`ai_config`(单行配置)/`ai_conversation`(user_id 隔离)/`ai_message`(role/content/sources)。
- 多模型可扩展：`services/llm/base.py` 抽象 `BaseLLMProvider.stream_chat` + `deepseek.py`(OpenAI 兼容 SSE) + `__init__.py` 工厂 `get_provider`；新模型只加 Provider 类。
- 流式接口 `POST /api/ai/chat/stream` 走 SSE（delta/error/done）；前端 fetch 读流 + AbortController 停止。
- **踩坑**：①chat_stream 生成器 `finally` 里 `db.close()` 后再 yield 访问 `conv.id` 抛 `DetachedInstanceError`——须 close 前把会话 ID 固化到普通变量；②AI 的 `MessageItem` 与系统消息 `MessageItem` 命名冲突，已改名 `AiMessageItem`。
- DeepSeek Key 存 `.env` 的 `AI_API_KEY`（仅首次初始化默认值，运行期以 ai_config 表为准，接口脱敏 `sk-4****7be2`）。模型 `deepseek-v4-flash`。

## AI 安全红线（V1.4.9 起）
- **身份绑定**：`ai_service._resolve_identity()` 解析 `{is_internal, company_name}`（客户走 category_id→category_name），身份作为**代码级安全 system prompt 强制注入**（不随管理员可改 prompt 变化），绝不许反问公司/身份。
- **数据隔离**：客户账号按 `Project.category_id == 所属单位` 过滤，员工全量。
- **防幻觉**：知识库为空 → 短路返回固定话术，不调 LLM。
- **限流**：per-user 滑动窗口（60s 20 次，`threading.Lock`+deque，管理员豁免）。
- **会话/审计**：`pinned`/`is_deleted` 软删；oper_type `ai_chat`/`ai_conversation_rename`/`ai_conversation_pin`/`ai_conversation_delete`。
- 自检：`ai_full_check.py` + `mock_llm.py`（8899 端口 mock，monkeypatch get_provider 免真实 API）+ `full_flow_check.py`。

## AI 数据供给（V1.4.16 重构，当前态）
- **去关键词 + 去联网，改结构化知识库全量注入**：`services/llm/retriever.py` 重写为 `build_knowledge_base(db, current_user)->(context, sources)`——每次提问实时读库，把当前用户可见**全部项目**（进行中+已归档，已归档标「已结项」）渲染成固定模板文本（项目名称/客户单位/对接人/我方负责人·设计师/立项时间/预计结束时间/项目状态）注入 system 层。对接人/设计师 `IN_` 批量查避免 N+1；时间空「未设置」、设计师空「未分配」、对接人空回退首位再「未设置」。
- **不注入**：进度百分比、当前节点（用户明确不要）。
- **隔离**：客户 SQL 层 `WHERE category_id==所属单位`；员工全量。知识库拼 system 层（每次请求重建只发一次），历史层只存问答文本，多轮不重复注入。
- **空库短路**：`ai_service.chat_stream` 里 `if not context` 直接 yield 固定话术不调 LLM。
- **摘联网**：`deepseek.py` 只留 `/chat/completions`；`base.py`/`schemas/ai.py`/`routers/ai.py` 摘 `web_search`；前端 `ChatInput/ChatPanel/stores/api` 去「联网搜索」开关与 `webSearch`。库结构无变化。
- 历史（已被本版取代，仅留档）：V1.4.8 RAG+关键词检索 → V1.4.13 补停用词+意图识别+富上下文 → V1.4.16 全量注入。

## 流程模板与节点模板
- ①`node_template` 节点模板库（`form_fields` 存 JSON camelCase `{fieldLabel,fieldType,selectOptions,sort}`，fieldType∈text_single/text_multi/select/image）；②`flow_template`+`flow_template_node`+`flow_template_node_edge`+`flow_template_node_form`（新建项目一键实例化，表单/图标从节点模板库溯源）。
- 节点模板 ID（勿改，seed 依赖）：1 立项登记 2 需求对齐 3 IP设计输出 4 方案内部评审 5 打样制作 6 实物生产 7 验收 8 项目归档 9 备注节点 10 测试图像 11 布展搭建。
- 模板初始化挂 `main.py init_database()`（先 node 后 flow，幂等自动预置）。**空库崩溃教训**：首版只建布展搭建却依赖 8 基础节点，全新空库崩溃——收敛进 `BASE_NODE_TEMPLATES` 修复。

## 启动与自检
- `start.bat` 相对路径自动建 venv/装依赖/起 uvicorn 8000 单端口托管 dist；`stop.bat` 按端口杀进程。
- 回归：先起后端再跑 `backend/tests/full_flow_check.py`（18 模块含门户隔离+AI，92 项，数据自动清理）。
- 前端改完重构建：先停后端（运行中锁 dist 旧 hash 致 EPERM），沙箱内清 dist 用 `node -e "fs.rmSync('dist',{recursive:true,force:true})"`，再 `npm run build`。
- 环境：根目录 `.venv` 实为 **Python 3.10.11**（非 3.13.12）；跑 full_flow_check 前把 `ai_config.base_url` 指 mock LLM(8899)，跑完恢复 `https://api.deepseek.com` 并停 mock。
