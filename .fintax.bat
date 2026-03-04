后端：
cd D:\fintax_ai
uvicorn api.main:app --reload --port 8000

前端：
cd D:\fintax_ai\frontend
npm run dev
===
清除浏览器登录session（因24小时内记录登录token自动登录，无法测试验证码登录，因此需要清除）
localStorage.clear()
location.reload()

==
阿里云
putty
root
166Tax@186

cd /var/www/fintax_ai
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > dev.log 2>&1 &

退出：
pkill -f uvicorn
==
访问：

=====

  To run:
  # Terminal 1: FastAPI
pip install -r requirements.txt
cd D:\fintax_ai
uvicorn api.main:app --reload --port 8000

  # Terminal 2: React dev
cd D:\fintax_ai\frontend
npm run dev

  # Production (single server)
cd frontend && npm run build
uvicorn api.main:app --port 8000

  The original Gradio UI (python app.py on :7861) is preserved unchanged.