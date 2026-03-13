"""测试API接受对话历史"""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.schemas import ChatRequest


def test_chat_request_schema():
    """测试ChatRequest schema接受conversation_history"""
    print("\n" + "="*60)
    print("测试API Schema")
    print("="*60)

    # 测试1: 不带对话历史的请求
    print("\n【测试1】不带对话历史的请求")
    req1 = ChatRequest(
        query="华兴科技2025年1月的增值税",
        company_id="91310000MA1FL8XQ30"
    )
    print(f"  query: {req1.query}")
    print(f"  conversation_history: {req1.conversation_history}")
    print(f"  conversation_depth: {req1.conversation_depth}")
    assert req1.conversation_history is None, "默认应该是None"
    assert req1.conversation_depth == 3, "默认深度应该是3"
    print("  ✓ 通过")

    # 测试2: 带对话历史的请求
    print("\n【测试2】带对话历史的请求")
    conversation_history = [
        {
            "role": "user",
            "content": "华兴科技2025年1月的增值税",
            "timestamp": "2026-03-02T10:00:00Z",
        },
        {
            "role": "assistant",
            "content": "华兴科技2025年1月的增值税为...",
            "timestamp": "2026-03-02T10:00:05Z",
            "metadata": {
                "route": "financial_data",
                "domain": "vat",
                "entities": {
                    "taxpayer_id": "91310000MA1FL8XQ30",
                    "period_year": 2025,
                    "period_month": 1,
                }
            }
        }
    ]

    req2 = ChatRequest(
        query="2月呢?",
        company_id="91310000MA1FL8XQ30",
        conversation_history=conversation_history,
        conversation_depth=5
    )
    print(f"  query: {req2.query}")
    print(f"  conversation_history: {len(req2.conversation_history)} 条消息")
    print(f"  conversation_depth: {req2.conversation_depth}")
    assert req2.conversation_history is not None, "应该有对话历史"
    assert len(req2.conversation_history) == 2, "应该有2条消息"
    assert req2.conversation_depth == 5, "深度应该是5"
    print("  ✓ 通过")

    # 测试3: 验证深度范围限制
    print("\n【测试3】验证深度范围限制")
    try:
        req3 = ChatRequest(
            query="测试",
            conversation_depth=1  # 小于最小值2
        )
        print("  ✗ 应该抛出验证错误")
        assert False, "应该抛出验证错误"
    except Exception as e:
        print(f"  ✓ 正确拒绝了无效深度: {type(e).__name__}")

    try:
        req4 = ChatRequest(
            query="测试",
            conversation_depth=6  # 大于最大值5
        )
        print("  ✗ 应该抛出验证错误")
        assert False, "应该抛出验证错误"
    except Exception as e:
        print(f"  ✓ 正确拒绝了无效深度: {type(e).__name__}")

    print("\n" + "="*60)
    print("🎉 所有API Schema测试通过!")
    print("="*60)


if __name__ == "__main__":
    try:
        test_chat_request_schema()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
