"""迁移脚本：创建 profile_reports 表"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def migrate(db_path=None):
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile_reports (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            taxpayer_id   TEXT    NOT NULL,
            taxpayer_name TEXT    NOT NULL,
            year          INTEGER NOT NULL,
            user_id       INTEGER NOT NULL,
            username      TEXT    NOT NULL,
            status        TEXT    NOT NULL DEFAULT 'generating',
            content       TEXT,
            error_msg     TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at  TIMESTAMP
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_reports_taxpayer "
        "ON profile_reports(taxpayer_id, year)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_profile_reports_user "
        "ON profile_reports(user_id)"
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
    print("[migrate_profile_reports] Done.")
