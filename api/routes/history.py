"""Chat history endpoints — reuses app.py JSON file persistence."""
import json
import threading
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.auth import get_current_user
from pydantic import BaseModel, Field

router = APIRouter()

HISTORY_PATH = Path(__file__).resolve().parent.parent.parent / "query_history.json"
HISTORY_MAX = 100
_lock = threading.Lock()


class ReinvokeRequest(BaseModel):
    """Request model for re-invoking a query from history."""
    history_index: int = Field(..., ge=0, description="Index in history array")
    thinking_mode: str = Field(default="quick", description="Override thinking mode: quick|think|deep")


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
async def get_history(limit: int = 100, user: dict = Depends(get_current_user)):
    history = _load()
    return history[:limit]


@router.post("/chat/history")
async def save_history_entry(entry: dict, user: dict = Depends(get_current_user)):
    """Save history entry with enhanced schema supporting re-invocation.

    New fields (backward compatible):
    - conversation_history: list of message objects for multi-turn context
    - conversation_enabled: bool, whether multi-turn was enabled
    - conversation_depth: int, conversation depth setting
    - response_mode: str, detailed/standard/concise
    - thinking_mode: str, quick/think/deep
    - result: dict, full pipeline result including display_data
    """
    history = _load()

    # Ensure new fields have defaults for backward compatibility
    entry.setdefault("conversation_history", [])
    entry.setdefault("conversation_enabled", False)
    entry.setdefault("conversation_depth", 3)
    entry.setdefault("response_mode", "detailed")
    entry.setdefault("thinking_mode", "quick")
    entry.setdefault("result", {})
    entry.setdefault("company_id", "")

    history = [entry] + history
    _save(history[:HISTORY_MAX])
    return {"ok": True}


@router.delete("/chat/history")
async def delete_history(body: dict, user: dict = Depends(get_current_user)):
    ids = body.get("ids", [])
    history = _load()

    # Collect cache_keys from entries being deleted for cascade cleanup
    cache_keys_to_delete = []
    if not ids:
        # Deleting all — collect all cache_keys
        for h in history:
            ck = h.get("cache_key", "")
            if ck:
                cache_keys_to_delete.append(ck)
        _save([])
    else:
        id_set = set(ids)
        for i, h in enumerate(history):
            if i in id_set:
                ck = h.get("cache_key", "")
                if ck:
                    cache_keys_to_delete.append(ck)
        history = [h for i, h in enumerate(history) if i not in id_set]
        _save(history)

    # Cascade delete cache files (non-critical)
    if cache_keys_to_delete:
        try:
            from api.services.query_cache import delete_query_caches
            delete_query_caches(cache_keys_to_delete)
        except Exception:
            pass

    return {"ok": True}


