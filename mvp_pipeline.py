"""NL2SQL MVP 完整管线编排"""
import sqlite3
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import DB_PATH, MAX_ROWS, ROUTER_ENABLED
from modules.entity_preprocessor import detect_entities, detect_entities_with_context, normalize_query, get_scope_view
from modules.intent_parser import parse_intent
from modules.constraint_injector import inject_constraints
from modules.sql_writer import generate_sql
from modules.sql_auditor import audit_sql
from modules.cross_domain_calculator import detect_cross_domain_operation, merge_cross_domain_results
from modules.metric_calculator import detect_computed_metrics, get_metric_required_domains, compute_metric, METRIC_FORMULAS
from modules.concept_registry import resolve_concepts, detect_time_granularity, build_concept_sql, execute_computed_concept, merge_concept_results


def is_multi_period_query(entities: dict) -> bool:
    """检测是否为多期间查询（比较/趋势），应绕过概念管线单点查询。

    多期间查询特征：
    - 跨年: period_end_year != period_year
    - 跨季度: period_end_quarter 存在
    - 多年范围: period_years 长度 > 1
    - 多月枚举: period_months 长度 > 1
    - 月份范围: period_end_month != period_month (同年内)
    """
    # 跨年查询
    if entities.get('period_end_year') and entities.get('period_year'):
        if entities['period_end_year'] != entities['period_year']:
            return True

    # 跨季度查询（同年或跨年）
    if entities.get('period_end_quarter'):
        return True

    # 多年范围
    if entities.get('period_years') and len(entities['period_years']) > 1:
        return True

    # 多月枚举
    if entities.get('period_months') and len(entities['period_months']) > 1:
        return True

    # 同年内月份范围（排除单月查询）
    if entities.get('period_end_month') and entities.get('period_month'):
        if entities['period_end_month'] != entities['period_month']:
            return True

    return False


def _extract_requested_metrics(query: str, entities: dict) -> list:
    """从用户查询中提取所有请求的指标名称（中文）。

    使用简单的分隔符拆分 + 噪音词过滤。

    Returns:
        ['应纳税所得额', '实际缴纳的企业所得税额', '利润总额', '所得税税负率']
    """
    import re

    # Remove taxpayer name, dates, common noise words
    cleaned = query
    if entities.get('taxpayer_name'):
        cleaned = cleaned.replace(entities['taxpayer_name'], '')

    # Remove date patterns
    cleaned = re.sub(r'\d{4}年?', '', cleaned)
    cleaned = re.sub(r'第?[一二三四1-4]季度?', '', cleaned)
    cleaned = re.sub(r'\d{1,2}月', '', cleaned)

    # Split by common delimiters
    parts = re.split(r'[、，,和与及以及]', cleaned)

    # Filter noise words
    noise = {'分析', '查询', '情况', '数据', '多少', '趋势', '变化', '对比', '比较',
             '的', '和', '与', '及', '以及', '还有', '怎么样', '如何', '是多少', '是'}

    metrics = []
    for part in parts:
        part = part.strip()
        if part and part not in noise and len(part) > 1:
            metrics.append(part)

    return metrics


def _fuzzy_match_metric(requested: str, returned: str) -> bool:
    """模糊匹配两个指标名称。

    匹配规则:
    1. 完全相同
    2. 一个是另一个的子串
    3. 去除常见修饰词后相同（如"实际缴纳的"、"应"等）
    4. 核心词匹配（如"企业所得税"）

    Args:
        requested: 用户请求的指标名称
        returned: 概念管线返回的指标名称

    Returns:
        是否匹配
    """
    # 完全相同
    if requested == returned:
        return True

    # 子串匹配
    if requested in returned or returned in requested:
        return True

    # 去除常见修饰词后匹配
    modifiers = ['实际缴纳的', '实际', '应纳', '应', '本期', '本年', '累计', '合计']
    req_cleaned = requested
    ret_cleaned = returned

    for mod in modifiers:
        req_cleaned = req_cleaned.replace(mod, '')
        ret_cleaned = ret_cleaned.replace(mod, '')

    # 去除修饰词后的完全匹配
    if req_cleaned == ret_cleaned:
        return True

    # 去除修饰词后的子串匹配
    if req_cleaned in ret_cleaned or ret_cleaned in req_cleaned:
        return True

    # 核心词匹配：提取核心业务词（如"企业所得税"、"增值税"）
    # 如果两个指标都包含相同的核心词，且长度相近，则认为匹配
    core_words = ['企业所得税', '增值税', 'VAT', 'EIT', '利润', '资产', '负债', '现金流']
    for core in core_words:
        if core in requested and core in returned:
            # 核心词相同，且长度差异不超过5个字符，认为匹配
            if abs(len(requested) - len(returned)) <= 5:
                return True

    return False



