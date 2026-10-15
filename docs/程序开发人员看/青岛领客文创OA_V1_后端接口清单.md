# 青岛领客文创OA V1 后端接口清单 Api.md

> 配套文档：
> - 领客文创OA_V1_PRD.md 产品需求
> - 领客文创OA_V1_Database.md 数据库表结构

> 版本：V1.4.16（V1.4.4 启动自动迁移；V1.4.5 修复连线自环误杀、补模板连线审计日志、封面/图标上传魔数校验、补文档缺失的封面上传接口；V1.4.6 登录防暴力破解：连续 5 次失败锁定 10 分钟 + 管理员手动解锁接口；品牌文案统一为「青岛领客文化传播有限公司」；V1.4.7 客户单位/对接人模型 + 门户重构；V1.4.8 新增 AI 助手「青青侠」模块，含会话 CRUD + SSE 流式对话 + 管理员 AI 配置；V1.4.9 AI 助手安全加固：身份绑定数据隔离、速率限制、防幻觉短路、会话置顶/重命名/软删、AI 对话审计留痕；V1.4.10 AI 联网搜索：chat/stream 入参新增 webSearch，模型升级 deepseek-v4-flash；V1.4.11 BUG 修复与健壮性加固：AI 弹层层级根治、中文输入法 Enter 误发送、移动端三点菜单、会话切换卡 streaming、文件删除失败冒泡 500；V1.4.12 前端 CRUD 未保存数据丢失修复：项目详情页节点表单新增脏检测，切换/新增/归档节点及离开详情页时拦截未保存修改，接口契约无变化；V1.4.13 AI 助手检索与富上下文优化：修复模糊/全局项目查询失败 + 扩充负责人/进度/倒计时/紧急度/统计能力，接口契约无变化；V1.4.14 预置 3 套项目流程模板 + 「布展搭建」节点类型，模板初始化挂启动流程，接口契约无变化；V1.4.15 客户账号改绑客户单位：sys_user 新增 category_id 列，sysUser/create 客户分支入参改为 categoryId，登录返回 categoryId/companyName，隔离逻辑按 category_id 直取，接口契约按此更新；V1.4.16 AI 助手数据供给改造：去关键词检索与联网搜索，改结构化知识库全量注入，chat/stream 入参移除 webSearch，接口契约按此更新）
> 部署环境：仅内网使用
> 后端技术栈：FastAPI + SQLAlchemy + SQLite（默认）/ MySQL 8.0（可选）
> 回归测试：`backend/tests/full_flow_check.py`（HTTP 层断言，覆盖 18 个路由模块主链路，含客户门户隔离与 AI 助手）

---

## 全局约定

### 1. 统一返回格式

所有接口统一返回 JSON：

```json
{
  "code": 200,
  "msg": "",
  "data": {}
}
```

- `code`：状态码，200 表示成功，非 200 表示失败
- `msg`：提示信息，成功为空字符串，失败为具体错误描述
- `data`：业务数据，对象或数组或 null

### 2. 错误码定义

| code | 含义 | 触发场景 |
|---|---|---|
| 200 | 成功 | 正常返回 |
| 400 | 参数错误 / 业务规则不满足 | 归档项目禁止操作、删除别人附件、参数缺失、删除约束拦截 |
| 401 | 未登录 / token 失效 | 无 token、token 过期、签名错误 |
| 403 | 无权限 | 角色不允许调用该接口 |
| 500 | 服务器内部错误 | 异常未捕获 |

### 3. 鉴权方式

- 登录接口返回 JWT Token，前端存储在 localStorage
- 后续所有需登录接口，请求头携带：`Authorization: Bearer <token>`
- Token 过期时间：24 小时
- 后端校验失败返回 401，前端拦截器清除 token 并跳转登录页

### 4. 分页规范

分页接口统一使用 Query 参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| pageNum | int | 1 | 当前页码，从 1 开始 |
| pageSize | int | 10 | 每页条数 |

分页返回 data 结构：

```json
{
  "items": [],
  "total": 128,
  "pageNum": 1,
  "pageSize": 10
}
```

**分页接口**：项目列表、客户列表、全局审计日志、个人消息列表
**不分页接口**：用户列表、客户分类列表、模板列表、项目内日志、节点附件、项目评论

### 5. 归档项目全局约束

当项目状态为【已归档】时，以下接口禁止调用，返回 400：
- 节点增删改、节点连线增删、批量坐标更新
- 节点表单保存
- 附件上传、附件删除
- 评论新增、评论删除
- 项目删除（必须先取消归档）

### 6. 并发策略

节点编辑无协同锁，后提交覆盖先提交；操作日志完整记录两次操作。

---

## 目录

