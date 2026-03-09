"""
Update financial metrics and validate data quality for new taxpayers
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.data_quality import DataQualityChecker

DB_PATH = "database/fintax_ai.db"

NEW_TAXPAYERS = [
    "91110108MA01AAAAA1",  # 博雅文化传媒
    "91320200MA02BBBBB2",  # 恒泰建材
]


def calculate_financial_metrics(conn, taxpayer_id, year, month):
    """Calculate financial metrics for a given period"""
    cursor = conn.cursor()

    # Get balance sheet data
    cursor.execute("""
        SELECT item_code, ending_balance
        FROM fs_balance_sheet_item
        WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
        AND revision_no = (
            SELECT MAX(revision_no) FROM fs_balance_sheet_item
            WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
        )
    """, (taxpayer_id, year, month, taxpayer_id, year, month))

    bs_data = {row[0]: row[1] for row in cursor.fetchall()}

    # Get income statement data
    cursor.execute("""
        SELECT item_code, current_amount, cumulative_amount
        FROM fs_income_statement_item
        WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
        AND revision_no = (
            SELECT MAX(revision_no) FROM fs_income_statement_item
            WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
        )
    """, (taxpayer_id, year, month, taxpayer_id, year, month))

    is_data = {row[0]: {'current': row[1], 'ytd': row[2]} for row in cursor.fetchall()}

    # Calculate metrics
    metrics = {}

    # Asset-liability ratio
    total_assets = bs_data.get('100', 0)
    total_liabilities = bs_data.get('300', 0)
    if total_assets > 0:
        metrics['asset_liability_ratio'] = round(total_liabilities / total_assets, 4)

    # Current ratio
    current_assets = bs_data.get('1', 0)
    current_liabilities = bs_data.get('3', 0)
    if current_liabilities > 0:
        metrics['current_ratio'] = round(current_assets / current_liabilities, 4)

    # Quick ratio
    inventory = bs_data.get('103', 0)
    if current_liabilities > 0:
        metrics['quick_ratio'] = round((current_assets - inventory) / current_liabilities, 4)

    # Gross margin
    revenue = is_data.get('1', {}).get('current', 0)
    cost = is_data.get('2', {}).get('current', 0)
    if revenue > 0:
        metrics['gross_margin'] = round((revenue - cost) / revenue, 4)

    # Net margin
    net_profit = is_data.get('6', {}).get('current', 0)
    if revenue > 0:
        metrics['net_margin'] = round(net_profit / revenue, 4)

    # ROE
    total_equity = bs_data.get('5', 0)
    if total_equity > 0:
        metrics['roe'] = round(net_profit / total_equity, 4)

    # ROA
    if total_assets > 0:
        metrics['roa'] = round(net_profit / total_assets, 4)

    return metrics


def update_financial_metrics_table(conn):
    """Update financial_metrics table for new taxpayers"""
    cursor = conn.cursor()

    print("\nUpdating financial_metrics table...")

    for taxpayer_id in NEW_TAXPAYERS:
        # Get taxpayer info
        cursor.execute("""
            SELECT taxpayer_name, taxpayer_type, accounting_standard
            FROM taxpayer_info WHERE taxpayer_id = ?
        """, (taxpayer_id,))

        taxpayer_info = cursor.fetchone()
        if not taxpayer_info:
            print(f"  ✗ Taxpayer {taxpayer_id} not found")
            continue

        taxpayer_name = taxpayer_info[0]
        print(f"\n  Processing: {taxpayer_name}")

        # Get all periods
        cursor.execute("""
            SELECT DISTINCT period_year, period_month
            FROM fs_balance_sheet_item
            WHERE taxpayer_id = ?
            ORDER BY period_year, period_month
        """, (taxpayer_id,))

        periods = cursor.fetchall()
        count = 0

        for year, month in periods:
            metrics = calculate_financial_metrics(conn, taxpayer_id, year, month)

            if metrics:
                # Insert into financial_metrics
                cursor.execute("""
                    INSERT OR REPLACE INTO financial_metrics (
                        taxpayer_id, period_year, period_month,
                        asset_liability_ratio, current_ratio, quick_ratio,
                        gross_margin, net_margin, roe, roa,
                        revision_no, submitted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    taxpayer_id, year, month,
                    metrics.get('asset_liability_ratio'),
                    metrics.get('current_ratio'),
                    metrics.get('quick_ratio'),
                    metrics.get('gross_margin'),
                    metrics.get('net_margin'),
                    metrics.get('roe'),
                    metrics.get('roa'),
                    1
                ))

                # Insert into financial_metrics_item
                for metric_code, value in metrics.items():
                    if value is not None:
                        cursor.execute("""
                            INSERT OR REPLACE INTO financial_metrics_item (
                                taxpayer_id, period_year, period_month,
                                metric_code, metric_value,
                                revision_no, submitted_at
                            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                        """, (taxpayer_id, year, month, metric_code, value, 1))

                count += 1

        print(f"    ✓ Updated {count} periods")

    conn.commit()
    print("\n  ✓ Financial metrics updated successfully")


def validate_data_quality(conn):
    """Run data quality checks on new taxpayers"""
    print("\n" + "=" * 70)
    print("Running data quality validation...")
    print("=" * 70)

    checker = DataQualityChecker(DB_PATH)

    for taxpayer_id in NEW_TAXPAYERS:
        # Get taxpayer info
        cursor = conn.cursor()
        cursor.execute("""
            SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?
        """, (taxpayer_id,))

        taxpayer_name = cursor.fetchone()[0]

        print(f"\n{'='*70}")
        print(f"Validating: {taxpayer_name} ({taxpayer_id})")
        print(f"{'='*70}")

        # Run checks for 2025 (full year)
        result = checker.check_company(taxpayer_id, 2025)

        # Print summary
        print(f"\nOverall Pass Rate: {result.overall_pass_rate:.1%}")
        print(f"Total Checks: {result.total_checks}")
        print(f"Passed: {result.passed_checks}")
        print(f"Failed: {result.failed_checks}")

        # Print category breakdown
        print("\nCategory Breakdown:")
        for category, cat_result in result.category_results.items():
            status = "✓" if cat_result.pass_rate == 1.0 else "✗"
            print(f"  {status} {category}: {cat_result.pass_rate:.1%} "
                  f"({cat_result.passed}/{cat_result.total})")

        # Print failed checks
        if result.failed_checks > 0:
            print("\nFailed Checks:")
            for domain_result in result.domain_results.values():
                for check in domain_result.checks:
                    if not check.passed:
                        print(f"  ✗ [{check.rule_id}] {check.message}")
                        if check.details:
                            print(f"    Details: {check.details}")

    print("\n" + "=" * 70)
    print("✓ Data quality validation completed")
    print("=" * 70)


def main():
    """Main execution"""
    print("=" * 70)
    print("Update Financial Metrics and Validate Data Quality")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Update financial metrics
        update_financial_metrics_table(conn)

        # Validate data quality
        validate_data_quality(conn)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("✓ All operations completed")
    print("=" * 70)


if __name__ == "__main__":
    main()
