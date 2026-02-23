"""FastAPI entry point."""
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import chat, history, company, profile

# Ensure database is ready (reuse app.py logic)
from config.settings import DB_PATH

def ensure_db():
    if not Path(DB_PATH).exists():
        from database.init_db import init_database
        from database.seed_data import seed_reference_data
        from database.sample_data import insert_sample_data
        init_database()
        seed_reference_data()
        insert_sample_data()

ensure_db()

app = FastAPI(title="fintax_ai API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(profile.router, prefix="/api")

# Production: serve React build
dist_dir = PROJECT_ROOT / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")
