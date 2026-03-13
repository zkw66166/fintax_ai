"""
Simplified test script to verify domain detection and quarterly period handling fixes.
"""

import sys
from modules.entity_preprocessor import detect_entities
from modules.intent_parser import parse_intent
from modules.db_utils import get_connection

def test_domain_detection():
    """Test Case 1: Domain Detection Fix"""
    print("\n" + "="*80)
    print("Test Case 1: Domain Detection Fix")
    print("="*80)

    query = "TSE科技有限公司 去年第四季度总资产、净利润、应纳企业所得税额情况"
    print(f"Query: {query}")

    # Step 1: Entity preprocessing
    conn = get_connection()
    try:
        entities = detect_entities(query, conn)
    finally:
        conn.close()

    print(f"\nEntity Preprocessing Result:")
    print(f"  taxpayer_id: {entities.get('taxpayer_id')}")
    print(f"  period_year: {entities.get('period_year')}")
    print(f"  period_quarter: {entities.get('period_quarter')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_end_month: {entities.get('period_end_month')}")
    print(f"  quarter_mode: {entities.get('quarter_mode')}")
    print(f"  domain_hint: {entities.get('domain_hint')}")
    print(f"  cross_domain_list (from entity_preprocessor): {entities.get('cross_domain_list')}")

    # Step 2: Intent parsing
    intent = parse_intent(query, entities, [])
    print(f"\nIntent Parsing Result:")
    print(f"  domain: {intent.get('domain')}")
    print(f"  cross_domain_list: {intent.get('cross_domain_list')}")

    # Verify
    expected_domains = ["balance_sheet", "eit", "profit"]
    actual_domains = intent.get('cross_domain_list', [])

    if set(actual_domains) == set(expected_domains):
        print(f"\n✅ PASS: Domain detection correct")
        print(f"   Expected: {sorted(expected_domains)}")
        print(f"   Actual:   {sorted(actual_domains)}")
        return True
    else:
        print(f"\n❌ FAIL: Domain detection incorrect")
        print(f"   Expected: {sorted(expected_domains)}")
        print(f"   Actual:   {sorted(actual_domains)}")
        if 'invoice' in actual_domains:
            print(f"   ERROR: 'invoice' should NOT be in cross_domain_list")
        return False

def test_quarterly_period_single():
    """Test Case 2: Single Quarter Period Handling"""
    print("\n" + "="*80)
    print("Test Case 2: Single Quarter Period Handling")
    print("="*80)

    query = "TSE科技有限公司 去年第四季度总资产、净利润情况"
    print(f"Query: {query}")

    # Entity preprocessing
    conn = get_connection()
    try:
        entities = detect_entities(query, conn)
    finally:
        conn.close()

    print(f"\nEntity Preprocessing Result:")
    print(f"  period_quarter: {entities.get('period_quarter')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_end_month: {entities.get('period_end_month')}")
    print(f"  quarter_mode: {entities.get('quarter_mode')}")

    # Verify
    expected_quarter_mode = 'single'
    expected_month = 12
    expected_end_month = None

    actual_quarter_mode = entities.get('quarter_mode')
    actual_month = entities.get('period_month')
    actual_end_month = entities.get('period_end_month')

    if (actual_quarter_mode == expected_quarter_mode and
        actual_month == expected_month and
        actual_end_month == expected_end_month):
        print(f"\n✅ PASS: Single quarter period handling correct")
        print(f"   quarter_mode: {actual_quarter_mode} (expected: {expected_quarter_mode})")
        print(f"   period_month: {actual_month} (expected: {expected_month})")
        print(f"   period_end_month: {actual_end_month} (expected: {expected_end_month})")
        return True
    else:
        print(f"\n❌ FAIL: Single quarter period handling incorrect")
        print(f"   quarter_mode: {actual_quarter_mode} (expected: {expected_quarter_mode})")
        print(f"   period_month: {actual_month} (expected: {expected_month})")
        print(f"   period_end_month: {actual_end_month} (expected: {expected_end_month})")
        return False

def test_quarterly_period_all():
    """Test Case 3: All Quarters Period Handling"""
    print("\n" + "="*80)
    print("Test Case 3: All Quarters Period Handling")
    print("="*80)

    query = "TSE科技有限公司 2025年各季度总资产、净利润情况"
    print(f"Query: {query}")

    # Entity preprocessing
    conn = get_connection()
    try:
        entities = detect_entities(query, conn)
    finally:
        conn.close()

    print(f"\nEntity Preprocessing Result:")
    print(f"  period_quarter: {entities.get('period_quarter')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_end_month: {entities.get('period_end_month')}")
    print(f"  quarter_mode: {entities.get('quarter_mode')}")
    print(f"  all_quarters: {entities.get('all_quarters')}")

    # Verify
    expected_quarter_mode = 'all'
    expected_all_quarters = True
    expected_month = 1
    expected_end_month = 12

    actual_quarter_mode = entities.get('quarter_mode')
    actual_all_quarters = entities.get('all_quarters')
    actual_month = entities.get('period_month')
    actual_end_month = entities.get('period_end_month')

    if (actual_quarter_mode == expected_quarter_mode and
        actual_all_quarters == expected_all_quarters and
        actual_month == expected_month and
        actual_end_month == expected_end_month):
        print(f"\n✅ PASS: All quarters period handling correct")
        print(f"   quarter_mode: {actual_quarter_mode} (expected: {expected_quarter_mode})")
        print(f"   all_quarters: {actual_all_quarters} (expected: {expected_all_quarters})")
        print(f"   period_month: {actual_month} (expected: {expected_month})")
        print(f"   period_end_month: {actual_end_month} (expected: {expected_end_month})")
        return True
    else:
        print(f"\n❌ FAIL: All quarters period handling incorrect")
        print(f"   quarter_mode: {actual_quarter_mode} (expected: {expected_quarter_mode})")
        print(f"   all_quarters: {actual_all_quarters} (expected: {expected_all_quarters})")
        print(f"   period_month: {actual_month} (expected: {expected_month})")
        print(f"   period_end_month: {actual_end_month} (expected: {expected_end_month})")
        return False

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Domain Detection and Quarterly Period Handling Fix - Test Suite")
    print("="*80)

    results = []

    # Test Case 1: Domain detection
    results.append(("Domain Detection", test_domain_detection()))

    # Test Case 2: Single quarter period handling
    results.append(("Single Quarter Period", test_quarterly_period_single()))

    # Test Case 3: All quarters period handling
    results.append(("All Quarters Period", test_quarterly_period_all()))

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)
