"""简化测试:验证对话上下文核心功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.conversation_manager import (
    is_context_dependent,
    extract_last_turn_entities,
    prepare_conversation_context,
    _resolve_pronouns,
)
from modules.entity_preprocessor import detect_entities_with_context
from modules.cache_manager import _generate_context_aware_cache_key
from modules.db_utils import get_connection


def main():
    print("\n" + "="*60)
    print("多轮对话功能测试")
    print("="*60)

    conn = get_connection()

    # 模拟对话历史
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
                    "taxpayer_name": "华兴科技有限公司",
                    "taxpayer_type": "一般纳税人",
                    "period_year": 2025,
                    "period_month": 1,
                    "domain_hint": "vat",
                },
            },
        },
    ]

    # 测试1: 上下文依赖检测
    print("\n【测试1】上下文依赖检测")
    test_queries = [
        ("华兴科技2025年1月的增值税", False),
        ("2月呢?", True),
        ("它的利润", True),
        ("那个指标", True),
    ]
    for query, expected in test_queries:
        result = is_context_dependent(query)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{query}' -> {result} (expected: {expected})")

    # 测试2: 实体继承
    print("\n【测试2】实体继承")
    query = "2月呢?"
    entities = detect_entities_with_context(query, conn, conversation_history)
    print(f"  查询: {query}")
    print(f"  继承的纳税人: {entities.get('taxpayer_name')}")
    print(f"  继承的年份: {entities.get('period_year')}")
    print(f"  提取的月份: {entities.get('period_month')}")

    assert entities.get('taxpayer_id') == "91310000MA1FL8XQ30", "应该继承纳税人ID"
    assert entities.get('period_year') == 2025, "应该继承年份"
    assert entities.get('period_month') == 2, "应该提取月份"
    print("  ✓ 实体继承正确")

    # 测试3: 代词解析
    print("\n【测试3】代词解析")
    query = "它的利润"
    entities = detect_entities_with_context(query, conn, conversation_history)
    print(f"  查询: {query}")
    print(f"  解析的纳税人: {entities.get('taxpayer_name')}")

    assert entities.get('taxpayer_id') == "91310000MA1FL8XQ30", "应该从代词解析纳税人"
    print("  ✓ 代词解析正确")

    # 测试4: 独立查询不继承
    print("\n【测试4】独立查询不继承")
    query = "鑫源贸易2025年3月的增值税"
    entities = detect_entities_with_context(query, conn, conversation_history)
    print(f"  查询: {query}")
    print(f"  纳税人: {entities.get('taxpayer_name')}")
    print(f"  期间: {entities.get('period_year')}年{entities.get('period_month')}月")

    assert entities.get('taxpayer_id') != "91310000MA1FL8XQ30", "不应该继承纳税人"
    assert entities.get('taxpayer_name') == "鑫源贸易商行", "应该是新纳税人"
    assert entities.get('period_month') == 3, "应该是新月份"
    print("  ✓ 独立查询不继承")

    # 测试5: 缓存键生成
    print("\n【测试5】缓存键生成")
    key1 = _generate_context_aware_cache_key(
        "华兴科技2025年1月的增值税",
        "一般纳税人",
        [],
        None
    )
    key2 = _generate_context_aware_cache_key(
        "2月呢?",
        "一般纳税人",
        [],
        conversation_history
    )
    print(f"  独立查询缓存键: {key1[:16]}...")
    print(f"  上下文查询缓存键: {key2[:16]}...")
    print(f"  两个键不同: {key1 != key2}")

    assert key1 != key2, "上下文查询应该使用不同的缓存键"
    print("  ✓ 缓存键生成正确")

    # 测试6: 对话上下文准备
    print("\n【测试6】对话上下文准备")
    long_history = []
    for i in range(10):
        long_history.append({"role": "user", "content": f"查询{i+1}"})
        long_history.append({"role": "assistant", "content": f"结果{i+1}"})

    prepared = prepare_conversation_context(long_history, max_turns=3)
    print(f"  原始历史: {len(long_history)} 条消息")
    print(f"  准备后: {len(prepared)} 条消息 (最近3轮 = 6条)")

    assert len(prepared) == 6, "应该只保留最近3轮(6条消息)"
    print("  ✓ 对话上下文准备正确")

    conn.close()

    print("\n" + "="*60)
    print("🎉 所有测试通过!")
    print("="*60)
    print("\n多轮对话核心功能已验证:")
    print("  ✓ 上下文依赖检测")
    print("  ✓ 实体继承")
    print("  ✓ 代词解析")
    print("  ✓ 独立查询不继承")
    print("  ✓ 缓存键生成")
    print("  ✓ 对话上下文准备")
    print("\n功能开关状态:")
    from config.settings import CONVERSATION_ENABLED, CONVERSATION_BETA_USERS
    print(f"  CONVERSATION_ENABLED = {CONVERSATION_ENABLED}")
    print(f"  CONVERSATION_BETA_USERS = {CONVERSATION_BETA_USERS}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
