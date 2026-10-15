# ============================================================================
#  LINKOA 领客文创 OA - Docker 镜像
# ============================================================================

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY frontend/dist /app/frontend/dist

COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN tr -d '\r' < /usr/local/bin/docker-entrypoint.sh > /usr/local/bin/docker-entrypoint.sh.tmp \
    && mv /usr/local/bin/docker-entrypoint.sh.tmp /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

VOLUME ["/app/data"]

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
