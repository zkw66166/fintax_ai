"""迁移脚本：扩展角色体系 + 创建 user_company_access 表 + 预置用户"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH
from config.config_loader import load_json as _load_json

_CFG_seed = _load_json(Path(__file__).resolve().parent.parent / "config" / "auth" / "seed_users.json", {})

try:
    import bcrypt
except ImportError:
    print("[migrate_permissions] bcrypt 未安装，请先运行: pip install bcrypt")
    sys.exit(1)


def _hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def migrate(db_path=None):
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # 1. 创建 user_company_access 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_company_access (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            taxpayer_id TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by  INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id),
            UNIQUE(user_id, taxpayer_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_uca_user ON user_company_access(user_id)")
    print("[migrate_permissions] user_company_access 表已就绪")

    # 2. 更新现有用户角色
    cur.execute("UPDATE users SET role = 'firm', display_name = '事务所用户1' WHERE username = 'user1'")
    cur.execute("UPDATE users SET display_name = '系统管理员' WHERE username = 'admin'")
    print("[migrate_permissions] 更新 user1 -> firm, admin display_name -> 系统管理员")

    # 3. 插入新用户 (INSERT OR IGNORE 防止重复)
    _seed_users = _CFG_seed.get("users", [
        {"username": "sys", "password": "sys123", "role": "sys", "display_name": "超级管理员"},
        {"username": "user2", "password": "123456", "role": "group", "display_name": "集团用户2"},
        {"username": "user3", "password": "123456", "role": "group", "display_name": "集团用户3"},
        {"username": "user4", "password": "123456", "role": "enterprise", "display_name": "企业用户4"},
        {"username": "sws2", "password": "123456", "role": "firm", "display_name": "事务所用户2"},
    ])
    new_users = [
        (u["username"], _hash_pw(u["password"]), u["role"], u["display_name"], 1)
        for u in _seed_users
    ]
    for username, pw_hash, role, display_name, is_active in new_users:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role, display_name, is_active) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, pw_hash, role, display_name, is_active),
        )
    print(f"[migrate_permissions] 预置用户已就绪")

    # 4. 插入 user_company_access 关联
    # sys/admin 不需要行，靠角色判断获取全部企业
    access_map = _CFG_seed.get("access_map", {
        "user1": [
            "91310000MA1FL8XQ30",  # 华兴科技有限公司
            "92440300MA5EQXL17P",  # 鑫源贸易商行
        ],
        "user2": [
            "91330200MA2KXXXXXX",  # 创智软件股份有限公司
            "91330200MA2KYYYYYY",  # 大华智能制造厂
            "91310115MA2KZZZZZZ",  # TSE科技有限公司
            "91330100MA2KWWWWWW",  # 环球机械有限公司
        ],
        "user3": [
            "91330200MA2KXXXXXX",  # 创智软件股份有限公司
            "91330200MA2KYYYYYY",  # 大华智能制造厂
            "91310115MA2KZZZZZZ",  # TSE科技有限公司
        ],
        "user4": [
            "91310000MA1FL8XQ30",  # 华兴科技有限公司
        ],
        "sws2": [
            "91310000MA1FL8XQ30",  # 华兴科技有限公司
            "92440300MA5EQXL17P",  # 鑫源贸易商行
        ],
    })
    for username, taxpayer_ids in access_map.items():
        row = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if not row:
            print(f"[migrate_permissions] 警告: 用户 {username} 不存在，跳过权限分配")
            continue
        user_id = row[0]
        for tid in taxpayer_ids:
            cur.execute(
                "INSERT OR IGNORE INTO user_company_access (user_id, taxpayer_id) VALUES (?, ?)",
                (user_id, tid),
            )
    print("[migrate_permissions] 企业权限关联已就绪")

    conn.commit()
    conn.close()
    print("[migrate_permissions] 迁移完成")


if __name__ == "__main__":
    migrate()