def run_pipeline_stream(
    user_query: str,
    db_path: str = None,
    progress_callback=None,
    original_query: str = None,
    conversation_history=None,
    multi_turn_enabled: bool = False  # 新增：前端是否勾选多轮对话
):
    """流式管线：对 tax_incentive / regulation 路由逐步 yield 文本片段。

    Args:
        user_query: 用户查询
        db_path: 数据库路径
        progress_callback: 进度回调函数
        original_query: 原始查询（不含企业名前缀）
        conversation_history: 对话历史（可选，用于多轮对话）
        multi_turn_enabled: 前端是否勾选多轮对话

    Yields event dicts:
        {'type': 'stage', 'route': str, 'text': str}  — 阶段提示
        {'type': 'chunk', 'text': str}                 — 文本片段
        {'type': 'done', 'result': dict}               — 最终结果
    """
    db_path = db_path or str(DB_PATH)
    # 对 tax_incentive / regulation 路由使用原始查询（不含企业名前缀）
    raw_query = original_query or user_query

    # ⚠️ 关键：只有当用户勾选"多轮对话"时才进行混合分析检测
    # 如果未勾选，直接跳到意图路由，走原有三大路由逻辑
    if multi_turn_enabled and conversation_history and len(conversation_history) >= 2:
        from modules.mixed_analysis_detector import should_trigger_mixed_analysis

        should_trigger, reason = should_trigger_mixed_analysis(
            user_query=user_query,
            conversation_history=conversation_history,
            conversation_depth=len(conversation_history) // 2,  # 估算轮数
            multi_turn_enabled=multi_turn_enabled
        )

        if should_trigger:
            # 路由到混合分析
            yield {'type': 'stage', 'route': 'mixed_analysis', 'text': '检测到跨路由查询，启动综合分析模式...'}
            if progress_callback:
                progress_callback(0.10, "🎯 启动综合分析模式...")

            from modules.mixed_analysis_executor import execute_mixed_analysis_stream

            # 提取 taxpayer_id（如果有）
            taxpayer_id = None
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            from modules.entity_preprocessor import detect_entities_with_context
            entities = detect_entities_with_context(user_query, conn, conversation_history)
            taxpayer_id = entities.get('taxpayer_id')
            conn.close()

            for event in execute_mixed_analysis_stream(
                user_query=user_query,
                conversation_history=conversation_history,
                conversation_depth=len(conversation_history) // 2,
                taxpayer_id=taxpayer_id
            ):
                yield event

            if progress_callback:
                progress_callback(1.0, "✅ 综合分析完成")
            return  # 提前返回，不走后续路由

    # 意图路由（现有逻辑完全保持不变）
    route = 'financial_data'
    if ROUTER_ENABLED:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        from modules.intent_router import IntentRouter
        _router = IntentRouter()
        route = _router.classify(user_query, db_conn=conn)
        conn.close()
        print(f"\n[0] 意图路由(stream): {route}")

    if route == 'tax_incentive':
        yield {'type': 'stage', 'route': 'tax_incentive', 'text': '正在查询税收优惠政策...'}
        if progress_callback:
            progress_callback(0.10, "📚 正在查询税收优惠政策...")
        from modules.tax_incentive_query import TaxIncentiveQuery
        tiq = TaxIncentiveQuery()
        for chunk, is_done, result in tiq.search_stream(raw_query):
            if not is_done:
                yield {'type': 'chunk', 'text': chunk}
            else:
                result['user_query'] = raw_query
                result['entities'] = {}
                result['intent'] = {'domain': 'tax_incentive'}
                if progress_callback:
                    progress_callback(1.0, "✅ 税收优惠查询完成")
                yield {'type': 'done', 'result': result}
        return

    if route == 'regulation':
        yield {'type': 'stage', 'route': 'regulation', 'text': '正在查询法规知识库...'}
        if progress_callback:
            progress_callback(0.10, "🌐 正在查询法规知识库...")
        from modules.regulation_api import query_regulation_stream
        for chunk, is_done, result in query_regulation_stream(raw_query, progress_callback):
            if not is_done:
                yield {'type': 'chunk', 'text': chunk}
            else:
                result['user_query'] = raw_query
                result['entities'] = {}
                result['intent'] = {'domain': 'regulation'}
                if progress_callback:
                    progress_callback(1.0, "✅ 法规查询完成")
                yield {'type': 'done', 'result': result}
        return

    # financial_data：使用现有非流式管线
    result = run_pipeline(user_query, db_path=db_path, progress_callback=progress_callback, conversation_history=conversation_history)
    yield {'type': 'done', 'result': result}


