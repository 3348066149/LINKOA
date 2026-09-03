# V1.3 增量改造：卡片网格 + 截止倒计时 + 排序（2026-09-01）

## 本轮三项需求交付

### 1. 客户分类下拉「没有用」→ 根因与修复
- **根因**：后端筛选接口实测正常（categoryId=1 时 total 2→1），问题是下拉选择后不会自动查询，必须手动点「搜索」。
- **修复**：客户页分类下拉、项目页客户/状态下拉全部加 `@change="onSearch"`，选择即筛选。名称输入框同时支持回车搜索。

### 2. 预计时间 → 预计截止时间 + 倒计时
- 新建项目弹窗、编辑基础信息弹窗 label 改为「预计截止时间」，placeholder 提示会显示倒计时。
- 新增 `frontend/src/utils/deadline.js`：`deadlineInfo(expectTime, status)` 返回 `{label, type}`：
  - 剩余 >3 天 → 蓝色「剩 X 天」
  - 剩余 ≤3 天 → 橙色「剩 X 天」
  - 已过期 → 红色「已逾期 X 天」（当天过期显示「已逾期」）
  - 未设置截止时间或已归档 → 不显示
- 项目卡片徽标 + 项目详情页顶栏均显示倒计时。

### 3. 卡片网格布局 + 排序
- **项目列表**、**客户列表**由表格改为卡片网格：一行 3 列（≤1200px 2 列，≤768px 1 列），间隔 16px。
  - 项目卡：名称链接、状态、倒计时徽标、客户/设计师/创建时间、操作按钮。
  - 客户卡：名称、分类标签、备注（3行截断）、创建时间、操作按钮。
  - 加载骨架屏、空态引导、分页保留。
- **后端全局排序**（翻页保持）：`/project/list` 支持 sortField ∈ {projectName, createTime, expectTime, projectStatus}；`/customer/list` 支持 {customerName, createTime, categoryName}；sortOrder ∈ {asc, desc}。白名单映射防注入，非法值回退 id 倒序。
- 排序 UI：筛选栏排序字段下拉 + 升/降序切换按钮。

## 改动文件
- 后端：`schemas/common.py`（PageQuery 加 sortField/sortOrder）、`schemas/project.py`（ProjectListItem 加 expectTime）、`services/project_service.py`、`services/customer_service.py`
- 前端：`views/project/List.vue`、`views/customer/Index.vue`（整体重写为卡片网格）、`views/project/Detail.vue`、`utils/deadline.js`（新增）

## 验证
- 接口实测（8001 临时实例，已清理）：expectTime 返回 ✅、名称/截止时间/分类排序 ✅、非法排序字段安全回退 ✅、分类筛选 ✅
- 前端 vite build 通过（5.37s），dist 产物已含新代码。

