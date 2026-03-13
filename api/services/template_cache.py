"""L2 模板缓存 - 支持跨纳税人查询加速（域感知缓存键）"""
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Tuple

from config.settings import (
    QUERY_CACHE_DIR,
    QUERY_CACHE_ENABLED_L2,
    QUERY_CACHE_MAX_FILES_L2,
    QUERY_CACHE_L2_PREFIX
)

_lock = threading.Lock()
_index: Dict[str, float] = {}  # cache_key -> last_accessed_at
_initialized = False

# 域分类常量
_FINANCIAL_STATEMENT_DOMAINS = frozenset([
    "balance_sheet", "profit", "cash_flow", "account_balance"
])
_FINANCIAL_STATEMENT_VIEWS = frozenset([
    "vw_balance_sheet_eas", "vw_balance_sheet_sas",
    "vw_profit_eas", "vw_profit_sas",
    "vw_cash_flow_eas", "vw_cash_flow_sas",
    "vw_account_balance"
])
_VAT_VIEWS = frozenset(["vw_vat_return_general", "vw_vat_return_small"])
_EIT_VIEWS = frozenset(["vw_eit_annual_main", "vw_eit_quarter_main"])


def _ensure_dir():
    """确保缓存目录存在"""
    global _initialized
    if _initialized:
        return
    QUERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _initialized = True


def _cache_path(cache_key: str) -> Path:
    """生成 L2 缓存文件路径"""
    return QUERY_CACHE_DIR / f"{QUERY_CACHE_L2_PREFIX}{cache_key}.json"


def detect_cache_domain(domain: str = "", sql_template: str = "") -> str:
    """检测缓存键应使用的域类别

    优先使用 domain 参数，其次从 SQL 模板中检测视图名称。

    Returns:
        "financial_statement" | "vat" | "eit" | "unknown"
    """
    # 方式1：基于 domain 参数
    if domain in _FINANCIAL_STATEMENT_DOMAINS:
        return "financial_statement"
    if domain == "vat":
        return "vat"
    if domain in ("eit", "eit_annual", "eit_quarter"):
        return "eit"

    # 方式2：基于 SQL 模板中的视图名称
    if sql_template:
        sql_lower = sql_template.lower()
        if any(v in sql_lower for v in _FINANCIAL_STATEMENT_VIEWS):
            return "financial_statement"
        if any(v in sql_lower for v in _VAT_VIEWS):
            return "vat"
        if any(v in sql_lower for v in _EIT_VIEWS):
            return "eit"

    return "unknown"


def _build_cache_key(query: str, response_mode: str, taxpayer_type: str,
                     accounting_standard: str) -> str:
    """生成 L2 缓存键（旧版，保留向后兼容）

    Args:
        query: 标准化查询
        response_mode: 响应模式
        taxpayer_type: 纳税人类型
        accounting_standard: 会计准则

    Returns:
        MD5 哈希值
    """
    normalized = query.strip().lower()
    raw = f"{normalized}|{response_mode}|{taxpayer_type}|{accounting_standard}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_cache_key_v2(query: str, response_mode: str, cache_domain: str,
                        taxpayer_type: str = "", accounting_standard: str = "") -> str:
    """生成域感知 L2 缓存键

    根据域类别决定缓存键包含哪些维度：
    - financial_statement: key by (query, response_mode, accounting_standard)
    - vat: key by (query, response_mode, taxpayer_type)
    - eit: key by (query, response_mode) — 无类型/准则区分
    - unknown: fallback to (query, response_mode, taxpayer_type, accounting_standard)

    Args:
        query: 用户查询
        response_mode: 响应模式
        cache_domain: 缓存域类别 ("financial_statement"|"vat"|"eit"|"unknown")
        taxpayer_type: 纳税人类型（仅 vat/unknown 使用）
        accounting_standard: 会计准则（仅 financial_statement/unknown 使用）

    Returns:
        MD5 哈希值
    """
    normalized = query.strip().lower()

    if cache_domain == "financial_statement":
        raw = f"{normalized}|{response_mode}|fs|{accounting_standard}"
    elif cache_domain == "vat":
        raw = f"{normalized}|{response_mode}|vat|{taxpayer_type}"
    elif cache_domain == "eit":
        raw = f"{normalized}|{response_mode}|eit"
    else:
        # Fallback：使用全部维度（向后兼容）
        raw = f"{normalized}|{response_mode}|{taxpayer_type}|{accounting_standard}"

    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def templatize_sql(sql: str, company_id: str) -> Tuple[str, bool]:
    """将 SQL 中的纳税人 ID 参数占位符替换为模板占位符

    支持两种格式：
    1. 参数化查询: taxpayer_id = :taxpayer_id → taxpayer_id = {{TAXPAYER_ID}}
    2. 内联字符串: taxpayer_id = 'HX001' → taxpayer_id = {{TAXPAYER_ID}}

    Args:
        sql: 原始 SQL
        company_id: 纳税人 ID

    Returns:
        (模板化的 SQL, 是否成功)
    """
    if not sql or not company_id:
        return sql, False

    # 方案1：替换参数化占位符 :taxpayer_id
    pattern_param = r"\btaxpayer_id\s*=\s*:taxpayer_id\b"
    template = re.sub(pattern_param, "taxpayer_id = {{TAXPAYER_ID}}", sql, flags=re.IGNORECASE)

    # 方案2：如果没有参数化占位符，尝试替换内联字符串（向后兼容）
    if "{{TAXPAYER_ID}}" not in template:
        pattern_inline = rf"\btaxpayer_id\s*=\s*'{re.escape(company_id)}'"
        template = re.sub(pattern_inline, "taxpayer_id = {{TAXPAYER_ID}}", template, flags=re.IGNORECASE)

    # 验证是否有替换
    if "{{TAXPAYER_ID}}" not in template:
        return sql, False

    return template, True


