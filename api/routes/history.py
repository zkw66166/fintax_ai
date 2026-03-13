"""Chat history endpoints — reuses app.py JSON file persistence."""
import json
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
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


def _normalize_timestamp(ts_str: str) -> str:
    """规范化timestamp为ISO格式，用于排序

    支持格式：
    - ISO: "2024-03-12T15:30:00.000Z" (新格式，优先排序)
    - 中文: "下午3:30:00" (旧格式，视为历史数据，排在后面)

    返回可排序的字符串（ISO格式）
    """
    if not ts_str:
        return ""

    # 已经是ISO格式（新数据）
    if "T" in ts_str or "-" in ts_str[:10]:
        return ts_str

    # 中文格式：视为旧数据，使用1970-01-01的日期确保排在新数据后面
    try:
        # 解析"下午3:30:00"或"上午10:15:30"
        if "下午" in ts_str:
            time_part = ts_str.replace("下午", "").strip()
            hour, minute, second = map(int, time_part.split(":"))
            if hour != 12:
                hour += 12
        elif "上午" in ts_str:
            time_part = ts_str.replace("上午", "").strip()
            hour, minute, second = map(int, time_part.split(":"))
            if hour == 12:
                hour = 0
        else:
            return ts_str

        # 使用1970-01-01作为旧数据的日期
        dt = datetime(1970, 1, 1, hour, minute, second)
        return dt.isoformat()
    except:
        return ts_str


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


def _require_admin(user: dict):
    """检查用户是否为 sys/admin，否则抛出 403"""
    role = user.get("role", "")
    if role not in ("sys", "admin"):
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


