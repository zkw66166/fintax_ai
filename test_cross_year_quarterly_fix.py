#!/usr/bin/env python3
"""
跨年季度比较系统性修复验证脚本

测试所有修复点：
- Phase 0: 中文月份词转换 + 跨年月份提取
- Phase 1: 零值列保留（跨域查询）
- Phase 2: 跨年季度模板（5个域）
- Phase 3: VAT数据处理
- Phase 4: 跨域合并逻辑
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mvp_pipeline import run_pipeline
from modules.entity_preprocessor import detect_entities
import sqlite3
from config.settings import DB_PATH


def test_phase0_chinese_month_conversion():
    """Phase 0: 测试中文月份词转换"""
    print("\n" + "="*80)
    print("Phase 0: 中文月份词转换测试")
    print("="*80)

    # 创建数据库连接
    db_conn = sqlite3.connect(DB_PATH)

    test_cases = [
        ("2024年一月和2025年一月利润总额", {
            'expected_year': 2024,
            'expected_month': 1,
            'expected_end_year': 2025,
            'expected_end_month': 1
        }),
        ("2024年十二月与2025年一月对比", {
            'expected_year': 2024,
            'expected_month': 12,
            'expected_end_year': 2025,
            'expected_end_month': 1
        }),
        ("2024年三月到2025年三月", {
            'expected_year': 2024,
            'expected_month': 3,
            'expected_end_year': 2025,
            'expected_end_month': 3
        }),
    ]

    for query, expected in test_cases:
        print(f"\n查询: {query}")
        entities = detect_entities(query, db_conn)
        print(f"提取结果: period_year={entities.get('period_year')}, "
              f"period_month={entities.get('period_month')}, "
              f"period_end_year={entities.get('period_end_year')}, "
              f"period_end_month={entities.get('period_end_month')}")

        # 验证
        passed = True
        if entities.get('period_year') != expected['expected_year']:
            print(f"❌ period_year 错误: 期望 {expected['expected_year']}, 实际 {entities.get('period_year')}")
            passed = False
        if entities.get('period_month') != expected['expected_month']:
            print(f"❌ period_month 错误: 期望 {expected['expected_month']}, 实际 {entities.get('period_month')}")
            passed = False
        if entities.get('period_end_year') != expected['expected_end_year']:
            print(f"❌ period_end_year 错误: 期望 {expected['expected_end_year']}, 实际 {entities.get('period_end_year')}")
            passed = False
        if entities.get('period_end_month') != expected['expected_end_month']:
            print(f"❌ period_end_month 错误: 期望 {expected['expected_end_month']}, 实际 {entities.get('period_end_month')}")
            passed = False

        if passed:
            print("✅ 通过")

    db_conn.close()


def test_phase0_cross_year_extraction():
    """Phase 0: 测试跨年月份提取（两个期间都提取）"""
    print("\n" + "="*80)
    print("Phase 0: 跨年月份提取测试")
    print("="*80)

    # 创建数据库连接
    db_conn = sqlite3.connect(DB_PATH)

    query = "2024年1月和2025年1月利润总额、增值税应纳税额、企业所得税应纳税额比较分析"
    print(f"\n查询: {query}")

    entities = detect_entities(query, db_conn)
    print(f"提取结果: period_year={entities.get('period_year')}, "
          f"period_month={entities.get('period_month')}, "
          f"period_end_year={entities.get('period_end_year')}, "
          f"period_end_month={entities.get('period_end_month')}")

    # 验证
    if (entities.get('period_year') == 2024 and
        entities.get('period_month') == 1 and
        entities.get('period_end_year') == 2025 and
        entities.get('period_end_month') == 1):
        print("✅ 通过：两个期间都正确提取")
    else:
        print("❌ 失败：期间提取不完整")

    db_conn.close()


def test_original_failing_query():
    """测试原始失败查询（完整pipeline）"""
    print("\n" + "="*80)
    print("原始失败查询测试（完整pipeline）")
    print("="*80)

    query = "2024年一季度和2025年一季度利润总额、增值税应纳税额、企业所得税应纳税额比较分析"
    print(f"\n查询: {query}")
    print("执行完整pipeline...")

    try:
        result = run_pipeline(
            user_query=query,
            company_id="91310115MA2KZZZZZZ",  # TSE科技
            response_mode="concise"
        )

        print(f"\n路由: {result.get('route')}")
        print(f"域: {result.get('domain')}")

        if result.get('results'):
            print(f"结果行数: {len(result['results'])}")
            print(f"结果列: {list(result['results'][0].keys())}")

            # 检查是否包含所有3个指标
            first_row = result['results'][0]
            has_profit = any('利润' in k for k in first_row.keys())
            has_vat = any('增值税' in k for k in first_row.keys())
            has_eit = any('企业所得税' in k or '所得税' in k for k in first_row.keys())

            print(f"\n指标检查:")
            print(f"  利润总额: {'✅' if has_profit else '❌'}")
            print(f"  增值税应纳税额: {'✅' if has_vat else '❌'}")
            print(f"  企业所得税应纳税额: {'✅' if has_eit else '❌'}")

            if has_profit and has_vat and has_eit:
                print("\n✅ 通过：所有3个指标都存在")
            else:
                print("\n❌ 失败：缺少指标")

            # 检查零值列是否保留
            print(f"\n零值列检查:")
            for col in first_row.keys():
                if col not in ['period', 'taxpayer_id', 'taxpayer_name', 'period_year', 'period_month']:
                    val = first_row[col]
                    if val == 0 or val is None:
                        print(f"  {col}: {val} (零值/NULL列已保留)")

        else:
            print("❌ 失败：无结果")

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_other_domains():
    """测试其他域的跨年季度查询"""
    print("\n" + "="*80)
    print("其他域跨年季度查询测试")
    print("="*80)

    test_cases = [
        ("2024年一季度和2025年一季度资产负债表对比", "balance_sheet"),
        ("2024年一季度和2025年一季度现金流量表对比", "cash_flow"),
        ("2024年一季度和2025年一季度科目余额对比", "account_balance"),
    ]

    for query, expected_domain in test_cases:
        print(f"\n查询: {query}")
        print(f"期望域: {expected_domain}")

        try:
            result = run_pipeline(
                user_query=query,
                company_id="91310115MA2KZZZZZZ",  # TSE科技
                response_mode="concise"
            )

            print(f"实际域: {result.get('domain')}")
            print(f"结果行数: {len(result.get('results', []))}")

            if result.get('results'):
                # 检查期间
                periods = set()
                for row in result['results']:
                    y = row.get('period_year')
                    m = row.get('period_month')
                    if y and m:
                        periods.add(f"{y}-{m:02d}")

                print(f"期间: {sorted(periods)}")

                # 验证：应该只有2个期间（2024-03, 2025-03）
                if len(periods) == 2 and '2024-03' in periods and '2025-03' in periods:
                    print("✅ 通过：期间正确")
                else:
                    print(f"❌ 失败：期间错误，期望 ['2024-03', '2025-03']，实际 {sorted(periods)}")
            else:
                print("❌ 失败：无结果")

        except Exception as e:
            print(f"❌ 执行失败: {e}")


if __name__ == '__main__':
    print("跨年季度比较系统性修复验证")
    print("="*80)

    # Phase 0: 实体提取测试（不需要LLM）
    test_phase0_chinese_month_conversion()
    test_phase0_cross_year_extraction()

    # 完整pipeline测试（需要LLM）
    print("\n\n" + "="*80)
    print("完整Pipeline测试（需要LLM API）")
    print("="*80)
    print("提示：以下测试需要调用LLM API，可能需要几分钟")
    input("按Enter继续，或Ctrl+C取消...")

    test_original_failing_query()
    test_other_domains()

    print("\n\n" + "="*80)
    print("测试完成")
    print("="*80)
