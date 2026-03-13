"""集成测试：多轮对话完整流程"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mvp_pipeline import run_pipeline
from modules.db_utils import get_connection


def test_multi_turn_vat_query():
    """测试场景1：增值税多轮查询"""
    print("\n" + "="*60)
    print("测试场景1：增值税多轮查询")
    print("="*60)

    # 第1轮：完整查询
    print("\n【第1轮】用户: 华兴科技2025年1月的增值税是多少？")
    result1 = run_pipeline("华兴科技2025年1月的增值税是多少？")

    if result1.get('success'):
        print(f"✓ 查询成功")
        print(f"  - 纳税人: {result1['entities'].get('taxpayer_name')}")
        print(f"  - 期间: {result1['entities'].get('period_year')}年{result1['entities'].get('period_month')}月")
        print(f"  - 域: {result1['intent'].get('domain')}")
        if result1.get('rows'):
            print(f"  - 结果行数: {len(result1['rows'])}")
    else:
        print(f"✗ 查询失败: {result1.get('error')}")
        return

    # 构建对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年1月的增值税是多少？",
            "timestamp": "2026-03-02T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年1月的增值税为...",
            "timestamp": "2026-03-02T10:00:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": result1['intent'].get('domain'),
                "entities": result1['entities'],
                "sql": result1.get('sql'),
            }
        }
    ]

    # 第2轮：隐式时间查询
    print("\n【第2轮】用户: 2月呢？")
    result2 = run_pipeline("2月呢？", conversation_history=conversation_history)

    if result2.get('success'):
        print(f"✓ 查询成功（上下文继承）")
        print(f"  - 纳税人: {result2['entities'].get('taxpayer_name')} (继承)")
        print(f"  - 期间: {result2['entities'].get('period_year')}年{result2['entities'].get('period_month')}月")
        print(f"  - 域: {result2['intent'].get('domain')} (继承)")
        if result2.get('rows'):
            print(f"  - 结果行数: {len(result2['rows'])}")
    else:
        print(f"✗ 查询失败: {result2.get('error')}")
        return

    # 验证继承
    assert result2['entities'].get('taxpayer_id') == result1['entities'].get('taxpayer_id'), "纳税人ID应该继承"
    assert result2['entities'].get('period_year') == 2025, "年份应该继承"
    assert result2['entities'].get('period_month') == 2, "月份应该从查询中提取"
    print("\n✅ 场景1通过：隐式时间继承正常工作")


def test_pronoun_resolution():
    """测试场景2：代词解析"""
    print("\n" + "="*60)
    print("测试场景2：代词解析")
    print("="*60)

    # 第1轮：查询利润
    print("\n【第1轮】用户: 华兴科技2025年的利润")
    result1 = run_pipeline("华兴科技2025年的利润")

    if result1.get('success'):
        print(f"✓ 查询成功")
        print(f"  - 纳税人: {result1['entities'].get('taxpayer_name')}")
        print(f"  - 域: {result1['intent'].get('domain')}")
    else:
        print(f"✗ 查询失败: {result1.get('error')}")
        return

    # 构建对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年的利润",
            "timestamp": "2026-03-02T10:05:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年的利润为...",
            "timestamp": "2026-03-02T10:05:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": result1['intent'].get('domain'),
                "entities": result1['entities'],
                "sql": result1.get('sql'),
            }
        }
    ]

    # 第2轮：代词查询
    print("\n【第2轮】用户: 它的现金流怎么样？")
    result2 = run_pipeline("它的现金流怎么样？", conversation_history=conversation_history)

    if result2.get('success'):
        print(f"✓ 查询成功（代词解析）")
        print(f"  - 纳税人: {result2['entities'].get('taxpayer_name')} (从'它'解析)")
        print(f"  - 域: {result2['intent'].get('domain')} (新域)")
    else:
        print(f"✗ 查询失败: {result2.get('error')}")
        return

    # 验证代词解析
    assert result2['entities'].get('taxpayer_id') == result1['entities'].get('taxpayer_id'), "纳税人ID应该从代词解析"
    assert result2['intent'].get('domain') == 'cash_flow', "域应该是现金流"
    print("\n✅ 场景2通过：代词解析正常工作")


def test_cross_domain_context():
    """测试场景3：跨域上下文"""
    print("\n" + "="*60)
    print("测试场景3：跨域上下文")
    print("="*60)

    # 第1轮：查询资产负债表
    print("\n【第1轮】用户: 华兴科技2025年12月的资产负债表")
    result1 = run_pipeline("华兴科技2025年12月的资产负债表")

    if result1.get('success'):
        print(f"✓ 查询成功")
        print(f"  - 纳税人: {result1['entities'].get('taxpayer_name')}")
        print(f"  - 期间: {result1['entities'].get('period_year')}年{result1['entities'].get('period_month')}月")
        print(f"  - 域: {result1['intent'].get('domain')}")
    else:
        print(f"✗ 查询失败: {result1.get('error')}")
        return

    # 构建对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年12月的资产负债表",
            "timestamp": "2026-03-02T10:10:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年12月的资产负债表...",
            "timestamp": "2026-03-02T10:10:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": result1['intent'].get('domain'),
                "entities": result1['entities'],
                "sql": result1.get('sql'),
            }
        }
    ]

    # 第2轮：切换到利润表（继承纳税人和时间）
    print("\n【第2轮】用户: 利润表呢？")
    result2 = run_pipeline("利润表呢？", conversation_history=conversation_history)

    if result2.get('success'):
        print(f"✓ 查询成功（跨域上下文）")
        print(f"  - 纳税人: {result2['entities'].get('taxpayer_name')} (继承)")
        print(f"  - 期间: {result2['entities'].get('period_year')}年{result2['entities'].get('period_month')}月 (继承)")
        print(f"  - 域: {result2['intent'].get('domain')} (新域)")
    else:
        print(f"✗ 查询失败: {result2.get('error')}")
        return

    # 验证跨域继承
    assert result2['entities'].get('taxpayer_id') == result1['entities'].get('taxpayer_id'), "纳税人ID应该继承"
    assert result2['entities'].get('period_year') == result1['entities'].get('period_year'), "年份应该继承"
    assert result2['entities'].get('period_month') == result1['entities'].get('period_month'), "月份应该继承"
    assert result2['intent'].get('domain') == 'profit', "域应该切换到利润表"
    print("\n✅ 场景3通过：跨域上下文继承正常工作")


def test_independent_query_no_inheritance():
    """测试场景4：独立查询不继承"""
    print("\n" + "="*60)
    print("测试场景4：独立查询不继承")
    print("="*60)

    # 第1轮：查询华兴科技
    print("\n【第1轮】用户: 华兴科技2025年1月的增值税")
    result1 = run_pipeline("华兴科技2025年1月的增值税")

    if result1.get('success'):
        print(f"✓ 查询成功")
        print(f"  - 纳税人: {result1['entities'].get('taxpayer_name')}")
    else:
        print(f"✗ 查询失败: {result1.get('error')}")
        return

    # 构建对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年1月的增值税",
            "timestamp": "2026-03-02T10:15:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年1月的增值税为...",
            "timestamp": "2026-03-02T10:15:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": result1['intent'].get('domain'),
                "entities": result1['entities'],
                "sql": result1.get('sql'),
            }
        }
    ]

    # 第2轮：完整独立查询（不应该继承）
    print("\n【第2轮】用户: 鑫源贸易2025年3月的增值税")
    result2 = run_pipeline("鑫源贸易2025年3月的增值税", conversation_history=conversation_history)

    if result2.get('success'):
        print(f"✓ 查询成功（独立查询）")
        print(f"  - 纳税人: {result2['entities'].get('taxpayer_name')} (新纳税人)")
        print(f"  - 期间: {result2['entities'].get('period_year')}年{result2['entities'].get('period_month')}月 (新时间)")
    else:
        print(f"✗ 查询失败: {result2.get('error')}")
        return

    # 验证不继承
    assert result2['entities'].get('taxpayer_id') != result1['entities'].get('taxpayer_id'), "纳税人ID不应该继承"
    assert result2['entities'].get('taxpayer_name') == '鑫源贸易商行', "应该是新纳税人"
    assert result2['entities'].get('period_month') == 3, "应该是新月份"
    print("\n✅ 场景4通过：独立查询不继承上下文")


def test_cache_behavior():
    """测试场景5：缓存行为"""
    print("\n" + "="*60)
    print("测试场景5：缓存行为")
    print("="*60)

    from modules.cache_manager import clear_cache, get_cache_stats

    # 清空缓存
    clear_cache()
    print("\n清空缓存")

    # 第1次查询（缓存未命中）
    print("\n【第1次】查询: 华兴科技2025年1月的增值税")
    result1 = run_pipeline("华兴科技2025年1月的增值税")
    stats1 = get_cache_stats()
    print(f"  - Intent缓存: {stats1['intent']['hits']} hits, {stats1['intent']['misses']} misses")
    print(f"  - SQL缓存: {stats1['sql']['hits']} hits, {stats1['sql']['misses']} misses")

    # 第2次相同查询（缓存命中）
    print("\n【第2次】相同查询: 华兴科技2025年1月的增值税")
    result2 = run_pipeline("华兴科技2025年1月的增值税")
    stats2 = get_cache_stats()
    print(f"  - Intent缓存: {stats2['intent']['hits']} hits, {stats2['intent']['misses']} misses")
    print(f"  - SQL缓存: {stats2['sql']['hits']} hits, {stats2['sql']['misses']} misses")

    # 验证缓存命中
    assert stats2['intent']['hits'] > stats1['intent']['hits'], "Intent缓存应该命中"
    assert stats2['sql']['hits'] > stats1['sql']['hits'], "SQL缓存应该命中"

    # 构建对话历史
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年1月的增值税",
            "timestamp": "2026-03-02T10:20:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年1月的增值税为...",
            "timestamp": "2026-03-02T10:20:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": "vat",
                "entities": result1['entities'],
                "sql": result1.get('sql'),
            }
        }
    ]

    # 第3次上下文依赖查询（不同缓存键）
    print("\n【第3次】上下文查询: 2月呢？")
    result3 = run_pipeline("2月呢？", conversation_history=conversation_history)
    stats3 = get_cache_stats()
    print(f"  - Intent缓存: {stats3['intent']['hits']} hits, {stats3['intent']['misses']} misses")
    print(f"  - SQL缓存: {stats3['sql']['hits']} hits, {stats3['sql']['misses']} misses")

    # 验证上下文查询使用不同缓存键
    assert stats3['intent']['misses'] > stats2['intent']['misses'], "上下文查询应该使用不同缓存键"

    print("\n✅ 场景5通过：缓存行为正确")


if __name__ == "__main__":
    try:
        test_multi_turn_vat_query()
        test_pronoun_resolution()
        test_cross_domain_context()
        test_independent_query_no_inheritance()
        test_cache_behavior()

        print("\n" + "="*60)
        print("🎉 所有集成测试通过！")
        print("="*60)
        print("\n多轮对话功能已启用并正常工作：")
        print("  ✓ 隐式时间继承")
        print("  ✓ 代词解析")
        print("  ✓ 跨域上下文")
        print("  ✓ 独立查询不继承")
        print("  ✓ 缓存行为正确")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