def instantiate_sql(template: str, company_id: str) -> str:
    """将占位符替换为参数化占位符

    Args:
        template: SQL 模板
        company_id: 纳税人 ID (此参数保留用于向后兼容，但实际不使用)

    Returns:
        实例化的 SQL（使用参数化占位符 :taxpayer_id）
    """
    # 将模板占位符替换回参数化占位符，而不是直接替换为公司ID
    # 这样可以使用 conn.execute(sql, params) 的参数化查询方式
    return template.replace("{{TAXPAYER_ID}}", ":taxpayer_id")


def templatize_cross_domain_sql(sub_results: list, company_id: str) -> Tuple[list, bool]:
    """将跨域查询的多个子域SQL模板化

    Args:
        sub_results: 子域结果列表，每个包含 {'domain': str, 'sql': str, 'params': dict, 'data': list}
        company_id: 纳税人ID

    Returns:
        (模板化的子域列表, 是否全部成功)
    """
    templated_subs = []
    all_success = True

    for sub in sub_results:
        sql = sub.get('sql', '')
        domain = sub.get('domain', 'unknown')
        params = sub.get('params', {})

        if not sql:
            all_success = False
            continue

        template, success = templatize_sql(sql, company_id)
        if success:
            # 保存 params 的键列表和静态参数值
            param_keys = list(params.keys()) if params else []
            # 静态参数：不依赖运行时 entities 的常量值（如 vat_item_type, vat_time_range, filter_*, time_range）
            # 排除动态参数：taxpayer_id, year, quarter, month, year_N, month_N
            static_params = {}
            if params:
                for k, v in params.items():
                    if k not in ('taxpayer_id',) and not k.startswith('year') and not k.startswith('month') and k not in ('quarter',):
                        static_params[k] = v

            templated_subs.append({
                'domain': domain,
                'sql_template': template,
                'param_keys': param_keys,  # ✅ 保存参数键列表
                'static_params': static_params  # ✅ 保存静态参数值
            })
        else:
            all_success = False

    return templated_subs, all_success


def instantiate_cross_domain_sql(sub_templates: list, company_id: str) -> list:
    """实例化跨域查询的多个子域SQL模板

    Args:
        sub_templates: 子域模板列表，每个包含 {'domain': str, 'sql_template': str}
        company_id: 纳税人ID

    Returns:
        实例化后的子域SQL列表，格式: [{'domain': str, 'sql': str}, ...]
    """
    instantiated = []
    for sub in sub_templates:
        template = sub.get('sql_template', '')
        domain = sub.get('domain', 'unknown')

        if template:
            sql = instantiate_sql(template, company_id)
            instantiated.append({
                'domain': domain,
                'sql': sql
            })

    return instantiated


