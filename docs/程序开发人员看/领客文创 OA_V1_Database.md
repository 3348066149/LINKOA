# 青岛领客文创OA V1 数据库表结构设计

> 配套 PRD：领客文创OA_V1_PRD.md
> 配套接口：青岛领客文创OA_V1_后端接口清单.md
> 用途：给大模型生成后端 ORM 模型、建表 SQL、数据库迁移脚本
> 版本：V1.4.16（SQLite 默认 + MySQL 双支持；节点模板库；表单定义收口到节点模板；启动期结构自愈迁移；登录防暴力破解；AI 助手三张表 + 会话置顶/软删 + AI 审计留痕；V1.4.12 为前端 CRUD 未保存数据丢失修复；V1.4.13 为 AI 助手检索与富上下文优化，纯后端改动；V1.4.14 预置 3 套项目流程模板 + 「布展搭建」节点类型，数据库结构无变化；V1.4.15 客户账号改绑客户单位：sys_user 新增 category_id 列（绑定 customer_category.id），customer_id 列保留为历史兼容，启动幂等回填存量数据；V1.4.16 AI 助手数据供给改造：去关键词检索与联网搜索，改结构化知识库全量注入，数据库结构无变化）
> 部署环境：内网，管理员可查看用户明文密码

---

## 数据库全局约定

