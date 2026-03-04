@echo off
REM 阿里云部署脚本 - fintax_ai (Windows版本)
REM 使用方法: deploy_to_aliyun.bat

setlocal enabledelayedexpansion

set ALIYUN_HOST=121.41.87.137
set ALIYUN_USER=root
set ALIYUN_PATH=/var/www/fintax_ai
set LOCAL_PATH=D:\fintax_ai

echo =========================================
echo fintax_ai 阿里云部署脚本 (Windows)
echo =========================================
echo.

REM 步骤1：检查本地构建
echo [1/6] 检查本地前端构建...
if not exist "%LOCAL_PATH%\frontend\dist" (
    echo ❌ 前端构建不存在，正在构建...
    cd /d "%LOCAL_PATH%\frontend"
    call npm run build
    if errorlevel 1 (
        echo ❌ 前端构建失败
        pause
        exit /b 1
    )
    echo ✅ 前端构建完成
) else (
    echo ✅ 前端构建已存在
)

REM 步骤2：提示SSH连接
echo.
echo [2/6] 准备SSH连接...
echo 请确保已安装Git Bash或WSL
echo 如果提示 "Host key verification failed"，请先运行:
echo   ssh-keygen -R %ALIYUN_HOST%
echo.
pause

REM 步骤3-6：调用Git Bash执行SSH/SCP命令
echo.
echo [3/6] 开始部署...
echo.

REM 生成临时脚本
set TEMP_SCRIPT=%TEMP%\deploy_fintax.sh
(
echo #!/bin/bash
echo set -e
echo BACKUP_TIME=$(date +%%Y%%m%%d_%%H%%M%%S^)
echo.
echo # 备份
echo echo "[备份服务器文件...]"
echo ssh %ALIYUN_USER%@%ALIYUN_HOST% "cd %ALIYUN_PATH% && cp api/main.py api/main.py.backup.$BACKUP_TIME 2>/dev/null || true && mv frontend/dist frontend/dist.backup.$BACKUP_TIME 2>/dev/null || true"
echo.
echo # 上传后端
echo echo "[上传后端文件...]"
echo scp "%LOCAL_PATH:\=/%/api/main.py" %ALIYUN_USER%@%ALIYUN_HOST%:%ALIYUN_PATH%/api/
echo.
echo # 上传前端
echo echo "[上传前端构建...]"
echo scp -r "%LOCAL_PATH:\=/%/frontend/dist" %ALIYUN_USER%@%ALIYUN_HOST%:%ALIYUN_PATH%/frontend/
echo.
echo # 重启服务
echo echo "[重启后端服务...]"
echo ssh %ALIYUN_USER%@%ALIYUN_HOST% "cd %ALIYUN_PATH% && export ALLOWED_ORIGINS='http://121.41.87.137,http://121.41.87.137:8000' && pkill -f 'uvicorn api.main:app' 2>/dev/null || true && sleep 2 && nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 ^> /tmp/fintax.log 2^>^&1 ^&"
echo.
echo echo "✅ 部署完成！"
) > "%TEMP_SCRIPT%"

REM 执行脚本
"C:\Program Files\Git\bin\bash.exe" "%TEMP_SCRIPT%"
if errorlevel 1 (
    echo.
    echo ❌ 部署失败
    echo.
    echo 可能的原因:
    echo 1. Git Bash未安装或路径不正确
    echo 2. SSH连接失败
    echo 3. 权限问题
    echo.
    echo 请尝试手动部署（参考 aliyun-deployment-diagnosis.md）
    pause
    exit /b 1
)

REM 清理临时文件
del "%TEMP_SCRIPT%"

echo.
echo =========================================
echo 部署完成！
echo =========================================
echo.
echo 验证步骤:
echo 1. 访问: http://121.41.87.137:8000
echo 2. 打开浏览器开发者工具（F12）
echo 3. 检查Console标签是否有CORS错误
echo 4. 验证码输入: 123456
echo 5. 登录账号: admin / admin123
echo 6. 应该进入'工作台'页面（不是'AI智问'）
echo.
echo 查看服务器日志:
echo   ssh %ALIYUN_USER%@%ALIYUN_HOST% "tail -f /tmp/fintax.log"
echo.
echo 检查服务状态:
echo   ssh %ALIYUN_USER%@%ALIYUN_HOST% "ps aux | grep uvicorn"
echo.
pause