def run_pipeline(user_query: str, db_path: str = None, progress_callback=None, conversation_history=None) -> dict:
    """
    完整NL2SQL管线：
    实体预处理 → 同义词标准化 → 阶段1(LLM→JSON) → 约束注入
    → 阶段2(LLM→SQL) → SQL审核 → 执行 → 日志

    Args:
        user_query: 用户查询
        db_path: 数据库路径
        progress_callback: 进度回调函数 callback(percentage, description)
    """
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    start_time = time.time()

    result = {
        'success': False, 'user_query': user_query,
        'clarification': None, 'sql': None,
        'results': None, 'error': None,
        'entities': None, 'intent': None, 'audit_violations': None,
    }

    try:
        # Step 0: 意图路由（在所有域检测之前）
        if ROUTER_ENABLED:
            from modules.intent_router import IntentRouter
            _router = IntentRouter()
            route = _router.classify(user_query, db_conn=conn)
            print(f"\n[0] 意图路由: {route}")

            if route == 'tax_incentive':
                if progress_callback:
                    progress_callback(0.10, "📚 正在查询税收优惠政策...")
                from modules.tax_incentive_query import TaxIncentiveQuery
                tiq = TaxIncentiveQuery()
                tax_result = tiq.search(user_query)
                tax_result['user_query'] = user_query
                tax_result['entities'] = {}
                tax_result['intent'] = {'domain': 'tax_incentive'}
                conn.close()
                if progress_callback:
                    progress_callback(1.0, "✅ 税收优惠查询完成")
                return tax_result

            if route == 'regulation':
                if progress_callback:
                    progress_callback(0.10, "🌐 正在查询法规知识库...")
                from modules.regulation_api import query_regulation
                reg_result = query_regulation(user_query, progress_callback)
                reg_result['user_query'] = user_query
                reg_result['entities'] = {}
                reg_result['intent'] = {'domain': 'regulation'}
                conn.close()
                if progress_callback:
                    progress_callback(1.0, "✅ 法规查询完成")
                return reg_result

            # route == 'financial_data' → 继续现有管线，零改动

        # Step 1: 实体预处理（支持多轮对话上下文）
        if progress_callback:
            progress_callback(0.05, "🔍 正在识别实体...")

        print(f"\n{'='*60}")
        print(f"用户问题: {user_query}")
        print(f"{'='*60}")

        # 使用上下文感知的实体检测（如果有对话历史）
        if conversation_history:
            entities = detect_entities_with_context(user_query, conn, conversation_history)
        else:
            entities = detect_entities(user_query, conn)
        result['entities'] = entities

        # 提取上下文信息用于空结果提示
        result['taxpayer_id'] = entities.get('taxpayer_id')
        result['taxpayer_name'] = entities.get('taxpayer_name')

        # 构建期间字符串
        period_year = entities.get('period_year')
        period_month = entities.get('period_month')
        period_quarter = entities.get('period_quarter')
        if period_year and period_month:
            result['period'] = f"{period_year}年{period_month}月"
        elif period_year and period_quarter:
            result['period'] = f"{period_year}年第{period_quarter}季度"
        elif period_year:
            result['period'] = f"{period_year}年"
        else:
            result['period'] = None

        domain_hint = entities.get('domain_hint')
        result['domain'] = domain_hint  # 初始域提示，后续可能被intent覆盖
        resolved_query = entities.get('resolved_query', user_query)
        print(f"\n[1] 实体识别: {json.dumps(entities, ensure_ascii=False)}")
        if resolved_query != user_query:
            print(f"    日期解析: {resolved_query}")

        # Step 2: 同义词标准化（域感知）
        if progress_callback:
            progress_callback(0.15, "📝 正在标准化查询...")

        # 根据域提示确定scope_view
        if domain_hint == 'eit':
            report_type = 'quarter' if entities.get('period_quarter') else 'annual'
            scope_view = get_scope_view(None, domain='eit', report_type=report_type)
        elif domain_hint == 'account_balance':
            scope_view = get_scope_view(None, domain='account_balance')
        elif domain_hint == 'balance_sheet':
            # 根据纳税人类型推断会计准则
            tp_type = entities.get('taxpayer_type')
            acct_std = None
            if tp_type == '小规模纳税人':
                acct_std = '小企业会计准则'
            # 也检查用户查询中是否明确提到准则
            if '小企业会计准则' in user_query or '小企业' in user_query:
                acct_std = '小企业会计准则'
            elif '企业会计准则' in user_query:
                acct_std = '企业会计准则'
            scope_view = get_scope_view(tp_type, domain='balance_sheet',
                                        accounting_standard=acct_std)
        elif domain_hint == 'profit':
            # 根据纳税人类型推断会计准则
            tp_type = entities.get('taxpayer_type')
            acct_std = None
            if tp_type == '小规模纳税人':
                acct_std = '小企业会计准则'
            if '小企业会计准则' in user_query or '小企业' in user_query:
                acct_std = '小企业会计准则'
            elif '企业会计准则' in user_query:
                acct_std = '企业会计准则'
            scope_view = get_scope_view(tp_type, domain='profit',
                                        accounting_standard=acct_std)
        elif domain_hint == 'cash_flow':
            # 根据纳税人类型推断会计准则
            tp_type = entities.get('taxpayer_type')
            acct_std = None
            if tp_type == '小规模纳税人':
                acct_std = '小企业会计准则'
            if '小企业会计准则' in user_query or '小企业' in user_query:
                acct_std = '小企业会计准则'
            elif '企业会计准则' in user_query:
                acct_std = '企业会计准则'
            scope_view = get_scope_view(tp_type, domain='cash_flow',
                                        accounting_standard=acct_std)
        elif domain_hint == 'cross_domain':
            # 跨域查询：使用第一个子域的scope_view做同义词标准化
            cross_list = entities.get('cross_domain_list', [])
            first_domain = cross_list[0] if cross_list else 'vat'
            tp_type = entities.get('taxpayer_type')
            scope_view = get_scope_view(tp_type, domain=first_domain)
        elif domain_hint == 'financial_metrics':
            scope_view = get_scope_view(None, domain='financial_metrics')
        elif domain_hint == 'invoice':
            # 发票域：根据方向选择视图
            direction = entities.get('invoice_direction', 'both')
            if direction == 'purchase':
                scope_view = 'vw_inv_spec_purchase'
            elif direction == 'sales':
                scope_view = 'vw_inv_spec_sales'
            else:
                scope_view = 'vw_inv_spec_purchase'  # 默认用进项视图做同义词标准化
        else:
            scope_view = get_scope_view(entities.get('taxpayer_type'))

        normalized, hits = normalize_query(
            resolved_query, scope_view, entities.get('taxpayer_type'), conn,
            domain=domain_hint
        )
        print(f"[2] 同义词标准化: {normalized}")
        if hits:
            print(f"    命中: {', '.join(h['phrase']+'→'+h['column_name'] for h in hits)}")

        # Step 2b: 提前检测计算指标（在意图解析前，避免被澄清拦截）
        # 注意：如果域已识别为financial_metrics，跳过G3路径，走标准NL2SQL查询
        early_metric_names = []
        if domain_hint != 'financial_metrics':
            early_metric_names = detect_computed_metrics(resolved_query)
        if early_metric_names:
            print(f"[2b] 提前检测到计算指标: {early_metric_names}")
            entities['has_computed_metric'] = True

        # Step 3: 阶段1 — 意图解析(LLM→JSON)
        if progress_callback:
            elapsed = int(time.time() - start_time)
            progress_callback(0.25, f"🤖 正在解析意图... (已用时{elapsed}秒)")

        print(f"[3] 调用LLM阶段1（意图解析）...")

        # 调用LLM（内存缓存已移除）
        t0 = time.time()
        intent = parse_intent(resolved_query, entities, hits, conversation_history=conversation_history)
        elapsed_ms = int((time.time() - t0) * 1000)
        print(f"    调用LLM ({elapsed_ms}ms)")

        result['intent'] = intent
        domain = intent.get('domain', domain_hint or 'vat')
        result['domain'] = domain  # 更新为intent解析后的域
        print(f"    domain={domain}, need_clarification={intent.get('need_clarification')}")

        # 检查是否需要澄清（计算指标查询跳过澄清）
        if intent.get('need_clarification') and not entities.get('has_computed_metric'):
            questions = intent.get('clarifying_questions', ['请补充更多信息'])
            result['clarification'] = '\n'.join(questions)
            print(f"\n[澄清] {result['clarification']}")
            _log_query(conn, user_query, normalized, entities, intent, None, False, result['clarification'])
            if progress_callback:
                progress_callback(1.0, "⚠️ 需要澄清")
            return result

        # Step 3b: 检测计算指标（G3）— 使用提前检测的结果
        metric_names = early_metric_names
        if metric_names:
            print(f"[3b] 检测到计算指标: {metric_names}")
            if progress_callback:
                progress_callback(0.50, "📊 正在计算指标...")
            metric_result = _run_metric_pipeline(
                conn, entities, intent, resolved_query, metric_names, progress_callback
            )
            result['success'] = metric_result.get('success', False)
            result['results'] = metric_result.get('results', [])
            result['metric_results'] = metric_result.get('metric_results', [])
            _log_query(conn, user_query, normalized, entities, intent, None,
                       result['success'], result.get('error'))
            if progress_callback:
                progress_callback(1.0, "✅ 指标计算完成")
            return result

        # Step 3b2: 概念时序查询（单概念+时间粒度即可触发，非跨域也走概念管线）
        # 注意：多期间比较查询（如"2024Q4与2025Q1"）应走标准管线，不走概念管线
        if domain != 'cross_domain':
            concepts = resolve_concepts(resolved_query, entities)
            time_gran = entities.get('time_granularity') or detect_time_granularity(resolved_query, entities)
            is_multi_period = is_multi_period_query(entities)
            if len(concepts) >= 1 and time_gran and not is_multi_period:
                # NEW: Extract all requested metrics
                requested_metrics = _extract_requested_metrics(resolved_query, entities)
                print(f"[3b2] 单概念时序管线: {[c['name'] for c in concepts]}, 粒度={time_gran}")
                print(f"      请求指标: {requested_metrics}")
                if progress_callback:
                    progress_callback(0.50, "📊 正在执行概念查询...")
                concept_result = _run_concept_pipeline(
                    conn, entities, concepts, time_gran, resolved_query
                )
                if concept_result.get('success'):
                    # NEW: Validate completeness
                    returned_metrics = set()
                    for r in concept_result.get('results', []):
                        # Extract metric name from result
                        if 'metric_name' in r:
                            returned_metrics.add(r['metric_name'])
                        elif 'concept_name' in r:
                            returned_metrics.add(r['concept_name'])
                        # Also check column names in result dict
                        for key in r.keys():
                            if key not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter'):
                                returned_metrics.add(key)

                    # Fuzzy match: check if requested metrics are covered
                    missing = []
                    for req in requested_metrics:
                        # Check if req matches any returned metric using fuzzy matching
                        if not any(_fuzzy_match_metric(req, ret) for ret in returned_metrics):
                            missing.append(req)

                    if missing:
                        print(f"      概念管线不完整，缺失: {missing}，回退标准NL2SQL管线")
                        # Fall through to standard pipeline
                    else:
                        print(f"      概念管线完整，返回结果")
                        result['success'] = True
                        result['results'] = concept_result.get('results', [])
                        result['cross_domain_summary'] = concept_result.get('cross_domain_summary')
                        result['concept_pipeline'] = True
                        _log_query(conn, user_query, normalized, entities, intent, None,
                                   True, None)
                        if progress_callback:
                            progress_callback(1.0, "✅ 概念查询完成")
                        return result
                else:
                    print(f"    概念管线失败，回退标准NL2SQL管线")
            elif is_multi_period:
                print(f"[3b2] 检测到多期间查询，跳过概念管线，走标准NL2SQL管线")

        # Step 3c: 跨域查询分支（G2）
        if domain == 'cross_domain':
            # 概念管线优先：尝试从查询中提取已注册概念
            # 注意：多期间比较查询（如"2024Q4与2025Q1"）应走标准管线，不走概念管线
            concepts = resolve_concepts(resolved_query, entities)
            time_gran = entities.get('time_granularity') or detect_time_granularity(resolved_query, entities)
            is_multi_period = is_multi_period_query(entities)
            if len(concepts) >= 1 and time_gran and not is_multi_period:
                # NEW: Extract all requested metrics
                requested_metrics = _extract_requested_metrics(resolved_query, entities)
                print(f"[3c] 概念管线: {[c['name'] for c in concepts]}, 粒度={time_gran}")
                print(f"     请求指标: {requested_metrics}")
                if progress_callback:
                    progress_callback(0.50, "📊 正在执行概念查询...")
                concept_result = _run_concept_pipeline(
                    conn, entities, concepts, time_gran, resolved_query
                )
                if concept_result.get('success'):
                    # NEW: Validate completeness
                    returned_metrics = set()
                    for r in concept_result.get('results', []):
                        # Extract metric name from result
                        if 'metric_name' in r:
                            returned_metrics.add(r['metric_name'])
                        elif 'concept_name' in r:
                            returned_metrics.add(r['concept_name'])
                        # Also check column names in result dict
                        for key in r.keys():
                            if key not in ('period', 'period_year', 'period_month', 'period_quarter', 'quarter'):
                                returned_metrics.add(key)

                    print(f"     返回指标: {list(returned_metrics)}")

                    # Fuzzy match: check if requested metrics are covered
                    missing = []
                    for req in requested_metrics:
                        # Check if req matches any returned metric using fuzzy matching
                        if not any(_fuzzy_match_metric(req, ret) for ret in returned_metrics):
                            missing.append(req)

                    if missing:
                        print(f"     缺失指标: {missing}")
                        print(f"     概念管线不完整，回退LLM跨域管线")
                        # Fall through to LLM cross-domain pipeline
                    else:
                        print(f"     概念管线完整，返回结果")
                        result['success'] = True
                        result['results'] = concept_result.get('results', [])
                        result['cross_domain_summary'] = concept_result.get('cross_domain_summary')
                        result['concept_pipeline'] = True
                        _log_query(conn, user_query, normalized, entities, intent, None,
                                   True, None)
                        if progress_callback:
                            progress_callback(1.0, "✅ 概念查询完成")
                        return result
                else:
                    print(f"    概念管线失败，回退LLM跨域管线")
            elif is_multi_period:
                print(f"[3c] 检测到多期间查询，跳过概念管线，走LLM跨域管线")

            print(f"[3c] 进入跨域查询管线...")
            if progress_callback:
                progress_callback(0.50, "🔀 正在执行跨域查询...")
            cross_result = _run_cross_domain_pipeline(
                conn, entities, intent, resolved_query, progress_callback, start_time, conversation_history
            )
            result['success'] = cross_result.get('success', False)
            result['results'] = cross_result.get('results', [])
            result['cross_domain_summary'] = cross_result.get('cross_domain_summary')
            result['cross_domain_operation'] = cross_result.get('cross_domain_operation')
            result['sub_results'] = cross_result.get('sub_results', [])
            if cross_result.get('error'):
                result['error'] = cross_result['error']
            _log_query(conn, user_query, normalized, entities, intent, None,
                       result['success'], result.get('error'))
            if progress_callback:
                progress_callback(1.0, "✅ 跨域查询完成")
            return result

        # Step 4: 约束注入
        if progress_callback:
            progress_callback(0.50, "⚙️ 正在注入约束...")

        constraints = inject_constraints(intent)
        print(f"[4] 约束注入: views={constraints['allowed_views']}, max_rows={constraints['max_rows']}")

        # Step 5: 阶段2 — SQL生成(LLM，域感知)
        if progress_callback:
            elapsed = int(time.time() - start_time)
            progress_callback(0.60, f"🤖 正在生成SQL... (已用时{elapsed}秒)")

        print(f"[5] 调用LLM阶段2（SQL生成, domain={domain}）...")

        # 调用LLM（内存缓存已移除）
        t0 = time.time()
        sql = generate_sql(constraints, domain=domain, conversation_history=conversation_history)
        elapsed_ms = int((time.time() - t0) * 1000)
        print(f"    调用LLM ({elapsed_ms}ms)")

        result['sql'] = sql
        print(f"    生成SQL:\n    {sql}")

        # Step 6: SQL审核
        if progress_callback:
            progress_callback(0.85, "✅ 正在审核SQL...")

        passed, violations = audit_sql(sql, constraints['allowed_views'], constraints['max_rows'], domain=domain)
        result['audit_violations'] = violations

        if not passed:
            print(f"[6] SQL审核失败: {violations}")
            # 重试一次
            print(f"    重试中...")
            if progress_callback:
                progress_callback(0.70, "🔄 SQL审核失败，正在重试...")

            feedback = "; ".join(violations)
            sql = generate_sql(constraints, retry_feedback=feedback, domain=domain, conversation_history=conversation_history)
            result['sql'] = sql
            print(f"    重试SQL:\n    {sql}")
            passed, violations = audit_sql(sql, constraints['allowed_views'], constraints['max_rows'], domain=domain)
            result['audit_violations'] = violations
            if not passed:
                result['error'] = f"SQL审核失败(重试后): {violations}"
                print(f"    重试仍失败: {violations}")
                _log_query(conn, user_query, normalized, entities, intent, sql, False, result['error'])
                if progress_callback:
                    progress_callback(1.0, "❌ SQL审核失败")
                return result

        print(f"[6] SQL审核通过")

        # Step 7: 执行SQL
        if progress_callback:
            progress_callback(0.95, "🗄️ 正在执行查询...")

        print(f"[7] 执行SQL...")
        params = _build_params(entities, intent)

        # 执行SQL（内存结果缓存已移除）
        try:
            rows = conn.execute(sql, params).fetchall()
            result['results'] = [dict(r) for r in rows]
            result['success'] = True
            elapsed = int((time.time() - start_time) * 1000)
            print(f"    返回 {len(rows)} 行 ({elapsed}ms)")

            if progress_callback:
                progress_callback(1.0, "✅ 查询完成")

            for i, row in enumerate(result['results'][:5]):
                print(f"    [{i+1}] {dict(row)}")
            if len(result['results']) > 5:
                print(f"    ... 共 {len(result['results'])} 行")
        except Exception as e:
            # 执行失败，重试一次（将错误信息反馈给LLM）
            exec_error = str(e)
            print(f"    执行失败: {exec_error}, 重试中...")
            retry_feedback = f"SQL执行报错: {exec_error}。请修正SQL。注意：SQLite不支持RIGHT JOIN和FULL OUTER JOIN，请改用LEFT JOIN或UNION ALL。"
            try:
                sql = generate_sql(constraints, retry_feedback=retry_feedback, domain=domain, conversation_history=conversation_history)
                result['sql'] = sql
                print(f"    重试SQL:\n    {sql}")
                passed, violations = audit_sql(sql, constraints['allowed_views'], constraints['max_rows'], domain=domain)
                if not passed:
                    result['error'] = f"SQL执行失败(重试审核不通过): {exec_error}"
                    print(f"    重试审核失败: {violations}")
                else:
                    rows = conn.execute(sql, params).fetchall()
                    result['results'] = [dict(r) for r in rows]
                    result['success'] = True
                    elapsed = int((time.time() - start_time) * 1000)
                    print(f"    重试成功，返回 {len(rows)} 行 ({elapsed}ms)")
                    for i, row in enumerate(result['results'][:5]):
                        print(f"    [{i+1}] {dict(row)}")
                    if len(result['results']) > 5:
                        print(f"    ... 共 {len(result['results'])} 行")
            except Exception as e2:
                result['error'] = f"SQL执行失败: {exec_error}"
                print(f"    重试仍失败: {e2}")
            if not result.get('success'):
                if not result.get('error'):
                    result['error'] = f"SQL执行失败: {exec_error}"
                if progress_callback:
                    progress_callback(1.0, "❌ 执行失败")

        _log_query(conn, user_query, normalized, entities, intent, sql,
                   result['success'], result.get('error'))

    except Exception as e:
        result['error'] = str(e)
        print(f"\n[错误] {e}")
    finally:
        conn.close()

    return result


