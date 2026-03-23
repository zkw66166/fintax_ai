#!/bin/bash
cd /var/www/fintax_ai
pkill -f uvicorn
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > dev.log 2>&1 &
echo "服务已启动，日志文件：/var/www/fintax_ai/dev.log"