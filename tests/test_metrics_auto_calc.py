#!/usr/bin/env python
"""测试修改示例数据后是否自动计算financial_metrics"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import DB_PATH

def check_metrics_exist(taxpayer_id='91310000MA1FL8XQ30'):
    """检查指定纳税人的财务指标是否存在"""
    conn = sqlite3.connect(DB_PATH)

    # 检查 financial_metrics 表
    cursor = conn.execute(
        "SELECT COUNT(*) FROM financial_metrics WHERE taxpayer_id = ?",
        (taxpayer_id,)
    )
    v1_count = cursor.fetchone()[0]

    # 检查 financial_metrics_item 表
    cursor = conn.execute(
        "SELECT COUNT(*) FROM financial_metrics_item WHERE taxpayer_id = ?",
        (taxpayer_id,)
    )
    v2_count = cursor.fetchone()[0]

    # 获取样本数据
    cursor = conn.execute(
        "SELECT period_year, period_month, metric_code, metric_value "
        "FROM financial_metrics_item WHERE taxpayer_id = ? "
        "ORDER BY period_year DESC, period_month DESC LIMIT 5",
        (taxpayer_id,)
    )
    samples = cursor.fetchall()

    conn.close()

    print(f"纳税人: {taxpayer_id}")
    print(f"  financial_metrics (v1) 记录数: {v1_count}")
    print(f"  financial_metrics_item (v2) 记录数: {v2_count}")

    if samples:
        print(f"\n  最新5条记录:")
        for row in samples:
            print(f"    {row[0]}-{row[1]:02d} | {row[2]} = {row[3]}")
    else:
        print(f"\n  ⚠️  没有找到财务指标数据")

    return v1_count > 0 and v2_count > 0

if __name__ == '__main__':
    print("=" * 60)
    print("检查财务指标数据是否存在")
    print("=" * 60)

    # 检查原始2个公司
    print("\n1. 华兴科技（原始数据）:")
    hx_ok = check_metrics_exist('91310000MA1FL8XQ30')

    print("\n2. 鑫源贸易（原始数据）:")
    xy_ok = check_metrics_exist('92440300MA5EQXL17P')

    # 检查新增4个公司
    print("\n3. 创智软件（新增数据）:")
    cz_ok = check_metrics_exist('91330200MA2KXXXXXX')

    print("\n4. TSE科技（新增数据）:")
    tse_ok = check_metrics_exist('91310115MA2KZZZZZZ')

    print("\n" + "=" * 60)
    print("总结:")
    print("=" * 60)

    if all([hx_ok, xy_ok, cz_ok, tse_ok]):
        print("✓ 所有公司都有财务指标数据")
    else:
        print("✗ 部分公司缺少财务指标数据")
        print("\n建议手动运行:")
        print("  python database/calculate_metrics.py")
        print("  python database/calculate_metrics_v2.py")