1. **数据库引擎**：默认 **SQLite**（V1.4.4 起文件位于项目内 `backend/linkoa.db`，`backend/.env` 的 `DB_URL=sqlite:///./linkoa.db` 为相对路径写法，config.py 按 `__file__` 解析为项目内绝对路径，随文件夹整体迁移）；也支持 MySQL（改 `.env` 的 `DB_URL`，见互转指南）
2. **MySQL 约定**：字符集 `utf8mb4`、排序规则 `utf8mb4_unicode_ci`、引擎 `InnoDB`
3. **外键**：**不建物理外键**，纯逻辑关联；级联删除/约束由后端代码事务控制
4. **主键**：全部 `bigint` 自增，起始值 1
5. **时间字段**：
   - `create_time`：`datetime`，默认 `CURRENT_TIMESTAMP`
   - `update_time`：`datetime`，默认 `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
6. **初始数据**：首次启动自动建表 + 插入默认管理员账号 `admin / admin123`，角色=管理员
7. **删除策略**：业务表均物理删除，不设 `deleted_at` 软删除字段；操作审计日志永久留存；**唯一例外**：`ai_conversation` 会话表 V1.4.9 起改软删（`is_deleted` 置位），消息与审计日志保留，便于 AI 对话溯源
8. **SQLite 索引注意**：SQLite 索引名需全库唯一（MySQL 仅表内唯一），代码已自动给索引名加表名前缀
9. **结构自愈迁移（V1.4.4 起）**：后端启动时 `auto_add_missing_columns()` 自动比对 ORM 模型与数据库实际列，`ALTER TABLE ADD COLUMN` 补齐缺失列后执行 `create_all`。**因此向模型新增列后无需手写迁移 SQL**，旧库在任意机器上启动即自动升级（仅补列，不删列、不改列类型）
10. **数据迁移（V1.4.7）**：`auto_add_missing_columns()` 之后执行 `_migrate_project_category()`，为 `category_id` 为空的历史项目按老客户回填所属单位，并在 `project_contact_rel` 补一条对接人记录（幂等，仅处理缺失数据）。**新增"需要按业务规则计算"的存量数据补写，应挂在这里，而不是写一次性脚本**

---

## 目录

- [1. 用户表 sys_user](#1-用户表-sys_user)
- [1-1. 部门表 sys_dept（V1.4 新增）](#1-1-部门表-sys_deptv14-新增)
- [1-2. 系统角色表 sys_role（V1.3 新增）](#1-2-系统角色表-sys_rolev13-新增保留兼容)
- [2. 客户单位表 customer_category（V1.4.7 语义变更）](#2-客户单位表-customer_category)
- [3. 对接人表 customer（V1.4.7 语义变更）](#3-对接人表-customer)
- [4. 流程模板表 flow_template](#4-流程模板表-flow_template)
- [5. 模板节点表 flow_template_node](#5-模板节点表-flow_template_node)
- [6. 模板节点连线表 flow_template_node_edge](#6-模板节点连线表-flow_template_node_edge)
- [7. 模板节点表单定义表 flow_template_node_form](#7-模板节点表单定义表-flow_template_node_form)
- [8. 项目表 project](#8-项目表-project)
- [9. 项目-设计师关联表 project_designer_rel](#9-项目-设计师关联表-project_designer_rel)
- [9-1. 项目-客户对接人关联表 project_contact_rel（V1.4.7 新增）](#9-1-项目-客户对接人关联表-project_contact_relv147-新增)
- [10. 项目画布节点表 project_node](#10-项目画布节点表-project_node)
- [11. 项目节点连线表 project_node_edge](#11-项目节点连线表-project_node_edge)
- [12. 项目节点表单填写值表 project_node_form_value](#12-项目节点表单填写值表-project_node_form_value)
- [13. 附件表 attachment](#13-附件表-attachment)
- [14. 评论表 comment](#14-评论表-comment)
- [15. 消息表 message](#15-消息表-message)
- [16. 节点模板表 node_template](#16-节点模板表-node_template)
- [17. 系统操作日志表 sys_operation_log](#17-系统操作日志表-sys_operation_log)
- [18. AI 配置表 ai_config（V1.4.8 新增）](#18-ai-配置表-ai_configv148-新增)
- [19. AI 会话表 ai_conversation（V1.4.8 新增）](#19-ai-会话表-ai_conversationv148-新增)
- [20. AI 消息表 ai_message（V1.4.8 新增）](#20-ai-消息表-ai_messagev148-新增)

---

## 1. 用户表 sys_user

> 角色枚举（V1.4.2 简化）：`管理员`、`普通`、`客户`（客户账号独立只读）
> 权限由用户自身角色决定，与部门无关（V1.4.1 起部门仅组织分组）
> 用户可启用/停用；管理员可物理删除（不能删自己、不能删初始 admin）；停用后禁止登录；删除后历史关联保留 user_id，展示层姓名兜底"已删除用户"

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| username | varchar(64) | 登录账号，唯一 |
| password | varchar(128) | **明文密码，内网使用** |
| real_name | varchar(64) | 真实姓名 |
| role | varchar(32) | 角色：管理员 / 普通 / 客户（V1.4.2 起；历史设计师/设计总监/行政已自动迁移为普通） |
| dept_id | bigint | 所属部门ID（sys_dept.id），内部员工；仅组织归属不决定权限（V1.4 新增） |
| customer_id | bigint | 绑定客户ID（customer.id），客户账号专用（V1.4 新增） |
| is_enable | tinyint | 0停用，1启用，默认1 |
| login_fail_count | smallint | 连续登录失败计数，默认0（V1.4.7 防暴力破解） |
| locked_until | datetime | 锁定到期时间，NULL 表示未锁定；登录失败达阈值后设为当前+10分钟（V1.4.7） |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `uk_username` (username) UNIQUE

---

## 1-1. 部门表 sys_dept（V1.4 新增）

> 部门仅做人员组织分组，**不携带权限**。V1.4.1 起 `role` 字段弃用恒为 NULL。启动幂等预置：研发部 / 设计部 / 市场部。

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| dept_name | varchar(64) | 部门名称，唯一 |
| dept_type | varchar(16) | internal 内置员工部门 / customer 客户部门（默认 internal） |
| role | varchar(32) | 兼容字段（V1.4.1 起不使用，恒为 NULL） |
| customer_id | bigint | 客户部门关联的客户ID（兼容，未使用） |
| create_time | datetime | 创建时间 |

**索引：**
- `uk_dept_name` (dept_name) UNIQUE

---

## 1-2. 系统角色表 sys_role（V1.3 新增，保留兼容）

> 自定义角色（权限=普通），用户管理页可增删；V1.4.2 角色简化后不再使用 UI 入口，表保留兼容。

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| role_name | varchar(64) | 角色名称，唯一 |
| create_time | datetime | 创建时间 |

---

## 2. 客户单位表 customer_category

> V1.4.7 语义变更：本表即**客户单位（公司）**，业务展示文案统一为「客户单位」
> 删除约束：单位下存在对接人时禁止删除；单位被项目引用（`project.category_id`）时同样禁止删除，后端返回 400

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| category_name | varchar(128) | 单位名称（展示为「客户单位」） |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

---

## 3. 对接人表 customer

> V1.4.7 语义变更：本表条目即**客户对接人（人）**，隶属某个客户单位；业务展示文案统一为「对接人」
> 删除约束：对接人被项目引用（`project.customer_id` 或 `project_contact_rel.customer_id`）时禁止删除，后端返回 400

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| category_id | bigint | 所属客户单位ID（customer_category.id，逻辑关联，无物理外键） |
| customer_name | varchar(128) | 对接人姓名 |
| remark | text | 对接人备注（职务、联系方式等） |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_category_id` (category_id)

