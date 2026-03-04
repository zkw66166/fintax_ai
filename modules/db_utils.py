"""统一 SQLite 连接工厂 — PRAGMA 调优 + 线程本地连接复用"""
import sqlite3
import threading
from pathlib import Path

_DB_PATH = None


def _default_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        from config.settings import DB_PATH
        _DB_PATH = str(DB_PATH)
    return _DB_PATH


def get_connection(db_path=None, row_factory=True):
    """创建带 PRAGMA 调优的 SQLite 连接。"""
    path = db_path or _default_db_path()
    conn = sqlite3.connect(path)
    if row_factory:
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-64000")      # 64 MB 页缓存
    conn.execute("PRAGMA mmap_size=268435456")     # 256 MB 内存映射
    conn.execute("PRAGMA temp_store=MEMORY")       # 临时表存内存
    conn.execute("PRAGMA synchronous=NORMAL")      # WAL 下安全且更快
    return conn


# --------------- 线程本地连接复用 ---------------
_local = threading.local()


def get_pooled_connection(db_path=None):
    """获取线程本地复用连接（读密集场景）。"""
    path = db_path or _default_db_path()
    conn = getattr(_local, 'conn', None)
    if conn is None:
        conn = get_connection(path)
        _local.conn = conn
    return conn


def close_pooled_connection():
    """关闭线程本地连接（线程退出或应用关闭时调用）。"""
    conn = getattr(_local, 'conn', None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _local.conn = None
