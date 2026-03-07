"""查询路径日志 - 记录每个查询走的缓存路径"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# 配置查询路径日志
def setup_query_path_logger():
    """设置查询路径日志记录器"""
    from config.settings import PROJECT_ROOT

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger("query_path")
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 文件 handler - JSON Lines 格式
    log_file = log_dir / "query_path.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 不使用格式化器，直接写入 JSON
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    return logger


def log_query_path(
    query: str,
    company_id: str,
    path: str,
    response_time: float,
    thinking_mode: str = "quick",
    response_mode: str = "detailed",
    success: bool = True,
    error: Optional[str] = None
):
    """记录查询路径

    Args:
        query: 用户查询
        company_id: 纳税人 ID
        path: 查询路径 (l1/l2/l2_adapted/pipeline)
        response_time: 响应时间（秒）
        thinking_mode: 思考模式
        response_mode: 响应模式
        success: 是否成功
        error: 错误信息（如果有）
    """
    logger = setup_query_path_logger()

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query[:100],  # 截断长查询
        "company_id": company_id,
        "path": path,
        "response_time": round(response_time, 3),
        "thinking_mode": thinking_mode,
        "response_mode": response_mode,
        "success": success
    }

    if error:
        log_entry["error"] = error

    logger.info(json.dumps(log_entry, ensure_ascii=False))


def get_query_path_stats(limit: int = 1000):
    """获取查询路径统计

    Args:
        limit: 读取最近的 N 条记录

    Returns:
        统计信息字典
    """
    from config.settings import PROJECT_ROOT

    log_file = PROJECT_ROOT / "logs" / "query_path.log"
    if not log_file.exists():
        return {
            "total": 0,
            "by_path": {},
            "avg_response_time": {},
            "success_rate": 1.0
        }

    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 读取最后 N 行
            for line in lines[-limit:]:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    except:
        pass

    if not entries:
        return {
            "total": 0,
            "by_path": {},
            "avg_response_time": {},
            "success_rate": 1.0
        }

    # 统计
    stats = {
        "total": len(entries),
        "by_path": {},
        "avg_response_time": {},
        "success_rate": 0.0
    }

    path_times = {}
    success_count = 0

    for entry in entries:
        path = entry.get("path", "unknown")
        response_time = entry.get("response_time", 0)
        success = entry.get("success", True)

        # 按路径统计
        stats["by_path"][path] = stats["by_path"].get(path, 0) + 1

        # 响应时间
        if path not in path_times:
            path_times[path] = []
        path_times[path].append(response_time)

        # 成功率
        if success:
            success_count += 1

    # 计算平均响应时间
    for path, times in path_times.items():
        stats["avg_response_time"][path] = round(sum(times) / len(times), 3)

    stats["success_rate"] = round(success_count / len(entries), 3)

    return stats
