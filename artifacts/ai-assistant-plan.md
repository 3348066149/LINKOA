# 青青侠 AI 助手 · 功能方案设计

> 版本：V1.4.8 规划稿 | 日期：2026-09-02 | 状态：待开发

## 一、需求总览

在 LINKOA 平台新增一个常驻 AI 助手「青青侠」，供公司内部员工与客户门户的客户使用。

- **员工端**：全量可见系统数据，可自由问答。
- **客户端**：严格按客户单位（customer_category）做数据隔离，AI 只能检索/回答该客户自己公司的项目信息，杜绝跨公司数据泄露。

核心交互：右下角常驻 IP 形象 → 悬停随机气泡 → 点击平滑展开为占屏 2/3 的居中弹窗 → 弹窗内对话问答（接入 DeepSeek，流式输出）。

---

## 二、功能模块划分

### A. 前端模块

| 模块 | 说明 |
|------|------|
| **MascotFloat 常驻形象** | 固定在屏幕右下角；常驻上下浮动「呼吸感」动画；悬停放大/摇头动效 |
| **BubbleTip 随机气泡** | 悬停触发，从纯前端数组随机取一条文案；气泡淡入淡出 |
| **ChatPanel 对话弹窗** | 桌面居中占屏 2/3，移动端自动全屏；展开/收起有平滑过渡动画 |
| **MascotAvatar 弹窗内头像** | 弹窗左上角缩小版青青侠，作为吉祥物；关闭弹窗后右下角形象淡入恢复 |
| **ConversationList 会话列表** | 左侧列表，仿豆包/DeepSeek；支持新建、切换、删除会话，历史持久化 |
| **MessageArea 消息区** | 用户/AI 消息气泡；Markdown 渲染（标题/列表/表格/代码高亮）；来源引用卡片；流式打字机输出 |
| **InputArea 输入区** | 多行输入、回车/按钮发送、停止生成按钮 |
| **SuggestQuestions 推荐问题** | 首次空状态展示若干推荐问题，点击直接提问 |
| **Pinia Store 状态管理** | 会话列表、当前会话、消息流、流式缓冲、加载态 |
| **API 层** | 会话 CRUD、消息流式接收（SSE/fetch stream） |

### B. 后端模块

| 模块 | 说明 |
|------|------|
| **LLM Provider 抽象层** | 统一接口 `chat_stream()`；DeepSeek 为首个实现；未来 OpenAI/Claude/通义等只加实现不改业务代码 |
| **流式输出接口** | `/api/ai/chat/stream`，SSE 或 fetch 流式返回，支持中途停止 |
| **知识库检索层（RAG）** | 从项目数据中检索并拼接上下文；员工=全量，客户=按 customer_category 隔离 |
| **AI 配置表** | 存人设 prompt、模型名、API Key、Base URL、生成参数，供管理员面板读写 |
| **会话/消息数据模型** | `ai_conversation`、`ai_message` 两张表，按用户持久化 |
| **权限隔离** | 复用现有 JWT 认证 + 客户单位隔离逻辑 |

### C. 管理端模块

| 模块 | 说明 |
|------|------|
| **AI 设置页** | 管理员可配置：AI 人设/prompt、模型名称、API Key、Base URL、生成参数（温度/最大 token 等） |

---

## 三、技术架构

- **前端**：Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios
- **后端**：FastAPI + SQLAlchemy + httpx（已有），流式用 SSE/stream
- **AI 接入**：DeepSeek（key 已提供），通过统一 Provider 抽象，配置化切换模型

```
前端组件层
  MascotFloat / BubbleTip / ChatPanel / ConversationList / MessageArea
        │  (Pinia + axios)
        ▼
后端 API 层  /api/ai/*
  ├─ /conversations   会话 CRUD
  ├─ /chat/stream     流式对话
  └─ /config          管理员配置
        │
        ▼
AI Service
  ├─ KnowledgeRetriever 知识库检索（含数据隔离）
  ├─ PromptBuilder      上下文拼接（人设 + 知识 + 历史）
  └─ LLMProvider 抽象
        ├─ DeepSeekProvider  ← 当前
        └─ (OpenAI / Claude / 通义 ...) ← 预留
```

