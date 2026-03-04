#!/usr/bin/env python
"""Test empty data message functionality."""

from mvp_pipeline import run_pipeline
import json

def test_empty_data_message():
    """Test that empty results show friendly message."""

    # Test 1: Query with no data (TSE科技 2026年2月)
    print("=" * 60)
    print("Test 1: Query with no data")
    print("=" * 60)
    query1 = 'TSE科技有限公司最新资产负债率是多少?'
    print(f"Query: {query1}\n")

    result1 = run_pipeline(query1)

    print("\nResult:")
    print(f"  Success: {result1.get('success')}")
    print(f"  Results count: {len(result1.get('results', []))}")
    print(f"  Empty data message: {result1.get('empty_data_message', 'N/A')}")

    assert result1.get('success') == True, "Query should succeed"
    assert len(result1.get('results', [])) == 0, "Should have no results"
    assert 'empty_data_message' in result1, "Should have empty_data_message"
    assert 'TSE科技有限公司' in result1['empty_data_message'], "Message should include company name"
    assert '2026年2月' in result1['empty_data_message'], "Message should include period"

    print("\n✅ Test 1 passed!")

    # Test 2: Query with data (华兴科技 2026年2月)
    print("\n" + "=" * 60)
    print("Test 2: Query with data")
    print("=" * 60)
    query2 = '华兴科技有限公司2026年2月资产负债率是多少?'
    print(f"Query: {query2}\n")

    result2 = run_pipeline(query2)

    print("\nResult:")
    print(f"  Success: {result2.get('success')}")
    print(f"  Results count: {len(result2.get('results', []))}")
    print(f"  Has empty_data_message: {'empty_data_message' in result2}")

    assert result2.get('success') == True, "Query should succeed"
    assert len(result2.get('results', [])) > 0, "Should have results"
    assert 'empty_data_message' not in result2, "Should not have empty_data_message when data exists"

    print("\n✅ Test 2 passed!")

    print("\n" + "=" * 60)
    print("All tests passed! ✅")
    print("=" * 60)

if __name__ == '__main__':
    test_empty_data_message()
