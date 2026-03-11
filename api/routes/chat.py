"""SSE streaming chat endpoint."""
import json
import re
import time
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from api.auth import get_current_user, require_company_access
from api.schemas import ChatRequest
from mvp_pipeline import run_pipeline_stream
from modules.display_formatter import build_display_data
from modules.db_utils import get_connection
from config.settings import QUERY_CACHE_ENABLED, QUERY_CACHE_ENABLED_L2
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
            from api.services.template_cache import get_template_cache, instantiate_sql, instantiate_cross_domain_sql
            from modules.db_utils import get_taxpayer_info

            try:
                taxpayer_type, accounting_standard = get_taxpayer_info(company_id)

                # 多域试探策略：由于多期间查询的域检测不稳定，尝试所有可能的域缓存键
                # 优先级：financial_statement > vat > eit > unknown
                print(f"[L2 Cache] Trying all domain cache keys for company_id={company_id}, type={taxpayer_type}, standard={accounting_standard}")

                l2_cached = None
                tried_domains = []

                # 1. 尝试财务报表域（最常见）
                l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="profit")
                tried_domains.append("profit")
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="balance_sheet")
                    tried_domains.append("balance_sheet")
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="cash_flow")
                    tried_domains.append("cash_flow")
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="account_balance")
                    tried_domains.append("account_balance")

                # 2. 尝试VAT域
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="vat")
                    tried_domains.append("vat")

                # 3. 尝试EIT域
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="eit")
                    tried_domains.append("eit")

                # 4. 尝试未知域（向后兼容）
                if not l2_cached:
                    l2_cached = get_template_cache(original_query, response_mode, taxpayer_type, accounting_standard, domain="")
                    tried_domains.append("unknown")

                # 如果命中，需要获取 entities_for_cache 用于概念管线参数重建
                entities_for_cache = {}
                if l2_cached:
                    hit_domain = l2_cached.get('domain', 'unknown')
                    print(f"[L2 Cache] Hit: query={original_query[:50]}, domain={hit_domain}, type={taxpayer_type}")

                    # 获取 entities 用于概念管线参数重建
                    try:
                        from modules.entity_preprocessor import detect_entities
                        from modules.db_utils import get_connection
                        conn = get_connection()
                        try:
                            entities_for_cache = detect_entities(original_query, conn)
                        finally:
                            conn.close()
                    except Exception as e:
                        print(f"[L2 Cache] Entity detection failed: {e}")
                else:
                    print(f"[L2 Cache] Miss after trying domains: {', '.join(tried_domains)}")

                if l2_cached:
                    # 跨域模板：实例化所有子域SQL并执行
                    if l2_cached.get('cache_domain') == 'cross_domain':
                        sub_templates = l2_cached.get('sub_templates', [])
                        pipeline_type = l2_cached.get('pipeline_type', '')
                        print(f"[L2 Cache] Cross-domain template found with {len(sub_templates)} subdomains, pipeline_type={pipeline_type}")

                        instantiated_subs = instantiate_cross_domain_sql(sub_templates, company_id)
                        print(f"[L2 Cache] Instantiated {len(instantiated_subs)} subdomain SQLs for company_id={company_id}")

                        # 执行每个子域SQL
                        sub_results = []
                        entities = {**l2_cached.get('intent', {}), 'taxpayer_id': company_id}

                        conn = get_connection()
                        try:
                            for i, sub in enumerate(instantiated_subs):
                                print(f"[L2 Cache] Executing subdomain {i}: {sub['domain']}")
                                try:
                                    # 概念管线：从 sub_templates 获取参数键列表和静态参数，从 entities_for_cache 重建动态参数值
                                    if pipeline_type == 'concept' and i < len(sub_templates):
                                        param_keys = sub_templates[i].get('param_keys', [])
                                        static_params = sub_templates[i].get('static_params', {})
                                        params = {'taxpayer_id': company_id}

                                        # 先加载静态参数（常量值）
                                        params.update(static_params)

                                        # 再重建动态参数（从 entities 推导）
                                        for key in param_keys:
                                            if key in params:
                                                continue  # 已在 static_params 中
                                            elif key == 'taxpayer_id':
                                                continue
                                            elif key == 'year':
                                                params['year'] = entities_for_cache.get('period_year')
                                            elif key == 'quarter':
                                                params['quarter'] = entities_for_cache.get('period_quarter')
                                            elif key == 'month':
                                                params['month'] = entities_for_cache.get('period_month')
                                            elif key.startswith('year_'):
                                                idx = int(key.split('_')[1]) - 1
                                                period_years = entities_for_cache.get('period_years', [])
                                                if idx < len(period_years):
                                                    params[key] = period_years[idx]
                                            elif key.startswith('month_'):
                                                idx = int(key.split('_')[1]) - 1
                                                period_months = entities_for_cache.get('period_months', [])
                                                if idx < len(period_months):
                                                    params[key] = period_months[idx]
                                            else:
                                                # 其他参数尝试从 entities 获取
                                                params[key] = entities_for_cache.get(key)

                                        print(f"[L2 Cache]   → params: {params}")
                                    else:
                                        # 非概念管线：只传 taxpayer_id
                                        params = {'taxpayer_id': company_id}

                                    rows = conn.execute(sub['sql'], params).fetchall()
                                    data = [dict(r) for r in rows]
                                    sub_results.append({
                                        'domain': sub['domain'],
                                        'sql': sub['sql'],
                                        'data': data
                                    })
                                    print(f"[L2 Cache]   → returned {len(data)} rows")
                                except Exception as e:
                                    print(f"[L2 Cache]   → SQL failed: {e}")
                                    sub_results.append({
                                        'domain': sub['domain'],
                                        'sql': sub['sql'],
                                        'data': [],
                                        'error': str(e)
                                    })
                        finally:
                            conn.close()

                        # 概念管线：使用 merge_concept_results 合并（保持与原始概念管线一致的输出格式）
                        if pipeline_type == 'concept':
                            from modules.concept_registry import merge_concept_results, detect_time_granularity

                            # 重建 concept_results 格式
                            concept_results_for_merge = []
                            for i, sr in enumerate(sub_results):
                                # 从保存的模板中恢复概念元数据
                                tmpl = sub_templates[i] if i < len(sub_templates) else {}
                                concept_results_for_merge.append({
                                    'name': tmpl.get('concept_name', sr['domain']),
                                    'label': tmpl.get('concept_label', sr['domain']),
                                    'data': sr.get('data', [])
                                })

                            # 优先使用保存的 time_granularity，回退到从查询文本重新检测
                            time_gran = l2_cached.get('time_granularity') or detect_time_granularity(original_query)
                            print(f"[L2 Cache] Concept pipeline merge: {len(concept_results_for_merge)} concepts, granularity={time_gran}")
                            merged_rows = merge_concept_results(concept_results_for_merge, time_gran or 'quarterly')

                            concept_names = [cr['label'] for cr in concept_results_for_merge]
                            year = entities.get('period_year', '')
                            gran_cn = {'quarterly': '各季度', 'monthly': '各月', 'yearly': '年度'}
                            summary = f"概念查询: {'、'.join(concept_names)} ({year}年{gran_cn.get(time_gran or 'quarterly', '')})"

                            result = {
                                "success": len(merged_rows) > 0,
                                "route": "financial_data",
                                "domain": "cross_domain",
                                "results": merged_rows,
                                "cross_domain_summary": summary,
                                "concept_pipeline": True,
                                "entities": entities,
                                "cache_hit": True,
                                "cache_source": "l2",
                                "need_reinterpret": True,
                                "response_mode": response_mode,
                                "thinking_mode": thinking_mode
                            }
                            print(f"[L2 Cache] Concept pipeline completed, returned {len(merged_rows)} rows")

                        # LLM 跨域管线：使用 merge_cross_domain_results 合并
                        else:
                            from modules.cross_domain_calculator import merge_cross_domain_results

                            operation = l2_cached.get('cross_domain_operation', 'list')
                            print(f"[L2 Cache] Merging cross-domain results: {len(sub_results)} subdomains, operation={operation}")
                            merged = merge_cross_domain_results(sub_results, operation, original_query)

                            result = {
                                "success": len(merged.get('merged_data', [])) > 0,
                                "route": "financial_data",
                                "domain": "cross_domain",
                                "results": merged.get('merged_data', []),
                                "cross_domain_summary": merged.get('summary'),
                                "cross_domain_operation": operation,
                                "sub_results": sub_results,
                                "entities": entities,
                                "cache_hit": True,
                                "cache_source": "l2",
                                "need_reinterpret": True,
                                "response_mode": response_mode,
                                "thinking_mode": thinking_mode
                            }

                        print(f"[L2 Cache] Cross-domain query completed, returned {len(result['results'])} rows")

                    # 单域模板：现有逻辑
                    else:
                        sql = instantiate_sql(l2_cached["sql_template"], company_id)
                        print(f"[L2 Cache] Instantiated SQL for company_id={company_id}:")
                        print(f"  SQL preview: {sql[:200]}...")

                        conn = get_connection()
                        try:
                            # 检测是否为概念管线单域查询（通过 pipeline_type 判断）
                            pipeline_type = l2_cached.get('pipeline_type', '')

                            if pipeline_type == 'concept':
                                # 概念管线：从 entities_for_cache 重建参数
                                params = {'taxpayer_id': company_id}

                                # 从 SQL 模板中提取参数占位符
                                param_pattern = r':(\w+)'
                                param_keys = re.findall(param_pattern, sql)

                                # 先加载静态参数（常量值，如 vat_item_type, time_range）
                                static_params = l2_cached.get('static_params', {})
                                params.update(static_params)

                                # 再重建动态参数（从 entities 推导）
                                for key in param_keys:
                                    if key in params:
                                        continue  # 已在 static_params 中
                                    elif key == 'taxpayer_id':
                                        continue
                                    elif key == 'year':
                                        params['year'] = entities_for_cache.get('period_year')
                                    elif key == 'quarter':
                                        params['quarter'] = entities_for_cache.get('period_quarter')
                                    elif key == 'month':
                                        params['month'] = entities_for_cache.get('period_month')
                                    elif key.startswith('year_'):
                                        idx = int(key.split('_')[1]) - 1
                                        period_years = entities_for_cache.get('period_years', [])
                                        if idx < len(period_years):
                                            params[key] = period_years[idx]
                                    elif key.startswith('month_'):
                                        idx = int(key.split('_')[1]) - 1
                                        period_months = entities_for_cache.get('period_months', [])
                                        if idx < len(period_months):
                                            params[key] = period_months[idx]
                                    else:
                                        # 其他参数尝试从 entities 获取
                                        params[key] = entities_for_cache.get(key)

                                print(f"[L2 Cache] Concept pipeline single-domain params: {params}")
                            else:
                                # 非概念管线：只传 taxpayer_id
                                params = {'taxpayer_id': company_id}

                            # 使用参数化查询执行SQL
                            rows = conn.execute(sql, params).fetchall()
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

                # 所有域都未命中，走完整pipeline

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
                from api.services.template_cache import save_template_cache, templatize_sql, templatize_cross_domain_sql
                from modules.db_utils import get_taxpayer_info

                print(f"[L2 Cache] Attempting to save template:")
                print(f"  - success: {result.get('success')}")
                print(f"  - route: {route}")
                print(f"  - company_id: {company_id}")

                try:
                    sql = result.get("sql")
                    domain = result.get("domain", "unknown")

                    # 概念管线：单域或跨域都保存
                    if result.get("concept_results"):
                        concept_results = result.get("concept_results", [])
                        print(f"[L2 Cache] Concept pipeline detected (domain={domain}), processing concept_results")
                        print(f"  - concept_results count: {len(concept_results)}")

                        # 过滤掉 computed 概念（sql=None）
                        converted_sub_results = []
                        skipped = 0
                        for cr in concept_results:
                            if cr.get('sql'):
                                converted_sub_results.append({
                                    'domain': cr.get('domain'),
                                    'sql': cr.get('sql'),
                                    'params': cr.get('params', {}),
                                    'data': cr.get('data', [])
                                })
                            else:
                                skipped += 1
                        print(f"  - Filtered SQL-based concepts: {len(converted_sub_results)} (skipped {skipped} computed concepts)")

                        if converted_sub_results:
                            sub_templates, success = templatize_cross_domain_sql(converted_sub_results, company_id)
                            if success and sub_templates:
                                # 保存概念元数据
                                sql_concept_idx = 0
                                for cr in concept_results:
                                    if cr.get('sql') and sql_concept_idx < len(sub_templates):
                                        sub_templates[sql_concept_idx]['concept_name'] = cr.get('name', '')
                                        sub_templates[sql_concept_idx]['concept_label'] = cr.get('label', '')
                                        sql_concept_idx += 1

                                # 检测时间粒度
                                from modules.concept_registry import detect_time_granularity
                                time_gran = detect_time_granularity(original_query, result.get("entities", {}))

                                print(f"  - All {len(sub_templates)} concepts templatized successfully")
                                taxpayer_type, accounting_standard = get_taxpayer_info(company_id)

                                # 检测是否为单域概念查询（所有概念来自同一个域）
                                unique_domains = set(st['domain'] for st in sub_templates)
                                effective_domain = domain  # 默认使用原始 domain
                                if len(unique_domains) == 1 and domain != 'cross_domain':
                                    # 单域概念查询：使用实际域名而不是 'cross_domain'
                                    effective_domain = list(unique_domains)[0]
                                    print(f"  - Single-domain concept query detected: {effective_domain}")

                                save_template_cache(
                                    original_query, response_mode, taxpayer_type,
                                    accounting_standard, result.get("entities", {}),
                                    None,
                                    effective_domain,  # 使用检测到的有效域
                                    sub_templates=sub_templates,
                                    cross_domain_operation='list',
                                    pipeline_type='concept',
                                    time_granularity=time_gran
                                )
                                print(f"[L2 Cache] Saved concept pipeline: {len(sub_templates)} concepts, domain={domain}, time_gran={time_gran}, type={taxpayer_type}, standard={accounting_standard}")
                            else:
                                print(f"[L2 Cache] Concept pipeline templatize failed")
                        else:
                            print(f"[L2 Cache] No SQL-based concepts to save")

                    # LLM 跨域查询：模板化所有子域SQL
                    elif domain == "cross_domain":
                        sub_results = result.get("sub_results", [])
                        if sub_results:
                            print(f"[L2 Cache] Cross-domain query detected, processing sub_results")
                            print(f"  - sub_results count: {len(sub_results)}")

                            sub_templates, success = templatize_cross_domain_sql(sub_results, company_id)

                            if success and sub_templates:
                                print(f"  - All {len(sub_templates)} subdomains templatized successfully")
                                for i, st in enumerate(sub_templates):
                                    print(f"  - subdomain {i}: {st['domain']}")
                                    print(f"    sql_template length: {len(st['sql_template'])}")

                                taxpayer_type, accounting_standard = get_taxpayer_info(company_id)
                                save_template_cache(
                                    original_query, response_mode, taxpayer_type,
                                    accounting_standard, result.get("entities", {}),
                                    None,  # 单域SQL为None
                                    domain,
                                    sub_templates=sub_templates,  # 传入子域模板列表
                                    cross_domain_operation=result.get("cross_domain_operation")
                                )
                                print(f"[L2 Cache] Saved cross-domain: {len(sub_templates)} subdomains, type={taxpayer_type}, standard={accounting_standard}")
                            else:
                                print(f"[L2 Cache] Cross-domain templatize failed - some subdomains missing {{{{TAXPAYER_ID}}}}")
                        else:
                            print(f"[L2 Cache] Skipping: cross-domain but no sub_results")

                    # 单域查询：现有逻辑
                    elif sql:
                        print(f"  - sql length: {len(sql)}")
                        print(f"  - sql preview: {sql[:200]}...")

                        template, success = templatize_sql(sql, company_id)
                        print(f"  - templatize_sql success: {success}")
                        if success:
                            print(f"  - template preview: {template[:200]}...")

                            taxpayer_type, accounting_standard = get_taxpayer_info(company_id)
                            print(f"  - taxpayer_type: {taxpayer_type}")
                            print(f"  - accounting_standard: {accounting_standard}")

                            save_template_cache(
                                original_query, response_mode, taxpayer_type,
                                accounting_standard, result.get("entities", {}),
                                template, domain
                            )
                            print(f"[L2 Cache] Saved: query={original_query[:50]}, type={taxpayer_type}")
                        else:
                            print(f"[L2 Cache] Templatize failed - no {{{{TAXPAYER_ID}}}} placeholder found")
                    else:
                        print(f"[L2 Cache] Skipping: domain={domain}, sql={'None' if sql is None else 'exists'}")

                except Exception as e:
                    print(f"[L2 Cache] Save error: {e}")
                    import traceback
                    traceback.print_exc()

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
