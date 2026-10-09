# LINKOA · Docker 部署速查

> 版本 V1.4.18 ｜ 单端口 8000 ｜ 数据在项目根 `data/`（数据库+附件）

## 1. docker/ 文件夹里有什么

| 文件 | 作用 |
| --- | --- |
| `README.md` | 本文件：部署速查 |
| `离线部署说明.txt` | 纯离线手把手（传输→校验→加载→启动→FAQ） |
| `linkoa-latest.tar` | 新版离线镜像包（约 70.7MB，镜像 `linkoa:latest`） |
| `Dockerfile` | 镜像构建配方（Node 构建前端 → Python 运行时） |
| `docker-compose.yml` | 默认方案：SQLite，一条命令启动 |
| `docker-compose.mysql.yml` | 可选方案：多人并发时叠加启用 MySQL |
| `docker-entrypoint.sh` | 容器启动入口（自动建附件目录） |

> 配套：项目根 `data/`（数据库+附件）、`.dockerignore`。命令都在 `docker/` 目录内执行。

## 2. 部署方式总览（先看这张表选你的场景）

先判断 Docker 新旧：`docker compose version` 有输出 = 新版；只有 `docker-compose --version` = 旧版。

| 场景 | 操作 |
| --- | --- |
| **新版 Docker + 有外网** | ① 拉现成镜像（免构建）：`docker pull ghcr.io/3348066149/linkoa:v1.4.18` → `docker tag ghcr.io/3348066149/linkoa:v1.4.18 linkoa:latest` → `docker compose up -d`；② 或源码构建：`docker compose up -d --build` |
| **新版 Docker + 无外网** | 下载 Release 附件 `linkoa-latest.tar`（GitHub Releases v1.4.18）→ `docker load -i linkoa-latest.tar` → `docker compose up -d` |
| **旧版 Docker + 无外网** | `docker load -i linkoa-latest.tar` → 用 `docker-compose up -d`（v1 需先删掉 compose 文件里的 `name: linkoa` 行）或直接 `docker run` 兜底 |
| **旧版 Docker + 有外网** | ① 拉镜像：`docker pull ghcr.io/3348066149/linkoa:v1.4.18` → `docker tag ... linkoa:latest` → `docker-compose up -d`；② 或 `docker-compose up -d --build` 构建新版 |

离线包校验（传完必查，防截断）：大小 **74144256** 字节，MD5 **75e32513b6ae2e632331a23bf96bacc2**。

## 3. 新老版本指令对照（常用）

| 操作 | 新版（v2：`docker compose`） | 旧版（v1：`docker-compose`） | 说明 |
| --- | --- | --- | --- |
| 构建并启动 | `docker compose up -d --build` | `docker-compose up -d --build` | 首次部署/升级代码用 |
| 启动 | `docker compose up -d` | `docker-compose up -d` | 镜像已存在时用 |
| 查看状态 | `docker compose ps` | `docker-compose ps` | healthy = 正常 |
| 看日志 | `docker compose logs -f app` | `docker-compose logs -f app` | 排障用 |
| 停止 | `docker compose down` | `docker-compose down` | 数据保留在 data/ |
| 导入离线镜像 | `docker load -i linkoa-latest.tar` | 同左 | 无外网场景 |
| 拉在线镜像 | `docker pull ghcr.io/3348066149/linkoa:v1.4.18` | 同左 | 有外网场景 |
| 无 compose 兜底 | `docker run -d --name linkoa --restart unless-stopped -p 8000:8000 -v <路径>/data:/app/data -e DB_URL="sqlite:////app/data/linkoa.db" -e UPLOAD_DIR="/app/data/uploads" -e JWT_SECRET=你的密钥 linkoa:latest` | 同左 | 任何 Docker 版本都能跑 |

## 4. 数据与配置

- **数据**：全部在项目根 `data/`（`linkoa.db` + `uploads/`），备份/迁移只拷这一个文件夹。
- **配置**：在 `docker/` 目录建 `.env` 覆盖默认值：`LINKOA_PORT`（默认 8000）、`LINKOA_JWT_SECRET`（生产必改，≥32 字节）、`LINKOA_AI_API_KEY`、`LINKOA_AI_BASE_URL`、`LINKOA_AI_MODEL`。改完 `docker compose up -d` 生效。
- **MySQL**（多人并发才需要）：`docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build`；离线环境需另导 `mysql:8.0` 镜像。

## 5. 常见问题

- **`docker load` 报 unexpected EOF**：tar 传残了，核对大小/MD5，重传。
- **`docker compose` 报 unknown shorthand flag**：Docker 太旧没 v2 插件，改 `docker-compose` 或 `docker run`。
- **旧版报 `name: linkoa` 错误**：删掉 compose 文件里顶层 `name: linkoa` 那行再用。
- **端口被占**：compose 改 `.env` 的 `LINKOA_PORT`；`docker run` 改 `-p 8001:8000`。
- **只升级镜像不动数据**：`docker compose down` → load 新包 → `docker compose up -d`，`data/` 没删数据就在。

> 详细手把手（含报错处理）见 `离线部署说明.txt`；原理学习见项目根 `docs/Docker入门与原理.md`。
