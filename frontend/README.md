# 青岛领客文化传播｜项目流程管理 OA 前端

Vue 3 + Element Plus + @vue-flow + Pinia + Vite，开发端口 5173。

## 启动步骤

```bash
# 1. 安装依赖
npm install

# 2. 开发模式（需后端已启动在 8000 端口，/api 与 /uploads 自动代理）
npm run dev

# 3. 生产构建（产物 dist/ 由后端 FastAPI 单端口托管）
npm run build
```

- 开发地址：http://localhost:5173
- 初始账号：admin / admin123

## 版本特性（V1.4.17）

- **品牌与文案（V1.4.5）**：登录页为 logo 图（`public/link-icon.png`）+「青岛领客文化传播有限公司」，居中排版；顶部导航与窄屏抽屉仅保留 LINK 文字（去掉 Brush 图标）；浏览器标签页标题为 `页面 - 领客文创`；客户门户页头为 logo 小图 +「领客文化 · 客户门户」；工作台欢迎语「开始管理你的项目」。
- **图片放大镜修复（V1.4.5）**：`DynamicForm.vue` 图片悬停遮罩的 ZoomIn 图标原先未绑点击处理，点击无反应；现通过函数 ref 调 `el-image` 的 `showPreview()` 打开全屏预览。
- **登录页体验优化（V1.4.6）**：`views/login/Index.vue` 重写——左右分栏品牌区 + 登录卡；错误改为表单内联提示（不再全局 alert）；密码显隐、记住账号仅存用户名；输入框聚焦/错误态高亮；页脚版权「© 2026 青岛领客文化传播有限公司」+ 版本号 + 浏览器建议；移动端上下布局。`utils/request.js` 新增 `{ silent: true }` 跳过全局错误弹窗，登录失败改为内联展示。
- **登录安全（V1.4.6）**：同一账号连续失败 5 次锁定 10 分钟；用户管理卡片在锁定态显示「已锁定」标签与「解锁」按钮（调用 `POST /api/sysUser/unlock`）。
- **客户单位/对接人（V1.4.7）**：客户库页面改为「客户单位 + 对接人」两级（分类=单位、客户=对接人）；项目新建/编辑弹窗改为「选客户单位 → 多选对接人」联动；用户管理客户账号按单位分组选择对接人。
- **客户门户重构（V1.4.7）**：卡片与详情去掉节点进度/总进度，改为展示客户单位、我方设计师、客户对接人、立项时间、预计结束时间与倒计时；新增项目名称搜索、进行中/已结项筛选、立项时间范围筛选；门户按客户单位隔离（可见同单位全部项目）；顶栏展示公司名；节点时间线按画布位置排序。
- **登录页改版**：深蓝渐变 + 品牌区 + 白色登录卡，响应式。
- **角色二分**：新建/编辑用户分配角色仅「普通 / 管理员」；客户账号独立（只读门户）。

