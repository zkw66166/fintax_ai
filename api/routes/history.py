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


def _derive_domain(entry: dict) -> str:
    """从历史记录条目派生 domain 字段

    仅 financial_data 路由有 domain，从 result.entities.domain_hint 提取
    """
    route = entry.get("route", "")

    # 非 financial_data 路由，domain 为空
    if route != "financial_data":
        return ""

    # 从 result.entities.domain_hint 提取
    result = entry.get("result", {})
    entities = result.get("entities", {})
    domain_hint = entities.get("domain_hint", "")

    return domain_hint


@router.get("/chat/history/counts")
async def get_history_counts(
    deduplicate: bool = True,
    user: dict = Depends(get_current_user)
):
    """获取各分类的历史记录数量（去重后）

    Returns:
        { "all": N, "financial_data": N, "tax_incentive": N, "regulation": N, "mixed_analysis": N }
        其中 mixed_analysis 包含 route 为 mixed_analysis 以及未分类（route为空/未知）的记录

    注意：统计逻辑与 /chat/history 端点一致，先按分类过滤再去重
    """
    history = _load()
    known_routes = {"financial_data", "tax_incentive", "regulation"}

    def dedup_with_priority(items):
        """去重：优先保留有明确route的记录"""
        if not deduplicate:
            return items

        seen = {}
        for item in items:
            query = item.get("query", "")
            route = item.get("route", "")

            if query not in seen:
                seen[query] = item
            else:
                existing = seen[query]
                existing_route = existing.get("route", "")

                # 优先级：有route > 无route；同等情况下保留最新
                if not existing_route and route:
                    seen[query] = item
                elif existing_route and route and item.get("timestamp", "") > existing.get("timestamp", ""):
                    seen[query] = item
                elif not existing_route and not route and item.get("timestamp", "") > existing.get("timestamp", ""):
                    seen[query] = item

        return list(seen.values())

    # 统计各分类（先过滤再去重，与实际显示逻辑一致）
    counts = {}

    # all: 全部记录去重
    counts["all"] = len(dedup_with_priority(history))

    # financial_data
    fd_items = [h for h in history if h.get("route") == "financial_data"]
    counts["financial_data"] = len(dedup_with_priority(fd_items))

    # tax_incentive
    ti_items = [h for h in history if h.get("route") == "tax_incentive"]
    counts["tax_incentive"] = len(dedup_with_priority(ti_items))

    # regulation
    reg_items = [h for h in history if h.get("route") == "regulation"]
    counts["regulation"] = len(dedup_with_priority(reg_items))

    # mixed_analysis: 未分类记录
    ma_items = [h for h in history if h.get("route", "") not in known_routes]
    counts["mixed_analysis"] = len(dedup_with_priority(ma_items))

    return counts


@router.get("/chat/history")
async def get_history(
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user_only: bool = False,
    deduplicate: bool = True,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user)
):
    """获取历史记录，支持分类过滤、搜索、去重和分页

    Args:
        limit: 返回记录数量上限（去重和分页前）
        category: 按 route 过滤（financial_data/tax_incentive/regulation/mixed_analysis）
        search: 关键词搜索（在 query 字段中搜索）
        user_only: 仅返回当前用户的记录
        deduplicate: 去重显示（按 query 分组，保留最新记录）
        page: 页码（从 1 开始）
        page_size: 每页条数
    """
    history = _load()
    user_id = user.get("id", 0)

    # 过滤：仅当前用户
    if user_only:
        history = [h for h in history if h.get("user_id") == user_id]

    # 过滤：按分类（category="all" 表示全部，不过滤）
    if category and category != "all":
        if category == "mixed_analysis":
            # 综合分析: mixed_analysis + 未分类（route为空/未知）
            known_routes = {"financial_data", "tax_incentive", "regulation"}
            history = [h for h in history if h.get("route", "") not in known_routes]
        else:
            history = [h for h in history if h.get("route") == category]

    # 过滤：关键词搜索
    if search:
        history = [h for h in history if search in h.get("query", "")]

    # 去重：按 query 分组，优先保留有明确 route 的记录
    if deduplicate:
        seen = {}
        for item in history:
            query = item.get("query", "")
            route = item.get("route", "")

            if query not in seen:
                seen[query] = item
            else:
                # 如果已存在记录，比较优先级
                existing = seen[query]
                existing_route = existing.get("route", "")

                # 优先级：有route > 无route；同等情况下保留最新
                if not existing_route and route:
                    # 现有记录无route，新记录有route，替换
                    seen[query] = item
                elif existing_route and route and item.get("timestamp", "") > existing.get("timestamp", ""):
                    # 都有route，保留最新
                    seen[query] = item
                elif not existing_route and not route and item.get("timestamp", "") > existing.get("timestamp", ""):
                    # 都无route，保留最新
                    seen[query] = item

        history = list(seen.values())
        # 按 timestamp 降序排序
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 应用 limit（去重后）
    history = history[:limit]

    # 分页
    total = len(history)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size
    items = history[start:end]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.post("/chat/history")
