# LINKOA 领客文创 OA · Docker 部署指南（docker/ 目录）

> **版本**：V1.4.18　|　**适用**：领客文创 OA（单端口 8000，页面 + API + 附件一体）
> **本文档解决**：在线部署、离线部署、Docker 版本兼容部署、低版本 Docker 部署，四种场景一次说清。
> **一句话**：装了 Docker 就能跑，不用装 Python / Node / MySQL；外网拉不到镜像就用离线包。

---

## 〇、docker/ 文件夹里有什么

```
docker/
├── README.md                ← 本文件：部署总指南（在线 / 离线 / 版本兼容 / 低版本）
├── 离线部署说明.txt          ← 纯离线场景手把手操作手册（服务器上 cat 即可看）
├── linkoa-latest.tar        ← 离线镜像包（约 70.7 MB，镜像 linkoa:latest）
├── Dockerfile               ← 构建配方（多阶段：Node 构建前端 → Python 运行时）
├── docker-compose.yml       ← 默认方案：SQLite + 数据卷，一条命令启动（新版 Docker 用）
├── docker-compose.mysql.yml ← 可选方案：多人并发时叠加启用 MySQL
└── docker-entrypoint.sh     ← 容器入口：启动前自动创建附件目录
```

> 配套：项目根目录 `data/`（数据库 + 附件）、`.dockerignore`（必须在项目根，勿移动）。
> 部署时**先进入 docker/ 目录**再敲命令。

---

## 一、部署方式总览（先看这张表选你的场景）

| 你的情况 | 用哪种方式 | 关键命令 |
| --- | --- | --- |
| 有外网 + 新版 Docker（有 `docker compose`） | **在线部署** | `docker compose up -d --build` |
| 无外网 / 拉不到镜像 + 新版 Docker | **离线部署** | `docker load -i linkoa-latest.tar` → `docker compose up -d` |
| 无外网 + 旧版 Docker（只有 `docker-compose` v1） | **离线 + 旧版** | `docker load` → 用兼容版 compose 或 `docker run` |
| 无外网 + 很老的 Docker（连 compose 都没有） | **低版本兜底** | `docker load` → `docker run` 一条命令 |

> **版本判断方法（先跑一下）**：
> ```bash
> docker --version            # 看 Docker 引擎版本
> docker compose version      # 有输出 = 新版（v2 插件）✅
> docker-compose --version    # 有输出 = 装了旧版（v1 独立程序）
> ```
> - 新版 → 用 `docker compose`（中间有空格）
> - 只有旧版 → 用 `docker-compose`（中间有连字符）
> - 都没有 → 用 `docker run` 兜底（任何版本都能跑）

---

## 二、如何在线部署（有外网，推荐）

前提：能访问外网，Docker 能拉取基础镜像（node:20-slim / python:3.12-slim）。

```bash
cd docker
docker compose up -d --build    # 首次：拉基础镜像 + 构建 + 启动（约几分钟）
```

- 启动后访问 **http://localhost:8000**，账号 **admin / admin123**
- 日常重启（镜像已存在时更快）：`docker compose up -d`
- 查看状态：`docker compose ps`（healthy 即正常）　|　看日志：`docker compose logs -f app`
- 停止：`docker compose down`（数据保留在项目根 `data/`）

---

## 三、如何离线部署（无外网，重点）

> 适用：公司内网 / NAS / 服务器无法访问外网，拉不到镜像。**用 `linkoa-latest.tar` 离线包。**

离线包信息（**传完务必核对，防传输截断**）：

| 项目 | 值 |
| --- | --- |
| 文件 | `docker/linkoa-latest.tar` |
| 大小 | 74,143,232 字节（约 70.7 MB） |
| MD5 | `52e8d6afd96b3d3f5f8e4addc4b4d962` |

### 步骤 1：传包到目标机（用 scp / WinSCP，别用浏览器拖拽）