def save_template_cache(query: str, response_mode: str, taxpayer_type: str,
                        accounting_standard: str, intent: Dict, sql_template: str,
                        domain: str, sub_templates: list = None,
                        cross_domain_operation: str = None,
                        pipeline_type: str = None,
                        time_granularity: str = None) -> str:
    """保存 L2 模板缓存（域感知缓存键，支持跨域查询和概念管线）

    Args:
        query: 用户查询
        response_mode: 响应模式
        taxpayer_type: 纳税人类型
        accounting_standard: 会计准则
        intent: 意图解析结果
        sql_template: SQL 模板（单域查询）
        domain: 数据域
        sub_templates: 子域模板列表（跨域查询），格式: [{'domain': str, 'sql_template': str}, ...]
        cross_domain_operation: 跨域操作类型（'compare'|'ratio'|'reconcile'|'list'）
        pipeline_type: 管线类型（'concept'|None），用于区分概念管线和 LLM 跨域管线
        time_granularity: 时间粒度（'quarterly'|'monthly'|'yearly'|None），概念管线使用

    Returns:
        缓存键
    """
    if not QUERY_CACHE_ENABLED_L2:
        return ""

    _ensure_dir()

    # 域感知缓存键
    cache_domain = detect_cache_domain(domain=domain, sql_template=sql_template or "")
    cache_key = _build_cache_key_v2(
        query, response_mode, cache_domain,
        taxpayer_type=taxpayer_type, accounting_standard=accounting_standard
    )
    print(f"[L2 Cache] Save key: domain={domain}, cache_domain={cache_domain}, key={cache_key[:12]}...")

    entry = {
        "cache_key": cache_key,
        "query": query,
        "response_mode": response_mode,
        "taxpayer_type": taxpayer_type,
        "accounting_standard": accounting_standard,
        "intent": intent,
        "domain": domain,
        "created_at": time.time(),
        "last_accessed_at": time.time(),
        "hit_count": 0
    }

    # 跨域查询：保存子域模板列表
    if sub_templates:
        # 检测是否为单域概念查询（所有子域来自同一个域）
        unique_domains = set(s['domain'] for s in sub_templates)
        if len(unique_domains) == 1 and domain != 'cross_domain':
            # 单域概念查询：保留原始域名用于域感知缓存键
            entry["cache_domain"] = domain
        else:
            # 真正的跨域查询
            entry["cache_domain"] = "cross_domain"

        entry["sub_templates"] = sub_templates
        entry["subdomains"] = [s['domain'] for s in sub_templates]
        if cross_domain_operation:
            entry["cross_domain_operation"] = cross_domain_operation
        if pipeline_type:
            entry["pipeline_type"] = pipeline_type
        if time_granularity:
            entry["time_granularity"] = time_granularity
    else:
        # 单域查询：保存单个SQL模板
        entry["sql_template"] = sql_template

    with _lock:
        try:
            fp = _cache_path(cache_key)
            fp.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
            _index[cache_key] = time.time()
        except Exception as e:
            print(f"[L2 Cache] Save failed: {e}")
            return ""

    # LRU 清理
    cleanup_l2_cache()
    return cache_key


def get_template_cache(query: str, response_mode: str, taxpayer_type: str,
                       accounting_standard: str,
                       domain: str = "") -> Optional[Dict]:
    """获取 L2 模板缓存（域感知缓存键）

    Args:
        query: 用户查询
        response_mode: 响应模式
        taxpayer_type: 纳税人类型
        accounting_standard: 会计准则
        domain: 数据域（可选，用于域感知缓存键）

    Returns:
        缓存条目，未命中返回 None
    """
    if not QUERY_CACHE_ENABLED_L2:
        return None

    _ensure_dir()

    # 域感知缓存键
    cache_domain = detect_cache_domain(domain=domain)
    cache_key = _build_cache_key_v2(
        query, response_mode, cache_domain,
        taxpayer_type=taxpayer_type, accounting_standard=accounting_standard
    )
    fp = _cache_path(cache_key)

    if not fp.exists():
        # 向后兼容：尝试旧版缓存键
        old_key = _build_cache_key(query, response_mode, taxpayer_type, accounting_standard)
        old_fp = _cache_path(old_key)
        if old_fp.exists():
            print(f"[L2 Cache] Hit via legacy key for domain={domain}")
            fp = old_fp
            cache_key = old_key
        else:
            return None

    try:
        data = json.loads(fp.read_text(encoding="utf-8"))

        # 更新访问时间
        data["last_accessed_at"] = time.time()
        data["hit_count"] = data.get("hit_count", 0) + 1

        with _lock:
            try:
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                _index[cache_key] = time.time()
            except Exception:
                pass

        return data
    except Exception as e:
        print(f"[L2 Cache] Read failed: {e}")
        return None