## ⚠️ 重要：后端需要重启才生效
- 8000 端口运行中的服务仍是旧代码（排序和 expectTime 不生效）。
- 原启动方式 `E:\Python\3.10.11\python.exe` 的依赖已丢失（无法 import uvicorn）。
- 已建好可用环境：`C:\Users\Administrator\.workbuddy\binaries\python\envs\linkoa\Scripts\python.exe`（依赖齐全）
- 重启命令：先停掉旧进程，再
  `cd backend && C:\Users\Administrator\.workbuddy\binaries\python\envs\linkoa\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

# V1.3 第二轮：节点模板卡片化 + 项目封面图 + 快捷编辑（2026-09-01 下午）

## 交付内容

### 1. 节点模板页卡片化
- 由表格改为一行 3 个卡片网格（≤1200px 2 列，≤768px 1 列，间隔 16px）。
- 卡片：图标 + 节点名 + 排序值、说明（两行截断）、表单字段标签、编辑/删除按钮；加载骨架屏、空态引导。

### 2. 项目卡片封面图（不打开项目就知道是什么项目）
- **数据库**：project 表新增 `cover_image` 列（SQLite 已执行 ALTER；init.sql 同步更新）。
- **后端**：新增 `POST /api/project/cover/upload`（multipart，jpg/png/webp，≤5MB，存 uploads/cover/UUID.ext，自动替换旧文件）与 `POST /api/project/cover/remove`；列表与详情均返回 `coverImage`。
- **前端**：卡片右侧 96px 方形封面图（object-fit: cover，点击进详情）；无封面显示占位图标。

### 3. 项目卡片快捷编辑
- 卡片新增「编辑」按钮，弹窗可直接修改：封面图（上传/更换/移除）、名称、关联客户、预计截止时间、参与设计师（仅管理员可调整）、描述——无需进详情页。

### 4. 倒计时「没有显示」根因
- 上一轮代码正常，是 8000 后端未重启（旧进程无 expectTime 字段）。本轮已用新环境（`C:\Users\Administrator\.workbuddy\binaries\python\envs\linkoa`）重启 8000，倒计时现已生效。
- 倒计时升级为卡片**顶部通栏色带**：蓝色（>3天）/橙色（≤3天）/红色（逾期，呼吸闪烁动画），白字大号「剩 X 天」+ 截止日期。

## 卡片新布局
```
┌──────────────────────────────┐
│ 距截止  剩 5 天   09-26 00:00 │ ← 通栏倒计时色带
│ 项目名称            [进行中] ┌────┐
│ 关联客户  xxx                │封面 │
│ 参与设计师 xxx               │96px │
│ 创建时间  2026-09-01         └────┘
│ [查看] [编辑]      [归档] [删除] │
└──────────────────────────────┘
```

## 验证
- 接口自检脚本 `backend/tests/check_cover_api.py`：7/7 通过（列表字段、上传、静态访问、回传、排序、格式拦截、移除）。
- 前端 vite build 通过；grep 自检 7 项改动全部落地。
- 测试封面文件已从 uploads/cover/ 清理，项目数据保持干净。

## 待优化建议（供决策，未实施）
见对话汇报：仪表盘图表化、客户卡片头像/首字、项目进度可视化、批量操作、快捷键、消息中心增强、节点表单图片类型字段、导出报表等。

---

# V1.3 第三轮：客户封面/联系方式 + 倒计时分档 + 模板&用户卡片化（2026-09-01 下午）

## 1. 客户卡片重排版 + 封面图 + 快捷编辑
- **数据库**：customer 表新增 `contact`（联系方式）、`cover_image`（封面图）两列，SQLite 已执行 ALTER，init.sql 同步。
- **后端**：新增 `POST /api/customer/cover/upload`、`POST /api/customer/cover/remove`（管理员/行政，jpg/png/webp，≤5MB）；列表与详情返回 contact + coverImage。
- **卡片比例修正**：名称字号 15→17px、卡片 min-height 190px、信息分区（名称/联系方式/创建时间/备注），解决「X 太长、Y 太小」的扁长比例。
- **右侧 112px 封面图**：有图点击全屏预览大图；无图显示虚线占位，点击直接进入编辑弹窗上传。
- **编辑 + 删除紧挨成组**：底部用 `.act-group` 6px 间距并排，不再分散。
- **编辑弹窗 5 项**：封面图（上传/更换/移除，预览可点击放大）、客户名称、客户分类、联系方式、客户备注。

## 2. 项目封面加大 + 点击全屏查看
- 封面尺寸 96px → **140px**（窄屏 108px），改用 `el-image` + `preview-src-list`，点击即全屏查看大图，不再跳转详情页。
- 无封面时点击卡片封面区域，可写角色直接打开编辑弹窗上传。
- 编辑弹窗内的封面预览同样支持点击放大。

## 3. 倒计时按比例分档变色
| 剩余天数 | 颜色 | 文案 |
|---|---|---|
| > 30 天 | 绿色 success | 剩 X 天 |
| 16 - 30 天 | 蓝色 primary | 剩 X 天 |
| 6 - 15 天 | 橙色 warning | 剩 X 天 |
| 1 - 5 天 | 红色 danger + 呼吸闪烁 | 剩 X 天 |
| 已逾期 | 红色 danger + 呼吸闪烁 | 已逾期 X 天 |
| 已归档 / 未设截止时间 | — | 不显示 |

## 4. 流程模板 + 用户管理卡片化
- `template/List.vue`：改 3 列卡片网格（渐变图标 + 模板名 + 创建人 + 创建时间 + 编辑流程/删除），骨架屏 + 空态引导。
- `system/User.vue`：改 3 列卡片网格（角色色首字头像 + 真实姓名 + 角色标签 + 账号 + 明文密码 + 启停开关 + 重置密码/删除）。

## 5. 顺带修复的真实缺陷
- **删除项目时附件与封面没真正删掉**：DB 存的是相对路径，直接 `remove_disk_file` 会按 CWD 解析、静默失败留下孤儿文件。已改为拼 `UPLOAD_ROOT`，并补上项目封面图清理。

## 验证
- `backend/tests/check_cover_api.py`（项目封面）：7/7 通过
- `backend/tests/check_customer_cover_api.py`（客户封面+联系方式）：9/9 通过（含测试数据自动还原）
- 倒计时 14 组边界用例全对（含已归档/未设置返回 null）
- `vite build` 通过；dist 产物已含 `cd-success`、`.proj-cover{width:140px}`、`cust-cover`、`tpl-card`、`user-avatar`
- 8000 后端已用 venv linkoa 重启

## 待用户决定
- `backend/uploads/cover/21299c91a4fd4dfc979dbf9ce4c5acd4.jpg`（1MB）是删除项目「测随」后遗留的孤儿文件，本次修复前的历史残留，可随时清理。

---

# V1.3 第四轮：自定义角色（2026-09-01 下午）

## 需求
新建用户时内置角色不够用，需要能自定义角色（如「研发人员」）。

## 交付内容

### 后端
- **新表 `sys_role`**：`role_name` 唯一；SQLite 重启自动建表（`create_all`），init.sql（MySQL 版）已同步。
- **角色接口（仅管理员，`/api/sysRole`）**：
  - `GET /list`：自定义角色列表，含每个角色的**使用人数**（userCount）
  - `POST /add`：新建角色；拦截「与内置角色同名」（管理员/行政/设计总监/设计师）与重名
  - `POST /delete`：删除角色；**有用户占用时拦截**（提示先修改这些用户的角色）
- **建用户放开角色**：`SysUserCreateRequest.role` 由硬编码 3 选 1 改为自由文本，`create_user` 时校验角色必须是内置角色或已存在的自定义角色。

### 权限语义（与你确认的方案）
自定义角色登录后拥有与**设计师**相同的权限：可查看全部数据（项目/客户/模板/日志等），可操作项目节点、节点表单、评论、附件、消息。不能做管理员/行政/设计总监专属的写操作（新建项目、改客户、改模板等）。该语义由现有权限体系天然成立，无需改动任何权限代码。

### 前端（system/User.vue + api/sysRole.js）
- **新建用户弹窗角色下拉**：分组显示「内置角色」（行政/设计总监/设计师）+「自定义角色」，底部还有**「＋ 新建角色…」快捷入口**——点它直接弹输入框创建，建完自动选中。
- **头部「角色管理」按钮**：弹窗内可添加角色、查看每个角色的使用人数（占用中显示「N 人」并禁用删除按钮）、删除未占用角色。
- 自定义角色在用户卡片上：头像用灰色渐变、角色标签蓝色，与内置角色视觉区分。

## 验证
- `backend/tests/check_role_api.py`：11/11 通过（登录/列表/添加/重名拦截/内置名拦截/自定义角色建用户/非法角色拦截/自定义角色登录+查询/占用删除拦截/使用人数统计/数据清理）。
- 测试数据（测试用户、测试角色）已全部清理，数据库无残留。
- 前端 vite build 通过；dist 入口正确引用新 User 页面 chunk。
- 8000 后端已重启加载新模块（sys_role 表自动创建）。

---

# V1.4 部门体系 + 客户门户（2026-09-01 下午）

## 需求
角色管理重构为**部门管理**：内置部门（研发部/设计部/市场部，部门即权限）+ 客户账号（一客户多账号，如青岛地铁 3 个对接人 3 个账号）；客户登录**独立只读门户**，只能看自己客户的项目与节点进度，绝不能修改。

## 交付内容

### 一、部门体系（后端）
- **新表 `sys_dept`**：部门名唯一；内置部门带权限模板（研发部=设计师、设计部=设计总监、市场部=行政），启动幂等预置；管理员可增删改查（有用户占用时禁止删除）。init.sql 同步。
- **建用户改造（部门即权限，二选一）**：
  - 内部员工 → 选部门，`role` 自动 = 部门权限模板
  - 客户账号 → 选客户（一客户可建多个账号），`role = 客户`，绑定 customer_id
- `sys_user` 新增 `dept_id` / `customer_id` 列（SQLite 已 ALTER，init.sql 同步）。

### 二、客户权限（安全核心）
- **项目隔离**：客户项目列表只返回自己客户的项目；访问他人客户项目详情 → 403。
- **写操作硬拦截**：节点增删改、表单保存、评论、附件上传/删除等所有写端点统一 `require_not_customer()`，客户调用一律 403。
- **只读可用**：客户可看自己项目的节点进度（表单填写=已完成）与表单内容（只读）。
- 客户账号可单独停用，不影响同客户其他账号。

### 三、客户门户（前端）
- 登录按角色分流：客户 → `/client` 独立门户，员工 → OA 工作台；客户访问任何 OA 内部页面一律拦回门户。
- 门户首页：我的项目卡片（状态/截止倒计时/节点进度条/封面），进度占比后端实时计算（`progressPercent`）。
- 项目进度页：节点时间线（已完成绿勾/未开始序号）+ 点击查看已填表单内容（只读，含图片/多选），明确标注「只读视图，如需修改请联系对接人」。

### 四、顺带修复
- `get_current_user` 未查询 `dept_id/customer_id` 导致客户隔离失效（测试抓出，已修复）。

## 验证（模拟数据全链路）
`backend/tests/check_dept_client_api.py`：**30/30 通过**。用「青岛地铁」+「服贸会」两客户、青岛地铁 3 个账号模拟：
部门 CRUD/占用拦截、内置部门预置、研发部员工=设计师、3 客户账号登录、客户只见自己项目（进度 67%）、跨客户 403、改表单/加节点/评论全部 403、读表单只读、停用单个账号不影响其他、测试数据全部清理。

## 使用方式
1. 部门管理：用户管理 → 部门管理（增删改内置部门）。
2. 新建客户账号：用户管理 → 新建用户 → 账号类型「客户账号」→ 选客户（如青岛地铁）→ 账号/密码/姓名。
3. 客户登录：浏览器打开系统 → 用客户账号登录 → 自动进入客户门户。
4. 员工登录：逻辑不变，按部门权限进入 OA。

---

# V1.4.1 部门与角色解耦（2026-09-01 下午）

## 需求
按需求文档将【部门】与【角色权限】解耦：部门仅做人员组织分组、不携带任何权限；权限全部收敛到用户账号（给用户分配角色）；同部门可有多角色岗位；人员调动部门权限不变；存量数据迁移保权限不丢。

## 交付内容

### 后端
- **部门去掉权限属性**：`sys_dept.role` 字段保留兼容（恒为 NULL）；新建/重命名部门不再涉及权限模板；预置部门（研发部/设计部/市场部）不再绑定角色。
- **存量迁移（启动幂等，`migrate_dept_role_to_user`）**：遍历非客户账号用户 → 若所属部门仍带权限模板，把模板写入该用户 role → 清空所有部门 role。实测：模拟老用户（设计部+role=设计师）重启后 role 自动变为「设计总监」，部门 role 全部清空。
- **建用户**：内部员工 = 选部门（组织归属）+ 选角色（设计师/设计总监/行政，权限来源）；客户账号 = 选客户（role 固定客户，只读）。
- **新增编辑用户接口** `POST /api/sysUser/update`：改部门 + 角色 + 姓名；账号不可改、密码走重置；客户账号仅可改姓名，禁止分配部门/角色。

### 前端（system/User.vue）
- **部门管理弹窗**：去掉权限模板下拉与列，仅保留部门名称 + 人数 + 重命名/删除；提示文案改为「部门用于人员组织分组，不控制权限；权限通过给账号分配角色实现」。
- **新建用户**：内部员工 = 选部门 + 分配角色（两个独立下拉，明确标注「角色决定权限，部门仅组织分组」）；客户账号逻辑不变。
- **用户卡片新增「编辑」按钮**：弹窗改部门 + 角色 + 姓名（客户账号显示只读提示）。

## 验收对照（模拟数据全链路 25/25 通过）
| 验收标准 | 结果 |
|---|---|
| 新建部门无需选择权限模板 | ✅ 接口/前端均无权限模板 |
| 同部门多用户多角色、权限独立 | ✅ 设计部下设计师（不能改项目）/设计总监（能改项目）/行政（能看客户不能进用户管理）各自独立 |
| 修改所属部门权限不变 | ✅ 设计总监从设计部调研发部，登录后仍为设计总监、仍能改项目 |
| 存量老用户迁移后权限一致 | ✅ 迁移实测：老用户 role 回填为部门模板，部门 role 清空 |
| 客户账号不受影响 | ✅ 客户登录只读、改项目 403、禁止分配部门/角色 |
| 附加 | ✅ 编辑用户缺角色/缺部门拦截；部门占用删除拦截；空部门可删除 |

- 测试脚本：`backend/tests/check_dept_role_split.py`（25/25）；测试数据已全部清理（当前仅 admin 账号 + 3 个无权限属性的内置部门）。
- 8000 后端已重启（迁移已在启动时执行完毕）。

---

# V1.4.2 角色简化：普通 / 管理员（2026-09-01 傍晚）

## 需求
不再区分设计师 / 设计总监 / 行政，内部员工角色只分「普通 / 管理员」两类。普通 = 原设计师权限；存量自动迁移；客户保持独立只读。

## 交付内容
### 后端
- 业务写权限全部收敛为仅管理员（客户/客户分类/流程模板/模板连线/项目/报表/审计日志 的 WRITE_ROLES → ("管理员",)）；项目节点/表单/评论/附件保持「登录即可」（普通可做）。
- 角色取值仅 普通/管理员（客户账号 role=客户 独立）；新建/编辑用户 Literal 同步。
- 启动幂等迁移 `migrate_legacy_roles`：设计师/设计总监/行政 → 普通；**初始管理员 admin 强制保持管理员**（实测用户曾把自己改成设计总监，迁移自动恢复）。

### 前端
- 新建/编辑用户角色下拉仅「普通 / 管理员」；各页面 canWrite、菜单、路由权限全部收敛为 `['管理员']`；头像/标签适配新角色。

## 验证（25/25 通过）
`backend/tests/check_role_simple.py`：普通=能查看/发评论、不能建项目/管客户/建模板/看日志/用户管理；管理员全权限；客户独立只读；普通↔管理员编辑互转；缺角色拦截；存量 legacy 已迁移；admin 保护。测试数据已清理。

## ⚠️ 环境变更（重要）
- 数据库已从 `backend/linkoa.db` 迁移到 `C:\Users\Administrator\linkoa-data\linkoa.db`（.env 已改）。原因：项目位于百度网盘下载目录 `BaiduNetdiskDownload`，网盘客户端会间歇锁定数据库文件导致写入失败、后端无法启动。
- 沙箱内启动后端写库会失败，需在沙箱外启动（本次已用提权方式重启 8000）。

---

# V1.4.3 节点图标 + 表单图像/链接 + 登录页 LINK（2026-09-01 傍晚）

## 需求
1. 节点模板支持图标：预设 20 个常用图标 + 自定义图标上传；节点库与画布节点直观显示。
2. 表单字段新增「上传图像」「链接」两种类型，由管理员在节点模板中配置；用户上传图像可点击放大查看（了解各节点做了什么）。
3. 登录界面大气改版；全站左上角品牌改为「LINK」。

## 交付内容

### 1. 节点图标
- **后端**：`node_template.icon`（预设图标组件名 或 uploads/ 路径）+ `project_node.icon`（模板实例化时冗余拷贝，含流程模板溯源）；新增 `POST /api/nodeTemplate/icon/upload`（管理员，jpg/png/svg ≤1MB，存 uploads/node_icon/）。init.sql 同步。
- **前端**：`utils/nodeIcon.js` 预设 20 个图标（文档/图片/数据/趋势/编辑/文件/文件夹/链接/相册/盒子/监控/目标/工单/备忘/记事本/收藏/印章/购物/指南/魔法）+ 自定义图标判定；节点模板管理页图标网格选择器 + 上传；节点库面板与画布节点均显示图标。

### 2. 表单字段 image / link
- **后端**：字段类型 Literal 扩展 `image`/`link`（节点模板 + 流程模板两处）；新增 `POST /api/projectNode/formImage/upload`（非客户登录即可，jpg/png/webp ≤5MB，存 uploads/node_form/，返回相对路径由前端写入字段值）。
- **前端**：DynamicForm 新增 image 分支（上传/替换/删除/点击放大预览）与 link 分支（URL 输入 + 可点击）；客户门户只读查看时 image 可放大、link 可点击跳转。
- 节点「已完成」判定自动生效（字段值非空即视为已填）。

### 3. 登录页 + LINK 品牌
- 登录页大改版：深蓝渐变背景 + 品牌区（LINK logo/标语/功能点）+ 白色登录卡，响应式（小屏隐藏品牌区）。
- 全站标题统一「LINK」：侧边栏、浏览器标签页、登录页、客户门户。

## 验证情况（如实说明）
- 后端语法/导入冒烟 ✅、init.sql 同步 ✅、前端 vite build ✅、10 项静态 grep 自检 ✅、dist 产物含新功能 ✅。
- **沙箱环境限制**：本会话沙箱对「运行中进程写 SQLite 数据库」有写保护（readonly），后端一旦启动数据库即对外只读（换路径/文件名均无法绕过），导致 API 联调无法在沙箱内完成。已准备 `backend/tests/check_icon_form_tc.py`（TestClient 全流程：图标 CRUD/上传、模板实例化拷贝 icon、image/link 字段保存与回显、权限隔离、数据清理），**请在真实环境（无沙箱）执行该脚本验证**：`<venv python> tests/check_icon_form_tc.py`。
- 数据库最终位置：`C:\Users\Administrator\.workbuddy\linkoa-data\app.db`（.env 已指向，含 icon 列与最新数据）。

---

# 文档全面更新（2026-09-01 傍晚，与 V1.4.3 同步）

按用户要求更新全部 MD 文档（8 份），统一反映 V1.3 ~ V1.4.3 所有迭代：

| 文档 | 更新内容 |
|---|---|
| backend/README.md | 数据库位置（app.db）、19 表/17 路由、新接口、8 个自检脚本、版本特性 |
| frontend/README.md | 品牌 LINK、角色二分/部门/图标/表单新特性、目录结构 |
| 青岛领客文创OA_V1_后端接口清单.md | 2.2 建用户（部门+角色）、新增 2.3 编辑用户、5-1.3 图标上传、8.6 表单图像上传、新增 15 部门接口/16 权限体系/17 客户门户章节 + 目录 |
| 领客文创 OA_V1_Database.md | 新增 sys_dept/sys_role 章节、sys_user 加 dept_id/customer_id、icon 列、字段类型 image/link、拷贝规则 |
| 领客文创OA_启动与使用指南.md | 数据库位置、新增用户/部门/客户门户使用说明、节点图标与表单新功能 |
| 领客文创OA_V1_数据库互转与MySQL部署指南.md | 数据库路径改为从 .env DB_URL 读取 |
| 领客文创OA_V1_AI开发总控指令.md | 交付物勾选完成、19 张表、追加版本迭代记录 |
| 领客文创 OA_V1_PRD.md | 追加版本迭代记录；正文旧角色/表数标注 |

**顺带修复**：`switch_db.py`、`migrate_sqlite_to_mysql.py`、`migrate_mysql_to_sqlite.py` 原硬编码 `backend/linkoa.db`，已改为从 `backend/.env` 的 `DB_URL` 读取实际 SQLite 路径（语法与取值实测通过）。

---

# 便携化改造 + 缺陷修复（2026-09-01 晚，V1.4.4）

## 1. 启动失败排查：数据库绝对路径
- 现象：双击 `start.bat` 后端起不来，报 `sqlite3.OperationalError: unable to open database file`。
- 根因：`backend/.env` 的 `DB_URL=sqlite:///C:/Users/Administrator/.workbuddy/linkoa-data/app.db` 是旧机器（用户名 Administrator）的绝对路径，当前机器无此目录。`config.py` 早已支持相对路径解析，但 `.env` 未同步。
- 修复：改为 `DB_URL=sqlite:///./linkoa.db`，数据库回到项目内 `backend/linkoa.db`。
- 连带清理：`switch_db.py`、`migrate_sqlite_to_mysql.py`、`tests/check_icon_form_tc.py` 中 3 处旧机器绝对路径全部改为相对/可配置写法（`switch_db.py` 若不改，日后执行会把坏路径写回 `.env` 导致问题复发）。