def _generate_subdomain_sql(sd, sub_constraints, conversation_history=None):
    """子域SQL生成+审核（可在线程中并行执行，不涉及DB操作）。

    Args:
        sd: 子域名称
        sub_constraints: 子域约束
        conversation_history: 对话历史（可选）

    Returns:
        dict: {'domain': sd, 'sql': str} 或 {'domain': sd, 'error': str}
    """
    t0 = time.time()

    # 调用LLM（内存缓存已移除）
    try:
        sql = generate_sql(sub_constraints, domain=sd, conversation_history=conversation_history)
    except Exception as e:
        print(f"    [{sd}] SQL生成失败: {e}")
        return {'domain': sd, 'error': str(e)}
    elapsed_ms = int((time.time() - t0) * 1000)
    print(f"    [{sd}] SQL生成 ({elapsed_ms}ms): {sql[:80]}...")

    # 审核
    passed, violations = audit_sql(sql, sub_constraints['allowed_views'],
                                   sub_constraints['max_rows'], domain=sd)
    if not passed:
        print(f"    [{sd}] 审核失败: {violations}, 重试...")
        feedback = "; ".join(violations)
        try:
            sql = generate_sql(sub_constraints, retry_feedback=feedback, domain=sd, conversation_history=conversation_history)
        except Exception as e:
            return {'domain': sd, 'error': f'SQL重试失败: {e}'}
        passed, violations = audit_sql(sql, sub_constraints['allowed_views'],
                                       sub_constraints['max_rows'], domain=sd)
        if not passed:
            print(f"    [{sd}] 重试仍失败: {violations}")
            return {'domain': sd, 'error': f'审核失败: {violations}'}

    return {'domain': sd, 'sql': sql, 'constraints': sub_constraints}