---

## 四、数据模型设计

### 1. `ai_config`（AI 配置表，单行或 key-value）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| system_prompt | text | AI 人设/职责 prompt |
| model | varchar | 模型名，如 deepseek-chat |
| api_key | varchar | API Key（加密存储） |
| base_url | varchar | 接口地址，默认 https://api.deepseek.com |
| temperature | float | 温度 |
| max_tokens | int | 最大 token |
| updated_at | datetime | 更新时间 |

### 2. `ai_conversation`（会话表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| user_id | int | 所属用户 |
| title | varchar | 会话标题（取首条消息截断） |
| created_at / updated_at | datetime | 时间 |

### 3. `ai_message`（消息表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| conversation_id | int | 所属会话 |
| role | varchar | user / assistant |
| content | text | 内容 |
| sources | json | 来源引用（项目 id、名称等） |
| created_at | datetime | 时间 |

---

## 五、API 接口设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/ai/conversations | 当前用户会话列表 |
| POST | /api/ai/conversations | 新建会话 |
| GET | /api/ai/conversations/{id}/messages | 获取会话消息 |
| DELETE | /api/ai/conversations/{id} | 删除会话 |
| POST | /api/ai/chat/stream | 发起对话（流式 SSE 返回） |
| GET | /api/ai/config | 管理员获取 AI 配置 |
| PUT | /api/ai/config | 管理员更新 AI 配置 |

---

## 六、关键交互时序

1. 页面加载 → 右下角淡入青青侠，开始浮动呼吸动画
2. 鼠标悬停 → 青青侠放大/摇头 + 弹出随机气泡（文案来自前端数组）
3. 点击青青侠 → 右下角形象淡出，弹窗从形象位置平滑放大过渡到居中占屏 2/3
4. 弹窗内 → 左侧会话列表 + 右侧消息区 + 底部输入框；左上角缩小头像
5. 用户提问 → 前端调用流式接口，AI 逐字输出；可点「停止生成」
6. 回答中如有项目数据 → 展示来源引用卡片，可点击跳转
7. 关闭弹窗 → 弹窗淡出，右下角青青侠淡入恢复

---

## 七、数据隔离规则（重点）

- **员工（内部账号）**：知识库检索无隔离，可查全部项目。
- **客户账号**：检索时强制注入 `category_id = 当前客户单位` 条件，只返回本单位项目；AI prompt 层同时声明「仅基于该客户公司数据回答」。

---

## 八、待开发文件规划

### 前端（frontend/src）
- `components/ai/MascotFloat.vue` — 常驻形象 + 浮动/悬停动效
- `components/ai/BubbleTip.vue` — 随机气泡
- `components/ai/ChatPanel.vue` — 对话弹窗（含展开动画）
- `components/ai/ConversationList.vue` — 会话列表
- `components/ai/MessageList.vue` — 消息区（Markdown + 流式 + 来源引用）
- `components/ai/ChatInput.vue` — 输入区
- `components/ai/SuggestQuestions.vue` — 推荐问题
- `stores/ai.js` — Pinia 状态
- `api/ai.js` — 接口封装
- `config/mascot.js` — 气泡文案数组

### 后端（backend/app）
- `models/ai.py` — ai_config / ai_conversation / ai_message
- `schemas/ai.py` — 请求/响应模型
- `services/llm/__init__.py` — Provider 抽象基类
- `services/llm/deepseek.py` — DeepSeek 实现
- `services/llm/retriever.py` — 知识库检索 + 数据隔离
- `services/llm/prompt.py` — Prompt 拼接
- `services/ai_service.py` — 会话/消息业务
- `routers/ai.py` — 路由
- `main.py` — 注册路由 + 启动建表迁移

### 管理端
- 管理员面板新增「AI 设置」页（前端）

---

## 九、版本与文档同步

按项目规范，功能完成后需同步 8 份 MD 文档、更新版本号至 V1.4.8，并跑 `backend/tests/full_flow_check.py` 回归。