def delete_template_cache(cache_key: str) -> bool:
    """删除指定 L2 缓存文件

    Args:
        cache_key: L2 缓存键（不含 prefix）

    Returns:
        是否成功删除
    """
    _ensure_dir()
    fp = _cache_path(cache_key)
    if fp.exists():
        with _lock:
            try:
                fp.unlink(missing_ok=True)
                _index.pop(cache_key, None)
                return True
            except Exception as e:
                print(f"[L2 Cache] Delete failed: {e}")
                return False
    return False


def find_l2_keys_for_entry(entry: dict) -> list:
    """根据 history entry 信息查找可能的 L2 cache keys

    由于 L2 缓存键依赖 domain + taxpayer_type/accounting_standard，
    需要从 entry 中提取这些信息并重新计算所有可能的 key。

    Args:
        entry: 历史记录条目

    Returns:
        可能的 L2 cache key 列表
    """
    query = entry.get("query", "")
    response_mode = entry.get("response_mode", "detailed")
    result = entry.get("result", {})
    entities = result.get("entities", {})
    domain = entry.get("domain", "") or entities.get("domain_hint", "")
    route = entry.get("route", "")

    if not query or route != "financial_data":
        return []

    keys = []
    cache_domain = detect_cache_domain(domain=domain)

    if cache_domain == "financial_statement":
        for std in ("企业会计准则", "小企业会计准则"):
            k = _build_cache_key_v2(query, response_mode, cache_domain, accounting_standard=std)
            keys.append(k)
    elif cache_domain == "vat":
        for tp in ("一般纳税人", "小规模纳税人"):
            k = _build_cache_key_v2(query, response_mode, cache_domain, taxpayer_type=tp)
            keys.append(k)
    elif cache_domain == "eit":
        k = _build_cache_key_v2(query, response_mode, cache_domain)
        keys.append(k)
    else:
        tp = entities.get("taxpayer_type", "")
        std = entities.get("accounting_standard", "")
        if tp and std:
            k = _build_cache_key_v2(query, response_mode, cache_domain, taxpayer_type=tp, accounting_standard=std)
            keys.append(k)

    return keys


def cleanup_l2_cache(max_files: int = QUERY_CACHE_MAX_FILES_L2) -> int:
    """清理 L2 缓存（LRU 淘汰）

    Args:
        max_files: 最大文件数

    Returns:
        淘汰的文件数
    """
    _ensure_dir()

    # 扫描所有 L2 缓存文件
    l2_files = list(QUERY_CACHE_DIR.glob(f"{QUERY_CACHE_L2_PREFIX}*.json"))

    if len(l2_files) <= max_files:
        return 0

    with _lock:
        # 按访问时间排序
        file_times = []
        for fp in l2_files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                accessed = data.get("last_accessed_at", 0)
                file_times.append((fp, accessed))
            except Exception:
                file_times.append((fp, 0))

        file_times.sort(key=lambda x: x[1])

        # 淘汰最旧的文件
        to_evict = len(l2_files) - max_files
        evicted = 0

        for fp, _ in file_times[:to_evict]:
            try:
                cache_key = fp.stem.replace(QUERY_CACHE_L2_PREFIX, "")
                fp.unlink(missing_ok=True)
                _index.pop(cache_key, None)
                evicted += 1
            except Exception:
                pass

        if evicted > 0:
            print(f"[L2 Cache] Evicted {evicted} files, current={len(l2_files) - evicted}")

        return evicted