def _run_cross_domain_pipeline(conn, entities, intent, resolved_query,
                                progress_callback=None, start_time=None, conversation_history=None) -> dict:
    """跨域查询管线：拆分为子域独立执行，然后Python端合并/计算。

    Args:
        conn: 数据库连接
        entities: 实体字典
        intent: 意图字典
        resolved_query: 解析后的查询
        progress_callback: 进度回调函数
        start_time: 开始时间
        conversation_history: 对话历史（可选）

    优化：Phase 2使用ThreadPoolExecutor并行执行LLM调用。
    """
    from modules.schema_catalog import DOMAIN_VIEWS, VIEW_COLUMNS

    cross_list = intent.get('cross_domain_list', entities.get('cross_domain_list', []))
    if not cross_list:
        return {'success': False, 'error': '跨域查询未检测到子域列表'}

    operation = detect_cross_domain_operation(resolved_query)
    print(f"    跨域操作类型: {operation}, 子域: {cross_list}")

    # 获取原始intent中的metrics列表
    orig_metrics = []
    if intent.get('select') and isinstance(intent['select'], dict):
        orig_metrics = intent['select'].get('metrics', [])
    elif isinstance(intent.get('metrics'), list):
        orig_metrics = intent['metrics']
    print(f"    [跨域] 原始metrics: {orig_metrics}")

    # === Phase 1: 串行构建所有子域intent和约束（快，无LLM） ===
    subdomain_tasks = []  # [(sd, sub_intent, sub_constraints)]
    for sd in cross_list:
        sub_intent = {
            'domain': sd,
            'filters': intent.get('filters', {}),
        }

        # 设置scope
        scope_key = f'{sd}_scope'
        if intent.get(scope_key):
            sub_intent[scope_key] = intent[scope_key]
        else:
            tp_type = entities.get('taxpayer_type')
            acct_std = None
            if tp_type == '小规模纳税人':
                acct_std = '小企业会计准则'
            view = get_scope_view(tp_type, domain=sd, accounting_standard=acct_std)
            if view:
                sub_intent[scope_key] = {'views': [view]}

        # 过滤出属于该子域的metrics
        sd_views = DOMAIN_VIEWS.get(sd, [])
        sd_columns = set()
        for v in sd_views:
            sd_columns.update(VIEW_COLUMNS.get(v, []))

        print(f"    [{sd}] 子域列: {list(sd_columns)[:10]}...")  # Show first 10 columns

        if orig_metrics:
            # Special handling for financial_metrics domain
            if sd == 'financial_metrics':
                # Financial metrics are stored as metric_name values, not physical columns
                # Accept Chinese metric names (含"率"的指标) and pass them to LLM
                filtered_metrics = []
                for m in orig_metrics:
                    # Accept if:
                    # 1. Contains "率" (tax burden rates, profit margins, turnover rates)
                    # 2. Is English abbreviation (ROE, ROA, EPS)
                    # 3. Is a physical column (fallback)
                    if '率' in m or m in ['ROE', 'ROA', 'EPS', 'EBIT', 'EBITDA'] or m in sd_columns:
                        filtered_metrics.append(m)
                if filtered_metrics:
                    print(f"    [financial_metrics] 识别到财务指标: {filtered_metrics}")
            else:
                # Standard filtering for physical column-based domains
                filtered_metrics = [m for m in orig_metrics if m in sd_columns]

            print(f"    [{sd}] 过滤后metrics: {filtered_metrics}")
            if filtered_metrics:
                sub_intent['select'] = {'metrics': filtered_metrics}
            else:
                # 没有原始metrics匹配该子域的列
                # 保留原始metrics作为提示，但标记为"用户意图参考"
                # LLM应从allowed_columns中选择与这些意图相关的所有列
                unmatched = [m for m in orig_metrics if m not in sd_columns]
                print(f"    [{sd}] 未匹配的metrics: {unmatched}")
                print(f"    [{sd}] 传递用户意图参考 (orig_metrics={len(orig_metrics)}个)")
                sub_intent['select'] = {
                    'metrics': [],
                    'user_intent_metrics': orig_metrics  # 新增：用户意图参考
                }
        else:
            sub_intent['select'] = intent.get('select', {})

        if intent.get('cross_domain_list'):
            sub_intent['cross_domain_list'] = intent['cross_domain_list']

        sub_constraints = inject_constraints(sub_intent)
        print(f"    [{sd}] views={sub_constraints['allowed_views']}")
        subdomain_tasks.append((sd, sub_intent, sub_constraints))

    # === Phase 2: 并行执行LLM SQL生成+审核 ===
    print(f"\n    并行生成SQL ({len(subdomain_tasks)}个子域)...")
    t_parallel = time.time()
    sql_results = {}  # {sd: {'sql': ..., 'constraints': ...} or {'error': ...}}

    with ThreadPoolExecutor(max_workers=len(subdomain_tasks)) as executor:
        futures = {
            executor.submit(_generate_subdomain_sql, sd, sc): sd
            for sd, _, sc in subdomain_tasks
        }
        for future in as_completed(futures):
            sd = futures[future]
            try:
                sql_results[sd] = future.result()
            except Exception as e:
                sql_results[sd] = {'domain': sd, 'error': str(e)}

    elapsed_parallel = int((time.time() - t_parallel) * 1000)
    print(f"    并行SQL生成完成 ({elapsed_parallel}ms)")

    # === Phase 3: 串行执行SQL查询（主线程，避免SQLite多线程问题） ===
    sub_results = []
    for sd, sub_intent, sub_constraints in subdomain_tasks:
        sr = sql_results.get(sd, {})
        if sr.get('error'):
            sub_results.append({'domain': sd, 'data': [], 'error': sr['error']})
            continue

        sql = sr['sql']
        params = _build_params(entities, sub_intent)
        try:
            rows = conn.execute(sql, params).fetchall()
            data = [dict(r) for r in rows]
            print(f"    [{sd}] 返回 {len(data)} 行")
            sub_results.append({'domain': sd, 'data': data, 'sql': sql})
        except Exception as e:
            # 执行失败，重试一次（需要LLM调用，串行执行）
            exec_error = str(e)
            print(f"    [{sd}] 执行失败: {exec_error}, 重试...")
            retry_fb = f"SQL执行报错: {exec_error}。请修正。SQLite不支持RIGHT JOIN和FULL OUTER JOIN，改用LEFT JOIN或UNION ALL。"
            try:
                sql = generate_sql(sub_constraints, retry_feedback=retry_fb, domain=sd, conversation_history=conversation_history)
                passed2, v2 = audit_sql(sql, sub_constraints['allowed_views'],
                                        sub_constraints['max_rows'], domain=sd)
                if passed2:
                    rows = conn.execute(sql, params).fetchall()
                    data = [dict(r) for r in rows]
                    print(f"    [{sd}] 重试成功，返回 {len(data)} 行")
                    sub_results.append({'domain': sd, 'data': data, 'sql': sql})
                else:
                    print(f"    [{sd}] 重试审核失败: {v2}")
                    sub_results.append({'domain': sd, 'data': [], 'error': exec_error, 'sql': sql})
            except Exception as e2:
                print(f"    [{sd}] 重试仍失败: {e2}")
                sub_results.append({'domain': sd, 'data': [], 'error': exec_error, 'sql': sql})

    # 合并结果
    merged = merge_cross_domain_results(sub_results, operation, resolved_query)
    print(f"\n    跨域合并: {merged.get('summary')}")

    cross_result = {
        'success': True,
        'results': merged.get('merged_data', []),
        'cross_domain_summary': merged.get('summary'),
        'cross_domain_operation': operation,
        'sub_results': sub_results,
    }

    return cross_result


