"""
修复博雅文化传媒和恒泰建材的数据缺失问题：
1. financial_metrics 表缺少这两家企业的数据（数据在 financial_metrics_item 中）
2. user_company_access 表缺少这两家企业的访问权限映射
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "fintax_ai.db"

COMPANIES_TO_FIX = [
    ("91110108MA01AAAAA1", "博雅文化传媒有限公司"),
    ("91320200MA02BBBBB2", "恒泰建材有限公司"),
]

# user1 (firm, id=2) should have access to all companies
# user2 (group, id=6) and user3 (group, id=7) also get access
USER_ACCESS = [
    (2, "91110108MA01AAAAA1"),
    (2, "91320200MA02BBBBB2"),
    (6, "91110108MA01AAAAA1"),
    (6, "91320200MA02BBBBB2"),
    (7, "91110108MA01AAAAA1"),
    (7, "91320200MA02BBBBB2"),
]


def fix_financial_metrics(conn: sqlite3.Connection) -> int:
    """Copy data from financial_metrics_item → financial_metrics for missing companies."""
    cur = conn.cursor()
    total_inserted = 0

    for tid, name in COMPANIES_TO_FIX:
        # Check current state
        cur.execute("SELECT COUNT(*) FROM financial_metrics WHERE taxpayer_id = ?", (tid,))
        before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM financial_metrics_item WHERE taxpayer_id = ?", (tid,))
        source_count = cur.fetchone()[0]

        if before > 0:
            print(f"  {name}: already has {before} rows in financial_metrics, skipping")
            continue

        if source_count == 0:
            print(f"  {name}: no data in financial_metrics_item, skipping")
            continue

        cur.execute("""
            INSERT OR IGNORE INTO financial_metrics
                (taxpayer_id, period_year, period_month, metric_category,
                 metric_code, metric_name, metric_value, metric_unit,
                 evaluation_level, calculated_at)
            SELECT taxpayer_id, period_year, period_month, metric_category,
                   metric_code, metric_name, metric_value, metric_unit,
                   evaluation_level, calculated_at
            FROM financial_metrics_item
            WHERE taxpayer_id = ?
        """, (tid,))

        inserted = cur.rowcount
        total_inserted += inserted
        print(f"  {name}: {inserted} rows inserted (source had {source_count})")

    conn.commit()
    return total_inserted


def fix_user_company_access(conn: sqlite3.Connection) -> int:
    """Add user_company_access entries for 博雅/恒泰."""
    cur = conn.cursor()
    added = 0

    for user_id, tid in USER_ACCESS:
        cur.execute(
            "SELECT COUNT(*) FROM user_company_access WHERE user_id = ? AND taxpayer_id = ?",
            (user_id, tid),
        )
        if cur.fetchone()[0] > 0:
            continue
        cur.execute(
            "INSERT INTO user_company_access (user_id, taxpayer_id) VALUES (?, ?)",
            (user_id, tid),
        )
        added += 1

    conn.commit()
    print(f"  user_company_access: {added} entries added")
    return added


def verify(conn: sqlite3.Connection):
    """Verify fixes."""
    cur = conn.cursor()
    print("\n=== Verification ===")

    for tid, name in COMPANIES_TO_FIX:
        cur.execute("SELECT COUNT(*) FROM financial_metrics WHERE taxpayer_id = ?", (tid,))
        fm = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM vw_financial_metrics WHERE taxpayer_id = ?", (tid,))
        vw = cur.fetchone()[0]
        print(f"  {name}: financial_metrics={fm}, vw_financial_metrics={vw}")

    cur.execute(
        "SELECT user_id, taxpayer_id FROM user_company_access WHERE taxpayer_id IN (?, ?) ORDER BY user_id",
        ("91110108MA01AAAAA1", "91320200MA02BBBBB2"),
    )
    rows = cur.fetchall()
    print(f"  user_company_access entries: {len(rows)}")
    for r in rows:
        print(f"    user_id={r[0]} → {r[1]}")


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    print("=" * 60)
    print("Phase 1: Fix missing data for 博雅文化传媒 / 恒泰建材")
    print("=" * 60)

    print("\n[1/2] Fixing financial_metrics...")
    fix_financial_metrics(conn)

    print("\n[2/2] Fixing user_company_access...")
    fix_user_company_access(conn)

    verify(conn)
    conn.close()

    print("\nDone.")


if __name__ == "__main__":
    main()