- **客户评价查看弹窗（V1.4.17）**：客户门户卡片评价后由平铺星星改为「查看评论」按钮 + 弹窗（三项星星 + 备注 + 时间，只读）；文案「我方负责人 → 项目对接人」。
- **品牌化设计改造（V1.4.17）**：全站主题色由 Element 蓝改为墨黑 `#161616` + 强调红 `#e2231a`（取自品牌标识黑白红，`styles/variables.scss` Token 全局生效）；登录页重做（深黑渐变 + 白色标牌 LOGO + 公司名大字 + 品牌口号「品牌与用户如此之近！」红色小字 + 墨黑登录按钮 + 呼吸红晕背景）；卡片 hover 上浮、AI 企鹅红色呼吸光晕、页面过渡增强；字体栈统一 + 数字表格对齐。
- **移动端窄屏适配（V1.4.17）**：12 页面 390px 逐页检查无横向溢出；修复客户门户页头标题竖排。
- **深度 BUG 修复（V1.4.17）**：新增节点表单残留上一节点内容、快捷编辑弹窗竞态、修改密码补确认字段、文件页项目列表分页 400（循环分页）、画布快速连线坐标漂移、死代码与废弃属性清理。
- **部门管理**：部门仅人员组织分组（新建/重命名/删除），不携带权限；用户管理页支持按部门筛选、编辑用户（部门+角色+姓名）。
- **节点图标**：节点模板管理支持图标选择（预设 20 个 + 自定义上传）；节点库面板与画布节点显示图标。
- **表单图像/链接**：节点表单支持 image（上传/替换/点击放大预览）与 link（URL）字段；客户门户只读展示。
- **AI 助手「青青侠」（V1.4.8）**：`components/ai/` 全套组件——右下角常驻形象 `MascotFloat`（呼吸浮动 + 悬停摇头 + 随机气泡）→ `AiAssistant` 总入口（`transform-origin: bottom right` 缩放展开 + 遮罩）→ `ChatPanel` 居中弹窗（桌面 66vw/80vh、移动端全屏）+ 左侧会话列表（`ConversationList` 新建/切换/删除）+ `MessageList`（markdown-it 渲染、来源引用、流式光标、推荐问题）+ `ChatInput`（多行 + 停止生成）；`stores/ai.js` Pinia 状态 + `api/ai.js` fetch 读 SSE + AbortController 停止；管理员 `views/system/AiConfig.vue` 配置面板（用户下拉进入）。
- **AI 助手体验加固（V1.4.9）**：`ConversationList` 会话项删除按钮改为三点菜单（`el-dropdown`：置顶/重命名/删除，删除红色），置顶态带角标、列表置顶优先排序；`MascotFloat` 动画分层（浮动动画移外层容器、hover 用 `transition`、`pointerenter/leave`）修复图标位移频闪；`MessageList` 来源标注（「引用自系统项目」/「本回答未引用系统数据」）；推荐问题按角色分层（`config/mascot.js` 客户视角排除员工操作类问题）。
- **AI 交互 BUG 修复（V1.4.11）**：① **弹层层级根治**——AI 面板遮罩 2090→1900、面板 2100→1950、常驻形象 2000→1500，使面板层级低于 Element Plus 默认弹层（2000），面板内的 dropdown / tooltip / `ElMessageBox` 确认框不再被面板盖住（原「删除/重命名菜单看不到」的 BUG）；② **中文输入法误发送**——`ChatInput` 的 Enter 发送增加 `e.isComposing || e.keyCode === 229` 拦截，避免拼写中文时按 Enter 选词把半成品发出去；③ **移动端三点菜单不可点**——`.conv-more` 默认 `display:none` 仅 hover 显示，触屏无 hover，补 `@media (hover: none)` 常驻显示；④ 移动端抽屉内删除/重命名后自动关闭；⑤ 面板高度 `100vh` → `100dvh`（修复 iOS Safari 地址栏收缩时溢出）；⑥ `MessageList` 滚动 watch 补 `messages.length` 依赖（切换会话时若末条内容相同则不滚动）；⑦ `stores/ai.js` 的 `openConversation`/`removeConversation` 先 `stopStreaming()`（原切换会话时 `streaming` 卡 true、输入框持续禁用）。登录页脚版本号同步升 `1.4.11`。
- **CRUD 未保存数据丢失修复（V1.4.12）**：`DynamicForm.vue` 新增 `isDirty` 脏检测（对比初始快照）；`views/project/Detail.vue` 新增 `guardUnsaved()` 统一拦截，在切换节点、点画布空白/面板关闭按钮、新增节点、归档前、以及 `onBeforeRouteLeave` 离开详情页时弹出「保存 / 放弃修改 / 取消」三态确认，避免编辑中切换导致未保存表单被静默覆盖。保存成功后调 `markClean()` 清脏，不再重复弹窗。
- **客户账号改绑客户单位（V1.4.15）**：`views/system/User.vue` 新建客户账号下拉改为选「客户单位（公司）」（`listCategories()` 取公司列表），列表卡片客户账号展示公司名（`categoryName`）、筛选按公司（`categoryId`）、编辑弹窗展示公司名、提交 payload 客户分支传 `categoryId`；客户门户页头继续展示公司名（`companyName`）；登录页脚版本号同步升 `1.4.15`。
- **AI 助手数据供给改造（V1.4.16）**：移除「联网搜索」胶囊开关（`ChatInput.vue` 删除 `search-toggle` 按钮与 `webSearch` ref、`Search` 图标导入与样式）；`ChatPanel.vue` 的 `onSend(message)`、`stores/ai.js` 的 `sendMessage(message)`、`api/ai.js` 的 `chatStream` 均去掉 `webSearch` 透传；登录页脚版本号同步升 `1.4.16`。

## 目录结构

```
src/
├── api/          # Axios 接口封装（按模块分文件，含 ai.js SSE 流式）
├── components/   # 公共组件（FlowCanvas / CustomFlowNode / DynamicForm / ResponsiveTable / ai/ 青青侠套件）
├── layouts/      # MainLayout（顶部主导航 + 用户下拉 + 窄屏抽屉 + 消息铃铛）
├── router/       # 路由 + 守卫（未登录跳登录、角色控制、客户门户隔离）
├── stores/       # Pinia（user 持久化 / message 未读数 / ai 会话与流式缓冲）
├── utils/        # request.js（Axios 拦截器）、auth.js（token 存取）、nodeIcon.js（预设 20 图标）
└── views/        # 页面（登录 / 项目 / 客户 / 模板 / 系统 / 消息 / 报表 / client 客户门户 / error / system/AiConfig）
```
