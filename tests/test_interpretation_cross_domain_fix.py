"""测试跨域查询解读修复：验证 sub_tables 数据提取"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.interpretation_service import _format_data_for_prompt, detect_scenario


def test_cross_domain_sub_tables_extraction():
    """测试跨域 list 操作的 sub_tables 数据提取"""

    # 模拟跨域查询结果（balance_sheet + profit + eit）
    result = {
        'intent': {'domain': 'cross_domain'},
        'display_data': {
            'table': {'headers': [], 'rows': []},  # list 操作时主表为空
            'sub_tables': [
                {
                    'domain': 'balance_sheet',
                    'domain_cn': '资产负债表',
                    'table': {
                        'headers': ['期间', '总资产'],
                        'rows': [
                            {'期间': '2025年12月', '总资产': '5000.00万'}
                        ]
                    }
                },
                {
                    'domain': 'profit',
                    'domain_cn': '利润表',
                    'table': {
                        'headers': ['期间', '净利润'],
                        'rows': [
                            {'期间': '2025年第四季度', '净利润': '800.00万'}
                        ]
                    }
                },
                {
                    'domain': 'eit',
                    'domain_cn': '企业所得税',
                    'table': {
                        'headers': ['期间', '应纳企业所得税额'],
                        'rows': [
                            {'期间': '2025年第四季度', '应纳企业所得税额': '200.00万'}
                        ]
                    }
                }
            ]
        },
        'results': []
    }

    query = "去年第四季度总资产、净利润、应纳企业所得税额情况"

    # 测试场景检测
    scenario = detect_scenario(result)
    print(f"✓ 场景检测: {scenario}")
    assert scenario['scenario'] == 'cross_domain', "应检测为 cross_domain 场景"

    # 测试数据格式化
    formatted = _format_data_for_prompt(result, query)
    print(f"\n✓ 格式化后的提示词:\n{formatted}\n")

    # 验证关键内容
    assert '数据来源' in formatted, "应包含'数据来源'列"
    assert '资产负债表' in formatted, "应包含资产负债表域"
    assert '利润表' in formatted, "应包含利润表域"
    assert '企业所得税' in formatted, "应包含企业所得税域"
    assert '总资产' in formatted, "应包含总资产指标"
    assert '净利润' in formatted, "应包含净利润指标"
    assert '应纳企业所得税额' in formatted, "应包含应纳企业所得税额指标"
    assert '5000.00万' in formatted, "应包含总资产数值"
    assert '800.00万' in formatted, "应包含净利润数值"
    assert '200.00万' in formatted, "应包含应纳企业所得税额数值"
    assert '各子域数据概览' in formatted, "应包含子域数据摘要"
    assert '1行 × 2列' in formatted, "应显示每个子域的行列数"

    print("✓ 所有验证通过！")
    print("\n关键改进:")
    print("1. 从 sub_tables 提取所有子域数据")
    print("2. 为每行添加'数据来源'列标识域")
    print("3. 合并所有子域的表头和数据行")
    print("4. 添加子域数据摘要（行数×列数）")
    print("5. LLM 现在可以看到完整的跨域数据")


def test_single_domain_backward_compatibility():
    """测试单域查询的向后兼容性"""

    result = {
        'intent': {'domain': 'vat'},
        'display_data': {
            'table': {
                'headers': ['期间', '应纳税额'],
                'rows': [
                    {'期间': '2025年1月', '应纳税额': '100.00万'}
                ]
            }
        },
        'results': []
    }

    query = "2025年1月增值税"
    formatted = _format_data_for_prompt(result, query)

    print(f"\n✓ 单域查询格式化:\n{formatted}\n")

    assert '应纳税额' in formatted, "应包含应纳税额"
    assert '100.00万' in formatted, "应包含数值"
    assert '数据来源' not in formatted, "单域查询不应有数据来源列"

    print("✓ 单域查询向后兼容性验证通过！")


def test_cross_domain_compare_operation():
    """测试跨域 compare 操作（非 list）"""

    result = {
        'intent': {'domain': 'cross_domain'},
        'display_data': {
            'table': {
                'headers': ['期间', '营业收入', '销项税额'],
                'rows': [
                    {'期间': '2025年1月', '营业收入': '1000.00万', '销项税额': '130.00万'}
                ]
            }
        },
        'results': []
    }

    query = "2025年1月营业收入和销项税额对比"
    formatted = _format_data_for_prompt(result, query)

    print(f"\n✓ 跨域 compare 操作格式化:\n{formatted}\n")

    assert '营业收入' in formatted, "应包含营业收入"
    assert '销项税额' in formatted, "应包含销项税额"
    assert '1000.00万' in formatted, "应包含营业收入数值"
    assert '130.00万' in formatted, "应包含销项税额数值"

    print("✓ 跨域 compare 操作验证通过！")


if __name__ == '__main__':
    print("=" * 60)
    print("测试跨域查询解读修复")
    print("=" * 60)

    test_cross_domain_sub_tables_extraction()
    print("\n" + "=" * 60)

    test_single_domain_backward_compatibility()
    print("\n" + "=" * 60)

    test_cross_domain_compare_operation()
    print("\n" + "=" * 60)

    print("\n✅ 所有测试通过！修复成功。")
    print("\n修复总结:")
    print("- 跨域 list 操作现在从 sub_tables 提取完整数据")
    print("- 为每行添加'数据来源'列标识域")
    print("- 添加子域数据摘要帮助 LLM 理解数据结构")
    print("- 更新跨域场景指令，明确要求检查数据完整性")
    print("- 保持单域和其他跨域操作的向后兼容性")
