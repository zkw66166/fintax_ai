#!/usr/bin/env python
"""测试修复后的混合管线"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mvp_pipeline import run_pipeline

def test_query():
    query = "TSE科技有限公司 比较2024与2025年末资产负债率、利润率"
    print(f"测试查询: {query}")
    print("=" * 60)

    result = run_pipeline(query)

    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  成功: {result.get('success')}")

    if result.get('cross_domain_summary'):
        print(f"  摘要: {result.get('cross_domain_summary')}")

    if result.get('error'):
        print(f"  错误: {result.get('error')}")

    if result.get('results'):
        print(f"  结果行数: {len(result.get('results'))}")
        print("\n  数据预览:")
        for i, row in enumerate(result.get('results')[:5], 1):
            print(f"    {i}. {row}")

    # 检查是否包含两个指标
    if result.get('success') and result.get('results'):
        results = result.get('results')
        has_debt_ratio = any('资产负债率' in str(row) for row in results)
        has_profit_margin = any('净利率' in str(row) or '利润率' in str(row) for row in results)

        print(f"\n  包含资产负债率: {has_debt_ratio}")
        print(f"  包含利润率: {has_profit_margin}")

        if has_debt_ratio and has_profit_margin:
            print("\n✓ 测试通过：两个指标都已返回")
        else:
            print("\n✗ 测试失败：缺少指标")

if __name__ == '__main__':
    test_query()