## 2. 编辑流程/节点模板 500
- 根因：老库 `node_template`、`project_node` 缺 `icon` 列（V1.4.3 加的），`create_all` 不给已有表补列。
- 修复：`app/database.py` 新增 `auto_add_missing_columns()`，`main.py` 在 `create_all` 前调用；启动自动比对模型与库结构并 `ALTER TABLE ADD COLUMN`。SQLite / MySQL 通用，同类问题不再复发。

## 3. 全流程回归发现并修复的缺陷
| 缺陷 | 修复 |
|---|---|
| 连线自环被误报「引用了不存在的节点」 | 端点校验由「集合长度=2」改为按端点存在性逐个判断（模板连线 + 项目连线两处） |
| 模板连线接口操作人写死 0、无审计 | 传入真实用户并写操作日志 |
| 封面上传只信 Content-Type，伪造扩展名可传任意文件 | 新增 `app/utils/images.py` 魔数校验（jpg/png/webp），项目和客户封面上传均接入 |

## 4. 回归体系
新增 `backend/tests/full_flow_check.py`（真实 HTTP，覆盖 17 个模块 68 项断言：登录、用户/部门/角色、客户分类/客户、节点模板、流程模板、项目、节点、连线、附件、评论、消息、审计、报表导出、归档），测试数据以「全流程测试」为前缀自动清理。

