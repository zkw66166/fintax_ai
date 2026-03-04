"""SSE streaming chat endpoint."""
import json
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.auth import get_current_user, require_company_access
from api.schemas import ChatRequest
from mvp_pipeline import run_pipeline_stream
from modules.display_formatter import build_display_data
from modules.db_utils import get_connection
from config.settings import QUERY_CACHE_ENABLED
from api.services.query_cache import get_cached_query, save_query_cache

router = APIRouter()


def _resolve_company_name(company_id: str) -> str:
    """Look up taxpayer_name from taxpayer_info by taxpayer_id."""
    try:
        conn = get_connection()
        cur = conn.execute(
            "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?",
            (company_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


def _sse_generator(
    query: str,
    response_mode: str = "detailed",
    original_query: str = "",
    thinking_mode: str = "quick",
    company_id: str = "",
    conversation_history: Optional[List[Dict]] = None,
    multi_turn_enabled: bool = False,  # 新增：前端是否勾选多轮对话
):
    """Wrap run_pipeline_stream as SSE text/event-stream with 3-mode cache."""
    print(f"[chat] thinking_mode={thinking_mode}, response_mode={response_mode}, company_id={company_id}, multi_turn={multi_turn_enabled}, query={original_query[:50]}")

    # --- Cache check for quick / think modes ---
    if thinking_mode in ("quick", "think") and QUERY_CACHE_ENABLED:
        cached = get_cached_query(company_id, original_query, response_mode)
        if cached:
            # Deep-copy to avoid mutating the cached data
            import copy
            result = copy.deepcopy(cached["result"])
            result["cache_hit"] = True
            result["cache_key"] = cached["cache_key"]
            if thinking_mode == "quick" and cached.get("interpretation"):
                result["cached_interpretation"] = cached["interpretation"]
                result["need_reinterpret"] = False
            else:
                # think mode: return cached query result, but request fresh interpretation
                result["cached_interpretation"] = ""
                result["need_reinterpret"] = True
            result["response_mode"] = response_mode
            result["thinking_mode"] = thinking_mode
            route = result.get("route", "financial_data")
            stage_data = json.dumps({"route": route, "text": "缓存命中"}, ensure_ascii=False)
            yield f"event: stage\ndata: {stage_data}\n\n"
            data = json.dumps(result, ensure_ascii=False)
            yield f"event: done\ndata: {data}\n\n"
            return

    # --- Deep mode: flush in-memory pipeline caches so LLM re-generates everything ---
    if thinking_mode == "deep":
        try:
            from modules.cache_manager import clear_cache
            clear_cache()
            print("[chat] deep mode: cleared in-memory pipeline caches")
        except Exception:
            pass

    # --- Normal pipeline execution ---
    for event in run_pipeline_stream(
        query,
        original_query=original_query or query,
        conversation_history=conversation_history,
        multi_turn_enabled=multi_turn_enabled  # 传递给 pipeline
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
                    display_data = build_display_data(result, query=original_query)
                    result["display_data"] = display_data
                    # Copy empty_data_message to top level for frontend access
                    if display_data.get("empty_data_message"):
                        result["empty_data_message"] = display_data["empty_data_message"]
                except Exception as e:
                    print(f"[display_data] 构建失败: {e}")
            result["response_mode"] = response_mode

            # Save to persistent cache (strip transient keys before saving)
            cache_key = ""
            if QUERY_CACHE_ENABLED and result.get("success"):
                save_result = {k: v for k, v in result.items()
                               if k not in ("cache_hit", "cache_key", "cached_interpretation",
                                            "need_reinterpret", "thinking_mode")}
                cache_key = save_query_cache(
                    company_id, original_query, response_mode, route, save_result
                )
            result["cache_key"] = cache_key
            result["cache_hit"] = False
            result["need_reinterpret"] = False

            data = json.dumps(result, ensure_ascii=False)
            yield f"event: done\ndata: {data}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    from config.settings import CONVERSATION_ENABLED, CONVERSATION_BETA_USERS
    from modules.conversation_manager import prepare_conversation_context

    if req.company_id:
        require_company_access(user, req.company_id)

    # 功能开关检查
    conversation_context = None
    multi_turn_enabled = False  # 新增：前端多轮开关

    if req.conversation_history:
        if not CONVERSATION_ENABLED:
            # 检查是否为Beta用户
            if user['username'] not in CONVERSATION_BETA_USERS:
                req.conversation_history = None
        if req.conversation_history:
            multi_turn_enabled = True  # 用户勾选了多轮对话
            # 准备对话上下文
            conversation_context = prepare_conversation_context(
                req.conversation_history,
                max_turns=req.conversation_depth,
                token_budget=4000
            )

    query = req.query
    if req.company_id:
        name = _resolve_company_name(req.company_id)
        if name:
            query = f"{name} {query}"
    original_query = req.query
    thinking_mode = req.thinking_mode if req.thinking_mode in ("quick", "think", "deep") else "quick"
    print(f"[chat endpoint] raw thinking_mode={req.thinking_mode!r}, resolved={thinking_mode!r}")
    return StreamingResponse(
        _sse_generator(
            query, req.response_mode,
            original_query=original_query,
            thinking_mode=thinking_mode,
            company_id=req.company_id,
            conversation_history=conversation_context,
            multi_turn_enabled=multi_turn_enabled,  # 新增参数
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