---

## 4. 流程模板表 flow_template

> 模板与项目为全量值拷贝、深度解绑；删除模板直接物理删除，不影响历史项目

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| template_name | varchar(128) | 模板名称 |
| create_user_id | bigint | 创建人用户ID |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

---

## 5. 模板节点表 flow_template_node

> 属于模板下的节点，复制模板时把本表数据值拷贝到 project_node
> 模板编辑采用自由拓扑画布，节点带画布坐标
> V1.3：流程模板为纯流程编排，节点通过 node_template_id 关联节点模板，表单定义统一来自节点模板库

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| template_id | bigint | 所属模板ID |
| node_template_id | bigint | 关联节点模板ID（表单定义来源），可空 |
| node_title | varchar(128) | 节点标题 |
| node_remark | text | 模板节点备注 |
| sort | int | 节点排序序号（用于列表展示顺序） |
| pos_x | decimal(10,2) | 节点画布X坐标，默认0.00 |
| pos_y | decimal(10,2) | 节点画布Y坐标，默认0.00 |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_template_id` (template_id)

---

## 6. 模板节点连线表 flow_template_node_edge

> 模板画布中节点之间的连线关系，复制模板时值拷贝到 project_node_edge
> 模板保存为整图提交，全量覆盖 nodes + edges

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| template_id | bigint | 所属模板ID |
| source_node_id | bigint | 连线起始节点ID（关联 flow_template_node.id） |
| target_node_id | bigint | 连线目标节点ID（关联 flow_template_node.id） |
| label | varchar(128) | 连线文字标签，可空 |
| create_time | datetime | 创建时间 |

**索引：**
- `idx_template_id` (template_id)
- `idx_source_target` (source_node_id, target_node_id)

---

## 7. 模板节点表单定义表 flow_template_node_form（V1.3 起废弃）

> ⚠️ **本表已废弃**：V1.3 起表单定义统一收口到「节点模板表 node_template」，流程模板改为纯流程编排，不再定义表单。
> 保留本表仅用于兼容历史数据；新代码不再读写，项目实例化时从 node_template.form_fields 拷贝表单。
> V1 支持字段类型：text_single（单行文本）、text_multi（多行文本）、select（下拉单选）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| template_node_id | bigint | 关联 flow_template_node.id |
| field_label | varchar(128) | 表单显示名称 |
| field_type | varchar(32) | text_single单行 / text_multi多行 / select下拉单选 / image上传图像 / link链接（V1.4.3） |
| select_options | text | 下拉选项JSON数组；非下拉存null |
| sort | int | 表单字段排序 |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_template_node_id` (template_node_id)

---

## 8. 项目表 project

