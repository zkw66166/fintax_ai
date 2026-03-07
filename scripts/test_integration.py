"""Test system integration with 2026 data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.db_utils import get_connection

conn = get_connection()

print("="*80)
print("System Integration Test - 2026 Data")
print("="*80)

# Test views
views = [
    'vw_profit_eas',
    'vw_profit_sas',
    'vw_balance_sheet_eas',
    'vw_balance_sheet_sas',
    'vw_cash_flow_eas',
    'vw_cash_flow_sas',
    'vw_vat_return_general',
    'vw_vat_return_small',
    'vw_eit_annual_main',
    'vw_eit_quarter_main',
    'vw_financial_metrics',
]

companies = [
    ('91310115MA2KZZZZZZ', 'TSE科技'),
    ('91330100MA2KWWWWWW', '环球机械'),
    ('91330200MA2KXXXXXX', '创智软件'),
    ('91330200MA2KYYYYYY', '大华智能制造'),
]

print("\nView Data Availability:")
print("-"*80)

for view in views:
    print(f"\n{view}:")
    for tid, name in companies:
        count = conn.execute(
            f"SELECT COUNT(*) as cnt FROM {view} WHERE taxpayer_id = ? AND period_year = 2026",
            (tid,)
        ).fetchone()['cnt']
        if count > 0:
            print(f"  {name}: {count} rows")

# Test financial metrics
print("\n\nFinancial Metrics (2026):")
print("-"*80)

for tid, name in companies:
    print(f"\n{name}:")
    metrics = conn.execute(
        """SELECT period_type, COUNT(*) as cnt
        FROM financial_metrics_item
        WHERE taxpayer_id = ? AND period_year = 2026
        GROUP BY period_type""",
        (tid,)
    ).fetchall()
    for m in metrics:
        print(f"  {m['period_type']}: {m['cnt']} metrics")

# Sample query test
print("\n\nSample Query Test:")
print("-"*80)

for tid, name in companies:
    print(f"\n{name} - 2026年12月:")

    # Profit
    profit = conn.execute(
        """SELECT operating_revenue, operating_cost, net_profit
        FROM vw_profit_eas
        WHERE taxpayer_id = ? AND period_year = 2026 AND period_month = 12
        AND time_range = '本年累计'
        LIMIT 1""",
        (tid,)
    ).fetchone()

    if not profit:
        profit = conn.execute(
            """SELECT operating_revenue, operating_cost, net_profit
            FROM vw_profit_sas
            WHERE taxpayer_id = ? AND period_year = 2026 AND period_month = 12
            AND time_range = '本年累计'
            LIMIT 1""",
            (tid,)
        ).fetchone()

    if profit:
        print(f"  营业收入: {profit['operating_revenue']:,.2f}")
        print(f"  营业成本: {profit['operating_cost']:,.2f}")
        print(f"  净利润: {profit['net_profit']:,.2f}")

    # Balance sheet
    bs = conn.execute(
        """SELECT assets_end, liabilities_end, equity_end
        FROM vw_balance_sheet_eas
        WHERE taxpayer_id = ? AND period_year = 2026 AND period_month = 12
        LIMIT 1""",
        (tid,)
    ).fetchone()

    if not bs:
        bs = conn.execute(
            """SELECT assets_end, liabilities_end, equity_end
            FROM vw_balance_sheet_sas
            WHERE taxpayer_id = ? AND period_year = 2026 AND period_month = 12
            LIMIT 1""",
            (tid,)
        ).fetchone()

    if bs:
        print(f"  资产总计: {bs['assets_end']:,.2f}")
        print(f"  负债总计: {bs['liabilities_end']:,.2f}")
        print(f"  所有者权益: {bs['equity_end']:,.2f}")

conn.close()

print("\n" + "="*80)
print("Integration test complete!")
print("="*80)