def _resolve_usernames(user_ids: set) -> dict:
    """批量解析 user_id → username 映射"""
    if not user_ids:
        return {}
    try:
        from modules.db_utils import get_connection
        conn = get_connection()
        placeholders = ",".join("?" for _ in user_ids)
        rows = conn.execute(
            f"SELECT id, username FROM users WHERE id IN ({placeholders})",
            list(user_ids),
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


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
    # 过滤已删除的记录
    history = [h for h in history if not h.get("deleted", False)]
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


@router.get("/chat/history/deleted")
async def get_deleted_history(user: dict = Depends(get_current_user)):
    """获取已删除的历史记录列表（仅 sys/admin）

    返回所有 deleted=True 的记录，附带创建者/删除者用户名
    """
    _require_admin(user)
    history = _load()
    deleted = [h for h in history if h.get("deleted", False)]

    # 收集需要解析的 user_id
    uid_set = set()
    for h in deleted:
        if h.get("user_id"):
            uid_set.add(h["user_id"])
        if h.get("deleted_by"):
            uid_set.add(h["deleted_by"])
    username_map = _resolve_usernames(uid_set)

    # 构建返回数据
    items = []
    for h in deleted:
        items.append({
            "timestamp": h.get("timestamp", ""),
            "query": h.get("query", ""),
            "route": h.get("route", ""),
            "user_id": h.get("user_id"),
            "creator_name": username_map.get(h.get("user_id"), "unknown"),
            "deleted_by": h.get("deleted_by"),
            "deleter_name": username_map.get(h.get("deleted_by"), "unknown"),
            "deleted_at": h.get("deleted_at", ""),
            "protected": h.get("protected", False),
            "cache_key": h.get("cache_key", ""),
        })

    # 按删除时间降序
    items.sort(key=lambda x: x.get("deleted_at", ""), reverse=True)
    return {"items": items, "total": len(items)}


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
    # 过滤已删除的记录
    history = [h for h in history if not h.get("deleted", False)]
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

    # 为每条记录添加原始索引（文件中的位置，越小越新）
    for idx, item in enumerate(history):
        item['_original_index'] = idx

    # 先按原始索引排序（确保所有分类都是最新在前）
    # 文件中的顺序已经是最新在前，直接使用索引即可
    history.sort(key=lambda x: x.get('_original_index', 999999))

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
        # 去重后再次排序，确保顺序正确（按原始索引，越小越新）
        history.sort(key=lambda x: x.get('_original_index', 999999))

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


@router.post("/chat/history/restore")
async def restore_history(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """恢复已删除的历史记录（仅 sys/admin）

    请求: { "timestamps": [...] } 或 { "restore_all": true }
    恢复后标记 protected=True，普通用户无法再次删除
    """
    _require_admin(user)
    history = _load()
    timestamps = body.get("timestamps", [])
    restore_all = body.get("restore_all", False)
    user_id = user.get("id", 0)
    now = datetime.now().isoformat()
    restored = 0

    if restore_all:
        for h in history:
            if h.get("deleted", False):
                h["deleted"] = False
                h["protected"] = True
                h["restored_by"] = user_id
                h["restored_at"] = now
                restored += 1
    else:
        ts_set = set(timestamps)
        for h in history:
            if h.get("timestamp") in ts_set and h.get("deleted", False):
                h["deleted"] = False
                h["protected"] = True
                h["restored_by"] = user_id
                h["restored_at"] = now
                restored += 1

    _save(history)
    return {"ok": True, "restored": restored}


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

    # 保留调试字段以便后端日志可见
    # 注意：这会增加 JSON 文件大小，但对调试很有用

    history = [entry] + history
    _save(history[:HISTORY_MAX])
    return {"ok": True}


@router.delete("/chat/history/permanent")
async def permanent_delete_history(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """彻底删除历史记录（仅 sys/admin）

    从 query_history.json 中物理移除记录，同步删除 L1/L2 缓存文件
    此操作不可恢复
    """
    _require_admin(user)
    from api.services.query_cache import delete_query_caches
    from api.services.template_cache import delete_template_cache, find_l2_keys_for_entry

    timestamps = body.get("timestamps", [])
    if not timestamps:
        return {"ok": False, "error": "timestamps 不能为空"}

    history = _load()
    ts_set = set(timestamps)

    # 找到要删除的记录，收集缓存键
    l1_keys = []
    l2_keys = []
    to_remove = []

    for h in history:
        if h.get("timestamp") in ts_set:
            to_remove.append(h)
            ck = h.get("cache_key", "")
            if ck:
                l1_keys.append(ck)
            l2_keys.extend(find_l2_keys_for_entry(h))

    # 物理移除记录
    history = [h for h in history if h.get("timestamp") not in ts_set]
    _save(history)

    # 删除 L1 缓存
    if l1_keys:
        try:
            delete_query_caches(l1_keys)
        except Exception as e:
            print(f"[permanent_delete] L1 cache delete error: {e}")

    # 删除 L2 缓存
    for k in l2_keys:
        try:
            delete_template_cache(k)
        except Exception as e:
            print(f"[permanent_delete] L2 cache delete error: {e}")

    return {
        "ok": True,
        "removed": len(to_remove),
        "l1_deleted": len(l1_keys),
        "l2_deleted": len(l2_keys),
    }


@router.delete("/chat/history")
async def delete_history(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """软删除历史记录，带权限控制

    权限规则：
    - sys/admin 用户：可以删除所有记录
    - 其他用户：只能删除自己创建的记录（protected 记录除外）

    软删除：标记为已删除，不实际移除记录，保留缓存文件
    """
    timestamps = body.get("timestamps")
    history = _load()

    user_role = user.get("role", "")
    user_id = user.get("id", 0)
    now = datetime.now().isoformat()

    # 安全检查：必须提供 timestamps 且不能为空
    if not timestamps or not isinstance(timestamps, list) or len(timestamps) == 0:
        return {"ok": False, "error": "必须提供要删除的记录 timestamps"}

    # 删除指定记录：按 timestamp 查找并标记
    ts_set = set(timestamps)
    marked = 0
    for h in history:
        if h.get("timestamp") in ts_set:
            if h.get("deleted", False):
                continue
            if user_role in ("sys", "admin"):
                h["deleted"] = True
                h["deleted_by"] = user_id
                h["deleted_at"] = now
                marked += 1
            elif not h.get("protected", False) and h.get("user_id") == user_id:
                h["deleted"] = True
                h["deleted_by"] = user_id
                h["deleted_at"] = now
                marked += 1

    _save(history)
    return {"ok": True, "marked": marked}


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