def _run_metric_pipeline(conn, entities, intent, resolved_query, metric_names,
                          progress_callback=None) -> dict:
    """计算指标管线：确定性SQL构建 + Python端公式计算。

    不依赖LLM生成SQL，直接根据METRIC_FORMULAS中的sources定义构建SQL。
    """
    results = []
    for metric_name in metric_names:
        metric_def = METRIC_FORMULAS.get(metric_name, {})
        if 'alias' in metric_def:
            metric_name = metric_def['alias']
            metric_def = METRIC_FORMULAS[metric_name]

        print(f"\n    计算指标: {metric_def.get('label', metric_name)}")
        source_data = {}

        for var_name, src in metric_def.get('sources', {}).items():
            domain = src['domain']
            tp_type = entities.get('taxpayer_type')
            acct_std = None
            if tp_type == '小规模纳税人':
                acct_std = '小企业会计准则'

            view = get_scope_view(tp_type, domain=domain, accounting_standard=acct_std)
            if not view:
                print(f"    [{var_name}] 无法确定视图")
                source_data[var_name] = None
                continue

            # 构建确定性SQL
            if 'expression' in src:
                columns = src.get('columns', [])
                select_cols = ', '.join(columns)
            else:
                column = src.get('column')
                select_cols = column
                columns = [column]

            # 构建WHERE条件
            where_parts = []
            params = {}
            if entities.get('taxpayer_id'):
                where_parts.append('taxpayer_id = :taxpayer_id')
                params['taxpayer_id'] = entities['taxpayer_id']
            if entities.get('period_year'):
                where_parts.append('period_year = :year')
                params['year'] = entities['period_year']
            if entities.get('period_month'):
                where_parts.append('period_month = :month')
                params['month'] = entities['period_month']

            # 利润表/现金流量表需要time_range过滤
            time_range = src.get('time_range')
            if domain in ('profit', 'cash_flow') and time_range:
                where_parts.append('time_range = :time_range')
                params['time_range'] = time_range
            elif domain in ('profit', 'cash_flow') and not time_range:
                # 默认取"本期"
                where_parts.append('time_range = :time_range')
                params['time_range'] = '本期'

            where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
            sql = f"SELECT {select_cols} FROM {view} WHERE {where_clause} LIMIT 1"
            print(f"    [{var_name}] SQL: {sql}")
            print(f"    [{var_name}] params: {params}")

            try:
                rows = conn.execute(sql, params).fetchall()
                if rows:
                    row = dict(rows[0])
                    if 'expression' in src:
                        local_vars = {c: row.get(c, 0) or 0 for c in columns}
                        source_data[var_name] = eval(src['expression'],
                                                     {"__builtins__": {}}, local_vars)
                    else:
                        source_data[var_name] = row.get(src['column'], 0) or 0
                else:
                    print(f"    [{var_name}] 查询返回0行")
                    source_data[var_name] = None
            except Exception as e:
                print(f"    [{var_name}] 查询失败: {e}")
                source_data[var_name] = None

        # 计算指标
        metric_result = compute_metric(metric_name, source_data)
        results.append(metric_result)
        print(f"    {metric_result['label']} = {metric_result['value']}{metric_result['unit']}")

    return {
        'success': True,
        'results': results,
        'metric_results': results,
    }