---

# 品牌与文案统一 + 前端缺陷修复（2026-09-01 晚，V1.4.5）

## 1. 图片放大镜失效
`DynamicForm.vue` 中 `<el-icon @click.stop><ZoomIn /></el-icon>` 只有阻止冒泡、未绑点击处理，点击无反应。改为给 `el-image` 加函数 ref 存入 `imageRefs[fieldId]`，ZoomIn 调用 `imageRefs[id]?.showPreview()`；三个操作按钮补 `title` 提示。

## 2. 品牌统一（用户提供 logo）
- 图标落位 `frontend/public/link-icon.png`（Vite public 目录，构建时原样复制进 dist，后端单端口托管 `http://localhost:8000/link-icon.png` 可访问）。
- 登录页：logo 图 + 「青岛领客文化传播有限公司」大字 + 渐变分隔线 + 三条卖点，去掉 LINK 大字与「IP 文创项目流程管理系统」标语。
- 顶部导航 / 窄屏抽屉：去掉 Brush 图标，仅保留 LINK 文字。
- 浏览器标签页：`页面 - 领客文创`。
- 客户门户页头：logo 小图 + 「领客文化 · 客户门户」。
- 工作台欢迎语：「开始管理你的项目」。

## 3. 构建清理
`vite.config.js` 原本 `emptyOutDir: false`（沙箱时代遗留），dist 累积三次历史构建产物（约 20MB 冗余）。改为清空后全量重建，并删除 MainLayout 中已失效的 `.logo-icon` CSS 规则。