@router.post("/chat/history/reinvoke")
async def reinvoke_from_history(req: ReinvokeRequest, user: dict = Depends(get_current_user)):
    """Re-invoke a query from history with specified thinking mode.

    Supports three modes:
    - quick: Return cached result + cached interpretation (instant, no LLM call)
    - think: Return cached result + trigger fresh interpretation
    - deep: Re-run full pipeline with conversation context (clears in-memory caches)

    Returns SSE stream in same format as /api/chat endpoint.
    """
    from api.auth import require_company_access
    from config.settings import QUERY_CACHE_ENABLED
    from api.services.query_cache import get_cached_query
    from mvp_pipeline import run_pipeline_stream
    from modules.display_formatter import build_display_data

    history = _load()
    if req.history_index >= len(history):
        return {"success": False, "error": "History index out of range"}

    entry = history[req.history_index]
    company_id = entry.get("company_id", "")
    query = entry.get("query", "")
    cache_key = entry.get("cache_key", "")
    conversation_history = entry.get("conversation_history", [])
    conversation_enabled = entry.get("conversation_enabled", False)
    conversation_depth = entry.get("conversation_depth", 3)
    response_mode = entry.get("response_mode", "detailed")
    route = entry.get("route", "financial_data")

    # Validate company access
    if company_id:
        require_company_access(user, company_id)

    thinking_mode = req.thinking_mode if req.thinking_mode in ("quick", "think", "deep") else "quick"

    def _reinvoke_generator():
        """SSE generator for re-invocation."""
        # --- Quick mode: return cached result directly ---
        if thinking_mode == "quick" and QUERY_CACHE_ENABLED and cache_key:
            cached = get_cached_query(company_id, query, response_mode)
            if cached:
                import copy
                result = copy.deepcopy(cached["result"])
                result["cache_hit"] = True
                result["cache_key"] = cache_key
                result["cached_interpretation"] = cached.get("interpretation", "")
                result["need_reinterpret"] = False
                result["response_mode"] = response_mode
                result["thinking_mode"] = thinking_mode
                stage_data = json.dumps({"route": route, "text": "历史记录重新运行（缓存命中）"}, ensure_ascii=False)
                yield f"event: stage\ndata: {stage_data}\n\n"
                data = json.dumps(result, ensure_ascii=False)
                yield f"event: done\ndata: {data}\n\n"
                return

        # --- Think mode: return cached result but request fresh interpretation ---
        if thinking_mode == "think" and QUERY_CACHE_ENABLED and cache_key:
            cached = get_cached_query(company_id, query, response_mode)
            if cached:
                import copy
                result = copy.deepcopy(cached["result"])
                result["cache_hit"] = True
                result["cache_key"] = cache_key
                result["cached_interpretation"] = ""
                result["need_reinterpret"] = True
                result["response_mode"] = response_mode
                result["thinking_mode"] = thinking_mode
                stage_data = json.dumps({"route": route, "text": "历史记录重新运行（思考模式）"}, ensure_ascii=False)
                yield f"event: stage\ndata: {stage_data}\n\n"
                data = json.dumps(result, ensure_ascii=False)
                yield f"event: done\ndata: {data}\n\n"
                return

        # --- Deep mode: clear caches and re-run full pipeline ---
        if thinking_mode == "deep":
            try:
                from modules.cache_manager import clear_cache
                clear_cache()
                print("[reinvoke] deep mode: cleared in-memory pipeline caches")
            except Exception:
                pass

        # --- Re-run pipeline with conversation context ---
        # Prepare conversation context for multi-turn queries
        conversation_context = None
        multi_turn_enabled = False
        if conversation_enabled and conversation_history:
            from modules.conversation_manager import prepare_conversation_context
            multi_turn_enabled = True
            conversation_context = prepare_conversation_context(
                conversation_history,
                max_turns=conversation_depth,
                token_budget=4000
            )

        # Resolve company name for query prefix
        from modules.db_utils import get_connection
        full_query = query
        if company_id:
            try:
                conn = get_connection()
                cur = conn.execute(
                    "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?",
                    (company_id,),
                )
                row = cur.fetchone()
                conn.close()
                if row:
                    full_query = f"{row[0]} {query}"
            except Exception:
                pass

        # Run pipeline
        for event in run_pipeline_stream(
            full_query,
            original_query=query,
            conversation_history=conversation_context,
            multi_turn_enabled=multi_turn_enabled
        ):
            etype = event.get("type", "")
            if etype == "stage":
                data = json.dumps({"route": event.get("route", ""), "text": event.get("text", "")}, ensure_ascii=False)
                yield f"event: stage\ndata: {data}\n\n"
            elif etype == "chunk":
                data = json.dumps({"text": event.get("text", "")}, ensure_ascii=False)
                yield f"event: chunk\ndata: {data}\n\n"
            elif etype == "done":
                result = event.get("result", {})
                route = result.get("route", "financial_data")
                if route not in ("tax_incentive", "regulation") and result.get("success"):
                    try:
                        display_data = build_display_data(result, query=query)
                        result["display_data"] = display_data
                        if display_data.get("empty_data_message"):
                            result["empty_data_message"] = display_data["empty_data_message"]
                    except Exception as e:
                        print(f"[reinvoke display_data] 构建失败: {e}")
                result["response_mode"] = response_mode
                result["thinking_mode"] = thinking_mode
                result["cache_hit"] = False
                result["need_reinterpret"] = False
                data = json.dumps(result, ensure_ascii=False)
                yield f"event: done\ndata: {data}\n\n"

    return StreamingResponse(
        _reinvoke_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
