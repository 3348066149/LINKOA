# docs/ 文档索引

> 项目文档统一索引（版本 V1.4.18，2026-09-04 整理）。
> 按读者分三类：**使用部署**、**开发设计**、**原理学习**。

---

## 一、使用 & 部署（看根目录 README 就够了）

| 文档 | 位置 | 说明 |
| --- | --- | --- |
| 安装·启动·演示指南 | 项目根 `README.md` | **使用入口**：环境要求、Docker/脚本/手动三种启动、数据库、模块说明、演示清单、FAQ |
| Docker 部署指南 | `docker/README.md` | **Docker 专属总指南**：在线部署、离线部署、版本兼容（v2/v1）、低版本兜底、数据备份、MySQL 可选、FAQ |
| 离线部署手册 | `docker/离线部署说明.txt` | **无外网场景**手把手：传包→校验→加载→启动→排错（与 docker/README.md 配合） |

> 部署时只需看根 `README.md` + `docker/README.md`（离线再看同目录 `离线部署说明.txt`）三份。

## 二、原理学习（想弄懂 Docker）

| 文档 | 说明 |
| --- | --- |
| `Docker入门与原理.md` | 从概念到实操：镜像/容器/数据卷/仓库、构建原理、LINKOA 封装实录、三种部署对比、版本切换、新项目怎么写 Dockerfile |

## 三、开发 & 设计（`docs/程序开发人员看/`）

> 面向开发/接手代码的人，包含需求、库表、接口、AI 总控、数据库互转等。

| 文档 | 说明 |
| --- | --- |
| `程序开发人员看/领客文创 OA_V1_PRD.md` | 产品需求文档（主系统） |
| `程序开发人员看/领客文创OA_V1_客户满意度评价_PRD.md` | 客户满意度评价模块 PRD |
| `程序开发人员看/领客文创 OA_V1_Database.md` | 数据库设计（23 张表） |
| `程序开发人员看/青岛领客文创OA_V1_后端接口清单.md` | 后端接口清单 |
| `程序开发人员看/领客文创OA_V1_AI开发总控指令.md` | AI 辅助开发总控指令 |
| `程序开发人员看/领客文创OA_V1_数据库互转与MySQL部署指南.md` | SQLite↔MySQL 迁移 + 原生 MySQL 部署 |

## 四、历史设计文档（留档参考）

| 文档 | 说明 |
| --- | --- |
| `ai-refactor-design.md` + `ai-refactor-class-diagram.mermaid` + `ai-refactor-sequence-diagram.mermaid` | AI 助手重构设计（V1.4.16 前后） |
| `ai-satisfaction-design.md` + `ai-satisfaction-class-diagram.mermaid` + `ai-satisfaction-sequence-diagram.mermaid` | 客户满意度评价设计 |

> 同类历史材料另见 `artifacts/`（AI 助手改造方案、总体 overview 等；交付记录已并入其中）。

---

## 快速定位

- **"我要部署/启动"** → 根 `README.md` → 三章「启动方式总览」→ 3.1 Docker / 四章手动 / 五章脚本
- **"我要用 Docker 跑起来"** → `docker/README.md`（离线看 `docker/离线部署说明.txt`）
- **"我想搞懂 Docker"** → `docs/Docker入门与原理.md`
- **"我要改代码"** → `docs/程序开发人员看/` + `backend/README.md` + `frontend/README.md`