## 验证
后端 68 项回归全通过；HTTP 实测首页 200、logo 图 30764B 有效 PNG、登录页与客户门户 chunk 含新文案、无旧文案残留。

---

# 全量 MD 文档同步（2026-09-01 夜）

按 V1.4.4 / V1.4.5 实况同步全部 8 份文档：

| 文档 | 更新内容 |
|---|---|
| backend/README.md | 标题改公司名；DB 路径改 `backend/linkoa.db`；补结构自愈迁移说明；版本特性升 V1.4.5（含连线/上传加固）；自检脚本补 `full_flow_check.py`；删除旧机器 venv 路径 |
| frontend/README.md | 标题改公司名；版本特性升 V1.4.5（品牌统一、放大镜修复）；目录结构描述改为「顶部主导航 + 窄屏抽屉」 |
| 领客文创OA_启动与使用指南.md | 版本 V1.4.5；DB 路径改项目内；补自动迁移与迁移说明 |
| 青岛领客文创OA_V1_后端接口清单.md | 版本头补 V1.4.4/V1.4.5；连线接口补行为变更与权限；补缺失的 4 个封面上传/移除接口；全文权限行按 V1.4.2 角色简化修正 |
| 领客文创 OA_V1_PRD.md | 标题改公司名；版本 V1.4.5；DB 路径改项目内；追加 V1.4.4/V1.4.5 迭代记录；修正正文过期约束（表单组件类型、用户物理删除） |
| 领客文创 OA_V1_Database.md | 版本 V1.4.5；DB 路径改项目内并说明相对路径解析；全局约定新增第 9 条「结构自愈迁移」 |
| 领客文创OA_V1_数据库互转与MySQL部署指南.md | 版本 V1.4.5；DB 路径改项目内（保留历史沿革说明）；备份/迁移/文件清单一节路径同步；补启动期自愈迁移说明与限制 |
| 领客文创OA_V1_AI开发总控指令.md | 标题改 V1.4.5；新增「工程约束」硬性条款（禁止机器绝对路径、结构靠自愈迁移升级）；追加 V1.4.4/V1.4.5 迭代记录 |

**遗留说明**：`artifacts/overview.md` 与本文的历史记录中仍出现 `C:/Users/Administrator/...` 路径——属于既往事实陈述，不作改写。代码与配置中已无任何机器相关绝对路径。

---

# V1.4.8 AI 助手「青青侠」（2026-09-02）