async def save_history_entry(entry: dict, user: dict = Depends(get_current_user)):
    """Save history entry with enhanced schema supporting re-invocation.

    New fields (backward compatible):
    - user_id: 创建者用户ID（自动填充）
    - domain: 域标签（自动派生）
    - conversation_history: list of message objects for multi-turn context
    - conversation_enabled: bool, whether multi-turn was enabled
    - conversation_depth: int, conversation depth setting
    - response_mode: str, detailed/standard/concise
    - thinking_mode: str, quick/think/deep
    - result: dict, full pipeline result including display_data

    Removed fields (debug only):
    - main_output: 与 result.answer 重复
    - entity_text: 调试字段
    - intent_text: 调试字段
    - sql_text: 调试字段
    """
    history = _load()

    # 自动填充 user_id
    entry["user_id"] = user.get("id", 0)

    # 自动派生 domain
    entry["domain"] = _derive_domain(entry)

    # Ensure new fields have defaults for backward compatibility
    entry.setdefault("conversation_history", [])
    entry.setdefault("conversation_enabled", False)
    entry.setdefault("conversation_depth", 3)
    entry.setdefault("response_mode", "detailed")
    entry.setdefault("thinking_mode", "quick")
    entry.setdefault("result", {})
    entry.setdefault("company_id", "")

    # 移除调试字段（精简 JSON）
    entry.pop("main_output", None)
    entry.pop("entity_text", None)
    entry.pop("intent_text", None)
    entry.pop("sql_text", None)

    history = [entry] + history
    _save(history[:HISTORY_MAX])
    return {"ok": True}


@router.delete("/chat/history")
async def delete_history(body: dict, user: dict = Depends(get_current_user)):
    """删除历史记录，带权限控制

    权限规则：
    - sys/admin 用户：可以删除所有记录
    - 其他用户：只能删除自己创建的记录

    Note: 缓存文件保留，以便其他用户或未来查询可以复用
    """
    ids = body.get("ids", [])
    history = _load()

    user_role = user.get("role", "")
    user_id = user.get("id", 0)

    if not ids:
        # 删除全部：仅 sys/admin 可以删除所有，其他用户只删除自己的
        if user_role in ("sys", "admin"):
            _save([])
        else:
            history = [h for h in history if h.get("user_id") != user_id]
            _save(history)
    else:
        # 删除指定记录
        id_set = set(ids)

        if user_role in ("sys", "admin"):
            # sys/admin 可以删除任何记录
            history = [h for i, h in enumerate(history) if i not in id_set]
        else:
            # 其他用户只能删除自己的记录
            history = [
                h for i, h in enumerate(history)
                if i not in id_set or h.get("user_id") != user_id
            ]

        _save(history)

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

        # --- Deep mode: no in-memory cache to clear ---
        # In-memory pipeline cache removed (conflicted with L1/L2)

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
