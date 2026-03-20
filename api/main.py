"""FastAPI entry point."""
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import chat, history, company, profile, profile_report, data_management, data_browser, auth, users, interpret, dashboard, cache_stats

# Ensure database is ready (reuse app.py logic)
from config.settings import DB_PATH

def ensure_db():
    if not Path(DB_PATH).exists():
        from database.init_db import init_database
        from database.seed_data import seed_reference_data
        from database.sample_data import insert_sample_data
        from database.migrate_users import migrate as migrate_users
        from database.migrate_permissions import migrate as migrate_permissions

        init_database()
        seed_reference_data()
        insert_sample_data()
        migrate_users()              # Auto-seed 2 initial users
        migrate_permissions()        # Auto-expand to 7 users + company access

    # profile_reports 表（无论DB是否新建都需要执行，IF NOT EXISTS 保证幂等）
    from database.migrate_profile_reports import migrate as migrate_profile_reports
    migrate_profile_reports()

ensure_db()

app = FastAPI(title="fintax_ai API", version="1.0.0")

# Dynamic CORS origins based on environment
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(profile_report.router, prefix="/api")  # Must be before profile to avoid route conflict
app.include_router(profile.router, prefix="/api")
app.include_router(data_management.router, prefix="/api")
app.include_router(data_browser.router, prefix="/api")
app.include_router(interpret.router, prefix="/api")
app.include_router(dashboard.router)
app.include_router(cache_stats.router, prefix="/api")

# Production: serve React build
dist_dir = PROJECT_ROOT / "frontend" / "dist"
if dist_dir.exists():
    # Serve static assets (JS/CSS) at /assets
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA catch-all: serve index.html for all non-API GET requests
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve actual files if they exist (favicon.ico, etc.)
        file_path = dist_dir / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(dist_dir / "index.html"))
