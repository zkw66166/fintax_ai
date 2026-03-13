"""测试多年全年查询修复"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mvp_pipeline import run_pipeline

def test_multi_year_queries():
    """测试多年全年查询"""

    test_cases = [
        {
            "name": "多年全年营业收入比较（带'比较'关键词）",
            "query": "创智软件股份有限公司 2024年和2025年的全年营业收入比较分析",
            "expected_years": [2024, 2025],
            "expected_month": 12,
        },
        {
            "name": "多年全年营业收入对比（带'对比'关键词）",
            "query": "创智软件股份有限公司 请对比2024年和2025年的全年营业收入",
            "expected_years": [2024, 2025],
            "expected_month": 12,
        },
        {
            "name": "多年全年现金流对比",
            "query": "创智软件股份有限公司 2024年和2025年的全年经营活动现金流量净额对比",
            "expected_years": [2024, 2025],
            "expected_month": 12,
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试用例 {i}: {case['name']}")
        print(f"查询: {case['query']}")
        print(f"{'='*80}")

        result = run_pipeline(case['query'])

        if result['success']:
            sql = result.get('sql', '')
            rows = result.get('results', [])  # 修复：使用 'results' 而不是 'rows'

            print(f"\n✓ 查询成功")
            print(f"返回行数: {len(rows)}")

            # 检查SQL是否包含正确的年份过滤（跨域查询时sql可能为None）
            if sql:
                has_2024 = 'period_year=2024' in sql or 'period_year = 2024' in sql
                has_2025 = 'period_year=2025' in sql or 'period_year = 2025' in sql
                has_month_12 = 'period_month=12' in sql or 'period_month = 12' in sql
                has_time_range = "time_range = '本年累计'" in sql

                print(f"\nSQL检查:")
                print(f"  - 包含2024年过滤: {'✓' if has_2024 else '✗'}")
                print(f"  - 包含2025年过滤: {'✓' if has_2025 else '✗'}")
                print(f"  - 包含12月过滤: {'✓' if has_month_12 else '✗'}")
                print(f"  - 包含本年累计过滤: {'✓' if has_time_range else '✗'}")
            else:
                print(f"\nSQL检查: 跳过（跨域查询）")

            # 检查返回的数据是否包含两个年份
            years_in_result = set()
            for row in rows:
                if 'period_year' in row:
                    years_in_result.add(row['period_year'])

            print(f"\n数据检查:")
            print(f"  - 返回的年份: {sorted(years_in_result)}")
            print(f"  - 期望的年份: {case['expected_years']}")

            if sorted(years_in_result) == sorted(case['expected_years']):
                print(f"  - 结果: ✓ 正确返回两个年份的数据")
            else:
                print(f"  - 结果: ✗ 数据不完整")

            # 显示前3行数据
            print(f"\n前3行数据:")
            for j, row in enumerate(rows[:3], 1):
                print(f"  [{j}] {row}")

        else:
            print(f"\n✗ 查询失败")
            print(f"错误: {result.get('error', 'Unknown error')}")

if __name__ == '__main__':
    test_multi_year_queries()
