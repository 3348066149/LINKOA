# Docker 入门与原理 — 以 LINKOA 为例

> 目标读者：想"心里有数"的自己。
> 这份文档把「Docker 到底是什么、你的 LINKOA 是怎么被封装的、以后遇到新项目该怎么写」一次讲透，全程大白话。
> 配套文件（已统一收进项目根 `docker/` 目录）：`Dockerfile`、`docker-compose.yml`、`docker-entrypoint.sh`、`docker/README.md`（部署指南）。

---

## 目录

- [0. 一句话总结](#0-一句话总结)
- [1. 四个核心概念](#1-四个核心概念大白话)
- [2. "怎么可能凭空几个文件就部署了"——构建的原理](#2-怎么可能凭空几个文件就部署了构建的原理)
- [3. 你的 LINKOA 是怎么被封装的（真实过程）](#3-你的-linkoa-是怎么被封装的真实过程)
- [4. 三种部署方式对比](#4-三种部署方式对比)
- [5. 版本切换原理](#5-版本切换原理)
- [6. 为什么数据要放在容器外](#6-为什么数据要放在容器外)
- [7. 换电脑 / 搬家的完整流程](#7-换电脑--搬家的完整流程)
- [8. 常见疑问 FAQ](#8-常见疑问-faq)
- [9. 遇到新项目怎么写？（通用方法论）](#9-遇到新项目怎么写通用方法论)

---

## 0. 一句话总结

> **Docker = 把「一套软件 + 它需要的整个运行环境」打包成一份"开机就能跑"的快照，在任何电脑上原样跑起来，不受那台电脑装了什么的影响。**

它解决的核心痛点：**"在我电脑上明明是好的"** 这个问题。Docker 让环境跟着代码一起走。

---

## 1. 四个核心概念（大白话）

| 概念 | 大白话 | 比喻 |
| --- | --- | --- |
| **镜像 Image** | 装好了一切、但"还没开机"的安装包。只读模板，不能改 | 一张装好所有软件的"系统安装光盘" |
| **容器 Container** | 镜像"开机"后的运行实例。同一个镜像能开出很多个容器，互相隔离 | 用光盘装出来的、正在运行的电脑 |
| **数据卷 Volume** | 存在容器**外面**的存储空间，容器删了它还在 | 插在电脑上的 U 盘 |
| **镜像仓库 Registry** | 存放镜像的"云货架"（如 Docker Hub），可上传/下载 | 应用商店 / 货架 |

它们的关系：

```
         docker build            docker run
 Dockerfile ──────────►  镜像  ──────────►  容器（在跑）
                         (Image)             │
                              pull/push      │  mount（挂载）
                        仓库(Registry)       ▼
                        （云货架）          数据卷（U盘，容器外）
```

**一句话记牢：镜像 = 没开机的安装包；容器 = 开机后的运行实例；数据卷 = 外面的保险柜；仓库 = 云货架。**

---

## 2. "怎么可能凭空几个文件就部署了"——构建的原理

这是最关键的一个疑问。答案是：**那几个文件不是"部署文件"，是"制作说明书"。真正的东西是构建时现场做出来的。**

### 2.1 关键认知：Dockerfile 是"菜谱"，不是"成品"

`Dockerfile` 只是一段文字，里面写着：

- 用什么系统当底座（基础镜像）
- 要装哪些依赖
- 要把哪些代码拷进去
- 启动时执行什么命令

它**本身不包含任何代码**。就像菜谱上写着"放多少盐、炒几分钟"，但菜谱里没有菜。

### 2.2 构建（docker build）时，Docker 引擎到底做了什么

当你在有网的机器上进入 `docker/` 目录执行 `docker compose build` 或 `docker compose up -d --build` 时，Docker 引擎按"菜谱"逐步执行：

1. **拉基础镜像**（在线下载）——比如 `python:3.12-slim`、`node:20-slim`，这是"买食材"；
2. **装依赖**——执行 `pip install -r requirements.txt`（后端）、`npm install`（前端），这是"下锅炒"；
3. **拷代码**——把 `backend/`、`frontend/` 复制进镜像；
4. **编译前端**——`npm run build` 把 Vue 源码编译成网页静态文件；
5. **定启动命令**——写下 `CMD ...`，容器一启动就执行它。

每一步执行完，都生成一个**层（layer）**。所有层叠起来，就是最终的镜像。**镜像 ≈ 基础系统 + 你装的所有东西 + 你的代码。**

所以"凭空多几个文件就能部署"的错觉，真相是：**那几个文件是图纸，构建时 Docker 联网把材料运来、现场盖好了整栋房子。**

### 2.3 层与缓存（为什么改一次代码重建很快）

- 镜像是一层一层叠起来的；
- 构建时，**没变过的层直接用缓存**，只有变过的层才重做；
- 所以 Dockerfile 里通常把"变动少的放前面"（依赖清单），"变动多的放后面"（源码）——这样改代码时，装依赖那一步不用重来。

### 2.4 多阶段构建（为什么前端要单独一段）

你的前端要 Node 来编译，但编译完只需要"结果"（静态文件），不需要 Node 运行环境。所以 Dockerfile 分两段：

- **阶段一**：用 Node 镜像编译前端 → 产出 `dist/`
- **阶段二**：用 Python 镜像装后端依赖 → 把 `dist/` 拷进来 → 得到干净的最终镜像

好处：**最终镜像里没有 Node、没有前端源码、没有编译中间产物**，更小、更干净。这也解释了"镜像里没有 Node 但页面能打开"。

### 2.5 你的 LINKOA Dockerfile 逐段讲解

```dockerfile
# 阶段一：构建前端
FROM node:20-slim AS frontend-build   # 底座：Node 20
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./   # 先拷依赖清单
RUN npm ci --no-audit --no-fund                             # 装前端依赖（npm ci = 按锁文件精确安装）
COPY frontend/ ./                                           # 拷前端源码
RUN npm run build                                           # 编译成 dist/

# 阶段二：后端运行时（最终镜像）
FROM python:3.12-slim          # 底座：Python 3.12
ENV PYTHONUNBUFFERED=1 ...     # UTF-8、日志即时输出
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt   # 装后端依赖
COPY backend/ /app/backend/                             # 拷后端代码
COPY --from=frontend-build /build/dist /app/frontend/dist  # 把阶段一的前端成品拷进来
VOLUME ["/app/data"]         # 声明数据卷（数据放这里，容器外）
WORKDIR /app/backend
EXPOSE 8000                  # 对外端口
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> 关键：`COPY backend/ /app/backend/` 里的目录结构不是随便定的，它要和代码里的路径解析一致（LINKOA 的 `config.py` / `main.py` 是按 `backend/`、`frontend/dist` 找文件的）。**改目录结构 = 改代码里的路径，两处必须对上。**

---

## 3. 你的 LINKOA 是怎么被封装的（真实过程）

当时我做的事，本质是"读菜谱 → 写菜谱 → 下厨 → 试吃"：

1. **探查项目**：确认技术栈 = 后端 FastAPI（Python）+ 前端 Vue（Node 构建）+ 默认 SQLite，单端口 8000 托管页面/接口/附件；启动方式是 `uvicorn app.main:app`。
2. **写 Dockerfile**：按上面的多阶段套路写好（2.5 节）。
3. **写 docker-compose.yml**：把"端口、数据挂哪、密钥、健康检查"这些运行参数一次性定好。
4. **写 docker-entrypoint.sh**：因为踩了一个坑——LINKOA 在**导入阶段就挂载 `/uploads` 目录**，目录不存在会直接启动崩溃；于是让入口脚本在启动前先建好目录。
5. **构建 + 启动 + 验证**：进入 `docker/` 目录后 `docker compose build` → `docker compose up -d` → 验证健康检查、登录页、admin 登录、数据落盘到项目根 `data/`。

> 这个"踩坑 → 修 → 验证"的循环，就是封装任何项目的常态。没有一次成功的 Dockerfile，只有不断验证修出来的。

---

## 4. 三种部署方式对比

| 维度 | Docker 在线构建 | Docker 离线 | Windows/Linux 直接部署 |
| --- | --- | --- | --- |
| **需要什么** | 整个项目文件夹（含 docker/ 目录）+ 有网 | 镜像包（tar）+ 数据 | 手动装 Python、Node、MySQL 等 |
| **装环境** | 不需要，构建时自动下载 | 不需要，load 进镜像 | 每台机器手动装，版本要对 |
| **换机器** | 拷贝文件夹 + 一条命令 | 拷 tar + 数据 + load | 重装所有环境，极易出错 |
| **适合** | 有网的部署/演示 | 内网、无外网、给客户 | 老式部署习惯 |
| **命令** | 进 `docker/` 目录后 `docker compose up -d --build` | `docker load -i xx.tar` + run | 一堆手动命令 |

**结论：Docker 就是省掉"装环境"这件事。** 环境跟代码一起打包，这才是一劳永逸的点。

---

## 5. 版本切换原理

> 云上放的不是"容器"，是**镜像**；容器永远在本地跑。版本 = 镜像的 **tag（标签）**。

同一个软件在云货架上有多个版本的镜像并存：

```
Docker Hub（云货架）
├── infiniflow/ragflow:v0.26.1   ← 旧版（独立完整快照）
├── infiniflow/ragflow:v0.28.0   ← 新版
└── infiniflow/ragflow:latest    ← 最新指针
```

切换版本的机制 = **改配置里的版本号 + 拉取 + 重启**：

```bash
# docker-compose.yml 里写：image: infiniflow/ragflow:v0.26.1
docker compose pull      # 从云仓库拉指定版本
docker compose up -d     # 用新版本重启容器
```

- 每个版本都是"当时那套代码+环境"的**独立完整快照**，互不影响；
- 拉下来的旧版镜像还在本地，想退回就改回 tag 再 pull；
- **数据卷在外面，换版本只换程序，数据不动** → 升级不丢数据。

你自己的 LINKOA 以后也可以这样：给镜像打版本号 `docker tag linkoa:latest 你的账号/linkoa:v1.4.17`，推到云仓库，别人就能像装 RagFlow 一样拉你的版本。

---

## 6. 为什么数据要放在容器外

容器是一次性的——升级、换版本、出问题重来，都会"换盒子"。如果数据存在容器里，盒子一扔数据就没了。

所以通过**挂载（bind mount）**把数据引到宿主机文件夹：

```yaml
volumes:
  - ./data:/app/data
# 左边 ./data = 你本机文件夹（物理存放）
# 右边 /app/data = 容器里看到的路径（逻辑位置）
```

效果：
- 容器"看得到"数据（读写的是挂进来的目录）；
- 数据**物理上**住在你本机的 `data` 文件夹；
- 容器删了/重建/升级，数据还在。

> **对比**：如果不挂载，数据会存在"容器内部的可写层"，容器删除即丢失。这就是为什么方案里反复强调 `data` 是命根子。
>
> **V1.4.18 起本地与 Docker 完全统一**：本地 start.bat（Windows）和 Docker 容器都读写项目根 data/（data/linkoa.db + data/uploads/），一份数据、两种启动方式通用，不会再出现『本地有项目、Docker 里是空的』这种分叉。

---

## 7. 换电脑 / 搬家的完整流程

### 7.1 在线方式（目标机能上网）

1. 整个项目文件夹拷过去（含 `data`，数据跟着走）；
2. 目标机装 Docker Desktop；
3. 进入 `docker/` 目录后跑：`docker compose up -d`（首次会自动构建）；
4. 打开 `http://localhost:8000`。

### 7.2 离线方式（无网 / 内网）

1. 本机导出镜像：`docker save -o linkoa.tar linkoa:latest`；
2. 带上 `linkoa.tar` + `data` 文件夹（放同一目录）；
3. 目标机装 Docker（**安装包要提前备好**）→ `docker load -i linkoa.tar` → `docker run`（或用一键脚本）；
4. `load` 完成后，`tar` 文件就没用了可删，但 **`data` 永远要留**。

### 7.3 什么能删、什么不能删

| 东西 | 能删吗 | 原因 |
| --- | --- | --- |
| `data/`（数据） | ❌ 不能删 | 数据命根子 |
| `docker-compose.yml` | ❌ 别删 | 启动配置（端口/卷/密钥） |
| 源码 `backend/ frontend/ docker/` | ⚠️ 可删但建议留 | 镜像里已有代码；删了以后无法重建 |
| `linkoa.tar`（离线包） | ✅ 可删 | load 完就没用了，可随时再导出 |

---

## 8. 常见疑问 FAQ

**Q1：镜像/容器/数据卷删了分别会怎样？**
- 删 `tar` 文件 → 没事（只是快递文件，可再导出）；
- 删 Docker 里的镜像（`docker rmi`）→ 正在跑的容器不受影响，但以后不能从该镜像起新容器；
- 删 `data` → 数据永久丢失，最危险。

**Q2：tar 是压缩包吗？**
镜像"像"压缩包但更"重"——它是一套完整的运行环境快照，类似 .iso 系统镜像。`docker save` 导出的 tar 就是用来搬运/分发的。

**Q3：云端放的是容器吗？**
不是。云端（镜像仓库）放的是**镜像**（没开机的安装包）；容器只能在你本地跑。

**Q4：`docker compose up -d` 和 `up -d --build` 区别？**
`up -d` = 有镜像直接用，没有才构建；`--build` = 每次都强制重建。首次部署两者一样；**改过代码才需要 `--build`**。

**Q5：数据会存在容器里吗？**
看有没有挂载。我们方案里挂了 `./data:/app/data`，所以数据物理上在你本机文件夹，容器能看到但不住在里面。

**Q6：LINKOA 为什么没有 Node 也能跑？**
前端在构建阶段已编译成静态文件（dist），运行阶段后端 FastAPI 直接托管这些文件，不需要 Node 运行时。

---

## 9. 遇到新项目怎么写？（通用方法论）

这是最重要的一章——换个项目你也能自己写。

### 9.1 第一步：先搞清这个项目怎么跑起来的

找 README / 启动脚本 / 依赖文件，回答三个问题：

1. **用什么语言/框架**（看 `requirements.txt` / `package.json` / `pom.xml` / `go.mod` …）；
2. **依赖哪些外部服务**（MySQL？Redis？Nginx？）——这些通常**不塞进镜像**，而是用 compose 另起容器或连外部；
3. **启动命令是什么**（后端 `uvicorn ...`？前端要不要先构建？）。

### 9.2 写 Dockerfile 的通用套路

```dockerfile
# ① 选底座：语言版本对应官方镜像
FROM python:3.12-slim            # 或 node:20-slim / openjdk:17 / golang:1.22 ...

# ② 装依赖（放前面，利于缓存）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ③ 拷代码
COPY . .

# ④ 启动命令（最关键，务必和项目 README 一致）
CMD ["python", "main.py"]
```

进阶技巧：
- **前端 + 后端混在一起的项目** → 用多阶段构建（先 Node 编译，再把产物拷进后端镜像）；
- **目录结构 = 代码里路径解析的依据**，别随意改；
- **启动时目录不存在会崩** → 用 entrypoint 脚本先 `mkdir -p`。

### 9.3 写 docker-compose.yml 的通用套路

```yaml
services:
  你的服务名:
    build:                     # 用项目根做构建上下文（compose 在 docker/ 子目录时写 ..）
      context: ..               # 让 Dockerfile 里的 COPY frontend/、COPY backend/ 相对项目根生效
      dockerfile: docker/Dockerfile   # Dockerfile 位于 docker/ 子目录
    ports:
      - "8000:8000"              # 宿主机端口:容器端口
    environment:                 # 密钥、配置走环境变量，别写死在镜像里
      - DB_URL=xxx
    volumes:
      - ./data:/app/data         # 数据挂到宿主机，容器删了不丢
    restart: unless-stopped      # 崩了自动重启
    healthcheck:                 # 健康检查，能自动判断是否"真起来了"
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
```

### 9.4 通用原则（四个不要）

1. **不要**把密码/API Key 写进 Dockerfile（写进 compose 环境变量或 .env）；
2. **不要**把数据塞进镜像（用卷挂载）；
3. **不要**在容器里放日志/缓存当数据（容器一次性的）；
4. **不要**在改完代码后忘了 `--build`（否则改动不生效）。

### 9.5 从 0 到 1 的完整 checklist

- [ ] 读了 README / 启动脚本，确认技术栈和启动命令
- [ ] 写了 Dockerfile（依赖缓存顺序、多阶段、正确 CMD）
- [ ] 写了 compose（端口、卷、环境变量、healthcheck）
- [ ] 配了 .dockerignore（排除 node_modules / .venv / 数据 / 密钥）
- [ ] 构建成功：`docker compose build`
- [ ] 启动成功：`docker compose up -d`
- [ ] 真实验证：打开页面、登录、数据落盘到宿主机文件夹
- [ ] 换台机器（或删卷重来）验证数据不丢

---

> 最后：**镜像负责"能跑"，文件夹负责"装数据"，数据卷是连接二者的桥。** 把这个关系焊死在脑子里，Docker 就再也不会神秘了。
