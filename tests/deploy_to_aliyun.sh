#!/bin/bash
# 阿里云部署脚本 - fintax_ai
# 使用方法: ./deploy_to_aliyun.sh

set -e  # 遇到错误立即退出

# 配置
ALIYUN_HOST="121.41.87.137"
ALIYUN_USER="root"
ALIYUN_PATH="/var/www/fintax_ai"
LOCAL_PATH="D:/fintax_ai"

echo "========================================="
echo "fintax_ai 阿里云部署脚本"
echo "========================================="
echo ""

# 步骤1：检查本地构建
echo "[1/6] 检查本地前端构建..."
if [ ! -d "$LOCAL_PATH/frontend/dist" ]; then
    echo "❌ 前端构建不存在，正在构建..."
    cd "$LOCAL_PATH/frontend"
    npm run build
    echo "✅ 前端构建完成"
else
    echo "✅ 前端构建已存在"
fi

# 步骤2：测试SSH连接
echo ""
echo "[2/6] 测试SSH连接..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes $ALIYUN_USER@$ALIYUN_HOST "echo '连接成功'" 2>/dev/null; then
    echo "✅ SSH连接正常"
else
    echo "❌ SSH连接失败"
    echo "请检查："
    echo "  1. 网络连接"
    echo "  2. SSH密钥配置"
    echo "  3. 服务器IP地址"
    echo ""
    echo "如果提示 'Host key verification failed'，运行："
    echo "  ssh-keygen -R $ALIYUN_HOST"
    exit 1
fi

# 步骤3：备份服务器文件
echo ""
echo "[3/6] 备份服务器文件..."
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
ssh $ALIYUN_USER@$ALIYUN_HOST "cd $ALIYUN_PATH && \
    cp api/main.py api/main.py.backup.$BACKUP_TIME 2>/dev/null || true && \
    mv frontend/dist frontend/dist.backup.$BACKUP_TIME 2>/dev/null || true"
echo "✅ 备份完成: main.py.backup.$BACKUP_TIME, dist.backup.$BACKUP_TIME"

# 步骤4：上传后端文件
echo ""
echo "[4/6] 上传后端文件..."
scp "$LOCAL_PATH/api/main.py" $ALIYUN_USER@$ALIYUN_HOST:$ALIYUN_PATH/api/
echo "✅ 后端文件上传完成"

# 步骤5：上传前端构建
echo ""
echo "[5/6] 上传前端构建..."
scp -r "$LOCAL_PATH/frontend/dist" $ALIYUN_USER@$ALIYUN_HOST:$ALIYUN_PATH/frontend/
echo "✅ 前端构建上传完成"

# 步骤6：重启服务
echo ""
echo "[6/6] 重启后端服务..."
ssh $ALIYUN_USER@$ALIYUN_HOST "cd $ALIYUN_PATH && \
    export ALLOWED_ORIGINS='http://121.41.87.137,http://121.41.87.137:8000' && \
    pkill -f 'uvicorn api.main:app' 2>/dev/null || true && \
    sleep 2 && \
    nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/fintax.log 2>&1 &"
echo "✅ 服务重启完成"

# 验证
echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "验证步骤："
echo "1. 访问: http://121.41.87.137:8000"
echo "2. 打开浏览器开发者工具（F12）"
echo "3. 检查Console标签是否有CORS错误"
echo "4. 验证码输入: 123456"
echo "5. 登录账号: admin / admin123"
echo "6. 应该进入'工作台'页面（不是'AI智问'）"
echo ""
echo "查看服务器日志："
echo "  ssh $ALIYUN_USER@$ALIYUN_HOST 'tail -f /tmp/fintax.log'"
echo ""
echo "检查服务状态："
echo "  ssh $ALIYUN_USER@$ALIYUN_HOST 'ps aux | grep uvicorn'"
echo ""
