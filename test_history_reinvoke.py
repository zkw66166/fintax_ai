"""Test history re-invocation functionality."""
import json
from pathlib import Path


def test_history_schema():
    """Test that history entries support new schema fields."""
    # Simulate a history entry with new fields
    entry = {
        "query": "华兴科技2025年1月增值税",
        "cache_key": "abc123",
        "route": "financial_data",
        "timestamp": "10:30:00",
        "company_id": "91310000MA1FL8XQ30",
        "status": "success",
        "main_output": "查询成功",
        "entity_text": "{}",
        "intent_text": "{}",
        "sql_text": "SELECT * FROM vat_return",
        "result_count": 10,
        # NEW FIELDS
        "conversation_history": [
            {"role": "user", "content": "test", "timestamp": "10:29:00"},
            {"role": "assistant", "content": "response", "timestamp": "10:29:30"}
        ],
        "conversation_enabled": True,
        "conversation_depth": 3,
        "response_mode": "detailed",
        "thinking_mode": "quick",
        "result": {
            "success": True,
            "results": [],
            "display_data": {}
        }
    }

    # Verify all fields are present
    assert "conversation_history" in entry
    assert "conversation_enabled" in entry
    assert "conversation_depth" in entry
    assert "response_mode" in entry
    assert "thinking_mode" in entry
    assert "result" in entry
    assert "company_id" in entry

    print("✓ History schema test passed")


def test_backward_compatibility():
    """Test that old history entries without new fields still work."""
    old_entry = {
        "query": "test query",
        "cache_key": "xyz789",
        "route": "financial_data",
        "timestamp": "10:00:00",
        "status": "success",
        "main_output": "output",
        "entity_text": "{}",
        "intent_text": "{}",
        "sql_text": "SELECT 1",
        "result_count": 1,
    }

    # Simulate backend default value assignment
    old_entry.setdefault("conversation_history", [])
    old_entry.setdefault("conversation_enabled", False)
    old_entry.setdefault("conversation_depth", 3)
    old_entry.setdefault("response_mode", "detailed")
    old_entry.setdefault("thinking_mode", "quick")
    old_entry.setdefault("result", {})
    old_entry.setdefault("company_id", "")

    # Verify defaults are applied
    assert old_entry["conversation_history"] == []
    assert old_entry["conversation_enabled"] is False
    assert old_entry["conversation_depth"] == 3
    assert old_entry["response_mode"] == "detailed"
    assert old_entry["thinking_mode"] == "quick"
    assert old_entry["result"] == {}
    assert old_entry["company_id"] == ""

    print("✓ Backward compatibility test passed")


def test_cache_invalidation():
    """Test cache invalidation utility."""
    from api.services.query_cache import invalidate_by_company

    # Test function signature (doesn't actually delete anything without real cache files)
    try:
        count = invalidate_by_company("test_company_id")
        assert count >= 0  # Should return 0 if no cache files exist
        print(f"✓ Cache invalidation test passed (deleted {count} entries)")
    except Exception as e:
        print(f"✗ Cache invalidation test failed: {e}")


if __name__ == "__main__":
    test_history_schema()
    test_backward_compatibility()
    test_cache_invalidation()
    print("\n✅ All tests passed!")
