# LINKOA V1.4.15 交付报告 — 客户账号改绑客户单位（公司）

- **交付日期**：2026-09-02
- **版本号**：V1.4.15
- **代码提交**：commit `554f21f9`
- **交付团队**：software-linkoa-tpl2（主理人：齐活林 · 交付总监）
- **交付状态**：✅ 完成，QA 回归全绿（智能路由判定 NoOne）

---

## 一、TL;DR

客户账号的数据归属，从「绑定对接人（Customer）」纠正为「绑定客户单位（CustomerCategory，即公司）」。

此前系统通过 `sys_user.customer_id`（对接人 ID）间接溯源到 `customer.category_id`（公司），语义错位且依赖冗余。本版新增 `sys_user.category_id` 直接绑定公司，全链路（建号 / 登录 / 列表展示 / 项目数据隔离 / AI 身份识别）统一按公司口径，`customer_id` 保留为存量兼容字段。版本升 **V1.4.15**。

---

## 二、需求来源

用户在 V1.4.14 收尾后明确指出：

> 「客户账号绑定的不是对接人。要绑定的是公司啊」

经确认，用户选择 **「改代码绑定公司」**（数据模型级改动，而非仅改文档）。

---

## 三、数据模型变更

### `sys_user` 表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `category_id` | `BIGINT`（可空） | 客户账号绑定的客户单位 ID（`customer_category.id`，仅 `role=客户`） |
| `customer_id` | `BIGINT`（可空） | **历史兼容字段**：V1.4.15 起客户账号改用 `category_id` 绑定公司，此字段仅存量保留 |

字段自动补列由启动期 `auto_add_missing_columns` 自愈迁移完成，无需手工迁移脚本。

---

## 四、改动清单（约 20 文件）

### 后端（10 文件）

| 文件 | 改动 |
|------|------|
| `backend/app/models/user.py` | `customer_id` 注释改为历史兼容；新增 `category_id` 列 |
| `backend/app/dependencies.py` | `get_current_user` 裸 SQL 列清单新增 `category_id` |
| `backend/app/schemas/auth.py` | `UserInfo` 新增 `category_id` |
| `backend/app/schemas/sys_user.py` | `SysUserCreateRequest` 新增 `category_id`（`customer_id` 标注历史兼容）；`SysUserItem` 新增 `category_id` / `category_name` |
| `backend/app/services/user_service.py` | `_user_info` 客户账号直取 `CustomerCategory`；`list_users` 按公司展示；`create_user` 互斥校验改「部门 vs 客户单位」二选一 |
| `backend/app/services/project_service.py` | `_resolve_user_category_id` 直取 `current_user["category_id"]` |
| `backend/app/services/llm/retriever.py` | `_resolve_user_category_id` 直取 `current_user["category_id"]` |
| `backend/app/services/ai_service.py` | `_resolve_identity` 客户分支直取 `category_id` → `CustomerCategory` 公司名 |
| `backend/app/main.py` | 新增 `_migrate_user_category_id()` 幂等回填存量；版本号升 `1.4.15` |
| `backend/tests/full_flow_check.py` | 门户账号断言 `customerId` → `categoryId` |

### 前端（2 文件）

| 文件 | 改动 |
|------|------|
| `frontend/src/views/system/User.vue` | 新建客户账号表单改「绑定客户单位」，`listCategories()` 取公司下拉；卡片/筛选/编辑按公司展示 |
| `frontend/src/views/login/Index.vue` | 登录页脚版本号 `1.4.15` |

### 文档（8 份 MD）

README.md、backend/README.md、frontend/README.md、程序开发人员看/领客文创 OA_V1_PRD.md、领客文创 OA_V1_Database.md、青岛领客文创OA_V1_后端接口清单.md、领客文创OA_V1_数据库互转与MySQL部署指南.md、领客文创OA_V1_AI开发总控指令.md —— 均升 V1.4.15 并含「客户账号改绑客户单位」变更说明。

---

## 五、数据隔离红线

客户数据隔离的口径已统一为「按客户单位（公司）」：

| 逻辑点 | 实现 |
|--------|------|
| 项目列表隔离 | `project_service._resolve_user_category_id` 直取 `category_id` |
| RAG 检索隔离 | `retriever._resolve_user_category_id` 直取 `category_id` |
| AI 身份识别 | `ai_service._resolve_identity` 直取 `category_id` → 公司名 |

客户账号只能看到所属公司的项目；AI 助手身份绑定不再通过对接人间接溯源。

---

## 六、存量数据迁移

`backend/app/main.py` 新增 `_migrate_user_category_id()`，幂等回填存量客户账号：

- 匹配条件：`role=客户` 且 `customer_id 非空` 且 `category_id 为空`
- 回填值：`customer.category_id`
- 幂等：重复启动不二次回填、不产生重复行

---

## 七、QA 回归结果（严过关）

| 项目 | 结果 |
|------|------|
| 现有库重启 + 自动补列 + 迁移幂等 | ✅ PASS（临时库真实回填模拟 4/4） |
| 新建客户账号 `categoryId` 成功 / 旧 `customerId` 被拒 | ✅ PASS（17/17，旧参数返回 400） |
| 客户数据隔离按公司 | ✅ PASS（仅见同 `category_id` 项目） |
| 全量回归 `full_flow_check.py` | ✅ PASS（91/91，mock LLM 8899） |
| 前端 `npm run build` | ✅ PASS（1891 modules，无 EPERM） |

**智能路由判定：NoOne（全绿，无需打回工程师）**

环境已还原：后端重启（8000，health 200）、`ai_config.base_url` 恢复 `https://api.deepseek.com`、mock LLM 已停、临时 QA 文件已清理。

---

## 八、下一步建议

1. **重启生效**：后端已重启（8000 端口），前端已重构建，可直接验证。
2. **验证存量账号**：用现有客户账号登录，确认「所属公司」显示正确、项目列表只含本公司项目。
3. **清理旧演示数据**：旧库早期手动演示的「测试」客户与演示项目，可自行决定是否清理。
4. **下一版**：从 V1.4.16 起记；升版时 grep `1.4.15` 收口全部散落点（`main.py`、`login/Index.vue`、8 份 MD）。