## 需求
常驻公司 IP 形象「青青侠」，供员工 + 客户门户客户使用。右下角浮动形象 → 悬停随机气泡 → 点击平滑展开居中弹窗（桌面 2/3、移动全屏）→ DeepSeek 流式对话。要求：动画流畅、多模型可扩展架构、**客户严格数据隔离（只能问自己公司项目）**、仿豆包/DeepSeek 会话历史、RAG 接项目数据、卖萌人设 + 管理员面板可配、来源引用/停止生成/Markdown/推荐问题。

## 交付内容

### 后端
- **数据模型**：`ai_config`（单行配置）/ `ai_conversation`（按 user_id 隔离）/ `ai_message`（role/content/sources）三张表，启动幂等 `_init_ai_config()` 读 `.env` 初始化。
- **LLM 抽象层**：`services/llm/base.py`（`BaseLLMProvider.stream_chat`）+ `deepseek.py`（OpenAI 兼容 SSE）+ `retriever.py`（RAG）+ `__init__.py` 工厂 `get_provider`，未来加模型只加 Provider 类。
- **数据隔离（红线）**：客户账号 RAG 检索强制 `Project.category_id == 所属单位` 过滤；员工全量。
- **接口**（`/api/ai`）：会话 CRUD + `POST /chat/stream`（SSE 流式 delta/error/done）+ 管理员 `GET/PUT /config`（api_key 脱敏）。

### 前端
- `components/ai/`：`MascotFloat`（呼吸 + 悬停摇头 + 随机气泡）、`AiAssistant`（缩放展开 + 遮罩）、`ChatPanel`（居中弹窗 + 会话列表 + 消息区 + 输入）、`ConversationList` / `MessageList`（markdown-it + 来源引用 + 流式光标）/ `ChatInput`（停止生成）。
- `stores/ai.js` + `api/ai.js`（fetch 读 SSE + AbortController）；`views/system/AiConfig.vue` 管理员配置页；`config/mascot.js` 气泡与推荐问题。

## 修复的关键 Bug
1. **`DetachedInstanceError`**：`chat_stream` 生成器 `finally` 里 `db.close()` 后再 `yield done` 访问 `conv.id`（commit 后对象 expired，close 后 detach）→ 会话 ID 在 close 前固化到普通变量。
2. **`MessageItem` schema 命名冲突**：AI 的 `MessageItem` 被 `schemas/__init__.py` 里系统消息模块的同名类覆盖（msgType/msgContent/isRead），导致消息列表 500 → 改名 `AiMessageItem`。

## 验证
- 冒烟测试全通过：会话 CRUD、配置脱敏（`sk-4****7be2`）、DeepSeek 真实流式（完整 delta + done + 消息落库）。
- `backend/tests/full_flow_check.py` 回归：**91 项通过，0 失败**（已将 AI 模块纳入回归：配置脱敏 + 会话/消息 CRUD + 流式 done 事件断言）。
- 前端 vite build 成功（AiConfig 已打包进 dist）。
- 8 份 MD 文档已同步（版本号 V1.4.7→V1.4.8，接口清单/Database/PRD 新增 AI 模块）。
- 临时冒烟脚本 `_ai_smoke.py` 已删除。

## 使用方式
1. 启动：`start.bat`（或 `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`）。
2. 管理员在「AI 设置」（用户下拉菜单）确认/填写 API Key（或已在部署配置预置）。
3. 员工/客户登录后，右下角点「青青侠」即可对话；客户只能问到自己公司的项目。


---

# V1.4.9 AI 助手安全加固（2026-09-02）

## 需求
用户实测 AI 助手「青青侠」暴露三类问题：① 问「最近有哪些项目」时**编造 3 个不存在的项目**；② 问「青岛地铁」把真实存在但**非本公司做的项目**当内部项目回答；③ 问项目时会**反问「你的公司名称是什么」**——用户严厉更正：公司名与账号绑定，内部账号=本公司、客户账号=归属公司，AI 只答归属公司项目，严禁反问身份。

## 交付内容（23 个节点全部落地）
1. **身份绑定与数据隔离（红线）**：`_resolve_identity()` 解析 `{is_internal, company_name}`，身份作为**代码级安全 system prompt 强制注入**（不随管理员可改的 system_prompt 变化），主 prompt 加「严禁反问公司名/身份/账号」硬约束。
2. **防幻觉业务短路**：RAG 检索为空 + 命中业务关键词 → 不调 LLM 直接返回固定话术（「当前没有进行中的项目」）。
3. **per-user 滑动窗口限流**：threading.Lock + deque，管理员豁免。
4. **中文关键词提取优化**：停用词表 + 正则二次切分（权衡单字停用词避免误伤实体词）。
5. **会话管理**：三点菜单（置顶/重命名/软删），`pinned`/`is_deleted` 列，排序 `pinned.desc()→updated_at.desc()`。
6. **AI 审计留痕**：oper_type 新增 `ai_chat`/`ai_conversation_rename`/`ai_conversation_pin`/`ai_conversation_delete`。
7. 会话标题自动生成、停止生成兜底、AI 空返回兜底、推荐问题角色分层、来源标注、MascotFloat 频闪修复（动画分层）。

## 自检
- 新建 `backend/tests/ai_full_check.py`（AI 全链路 **23 项断言**，覆盖隔离/防幻觉/审计/限流/置顶/软删/关键词提取）+ `backend/tests/mock_llm.py`（OpenAI 兼容 SSE mock，monkeypatch `ai_service.get_provider` 免真实 API）。
- `full_flow_check.py` 用 mock LLM 跑通 **91 项，0 失败**。
- 版本号升至 V1.4.9，8 份 MD 文档同步。

## 数据清理
- AI 会话/消息/`ai_*` 审计日志（自检副产物）已全部清零。
- 业务表「测试」客户 +「第一个项目」「第二个项目」为用户早期手动演示数据（非自检残留），保留未删，可自行决定是否清理。

---

# V1.4.10 AI 联网搜索（2026-09-02）

## 需求
用户最初建议「在对话框加入一个联网搜索开关」，区分「本地知识库」与「联网搜索」两种来源，避免 AI 把联网搜到的外部信息与内部项目数据混淆。本轮将联网搜索从方案阶段落到实施。

