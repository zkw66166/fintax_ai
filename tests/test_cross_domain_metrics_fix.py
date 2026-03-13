#!/usr/bin/env python3
"""
Test script to verify cross-domain query metric extraction fix.

This script tests that the Stage 1 LLM correctly extracts metric names
for all domains after adding comprehensive metric mappings to the prompt.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mvp_pipeline import run_pipeline
from config.settings import DB_PATH
import sqlite3


def test_balance_sheet_metrics():
    """Test: Balance sheet metrics in cross-domain query"""
    print("\n" + "="*80)
    print("TEST 1: Balance Sheet + Profit Cross-Domain Query")
    print("="*80)

    query = "博雅文化传媒有限公司2025年各季度总资产、总负债和净利润情况"
    print(f"Query: {query}")

    result = run_pipeline(user_query=query)

    print(f"\nRoute: {result.get('route')}")
    print(f"Domain: {result.get('domain')}")

    if result.get('route') == 'financial_data':
        intent = result.get('entities', {})
        print(f"\nExtracted metrics: {intent.get('metrics', [])}")

        # Check if correct metrics were extracted
        expected_metrics = ['assets_end', 'liabilities_end', 'net_profit']
        actual_metrics = intent.get('metrics', [])

        if set(expected_metrics).issubset(set(actual_metrics)):
            print("✅ PASS: Correct metrics extracted")
        else:
            print(f"❌ FAIL: Expected {expected_metrics}, got {actual_metrics}")

        # Check if data was returned
        data = result.get('data', [])
        print(f"\nRows returned: {len(data)}")

        if len(data) > 0:
            print("✅ PASS: Data returned")
            print(f"Sample row: {data[0]}")
        else:
            print("❌ FAIL: No data returned")
    else:
        print(f"❌ FAIL: Wrong route: {result.get('route')}")

    return result


def test_cash_flow_metrics():
    """Test: Cash flow metrics in cross-domain query"""
    print("\n" + "="*80)
    print("TEST 2: Cash Flow + Profit Cross-Domain Query")
    print("="*80)

    query = "博雅文化传媒有限公司2025年经营活动现金流量净额和营业收入"
    print(f"Query: {query}")

    result = run_pipeline(user_query=query)

    print(f"\nRoute: {result.get('route')}")
    print(f"Domain: {result.get('domain')}")

    if result.get('route') == 'financial_data':
        intent = result.get('entities', {})
        print(f"\nExtracted metrics: {intent.get('metrics', [])}")

        # Check if correct metrics were extracted
        expected_metrics = ['operating_net_cash', 'operating_revenue']
        actual_metrics = intent.get('metrics', [])

        if set(expected_metrics).issubset(set(actual_metrics)):
            print("✅ PASS: Correct metrics extracted")
        else:
            print(f"❌ FAIL: Expected {expected_metrics}, got {actual_metrics}")

        # Check if data was returned
        data = result.get('data', [])
        print(f"\nRows returned: {len(data)}")

        if len(data) > 0:
            print("✅ PASS: Data returned")
        else:
            print("❌ FAIL: No data returned")
    else:
        print(f"❌ FAIL: Wrong route: {result.get('route')}")

    return result


def test_vat_metrics():
    """Test: VAT metrics (single domain, not cross-domain)"""
    print("\n" + "="*80)
    print("TEST 3: VAT Single Domain Query")
    print("="*80)

    query = "博雅文化传媒有限公司2025年1月销项税额、进项税额和应纳税额"
    print(f"Query: {query}")

    result = run_pipeline(user_query=query)

    print(f"\nRoute: {result.get('route')}")
    print(f"Domain: {result.get('domain')}")

    if result.get('route') == 'financial_data':
        intent = result.get('entities', {})
        print(f"\nExtracted metrics: {intent.get('metrics', [])}")

        # Check if data was returned
        data = result.get('data', [])
        print(f"\nRows returned: {len(data)}")

        if len(data) > 0:
            print("✅ PASS: Data returned")
        else:
            print("❌ FAIL: No data returned")
    else:
        print(f"❌ FAIL: Wrong route: {result.get('route')}")

    return result


def test_eit_metrics():
    """Test: EIT metrics (single domain)"""
    print("\n" + "="*80)
    print("TEST 4: EIT Quarterly Query")
    print("="*80)

    query = "博雅文化传媒有限公司2025年第1季度实际利润额和应纳税额"
    print(f"Query: {query}")

    result = run_pipeline(user_query=query)

    print(f"\nRoute: {result.get('route')}")
    print(f"Domain: {result.get('domain')}")

    if result.get('route') == 'financial_data':
        intent = result.get('entities', {})
        print(f"\nExtracted metrics: {intent.get('metrics', [])}")

        # Check if data was returned
        data = result.get('data', [])
        print(f"\nRows returned: {len(data)}")

        if len(data) > 0:
            print("✅ PASS: Data returned")
        else:
            print("❌ FAIL: No data returned")
    else:
        print(f"❌ FAIL: Wrong route: {result.get('route')}")

    return result


def test_complex_cross_domain():
    """Test: Complex cross-domain query with 4 domains"""
    print("\n" + "="*80)
    print("TEST 5: Complex Cross-Domain Query (4 domains)")
    print("="*80)

    query = "博雅文化传媒有限公司2025年总资产、经营现金流净额、净利润和资产负债率"
    print(f"Query: {query}")

    result = run_pipeline(user_query=query)

    print(f"\nRoute: {result.get('route')}")
    print(f"Domain: {result.get('domain')}")

    if result.get('route') == 'financial_data':
        intent = result.get('entities', {})
        print(f"\nExtracted metrics: {intent.get('metrics', [])}")
        print(f"Cross-domain list: {intent.get('cross_domain_list', [])}")

        # Check if correct metrics were extracted
        expected_metrics = ['assets_end', 'operating_net_cash', 'net_profit', '资产负债率']
        actual_metrics = intent.get('metrics', [])

        if set(expected_metrics).issubset(set(actual_metrics)):
            print("✅ PASS: Correct metrics extracted")
        else:
            print(f"❌ FAIL: Expected {expected_metrics}, got {actual_metrics}")

        # Check if data was returned
        data = result.get('data', [])
        print(f"\nRows returned: {len(data)}")

        if len(data) > 0:
            print("✅ PASS: Data returned")
        else:
            print("❌ FAIL: No data returned")
    else:
        print(f"❌ FAIL: Wrong route: {result.get('route')}")

    return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CROSS-DOMAIN METRICS FIX VERIFICATION")
    print("="*80)
    print("\nThis test verifies that the Stage 1 LLM correctly extracts")
    print("metric names for all domains after adding comprehensive mappings.")

    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"\n❌ ERROR: Database not found at {DB_PATH}")
        return

    # Check if test company exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?",
        ("91110108MA01AAAAA1",)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("\n❌ ERROR: Test company (博雅文化传媒有限公司) not found in database")
        return

    print(f"\nTest company: {row[0]}")

    # Run tests
    try:
        test_balance_sheet_metrics()
        test_cash_flow_metrics()
        test_vat_metrics()
        test_eit_metrics()
        test_complex_cross_domain()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        print("\nCheck the results above to verify:")
        print("1. Stage 1 extracts correct metric names (e.g., assets_end, not total_assets_end)")
        print("2. Cross-domain filtering keeps the metrics")
        print("3. Queries return data (> 0 rows)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
