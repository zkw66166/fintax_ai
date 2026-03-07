"""Persistent file-based query cache for complete pipeline results.

Each query result (including display_data and interpretation) is stored as a
JSON file under ``cache/{md5_hash}.json``.  An in-memory index accelerates
LRU eviction and key lookups.
"""

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import (
    QUERY_CACHE_DIR,
    QUERY_CACHE_ENABLED,
    QUERY_CACHE_MAX_FILES_L1,
    QUERY_CACHE_L2_PREFIX
)

# 向后兼容
try:
    from config.settings import QUERY_CACHE_MAX_FILES
except ImportError:
    QUERY_CACHE_MAX_FILES = QUERY_CACHE_MAX_FILES_L1

_lock = threading.Lock()

# In-memory index: cache_key -> last_accessed_at (epoch)
_index: Dict[str, float] = {}

_initialized = False


def _ensure_dir():
    """Create cache directory if it doesn't exist."""
    global _initialized
    if _initialized:
        return
    QUERY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _initialized = True


def _rebuild_index():
    """Scan cache directory and rebuild in-memory index on startup."""
    _ensure_dir()
    for fp in QUERY_CACHE_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            key = data.get("cache_key", fp.stem)
            accessed = data.get("last_accessed_at", 0)
            if isinstance(accessed, str):
                # ISO timestamp -> epoch
                try:
                    from datetime import datetime, timezone
                    accessed = datetime.fromisoformat(accessed).timestamp()
                except Exception:
                    accessed = fp.stat().st_mtime
            _index[key] = accessed
        except Exception:
            # Corrupted file — ignore
            pass


def _init():
    """Lazy initialization: rebuild index on first call."""
    global _initialized
    if not _initialized:
        _rebuild_index()
        _initialized = True


def _cache_path(cache_key: str) -> Path:
    return QUERY_CACHE_DIR / f"{cache_key}.json"


def _build_cache_key(company_id: str, query: str, response_mode: str) -> str:
    """Build deterministic cache key from company_id + normalized query + response_mode."""
    normalized = query.strip().lower()
    raw = f"{company_id}|{normalized}|{response_mode}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cached_query(company_id: str, query: str, response_mode: str) -> Optional[dict]:
    """Look up cache by company_id + query + response_mode.

    Returns the full cache entry dict on hit, or None on miss.
    Updates ``last_accessed_at`` and ``hit_count`` on hit.
    """
    if not QUERY_CACHE_ENABLED:
        return None
    _init()
    cache_key = _build_cache_key(company_id, query, response_mode)
    fp = _cache_path(cache_key)
    if not fp.exists():
        return None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Update access metadata
    now = _now_iso()
    data["last_accessed_at"] = now
    data["hit_count"] = data.get("hit_count", 0) + 1
    with _lock:
        try:
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        _index[cache_key] = time.time()
    return data


def save_query_cache(
    company_id: str,
    query: str,
    response_mode: str,
    route: str,
    result: dict,
    interpretation: str = "",
) -> str:
    """Save a complete pipeline result to cache.  Returns the cache_key."""
    if not QUERY_CACHE_ENABLED:
        return ""
    _init()
    cache_key = _build_cache_key(company_id, query, response_mode)
    now = _now_iso()
    entry = {
        "cache_key": cache_key,
        "company_id": company_id,
        "query": query,
        "response_mode": response_mode,
        "route": route,
        "result": result,
        "interpretation": interpretation,
        "created_at": now,
        "last_accessed_at": now,
        "hit_count": 0,
    }
    with _lock:
        try:
            _ensure_dir()
            _cache_path(cache_key).write_text(
                json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            _index[cache_key] = time.time()
        except Exception:
            pass

    # LRU cleanup if over limit
    cleanup_cache(QUERY_CACHE_MAX_FILES)
    return cache_key


def update_cache_interpretation(cache_key: str, interpretation: str) -> bool:
    """Write interpretation text back into an existing cache entry."""
    if not cache_key:
        return False
    fp = _cache_path(cache_key)
    if not fp.exists():
        return False
    with _lock:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            data["interpretation"] = interpretation
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False


def delete_query_cache(cache_key: str) -> bool:
    """Delete a single cache entry by key."""
    fp = _cache_path(cache_key)
    with _lock:
        _index.pop(cache_key, None)
        try:
            fp.unlink(missing_ok=True)
            return True
        except Exception:
            return False


def delete_query_caches(cache_keys: List[str]) -> int:
    """Delete multiple cache entries.  Returns count of successfully deleted."""
    count = 0
    for key in cache_keys:
        if delete_query_cache(key):
            count += 1
    return count


def invalidate_company_caches(company_id: str) -> int:
    """Delete all cache entries for a given company.  Returns count deleted."""
    _init()
    deleted = 0
    with _lock:
        to_remove = []
        for fp in QUERY_CACHE_DIR.glob("*.json"):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                if data.get("company_id") == company_id:
                    to_remove.append((fp, data.get("cache_key", fp.stem)))
            except Exception:
                pass
        for fp, key in to_remove:
            try:
                fp.unlink(missing_ok=True)
                _index.pop(key, None)
                deleted += 1
            except Exception:
                pass
    return deleted


def invalidate_by_company(
    company_id: str,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None
) -> int:
    """Delete cache entries for a company, optionally filtered by period.

    Args:
        company_id: Taxpayer ID to invalidate
        period_year: Optional year filter (e.g., 2025)
        period_month: Optional month filter (e.g., 1-12)

    Returns:
        Count of cache entries deleted

    Examples:
        invalidate_by_company("91310000MA1FL8XQ30")  # All queries for this company
        invalidate_by_company("91310000MA1FL8XQ30", 2025)  # All 2025 queries
        invalidate_by_company("91310000MA1FL8XQ30", 2025, 3)  # March 2025 queries
    """
    _init()
    deleted = 0
    with _lock:
        to_remove = []
        for fp in QUERY_CACHE_DIR.glob("*.json"):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                if data.get("company_id") != company_id:
                    continue

                # If period filters specified, check result entities
                if period_year is not None or period_month is not None:
                    result = data.get("result", {})
                    entities = result.get("entities", {})
                    result_year = entities.get("period_year")
                    result_month = entities.get("period_month")

                    # Skip if period doesn't match
                    if period_year is not None and result_year != period_year:
                        continue
                    if period_month is not None and result_month != period_month:
                        continue

                to_remove.append((fp, data.get("cache_key", fp.stem)))
            except Exception:
                pass

        for fp, key in to_remove:
            try:
                fp.unlink(missing_ok=True)
                _index.pop(key, None)
                deleted += 1
            except Exception:
                pass
    return deleted


def cleanup_cache(max_files: int = None) -> int:
    """Evict oldest L1 cache entries (excludes template_ files). Returns count evicted."""
    if max_files is None:
        max_files = QUERY_CACHE_MAX_FILES_L1

    _init()

    # 仅统计 L1 文件（不含 template_ 前缀）
    l1_keys = [k for k in _index.keys() if not k.startswith(QUERY_CACHE_L2_PREFIX)]

    if len(l1_keys) <= max_files:
        return 0

    with _lock:
        # 按访问时间排序
        sorted_keys = sorted(
            [(k, _index[k]) for k in l1_keys],
            key=lambda kv: kv[1]
        )
        to_evict = len(l1_keys) - max_files
        evicted = 0

        for key, _ in sorted_keys[:to_evict]:
            try:
                _cache_path(key).unlink(missing_ok=True)
                del _index[key]
                evicted += 1
            except Exception:
                pass

        return evicted