> 项目状态枚举：`进行中`、`已归档`
> 新建项目默认为进行中；已归档项目全部内容只读
> 删除约束：已归档项目必须先取消归档才能删除，后端返回 400

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_name | varchar(256) | 项目名称 |
| category_id | bigint | 所属客户单位ID（customer_category.id，V1.4.7 新增；门户按单位隔离） |
| customer_id | bigint | 首位客户对接人ID（customer.id，V1.4.7 起语义为对接人，兼容老数据保留非空） |
| project_desc | text | 项目描述 |
| expect_time | datetime | 预计结束时间（门户展示为「预计结束时间 / 距截止」） |
| project_status | varchar(32) | 进行中 / 已归档，默认"进行中"（门户侧将「已归档」展示为「已结项」） |
| create_user_id | bigint | 创建人ID |
| create_time | datetime | 创建时间（= 立项时间，门户按此字段筛选） |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_customer_id` (customer_id)
- `idx_category_id` (category_id)
- `idx_project_status` (project_status)

---

## 9. 项目-设计师关联表 project_designer_rel

> **仅用于溯源展示，不做权限控制**；一个项目可以关联多个设计师
> 所有设计师均可查看全部项目并修改全部项目画布节点

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 项目ID |
| user_id | bigint | 设计师用户ID |
| create_time | datetime | 创建时间 |

**索引：**
- `idx_project_id` (project_id)
- `idx_user_id` (user_id)

---

## 9-1. 项目-客户对接人关联表 project_contact_rel（V1.4.7 新增）

> 一个项目可关联多个客户对接人（均属同一客户单位）；编辑时为**全量覆盖**（先删后插）
> `project.customer_id` 冗余保存首位对接人，用于列表展示兜底与老数据兼容
> 启动期迁移 `_migrate_project_category()`：为 `category_id` 为空的历史项目回填单位（取老客户所属分类）并补一条关联记录

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 项目ID |
| customer_id | bigint | 对接人ID（customer.id） |
| create_time | datetime | 创建时间 |

**索引：**
- `idx_pcr_project_id` (project_id)
- `idx_pcr_customer_id` (customer_id)

---

## 10. 项目画布节点表 project_node

> 项目实际运行的画布节点；从模板节点值拷贝生成（含坐标、备注）
> 项目运行中临时新增的节点不带自定义表单字段，仅具备标题+备注+附件+评论
> 删除节点时，事务级联删除该节点的全部出入连线（project_node_edge）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 所属项目ID |
| node_title | varchar(128) | 节点标题 |
| node_remark | text | 节点备注 |
| icon | varchar(512) | 节点图标（V1.4.3，从模板冗余拷贝：预设图标名或 uploads 路径） |
| sort | int | 节点排序序号 |
| pos_x | decimal(10,2) | 节点画布X坐标，默认0.00 |
| pos_y | decimal(10,2) | 节点画布Y坐标，默认0.00 |
| create_user_id | bigint | 创建人ID |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_project_id` (project_id)

---

## 11. 项目节点连线表 project_node_edge

> 项目画布中节点之间的连线关系
> 从模板连线表值拷贝生成，拷贝时需完成节点ID重映射
> 删除节点时级联删除以该节点为 source 或 target 的全部连线

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 所属项目ID |
| source_node_id | bigint | 连线起始节点ID（关联 project_node.id） |
| target_node_id | bigint | 连线目标节点ID（关联 project_node.id） |
| label | varchar(128) | 连线文字标签，可空 |
| create_time | datetime | 创建时间 |

**索引：**
- `idx_project_id` (project_id)
- `idx_source_target` (source_node_id, target_node_id)

---

## 12. 项目节点表单填写值表 project_node_form_value

> 保存项目节点用户实际填写的表单数据；冗余字段保证模板修改不破坏历史数据
> V1.3：表单定义唯一来源是节点模板库，节点实例化时值拷贝（含 select_options 冗余），项目运行中仅填写值不可改结构
> 表单值保存为全量覆盖，后提交覆盖先提交

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_node_id | bigint | 关联 project_node.id |
| template_node_form_id | bigint | 来源模板表单ID，仅溯源用（V1.3 起为 null） |
| field_label | varchar(128) | 冗余：表单显示名称 |
| field_type | varchar(32) | 冗余：字段类型（text_single/text_multi/select/image/link，V1.4.3 支持图像与链接） |
| select_options | text | 冗余：下拉选项JSON数组（V1.3），非下拉为 null |
| field_value | text | 用户填写内容 |
| create_user_id | bigint | 填写人ID |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

