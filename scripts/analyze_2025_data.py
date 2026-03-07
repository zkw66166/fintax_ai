"""Analyze 2025 data patterns for the 4 companies that need 2026 data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.db_utils import get_connection
import json

# Companies that need 2026 data
TARGET_COMPANIES = [
    '91310115MA2KZZZZZZ',  # TSE科技
    '91330100MA2KWWWWWW',  # 环球机械
    '91330200MA2KXXXXXX',  # 创智软件
    '91330200MA2KYYYYYY',  # 大华智能制造
]

def analyze_company(conn, taxpayer_id):
    """Analyze all data for one company."""
    # Get company info
    info = conn.execute(
        "SELECT * FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()

    result = {
        'taxpayer_id': taxpayer_id,
        'taxpayer_name': info['taxpayer_name'],
        'taxpayer_type': info['taxpayer_type'],
        'accounting_standard': info['accounting_standard'],
        'data_ranges': {}
    }

    # Check each table
    tables = [
        ('account_balance', 'period_year, period_month'),
        ('fs_balance_sheet_item', 'period_year, period_month, gaap_type'),
        ('fs_income_statement_item', 'period_year, period_month, gaap_type, time_range'),
        ('fs_cash_flow_item', 'period_year, period_month, gaap_type, time_range'),
        ('vat_return_general', 'period_year, period_month, time_range, item_type'),
        ('vat_return_small', 'period_year, period_month, time_range'),
        ('eit_annual_main', 'period_year'),
        ('eit_quarter_main', 'period_year, period_quarter'),
        ('inv_spec_purchase', 'period_year, period_month'),
        ('inv_spec_sales', 'period_year, period_month'),
        ('hr_employee_salary', 'period_year, period_month'),
    ]

    for table, group_cols in tables:
        try:
            # Count rows
            count = conn.execute(
                f"SELECT COUNT(*) as cnt FROM {table} WHERE taxpayer_id = ? AND period_year = 2025",
                (taxpayer_id,)
            ).fetchone()['cnt']

            # Get sample data
            sample = conn.execute(
                f"SELECT * FROM {table} WHERE taxpayer_id = ? AND period_year = 2025 LIMIT 3",
                (taxpayer_id,)
            ).fetchall()

            result['data_ranges'][table] = {
                'row_count_2025': count,
                'sample_columns': list(sample[0].keys()) if sample else [],
            }
        except Exception as e:
            result['data_ranges'][table] = {'error': str(e)}

    return result

def main():
    conn = get_connection()

    results = {}
    for tid in TARGET_COMPANIES:
        print(f"\nAnalyzing {tid}...")
        results[tid] = analyze_company(conn, tid)

    conn.close()

    # Print summary
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    for tid, data in results.items():
        print(f"\n{data['taxpayer_name']} ({data['taxpayer_type']}, {data['accounting_standard']})")
        print("-" * 80)
        for table, info in data['data_ranges'].items():
            if 'error' in info:
                print(f"  {table}: ERROR - {info['error']}")
            else:
                print(f"  {table}: {info['row_count_2025']} rows")

    # Save to JSON
    output_file = Path(__file__).parent / 'analysis_2025_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nFull analysis saved to: {output_file}")

if __name__ == '__main__':
    main()
