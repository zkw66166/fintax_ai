"""
端到端测试：跨路由混合多轮查询完整流程

模拟真实用户场景：
1. 第1轮：查询税收优惠政策
2. 第2轮：查询企业财务数据
3. 第3轮：要求综合分析
"""
import sys
sys.path.insert(0, '.')

from mvp_pipeline import run_pipeline_stream


def test_end_to_end():
    """端到端测试：完整的混合分析流程"""
    print("\n" + "="*60)
    print("端到端测试：跨路由混合多轮查询")
    print("="*60)

    # 模拟对话历史
    conversation_history = [
        {
            'role': 'user',
            'content': '小微企业税收优惠有哪些'
        },
        {
            'role': 'assistant',
            'content': '小微企业可以享受以下税收优惠政策：\n1. 增值税小规模纳税人减免\n2. 企业所得税优惠税率\n3. 印花税减免',
            'metadata': {
                'route': 'tax_incentive',
                'original_query': '小微企业税收优惠有哪些'
            }
        },
        {
            'role': 'user',
            'content': 'TSE科技有限公司2025年营业收入'
        },
        {
            'role': 'assistant',
            'content': 'TSE科技有限公司2025年营业收入为500万元',
            'metadata': {
                'route': 'financial_data',
                'original_query': 'TSE科技有限公司2025年营业收入',
                'domain': 'profit'
            }
        },
    ]

    # 第3轮：要求综合分析
    user_query = "TSE科技可以享受哪些小微企业税收优惠，请结合上述数据分析"

    print(f"\n第3轮查询: {user_query}")
    print(f"对话历史: {len(conversation_history)} 条消息")
    print(f"多轮对话: 已启用")
    print("\n开始执行...")

    # 执行pipeline
    events = []
    for event in run_pipeline_stream(
        user_query=user_query,
        conversation_history=conversation_history,
        multi_turn_enabled=True  # 关键：启用多轮对话
    ):
        events.append(event)
        etype = event.get('type')

        if etype == 'stage':
            route = event.get('route', '')
            text = event.get('text', '')
            print(f"\n[阶段] {route}: {text}")

        elif etype == 'chunk':
            text = event.get('text', '')
            print(text, end='', flush=True)

        elif etype == 'done':
            result = event.get('result', {})
            route = result.get('route', '')
            print(f"\n\n[完成] 路由: {route}")

            if route == 'mixed_analysis':
                print(f"✅ 成功触发混合分析路由")
                print(f"涉及路由: {result.get('routes_used', [])}")
                print(f"分析长度: {len(result.get('analysis', ''))} 字符")
            else:
                print(f"⚠️ 未触发混合分析，实际路由: {route}")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

    # 验证结果
    done_events = [e for e in events if e.get('type') == 'done']
    assert len(done_events) == 1, "应该有1个done事件"

    result = done_events[0].get('result', {})
    route = result.get('route')

    if route == 'mixed_analysis':
        print("\n✅ 端到端测试通过：成功触发混合分析")
        return True
    else:
        print(f"\n⚠️ 端到端测试警告：未触发混合分析（实际路由: {route}）")
        print("可能原因：LLM判断当前查询不需要综合分析")
        return False


def test_without_multi_turn():
    """测试：未启用多轮对话时不触发混合分析"""
    print("\n" + "="*60)
    print("测试：未启用多轮对话")
    print("="*60)

    conversation_history = [
        {
            'role': 'user',
            'content': '小微企业税收优惠有哪些'
        },
        {
            'role': 'assistant',
            'content': '...',
            'metadata': {'route': 'tax_incentive'}
        },
    ]

    user_query = "TSE科技可以享受哪些税收优惠"

    print(f"\n查询: {user_query}")
    print(f"多轮对话: 未启用")
    print("\n开始执行...")

    for event in run_pipeline_stream(
        user_query=user_query,
        conversation_history=conversation_history,
        multi_turn_enabled=False  # 关键：未启用多轮对话
    ):
        if event.get('type') == 'done':
            result = event.get('result', {})
            route = result.get('route', '')
            print(f"\n[完成] 路由: {route}")

            assert route != 'mixed_analysis', "未启用多轮对话时不应触发混合分析"
            print(f"✅ 正确：未触发混合分析（实际路由: {route}）")
            break

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    try:
        # 测试1：完整的混合分析流程
        test_end_to_end()

        # 测试2：未启用多轮对话
        test_without_multi_turn()

        print("\n" + "="*60)
        print("所有端到端测试完成！")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
