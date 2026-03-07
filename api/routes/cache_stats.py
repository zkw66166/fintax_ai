"""缓存统计路由"""
import json
from pathlib import Path
from fastapi import APIRouter, Depends
from api.auth import get_current_user
from config.settings import QUERY_CACHE_DIR, QUERY_CACHE_L2_PREFIX

router = APIRouter()


@router.get("/cache/stats")
async def get_cache_stats(user: dict = Depends(get_current_user)):
    """获取缓存统计信息"""
    try:
        # 扫描缓存目录
        cache_dir = Path(QUERY_CACHE_DIR)
        if not cache_dir.exists():
            return {
                "l1_cache": {"total_files": 0, "hit_count": 0, "miss_count": 0, "hit_rate": 0.0},
                "l2_cache": {"total_files": 0, "hit_count": 0, "miss_count": 0, "hit_rate": 0.0, "adapted_count": 0},
                "performance": {}
            }

        # 统计 L1 缓存
        l1_files = [f for f in cache_dir.glob("*.json") if not f.name.startswith(QUERY_CACHE_L2_PREFIX)]
        l1_total_hits = 0
        l1_total_count = 0

        for fp in l1_files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                hit_count = data.get("hit_count", 0)
                l1_total_hits += hit_count
                l1_total_count += 1
            except:
                pass

        # 统计 L2 缓存
        l2_files = list(cache_dir.glob(f"{QUERY_CACHE_L2_PREFIX}*.json"))
        l2_total_hits = 0
        l2_total_count = 0

        for fp in l2_files:
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                hit_count = data.get("hit_count", 0)
                l2_total_hits += hit_count
                l2_total_count += 1
            except:
                pass

        # 读取查询日志统计
        log_stats = _read_query_log_stats()

        return {
            "l1_cache": {
                "total_files": len(l1_files),
                "avg_hit_count": round(l1_total_hits / len(l1_files), 2) if l1_files else 0,
                "hit_count": log_stats.get("l1_hits", 0),
                "miss_count": log_stats.get("total_queries", 0) - log_stats.get("l1_hits", 0),
                "hit_rate": round(log_stats.get("l1_hits", 0) / log_stats.get("total_queries", 1), 3)
            },
            "l2_cache": {
                "total_files": len(l2_files),
                "avg_hit_count": round(l2_total_hits / len(l2_files), 2) if l2_files else 0,
                "hit_count": log_stats.get("l2_hits", 0),
                "adapted_count": log_stats.get("l2_adapted", 0),
                "miss_count": log_stats.get("pipeline_full", 0),
                "hit_rate": round((log_stats.get("l2_hits", 0) + log_stats.get("l2_adapted", 0)) / log_stats.get("total_queries", 1), 3),
                "adapt_success_rate": round(log_stats.get("l2_adapted", 0) / (log_stats.get("l2_hits", 0) + log_stats.get("l2_adapted", 0) + 1), 3)
            },
            "performance": {
                "total_queries": log_stats.get("total_queries", 0),
                "l1_hits": log_stats.get("l1_hits", 0),
                "l2_hits": log_stats.get("l2_hits", 0),
                "l2_adapted": log_stats.get("l2_adapted", 0),
                "pipeline_full": log_stats.get("pipeline_full", 0)
            }
        }
    except Exception as e:
        return {"error": str(e)}


def _read_query_log_stats():
    """从查询日志中读取统计信息"""
    from config.settings import PROJECT_ROOT

    log_file = PROJECT_ROOT / "logs" / "query_path.log"
    if not log_file.exists():
        return {"total_queries": 0, "l1_hits": 0, "l2_hits": 0, "l2_adapted": 0, "pipeline_full": 0}

    stats = {"total_queries": 0, "l1_hits": 0, "l2_hits": 0, "l2_adapted": 0, "pipeline_full": 0}

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    path = data.get("path", "")
                    stats["total_queries"] += 1

                    if path == "l1":
                        stats["l1_hits"] += 1
                    elif path == "l2":
                        stats["l2_hits"] += 1
                    elif path == "l2_adapted":
                        stats["l2_adapted"] += 1
                    elif path == "pipeline":
                        stats["pipeline_full"] += 1
                except:
                    pass
    except:
        pass

    return stats
