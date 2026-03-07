"""Verify 2026 data was inserted."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.db_utils import get_connection

conn = get_connection()

companies = [
    ('91310115MA2KZZZZZZ', 'TSE科技'),
    ('91330100MA2KWWWWWW', '环球机械'),
    ('91330200MA2KXXXXXX', '创智软件'),
    ('91330200MA2KYYYYYY', '大华智能制造'),
]

print("2026 Data Verification:")
print("="*80)

for tid, name in companies:
    print(f"\n{name} ({tid}):")

    tables = [
        'account_balance',
        'fs_balance_sheet_item',
        'fs_income_statement_item',
        'fs_cash_flow_item',
        'vat_return_general',
        'vat_return_small',
        'inv_spec_purchase',
        'inv_spec_sales',
    ]

    for table in tables:
        count = conn.execute(
            f"SELECT COUNT(*) as cnt FROM {table} WHERE taxpayer_id = ? AND period_year = 2026",
            (tid,)
        ).fetchone()['cnt']
        if count > 0:
            print(f"  {table}: {count} rows")

    # EIT
    eit_annual = conn.execute(
        "SELECT COUNT(*) as cnt FROM eit_annual_filing WHERE taxpayer_id = ? AND period_year = 2026",
        (tid,)
    ).fetchone()['cnt']
    eit_quarter = conn.execute(
        "SELECT COUNT(*) as cnt FROM eit_quarter_filing WHERE taxpayer_id = ? AND period_year = 2026",
        (tid,)
    ).fetchone()['cnt']
    print(f"  eit_annual_filing: {eit_annual} rows")
    print(f"  eit_quarter_filing: {eit_quarter} rows")

conn.close()
