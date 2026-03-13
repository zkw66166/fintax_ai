"""
端到端测试：多年年末查询完整管线
End-to-end test for multi-year year-end queries through full pipeline

测试目标：
1. 验证实体识别正确
2. 验证SQL生成正确（包含所有年份的12月）
3. 验证返回数据正确（2个月的数据）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mvp_pipeline import run_pipeline

# 数据库路径
DB_PATH = "database/fintax_ai.db"


def test_e2e_multi_year_end_dash_with_mei():
    """端到端测试：\"2024-2025每年末\""""
    query = "TSE科技2024-2025每年末的总资产和总负债"
    print(f"\n{'='*60}")
    print(f"测试1: {query}")
    print('='*60)

    result = run_pipeline(query, DB_PATH)

    print(f"\nSQL: {result.get('sql', 'N/A')[:300]}...")

    # 验证SQL包含多年年末条件
    sql = result.get('sql', '')
    assert 'period_year IN (2024, 2025)' in sql or '((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))' in sql, \
        f"SQL应包含多年年末条件，实际SQL: {sql}"
    assert 'period_month = 12' in sql or 'period_month=12' in sql, \
        f"SQL应包含 period_month=12 条件，实际SQL: {sql}"

    # 验证返回数据
    data = result.get('results', [])
    print(f"\n返回数据行数: {len(data)}")
    if data:
        print(f"第一行: {data[0]}")
        if len(data) > 1:
            print(f"第二行: {data[1]}")

    # 应该返回2行数据（2024.12 和 2025.12）
    assert len(data) == 2, f"期望返回2行数据（2024.12和2025.12），实际返回{len(data)}行"

    # 验证年份和月份
    years = [row.get('period_year') for row in data]
    months = [row.get('period_month') for row in data]
    assert set(years) == {2024, 2025}, f"期望年份为2024和2025，实际 {years}"
    assert all(m == 12 for m in months), f"期望所有月份为12，实际 {months}"

    print("✅ 测试通过")


def test_e2e_multi_year_end_comma():
    """端到端测试：\"2024、2025年末\""""
    query = "TSE科技2024、2025年末的总资产和总负债"
    print(f"\n{'='*60}")
    print(f"测试2: {query}")
    print('='*60)

    result = run_pipeline(query, DB_PATH)

    print(f"\nSQL: {result.get('sql', 'N/A')[:300]}...")

    sql = result.get('sql', '')
    assert 'period_year IN (2024, 2025)' in sql or '((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))' in sql, \
        f"SQL应包含多年年末条件，实际SQL: {sql}"

    data = result.get('results', [])
    print(f"\n返回数据行数: {len(data)}")

    assert len(data) == 2, f"期望返回2行数据（2024.12和2025.12），实际返回{len(data)}行"

    years = [row.get('period_year') for row in data]
    months = [row.get('period_month') for row in data]
    assert set(years) == {2024, 2025}, f"期望年份为2024和2025，实际 {years}"
    assert all(m == 12 for m in months), f"期望所有月份为12，实际 {months}"

    print("✅ 测试通过")


def test_e2e_single_year_end():
    """端到端测试：\"2025年末\"（单年，不受影响）"""
    query = "TSE科技2025年末的总资产和总负债"
    print(f"\n{'='*60}")
    print(f"测试3: {query}")
    print('='*60)

    result = run_pipeline(query, DB_PATH)

    sql = result.get('sql')
    if sql:
        print(f"\nSQL: {sql[:300]}...")
    else:
        print(f"\n使用概念管线（无SQL）")

    data = result.get('results', [])
    print(f"\n返回数据行数: {len(data)}")
    print(f"数据: {data}")

    # 单年年末应该返回1行数据
    assert len(data) == 1, f"期望返回1行数据（2025.12），实际返回{len(data)}行"

    # 概念管线返回的数据格式不同，只验证有数据即可
    assert data[0] is not None, "期望返回数据，实际为None"

    print("✅ 测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("多年年末查询端到端测试")
    print("=" * 60)

    try:
        test_e2e_multi_year_end_dash_with_mei()
        test_e2e_multi_year_end_comma()
        test_e2e_single_year_end()

        print("\n" + "=" * 60)
        print("✅ 所有端到端测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
