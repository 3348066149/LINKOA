#!/bin/sh
# ============================================================================
#  LINKOA OA - 容器入口脚本
#  main.py 在导入阶段就会挂载 /uploads 静态目录（StaticFiles），
#  若目录不存在会直接抛 RuntimeError 导致容器退出。
#  这里在启动 uvicorn 前确保目录存在（兼容 compose 的 /app/data 与默认的 backend/uploads 两种路径）。
# ============================================================================
set -e

mkdir -p /app/data/uploads /app/backend/uploads

exec "$@"
