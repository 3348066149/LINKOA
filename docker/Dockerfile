# ============================================================================
#  LINKOA 领客文创 OA - Docker 镜像（多阶段构建）
#  阶段一：Node 构建前端 dist
#  阶段二：Python 运行时，单端口 8000 托管「页面 + API + 附件」
# ============================================================================

# ------------------------- 阶段一：构建前端 -------------------------
FROM node:20-slim AS frontend-build
WORKDIR /build

# 先只拷贝依赖清单，利用 Docker 层缓存：package.json / lock 未变化时跳过重新下载
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

# 拷贝前端源码并构建（产物在 /build/dist）
COPY frontend/ ./
RUN npm run build

# ------------------------- 阶段二：后端运行时 -------------------------
FROM python:3.12-slim

# UTF-8 环境（中文文案/日志不乱码）+ Python 日志即时输出
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# 先装依赖（利用层缓存），再拷代码
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 目录结构必须与 config.py / main.py 的路径解析一致：
#   backend/        -> /app/backend
#   frontend/dist   -> /app/frontend/dist
COPY backend/ /app/backend/
COPY --from=frontend-build /build/dist /app/frontend/dist

# 入口脚本：启动前确保附件目录存在（main.py 导入阶段即挂载 /uploads，目录缺失会启动失败）
# 注意：build context 是项目根，docker-entrypoint.sh 位于 docker/ 下，故路径带 docker/ 前缀
COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && tr -d '\r' < /usr/local/bin/docker-entrypoint.sh > /usr/local/bin/docker-entrypoint.sh.tmp \
    && mv /usr/local/bin/docker-entrypoint.sh.tmp /usr/local/bin/docker-entrypoint.sh

# 数据卷：数据库 + 上传附件（推荐由 docker-compose 挂载到宿主机 ./data）
VOLUME ["/app/data"]

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
