#!/bin/bash
# Fintax AI 服务启动脚本

echo "=========================================="
echo "Fintax AI 服务启动"
echo "=========================================="
echo ""

# 创建日志目录
mkdir -p logs

# 检查并清理端口
echo "[1/4] 清理旧进程..."
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
sleep 2

# 启动后端
echo "[2/4] 启动后端服务 (端口 8000)..."
cd /d/fintax_ai
python -m uvicorn api.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"
sleep 3

# 启动前端
echo "[3/4] 启动前端服务..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"
sleep 5

# 显示状态
echo "[4/4] 检查服务状态..."
echo ""
echo "=========================================="
echo "服务已启动！"
echo "=========================================="
echo "后端: http://localhost:8000"
echo "前端: http://localhost:5173"
echo "调试: http://localhost:5173/debug.html"
echo ""
echo "日志文件:"
echo "  - logs/backend.log"
echo "  - logs/frontend.log"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

# 等待用户中断
wait