```bash
# Windows 本机执行（把 link 换成目标机地址/账号）
scp "E:\Docker\LINKOA\docker\linkoa-latest.tar" 账号@目标机:/目标目录/
```

### 步骤 2：校验文件完整（缺这一步容易白折腾）

```bash
ls -l linkoa-latest.tar      # 必须显示 74143232 字节
md5sum linkoa-latest.tar     # 必须等于 52e8d6afd96b3d3f5f8e4addc4b4d962
```

> 大小或 MD5 对不上 = 文件传残了，重新传（否则 `docker load` 会报 `unexpected EOF`）。

### 步骤 3：加载镜像

```bash
sudo docker load -i linkoa-latest.tar
# 看到 "Loaded image: linkoa:latest" 即成功
```

### 步骤 4：启动（新版 / 旧版分别见下）

**📌 完整手把手操作（含各种报错处理）请看同目录的 `离线部署说明.txt`。**

---

## 四、版本兼容部署（新版 / 旧版 compose 怎么选）

### 4.1 新版 Docker（有 `docker compose` 插件）——最顺滑

```bash
cd docker
docker compose up -d        # 镜像已 load，直接用，别加 --build
```

### 4.2 旧版 Docker（只有 `docker-compose` v1 独立程序）

```bash
cd docker
docker-compose up -d
```

> ⚠️ **注意**：`docker-compose.yml` 里有新版才支持的顶层 `name: linkoa` 字段，
> 旧版 v1 会报错。用 v1 前需先删掉该文件的第 21 行 `name: linkoa`，
> 或在 docker/ 目录放一个精简的 v1 兼容 compose 文件。

### 4.3 新版 / 旧版命令对照

| 操作 | 新版（v2） | 旧版（v1） |
| --- | --- | --- |
| 构建 + 启动 | `docker compose up -d --build` | `docker-compose up -d --build` |
| 启动（镜像已存在） | `docker compose up -d` | `docker-compose up -d` |
| 查看状态 | `docker compose ps` | `docker-compose ps` |
| 看日志 | `docker compose logs -f app` | `docker-compose logs -f app` |
| 停止 | `docker compose down` | `docker-compose down` |

---

## 五、低版本 Docker 怎么部署（兜底方案，任何版本都能跑）

> 适用：很老的 Docker，既没有 `docker compose` 也没有 `docker-compose`。
> **不用 compose 文件，直接用 `docker run` 一条命令启动**（已验证可跑通）。

```bash
# 1. 加载镜像
sudo docker load -i linkoa-latest.tar

# 2. 一条命令启动（把 /目标目录 换成你的实际路径）
sudo docker run -d \
  --name linkoa \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /目标目录/data:/app/data \
  -e DB_URL="sqlite:////app/data/linkoa.db" \
  -e UPLOAD_DIR="/app/data/uploads" \
  -e JWT_SECRET="linkoa-docker-secret-0123456789abcdef-change-me" \
  linkoa:latest
```

验证与日常命令：

```bash
sudo docker ps            # 看到 linkoa 容器 Up 且 healthy 即成功
sudo docker logs linkoa   # 出现 uvicorn running 即正常
sudo docker restart linkoa    # 重启
sudo docker stop linkoa       # 停止
sudo docker start linkoa      # 再次启动
sudo docker rm -f linkoa      # 删除容器（数据在 data/ 不受影响）
```

> 端口 8000 被占用时，把 `-p 8000:8000` 改成 `-p 8001:8000`。
> 镜像加载后若想导出备份：`sudo docker save -o linkoa-backup.tar linkoa:latest`

---

## 六、数据持久化与备份

- 数据都在项目根目录的 **`data/`** 文件夹（docker/ 的上一级）：
  - `data/linkoa.db` —— 数据库（全部业务数据）
  - `data/uploads/` —— 上传的附件
