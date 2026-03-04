"""为现有数据库补齐缺失的复合索引（利润表、现金流量表、财务指标）"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def add_missing_indexes():
    print(f"连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    indexes = [
        ("idx_is_taxpayer_period_gaap",
         "fs_income_statement_item(taxpayer_id, period_year, period_month, gaap_type, revision_no DESC)",
         "利润表：优化 EAV 透视视图查询"),

        ("idx_cf_taxpayer_period_gaap",
         "fs_cash_flow_item(taxpayer_id, period_year, period_month, gaap_type, revision_no DESC)",
         "现金流量表：优化 EAV 透视视图查询"),

        ("idx_fmi_taxpayer_period_type",
         "financial_metrics_item(taxpayer_id, period_year, period_type, metric_code)",
         "财务指标：优化画像服务复合查询"),
    ]

    print(f"\n准备添加 {len(indexes)} 个索引...\n")

    success_count = 0
    skip_count = 0

    for idx_name, idx_def, description in indexes:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (idx_name,)
        )
        if cursor.fetchone():
            print(f"⊙ {idx_name}: 已存在，跳过")
            skip_count += 1
            continue

        print(f"→ {idx_name}: {description}")
        conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
        conn.commit()
        print(f"  ✓ 创建成功")
        success_count += 1

    conn.close()
    print(f"\n完成：成功 {success_count}，跳过 {skip_count}")


if __name__ == "__main__":
    add_missing_indexes()