- [1. 登录模块接口](#1-登录模块接口)
- [2. 用户管理接口（仅管理员）](#2-用户管理接口仅管理员)
- [3. 客户分类接口](#3-客户分类接口)
- [4. 客户库接口](#4-客户库接口)
- [5. 流程模板接口](#5-流程模板接口)
- [5-1. 节点模板接口](#5-1-节点模板接口)
- [6. 模板节点连线接口](#6-模板节点连线接口)
- [7. 项目基础接口](#7-项目基础接口)
- [8. 项目画布节点接口](#8-项目画布节点接口)
- [9. 项目节点连线接口](#9-项目节点连线接口)
- [10. 附件接口](#10-附件接口)
- [11. 评论接口](#11-评论接口)
- [12. 消息中心接口](#12-消息中心接口)
- [13. 操作审计日志接口](#13-操作审计日志接口)
- [14. 报表导出接口](#14-报表导出接口)
- [15. 部门管理接口（V1.4 新增）](#15-部门管理接口v14-新增仅管理员)
- [16. 权限体系（V1.4.2 两类角色）](#16-权限体系v142-简化为两类角色)
- [17. 客户门户（V1.4 新增）](#17-客户门户v14-新增)
- [18. AI 助手接口（V1.4.8 新增）](#18-ai-助手接口v148-新增)

---

# 1. 登录模块接口

### 1.1 用户登录

- **请求**：`POST /api/login`
- **入参**（JSON Body）：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

- **返回 data**：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "userInfo": {
    "id": 1,
    "username": "admin",
    "realName": "管理员",
    "role": "管理员",
    "deptId": null,
    "deptName": null,
    "customerId": null,
    "customerName": null,
    "companyName": null
  }
}
```

- **字段说明**：内部员工返回 `deptName`；客户账号额外返回 `customerName`（绑定对接人姓名）与 `companyName`（对接人所属客户单位名，V1.4.7 新增，门户顶栏直接展示公司名）

- **业务规则**：
  - 账号或密码错误返回 400，msg="账号或密码错误"
  - 账号已停用（is_enable=0）返回 400，msg="账号已停用，请联系管理员"
  - **V1.4.6 登录防暴力破解**：同一账号连续登录失败达到 5 次，自动锁定 10 分钟（msg 提示剩余锁定分钟数，或"密码错误次数过多，账号已锁定 10 分钟，或联系管理员解锁"）；锁定期间不再校验密码，直接拒绝。登录成功自动清零失败计数与锁定状态。账号不存在时不累加失败次数（避免账号枚举）。
  - 登录成功记录操作日志（oper_type=user_login）；触发锁定时记录 oper_type=user_login_lock
- **权限**：无

### 1.2 修改本人密码

- **请求**：`POST /api/user/updateMyPwd`
- **入参**（JSON Body）：

```json
{
  "oldPassword": "旧密码",
  "newPassword": "新密码"
}
```

- **返回 data**：null
- **业务规则**：
  - 旧密码校验不通过返回 400，msg="原密码错误"
  - 新密码不能为空
- **权限**：全部登录用户

---

# 2. 用户管理接口（仅管理员）

### 2.1 获取全部用户列表（展示明文密码）

- **请求**：`GET /api/sysUser/list`
- **返回 data**：用户数组（不分页），V1.4 起含部门/客户信息

```json
[
  {
    "id": 1,
    "username": "admin",
    "password": "admin123",
    "realName": "管理员",
    "role": "管理员",
    "deptId": null,
    "deptName": null,
    "customerId": null,
    "customerName": null,
    "isEnable": 1
  },
  {
    "id": 2,
    "username": "qd_gong1",
    "realName": "青岛地铁-张工",
    "role": "客户",
    "customerId": 3,
    "customerName": "青岛地铁",
    "isEnable": 1
  }
]
```

- **权限**：仅管理员

### 2.2 新建系统用户（V1.4.2：部门+角色，部门即组织归属，角色即权限）

- **请求**：`POST /api/sysUser/create`
- **入参**（JSON Body，二选一）：
  - 内部员工：`deptId` + `role`（普通/管理员）
  - 客户账号：`customerId`（绑定**对接人**，role 固定为「客户」，只读门户；V1.4.7 起该账号可见其对接人所属**客户单位的全部项目**）

```json
{ "username": "zhangsan", "password": "123456", "realName": "张三", "deptId": 1, "role": "普通" }
{ "username": "qingdao_zhang", "password": "qd123", "realName": "张工", "customerId": 12 }
```

- **返回 data**：`{ "userId": 2 }`
- **业务规则**：username 唯一；deptId/customerId 必须二选一；员工角色仅「普通/管理员」
- **说明（V1.4.7）**：同一客户单位可为多个对接人各建账号（如李主任、王经理各一个），任一账号登录后门户列表一致
- **权限**：仅管理员

### 2.3 编辑用户（V1.4.1 新增：改部门/角色/姓名）

- **请求**：`POST /api/sysUser/update`
- **入参**（JSON Body）：

```json
{ "id": 2, "realName": "张三", "deptId": 2, "role": "普通" }
```

- **返回 data**：null
- **业务规则**：账号不可改、密码走重置；角色仅「普通/管理员」；客户账号仅可改姓名（禁止分配部门/角色）；员工必须提供 deptId + role
- **权限**：仅管理员

### 2.4 重置用户密码

- **请求**：`POST /api/sysUser/resetPwd`
- **入参**（JSON Body）：

```json
{
  "userId": 2,
  "newPassword": "654321"
}
```

- **返回 data**：null
- **权限**：仅管理员

### 2.5 启用 / 停用账号

- **请求**：`POST /api/sysUser/setEnable`
- **入参**（JSON Body）：

```json
{
  "userId": 2,
  "isEnable": 0
}
```

- **返回 data**：null
- **业务规则**：记录操作日志（oper_type=user_enable / user_disable）
- **权限**：仅管理员

### 2.5.1 手动解锁账号（V1.4.7 新增）

- **请求**：`POST /api/sysUser/unlock`
- **入参**（JSON Body）：

```json
{ "userId": 2 }
```

- **返回 data**：null
- **业务规则**：
  - 清零该账号的登录失败计数（login_fail_count）与锁定时间（locked_until），用于误锁后即时恢复
  - 账号未被锁定时重复调用返回 400，msg="该账号未被锁定"
  - 记录操作日志（oper_type=user_unlock）
- **权限**：仅管理员
- **前端**：「用户管理」卡片在账号处于锁定状态时显示「已锁定」标签并出现「解锁」按钮，点击确认后调用本接口

### 2.6 删除用户（物理删除，V1.3 新增）

- **请求**：`POST /api/sysUser/delete`
- **入参**（JSON Body）：`{ "userId": 2 }`
- **返回 data**：null
- **业务规则**：
  - 不能删除自己；初始管理员 `admin` 禁止删除
  - 物理删除后，历史项目/评论/附件/日志中保留原 `user_id`，展示层姓名兜底显示"已删除用户"
  - 记录操作日志（oper_type=user_delete）
- **权限**：仅管理员

---

# 3. 客户单位接口（原客户分类，V1.4.7 语义变更）

### 3.1 查询全部客户单位

- **请求**：`GET /api/customerCategory/list`
- **返回 data**：单位数组（不分页），字段 `id, categoryName`（前端展示为「客户单位」）
- **权限**：全部角色

### 3.2 新增客户单位

- **请求**：`POST /api/customerCategory/add`
- **入参**（JSON Body）：`{ "categoryName": "青岛博物馆" }`（单位名称，即公司/机构全称）
- **返回 data**：`{ "id": 1 }`
- **业务规则**：记录操作日志（oper_type=category_create）
- **权限**：管理员（V1.4.2 角色简化后）

### 3.3 修改客户单位

- **请求**：`POST /api/customerCategory/update`
- **入参**（JSON Body）：`{ "id": 1, "categoryName": "新单位名称" }`
- **返回 data**：null
- **业务规则**：记录操作日志（oper_type=category_update）
- **权限**：管理员（V1.4.2 角色简化后）

### 3.4 删除客户单位（物理删除）

- **请求**：`POST /api/customerCategory/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **业务规则**：
  - 删除前查询 customer 表，若存在 category_id=当前ID 的数据，返回 400，msg="该单位下存在对接人，无法删除"
  - **V1.4.7**：同时校验 project.category_id，若该单位已绑定项目，返回 400，msg="该单位下存在项目，无法删除"
  - 删除成功记录操作日志（oper_type=category_delete）
- **权限**：管理员（V1.4.2 角色简化后）

---

# 4. 对接人接口（原客户库，V1.4.7 语义变更）

### 4.1 获取对接人列表（分页）

- **请求**：`GET /api/customer/list`
- **Query 参数**：`pageNum, pageSize, categoryId(可选,按客户单位过滤), customerName(可选,模糊搜索对接人姓名)`
- **返回 data**：分页结构 `{items, total, pageNum, pageSize}`
- **items 字段**：`id, categoryId, categoryName(所属单位名), customerName(对接人姓名), remark, createTime`
- **权限**：全部角色

### 4.2 获取对接人详情

- **请求**：`GET /api/customer/detail/{id}`
- **返回 data**：`{ id, categoryId, customerName, remark }`
- **权限**：全部角色

### 4.3 新增对接人

- **请求**：`POST /api/customer/add`
- **入参**（JSON Body）：

```json
{
  "categoryId": 1,
  "customerName": "李主任",
  "remark": "项目对接人，电话..."
}
```

- **返回 data**：`{ "id": 1 }`
- **业务规则**：记录操作日志（oper_type=customer_create）
- **权限**：管理员（V1.4.2 角色简化后）

### 4.4 修改客户

- **请求**：`POST /api/customer/update`
- **入参**（JSON Body）：`{ id, categoryId, customerName, remark }`
- **返回 data**：null
- **业务规则**：记录操作日志（oper_type=customer_update）
- **权限**：管理员（V1.4.2 角色简化后）

### 4.5 删除客户（物理删除）

- **请求**：`POST /api/customer/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **业务规则**：
  - 删除前查询 project 表，若存在 customer_id=当前ID 的数据，返回 400，msg="该客户存在关联项目，无法删除"
  - 删除成功记录操作日志（oper_type=customer_delete）
- **权限**：管理员（V1.4.2 角色简化后）

### 4.6 客户封面上传（V1.3 新增，V1.4.5 补录文档）

- **请求**：`POST /api/customer/cover/upload`（multipart/form-data）
- **form-data 字段**：`file`（图片文件）、`customerId`
- **返回 data**：`{ "coverImage": "cover/xxx.png" }`
- **业务规则**：
  - 仅支持 jpg / png / webp（按文件头魔数校验，V1.4.5 起——Content-Type 伪造或文件损坏将返回 400）
  - 上传成功自动删除旧封面文件
- **权限**：管理员

### 4.7 客户封面移除（V1.3 新增，V1.4.5 补录文档）

- **请求**：`POST /api/customer/cover/remove`
- **入参**（JSON Body）：`{ "customerId": 1 }`
- **返回 data**：null
- **权限**：管理员

---

# 5. 流程模板接口

### 5.1 获取模板列表

- **请求**：`GET /api/flowTemplate/list`
- **返回 data**：模板数组（不分页），字段：`id, templateName, createUserName, createTime`
- **权限**：全部角色

### 5.2 获取模板详情（含节点+连线，节点关联节点模板）

- **请求**：`GET /api/flowTemplate/detail/{id}`
- **返回 data**：

```json
{
  "id": 1,
  "templateName": "标准IP设计流程",
  "nodes": [
    {
      "id": 1,
      "nodeTemplateId": 1,
      "nodeTitle": "需求对齐",
      "nodeRemark": "与客户确认需求",
      "sort": 1,
      "posX": 100.00,
      "posY": 200.00,
      "formFields": []
    }
  ],
  "edges": [
    {
      "id": 1,
      "sourceNodeId": 1,
      "targetNodeId": 2,
      "label": ""
    }
  ]
}
```

- **说明**：V1.4 流程模板为纯流程编排，`nodeTemplateId` 关联节点模板，表单字段定义在节点模板库（`formFields` 恒为空数组，仅保留字段兼容）
- **权限**：全部角色

### 5.3 新增流程模板（整图提交）

- **请求**：`POST /api/flowTemplate/add`
- **入参**（JSON Body）：

```json
{
  "templateName": "标准IP设计流程",
  "nodes": [
    {
      "nodeTemplateId": 1,
      "nodeTitle": "需求对齐",
      "nodeRemark": "",
      "sort": 1,
      "posX": 100.00,
      "posY": 200.00
    }
  ],
  "edges": [
    {
      "sourceNodeId": 1,
      "targetNodeId": 2,
      "label": ""
    }
  ]
}
```

- **返回 data**：`{ "id": 1 }`
- **业务规则**：
  - 单事务内插入模板、节点、连线（V1.4 表单定义来自节点模板，不在此写入）
  - 记录操作日志（oper_type=template_create）
- **权限**：管理员（V1.4.2 角色简化后）

### 5.4 修改流程模板（整图全量覆盖）

- **请求**：`POST /api/flowTemplate/update`
- **入参**（JSON Body）：

```json
{
  "id": 1,
  "templateName": "新模板名",
  "nodes": [
    {
      "id": 1,
      "nodeTemplateId": 1,
      "nodeTitle": "需求对齐",
      "nodeRemark": "",
      "sort": 1,
      "posX": 100.00,
      "posY": 200.00
    },
    {
      "nodeTemplateId": 2,
      "nodeTitle": "新增节点",
      "nodeRemark": "",
      "sort": 2,
      "posX": 400.00,
      "posY": 200.00
    }
  ],
  "edges": [
    {
      "id": 1,
      "sourceNodeId": 1,
      "targetNodeId": 2,
      "label": ""
    }
  ]
}
```

- **返回 data**：null
- **业务规则**：
  - **整图全量覆盖**：单事务内先物理删除该模板下所有节点、连线，再重新插入（表单定义来自节点模板，不在此写入）
  - 节点带 id 表示已有节点更新，不带 id 表示新增节点
  - 记录操作日志（oper_type=template_update）
- **权限**：管理员（V1.4.2 角色简化后）

### 5.5 删除流程模板（物理删除）

- **请求**：`POST /api/flowTemplate/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **业务规则**：
  - 单事务内物理删除模板、模板节点、模板连线、模板表单定义
  - 模板与项目深度解绑，删除不影响已创建的历史项目
  - 记录操作日志（oper_type=template_delete）
- **权限**：管理员（V1.4.2 角色简化后）

---

# 5-1. 节点模板接口（V1.3 新增，V1.4.3 支持图标）

> 节点模板库是画布节点的可选来源：项目画布与流程模板编辑页只能从节点模板库选类型新增节点；写操作仅管理员。

### 5-1.1 查询全部节点模板

- **请求**：`GET /api/nodeTemplate/list`
- **返回 data**：节点模板数组（不分页），字段 `id, nodeTitle, nodeRemark, icon, sort, formFields`
  - `icon`：预设图标组件名（如 `Document`）或自定义上传相对路径（`node_icon/xxx.svg`）；为空则前端按标题兜底
  - `formFields[].fieldType`：`text_single / text_multi / select / image（上传图像）/ link（链接）`（V1.4.3）
- **权限**：全部角色

### 5-1.2 新增节点模板

- **请求**：`POST /api/nodeTemplate/add`
- **入参**（JSON Body）：`{ nodeTitle, nodeRemark, icon, sort, formFields }`（formFields 结构同模板表单字段：fieldLabel/fieldType/selectOptions/sort；fieldType 支持 image/link）
- **返回 data**：`{ "id": 1 }`
- **业务规则**：记录操作日志（oper_type=node_template_create）
- **权限**：仅管理员

### 5-1.3 自定义图标上传（V1.4.3 新增）

- **请求**：`POST /api/nodeTemplate/icon/upload`（multipart，字段名 `file`）
- **返回 data**：`{ "iconPath": "node_icon/ab12cd34.svg" }`
- **业务规则**：仅支持 jpg/png/svg，≤1MB；返回相对路径供 icon 字段使用
- **权限**：仅管理员
- **权限**：仅管理员

### 5-1.4 修改节点模板

- **请求**：`POST /api/nodeTemplate/update`
- **入参**（JSON Body）：`{ id, nodeTitle, nodeRemark, icon, sort, formFields }`
- **返回 data**：null
- **业务规则**：记录操作日志（oper_type=node_template_update）
- **权限**：仅管理员

### 5-1.5 删除节点模板

- **请求**：`POST /api/nodeTemplate/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **业务规则**：
  - 物理删除；已生成的流程模板与项目节点为值拷贝，不受影响
  - 记录操作日志（oper_type=node_template_delete）
- **权限**：仅管理员

---

# 6. 模板节点连线接口

> 注：模板连线的增删通常通过 5.4 整图提交完成；以下独立接口供前端单条操作使用

### 6.1 新增模板连线

- **请求**：`POST /api/flowTemplateEdge/add`
- **入参**（JSON Body）：`{ templateId, sourceNodeId, targetNodeId, label }`
- **返回 data**：`{ "id": 1 }`
- **权限**：管理员（V1.4.2 角色简化后仅管理员）
- **业务规则**：
  - source/target 节点必须存在于该模板下，否则 400；**允许自环**（source == target，V1.4.5 修复此前自环被误报"节点不存在"的 bug）
  - V1.4.5 起记录审计日志（flow_edge_add），操作人为真实登录用户

### 6.2 删除模板连线

- **请求**：`POST /api/flowTemplateEdge/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **权限**：管理员（V1.4.2 角色简化后仅管理员）
- **业务规则**：V1.4.5 起记录审计日志（flow_edge_delete），操作人为真实登录用户

---

# 7. 项目基础接口

### 7.1 新建项目（可选择模板实例化）

- **请求**：`POST /api/project/create`
- **入参**（JSON Body）：

```json
{
  "projectName": "熊猫IP设计项目",
  "categoryId": 1,
  "contactCustomerIds": [12, 13],
  "projectDesc": "为青岛博物馆设计熊猫IP形象",
  "expectTime": "2026-10-01 00:00:00",
  "designerRelUserIdList": [2, 3],
  "templateId": 1
}
```

- **入参说明（V1.4.7）**：
  - `categoryId`：**必填**，归属客户单位（customer_category.id）
  - `contactCustomerIds`：**必填且至少 1 人**，客户对接人（customer.id），必须全部属于该单位，否则 400
  - 后端同时把 `contactCustomerIds[0]` 写入 `project.customer_id`（首位对接人，兼容保留）
- **返回 data**：`{ "projectId": 1 }`
- **业务规则**：
  - templateId 不为空时，执行模板实例化（值拷贝节点+连线+表单定义，ID重映射），详见 Database.md 模板实例化规则
  - templateId 为空时，创建空项目（无节点）
  - 项目默认状态 = 进行中
  - 记录操作日志（oper_type=project_create，related_project_id=新项目ID）
- **权限**：管理员（V1.4.2 角色简化后）

### 7.2 项目列表查询（分页）

- **请求**：`GET /api/project/list`
- **Query 参数（V1.4.7）**：`pageNum, pageSize, projectName(模糊), categoryId(按客户单位), projectStatus, createTimeStart(立项时间起,含), createTimeEnd(立项时间止,含)`
- **返回 data**：分页结构 `{items, total, pageNum, pageSize}`
- **items 字段**：

```json
{
  "id": 1,
  "projectName": "熊猫IP设计",
  "categoryId": 1,
  "companyName": "青岛博物馆",
  "customerId": 12,
  "customerName": "李主任",
  "contactNames": "李主任、王经理",
  "designerNames": "张三、李四",
  "createTime": "2026-08-30 10:00:00",
  "expectTime": "2026-10-01 00:00:00",
  "coverImage": null,
  "projectStatus": "进行中",
  "progressPercent": 40
}
```

- **字段说明**：`companyName` 客户单位名；`customerName` 首位对接人；`contactNames` 全部对接人（顿号分隔）；`createTime` 即立项时间；`progressPercent` 仅内部使用，客户门户不展示
- **权限**：全部角色；**客户账号自动按所属客户单位隔离**（只返回 `category_id` = 其对接人所属单位的项目，即同单位全部项目，不再是仅本人项目）

### 7.3 项目详情（含节点+连线+设计师）

- **请求**：`GET /api/project/detail/{projectId}`
- **返回 data**：

```json
{
  "id": 1,
  "projectName": "熊猫IP设计",
  "categoryId": 1,
  "companyName": "青岛博物馆",
  "customerId": 12,
  "customerName": "李主任",
  "projectDesc": "项目描述",
  "expectTime": "2026-10-01 00:00:00",
  "projectStatus": "进行中",
  "createUserName": "admin",
  "createTime": "2026-08-30 10:00:00",
  "designerList": [
    { "userId": 2, "realName": "张三" },
    { "userId": 3, "realName": "李四" }
  ],
  "contactList": [
    { "customerId": 12, "customerName": "李主任" },
    { "customerId": 13, "customerName": "王经理" }
  ],
  "nodes": [
    {
      "id": 1,
      "nodeTitle": "需求对齐",
      "nodeRemark": "",
      "sort": 1,
      "posX": 100.00,
      "posY": 200.00,
      "hasForm": true,
      "formFilled": false,
      "attachmentCount": 0,
      "icon": null
    }
  ],
  "edges": [
    {
      "id": 1,
      "sourceNodeId": 1,
      "targetNodeId": 2,
      "label": ""
    }
  ]
}
```

- **节点排序（V1.4.7）**：`nodes` 按 `posX → posY → sort → id` 升序返回（即画布从左到右、从上到下），修复"删除节点后重新添加，客户端看到顺序跑到最后"的问题
- **权限**：全部角色；客户账号只能看本客户单位的项目，跨单位 403

### 7.4 修改项目顶层基础信息

- **请求**：`POST /api/project/updateBase`
- **入参**（JSON Body）：

```json
{
  "id": 1,
  "projectName": "新名称",
  "categoryId": 1,
  "contactCustomerIds": [12, 13],
  "projectDesc": "新描述",
  "expectTime": "2026-11-01 00:00:00",
  "designerRelUserIdList": [2, 3, 4]
}
```

- **返回 data**：null
- **业务规则**：
  - `contactCustomerIds` 与 `designerRelUserIdList` 均为全量覆盖（先删后插）
  - 对接人必须属于 `categoryId` 指定单位，否则 400；更新后同步刷新 `project.customer_id`
  - 记录操作日志（oper_type=project_update）
- **权限**：管理员（V1.4.2 角色简化后）

### 7.5 项目归档

- **请求**：`POST /api/project/archive`
- **入参**（JSON Body）：`{ "projectId": 1 }`
- **返回 data**：null
- **业务规则**：project_status 更新为"已归档"，记录操作日志（oper_type=project_archive）
- **权限**：管理员（V1.4.2 角色简化后）

### 7.6 取消归档

- **请求**：`POST /api/project/unArchive`
- **入参**（JSON Body）：`{ "projectId": 1 }`
- **返回 data**：null
- **业务规则**：project_status 更新为"进行中"，记录操作日志（oper_type=project_unarchive）
- **权限**：管理员（V1.4.2 角色简化后）

### 7.7 删除项目（物理删除，全部业务数据销毁，日志保留）

- **请求**：`POST /api/project/delete`
- **入参**（JSON Body）：`{ "projectId": 1 }`
- **返回 data**：null
- **业务规则**：
  - **已归档项目禁止直接删除**，返回 400，msg="已归档项目请先取消归档后再删除"
  - 单事务内物理删除：项目、项目节点、节点连线、节点表单值、附件、评论、项目-设计师关联、项目相关消息
  - 服务器本地磁盘上的附件文件同步删除
  - 操作审计日志永久留存（oper_type=project_delete，related_project_id 保留已删项目ID）
- **权限**：管理员（V1.4.2 角色简化后）

### 7.8 项目封面上传（V1.3 新增，V1.4.5 补录文档）

- **请求**：`POST /api/project/cover/upload`（multipart/form-data）
- **form-data 字段**：`file`（图片文件）、`projectId`
- **返回 data**：`{ "coverImage": "cover/xxx.png" }`
- **业务规则**：
  - 仅支持 jpg / png / webp（按文件头魔数校验，V1.4.5 起——Content-Type 伪造或文件损坏将返回 400）
  - 上传成功自动删除旧封面文件；归档项目禁止上传
- **权限**：管理员（V1.4.2 角色简化后）

### 7.9 项目封面移除（V1.3 新增，V1.4.5 补录文档）

- **请求**：`POST /api/project/cover/remove`
- **入参**（JSON Body）：`{ "projectId": 1 }`
- **返回 data**：null
- **权限**：管理员（V1.4.2 角色简化后）

---

# 8. 项目画布节点接口

> 全部角色均可增删改任意项目节点；**项目归档状态禁止调用**

### 8.1 新增节点

- **请求**：`POST /api/projectNode/add`
- **入参**（JSON Body）：

```json
{
  "projectId": 1,
  "nodeTemplateId": 1,
  "sort": 99,
  "posX": 300.00,
  "posY": 300.00
}
```

- **返回 data**：`{ "id": 1 }`
- **业务规则**：
  - 节点标题、节点备注取自所选节点模板（nodeTemplateId），未预设的节点模板返回 400"节点模板不存在"
  - 节点表单字段**从节点模板 form_fields 值拷贝**（V1.4：表单定义唯一来源是节点模板库），项目运行中可填写值、不可改结构
  - 记录操作日志（oper_type=node_create，related_project_id）
  - 触发消息推送（msg_type=node_create）
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户 403）

### 8.2 修改节点

- **请求**：`POST /api/projectNode/update`
- **入参**（JSON Body）：`{ id, nodeTitle, nodeRemark, sort, posX, posY }`
- **返回 data**：null
- **业务规则**：
  - 记录操作日志（oper_type=node_update）
  - 触发消息推送（msg_type=node_update）
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户 403）

### 8.3 批量更新节点坐标（拖拽防抖提交）

- **请求**：`POST /api/projectNode/batchUpdatePositions`
- **入参**（JSON Body）：

```json
{
  "projectId": 1,
  "positions": [
    { "id": 1, "posX": 150.50, "posY": 220.00 },
    { "id": 2, "posX": 400.00, "posY": 220.00 }
  ]
}
```

- **返回 data**：null
- **业务规则**：
  - 前端拖拽结束后防抖调用，避免高频单条请求
  - 单事务内批量更新
  - 不触发消息推送（仅坐标变化，非内容变更）
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户 403）

### 8.4 删除节点（物理删除，连带连线+表单数据）

- **请求**：`POST /api/projectNode/delete`
- **入参**（JSON Body）：`{ "nodeId": 1 }`
- **返回 data**：null
- **业务规则**：
  - 单事务内级联物理删除：节点备注、节点表单填写值、以该节点为 source/target 的全部连线
  - 节点下的附件不自动删除（附件保留在项目中，project_node_id 变为无效值，前端不再展示）
  - 记录操作日志（oper_type=node_delete）
  - 触发消息推送（msg_type=node_delete）
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户 403）

### 8.5 获取项目节点表单定义与填写值

- **请求**：`GET /api/projectNode/getForm/{projectNodeId}`
- **返回 data**：

```json
{
  "fields": [
    {
      "id": 1,
      "fieldLabel": "需求描述",
      "fieldType": "text_multi",
      "selectOptions": null,
      "sort": 1,
      "fieldValue": "用户已填写的内容"
    }
  ]
}
```

- **业务规则**：临时新增的节点（无表单记录）返回空数组；`fieldType` 支持 `text_single / text_multi / select / image / link`（V1.4.3：image 的 fieldValue 存相对路径，link 存 URL）
- **权限**：全部角色（客户也可读，客户门户只读展示）

### 8.6 节点表单「上传图像」字段图片上传（V1.4.3 新增）

- **请求**：`POST /api/projectNode/formImage/upload`（multipart，字段名 `file`）
- **返回 data**：`{ "imagePath": "node_form/ab12cd34.png" }`
- **业务规则**：仅支持 jpg/png/webp，≤5MB；仅返回路径不落库，由前端保存表单时写入 field_value；客户账号禁止（403）
- **权限**：登录即可（除客户）

### 8.7 保存项目节点表单填写内容

- **请求**：`POST /api/projectNode/saveFormValue`
- **入参**（JSON Body）：

```json
{
  "projectNodeId": 1,
  "formValueList": [
    { "id": 1, "fieldValue": "填写内容1" },
    { "id": 2, "fieldValue": "选项A" }
  ]
}
```

- **返回 data**：null
- **业务规则**：
  - 全量覆盖保存，后提交覆盖先提交
  - 记录操作日志（oper_type=node_form_value_update）
  - 触发消息推送（msg_type=form_update）
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户 403）；归档项目禁止调用

---

# 9. 项目节点连线接口

> 全部角色均可增删项目节点连线；**项目归档状态禁止调用**

### 9.1 新增节点连线

- **请求**：`POST /api/projectNodeEdge/add`
- **入参**（JSON Body）：`{ projectId, sourceNodeId, targetNodeId, label }`
- **返回 data**：`{ "id": 1 }`
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户账号 403）
- **业务规则**：
  - source/target 节点必须存在于该项目下，否则 400；**允许自环**（source == target，V1.4.5 修复此前自环被误报"节点不存在"的 bug）
  - 归档项目禁止调用

### 9.2 删除节点连线

- **请求**：`POST /api/projectNodeEdge/delete`
- **入参**（JSON Body）：`{ "id": 1 }`
- **返回 data**：null
- **权限**：全部内部角色（管理员、普通；V1.4.2 角色简化后，客户账号 403）
- **业务规则**：归档项目禁止调用

---

# 10. 附件接口

### 10.1 上传附件（绑定节点）

- **请求**：`POST /api/attachment/upload`
- **Content-Type**：`multipart/form-data`
- **form-data 字段**：
  - `file`：文件
  - `projectId`：项目ID
  - `projectNodeId`：节点ID
- **返回 data**：`{ id, fileName, filePath, fileSize }`
- **业务规则**：
  - 单文件最大 1G
  - 存储路径：`uploads/YYYYMMDD/UUID_原始文件名`（日期隔离 + UUID 防重名）
  - 记录操作日志（oper_type=attachment_upload）
- **权限**：全部角色；归档项目禁止上传

### 10.2 获取节点附件列表

- **请求**：`GET /api/attachment/list`
- **Query 参数**：`projectNodeId`
- **返回 data**：附件数组（不分页）

```json
[
  {
    "id": 1,
    "fileName": "设计稿.psd",
    "fileSize": 10485760,
    "uploadUserId": 2,
    "uploadUserName": "张三",
    "createTime": "2026-08-30 10:00:00"
  }
]
```

- **权限**：全部角色

### 10.3 删除附件（上传本人或管理员）

- **请求**：`POST /api/attachment/delete`
- **入参**（JSON Body）：`{ "attachmentId": 1 }`
- **返回 data**：null
- **业务规则**：
  - 非上传本人且非管理员返回 403，msg="无权删除他人附件"
  - 同步删除服务器本地磁盘文件
  - 记录操作日志（oper_type=attachment_delete）
- **权限**：附件上传本人 或 管理员；归档项目禁止删除

### 10.4 文件下载

- **请求**：`GET /api/attachment/download/{attachmentId}`
- **返回**：文件流（Content-Disposition: attachment）
- **权限**：全部角色

### 10.5 获取某项目下全部文件（文件管理页，V1.4 新增）

- **请求**：`GET /api/attachment/listByProject`
- **Query 参数**：`projectId`
- **返回 data**：文件数组（不分页）

```json
[
  {
    "id": 1,
    "fileName": "设计稿.psd",
    "fileSize": 10485760,
    "projectId": 1,
    "projectNodeId": 2,
    "nodeTitle": "IP设计输出",
    "uploadUserId": 2,
    "uploadUserName": "张三",
    "createTime": "2026-08-30 10:00:00"
  }
]
```

- **说明**：返回该项目下所有节点的附件，含所属节点标题（nodeTitle）；节点已删则 nodeTitle 为 null
- **权限**：全部角色

---

# 11. 评论接口

### 11.1 获取项目评论列表

- **请求**：`GET /api/comment/list`
- **Query 参数**：`projectId`
- **返回 data**：评论数组（不分页，按时间倒序）

```json
[
  {
    "id": 1,
    "projectId": 1,
    "content": "这个方案不错",
    "createUserId": 2,
    "createUserName": "张三",
    "createTime": "2026-08-30 10:00:00"
  }
]
```

- **权限**：全部角色

### 11.2 新增评论

- **请求**：`POST /api/comment/add`
- **入参**（JSON Body）：`{ projectId, content }`
- **返回 data**：`{ "id": 1 }`
- **业务规则**：
  - 记录操作日志（oper_type=comment_create）
  - 触发消息推送（msg_type=comment_create）
- **权限**：全部角色；归档项目禁止新增

### 11.3 删除自己评论

- **请求**：`POST /api/comment/delete`
- **入参**（JSON Body）：`{ "commentId": 1 }`
- **返回 data**：null
- **业务规则**：
  - 非发布本人返回 403，msg="无权删除他人评论"
  - 记录操作日志（oper_type=comment_delete）
- **权限**：评论发布本人；归档项目禁止删除

---

# 12. 消息中心接口

### 12.1 获取本人消息列表（分页）

- **请求**：`GET /api/message/myList`
- **Query 参数**：`pageNum, pageSize, isRead(可选), includeRoutine(可选，默认 false)`
  - **V1.4.21 消息降噪**：默认只返回**关键通知**（`customer_review` / `evaluation_create` / `comment_create`）；
    传 `includeRoutine=true` 才把常规操作（`node_create` / `node_update` / `node_delete` / `form_update`）的**历史**消息一并带出
- **返回 data**：分页结构 `{items, total, pageNum, pageSize}`
- **items 字段**：

```json
{
  "id": 1,
  "projectId": 1,
  "msgType": "node_create",
  "msgContent": "张三 在项目「熊猫IP设计」中新增了节点：IP设计输出",
  "isRead": 0,
  "createTime": "2026-08-30 10:00:00"
}
```

- **权限**：登录用户

### 12.2 设置消息已读

- **请求**：`POST /api/message/read`
- **入参**（JSON Body）：`{ "messageId": 1 }`
- **返回 data**：null
- **权限**：登录用户

### 12.3 全部标记已读（V1.4 新增，V1.4.21 扩展）

- **请求**：`POST /api/message/readAll`
- **入参**（JSON Body，可省略）：`{ "projectId": 1, "includeRoutine": false }`
  - `projectId`：传则只标记该项目的消息（消息中心按项目分组的「本项目全部已读」）；不传=全部项目
  - `includeRoutine`：默认 false，只标记关键通知；传 true 时连常规操作消息一起标记
- **返回 data**：`{ "count": 9 }`（count = 本次标记为已读的条数）
- **业务规则**：将本人未读消息批量标记为已读；默认口径与消息中心展示一致，避免出现「页面只看到 11 条、提示却说标记了 81 条」
- **权限**：登录用户

---

# 13. 操作审计日志接口

> 日志只可读，无修改删除接口

### 13.1 获取全局全部审计日志（分页）

- **请求**：`GET /api/sysOperationLog/globalList`
- **Query 参数**：`pageNum, pageSize, operUserId(可选), startTime(可选), endTime(可选), operType(可选)`
- **返回 data**：分页结构 `{items, total, pageNum, pageSize}`
- **items 字段**：`id, operUserId, operUserName, operTime, operType, operDesc, relatedProjectId`
- **权限**：管理员（V1.4.2 角色简化后）

### 13.2 获取单个项目内部操作记录

- **请求**：`GET /api/sysOperationLog/projectLog`
- **Query 参数**：`projectId`
- **返回 data**：日志数组（不分页，按时间倒序）
- **权限**：全部角色（仅可查传入 projectId 对应项目）

---

# 14. 报表导出接口

### 14.1 导出项目列表 Excel

- **请求**：`GET /api/report/exportProject`
- **Query 参数（V1.4.7）**：`projectStatus(可选), categoryId(可选,按客户单位), startTime(可选), endTime(可选)`
- **返回**：文件流下载（Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet）
- **文件名**：`项目列表_YYYYMMDD.xlsx`
- **导出列（V1.4.7）**：项目名称、客户单位、客户对接人、参与设计师、立项时间、预计结束时间、项目状态
- **样式**：表头加粗+背景色，列宽自适应
- **权限**：管理员（V1.4.2 角色简化后）

---

## 消息推送规则（后端 service 层自动触发）

> **V1.4.21 消息降噪**：消息中心只承载**关键事件**。常规操作（节点增删改、表单填写）**不再生成消息**，
> 但仍全量写入审计日志 `sys_operation_log`（「系统管理 → 日志」），追溯能力不受影响。
> 策略收敛在 `app/services/message_service.py` 的 `NOTIFY_TYPES` / `ROUTINE_TYPES` 两处常量，调用方无需改动。
> 历史遗留的常规消息保留在库中，客户端默认不展示（`includeRoutine` 开关可查看）。

### 触发事件与推送范围

| 触发事件 | msg_type | 是否推送 | 推送范围 |
|---|---|---|---|
| 客户提交审核 | customer_review | ✅ 关键 | 项目创建人 + 项目关联设计师（操作人为客户，天然不在其中） |
| 客户提交满意度评价 | evaluation_create | ✅ 关键 | 项目创建人 + 项目关联设计师 + 全部管理员 |
| 发表评论 | comment_create | ✅ 关键 | 项目创建人 + 项目关联设计师（排除操作人） |
| 新增节点 | node_create | ❌ 常规（仅审计日志） | — |
| 修改节点 | node_update | ❌ 常规（仅审计日志） | — |
| 删除节点 | node_delete | ❌ 常规（仅审计日志） | — |
| 表单填写修改 | form_update | ❌ 常规（仅审计日志） | — |

### 消息内容模板

| msg_type | msg_content 模板 | 示例 |
|---|---|---|
| customer_review | `{客户名} 在项目「{项目名}」的「{节点名}」完成审核：{审核结论}` | 周峰 在项目「熊猫IP设计」的「八级节点审核」完成审核：通过 |
| evaluation_create | `客户已对项目「{项目名}」提交满意度评价` | 客户已对项目「熊猫IP设计」提交满意度评价 |
| comment_create | `{操作人} 在项目「{项目名}」中发表了评论：{评论前20字}...` | 张三 发表了评论：这个方案不错，建议调... |
| node_create / node_update / node_delete / form_update | 模板保留但默认不再推送（见上方降噪说明） | — |

> 前端展示约定：`msg_content` 中第一个「」恒为项目名，客户端据此把消息按项目分组，
> 并把文案精简为「操作人 + 动作」（见 `frontend/src/utils/message.js`）。

---

## 后续迭代接口预留（V1 不实现）

1. 首页仪表盘统计接口
2. 多维度统计图表接口
3. 对象存储文件对接接口
4. 画布协同锁相关接口
5. 表单必填校验、更多表单组件接口

---

# 15. 部门管理接口（V1.4 新增，仅管理员）

> 部门仅做人员组织分组，**不携带权限**（V1.4.1 起 role 字段弃用，恒为 NULL）。权限由用户自身角色决定。

### 15.1 查询全部部门（含人数）

- **请求**：`GET /api/sysDept/list`
- **返回 data**：`[{ "id": 1, "deptName": "研发部", "deptType": "internal", "userCount": 3, "createTime": "..." }]`
- **权限**：仅管理员

### 15.2 新增部门

- **请求**：`POST /api/sysDept/add`
- **入参**（JSON Body）：`{ "deptName": "运营部", "deptType": "internal" }`
- **业务规则**：部门名唯一；无需指定权限模板
- **返回 data**：`{ "deptId": 4 }`

### 15.3 重命名部门

- **请求**：`POST /api/sysDept/update`
- **入参**（JSON Body）：`{ "id": 4, "deptName": "运营中心" }`

### 15.4 删除部门

- **请求**：`POST /api/sysDept/delete`
- **入参**（JSON Body）：`{ "id": 4 }`
- **业务规则**：部门下仍有用户时返回 400（需先调整用户部门）；删除仅解除组织分组，不影响用户权限

---

# 16. 权限体系（V1.4.2 简化为两类角色）

| 角色 | 权限 | 说明 |
|---|---|---|
| **管理员** | 全部权限（含用户/部门/节点模板管理等系统管理） | 初始 admin；也可给其他账号分配 |
| **普通** | 查看全部数据 + 项目内执行（加节点/填表单/评论/附件）；**不能**建项目/管客户/建模板/看日志报表/系统管理 | 原「设计师」权限 |
| **客户** | 独立只读门户，看**所属客户单位**的全部项目（V1.4.7 起；不展示节点进度，展示立项/预计结束时间与倒计时） | 客户账号自动获得，写操作一律 403 |

- 写权限收敛：客户单位/对接人/流程模板/项目/报表/审计日志等业务写操作**仅管理员**；项目节点/表单/评论/附件「登录即可（除客户）」。

# 17. 客户门户（V1.4 新增）

- 客户账号登录后进入 `/client` 独立界面（前端路由），后端接口复用：
  - `GET /api/project/list`（客户按**所属客户单位**隔离，返回同单位全部项目；支持 projectName / projectStatus / createTimeStart / createTimeEnd 筛选）
  - `GET /api/project/detail/{projectId}`（客户只能看本客户单位的项目，跨单位 403）
  - 门户**不展示节点进度/总进度**，改为展示立项时间（createTime）、预计结束时间（expectTime）与倒计时；`projectStatus=已归档` 在门户展示为「已结项」
  - `GET /api/projectNode/getForm/{projectNodeId}`（只读，image/link 字段可见）
- 客户所有写操作（节点/表单/评论/附件/项目/客户）均被后端 403 拦截。

# 18. AI 助手接口（V1.4.8 新增）

> 模块前缀 `/api/ai`，鉴权同全局（`Authorization: Bearer <token>`）。流式对话为 SSE（`text/event-stream`）。
> **数据隔离**：客户账号调用 `POST /chat/stream` 时，结构化知识库构建强制按 `Project.category_id == 所属单位` 过滤，只能问到本公司的项目数据；员工账号全量可见。

### 18.1 会话列表

- `GET /api/ai/conversations`
- **返回**：`data: [{ id, title, pinned, createdAt, updatedAt }]`，按 `pinned desc → updatedAt desc` 排序（置顶优先），仅本人未删除会话；`pinned` 为 V1.4.9 新增置顶标记

### 18.2 新建会话

- `POST /api/ai/conversations`
- **返回**：`data: { id }`（初始 title 为「新对话」）

### 18.3 会话消息列表

- `GET /api/ai/conversations/{conversationId}/messages`
- **返回**：`data: [{ id, role, content, sources, createdAt }]`；`role ∈ {user, assistant}`；`sources` 为来源引用数组（空则 `[]`）
- **异常**：会话不存在、非本人会话、或已软删除均返回 400

### 18.4 删除会话（V1.4.9 起软删）

- `DELETE /api/ai/conversations/{conversationId}`
- **返回**：`data: null`；**软删除**：仅置 `is_deleted=true`，消息与审计日志保留（便于溯源），列表与消息接口均不再返回

### 18.5 重命名会话（V1.4.9 新增）

- `PATCH /api/ai/conversations/{conversationId}`
- **入参**：`{ title: string(1~128) }`
- **返回**：`data: null`；空标题回退为「新对话」；记录审计日志 `ai_conversation_rename`

### 18.6 置顶 / 取消置顶会话（V1.4.9 新增）

- `POST /api/ai/conversations/{conversationId}/pin`
- **入参**：`{ pinned: boolean }`
- **返回**：`data: null`；记录审计日志 `ai_conversation_pin`

### 18.7 流式对话（核心）

- `POST /api/ai/chat/stream`
- **入参**：`{ conversationId?: number, message: string(1~4000) }`；`conversationId` 为空则自动新建会话（title 取问题前 30 字）
- **返回**：SSE 流（`text/event-stream`），每个事件为 `data: {json}\n\n`，事件类型：
  - `delta`：`{ type:"delta", content:"增量文本" }`（打字机输出）
  - `error`：`{ type:"error", message:"错误描述" }`
  - `done`：`{ type:"done", conversationId, messageId, sources }`（正常结束，`messageId` 为已落库的 assistant 消息 ID，`sources` 为来源引用）
- **业务**：保存用户问题 → 构建结构化知识库（当前用户可见的全部项目文本，客户按单位隔离）注入上下文 → 调 LLM Provider 流式生成 → 保存完整回答；客户端中断（停止生成）时兜底保存已生成的部分内容
- **V1.4.9 加固**：
  - **身份绑定与数据隔离**：按登录账号自动注入身份（客户账号注入归属公司名，员工注入全量可见），**严禁反问公司/身份**；代码级安全约束强制追加，不随管理员可改的 system_prompt 变化
  - **防幻觉**：知识库为空（当前用户无可见项目）时，**直接短路返回固定话术，不调 LLM**，从根上杜绝编造
  - **速率限制**：per-user 滑动窗口（60 秒内最多 20 次，管理员豁免），超限返回 `error` 事件
  - **审计留痕**：每次提问写 `ai_chat` 日志（与用户消息同事务）
- **V1.4.16 数据供给改造**：
  - **移除联网搜索**：`chat/stream` 入参不再有 `webSearch`，仅走 `/chat/completions`；前端「联网搜索」开关一并移除
  - **结构化知识库全量注入**：每次提问实时读库，把当前用户可见的全部项目（进行中 + 已归档，已归档标注「已结项」）渲染成固定模板文本（项目名称 / 客户单位 / 对接人 / 我方负责人·设计师 / 立项时间 / 预计结束时间 / 项目状态）拼入 system prompt，替代原「关键词 + SQL LIKE」检索
  - **模型**：`deepseek-v4-flash`（`deepseek-chat`/`deepseek-reasoner` 已弃用，启动时自动升级）
- **异常**：未配置 API Key 返回 `error` 事件「AI 尚未配置 API Key」
- **V1.4.11 说明**：本轮为 BUG 修复版本，接口契约无变化。相关改动为健壮性加固——`file_service.remove_disk_file` 由只捕获 `OSError` 改为捕获 `Exception`，因此**删除封面 / 附件时若物理文件删除失败（被占用、权限不足或运行环境拦截），接口仍返回 200 且数据库记录已正确更新**，不再因磁盘副作用冒泡成 500。
- **V1.4.12 说明**：本轮为前端交互修复版本，接口契约无变化。改动集中在前端——项目详情页节点表单（`DynamicForm`）新增 `isDirty` 脏检测，切换节点 / 点画布空白 / 面板关闭 / 新增节点 / 归档前 / 离开详情页路由守卫处统一拦截未保存修改并提示「保存 / 放弃修改 / 取消」，避免编辑中切换导致未保存表单被静默覆盖。后端 `POST /api/projectNode/formValue/save` 等保存接口行为不变。

### 18.8 获取 AI 配置（仅管理员）

- `GET /api/ai/config`
- **返回**：`data: { systemPrompt, model, apiKey, baseUrl, temperature, maxTokens }`；`apiKey` 脱敏（`sk-4****7be2`）

### 18.9 更新 AI 配置（仅管理员）

- `PUT /api/ai/config`
- **入参**：`{ systemPrompt(必填,1~4000), model(必填,1~64), apiKey(可空), baseUrl(必填,1~256), temperature(0~2,默认0.7), maxTokens(1~32768,默认2048) }`
- **规则**：`apiKey` 传脱敏值（含 `****`）表示沿用旧值不修改；否则更新为新值；记录 `updatedBy`
# 19. 客户满意度评价接口（V1.4.17 新增）

### 19.1 客户提交评价

- `POST /api/evaluation/submit`
- **鉴权**：仅客户角色
- **入参**：`{ projectId(必填), designScore(1~5,必填), serviceScore(1~5,必填), productScore(1~5,必填), customerRemark(可空,≤2000) }`
- **返回**：`data: { designScore, serviceScore, productScore, customerRemark, evaluateTime }`
- **规则**：
  - 仅项目所属客户单位的客户账号可评（跨单位 403「无权评价该项目」）
  - 仅已归档项目可评（未归档 400「项目尚未归档，暂不能评价」）
  - 一次性锁定：已评价项目不可重复提交（400「该项目已评价，不可重复提交」）
  - 提交后向项目相关成员推送评价消息

### 19.2 查询评价

- `GET /api/evaluation/{projectId}`
- **鉴权**：全部登录角色
- **返回**：
  - 客户：公开 DTO `{ designScore, serviceScore, productScore, customerRemark, evaluateTime }`（不含反思；跨单位 403「无权查看该项目的评价」）
  - 内部：详情 DTO，额外含 `{ reflection, reflectionUserName, reflectionTime }`（反思人已删除时兜底「已删除用户」）
  - 未评价：`data: null`

### 19.3 保存内部反思（覆盖式）

- `POST /api/evaluation/reflection`
- **鉴权**：仅内部角色（普通/管理员，客户不可用）
- **入参**：`{ projectId(必填), reflection(必填,1~5000) }`
- **返回**：`data: null`
- **规则**：覆盖式写入；客户尚未评价时 400「客户尚未评价，暂不能填写反思」；反思内容对客户不可见
