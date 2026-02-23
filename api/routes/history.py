"""Chat history endpoints — reuses app.py JSON file persistence."""
import json
import threading
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "query_history.json"
HISTORY_MAX = 100
_lock = threading.Lock()


def _load() -> list:
    try:
        if HISTORY_PATH.exists():
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data[:HISTORY_MAX]
    except Exception:
        pass
    return []


def _save(history: list):
    with _lock:
        try:
            HISTORY_PATH.write_text(
                json.dumps(history[:HISTORY_MAX], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


@router.get("/chat/history")
async def get_history(limit: int = 100):
    history = _load()
    return history[:limit]


@router.post("/chat/history")
async def save_history_entry(entry: dict):
    history = _load()
    history = [entry] + history
    _save(history[:HISTORY_MAX])
    return {"ok": True}


@router.delete("/chat/history")
async def delete_history(body: dict):
    ids = body.get("ids", [])
    if not ids:
        _save([])
        return {"ok": True}
    history = _load()
    history = [h for i, h in enumerate(history) if i not in set(ids)]
    _save(history)
    return {"ok": True}
