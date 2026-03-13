"""
测试多年年末查询修复
Test multi-year year-end query fixes

测试场景：
1. "2024-2025每年末" → 返回2024.12和2025.12
2. "2024-2025年末" → 返回2024.12和2025.12
3. "2024、2025年末" → 返回2024.12和2025.12
4. "2024年到2025年" → 返回24个月（范围查询，不受影响）
5. "2025年末" → 返回1个月（单年年末，不受影响）
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from modules.entity_preprocessor import detect_entities

# 连接数据库
DB_PATH = "database/fintax_ai.db"
conn = sqlite3.connect(DB_PATH)


def test_multi_year_end_dash_with_mei():
    """测试\"2024-2025每年末\" - 应识别为多年年末"""
    query = "TSE科技2024-2025每年末的总资产和总负债分析"
    entities = detect_entities(query, conn)

    print(f"\n测试1: {query}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_years') == [2024, 2025], f"期望 period_years=[2024, 2025], 实际 {entities.get('period_years')}"
    assert entities.get('period_month') == 12, f"期望 period_month=12, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') == [12], f"期望 period_months=[12], 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


def test_multi_year_end_dash():
    """测试\"2024-2025年末\" - 应识别为多年年末"""
    query = "TSE科技2024-2025年末的总资产和总负债分析"
    entities = detect_entities(query, conn)

    print(f"\n测试2: {query}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_years') == [2024, 2025], f"期望 period_years=[2024, 2025], 实际 {entities.get('period_years')}"
    assert entities.get('period_month') == 12, f"期望 period_month=12, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') == [12], f"期望 period_months=[12], 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


def test_multi_year_end_comma():
    """测试\"2024、2025年末\" - 应识别为多年年末（新增顿号支持）"""
    query = "TSE科技2024、2025年末的总资产和总负债分析"
    entities = detect_entities(query, conn)

    print(f"\n测试3: {query}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_years') == [2024, 2025], f"期望 period_years=[2024, 2025], 实际 {entities.get('period_years')}"
    assert entities.get('period_month') == 12, f"期望 period_month=12, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') == [12], f"期望 period_months=[12], 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


def test_year_range_no_year_end():
    """测试\"2024年到2025年\" - 范围查询，不应设置period_months"""
    query = "TSE科技2024年到2025年的总资产"
    entities = detect_entities(query, conn)

    print(f"\n测试4: {query}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_years') == [2024, 2025], f"期望 period_years=[2024, 2025], 实际 {entities.get('period_years')}"
    assert entities.get('period_month') is None, f"期望 period_month=None, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') is None, f"期望 period_months=None, 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


def test_single_year_end():
    """测试\"2025年末\" - 单年年末，不应设置period_months"""
    query = "TSE科技2025年末的总资产"
    entities = detect_entities(query, conn)

    print(f"\n测试5: {query}")
    print(f"  period_year: {entities.get('period_year')}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_year') == 2025, f"期望 period_year=2025, 实际 {entities.get('period_year')}"
    assert entities.get('period_month') == 12, f"期望 period_month=12, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') is None, f"期望 period_months=None, 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


def test_multi_year_begin():
    """测试\"2024-2025年初\" - 多年年初，应设置period_months=[1]"""
    query = "TSE科技2024-2025年初的总资产"
    entities = detect_entities(query, conn)

    print(f"\n测试6: {query}")
    print(f"  period_years: {entities.get('period_years')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_months: {entities.get('period_months')}")

    assert entities.get('period_years') == [2024, 2025], f"期望 period_years=[2024, 2025], 实际 {entities.get('period_years')}"
    assert entities.get('period_month') == 1, f"期望 period_month=1, 实际 {entities.get('period_month')}"
    assert entities.get('period_months') == [1], f"期望 period_months=[1], 实际 {entities.get('period_months')}"
    print("  ✅ 通过")


if __name__ == "__main__":
    print("=" * 60)
    print("多年年末查询修复测试")
    print("=" * 60)

    try:
        test_multi_year_end_dash_with_mei()
        test_multi_year_end_dash()
        test_multi_year_end_comma()
        test_year_range_no_year_end()
        test_single_year_end()
        test_multi_year_begin()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
