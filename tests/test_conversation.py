"""测试对话上下文功能"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules.conversation_manager import (
    is_context_dependent,
    extract_last_turn_entities,
    prepare_conversation_context,
)
from modules.entity_preprocessor import detect_entities_with_context
from modules.db_utils import get_connection


def test_context_dependent_detection():
    """测试上下文依赖检测"""
    print("\n=== 测试上下文依赖检测 ===")

    test_cases = [
        ("华兴科技2025年1月的增值税", False),  # 独立查询
        ("2月呢？", True),  # 隐式时间
        ("它的利润", True),  # 代词
        ("那个指标", True),  # 代词
        ("对比一下", True),  # 对比
        ("资产负债率", False),  # 独立查询
    ]

    for query, expected in test_cases:
        result = is_context_dependent(query)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{query}' → {result} (expected: {expected})")


def test_entity_extraction_with_context():
    """测试带上下文的实体提取"""
    print("\n=== 测试带上下文的实体提取 ===")

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

    # 测试1：隐式时间继承
    print("\n测试1：隐式时间继承")
    query1 = "2月呢？"
    entities1 = detect_entities_with_context(query1, conn, conversation_history)
    print(f"查询: {query1}")
    print(f"继承的实体: taxpayer_id={entities1.get('taxpayer_id')}, "
          f"period_year={entities1.get('period_year')}, "
          f"period_month={entities1.get('period_month')}")

    # 测试2：代词解析
    print("\n测试2：代词解析")
    query2 = "它的利润"
    entities2 = detect_entities_with_context(query2, conn, conversation_history)
    print(f"查询: {query2}")
    print(f"继承的实体: taxpayer_id={entities2.get('taxpayer_id')}, "
          f"taxpayer_name={entities2.get('taxpayer_name')}")

    # 测试3：独立查询（不继承）
    print("\n测试3：独立查询（不继承）")
    query3 = "鑫源贸易2025年3月的增值税"
    entities3 = detect_entities_with_context(query3, conn, conversation_history)
    print(f"查询: {query3}")
    print(f"实体: taxpayer_id={entities3.get('taxpayer_id')}, "
          f"period_year={entities3.get('period_year')}, "
          f"period_month={entities3.get('period_month')}")

    conn.close()


def test_conversation_context_preparation():
    """测试对话上下文准备"""
    print("\n=== 测试对话上下文准备 ===")

    # 模拟长对话历史（10轮）
    history = []
    for i in range(10):
        history.append({
            "role": "user",
            "content": f"查询{i+1}",
            "timestamp": f"2026-03-02T10:{i:02d}:00Z",
        })
        history.append({
            "role": "assistant",
            "content": f"结果{i+1}",
            "timestamp": f"2026-03-02T10:{i:02d}:05Z",
        })

    # 测试滑动窗口（最近3轮）
    prepared = prepare_conversation_context(history, max_turns=3)
    print(f"原始历史: {len(history)} 条消息")
    print(f"准备后: {len(prepared)} 条消息（最近3轮 = 6条消息）")
    print(f"第一条: {prepared[0]['content']}")
    print(f"最后一条: {prepared[-1]['content']}")


def test_cache_key_generation():
    """测试缓存键生成"""
    print("\n=== 测试缓存键生成 ===")

    from modules.cache_manager import _generate_context_aware_cache_key

    # 独立查询
    key1 = _generate_context_aware_cache_key(
        "华兴科技2025年1月的增值税",
        "一般纳税人",
        [],
        None
    )
    print(f"独立查询缓存键: {key1[:16]}...")

    # 上下文依赖查询
    conversation_history = [
        {
            "role": "assistant",
            "metadata": {
                "entities": {
                    "taxpayer_id": "91310000MA1FL8XQ30",
                    "period_year": 2025,
                    "period_month": 1,
                    "domain_hint": "vat",
                }
            }
        }
    ]
    key2 = _generate_context_aware_cache_key(
        "2月呢？",
        "一般纳税人",
        [],
        conversation_history
    )
    print(f"上下文依赖查询缓存键: {key2[:16]}...")
    print(f"两个键不同: {key1 != key2}")


if __name__ == "__main__":
    test_context_dependent_detection()
    test_entity_extraction_with_context()
    test_conversation_context_preparation()
    test_cache_key_generation()

    print("\n✅ 所有测试完成")
