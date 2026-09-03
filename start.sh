#!/usr/bin/env bash
# ============================================
#   LINKOA OA - One-Click Start (Linux/macOS)
# ============================================
# 与 start.bat 逻辑一致：自动建 venv → 装依赖 → 前端完整性自检/重建 → 启动后端
cd "$(dirname "$0")"

echo "============================================"
echo "  LINKOA OA - One-Click Start (Linux/macOS)"
echo "============================================"

# ---- 检查 dist 是否完整：dist/index.html 引用的每个资源文件都必须存在 ----
check_dist_health() {
    [ -f "frontend/dist/index.html" ] || return 1
    local missing=0 asset
    while IFS= read -r asset; do
        [ -n "$asset" ] || continue
        if [ ! -f "frontend/dist$asset" ]; then
            missing=1
        fi
    done < <(grep -oE '/assets/[A-Za-z0-9_.-]+' "frontend/dist/index.html")
    [ "$missing" -eq 0 ]
}

# ---- 1. 后端虚拟环境 + Python 依赖 ----
if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual env .venv ..."
    python3 -m venv .venv || { echo "[ERROR] python3 not found. Please install Python 3.10+."; exit 1; }
fi

echo "Installing backend dependencies ..."
.venv/bin/python -m pip install -r "backend/requirements.txt" -q || {
    echo "[ERROR] pip install failed. Aborting."
    exit 1
}

# ---- 2. 前端：node_modules + 完整 dist ----
if ! command -v node >/dev/null 2>&1; then
    echo "[INFO] Node not found, skip frontend build. Make sure frontend/dist is complete."
else
    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend dependencies ..."
        (cd frontend && npm install) || {
            echo "[ERROR] npm install failed. Aborting."
            exit 1
        }
    fi

    if ! check_dist_health; then
        echo "Building frontend ..."
        if ! (cd frontend && npm run build); then
            echo "[WARN] build failed, retrying after npm install ..."
            (cd frontend && npm install)
            (cd frontend && npm run build)
        fi
        if ! check_dist_health; then
            echo "[ERROR] frontend build failed or dist still incomplete. Aborting."
            exit 1
        fi
        echo "Frontend build done."
    else
        echo "Frontend dist OK, skip build."
    fi
fi

# ---- 3. 启动后端（单端口托管 页面+API+附件） ----
echo "Backend listening on 0.0.0.0:8000"
echo "Open in browser:  http://localhost:8000  (or http://127.0.0.1:8000)"
echo "For LAN access:   http://<this-machine-ip>:8000   (use 'ip addr' to check)"
echo "Press Ctrl+C to stop."
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
