  To run:
  # Terminal 1: FastAPI
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

  # Terminal 2: React dev
cd frontend
npm run dev

  # Production (single server)
cd frontend && npm run build
uvicorn api.main:app --port 8000

  The original Gradio UI (python app.py on :7861) is preserved unchanged.