**索引：**
- `idx_project_node_id` (project_node_id)

---

## 13. 附件表 attachment

> 文件存储在服务器本地磁盘，路径格式：日期隔离 + UUID 防重名
> 单文件最大 1G；允许任意常见格式（图片、文档、设计稿 .psd/.ai、压缩包等）
> 删除权限：**上传本人 或 管理员**；归档项目禁止上传和删除附件

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 所属项目ID |
| project_node_id | bigint | 所属节点ID |
| file_name | varchar(256) | 原始文件名 |
| file_path | varchar(512) | 相对 uploads/ 根目录的相对路径（V1.4 便携化，如 `20260831/uuid_xxx.docx`） |
| file_size | bigint | 文件大小（byte） |
| upload_user_id | bigint | 上传人ID |
| create_time | datetime | 上传时间 |

**索引：**
- `idx_project_id` (project_id)
- `idx_project_node_id` (project_node_id)

---

## 14. 评论表 comment

> 项目级评论，全部角色可发表；仅评论发布本人可删除
> 归档项目禁止新增和删除评论

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| project_id | bigint | 项目ID |
| content | text | 评论内容 |
| create_user_id | bigint | 评论人ID |
| create_time | datetime | 评论时间 |

**索引：**
- `idx_project_id` (project_id)

---

## 15. 消息表 message

> 用户个人消息中心数据
> 消息来源：节点新增/修改/删除、节点表单填写修改、评论发表
> 推送范围：该项目创建人 + 该项目所有关联设计师（自动排除操作人自己）
> 点击消息跳转对应项目详情页

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| receive_user_id | bigint | 接收消息用户ID |
| project_id | bigint | 关联项目ID（用于前端点击跳转，可空） |
| msg_type | varchar(64) | 消息类型：node_create / node_update / node_delete / form_update / comment_create |
| msg_content | text | 消息简要内容（人类可读文案） |
| is_read | tinyint | 0未读，1已读，默认0 |
| create_time | datetime | 消息生成时间 |

**索引：**
- `idx_receive_user_id` (receive_user_id)
- `idx_project_id` (project_id)

---

## 16. 节点模板表 node_template（V1.3 新增）

> 管理员预设的可复用节点类型，画布（项目与流程模板）只能从节点模板库选类型新增节点
> form_fields 为 JSON 数组：[{fieldLabel, fieldType, selectOptions, sort}]；fieldType（V1.4.3）支持 `text_single / text_multi / select / image（上传图像）/ link（链接）`
> 删除节点模板不影响已生成的流程模板与项目节点（值拷贝解绑）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| node_title | varchar(128) | 节点类型名称 |
| node_remark | text | 节点类型说明 |
| icon | varchar(512) | 节点图标（V1.4.3）：预设图标组件名（如 Document）或自定义上传相对路径（node_icon/xxx.svg） |
| sort | int | 面板展示排序，默认0 |
| form_fields | text | 建议表单字段JSON数组，可空 |
| create_time | datetime | 创建时间 |
| update_time | datetime | 更新时间 |

---

## 17. 系统操作日志表 sys_operation_log

> 日志**不可修改，不可删除**；审计溯源
> 所有写操作均记录日志；物理删除业务数据时日志永久留存

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| oper_user_id | bigint | 操作人ID |
| oper_time | datetime | 操作时间 |
| oper_type | varchar(128) | 操作类型枚举（见下方清单） |
| oper_desc | text | 变更简要描述（人类可读） |
| related_project_id | bigint | null=全局操作；不为空代表归属某个项目 |

**索引：**
- `idx_oper_user_id` (oper_user_id)
- `idx_related_project_id` (related_project_id)

### oper_type 枚举值清单

