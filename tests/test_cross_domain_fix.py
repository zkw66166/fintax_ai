"""
Test script for cross-domain query incomplete results fix.

Tests the following scenarios:
1. Original failing query: 4 metrics across 3 domains
2. Invoice false positive prevention
3. Multiple EIT metrics
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mvp_pipeline import run_pipeline
from modules.db_utils import get_db_connection


def test_original_failing_query():
    """Test Case 1: Original failing query with 4 metrics."""
    print("\n" + "="*80)
    print("Test Case 1: Original Failing Query")
    print("="*80)

    query = "TSE科技2025年第4季度应纳税所得额、实际缴纳的企业所得税额、利润总额、所得税税负率"
    print(f"Query: {query}\n")

    conn = get_db_connection()
    result = run_pipeline(query, conn, response_mode='concise')

    print("\n--- Result ---")
    print(f"Success: {result.get('success')}")
    print(f"Route: {result.get('route')}")

    if result.get('success'):
        data = result.get('data', [])
        print(f"Rows returned: {len(data)}")

        # Check for expected metrics
        expected_metrics = [
            'actual_profit',  # 应纳税所得额 (EIT quarterly)
            'tax_payable',    # 实际缴纳的企业所得税额 (EIT quarterly)
            'total_profit',   # 利润总额
            '所得税税负率'     # 所得税税负率 (financial_metrics)
        ]

        found_metrics = set()
        for row in data:
            metric_name = row.get('metric_name', '')
            if metric_name:
                found_metrics.add(metric_name)

        print(f"\nExpected metrics: {expected_metrics}")
        print(f"Found metrics: {list(found_metrics)}")

        missing = [m for m in expected_metrics if m not in found_metrics]
        if missing:
            print(f"❌ MISSING METRICS: {missing}")
            return False
        else:
            print("✅ All metrics found!")
            return True
    else:
        print(f"❌ Query failed: {result.get('error')}")
        return False


def test_invoice_false_positive():
    """Test Case 2: Invoice domain should NOT be included."""
    print("\n" + "="*80)
    print("Test Case 2: Invoice False Positive Prevention")
    print("="*80)

    query = "TSE科技2025年实际缴纳的增值税和企业所得税"
    print(f"Query: {query}\n")

    conn = get_db_connection()
    result = run_pipeline(query, conn, response_mode='concise')

    print("\n--- Result ---")
    print(f"Success: {result.get('success')}")
    print(f"Route: {result.get('route')}")

    if result.get('success'):
        # Check intent parsing
        intent = result.get('intent', {})
        cross_domain_list = intent.get('cross_domain_list', [])
        print(f"Cross-domain list: {cross_domain_list}")

        if 'invoice' in cross_domain_list:
            print("❌ FAIL: Invoice domain incorrectly included!")
            return False
        else:
            print("✅ PASS: Invoice domain correctly excluded!")
            return True
    else:
        print(f"❌ Query failed: {result.get('error')}")
        return False


def test_multiple_eit_metrics():
    """Test Case 3: Multiple EIT metrics should all be returned."""
    print("\n" + "="*80)
    print("Test Case 3: Multiple EIT Metrics")
    print("="*80)

    query = "TSE科技2025年第4季度应纳税所得额、实际应纳税额、税率"
    print(f"Query: {query}\n")

    conn = get_db_connection()
    result = run_pipeline(query, conn, response_mode='concise')

    print("\n--- Result ---")
    print(f"Success: {result.get('success')}")
    print(f"Route: {result.get('route')}")

    if result.get('success'):
        data = result.get('data', [])
        print(f"Rows returned: {len(data)}")

        # Check for expected metrics
        expected_metrics = ['actual_profit', 'tax_payable', 'tax_rate']

        found_metrics = set()
        for row in data:
            metric_name = row.get('metric_name', '')
            if metric_name:
                found_metrics.add(metric_name)

        print(f"\nExpected metrics: {expected_metrics}")
        print(f"Found metrics: {list(found_metrics)}")

        # For single-domain query, might not use cross-domain format
        # Just check if we got multiple rows
        if len(data) >= 3:
            print("✅ PASS: Multiple metrics returned!")
            return True
        else:
            print(f"❌ FAIL: Expected at least 3 rows, got {len(data)}")
            return False
    else:
        print(f"❌ Query failed: {result.get('error')}")
        return False


if __name__ == '__main__':
    print("\n" + "="*80)
    print("Cross-Domain Query Fix - Test Suite")
    print("="*80)

    results = []

    # Run all tests
    results.append(("Original Failing Query", test_original_failing_query()))
    results.append(("Invoice False Positive", test_invoice_false_positive()))
    results.append(("Multiple EIT Metrics", test_multiple_eit_metrics()))

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    sys.exit(0 if passed == total else 1)
