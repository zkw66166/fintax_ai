"""
Test: Rate metrics extraction
Verifies that extract_all_rate_metrics() correctly extracts all rate metrics from query.
"""

import sys
sys.path.insert(0, '.')

from modules.metric_calculator import extract_all_rate_metrics

def test_extract_all_rate_metrics():
    """Test: extract_all_rate_metrics should find all rate metrics"""
    print("\n" + "="*70)
    print("Test: Extract All Rate Metrics")
    print("="*70)

    test_cases = [
        {
            'query': '利润率、增值税税负率、企业所得税税负率比较分析',
            'expected': ['增值税税负率', '企业所得税税负率', '利润率'],
            'description': 'Three rate metrics'
        },
        {
            'query': '2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析',
            'expected': ['增值税税负率', '企业所得税税负率', '利润率'],
            'description': 'Three rate metrics with periods'
        },
        {
            'query': '净利润率和毛利率',
            'expected': ['净利润率', '毛利率'],
            'description': 'Two profit rate metrics'
        },
        {
            'query': '资产负债率、流动比率',
            'expected': ['资产负债率', '流动比率'],
            'description': 'Debt ratio and current ratio'
        },
        {
            'query': 'ROE和ROA分析',
            'expected': ['ROE', 'ROA'],
            'description': 'English abbreviations'
        },
    ]

    all_passed = True
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {case['description']}")
        print(f"  Query: {case['query']}")

        result = extract_all_rate_metrics(case['query'])
        print(f"  Expected: {case['expected']}")
        print(f"  Got: {result}")

        # Check if all expected metrics are found
        missing = [m for m in case['expected'] if m not in result]
        extra = [m for m in result if m not in case['expected']]

        if missing:
            print(f"  ❌ FAILED - Missing metrics: {missing}")
            all_passed = False
        elif extra:
            print(f"  ⚠️  WARNING - Extra metrics: {extra}")
        else:
            print(f"  ✅ PASSED")

    return all_passed


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Rate Metrics Extraction - Test Suite")
    print("="*70)

    try:
        passed = test_extract_all_rate_metrics()

        print("\n" + "="*70)
        if passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("="*70 + "\n")

        sys.exit(0 if passed else 1)

    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERROR: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