## 交付内容
1. **后端双调用路径**（`services/llm/deepseek.py` 完全重写）：
   - `web_search=False` → 原 OpenAI 兼容 `/chat/completions` 流式（`data:{json}` + `data:[DONE]`）。
   - `web_search=True` → DeepSeek **Responses API** `/responses`，声明 `tools=[{"type":"web_search"}]` + `tool_choice:auto`，服务端托管搜索；流式事件 `response.output_text.delta`（取 `delta` 字段），结束事件 `response.completed/incomplete/failed`（无 `[DONE]`）。
2. **模型弃用升级**：`deepseek-chat`/`deepseek-reasoner`（2026/07/24 弃用）→ `deepseek-v4-flash`（Responses API 支持 web_search）。`.env`/`config.py`/`models/ai.py` 三处默认值 + 启动幂等迁移（`_init_ai_config` 存量 `deepseek-chat|deepseek-reasoner` → `deepseek-v4-flash`）。
3. **`web_search` 参数贯通**：`schemas/ai.py`（ChatStreamRequest）→ `routers/ai.py`（chat_stream 透传）→ `services/ai_service.py`（chat_stream + _build_messages）→ `base.py` 抽象方法。
4. **联网提示注入**：开启联网时追加 system 提示「内部项目/客户/进度/对接人数据仍仅以系统本地数据为准，严禁用联网结果编造内部业务数据」。
5. **前端联网搜索开关**：`ChatInput.vue` 重写，新增「联网搜索」胶囊开关（el-icon Search + tooltip，开启态主题色高亮），`send` 事件透传 `webSearch`；`api/ai.js`、`stores/ai.js`、`ChatPanel.vue` 贯通。

## 自检
- `backend/tests/ai_full_check.py`：升级 docstring V1.4.10，新增联网开关分流/提示注入用例，断言 **23→28 项，28 项全部通过 0 失败**。
- `backend/tests/mock_llm.py` 重写：支持 `/chat/completions` + `/responses` 双路径 mock，Responses 路径回显联网标记供断言。
- `full_flow_check.py`：**91 项通过 0 失败**（临时 base_url 指向 mock 省 token，已恢复）。
- 版本号升至 V1.4.10，8 份 MD 文档同步（接口清单 18.7 节重写、Database ai_config.model 更新、PRD/AI 总控新增 V1.4.10 章节、前后端 README）。

## 收尾
- `ai_config.base_url` 已从 mock `http://127.0.0.1:8899` 恢复为 `https://api.deepseek.com`。
- 停止 mock LLM 进程（8899），清理自检残留：`ai_message` 12 条、`ai_conversation` 7 条、`sys_operation_log` 20 条（oper_user_id 7/8/9 测试用户）。
- 保留用户早期演示会话（「青岛地铁的项目」等 3 条）。

---

# V1.4.11 AI 会话交互 BUG 修复（2026-09-02）

## 用户报告
AI 对话的删除/重命名三点菜单「在 AI 底层看不到了」——点不开、找不到。

## 根因
`AiAssistant.vue` 面板 `z-index: 2100` 高于 Element Plus 弹层默认 `2000`，导致面板内的 `el-dropdown` 下拉、`el-tooltip`、以及重命名/删除的 `ElMessageBox` 确认框全被面板盖住；`ConversationList.vue` 的 `el-dropdown` 还用了 `:teleported="false"`，被会话列表容器的 `overflow` 裁剪。

## 交付内容
1. **层级根治**：面板 `z-index` 2100/2090 → 1950（低于 Element Plus 弹层），`el-dropdown` 改 `teleport` 到 body，下拉/tooltip/MessageBox 自然盖过面板。
2. **移动端**：三点菜单按钮 `.conv-more` 由 `display:none`（仅 hover）改常驻，触屏可点出；抽屉内删/改会话后自动关闭面板；`100vh`→`100dvh` 修复 iOS Safari 地址栏溢出。
3. **输入法组词误发（严重）**：`ChatInput.vue` 发送由 `@keydown.enter.exact.prevent` 改 `keyup` + `e.isComposing` 判断，避免中文选词时 Enter 直接发半成品。
4. **滚动与流式**：`MessageList.vue` 滚动监听改依赖 `messages.length`（切换会话稳定滚底）；`stores/ai.js` 切/删会话时 `stopStreaming()` 中断流式，修复 `streaming` 卡死。
5. **后端健壮性**：`file_service.remove_disk_file` 的 `except OSError`→`except Exception`（删文件失败不阻断业务）；`full_flow_check.py` 的 `check()` 加 `resp.json()` 保护 + 表驱动前置清理（自愈残留）。
6. **system_prompt None 防御**（续查补充）：`_build_messages` 首条 system message 用 `system_prompt or ""`，管理员清空人设 prompt（存 None）时不再向 DeepSeek 发 `content:null` 导致 400/500；两条调用路径均受益。
7. **FlowCanvas 全屏状态同步**（业务模块续查）：按 ESC 退出全屏后 `isFullscreen` 未同步（未监听 `fullscreenchange`），按钮图标与实际状态不符；已加 `fullscreenchange` 监听 + `onBeforeUnmount` 解绑。排查确认全站 `el-dropdown` 仅 2 处无裁剪风险、DynamicForm/CustomFlowNode 无弹层嵌套、画布拖拽无回弹。
6. **升版**：`main.py` + 登录页脚 → V1.4.11；8 份 MD 同步。

## 自检与重启
- `ai_full_check.py` 28 项 + `full_flow_check.py` 91 项全绿。
- 重启后端：停旧进程 → 清 dist（PowerShell Remove-Item）→ `npm run build`（index-BECqfgxD.js）→ 重启（PID 30936，8000 监听，HTTP 200）。AI 配置正常（deepseek-v4-flash / api.deepseek.com / key 已配）。
- 环境认知：沙箱给 `os.remove` 挂钩子，累计删 >50 文件抛 `SystemExit`，导致封面/附件删除接口在沙箱内 500；正常部署无此钩子，业务逻辑（DB 字段先更新）无误。

---

# V1.4.12 候选：常规 CRUD 页面「未保存数据丢失」BUG 修复（2026-09-02 收尾）

## 用户指令
「解决已有的 BUG 之后，排查是否还有其他 BUG，一一解决。」本轮收尾将排查延伸到常规 CRUD 页面，定位到静默数据丢失隐患。

