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
    """将 SQL 中的纳税人 ID 替换为占位符

    Args:
        sql: 原始 SQL
        company_id: 纳税人 ID

    Returns:
        (模板化的 SQL, 是否成功)
    """
    if not sql or not company_id:
        return sql, False

    # 全局替换 taxpayer_id = 'xxx'
    pattern = rf"\btaxpayer_id\s*=\s*'{re.escape(company_id)}'"
    template = re.sub(pattern, "taxpayer_id = '{{TAXPAYER_ID}}'", sql, flags=re.IGNORECASE)

    # 验证是否有替换
    if "{{TAXPAYER_ID}}" not in template:
        return sql, False

    return template, True


def instantiate_sql(template: str, company_id: str) -> str:
    """将占位符替换为实际纳税人 ID

    Args:
        template: SQL 模板
        company_id: 纳税人 ID

    Returns:
        实例化的 SQL
    """
    return template.replace("{{TAXPAYER_ID}}", company_id)


def save_template_cache(query: str, response_mode: str, taxpayer_type: str,
                        accounting_standard: str, intent: Dict, sql_template: str,
                        domain: str) -> str:
    """保存 L2 模板缓存（域感知缓存键）

    Args:
        query: 用户查询
        response_mode: 响应模式
        taxpayer_type: 纳税人类型
        accounting_standard: 会计准则
        intent: 意图解析结果
        sql_template: SQL 模板
        domain: 数据域

    Returns:
        缓存键
    """
    if not QUERY_CACHE_ENABLED_L2:
        return ""

    _ensure_dir()

    # 域感知缓存键
    cache_domain = detect_cache_domain(domain=domain, sql_template=sql_template)
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
        "sql_template": sql_template,
        "domain": domain,
        "created_at": time.time(),
        "last_accessed_at": time.time(),
        "hit_count": 0
    }

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
