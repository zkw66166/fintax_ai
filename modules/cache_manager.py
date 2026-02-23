"""缓存管理器 - 两级缓存：Stage 1意图缓存 + Stage 2 SQL缓存"""
import hashlib
import json
import time
import threading
from typing import Optional, Dict, Any, List
from collections import OrderedDict


class LRUCache:
    """线程安全的LRU缓存实现（带TTL）"""

    def __init__(self, max_size: int, ttl: int):
        """
        Args:
            max_size: 最大缓存条目数
            ttl: 过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()  # {key: (value, timestamp)}
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self.cache:
                self.misses += 1
                return None

            value, timestamp = self.cache[key]

            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                del self.cache[key]
                self.misses += 1
                return None

            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self._lock:
            # 如果已存在，先删除
            if key in self.cache:
                del self.cache[key]

            # 如果超过最大大小，删除最旧的
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            # 添加新值
            self.cache[key] = (value, time.time())

    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0.0
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'total': total,
                'hit_rate': hit_rate
            }


# 全局缓存实例
_intent_cache: Optional[LRUCache] = None
_sql_cache: Optional[LRUCache] = None
_result_cache: Optional[LRUCache] = None
_cross_cache: Optional[LRUCache] = None


def _init_caches():
    """初始化缓存（延迟加载）"""
    global _intent_cache, _sql_cache, _result_cache, _cross_cache

    if _intent_cache is None:
        from config.settings import CACHE_MAX_SIZE_INTENT, CACHE_TTL_INTENT
        _intent_cache = LRUCache(max_size=CACHE_MAX_SIZE_INTENT, ttl=CACHE_TTL_INTENT)

    if _sql_cache is None:
        from config.settings import CACHE_MAX_SIZE_SQL, CACHE_TTL_SQL
        _sql_cache = LRUCache(max_size=CACHE_MAX_SIZE_SQL, ttl=CACHE_TTL_SQL)

    if _result_cache is None:
        from config.settings import CACHE_MAX_SIZE_RESULT, CACHE_TTL_RESULT
        _result_cache = LRUCache(max_size=CACHE_MAX_SIZE_RESULT, ttl=CACHE_TTL_RESULT)

    if _cross_cache is None:
        from config.settings import CACHE_MAX_SIZE_CROSS, CACHE_TTL_CROSS
        _cross_cache = LRUCache(max_size=CACHE_MAX_SIZE_CROSS, ttl=CACHE_TTL_CROSS)


def _generate_cache_key(data: Any) -> str:
    """生成稳定的缓存键"""
    if isinstance(data, dict):
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
    elif isinstance(data, (list, tuple)):
        content = json.dumps(data, ensure_ascii=False)
    else:
        content = str(data)

    return hashlib.md5(content.encode()).hexdigest()


# ============ Stage 1 意图缓存 ============

def get_cached_intent(normalized_query: str, taxpayer_type: str, synonym_hits: List[Dict]) -> Optional[Dict]:
    """
    获取缓存的意图解析结果

    Args:
        normalized_query: 标准化后的查询
        taxpayer_type: 纳税人类型
        synonym_hits: 同义词命中列表

    Returns:
        缓存的意图JSON，如果未命中则返回None
    """
    _init_caches()

    # 生成缓存键
    cache_data = {
        'query': normalized_query,
        'taxpayer_type': taxpayer_type,
        'synonym_hits': [(h['phrase'], h['column_name']) for h in synonym_hits]  # 只保留关键信息
    }
    cache_key = _generate_cache_key(cache_data)

    return _intent_cache.get(cache_key)


def cache_intent(normalized_query: str, taxpayer_type: str, synonym_hits: List[Dict], intent: Dict):
    """
    缓存意图解析结果

    Args:
        normalized_query: 标准化后的查询
        taxpayer_type: 纳税人类型
        synonym_hits: 同义词命中列表
        intent: 意图JSON
    """
    _init_caches()

    cache_data = {
        'query': normalized_query,
        'taxpayer_type': taxpayer_type,
        'synonym_hits': [(h['phrase'], h['column_name']) for h in synonym_hits]
    }
    cache_key = _generate_cache_key(cache_data)

    _intent_cache.set(cache_key, intent)


# ============ Stage 2 SQL缓存 ============

def get_cached_sql(constraints: Dict) -> Optional[str]:
    """
    获取缓存的SQL生成结果

    Args:
        constraints: 约束字典（包含intent_json_text, allowed_views_text, allowed_columns_text）

    Returns:
        缓存的SQL字符串，如果未命中则返回None
    """
    _init_caches()

    # 生成缓存键（使用关键约束字段）
    cache_data = {
        'intent': constraints.get('intent_json_text', ''),
        'views': constraints.get('allowed_views_text', ''),
        'columns': constraints.get('allowed_columns_text', '')
    }
    cache_key = _generate_cache_key(cache_data)

    return _sql_cache.get(cache_key)


def cache_sql(constraints: Dict, sql: str):
    """
    缓存SQL生成结果

    Args:
        constraints: 约束字典
        sql: 生成的SQL字符串
    """
    _init_caches()

    cache_data = {
        'intent': constraints.get('intent_json_text', ''),
        'views': constraints.get('allowed_views_text', ''),
        'columns': constraints.get('allowed_columns_text', '')
    }
    cache_key = _generate_cache_key(cache_data)

    _sql_cache.set(cache_key, sql)


# ============ 缓存管理 ============

def clear_cache():
    """清空所有缓存"""
    _init_caches()
    _intent_cache.clear()
    _sql_cache.clear()
    _result_cache.clear()
    _cross_cache.clear()


# ============ SQL执行结果缓存 ============

def get_cached_result(sql: str, params: Dict) -> Optional[List]:
    """获取缓存的SQL执行结果"""
    _init_caches()
    cache_data = {'sql': sql, 'params': sorted(params.items()) if params else []}
    cache_key = _generate_cache_key(cache_data)
    return _result_cache.get(cache_key)


def cache_result(sql: str, params: Dict, rows: List):
    """缓存SQL执行结果"""
    _init_caches()
    cache_data = {'sql': sql, 'params': sorted(params.items()) if params else []}
    cache_key = _generate_cache_key(cache_data)
    _result_cache.set(cache_key, rows)


# ============ 跨域合并结果缓存 ============

def get_cached_cross_domain(normalized_query: str, taxpayer_id: str,
                             cross_domain_list: List[str],
                             period_key: str) -> Optional[Dict]:
    """获取缓存的跨域查询合并结果"""
    _init_caches()
    cache_data = {
        'query': normalized_query,
        'taxpayer_id': taxpayer_id,
        'cross_list': sorted(cross_domain_list),
        'period': period_key,
    }
    cache_key = _generate_cache_key(cache_data)
    return _cross_cache.get(cache_key)


def cache_cross_domain(normalized_query: str, taxpayer_id: str,
                        cross_domain_list: List[str],
                        period_key: str, result: Dict):
    """缓存跨域查询合并结果"""
    _init_caches()
    cache_data = {
        'query': normalized_query,
        'taxpayer_id': taxpayer_id,
        'cross_list': sorted(cross_domain_list),
        'period': period_key,
    }
    cache_key = _generate_cache_key(cache_data)
    _cross_cache.set(cache_key, result)


def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息

    Returns:
        {
            'intent': {...},
            'sql': {...},
            'total_hits': int,
            'total_misses': int,
            'overall_hit_rate': float
        }
    """
    _init_caches()

    intent_stats = _intent_cache.get_stats()
    sql_stats = _sql_cache.get_stats()
    result_stats = _result_cache.get_stats()
    cross_stats = _cross_cache.get_stats()

    total_hits = intent_stats['hits'] + sql_stats['hits'] + result_stats['hits'] + cross_stats['hits']
    total_misses = intent_stats['misses'] + sql_stats['misses'] + result_stats['misses'] + cross_stats['misses']
    total = total_hits + total_misses
    overall_hit_rate = total_hits / total if total > 0 else 0.0

    return {
        'intent': intent_stats,
        'sql': sql_stats,
        'result': result_stats,
        'cross_domain': cross_stats,
        'total_hits': total_hits,
        'total_misses': total_misses,
        'total_requests': total,
        'overall_hit_rate': overall_hit_rate
    }
