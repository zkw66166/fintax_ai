fintax_ai阿里云部署极简版

服务器目录已定为 /var/www/fintax_ai 且代码与数据库已上传，我们将直接基于此路径进行环境配置、依赖安装、服务启动。

以下是针对 开发测试版 的最简部署步骤：

第一步：登录并进入项目目录

通过 SSH 登录服务器并切换到指定目录：
ssh root@121.41.87.137
密码: 166Tax@186

进入项目目录
cd /var/www/fintax_ai

第二步：检查目录结构与文件完整性

确认关键文件是否存在（特别是 requirements.txt, api/main.py, database/fintax_ai.db, frontend/dist）：
ls -la
应该看到: api/, database/, frontend/, requirements.txt 等

检查数据库文件
ls -lh database/fintax_ai.db
应显示约 12MB

检查前端构建文件 (如果本地已构建好)
ls frontend/dist/index.html

*注意：如果 frontend/dist 为空或不存在，请跳转至 [可选] 第四步 在服务器构建前端。*

第三步：安装 Python 依赖

在项目根目录下安装所需的 Python 库：
pip3 install -r requirements.txt
(若提示 pip3 未找到，请先执行 apt update && apt install -y python3-pip)

第四步：[可选] 服务器端构建前端
仅当您上传的代码中 frontend/dist 为空或缺失时执行此步。如果已有 dist 文件夹，请跳过。

安装 Node.js (如果服务器尚未安装)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

安装前端依赖并构建
cd frontend
npm install
npm run build
cd ..

确认构建成功
ls frontend/dist

第五步：验证数据库状态 (可选但推荐)

虽然数据库已上传，但建议快速验证一下连接是否正常，并确保指标已计算（避免前端图表空白）：
尝试导入并运行一次指标计算脚本 (确保数据就绪)
python3 database/calculate_metrics_v2.py
如果脚本报错说表不存在，说明数据库文件损坏或未正确上传；如果运行成功或提示“无新数据”，则正常。

第六步：启动开发服务

使用 uvicorn 启动 FastAPI 服务。
--host 0.0.0.0: 允许外部 IP 访问。
--port 8000: 使用 8000 端口。
--reload: 开启热重载（修改代码后自动重启，适合开发调试）。

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

成功标志：
终端输出类似：
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.

第七步：配置阿里云防火墙 (关键步骤)

如果不配置防火墙，外部无法访问 8000 端口。

登录 阿里云轻量应用服务器控制台。
点击实例 121.41.87.137 进入详情页。
点击左侧菜单 防火墙。
点击 添加规则：
    端口: 8000
    协议: TCP
    备注: Fintax Dev
点击确定。

第八步：访问验证

现在您可以在本地浏览器中访问：
👉 http://121.41.87.137:8000

前端页面：应直接显示 React 界面。
API 文档：访问 http://121.41.87.137:8000/docs 可测试接口。
测试账号：
  管理员: sys / sys123
  普通用户: user4 / 123456

💡 开发调试小贴士

保持运行：当前命令在前台运行，关闭 SSH 窗口服务会停止。
    若需后台运行（断开 SSH 不停止），请使用：
                nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > dev.log 2>&1 &
        
    查看日志：tail -f dev.log
    停止服务：pkill -f uvicorn

代码修改：由于开启了 --reload，您在本地修改代码并重新上传（如 scp）后，服务会自动重启生效，无需手动重启。

Hardcoded 配置：目前系统直接使用代码中的 API Key 和配置，符合您“暂不修改”的要求。