def _run_concept_pipeline(conn, entities, concepts, time_granularity,
                           resolved_query) -> dict:
    """概念驱动的确定性跨域管线：无LLM参与。

    Args:
        conn: SQLite连接
        entities: detect_entities() 输出
        concepts: resolve_concepts() 输出
        time_granularity: 'quarterly' | 'monthly' | 'yearly'
        resolved_query: 日期解析后的查询文本

    Returns:
        与现有管线兼容的 result dict
    """
    concept_results = []

    for concept in concepts:
        cdef = concept['def']
        name = concept['name']
        label = cdef['label']
        print(f"    [concept] {name} → {cdef['domain']}.{cdef.get('column', 'computed')}")

        if cdef.get('type') == 'computed':
            data = execute_computed_concept(conn, cdef, entities, time_granularity)
        else:
            sql, params = build_concept_sql(cdef, entities, time_granularity)
            if sql is None:
                print(f"    [concept] {name}: SQL构建失败")
                concept_results.append({'name': name, 'label': label, 'data': []})
                continue
            print(f"    [concept] SQL: {sql}")
            print(f"    [concept] params: {params}")
            try:
                rows = conn.execute(sql, params).fetchall()
                data = [dict(r) for r in rows]
                print(f"    [concept] {name}: {len(data)} 行")
            except Exception as e:
                print(f"    [concept] {name}: 执行失败 {e}")
                data = []

        concept_results.append({'name': name, 'label': label, 'data': data})

    # 合并结果
    merged = merge_concept_results(concept_results, time_granularity)
    if not merged:
        return {'success': False, 'error': '概念查询无数据'}

    concept_names = [c['def']['label'] for c in concepts]
    year = entities.get('period_year', '')
    gran_cn = {'quarterly': '各季度', 'monthly': '各月', 'yearly': '年度'}
    summary = f"概念查询: {'、'.join(concept_names)} ({year}年{gran_cn.get(time_granularity, '')})"

    return {
        'success': True,
        'results': merged,
        'cross_domain_summary': summary,
        'concept_pipeline': True,
    }


