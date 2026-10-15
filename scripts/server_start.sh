#!/bin/bash
# LINKOA 服务器端一键启动脚本（离线环境，不依赖 docker compose）
# 用法：
#   1. 把 linkoa-latest.tar 和本脚本放同一目录
#   2. chmod +x server_start.sh
#   3. ./server_start.sh
#
# 数据目录：脚本同目录下的 data/（首次启动自动创建）
# 端口：默认 8000，可用环境变量 PORT=8001 覆盖
# JWT 密钥：首次启动自动生成一个随机值写入 .jwt_secret，重启不换

set -e

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
DATA_DIR="$(pwd)/data"
mkdir -p "$DATA_DIR/uploads"

# JWT 密钥：已存在就复用，不存在就生成一个 64 字节随机 hex
JWT_FILE=".jwt_secret"
if [ ! -f "$JWT_FILE" ]; then
  openssl rand -hex 32 > "$JWT_FILE"
  echo "[init] 已生成 JWT 密钥: $JWT_FILE"
fi
JWT_SECRET="$(cat "$JWT_FILE")"

# 检查镜像是否已导入
if ! docker images linkoa:latest --format '{{.Repository}}' | grep -q linkoa; then
  echo "[load] 首次运行，导入镜像 linkoa-latest.tar ..."
  docker load -i linkoa-latest.tar
fi

# 已存在同名容器先删掉（数据在 data/ 卷里，不影响）
if docker ps -a --format '{{.Names}}' | grep -q '^linkoa$'; then
  echo "[stop] 停止旧容器 ..."
  docker rm -f linkoa > /dev/null
fi

echo "[run] 启动容器 linkoa，端口 $PORT ..."
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
echo "==> 完成"
echo "  访问: http://<服务器IP>:$PORT"
echo "  初始账号: admin / admin123（首次登录后请到「修改密码」改掉）"
echo "  数据目录: $DATA_DIR"
echo ""
echo "常用命令："
echo "  docker logs -f linkoa      # 看日志"
echo "  docker restart linkoa      # 重启"
echo "  docker stop linkoa         # 停止"
echo "  docker rm -f linkoa        # 删容器（数据保留在 data/）"