- **备份**：把整个 `data/` 文件夹拷走即可。
- **迁移到新机器**：新机器装 Docker → 拷贝 `docker/` + `data/` → 加载离线包 → 启动。

---

## 七、配置项（环境变量）

在本 **`docker/` 目录**创建 `.env`（与 `docker-compose.yml` 同级，compose 自动读取）：

```bash
LINKOA_PORT=8000                    # 宿主机访问端口（默认 8000）
LINKOA_JWT_SECRET=请改成随机串      # JWT 密钥，生产必改（>=32 字节）
LINKOA_JWT_EXPIRE_HOURS=24          # 过期时间（小时）
LINKOA_AI_API_KEY=sk-xxxx           # AI 助手密钥（可选）
LINKOA_AI_BASE_URL=https://api.deepseek.com
LINKOA_AI_MODEL=deepseek-v4-flash
```

改完在 docker/ 目录执行 `docker compose up -d` 重启生效（docker run 方式需用 `-e` 传参）。

---

## 八、启用 MySQL（可选，多人并发才需要）

> 默认 SQLite 对单机 / 演示 / 单人使用完全够用；**多个员工同时在线改数据**才建议 MySQL。

```bash
# 新版（在线环境，需能拉取 mysql:8.0 镜像）
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build

# 离线环境：需另行离线导出 mysql:8.0 镜像（docker save mysql:8.0），
# 在目标机 docker load 后再执行上述命令（去掉 --build）
```

---

## 九、常见问题（FAQ）

**Q1：`docker load` 报 "unexpected EOF"？**
tar 传输不完整或磁盘空间不足。核对：大小是否 74143232 字节、MD5 是否
`52e8d6afd96b3d3f5f8e4addc4b4d962`；不一致就重新 scp 传一次。一致仍报错则
`df -h /目标分区` 检查空间（load 解压至少需 1GB 空闲）。

**Q2：`docker compose up -d` 报 "unknown shorthand flag: 'd' in -d"？**
你的 Docker 太旧，**没有 `docker compose`（v2 插件）**。改用：
① 若有旧版 → `docker-compose up -d`（注意连字符）；② 若没有 → 用第五节的 `docker run` 兜底。

**Q3：compose 启动报 "name: linkoa" 相关错误？**
旧版 v1 compose 不认识顶层 `name:` 字段。删掉 `docker-compose.yml` 第 21 行 `name: linkoa` 再用。

**Q4：启动后页面 404 / 白屏？**
看日志 `docker compose logs -f app` 或 `docker logs linkoa`；多半是端口没映射对
（浏览器访问 `http://IP:映射端口`）。

**Q5：端口 8000 被占用？**
compose 方式：`.env` 里改 `LINKOA_PORT`；docker run 方式：把 `-p 8000:8000` 改端口。

**Q6：数据想保留、只升级镜像？**
`docker compose down`（或 `docker stop linkoa`）→ 重新 load 新镜像 →
`docker compose up -d`（或 `docker run`）。`data/` 没删数据就在。

**Q7：`start.sh` 在 Linux/macOS 打不开 / Docker 构建报 "exec format error"？**
换行符 CRLF 问题。项目已用 `.gitattributes` 强制 `.sh` 为 LF；
重新 `git clone` 或执行 `git checkout -- start.sh docker/docker-entrypoint.sh` 即可
（Dockerfile 也已内置去除 CR 兜底）。

---

## 附：两份文档怎么配合

| 文档 | 定位 | 什么时候看 |
| --- | --- | --- |
| `README.md`（本文件） | 部署总指南：在线 / 离线 / 版本兼容 / 低版本 一表看懂 | 先看这个，选好场景 |
| `离线部署说明.txt` | 纯离线场景的完整手把手（传输→校验→加载→启动→FAQ） | 离线部署、报错排查时逐条跟做 |

> 底层原理学习（镜像/容器/数据卷/构建原理）见项目根 `docs/Docker入门与原理.md`。