| 模块 | 操作 | oper_type |
|---|---|---|
| 用户 | 登录 | `user_login` |
| 用户 | 启用账号 | `user_enable` |
| 用户 | 停用账号 | `user_disable` |
| 用户 | 删除 | `user_delete` |
| 项目 | 新建 | `project_create` |
| 项目 | 删除 | `project_delete` |
| 项目 | 归档 | `project_archive` |
| 项目 | 取消归档 | `project_unarchive` |
| 项目 | 修改基础信息 | `project_update` |
| 项目节点 | 新增 | `node_create` |
| 项目节点 | 修改 | `node_update` |
| 项目节点 | 删除 | `node_delete` |
| 模板表单 | 字段新增 | `template_form_create` |
| 模板表单 | 字段修改 | `template_form_update` |
| 模板表单 | 字段删除 | `template_form_delete` |
| 项目节点表单 | 填写内容修改 | `node_form_value_update` |
| 评论 | 新增 | `comment_create` |
| 评论 | 删除 | `comment_delete` |
| 附件 | 上传 | `attachment_upload` |
| 附件 | 删除 | `attachment_delete` |
| 对接人（原客户） | 新增 | `customer_create` |
| 对接人（原客户） | 修改 | `customer_update` |
| 对接人（原客户） | 删除 | `customer_delete` |
| 客户单位（原客户分类） | 新增 | `category_create` |
| 客户单位（原客户分类） | 修改 | `category_update` |
| 客户单位（原客户分类） | 删除 | `category_delete` |
| 项目-对接人关联 | 变更（随项目编辑） | `project_update` |
| 流程模板 | 新增 | `template_create` |
| 流程模板 | 修改 | `template_update` |
| 流程模板 | 删除 | `template_delete` |
| 节点模板 | 新增 | `node_template_create` |
| 节点模板 | 修改 | `node_template_update` |
| 节点模板 | 删除 | `node_template_delete` |
| AI 助手 | 提问 | `ai_chat`（V1.4.9 新增，每次对话记录问题摘要） |
| AI 助手 | 置顶/取消置顶 | `ai_conversation_pin`（V1.4.9 新增） |
| AI 助手 | 重命名会话 | `ai_conversation_rename`（V1.4.9 新增） |
| AI 助手 | 删除会话 | `ai_conversation_delete`（V1.4.9 新增，软删） |

---

## 18. AI 配置表 ai_config（V1.4.8 新增）

> 单行配置（运行时读 id 最小的一条），管理员面板「AI 设置」可改，替换 .env 硬编码；`api_key` 返回时脱敏

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| system_prompt | text | AI 人设/职责 system prompt（卖萌人设，管理员可改） |
| model | varchar(64) | 模型名，默认 `deepseek-v4-flash`（V1.4.10 起；`deepseek-chat`/`deepseek-reasoner` 已于 2026/07 弃用，启动时幂等回填升级） |
| api_key | varchar(256) | API Key（默认空；接口返回脱敏 `sk-4****7be2`） |
| base_url | varchar(256) | 接口地址，默认 `https://api.deepseek.com` |
| temperature | float | 采样温度，默认 0.7（0~2） |
| max_tokens | integer | 单次最大 token，默认 2048（1~32768） |
| updated_at | datetime | 更新时间 |
| updated_by | bigint | 最后更新人ID（可空） |

- 首次启动 `_init_ai_config()` 幂等初始化：若表空则按 `.env` 的 `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL` 写入一条默认配置；若已存在且 `model` 为弃用的 `deepseek-chat`/`deepseek-reasoner`，则自动升级为 `deepseek-v4-flash`（V1.4.10，幂等）。

---

## 19. AI 会话表 ai_conversation（V1.4.8 新增，V1.4.9 加 pinned / is_deleted）

> 每个用户多个会话，仿豆包/DeepSeek 左侧会话列表；**V1.4.9 起删除改软删**（仅置 `is_deleted`，消息与审计日志保留，便于溯源）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| user_id | bigint | 所属用户ID（会话按用户隔离） |
| title | varchar(128) | 会话标题，默认「新对话」（首条消息前 30 字） |
| pinned | boolean | 是否置顶（V1.4.9 新增，默认 false；列表置顶优先排序） |
| is_deleted | boolean | 软删除标记（V1.4.9 新增，默认 false；删除仅置位不物理删） |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

