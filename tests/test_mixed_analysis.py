"""
测试跨路由混合多轮查询功能

测试场景：
1. 未勾选多轮对话 → 不触发混合分析
2. 单路由多轮 → 不触发混合分析
3. 混合路由多轮 → 触发混合分析
"""
import sys
sys.path.insert(0, '.')

from modules.mixed_analysis_detector import should_trigger_mixed_analysis


def test_multi_turn_disabled():
    """测试：未勾选多轮对话"""
    print("\n=== 测试1：未勾选多轮对话 ===")

    conversation_history = [
        {'role': 'user', 'content': '资产税收优惠有哪些'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'tax_incentive'}},
        {'role': 'user', 'content': 'TSE科技2025年末流动资产结构'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'financial_data'}},
    ]

    should_trigger, reason = should_trigger_mixed_analysis(
        user_query="TSE可以享受哪些税收优惠",
        conversation_history=conversation_history,
        conversation_depth=2,
        multi_turn_enabled=False  # 未勾选
    )

    print(f"结果: should_trigger={should_trigger}, reason={reason}")
    assert should_trigger == False, "未勾选多轮对话时不应触发"
    assert reason == "multi_turn_disabled"
    print("✅ 通过")


def test_single_route():
    """测试：单路由多轮"""
    print("\n=== 测试2：单路由多轮 ===")

    conversation_history = [
        {'role': 'user', 'content': '华兴科技2025年1月增值税'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'financial_data'}},
        {'role': 'user', 'content': '2月呢'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'financial_data'}},
    ]

    should_trigger, reason = should_trigger_mixed_analysis(
        user_query="3月呢",
        conversation_history=conversation_history,
        conversation_depth=2,
        multi_turn_enabled=True  # 已勾选
    )

    print(f"结果: should_trigger={should_trigger}, reason={reason}")
    assert should_trigger == False, "单路由多轮不应触发"
    assert "single_route" in reason
    print("✅ 通过")


def test_mixed_routes_no_synthesis():
    """测试：混合路由但不需要综合分析"""
    print("\n=== 测试3：混合路由但不需要综合分析 ===")

    conversation_history = [
        {'role': 'user', 'content': '资产税收优惠有哪些'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'tax_incentive'}},
        {'role': 'user', 'content': 'TSE科技2025年末流动资产结构'},
        {'role': 'assistant', 'content': '...', 'metadata': {'route': 'financial_data'}},
    ]

    should_trigger, reason = should_trigger_mixed_analysis(
        user_query="华兴科技2025年利润是多少",  # 独立新问题
        conversation_history=conversation_history,
        conversation_depth=2,
        multi_turn_enabled=True
    )

    print(f"结果: should_trigger={should_trigger}, reason={reason}")
    # 这个测试依赖LLM判断，可能返回True或False
    print(f"✅ 完成（LLM判断结果: {should_trigger}）")


def test_mixed_routes_with_synthesis():
    """测试：混合路由且需要综合分析"""
    print("\n=== 测试4：混合路由且需要综合分析 ===")

    conversation_history = [
        {'role': 'user', 'content': '资产税收优惠有哪些'},
        {'role': 'assistant', 'content': '固定资产加速折旧、研发费用加计扣除...', 'metadata': {'route': 'tax_incentive'}},
        {'role': 'user', 'content': 'TSE科技2025年末流动资产结构'},
        {'role': 'assistant', 'content': '流动资产总额1000万元...', 'metadata': {'route': 'financial_data'}},
    ]

    should_trigger, reason = should_trigger_mixed_analysis(
        user_query="TSE可以享受哪些税收优惠，请结合上述数据分析",  # 明确要求综合分析
        conversation_history=conversation_history,
        conversation_depth=2,
        multi_turn_enabled=True
    )

    print(f"结果: should_trigger={should_trigger}, reason={reason}")
    # 这个测试依赖LLM判断，应该返回True
    print(f"✅ 完成（LLM判断结果: {should_trigger}）")


if __name__ == "__main__":
    print("开始测试跨路由混合多轮查询功能...")

    try:
        test_multi_turn_disabled()
        test_single_route()
        test_mixed_routes_no_synthesis()
        test_mixed_routes_with_synthesis()

        print("\n" + "="*50)
        print("所有测试完成！")
        print("="*50)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
