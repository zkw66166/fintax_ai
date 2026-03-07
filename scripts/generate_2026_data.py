"""
Generate realistic 2026 data for 4 companies across all financial tables.
Maintains cross-table consistency and follows data quality rules.

Companies to populate:
- TSE科技有限公司 (91310115MA2KZZZZZZ) - 一般纳税人, 企业会计准则
- 环球机械有限公司 (91330100MA2KWWWWWW) - 小规模纳税人, 小企业会计准则
- 创智软件股份有限公司 (91330200MA2KXXXXXX) - 一般纳税人, 企业会计准则
- 大华智能制造厂 (91330200MA2KYYYYYY) - 小规模纳税人, 小企业会计准则
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import random
import math
from datetime import datetime
from modules.db_utils import get_connection

# Company configurations
COMPANIES = {
    'TSE': {
        'taxpayer_id': '91310115MA2KZZZZZZ',
        'taxpayer_name': 'TSE科技有限公司',
        'taxpayer_type': '一般纳税人',
        'accounting_standard': '企业会计准则',
        'gaap_bs': 'ASBE',
        'gaap_pl': 'CAS',
        'gaap_cf': 'CAS',
        'base_revenue_monthly': 1200000,  # 月均营收
        'cost_ratio': 0.58,
        'growth_rate': 0.08,  # 8% annual growth
        'seasonal_pattern': [0.85, 0.90, 1.05, 1.10, 1.15, 1.20, 1.10, 1.05, 0.95, 0.90, 0.85, 0.90],
        'asset_base': 15000000,
        'employee_count': 120,
    },
    'HQ': {
        'taxpayer_id': '91330100MA2KWWWWWW',
        'taxpayer_name': '环球机械有限公司',
        'taxpayer_type': '小规模纳税人',
        'accounting_standard': '小企业会计准则',
        'gaap_bs': 'ASSE',
        'gaap_pl': 'SAS',
        'gaap_cf': 'SAS',
        'base_revenue_monthly': 180000,
        'cost_ratio': 0.68,
        'growth_rate': 0.05,
        'seasonal_pattern': [0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.85],
        'asset_base': 2500000,
        'employee_count': 35,
    },
    'CZ': {
        'taxpayer_id': '91330200MA2KXXXXXX',
        'taxpayer_name': '创智软件股份有限公司',
        'taxpayer_type': '一般纳税人',
        'accounting_standard': '企业会计准则',
        'gaap_bs': 'ASBE',
        'gaap_pl': 'CAS',
        'gaap_cf': 'CAS',
        'base_revenue_monthly': 950000,
        'cost_ratio': 0.52,
        'growth_rate': 0.12,  # High growth software company
        'seasonal_pattern': [0.80, 0.85, 0.95, 1.00, 1.10, 1.20, 1.15, 1.10, 1.05, 1.00, 0.95, 1.10],
        'asset_base': 12000000,
        'employee_count': 95,
    },
    'DH': {
        'taxpayer_id': '91330200MA2KYYYYYY',
        'taxpayer_name': '大华智能制造厂',
        'taxpayer_type': '小规模纳税人',
        'accounting_standard': '小企业会计准则',
        'gaap_bs': 'ASSE',
        'gaap_pl': 'SAS',
        'gaap_cf': 'SAS',
        'base_revenue_monthly': 220000,
        'cost_ratio': 0.65,
        'growth_rate': 0.06,
        'seasonal_pattern': [0.88, 0.92, 1.00, 1.08, 1.12, 1.18, 1.15, 1.10, 1.05, 1.00, 0.95, 0.92],
        'asset_base': 3200000,
        'employee_count': 42,
    },
}

def get_2025_baseline(conn, company_code):
    """Get 2025 Dec baseline data for growth calculation."""
    cfg = COMPANIES[company_code]
    tid = cfg['taxpayer_id']

    # Get 2025 Dec profit data
    pv = 'vw_profit_sas' if cfg['gaap_pl'] == 'SAS' else 'vw_profit_eas'
    profit_2025 = conn.execute(
        f"SELECT * FROM {pv} WHERE taxpayer_id = ? AND period_year = 2025 AND period_month = 12 AND time_range = '本年累计' LIMIT 1",
        (tid,)
    ).fetchone()

    # Get 2025 Dec balance sheet
    bv = 'vw_balance_sheet_sas' if cfg['gaap_bs'] == 'ASSE' else 'vw_balance_sheet_eas'
    bs_2025 = conn.execute(
        f"SELECT * FROM {bv} WHERE taxpayer_id = ? AND period_year = 2025 AND period_month = 12 LIMIT 1",
        (tid,)
    ).fetchone()

    return {
        'revenue_2025': profit_2025['operating_revenue'] if profit_2025 else cfg['base_revenue_monthly'] * 12,
        'assets_2025': bs_2025['assets_end'] if bs_2025 else cfg['asset_base'],
    }

# ============================================================================
# GENERATOR FUNCTIONS
# ============================================================================

def generate_balance_sheet(conn, cfg, year, month, assets_begin, revenue_monthly, net_profit_monthly):
    """Generate balance sheet data."""
    tid = cfg['taxpayer_id']
    gaap = cfg['gaap_bs']

    # Calculate ending assets (growing with profit)
    assets_end = assets_begin + net_profit_monthly * 0.5  # 50% retained

    # Asset structure (typical ratios)
    current_assets_end = assets_end * 0.60
    non_current_assets_end = assets_end * 0.40

    # Liability structure
    liabilities_end = assets_end * 0.45
    current_liabilities_end = liabilities_end * 0.70
    non_current_liabilities_end = liabilities_end * 0.30

    # Equity (balancing item)
    equity_end = assets_end - liabilities_end

    # Detailed current assets
    cash_end = current_assets_end * 0.25
    ar_end = current_assets_end * 0.35
    inventory_end = current_assets_end * 0.30
    other_current_end = current_assets_end * 0.10

    # Detailed non-current assets
    fixed_assets_end = non_current_assets_end * 0.60
    intangible_end = non_current_assets_end * 0.20
    other_non_current_end = non_current_assets_end * 0.20

    # Detailed current liabilities
    ap_end = current_liabilities_end * 0.50
    short_term_loans_end = current_liabilities_end * 0.30
    other_current_liab_end = current_liabilities_end * 0.20

    # Detailed equity
    share_capital_end = equity_end * 0.40
    retained_earnings_end = equity_end * 0.50
    capital_reserve_end = equity_end * 0.10

    now = datetime.now().isoformat()
    rows = []

    if gaap == 'ASBE':
        # ASBE (企业会计准则) items
        items = [
            # Assets
            ('ASSETS', assets_end, assets_begin),
            ('CURRENT_ASSETS', current_assets_end, current_assets_end * 0.95),
            ('CASH', cash_end, cash_end * 0.90),
            ('ACCOUNTS_RECEIVABLE', ar_end, ar_end * 0.95),
            ('INVENTORY', inventory_end, inventory_end * 0.98),
            ('OTHER_CURRENT_ASSETS', other_current_end, other_current_end),
            ('NON_CURRENT_ASSETS', non_current_assets_end, non_current_assets_end * 0.98),
            ('FIXED_ASSETS', fixed_assets_end, fixed_assets_end * 0.97),
            ('INTANGIBLE_ASSETS', intangible_end, intangible_end),
            ('OTHER_NON_CURRENT_ASSETS', other_non_current_end, other_non_current_end),
            # Liabilities
            ('LIABILITIES', liabilities_end, liabilities_end * 0.96),
            ('CURRENT_LIABILITIES', current_liabilities_end, current_liabilities_end * 0.95),
            ('ACCOUNTS_PAYABLE', ap_end, ap_end * 0.94),
            ('SHORT_TERM_LOANS', short_term_loans_end, short_term_loans_end),
            ('OTHER_CURRENT_LIABILITIES', other_current_liab_end, other_current_liab_end),
            ('NON_CURRENT_LIABILITIES', non_current_liabilities_end, non_current_liabilities_end),
            # Equity
            ('EQUITY', equity_end, equity_end * 0.97),
            ('SHARE_CAPITAL', share_capital_end, share_capital_end),
            ('CAPITAL_RESERVE', capital_reserve_end, capital_reserve_end),
            ('RETAINED_EARNINGS', retained_earnings_end, retained_earnings_end * 0.95),
        ]
    else:
        # ASSE (小企业会计准则) items
        items = [
            # Assets
            ('ASSETS', assets_end, assets_begin),
            ('CURRENT_ASSETS', current_assets_end, current_assets_end * 0.95),
            ('CASH', cash_end, cash_end * 0.90),
            ('ACCOUNTS_RECEIVABLE', ar_end, ar_end * 0.95),
            ('INVENTORY', inventory_end, inventory_end * 0.98),
            ('OTHER_CURRENT_ASSETS', other_current_end, other_current_end),
            ('NON_CURRENT_ASSETS', non_current_assets_end, non_current_assets_end * 0.98),
            ('FIXED_ASSETS_NET', fixed_assets_end, fixed_assets_end * 0.97),
            ('INTANGIBLE_ASSETS', intangible_end, intangible_end),
            ('OTHER_NON_CURRENT_ASSETS', other_non_current_end, other_non_current_end),
            # Liabilities
            ('LIABILITIES', liabilities_end, liabilities_end * 0.96),
            ('CURRENT_LIABILITIES', current_liabilities_end, current_liabilities_end * 0.95),
            ('ACCOUNTS_PAYABLE', ap_end, ap_end * 0.94),
            ('SHORT_TERM_LOANS', short_term_loans_end, short_term_loans_end),
            ('OTHER_CURRENT_LIABILITIES', other_current_liab_end, other_current_liab_end),
            ('NON_CURRENT_LIABILITIES', non_current_liabilities_end, non_current_liabilities_end),
            # Equity
            ('EQUITY', equity_end, equity_end * 0.97),
            ('SHARE_CAPITAL', share_capital_end, share_capital_end),
            ('CAPITAL_RESERVE', capital_reserve_end, capital_reserve_end),
            ('RETAINED_EARNINGS', retained_earnings_end, retained_earnings_end * 0.95),
        ]

    for item_code, ending, beginning in items:
        rows.append((
            tid, year, month, gaap, item_code,
            ending, beginning, 0, now, 'system', None, None, 1.0, 0
        ))

    conn.executemany(
        """INSERT OR IGNORE INTO fs_balance_sheet_item
        (taxpayer_id, period_year, period_month, gaap_type, item_code,
         ending_balance, beginning_balance, revision_no, submitted_at, etl_batch_id,
         source_doc_id, source_unit, etl_confidence, revision_no)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )

    return assets_end


    """Generate profit statement (income statement) data."""
    tid = cfg['taxpayer_id']
    gaap = cfg['gaap_pl']

    # Calculate YTD cumulative
    revenue_ytd = revenue_monthly * month
    cost_ytd = cost_monthly * month

    # Other expenses (proportional to revenue)
    selling_exp = revenue_monthly * 0.08
    admin_exp = revenue_monthly * 0.12
    rd_exp = revenue_monthly * 0.05 if cfg['taxpayer_type'] == '一般纳税人' else 0
    financial_exp = revenue_monthly * 0.02

    # Operating profit
    operating_profit_monthly = revenue_monthly - cost_monthly - selling_exp - admin_exp - rd_exp - financial_exp
    operating_profit_ytd = operating_profit_monthly * month

    # Net profit (after tax)
    net_profit_monthly = operating_profit_monthly * 0.75  # Assume 25% tax
    net_profit_ytd = net_profit_monthly * month

    # Insert monthly data (本期)
    rows = []
    if gaap == 'CAS':
        # CAS (企业会计准则) items
        items = [
            ('operating_revenue', revenue_monthly),
            ('operating_cost', cost_monthly),
            ('taxes_and_surcharges', revenue_monthly * 0.015),
            ('selling_expense', selling_exp),
            ('administrative_expense', admin_exp),
            ('rd_expense', rd_exp),
            ('financial_expense', financial_exp),
            ('operating_profit', operating_profit_monthly),
            ('total_profit', operating_profit_monthly),
            ('net_profit', net_profit_monthly),
        ]
    else:
        # SAS (小企业会计准则) items
        items = [
            ('operating_revenue', revenue_monthly),
            ('operating_cost', cost_monthly),
            ('taxes_and_surcharges', revenue_monthly * 0.015),
            ('selling_expense', selling_exp),
            ('administrative_expense', admin_exp),
            ('financial_expense', financial_exp),
            ('operating_profit', operating_profit_monthly),
            ('total_profit', operating_profit_monthly),
            ('net_profit', net_profit_monthly),
        ]

    now = datetime.now().isoformat()
    for item_code, value in items:
        rows.append((
            tid, year, month, gaap, item_code, '本期',
            value, value, 0, now, 'system', None, None, 1.0, 0
        ))

    # Insert YTD data (本年累计)
    for item_code, value_monthly in items:
        value_ytd = value_monthly * month
        rows.append((
            tid, year, month, gaap, item_code, '本年累计',
            value_ytd, value_ytd, 0, now, 'system', None, None, 1.0, 0
        ))

    # Batch insert
    conn.executemany(
        """INSERT OR IGNORE INTO fs_income_statement_item
        (taxpayer_id, period_year, period_month, gaap_type, item_code, time_range,
         ending_balance, current_amount, beginning_balance, submitted_at, etl_batch_id,
         source_doc_id, source_unit, etl_confidence, revision_no)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )

    return revenue_monthly, cost_monthly, net_profit_monthly

def main():
    """Main entry point."""
    print("="*80)
    print("2026 Data Generation Script")
    print("="*80)

    conn = get_connection()

    for code, cfg in COMPANIES.items():
        print(f"\nGenerating 2026 data for {cfg['taxpayer_name']}...")
        baseline = get_2025_baseline(conn, code)

        # Generate data for each month
        for month in range(1, 13):
            print(f"  Month {month}...")
            # TODO: Call generator functions
            pass

    conn.commit()
    conn.close()

    print("\n" + "="*80)
    print("Data generation complete!")
    print("="*80)

if __name__ == '__main__':
    main()
