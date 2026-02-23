"""Company list endpoint."""
import sqlite3
from fastapi import APIRouter
from config.settings import DB_PATH

router = APIRouter()


@router.get("/companies")
async def list_companies():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT taxpayer_id, taxpayer_name, taxpayer_type FROM taxpayer_info ORDER BY taxpayer_name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