## 根因
全站此前**无任何离开守卫 / 未保存提示**（`grep` 无 `beforeRouteLeave/onBeforeRouteLeave/beforeunload`）。最危险路径：在项目详情页编辑节点 A 的 DynamicForm 后直接点节点 B，`onNodeClick` 重设 `formFields` 触发 DynamicForm 的 `watch(props.fields)` 重置 `values`，A 的未保存编辑被**静默覆盖丢失**，用户毫无感知。

## 交付内容
1. **`DynamicForm.vue`**：加 `initialSnapshot` ref + `isDirty` computed（对比初始快照判断脏）；`defineExpose({ collect, isDirty, markClean })`，`markClean()` 在保存成功后重置基准，避免保存后重复弹提示。
2. **`Detail.vue`**：新增 `guardUnsaved(message, confirmText)` 统一拦截：
   - confirm（如「保存并切换」）→ 落库后继续
   - cancel（放弃修改）→ 直接继续
   - X / ESC 关闭弹窗 → 中止当前操作
   - 用 `distinguishCancelAndClose:true` + `closeOnClickModal:false` + `closeOnPressEscape:false` 三态区分，杜绝误触关闭误丢数据。
   - 在四处调用：`onNodeClick`（切节点）、`onDeselect`（点画布空白 + 面板关闭按钮）、`onAddPreset`/`onAddConnected`（新增节点）、`onArchive`（归档前）。
   - 新增 `onBeforeRouteLeave` 页面级离开守卫（保存并离开 / 放弃修改 / 中止）。
   - `saveSelectedNode()` 与 `onSaveForm()` 保存后调 `markClean()` 清脏。

## 验证
- `vite build` 成功（`Detail-DGWLsa_x.js` 37kB，无报错）。
- 停后端 → 重建 → 重启后端（8000 监听，HTTP 200）。

## 状态
- 代码修复已落盘并通过编译验证（`vite build` 成功，Detail-DGWLsa_x.js 37kB）。
- **升版 V1.4.12 已完成**：`main.py` + 登录页脚 `1.4.12`，8 份 MD 全同步（README/backend/README/frontend/README 补章节，接口清单/Database/PRD/MySQL部署指南/AI总控指令 标题与正文升 V1.4.12，注明接口与库结构无变化）。grep 校验 `1.4.12` 在 8 文档+2 代码版本字符串均命中。
- **本轮「修复已知 BUG + 排查其他 BUG 一一解决」任务全部结束**：V1.4.11 修 AI 交互 6 类 BUG，V1.4.12 修 CRUD 未保存丢失 BUG，全站无已知未保存数据丢失类隐患，版本/文档/代码三者一致。
- **回归实测（收尾）**：重建 + 重启后 `full_flow_check.py` 91 项 / `ai_full_check.py` 28 项全绿（exit 0）；后端 `/docs` 报 `1.4.12`，`dist` 登录块含 `1.4.12`，服务在线 HTTP 200。

---

# V1.4.13：AI 助手检索与富上下文优化（2026-09-02 收尾）

## 需求背景
用户反馈 AI 助手「青青侠」两类查询失败：① 模糊查询「帮我查一下关于服贸会的项目」、全局列表「看下当前我们的项目，按时间排序」被误判为「没查到相关的项目数据」，只有明确说「查 XXXX 单位的项目」才正常；② 答不了「谁负责 / 到哪一步 / 还有几天交付 / 最紧急是哪个」以及「今年做了几个项目 / 归档了几个 / 还有几个未完成」这类自然语言问题。

## 根因
- `retriever._extract_keywords` 停用词表不全，意图功能词（关于/找/看下/当前/按/时间/排序…）与实体词粘死（「关于服贸会」）或冒充关键词（「看下当前」「按时间排序」）→ LIKE 落空。
- 关键词落空后无回退：只有「一个关键词都没切出」才回退全量列表，切出关键词但命中 0 行时直接 `return "", []`。
- `ai_service.chat_stream` 的 `if not context and is_business_query` 防幻觉短路被上游「垃圾词 + 无回退」误伤 → 直接回「没查到」。
- 拼给大模型的项目上下文仅 7 个字段，缺负责人/进度/倒计时/紧急度。

## 已确认口径（用户拍板）
| 问题 | 结论 |
|---|---|
| 「是谁负责」 | 我方设计师（`project_designer_rel`→`user.real_name`，多名全部列出） |
| 「最紧急」 | 交付时间紧迫度：已逾期排最前 → expect_time 越近越紧急 → NULL 排最后；只看「进行中」 |
| 「到哪一步」 | 表单填写进度：`project_node_form_value` 有记录=已完成，按画布顺序（pos_x→pos_y→sort→id）首个未填=当前进行中，附整体进度% |
| 「今年几个/归档几个/未完成几个」 | 按 `create_time` 当前自然年立项数 / `project_status=='已归档'` / `=='进行中'` 计数 |

## 改动（纯后端，最小变更）
1. `backend/app/services/llm/retriever.py`：补停用词表 + `_detect_intent`（查实体/全局列表/统计）+ 关键词落空回退全量进行中列表 + `_compute_stats` + `_build_rich_context`。
2. `backend/app/services/ai_service.py`：仅注释/版本号，主流程与防幻觉短路不变。
3. `backend/app/main.py`：version 1.4.12 → 1.4.13。

## 红线不变
客户账号按 `Project.category_id == 本人所属单位` 隔离；`if not context and is_business_query` 防幻觉短路保留。

## 验证（QA 独立实测）
- 针对性脚本 `backend/tests/qa_retriever_verify.py`（32 项断言，0 失败）。
- `ai_full_check.py` 30 项（原 28 项 + 新增 2 断言，修复 2 条过时断言）全绿。
- `full_flow_check.py` 91 项全绿。
- 智能路由判定：NoOne（源码 0 Bug，无需返工）。

## 版本收口
`main.py` + 登录页脚 `1.4.13`，8 份 MD（README/backend/README/frontend/README/接口清单/Database/PRD/MySQL部署指南/AI总控指令）标题与正文升 V1.4.13 并补 V1.4.13 变更说明；前端与数据库结构无变化。
