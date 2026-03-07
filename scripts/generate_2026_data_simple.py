"""
Generate 2026 data for 4 companies (TSE, HQ, CZ, DH).
Simplified approach: copy 2025 structure and apply growth factors.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from datetime import datetime
from modules.db_utils import get_connection

# Target companies
COMPANIES = {
    'TSE': {
        'id': '91310115MA2KZZZZZZ',
        'name': 'TSE科技有限公司',
        'type': '一般纳税人',
        'std': '企业会计准则',
        'growth': 1.08,  # 8% growth
    },
    'HQ': {
        'id': '91330100MA2KWWWWWW',
        'name': '环球机械有限公司',
        'type': '小规模纳税人',
        'std': '小企业会计准则',
        'growth': 1.05,
    },
    'CZ': {
        'id': '91330200MA2KXXXXXX',
        'name': '创智软件股份有限公司',
        'type': '一般纳税人',
        'std': '企业会计准则',
        'growth': 1.12,
    },
    'DH': {
        'id': '91330200MA2KYYYYYY',
        'name': '大华智能制造厂',
        'type': '小规模纳税人',
        'std': '小企业会计准则',
        'growth': 1.06,
    },
}

def copy_and_scale_table(conn, table, tid, growth, year_from=2025, year_to=2026):
    """Copy data from 2025 to 2026 with growth factor."""
    # Get 2025 data
    rows_2025 = conn.execute(
        f"SELECT * FROM {table} WHERE taxpayer_id = ? AND period_year = ?",
        (tid, year_from)
    ).fetchall()

    if not rows_2025:
        print(f"    No 2025 data in {table}")
        return 0

    # Get column names
    columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]

    # Numeric columns to scale
    numeric_cols = [
        'ending_balance', 'beginning_balance', 'current_amount',
        'debit_amount', 'credit_amount', 'debit_balance', 'credit_balance',
        'amount', 'tax_amount', 'total_amount', 'quantity', 'unit_price',
        'income_wage', 'income_bonus_monthly', 'total_income', 'net_salary',
        'gross_salary', 'taxable_income', 'tax_payable',
        # EIT fields
        'revenue', 'cost', 'total_profit', 'taxable_income', 'tax_payable',
        'actual_tax_payable', 'final_tax_payable_or_refund',
        # VAT fields
        'sales_taxable_rate', 'output_tax', 'input_tax', 'total_tax_payable',
        'tax_due_total', 'sales_3percent', 'sales_5percent',
    ]

    inserted = 0
    for row in rows_2025:
        row_dict = dict(row)

        # Update year
        row_dict['period_year'] = year_to

        # Scale numeric fields
        for col in numeric_cols:
            if col in row_dict and row_dict[col] is not None:
                row_dict[col] = round(row_dict[col] * growth, 2)

        # Update timestamps
        if 'submitted_at' in row_dict:
            row_dict['submitted_at'] = f"{year_to}-{row_dict.get('period_month', 1):02d}-15"
        if 'updated_at' in row_dict:
            row_dict['updated_at'] = datetime.now().isoformat()

        # Build INSERT OR IGNORE
        placeholders = ','.join(['?'] * len(columns))
        values = [row_dict.get(col) for col in columns]

        try:
            conn.execute(
                f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                values
            )
            inserted += 1
        except Exception as e:
            print(f"      Error inserting into {table}: {e}")

    return inserted

def generate_for_company(conn, code, cfg):
    """Generate 2026 data for one company."""
    print(f"\n{cfg['name']} ({code}):")
    tid = cfg['id']
    growth = cfg['growth']

    tables = [
        'account_balance',
        'fs_balance_sheet_item',
        'fs_income_statement_item',
        'fs_cash_flow_item',
        'inv_spec_purchase',
        'inv_spec_sales',
    ]

    # VAT table depends on taxpayer type
    if cfg['type'] == '一般纳税人':
        tables.append('vat_return_general')
    else:
        tables.append('vat_return_small')

    total = 0
    for table in tables:
        count = copy_and_scale_table(conn, table, tid, growth)
        print(f"  {table}: {count} rows")
        total += count

    # EIT tables (different structure - need special handling)
    count_eit = generate_eit_data(conn, tid, cfg, growth)
    print(f"  EIT tables: {count_eit} rows")
    total += count_eit

    return total

def generate_eit_data(conn, tid, cfg, growth):
    """Generate EIT data for 2026."""
    inserted = 0

    # Annual EIT
    annual_2025 = conn.execute(
        """SELECT eab.*, eam.*, eaf.period_year
        FROM eit_annual_filing eaf
        JOIN eit_annual_basic_info eab ON eaf.filing_id = eab.filing_id
        JOIN eit_annual_main eam ON eaf.filing_id = eam.filing_id
        WHERE eaf.taxpayer_id = ? AND eaf.period_year = 2025""",
        (tid,)
    ).fetchone()

    if annual_2025:
        fid_2026 = f"{tid}_2026_0"

        # Check if already exists
        exists = conn.execute(
            "SELECT 1 FROM eit_annual_filing WHERE filing_id = ?", (fid_2026,)
        ).fetchone()

        if not exists:
            # Insert filing
            conn.execute(
                """INSERT INTO eit_annual_filing
                (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
                 preparer, submitted_at, etl_batch_id, etl_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fid_2026, tid, 2026, 0, '元', '系统', '2027-05-15', 'ETL_2026', 1.0)
            )

            # Insert basic info
            conn.execute(
                """INSERT INTO eit_annual_basic_info
                (filing_id, tax_return_type_code, asset_avg, employee_avg,
                 industry_code, restricted_or_prohibited, small_micro_enterprise,
                 listed_company, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fid_2026, 'A',
                 round(annual_2025['asset_avg'] * growth) if annual_2025['asset_avg'] else None,
                 annual_2025['employee_avg'],
                 annual_2025['industry_code'], 0, 1, '否',
                 datetime.now().isoformat())
            )

            # Insert main (scale financial fields)
            revenue = round(annual_2025['revenue'] * growth) if annual_2025['revenue'] else 0
            cost = round(annual_2025['cost'] * growth) if annual_2025['cost'] else 0
            total_profit = round(annual_2025['total_profit'] * growth) if annual_2025['total_profit'] else 0
            taxable = max(total_profit, 0)
            tax_rate = annual_2025['tax_rate'] or 0.25
            tax_payable = round(taxable * tax_rate)

            conn.execute(
                """INSERT INTO eit_annual_main
                (filing_id, revenue, cost, total_profit, taxable_income,
                 tax_rate, tax_payable, actual_tax_payable,
                 final_tax_payable_or_refund, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (fid_2026, revenue, cost, total_profit, taxable,
                 tax_rate, tax_payable, tax_payable, tax_payable,
                 datetime.now().isoformat())
            )
            inserted += 3

    # Quarterly EIT
    for q in range(1, 5):
        quarter_2025 = conn.execute(
            """SELECT eqf.*, eqm.*
            FROM eit_quarter_filing eqf
            JOIN eit_quarter_main eqm ON eqf.filing_id = eqm.filing_id
            WHERE eqf.taxpayer_id = ? AND eqf.period_year = 2025 AND eqf.period_quarter = ?""",
            (tid, q)
        ).fetchone()

        if quarter_2025:
            fid_2026 = f"{tid}_2026Q{q}_0"

            exists = conn.execute(
                "SELECT 1 FROM eit_quarter_filing WHERE filing_id = ?", (fid_2026,)
            ).fetchone()

            if not exists:
                conn.execute(
                    """INSERT INTO eit_quarter_filing
                    (filing_id, taxpayer_id, period_year, period_quarter, revision_no,
                     amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fid_2026, tid, 2026, q, 0, '元', '系统',
                     f'2026-{q*3:02d}-20', 'ETL_2026', 1.0)
                )

                revenue = round(quarter_2025['revenue'] * growth) if quarter_2025['revenue'] else 0
                cost = round(quarter_2025['cost'] * growth) if quarter_2025['cost'] else 0
                profit = round(quarter_2025['total_profit'] * growth) if quarter_2025['total_profit'] else 0
                tax_rate = quarter_2025['tax_rate'] or 0.25
                tax = round(max(profit, 0) * tax_rate)

                conn.execute(
                    """INSERT INTO eit_quarter_main
                    (filing_id, revenue, cost, total_profit, tax_rate,
                     tax_payable, final_tax_payable_or_refund, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fid_2026, revenue, cost, profit, tax_rate, tax, tax,
                     datetime.now().isoformat())
                )
                inserted += 2

    return inserted

def main():
    print("="*80)
    print("2026 Data Generation (Simplified Copy-and-Scale Approach)")
    print("="*80)

    conn = get_connection()

    grand_total = 0
    for code, cfg in COMPANIES.items():
        total = generate_for_company(conn, code, cfg)
        grand_total += total

    conn.commit()
    conn.close()

    print("\n" + "="*80)
    print(f"Total rows inserted: {grand_total}")
    print("="*80)

if __name__ == '__main__':
    main()
