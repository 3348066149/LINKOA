# LINKOA OA · Docker 部署指南（docker/ 目录方式）

> 版本：V1.4.18　|　适用：领客文创 OA（单端口 8000，页面 + API + 附件一体）
> 目标：一条命令把整个系统跑起来，不再依赖本机装 Python / Node / MySQL。

---

## 〇、一句话说明：Docker 相关文件都集中在这个 docker/ 目录里

本项目所有 Docker 部署相关文件已统一收进 **`docker/` 文件夹**，部署时**先进入 docker/ 目录**再敲命令即可：

```
LINKOA/                      ← 项目根
├── docker/                  ← Docker 部署全家桶（部署时进入这里）
│   ├── Dockerfile           构建配方（多阶段：Node 构建前端 → Python 运行时）
│   ├── docker-compose.yml   默认方案：SQLite + 数据卷，一条命令启动
│   ├── docker-compose.mysql.yml  可选方案：多人并发时叠加启用 MySQL
│   ├── docker-entrypoint.sh 容器入口：启动前自动创建附件目录
│   └── README.md            本指南
├── data/                    ← 你的数据（数据库 + 附件），备份只拷这一个文件夹
├── backend/  frontend/      ← 源码（构建时被 Dockerfile 打进镜像）
└── .dockerignore            ← 必须在项目根（构建上下文根目录）才生效，勿移动
```

> 为什么 `.dockerignore` 在项目根而不在 docker/ 里？因为 Docker 的构建上下文（build context）必须是项目根（要覆盖 `backend/` 和 `frontend/`），而 `.dockerignore` 必须放在构建上下文根目录才生效。**别把它挪走。**

---

## 一、Docker 封装解决了什么

原来启动需要：本机装 Python 3.10+ → 建虚拟环境装依赖 → 装 Node 构建前端 → 手动启动 uvicorn。
换机器还要删 `.venv` / `node_modules` / `dist` 重新生成，很容易踩坑（登录页 404 等）。

封装成 Docker 后：

- **一条命令启动**：进入 docker/ 后 `docker compose up -d --build`，构建和运行全自动；
- **环境不再绑定本机**：镜像内自带 Python 3.12 + Node 20 构建链，任何装了 Docker 的机器（Windows / Linux / macOS / 服务器）都能跑；
- **数据好备份**：数据库 + 上传附件统一放在项目根 `data/` 文件夹（`data/linkoa.db` + `data/uploads/`），**本地 `start.bat` 与 Docker 共用同一份数据**（V1.4.18 起本地 `.env` 也指向 `data/`），备份/迁移只拷这一个文件夹。

## 二、环境要求

- 安装 **Docker Desktop**（Windows / macOS）或 Docker Engine（Linux），并确认引擎在运行：
  ```bash
  docker info        # 能显示 Server Version 即引擎正常
  docker compose version
  ```
- 不需要再装 Python / Node / MySQL（都在镜像里）。

## 三、快速启动（默认 SQLite，推荐）

**第 1 步**：进入 docker/ 目录

```bash
cd docker        # Windows / Linux / macOS 都一样
```

**第 2 步**：构建 + 启动

```bash
docker compose up -d --build
```

- 首次会拉取基础镜像并构建（约几分钟），之后启动秒级。
- 启动后浏览器访问 **http://localhost:8000**，账号 **admin / admin123**。
- 常用命令（都在 docker/ 目录里执行）：

```bash
docker compose up -d --build   # 启动（改代码后重建）
docker compose up -d           # 日常启动/重启（镜像已存在时，更快）
docker compose ps              # 查看状态（healthy 即正常）
docker compose logs -f app     # 看日志
docker compose down            # 停止（数据保留在项目根 data/）
docker compose down -v         # 停止并删除数据卷（慎用，会清数据）
```

## 四、数据持久化与备份

- 数据都在项目根目录的 **`data/`** 文件夹里（docker/ 的上一级）：
  - `data/linkoa.db` —— 数据库（全部业务数据）
  - `data/uploads/` —— 上传的附件
- **备份**：把整个 `data/` 文件夹拷走即可。
- **迁移到新机器**：新机器装好 Docker → 拷贝整个项目（含 `data/`）→ 进入 docker/ 执行 `docker compose up -d --build`。

## 五、配置项（环境变量）

在本 **`docker/` 目录**创建 `.env`（与 `docker-compose.yml` 同级，compose 会自动读取），按需填写：

```bash
# 宿主机访问端口（默认 8000，如服务器已有程序占用 8000 可改成 8001）
LINKOA_PORT=8000

# JWT 密钥，生产环境务必改成自己的随机串（>=32 字节）
LINKOA_JWT_SECRET=please-change-me-to-a-long-random-string-0123456789

# JWT 过期时间（小时），默认 24
LINKOA_JWT_EXPIRE_HOURS=24

# AI 助手（可选）：不填也能启动，AI 功能需登录后管理员在「AI 设置」面板填写
LINKOA_AI_API_KEY=sk-xxxx
LINKOA_AI_BASE_URL=https://api.deepseek.com
LINKOA_AI_MODEL=deepseek-v4-flash
```

改完 `.env` 后在 docker/ 目录执行 `docker compose up -d` 重启生效。

## 六、启用 MySQL（可选，多人并发才需要）

> 默认 SQLite 对单机 / 演示 / 单人使用完全够用。只有「多个员工同时在线改数据」才建议 MySQL。

在 **docker/ 目录**执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build
```

- 会自动拉起一个 `mysql:8.0` 容器，并自动创建数据库 `linkoa` 与账号。
- MySQL 密码可在 docker/ 目录的 `.env` 配置：
  ```bash
  MYSQL_ROOT_PASSWORD=root123456
  MYSQL_PASSWORD=linkoa123456
  ```
- 切回 SQLite：`docker compose down` 后用 `docker compose up -d --build` 重启即可（两套库数据相互独立）。

## 七、局域网 / 服务器访问（给客户演示）

- 本机：`http://localhost:8000`
- 同局域网客户电脑：`http://你的电脑IP:8000`
- 公网服务器：把 `LINKOA_PORT` 映射好，并配置云安全组放行对应端口。

## 八、常见问题（FAQ）

**Q1：`docker compose up` 报错 "no such file" / 端口被占用？**
先确认在 docker/ 目录执行；`docker compose ps` 看是否已有容器在跑；端口被占用就改 docker/ 下 `.env` 的 `LINKOA_PORT`。

**Q2：访问页面 404 / 白屏？**
前端在镜像构建阶段生成（`frontend/dist`），确认是 `docker compose up -d --build`（带 `--build`）启动的；或 `docker compose logs -f app` 看启动日志。

**Q3：数据想保留、只重建代码？**
`docker compose down` 后再 `docker compose up -d --build`，`data/` 不删数据就在。

**Q4：AI 助手提示"尚未配置 API Key"？**
两种方式任选：① docker/ 目录 `.env` 配 `LINKOA_AI_API_KEY` 后重启；② 管理员登录后进「AI 设置」面板直接填（写入数据库，立即生效）。

**Q5：怎样换一台机器部署？**
机器装 Docker → 拷贝整个项目文件夹（含 `data/`）→ 进入 docker/ 目录 → 执行 `docker compose up -d --build`。

**Q6：Docker 到底是什么 / 原理 / 遇到其他项目怎么写？**
看项目根的 `docs/Docker入门与原理.md`，从概念到实操一次讲透。
