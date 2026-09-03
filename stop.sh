#!/usr/bin/env bash
# ============================================
#   LINKOA OA - Stop Services (Linux/macOS)
# ============================================
# 按端口 8000 / 5173 结束监听进程
cd "$(dirname "$0")"

echo "============================================"
echo "  LINKOA OA - Stop Services (Linux/macOS)"
echo "============================================"
echo "Checking backend port 8000 and frontend port 5173 ..."

stopped=0
for port in 8000 5173; do
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti tcp:"$port" 2>/dev/null)
    elif command -v fuser >/dev/null 2>&1; then
        pids=$(fuser "$port"/tcp 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$')
    else
        pids=""
    fi
    for pid in $pids; do
        echo "  Port $port : killing PID $pid ..."
        if kill -9 "$pid" 2>/dev/null; then
            stopped=1
        fi
    done
done

echo
if [ "$stopped" = 1 ]; then
    echo "All services stopped."
else
    echo "No running service found (ports 8000 / 5173 are not listening)."
fi