def _build_params(entities: dict, intent: dict) -> dict:
    """构建SQL参数绑定（支持VAT月份、EIT年度/季度、多年对比、枚举月份）"""
    params = {}
    if entities.get('taxpayer_id'):
        params['taxpayer_id'] = entities['taxpayer_id']

    filters = intent.get('filters', {})
    period = filters.get('period', {})

    if period.get('year'):
        params['year'] = period['year']
    elif entities.get('period_year'):
        params['year'] = entities['period_year']

    if period.get('month'):
        params['month'] = period['month']
    elif entities.get('period_month'):
        params['month'] = entities['period_month']

    # 季度参数（EIT）
    if period.get('quarter'):
        params['quarter'] = period['quarter']
    elif entities.get('period_quarter'):
        params['quarter'] = entities['period_quarter']

    # 多年对比参数
    period_years = entities.get('period_years')
    if period_years and len(period_years) > 1:
        for i, y in enumerate(period_years):
            params[f'year{i+1}'] = y
        params['start_year'] = period_years[0]
        params['end_year'] = period_years[-1]

    # 枚举月份参数
    period_months = entities.get('period_months')
    if period_months and len(period_months) > 1:
        for i, m in enumerate(period_months):
            params[f'month{i+1}'] = m

    # 范围查询
    period_mode = filters.get('period_mode', 'month')
    if period_mode == 'range_month' or entities.get('period_end_month'):
        start_m = period.get('start_month') or entities.get('period_month') or 1
        end_m = period.get('end_month') or entities.get('period_end_month') or 12
        year = params.get('year', 2025)

        # 跨年范围
        end_year = entities.get('period_end_year')
        if end_year and end_year != year:
            params['start_yyyymm'] = year * 100 + start_m
            params['end_yyyymm'] = end_year * 100 + end_m
        else:
            params['start_yyyymm'] = year * 100 + start_m
            params['end_yyyymm'] = year * 100 + end_m

        # 补充start/end分量参数（LLM可能引用）
        if 'start_year' not in params:
            params['start_year'] = year
        if 'start_month' not in params:
            params['start_month'] = start_m
        if 'end_year' not in params:
            params['end_year'] = end_year or year
        if 'end_month' not in params:
            params['end_month'] = end_m

    # 全年范围：如果有year但没有month和end_month，补充全年范围参数
    if params.get('year') and 'start_yyyymm' not in params and not params.get('month'):
        year = params['year']
        params['start_yyyymm'] = year * 100 + 1
        params['end_yyyymm'] = year * 100 + 12
        params.setdefault('start_year', year)
        params.setdefault('start_month', 1)
        params.setdefault('end_year', year)
        params.setdefault('end_month', 12)

    return params


def _log_query(conn, user_query, normalized, entities, intent, sql, success, error_msg=None):
    """记录查询日志"""
    try:
        conn.execute(
            """INSERT INTO user_query_log
            (user_query, normalized_query, taxpayer_id, taxpayer_name,
             period_year, period_month, domain, success, error_message, generated_sql)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user_query, normalized,
             entities.get('taxpayer_id'), entities.get('taxpayer_name'),
             entities.get('period_year'), entities.get('period_month'),
             intent.get('domain') if intent else None,
             1 if success else 0, error_msg, sql)
        )
        conn.commit()
    except Exception:
        pass


def print_cache_stats():
    """打印缓存统计信息"""
    if not CACHE_ENABLED:
        print("缓存未启用")
        return

    stats = get_cache_stats()

    print(f"\n{'='*60}")
    print("缓存统计")
    print(f"{'='*60}")

    print(f"\nStage 1 (意图解析):")
    print(f"  缓存大小: {stats['intent']['size']}/{stats['intent']['max_size']}")
    print(f"  命中次数: {stats['intent']['hits']}")
    print(f"  未命中次数: {stats['intent']['misses']}")
    print(f"  总请求数: {stats['intent']['total']}")
    print(f"  命中率: {stats['intent']['hit_rate']:.1%}")

    print(f"\nStage 2 (SQL生成):")
    print(f"  缓存大小: {stats['sql']['size']}/{stats['sql']['max_size']}")
    print(f"  命中次数: {stats['sql']['hits']}")
    print(f"  未命中次数: {stats['sql']['misses']}")
    print(f"  总请求数: {stats['sql']['total']}")
    print(f"  命中率: {stats['sql']['hit_rate']:.1%}")

    print(f"\n执行结果缓存:")
    print(f"  缓存大小: {stats['result']['size']}/{stats['result']['max_size']}")
    print(f"  命中次数: {stats['result']['hits']}")
    print(f"  未命中次数: {stats['result']['misses']}")
    print(f"  命中率: {stats['result']['hit_rate']:.1%}")

    print(f"\n跨域结果缓存:")
    print(f"  缓存大小: {stats['cross_domain']['size']}/{stats['cross_domain']['max_size']}")
    print(f"  命中次数: {stats['cross_domain']['hits']}")
    print(f"  未命中次数: {stats['cross_domain']['misses']}")
    print(f"  命中率: {stats['cross_domain']['hit_rate']:.1%}")

    print(f"\n总体:")
    print(f"  总命中次数: {stats['total_hits']}")
    print(f"  总未命中次数: {stats['total_misses']}")
    print(f"  总请求数: {stats['total_requests']}")
    print(f"  总体命中率: {stats['overall_hit_rate']:.1%}")
    print(f"{'='*60}\n")


def main():
    """交互模式"""
    from database.init_db import init_database
    from database.seed_data import seed_reference_data
    from database.sample_data import insert_sample_data

    if not Path(DB_PATH).exists():
        print("初始化数据库...")
        init_database()
        seed_reference_data()
        insert_sample_data()

    print("\n" + "="*60)
    print("fintax_ai NL2SQL MVP 管线")
    print("输入自然语言查询，输入 'quit' 退出")
    print("="*60)

    while True:
        try:
            query = input("\n请输入查询> ").strip()
            if query.lower() in ('quit', 'exit', 'q'):
                break
            if not query:
                continue
            run_pipeline(query)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"错误: {e}")

    print("\n再见！")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_pipeline(query)
    else:
        main()