**索引：** `idx_ai_conv_user` (user_id)

---

## 20. AI 消息表 ai_message（V1.4.8 新增）

> 会话内消息；`role` 为 user / assistant；`sources` 存来源项目引用 JSON 字符串（`[{id, projectName}]`）

| 字段名 | 类型 | 说明 |
|---|---|---|
| id | bigint | 主键自增 |
| conversation_id | bigint | 所属会话ID |
| role | varchar(16) | 角色：user / assistant |
| content | text | 消息内容 |
| sources | text | 来源引用 JSON 数组（可空；无引用为 null，前端显示 `[]`） |
| created_at | datetime | 创建时间 |

**索引：** `idx_ai_msg_conv` (conversation_id)

---

## 表关系总览（逻辑关联，无物理外键）

```
sys_user (1) ──< (N) project (create_user_id)
sys_user (1) ──< (N) project_designer_rel (user_id)
customer_category 客户单位 (1) ──< (N) customer 对接人 (category_id)
customer_category 客户单位 (1) ──< (N) project (category_id)   ← V1.4.7 门户隔离依据
customer 对接人 (1) ──< (N) project (customer_id，首位对接人，兼容保留)
project (1) ──< (N) project_contact_rel (project_id)           ← V1.4.7 新增
customer 对接人 (1) ──< (N) project_contact_rel (customer_id)
project (1) ──< (N) project_designer_rel (project_id)
project (1) ──< (N) project_node (project_id)
project_node (1) ──< (N) project_node_edge (source_node_id / target_node_id)
project_node (1) ──< (N) project_node_form_value (project_node_id)
project (1) ──< (N) attachment (project_id)
project_node (1) ──< (N) attachment (project_node_id)
project (1) ──< (N) comment (project_id)
project (1) ──< (N) message (project_id)
sys_user (1) ──< (N) message (receive_user_id)
flow_template (1) ──< (N) flow_template_node (template_id)
flow_template_node (N) ──> (1) node_template (node_template_id，逻辑引用，表单定义来源)
flow_template_node (1) ──< (N) flow_template_node_edge (source_node_id / target_node_id)
sys_user (1) ──< (N) sys_operation_log (oper_user_id)
project (1) ──< (N) sys_operation_log (related_project_id)
sys_user (1) ──< (N) ai_conversation (user_id)               ← V1.4.8 新增
ai_conversation (1) ──< (N) ai_message (conversation_id)    ← V1.4.8 新增
```

---

## 模板实例化数据拷贝规则（核心业务逻辑）

使用模板新建项目时，执行以下值拷贝（全部在一个数据库事务内完成）：

1. **创建项目记录**：插入 project 表，project_status = "进行中"
2. **拷贝节点**：遍历模板节点（flow_template_node），插入 project_node 表
   - 拷贝字段：node_title, node_remark, icon, sort, pos_x, pos_y（V1.4.3 节点图标一并拷贝）
   - 维护内存映射：`Map<old_template_node_id, new_project_node_id>`
3. **拷贝节点连线**：遍历模板连线（flow_template_node_edge），插入 project_node_edge 表
   - 使用上述 ID 映射，将 source_node_id / target_node_id 重映射为新的 project_node.id
4. **拷贝表单字段定义**：根据节点关联的 `node_template_id`，从 `node_template.form_fields` 解析表单字段，插入 project_node_form_value 表
   - 拷贝字段：field_label, field_type, select_options（冗余保存，V1.3 起下拉选项直接冗余；V1.4.3 支持 image/link 类型）
   - template_node_form_id 为 null（V1.3 起表单来源是节点模板，非流程模板表单）
   - field_value 初始为空
5. **拷贝项目-设计师关联**：插入 project_designer_rel 表
6. **写入项目-对接人关联**：按入参 `contactCustomerIds` 插入 project_contact_rel 表，并把首位对接人写入 `project.customer_id`（V1.4.7）
7. **记录操作日志**：oper_type = project_create

> 拷贝完成后，新项目与模板彻底解绑，模板后续修改/删除不影响历史项目。
