"""迁移脚本：为企业画像扩展 taxpayer_info 字段 + 填充示例数据"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def migrate(db_path=None):
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 获取现有列名
    existing = {row[1] for row in cur.execute("PRAGMA table_info(taxpayer_info)")}

    new_columns = [
        ("registered_capital", "NUMERIC"),
        ("registered_address", "TEXT"),
        ("business_scope", "TEXT"),
        ("operating_status", "TEXT DEFAULT '存续'"),
        ("collection_method", "TEXT DEFAULT '查账征收'"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing:
            cur.execute(f"ALTER TABLE taxpayer_info ADD COLUMN {col_name} {col_type}")
            print(f"  [migrate] 添加列: {col_name} {col_type}")
        else:
            print(f"  [migrate] 列已存在: {col_name}")

    # 填充示例数据
    cur.execute("""
        UPDATE taxpayer_info SET
            registered_capital = 5000,
            registered_address = '上海市浦东新区张江高科技园区碧波路690号',
            business_scope = '软件开发、信息技术咨询、技术服务、计算机系统集成',
            operating_status = '存续',
            collection_method = '查账征收'
        WHERE taxpayer_id = '91310000MA1FL8XQ30'
    """)

    cur.execute("""
        UPDATE taxpayer_info SET
            registered_capital = 50,
            registered_address = '深圳市南山区科技园南区高新南一道',
            business_scope = '日用百货、办公用品、电子产品零售',
            operating_status = '存续',
            collection_method = '查账征收'
        WHERE taxpayer_id = '92440300MA5EQXL17P'
    """)

    conn.commit()
    conn.close()
    print("[migrate_profile] 迁移完成")


if __name__ == "__main__":
    migrate()
