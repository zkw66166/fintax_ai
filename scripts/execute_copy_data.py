"""
执行数据复制SQL脚本并计算财务指标
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = "database/fintax_ai.db"
SQL_FILE = "scripts/copy_sample_data_simple.sql"

def execute_sql_file(db_path, sql_file):
    """执行SQL文件"""
    print(f"执行SQL脚本: {sql_file}")
    print("=" * 70)

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("✓ SQL脚本执行成功")
        return True
    except Exception as e:
        print(f"✗ SQL脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def calculate_financial_metrics(db_path, taxpayer_id, taxpayer_name):
    """计算并插入财务指标"""
    print(f"\n计算财务指标: {taxpayer_name}")
    print("-" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取所有期间
    cursor.execute("""
        SELECT DISTINCT period_year, period_month
        FROM fs_balance_sheet_item
        WHERE taxpayer_id = ?
        ORDER BY period_year, period_month
    """, (taxpayer_id,))

    periods = cursor.fetchall()
    count = 0

    for year, month in periods:
        # 获取资产负债表数据
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

        # 获取利润表数据
        cursor.execute("""
            SELECT item_code, current_amount, cumulative_amount
            FROM fs_income_statement_item
            WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
            AND revision_no = (
                SELECT MAX(revision_no) FROM fs_income_statement_item
                WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?
            )
        """, (taxpayer_id, year, month, taxpayer_id, year, month))

        is_data = {row[0]: {'current': row[1], 'cumulative': row[2]} for row in cursor.fetchall()}

        # 计算指标
        metrics = {}

        # 资产负债率
        total_assets = bs_data.get('100', 0) or 0
        total_liabilities = bs_data.get('300', 0) or 0
        if total_assets > 0:
            metrics['asset_liability_ratio'] = round(total_liabilities / total_assets, 4)

        # 流动比率
        current_assets = bs_data.get('1', 0) or 0
        current_liabilities = bs_data.get('3', 0) or 0
        if current_liabilities > 0:
            metrics['current_ratio'] = round(current_assets / current_liabilities, 4)

        # 速动比率
        inventory = bs_data.get('103', 0) or 0
        if current_liabilities > 0:
            metrics['quick_ratio'] = round((current_assets - inventory) / current_liabilities, 4)

        # 毛利率
        revenue = is_data.get('1', {}).get('current', 0) or 0
        cost = is_data.get('2', {}).get('current', 0) or 0
        if revenue > 0:
            metrics['gross_margin'] = round((revenue - cost) / revenue, 4)

        # 净利率
        net_profit = is_data.get('6', {}).get('current', 0) or 0
        if revenue > 0:
            metrics['net_margin'] = round(net_profit / revenue, 4)

        # ROE
        total_equity = bs_data.get('5', 0) or 0
        if total_equity > 0:
            metrics['roe'] = round(net_profit / total_equity, 4)

        # ROA
        if total_assets > 0:
            metrics['roa'] = round(net_profit / total_assets, 4)

        if metrics:
            # 插入financial_metrics
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

            # 插入financial_metrics_item
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

    conn.commit()
    conn.close()

    print(f"✓ 已计算 {count} 个期间的财务指标")

def verify_data(db_path):
    """验证数据"""
    print("\n" + "=" * 70)
    print("数据验证")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    companies = [
        ('91110108MA01AAAAA1', '博雅文化传媒有限公司'),
        ('91320200MA02BBBBB2', '恒泰建材有限公司'),
    ]

    for taxpayer_id, name in companies:
        print(f"\n{name} ({taxpayer_id}):")

        # VAT数据
        cursor.execute("""
            SELECT COUNT(*) FROM vat_return_small WHERE taxpayer_id = ?
            UNION ALL
            SELECT COUNT(*) FROM vat_return_general WHERE taxpayer_id = ?
        """, (taxpayer_id, taxpayer_id))
        vat_counts = [row[0] for row in cursor.fetchall()]
        vat_count = sum(vat_counts)
        print(f"  VAT数据: {vat_count} 条")

        # 资产负债表
        cursor.execute("""
            SELECT COUNT(DISTINCT period_year * 100 + period_month)
            FROM fs_balance_sheet_item WHERE taxpayer_id = ?
        """, (taxpayer_id,))
        bs_count = cursor.fetchone()[0]
        print(f"  资产负债表: {bs_count} 个期间")

        # 利润表
        cursor.execute("""
            SELECT COUNT(DISTINCT period_year * 100 + period_month)
            FROM fs_income_statement_item WHERE taxpayer_id = ?
        """, (taxpayer_id,))
        is_count = cursor.fetchone()[0]
        print(f"  利润表: {is_count} 个期间")

        # 现金流量表
        cursor.execute("""
            SELECT COUNT(DISTINCT period_year * 100 + period_month)
            FROM fs_cash_flow_item WHERE taxpayer_id = ?
        """, (taxpayer_id,))
        cf_count = cursor.fetchone()[0]
        print(f"  现金流量表: {cf_count} 个期间")

        # 财务指标
        cursor.execute("""
            SELECT COUNT(*) FROM financial_metrics WHERE taxpayer_id = ?
        """, (taxpayer_id,))
        fm_count = cursor.fetchone()[0]
        print(f"  财务指标: {fm_count} 个期间")

        if vat_count > 0 and bs_count > 0 and is_count > 0:
            print(f"  ✓ 数据完整")
        else:
            print(f"  ✗ 数据不完整")

    conn.close()

def main():
    """主函数"""
    print("=" * 70)
    print("为新增公司复制示例数据并计算财务指标")
    print("=" * 70)

    # 执行SQL脚本
    if not execute_sql_file(DB_PATH, SQL_FILE):
        print("\n✗ SQL脚本执行失败，终止")
        return 1

    # 计算财务指标
    companies = [
        ('91110108MA01AAAAA1', '博雅文化传媒有限公司'),
        ('91320200MA02BBBBB2', '恒泰建材有限公司'),
    ]

    for taxpayer_id, name in companies:
        calculate_financial_metrics(DB_PATH, taxpayer_id, name)

    # 验证数据
    verify_data(DB_PATH)

    print("\n" + "=" * 70)
    print("✓ 所有操作完成")
    print("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())
