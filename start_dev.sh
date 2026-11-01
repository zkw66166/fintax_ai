#!/usr/bin/env bash
# fintax_ai 阿里云开发环境一键启动脚本
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_URL="http://127.0.0.1:8000/docs"
FRONTEND_URL="http://127.0.0.1:5173/"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}"
export ALLOWED_ORIGINS="http://121.41.87.137,http://121.41.87.137:8000,http://121.41.87.137:5173"

mkdir -p "$ROOT_DIR/logs"

wait_http() {
    local name="$1"
    local url="$2"
    local log_file="$3"
    for attempt in $(seq 1 45); do
        if curl -fsS --max-time 3 -o /dev/null 2>/dev/null "$url"; then
            echo "[OK] $name 已通过健康检查"
            return 0
        fi
        sleep 1
    done
    echo "[ERROR] $name 启动超时，最近日志如下：" >&2
    tail -n 40 "$log_file" >&2 || true
    return 1
}

echo "=========================================="
echo "fintax_ai 开发环境启动"
echo "项目目录：$ROOT_DIR"
echo "=========================================="

if curl -fsS --max-time 3 -o /dev/null 2>/dev/null "$BACKEND_URL"; then
    echo "[SKIP] 后端已在运行（端口 8000）"
else
    if ss -ltnH '( sport = :8000 )' | wc -l | { read -r count; test "$count" -ne 0; }; then
        echo "[ERROR] 端口 8000 已被其他进程占用，请先检查该进程" >&2
        exit 1
    fi
    echo "[START] 启动 FastAPI 后端（热重载）"
    cd "$ROOT_DIR"
    nohup uvicorn api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir "$ROOT_DIR/api" \
        --reload-dir "$ROOT_DIR/modules" \
        --reload-dir "$ROOT_DIR/config" \
        >> "$ROOT_DIR/dev.log" 2>&1 < /dev/null &
    echo $! > "$ROOT_DIR/logs/backend-dev.pid"
fi
wait_http "后端" "$BACKEND_URL" "$ROOT_DIR/dev.log"

if curl -fsS --max-time 3 -o /dev/null 2>/dev/null "$FRONTEND_URL"; then
    echo "[SKIP] Vite 前端已在运行（端口 5173）"
else
    if ss -ltnH '( sport = :5173 )' | wc -l | { read -r count; test "$count" -ne 0; }; then
        echo "[ERROR] 端口 5173 已被其他进程占用，请先检查该进程" >&2
        exit 1
    fi
    echo "[START] 启动 Vite 前端"
    cd "$ROOT_DIR/frontend"
    nohup npm run dev -- --host 127.0.0.1 --port 5173 \
        >> "$ROOT_DIR/frontend-dev.log" 2>&1 < /dev/null &
    echo $! > "$ROOT_DIR/logs/frontend-dev.pid"
fi
wait_http "Vite 前端" "$FRONTEND_URL" "$ROOT_DIR/frontend-dev.log"

echo "[CHECK] 校验并加载 Nginx 配置"
nginx -t
if systemctl is-active --quiet nginx; then
    systemctl reload nginx
else
    systemctl start nginx
fi

HOME_PAGE="$(curl -fsS --max-time 10 http://127.0.0.1/)"
if [[ "$HOME_PAGE" != *"/@vite/client"* ]]; then
    echo "[ERROR] 80 端口未返回 Vite 开发页面，请检查 Nginx 配置" >&2
    exit 1
fi

echo "=========================================="
echo "[OK] 开发环境已全部启动"
echo "访问地址：http://121.41.87.137/"
echo "后端日志：$ROOT_DIR/dev.log"
echo "前端日志：$ROOT_DIR/frontend-dev.log"
echo "=========================================="
