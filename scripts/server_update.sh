#!/bin/bash
# LINKOA 服务器端更新脚本
# 用法：把新的 linkoa-latest.tar 传到服务器，然后跑 ./server_update.sh
# 自动：停容器 → 删旧容器 → 删旧镜像 → 加载新镜像 → 启动新容器
# 数据保留在 data/ 目录，不动

set -e
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
DATA_DIR="$(pwd)/data"
JWT_FILE=".jwt_secret"

# 1. 停止并删除旧容器
if docker ps -a --format '{{.Names}}' | grep -q '^linkoa$'; then
  echo "[1/5] 停止旧容器 ..."
  docker stop linkoa
  docker rm linkoa
else
  echo "[1/5] 没有旧容器，跳过"
fi

# 2. 删除旧镜像（释放磁盘空间）
if docker images linkoa:latest --format '{{.Repository}}' | grep -q linkoa; then
  echo "[2/5] 删除旧镜像 ..."
  docker rmi linkoa:latest
else
  echo "[2/5] 没有旧镜像，跳过"
fi

# 3. 加载新镜像
echo "[3/5] 加载新镜像 linkoa-latest.tar ..."
docker load -i linkoa-latest.tar

# 4. JWT 密钥（首次启动自动生成）
if [ ! -f "$JWT_FILE" ]; then
  openssl rand -hex 32 > "$JWT_FILE"
  echo "[4/5] 已生成 JWT 密钥"
else
  echo "[4/5] 复用已有 JWT 密钥"
fi
JWT_SECRET="$(cat "$JWT_FILE")"

# 5. 启动新容器
echo "[5/5] 启动新容器 ..."
docker run -d \
  --name linkoa \
  --restart unless-stopped \
  -p "$PORT:8000" \
  -v "$DATA_DIR:/app/data" \
  -e "DB_URL=sqlite:////app/data/linkoa.db" \
  -e "UPLOAD_DIR=/app/data/uploads" \
  -e "JWT_SECRET=$JWT_SECRET" \
  -e "JWT_EXPIRE_HOURS=24" \
  linkoa:latest

echo ""
echo "==> 更新完成"
echo "  访问: http://<服务器IP>:$PORT"
echo "  数据目录: $DATA_DIR（未动）"
echo ""
echo "常用命令："
echo "  docker logs -f linkoa      # 看日志"
echo "  docker ps                  # 看状态"
