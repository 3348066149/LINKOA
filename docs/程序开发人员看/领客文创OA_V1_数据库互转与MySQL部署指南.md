# 青岛领客文创OA 数据库互转与 MySQL 部署指南（V1.4.16）

> 适用版本：V1.4.16（SQLite 默认 + MySQL 双支持，启动期结构自愈迁移；V1.4.13 为 AI 助手检索与富上下文优化，纯后端改动，库结构无变化；V1.4.14 预置 3 套项目流程模板 + 「布展搭建」节点类型，模板初始化挂启动流程幂等自愈，库结构无变化；V1.4.15 客户账号改绑客户单位：sys_user 新增 category_id 列，customer_id 保留为历史兼容，启动幂等回填存量，结构自愈迁移自动补列；V1.4.16 AI 助手数据供给改造：去关键词检索与联网搜索，改结构化知识库全量注入，库结构无变化）
> 配套文档：领客文创OA_V1_Database.md、领客文创OA_V1_PRD.md
> 说明：本文档指导从 **SQLite（单机便携）** 切换到 **MySQL（服务器多用户）**，并覆盖反向迁移。

---

## 目录

- [1. 先回答两个关键问题](#1-先回答两个关键问题)
- [2. 服务器安装 MySQL](#2-服务器安装-mysql)
- [3. 创建数据库与专用账号](#3-创建数据库与专用账号)
- [4. 项目切换到 MySQL（改配置）](#4-项目切换到-mysql改配置)
- [5. SQLite → MySQL 数据迁移](#5-sqlite--mysql-数据迁移)
- [6. 拷贝附件文件（uploads 目录）](#6-拷贝附件文件uploads-目录)
- [7. 启动与验证](#7-启动与验证)
- [8. 反向迁移：MySQL → SQLite](#8-反向迁移mysql--sqlite)
- [9. 上线前安全检查清单](#9-上线前安全检查清单)
- [10. 数据库日常备份与恢复](#10-数据库日常备份与恢复)
- [11. 常见问题 FAQ](#11-常见问题-faq)

---

## 1. 先回答两个关键问题

### Q1：目前数据库是 SQLite 吗？

**是。** 当前系统默认使用 SQLite。**V1.4.4 起数据库文件回到项目内 `backend/linkoa.db`**（配置见 `backend/.env` 的 `DB_URL`），相对路径写法，随项目文件夹整体迁移，不再依赖任何机器相关的绝对路径。

> 历史沿革：早期在 `backend/linkoa.db`；V1.4.3 曾迁到 `C:/Users/Administrator/.workbuddy/linkoa-data/app.db`（当时项目目录位于百度网盘下载目录、会被网盘客户端锁文件）；V1.4.4 改为相对路径写回项目内，兼顾便携与不被网盘锁文件。

```ini
# backend/.env 当前内容
DB_URL=sqlite:///./linkoa.db
```

`./linkoa.db` 是相对路径，`backend/app/config.py` 会按 `__file__` 解析为 `backend/linkoa.db` 的绝对路径，因此**项目文件夹复制到任何机器、任何目录都能正确定位数据库**。

SQLite 的特点：零安装、单文件、随项目拷贝即走，适合单机/小团队。但它是**文件型数据库**，多用户并发写入能力弱，正式上线到服务器建议换 MySQL。

### Q2：用 MySQL 需要给公司服务器装 MySQL 吗？

**需要。** 应用本身不内置数据库，选择 MySQL 存储，就必须有一台能连上的 MySQL 服务端。做法是**在公司服务器（或内网一台机器）上安装 MySQL 服务端**，第 2 节有详细步骤。

对本项目而言，只需改 `.env` 里的一行 `DB_URL`，再用项目自带的迁移脚本导入数据即可，**不需要改任何业务代码**。

---

## 2. 服务器安装 MySQL

### 2.1 Linux 服务器（CentOS / Rocky）

```bash
# CentOS / Rocky / Alibaba Cloud Linux
sudo yum install -y mysql-server
sudo systemctl enable --now mysqld

# 首次安装后查看临时 root 密码（如提示）
sudo grep 'temporary password' /var/log/mysqld.log

# 执行安全初始化（设 root 密码、删匿名用户）
sudo mysql_secure_installation
```

### 2.2 Linux 服务器（Ubuntu / Debian）

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation
```

### 2.3 Windows Server

1. 下载 MySQL Installer：https://dev.mysql.com/downloads/installer/
2. 选择 **Server only**，一路下一步；
3. 在配置步骤设置 **root 密码**，字符集选 `utf8mb4`；
4. 安装完成后，验证服务已在"服务"里启动（服务名 `MySQL80`）。

### 2.4 验证安装成功

```bash
# Linux 下执行
mysql -u root -p
# 能进入 mysql> 提示符即安装成功，然后退出
exit;
```

> **安全提示**：生产环境不要用 root 直接连应用。第 3 节会创建专用账号。

---

## 3. 创建数据库与专用账号

登录 MySQL（Linux 命令行，或 Windows 用 MySQL Workbench 操作等价）：

```bash
mysql -u root -p
```

执行以下 SQL（**请把密码 `Lingke@2026` 换成你自己的强密码**）：

```sql
-- 1. 创建数据库（必须 utf8mb4，与项目约定一致）
CREATE DATABASE IF NOT EXISTS linkoa
  DEFAULT CHARSET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 2. 创建专用账号并授权（仅授权 linkoa 库，别给全库权限）
CREATE USER 'linkoa'@'localhost' IDENTIFIED BY 'Lingke@2026';
GRANT ALL PRIVILEGES ON linkoa.* TO 'linkoa'@'localhost';

-- 如果应用服务器和数据库不是同一台机器，把 localhost 换成应用服务器 IP：
-- CREATE USER 'linkoa'@'192.168.1.20' IDENTIFIED BY 'Lingke@2026';
-- GRANT ALL PRIVILEGES ON linkoa.* TO 'linkoa'@'192.168.1.20';

FLUSH PRIVILEGES;
EXIT;
```

> **库可以先空着**，不需要手动导 `init.sql`——项目迁移脚本会自动建表（第 5 节）。
> 如果你想手工初始化空库结构，也可以：`mysql -u root -p linkoa < init.sql`（脚本在 `backend/init.sql`），但注意这样会插入默认管理员 admin，再跑迁移脚本时迁移脚本会先清空表，所以**建议直接让迁移脚本建表，别先导 init.sql**。

---

## 4. 项目切换到 MySQL（改配置）

本项目支持两种改法，**任选其一**。

### 4.1 方法一：用环境变量（推荐，不写进 .env，适合部署脚本）

Windows CMD：

```bat
set LINKOA_MYSQL_URL=mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4
```

Linux bash：

```bash
export LINKOA_MYSQL_URL='mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4'
```

> 说明：项目所有数据库脚本（`config.py`、`switch_db.py`、两个迁移脚本）都会读取 `LINKOA_MYSQL_URL` 环境变量；设置了它，就不用改任何文件。

### 4.2 方法二：用项目自带的切换脚本

```bash
cd backend

# Windows（在命令行先设置环境变量再切换，避免硬编码口令留在 .env）
set LINKOA_MYSQL_URL=mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4
python switch_db.py mysql

# Linux
LINKOA_MYSQL_URL='mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4' \
python switch_db.py mysql
```

脚本会把 `.env` 里的 `DB_URL` 替换成 MySQL 连接串，输出：

```
已切换到 MYSQL：mysql+pymysql://linkoa:****@localhost:3306/linkoa?charset=utf8mb4
提示：切换后需重启后端；如需同步数据，先跑对应迁移脚本：
  - MySQL→SQLite : python migrate_mysql_to_sqlite.py
  - SQLite→MySQL : python migrate_sqlite_to_mysql.py
```

### 4.3 手工改 .env（最直白，看懂即会）

编辑 `backend/.env`，把第一行改成：

```ini
DB_URL=mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4
```

> **连接串格式解析**：
> `mysql+pymysql://用户名:密码@数据库地址:3306/linkoa?charset=utf8mb4`
> - `用户名:密码`：第 3 节创建的专用账号
> - `数据库地址`：本机填 `localhost`；数据库在其他机器填其内网 IP
> - `linkoa`：数据库名
> - `?charset=utf8mb4`：必须带，否则中文可能乱码

---

## 5. SQLite → MySQL 数据迁移

> 前置条件：
> 1. MySQL 已安装并启动；
> 2. 第 3 节的 `linkoa` 库已创建（迁移脚本**不会**自动建库，库不存在会报错）；
> 3. `backend/.env` 已切到 MySQL（第 4 节），或设置了 `LINKOA_MYSQL_URL`。

### 5.1 迁移前备份 SQLite（强烈建议）

```bash
cd backend
copy linkoa.db linkoa_backup.db                    # Windows
# cp linkoa.db linkoa_backup.db                    # Linux
```

### 5.2 执行迁移

```bash
cd backend

# Windows：先设环境变量（与切换时的账号一致）
set LINKOA_MYSQL_URL=mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4
python migrate_sqlite_to_mysql.py

# Linux
LINKOA_MYSQL_URL='mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4' \
python migrate_sqlite_to_mysql.py
```

脚本会**先清空 MySQL 的 linkoa 库所有表，再按 SQLite 数据重建并写入**，输出类似：

```
  sys_user: 5 行
  customer_category: 3 行
  customer: 12 行
  flow_template: 4 行
  ...（共 23 张表）
迁移完成，共 236 行 → MySQL linkoa 库
```

> **重要**：
> - 迁移脚本是"覆盖式"：目标库里有旧数据会被清空重写。**不要把生产 MySQL 当测试目标**。
> - 迁移后 `.env` 的 `DB_URL` 应保持 MySQL 连接串，否则后端启动会读回 SQLite。

### 5.3 迁移脚本做了什么（了解即可）

| 步骤 | 说明 |
|------|------|
| 1. 读 SQLite | 路径从 `backend/.env` 的 `DB_URL` 读取（V1.4.4 起为项目内 `backend/linkoa.db`） |
| 2. 清空目标 | `Base.metadata.drop_all` 清空 MySQL linkoa 库旧表 |
| 3. 重建表 | `Base.metadata.create_all` 按模型建 23 张表（utf8mb4，V1.4.7 含 project_contact_rel，V1.4.8 新增 ai 三表） |
| 4. 逐表导数据 | 按 `sys_user → ... → sys_operation_log` 顺序逐行插入 |
| 5. 附件路径 | `attachment.file_path` 保持相对 `uploads/` 的路径，无需转换 |

---

## 6. 拷贝附件文件（uploads 目录）

数据库只存了**文件的相对路径**，附件本体在 `backend/uploads/` 目录里。**必须一并拷到服务器**，否则历史附件下载会 404。

```bash
# 把本机的 backend/uploads 整个目录复制到服务器的 backend/uploads
# Windows 用 robocopy：
robocopy "E:\BaiduNetdiskDownload\LINKOA\backend\uploads" "D:\LINKOA\backend\uploads" /E

# Linux scp 示例：
scp -r uploads 用户@服务器IP:/opt/linkoa/backend/
```

> 迁移脚本 `migrate_sqlite_to_mysql.py` 不做文件搬运，只搬数据库记录，附件目录要手动拷贝。

---

## 7. 启动与验证

### 7.1 启动后端（服务器上）

```bash
cd backend
# Windows
..\ .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Linux（建议用项目根目录的 start.sh）
./start.sh
```

> **V1.4.4 起：启动期自动补齐缺失列。** 后端启动时 `auto_add_missing_columns()` 会比对 ORM 模型与数据库实际结构，缺的列自动 `ALTER TABLE ADD COLUMN` 补齐，然后才 `create_all`。
> 无论 SQLite 还是 MySQL 都生效——**升级代码后老库无需手工执行迁移 SQL**，启动一次即完成升级。
> 已知限制：只会「加列」，不会删除列、不会修改既有列类型/重命名；这类结构性变更仍需按第 5 节重新迁移或手工处理。

### 7.2 验证数据库已切换到 MySQL

```bash
# 1. 后端健康检查
curl http://127.0.0.1:8000/api/health
# 期望：{"code":200,"msg":"","data":"ok"}

# 2. 直接查 MySQL 里的数据（确认已切换，不是读回 SQLite）
mysql -u linkoa -p -e "SELECT COUNT(*) FROM linkoa.sys_user;"
mysql -u linkoa -p -e "SELECT username,real_name,role FROM linkoa.sys_user;"
```

### 7.3 服务器防火墙/安全组放行

| 端口 | 用途 | 建议 |
|------|------|------|
| 8000 | OA 系统 Web | 内网全放行；公网按需放行或走内网访问 |
| 3306 | MySQL | **只允许应用服务器访问，不要对公网开放** |

Linux 防火墙（如果启用）：

```bash
sudo firewall-cmd --permanent --add-port=8000/tcp && sudo firewall-cmd --reload
```

云服务器记得在控制台**安全组**里同步放行。

---

## 8. 反向迁移：MySQL → SQLite

用于回退（服务器出问题想回到单机）或把服务器数据带回本机。**方向与第 5 节相反，脚本是现成的。**

### 8.1 前置

1. 能从当前环境连上 MySQL（设好 `LINKOA_MYSQL_URL` 或 `.env` 为 MySQL）；
2. 准备一个 SQLite 目标文件（脚本会清空并重建 `.env` 中 `DB_URL` 指向的库，**别在还有用的时候乱跑**）。

### 8.2 执行

```bash
cd backend

# Windows
set LINKOA_MYSQL_URL=mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4
python migrate_mysql_to_sqlite.py

# Linux
LINKOA_MYSQL_URL='mysql+pymysql://linkoa:Lingke@2026@localhost:3306/linkoa?charset=utf8mb4' \
python migrate_mysql_to_sqlite.py
```

输出：`迁移完成，共 N 行 → <DB_URL 指向的库>`

> 该脚本会把 `attachment.file_path` 里**绝对路径**转回相对 `uploads/` 的相对路径，保证拷贝到别的电脑也能用（便携化设计）。

### 8.3 切回 SQLite

```bash
# Windows
python switch_db.py sqlite
# Linux
python switch_db.py sqlite
```

重启后端即回到 SQLite 模式。

---

## 9. 上线前安全检查清单

- [ ] **改默认密码**：`admin / admin123` 上线前必须改掉（系统内改，或改后更新 SQLite/MySQL 数据）
- [ ] **不用 root 连库**：应用使用第 3 节创建的专用账号，只授权 `linkoa` 库
- [ ] **3306 不对外**：MySQL 只允许内网/应用服务器访问
- [ ] **换掉 JWT_SECRET**：`backend/.env` 里 `JWT_SECRET` 是开发默认值，上线改成随机长串（>=32 字符）
- [ ] **换掉开发口令**：连接串里不要再用 `123456`，用强密码
- [ ] **定期备份**：见第 10 节
- [ ] **测试环境先行**：先在内网测试机完整跑一遍 切换→迁移→验证，再上生产

---

## 10. 数据库日常备份与恢复

### 10.1 MySQL 备份（mysqldump）

```bash
# 备份整个 linkoa 库
mysqldump -u linkoa -p --single-transaction linkoa > linkoa_backup_$(date +%Y%m%d).sql

# 恢复
mysql -u linkoa -p linkoa < linkoa_backup_20260831.sql
```

建议配置 crontab 每日备份（Linux）：

```bash
0 2 * * * mysqldump -u linkoa -p'密码' --single-transaction linkoa > /backup/linkoa_$(date +\%Y\%m\%d).sql
```

### 10.2 SQLite 备份

直接复制文件即可：

```bash
copy backend\linkoa.db backup\linkoa_20260831.db
```

---

## 11. 常见问题 FAQ

### Q1：跑迁移脚本报 `Unknown database 'linkoa'`

库没建。先执行第 3 节的 `CREATE DATABASE linkoa ...`。脚本只建表，**不建库**。

### Q2：跑迁移脚本报 `Access denied for user`

账号密码/权限不对。用第 3 节的 SQL 重新授权，确认 `LINKOA_MYSQL_URL` 里账号密码与数据库一致。

### Q3：切换后重启，数据"没了"

多半是 `.env` 里 `DB_URL` 没真正切到 MySQL（或环境变量没生效），后端又读回 SQLite 了。验证方法见 7.2。

### Q4：页面能打开，但中文乱码

连接串**少了 `?charset=utf8mb4`**。补上并重启后端；同时确认建库时用了 utf8mb4。

### Q5：历史附件下载 404

`uploads` 目录没拷贝到服务器（第 6 节）。数据库有记录、磁盘没文件，就会 404。

### Q6：前端打包的 dist 需要重新构建吗？

不需要。前端通过 `/api` 和 `/uploads` 反向代理/静态托管访问后端，**切数据库不影响前端**。

### Q7：服务器上还要装 Python 依赖吗？

要。服务器第一次部署需创建虚拟环境并安装依赖：

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
# Linux
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` 已包含 MySQL 驱动 `PyMySQL` 和 `cryptography`（MySQL 8 认证加密需要）。

---

## 附：本项目数据库相关文件一览

| 文件 | 作用 |
|------|------|
| `backend/linkoa.db` | SQLite 数据库文件（V1.4.4 起，`backend/.env` 的 `DB_URL=sqlite:///./linkoa.db` 相对路径指定，随项目文件夹迁移） |
| `backend/.env` | 数据库连接配置（`DB_URL` 在这里切换） |
| `backend/switch_db.py` | 一键切换 `.env` 的数据库类型（两个分支均为相对路径/可配置路径，不含机器相关绝对路径） |
| `backend/migrate_sqlite_to_mysql.py` | SQLite → MySQL 数据迁移 |
| `backend/migrate_mysql_to_sqlite.py` | MySQL → SQLite 数据迁移 |
| `backend/init.sql` | MySQL 手工建表/初始化脚本（可选，迁移脚本会替代它建表） |
| `backend/uploads/` | 附件文件存储目录（迁移时要一并拷贝） |
