"""迁移脚本：创建 users 表 + 种子数据"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH

try:
    import bcrypt
except ImportError:
    print("[migrate_users] bcrypt 未安装，请先运行: pip install bcrypt")
    sys.exit(1)


def _hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def migrate(db_path=None):
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 检查 users 表是否已存在
    existing_tables = {
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    if "users" not in existing_tables:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'user',
                display_name  TEXT,
                is_active     INTEGER DEFAULT 1,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login    TIMESTAMP,
                created_by    INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
            ON users(username)
        """)
        print("[migrate_users] 创建 users 表")
    else:
        print("[migrate_users] users 表已存在")

    # 种子数据：仅在表为空时插入
    count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        seed = [
            ("admin", _hash_pw("admin123"), "admin", "超级管理员", 1, None),
            ("user1", _hash_pw("123456"), "user", "测试用户", 1, None),
        ]
        cur.executemany(
            "INSERT INTO users (username, password_hash, role, display_name, is_active, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            seed,
        )
        print(f"[migrate_users] 插入 {len(seed)} 条种子数据")
    else:
        print(f"[migrate_users] 已有 {count} 条用户数据，跳过种子插入")

    conn.commit()
    conn.close()
    print("[migrate_users] 迁移完成")


if __name__ == "__main__":
    migrate()
