"""SSE streaming chat endpoint."""
import json
import time
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.auth import get_current_user, require_company_access
from api.schemas import ChatRequest
from mvp_pipeline import run_pipeline_stream
from modules.display_formatter import build_display_data
from modules.db_utils import get_connection
from config.settings import QUERY_CACHE_ENABLED, QUERY_CACHE_ENABLED_L2, TAXPAYER_TYPE_SMART_ADAPT
from api.services.query_cache import get_cached_query, save_query_cache
from api.services.query_path_logger import log_query_path
from api.services.template_cache import detect_cache_domain

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
    start_time = time.time()
    print(f"[chat] thinking_mode={thinking_mode}, response_mode={response_mode}, company_id={company_id}, multi_turn={multi_turn_enabled}, query={original_query[:50]}")

    # --- Cache check for quick / think modes ---
    if thinking_mode in ("quick", "think"):
        # L1 check
        if QUERY_CACHE_ENABLED:
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
                stage_data = json.dumps({"route": route, "text": "L1缓存命中"}, ensure_ascii=False)
                yield f"event: stage\ndata: {stage_data}\n\n"
                data = json.dumps(result, ensure_ascii=False)
                yield f"event: done\ndata: {data}\n\n"

                # 记录查询路径
                log_query_path(original_query, company_id, "l1", time.time() - start_time, thinking_mode, response_mode, True)
                return

        # L2 Cache check (template cache) - only if L1 missed
        if QUERY_CACHE_ENABLED_L2 and company_id:
            from api.services.template_cache import get_template_cache, instantiate_sql
            from modules.db_utils import get_taxpayer_info

            try:
                taxpayer_type, accounting_standard = get_taxpayer_info(company_id)

                # 检测查询的域类别（用于域感知缓存键）
                query_domain = ""
                try:
                    from modules.entity_preprocessor import preprocess_entities
                    entities_for_cache = preprocess_entities(original_query, company_id)
                    query_domain = entities_for_cache.get("domain_hint", "")
                except Exception:
                    pass  # 域检测失败不影响缓存查找

                print(f"[L2 Cache] Checking for company_id={company_id}, type={taxpayer_type}, standard={accounting_standard}, domain={query_domain}")
                l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain=query_domain)

                if l2_cached:
                    print(f"[L2 Cache] Hit: query={original_query[:50]}, type={taxpayer_type}")
                    sql = instantiate_sql(l2_cached["sql_template"], company_id)
                    print(f"[L2 Cache] Instantiated SQL for company_id={company_id}:")
                    print(f"  SQL preview: {sql[:200]}...")

                    conn = get_connection()
                    try:
                        rows = conn.execute(sql).fetchall()
                        rows = [dict(row) for row in rows]
                        print(f"[L2 Cache] SQL executed, returned {len(rows)} rows")
                        if len(rows) > 0:
                            print(f"[L2 Cache] First row: {rows[0]}")
                    except Exception as e:
                        print(f"[L2 Cache] SQL failed: {e}")
                        rows = []
                    finally:
                        conn.close()

                    result = {
                        "success": len(rows) > 0,
                        "route": "financial_data",
                        "domain": l2_cached.get("domain", "unknown"),
                        "sql": sql,
                        "results": rows,  # Fixed: use 'results' not 'data' to match pipeline format
                        "entities": l2_cached.get("intent", {}),
                        "cache_hit": True,
                        "cache_source": "l2",
                        "need_reinterpret": True,
                        "response_mode": response_mode,
                        "thinking_mode": thinking_mode
                    }

                    try:
                        display_data = build_display_data(result, query=original_query)
                        result["display_data"] = display_data
                    except Exception as e:
                        print(f"[L2 Cache] build_display_data failed: {e}")

                    stage_data = json.dumps({"route": "financial_data", "text": "L2缓存命中"}, ensure_ascii=False)
                    yield f"event: stage\ndata: {stage_data}\n\n"
                    data = json.dumps(result, ensure_ascii=False)
                    yield f"event: done\ndata: {data}\n\n"

                    # 记录查询路径
                    log_query_path(original_query, company_id, "l2", time.time() - start_time, thinking_mode, response_mode, True)
                    return

                # 域感知智能适配
                print(f"[L2 Cache] Miss for type={taxpayer_type}, domain={query_domain}, trying smart adaptation...")
                if TAXPAYER_TYPE_SMART_ADAPT:
                    from api.services.view_adapter import adapt_sql_for_type, adapt_sql_for_financial_statement
                    from api.services.template_cache import save_template_cache

                    cache_domain = detect_cache_domain(domain=query_domain)

                    if cache_domain == "financial_statement":
                        # 财务报表：按会计准则适配（与纳税人类型无关）
                        opposite_standard = "小企业会计准则" if accounting_standard == "企业会计准则" else "企业会计准则"
                        print(f"[L2 Adapt] Financial statement: trying opposite standard={opposite_standard}")
                        oc = get_template_cache(original_query, response_mode, taxpayer_type, opposite_standard, domain=query_domain)
                        if not oc:
                            # 也尝试另一种纳税人类型 + 对立会计准则
                            other_type = "小规模纳税人" if taxpayer_type == "一般纳税人" else "一般纳税人"
                            oc = get_template_cache(original_query, response_mode, other_type, opposite_standard, domain=query_domain)
                        if oc:
                            print(f"[L2 Adapt] Found cache with standard={oc.get('accounting_standard')}, adapting...")
                            ad = adapt_sql_for_financial_statement(oc["sql_template"], opposite_standard, accounting_standard)
                            if ad:
                                sql = instantiate_sql(ad, company_id)
                                conn = get_connection()
                                try:
                                    rows = [dict(r) for r in conn.execute(sql).fetchall()]
                                    conn.close()
                                    print(f"[L2 Adapt] FS adapted: {len(rows)} rows")
                                    if rows:
                                        save_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, oc.get("intent", {}), ad, oc.get("domain", "unknown"))
                                        result = {"success": True, "route": "financial_data", "domain": oc.get("domain"), "sql": sql, "results": rows, "entities": oc.get("intent", {}), "cache_hit": True, "cache_source": "l2_adapted", "need_reinterpret": True, "response_mode": response_mode, "thinking_mode": thinking_mode}
                                        try:
                                            result["display_data"] = build_display_data(result, query=original_query)
                                        except:
                                            pass
                                        yield f"event: stage\ndata: {json.dumps({'route': 'financial_data', 'text': 'L2缓存适配'}, ensure_ascii=False)}\n\n"
                                        yield f"event: done\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
                                        log_query_path(original_query, company_id, "l2_adapted", time.time() - start_time, thinking_mode, response_mode, True)
                                        return
                                except Exception as e:
                                    print(f"[L2 Adapt] FS SQL failed: {e}")
                                    conn.close()
                    else:
                        # 非财务报表域（VAT 不适配、EIT 无需适配）：保留旧版遍历逻辑
                        for ot, os in [("一般纳税人", "企业会计准则"), ("小规模纳税人", "小企业会计准则")]:
                            if ot == taxpayer_type:
                                continue
                            print(f"[L2 Adapt] Checking opposite type: {ot} with standard {os}")
                            oc = get_template_cache(original_query, response_mode, ot, os, domain=query_domain)
                            if not oc:
                                continue
                            print(f"[L2 Adapt] Found cache for type={ot}, attempting adaptation...")
                            ad = adapt_sql_for_type(oc["sql_template"], ot, taxpayer_type, os, accounting_standard)
                            if not ad:
                                continue
                            print(f"[L2 Adapt] {ot}→{taxpayer_type}")
                            sql = instantiate_sql(ad, company_id)
                            conn = get_connection()
                            try:
                                rows = [dict(r) for r in conn.execute(sql).fetchall()]
                                conn.close()
                                print(f"[L2 Adapt] SQL executed, returned {len(rows)} rows")
                                if rows:
                                    save_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, oc.get("intent", {}), ad, oc.get("domain", "unknown"))
                                    result = {"success": True, "route": "financial_data", "domain": oc.get("domain"), "sql": sql, "results": rows, "entities": oc.get("intent", {}), "cache_hit": True, "cache_source": "l2_adapted", "need_reinterpret": True, "response_mode": response_mode, "thinking_mode": thinking_mode}
                                    try:
                                        result["display_data"] = build_display_data(result, query=original_query)
                                    except:
                                        pass
                                    yield f"event: stage\ndata: {json.dumps({'route': 'financial_data', 'text': 'L2缓存适配'}, ensure_ascii=False)}\n\n"
                                    yield f"event: done\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
                                    log_query_path(original_query, company_id, "l2_adapted", time.time() - start_time, thinking_mode, response_mode, True)
                                    return
                                else:
                                    print(f"[L2 Adapt] SQL returned 0 rows, continuing")
                            except Exception as e:
                                print(f"[L2 Adapt] SQL execution failed: {e}")
                                conn.close()
            except Exception as e:
                print(f"[L2 Cache] Error: {e}")

        # In-memory pipeline cache removed (conflicted with L1/L2)
        # L1/L2 persistent cache is now the sole caching strategy

    # --- Deep mode: no in-memory cache to clear ---
    # In-memory pipeline cache removed (conflicted with L1/L2)

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

                # "本年"/"今年" 0 行结果友好提示
                results_data = result.get("results", [])
                if not results_data and company_id:
                    has_current_year_ref = any(kw in original_query for kw in ("本年", "今年"))
                    if has_current_year_ref:
                        try:
                            import datetime
                            cur_year = datetime.date.today().year
                            conn_check = get_connection()
                            row = conn_check.execute("""
                                SELECT MAX(period_year) FROM (
                                    SELECT period_year FROM fs_cash_flow_item WHERE taxpayer_id = ?
                                    UNION SELECT period_year FROM fs_income_statement_item WHERE taxpayer_id = ?
                                    UNION SELECT period_year FROM fs_balance_sheet_item WHERE taxpayer_id = ?
                                    UNION SELECT period_year FROM vat_return_item WHERE taxpayer_id = ?
                                )
                            """, (company_id, company_id, company_id, company_id)).fetchone()
                            conn_check.close()
                            if row and row[0] and row[0] < cur_year:
                                latest_year = row[0]
                                msg = f"该企业暂无{cur_year}年数据，最新数据截至{latest_year}年。请尝试指定具体年份查询。"
                                result["empty_data_message"] = msg
                                print(f"[chat] 本年查询无数据: {msg}")
                        except Exception as e:
                            print(f"[chat] 本年数据检查失败: {e}")
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

            # Save to L2 template cache
            if QUERY_CACHE_ENABLED_L2 and result.get("success") and route == "financial_data" and company_id:
                from api.services.template_cache import save_template_cache, templatize_sql
                from modules.db_utils import get_taxpayer_info

                try:
                    sql = result.get("sql", "")
                    if sql:
                        template, success = templatize_sql(sql, company_id)
                        if success:
                            taxpayer_type, accounting_standard = get_taxpayer_info(company_id)
                            save_template_cache(
                                original_query, response_mode, taxpayer_type,
                                accounting_standard, result.get("intent", {}),
                                template, result.get("domain", "unknown")
                            )
                            print(f"[L2 Cache] Saved: query={original_query[:50]}, type={taxpayer_type}")
                except Exception as e:
                    print(f"[L2 Cache] Save failed: {e}")

            result["cache_key"] = cache_key
            result["cache_hit"] = False
            result["need_reinterpret"] = False

            data = json.dumps(result, ensure_ascii=False)
            yield f"event: done\ndata: {data}\n\n"

            # 记录查询路径
            log_query_path(original_query, company_id, "pipeline", time.time() - start_time, thinking_mode, response_mode, result.get("success", False), result.get("error"))


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
