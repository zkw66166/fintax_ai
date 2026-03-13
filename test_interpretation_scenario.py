"""
Test: Financial metrics interpretation scenario detection
Verifies that financial_metrics queries are correctly detected and interpreted.
"""

import sys
sys.path.insert(0, '.')

from modules.interpretation_service import detect_scenario

def test_financial_metrics_scenario_detection():
    """Test: financial_metrics with metric_name should be detected correctly"""
    print("\n" + "="*70)
    print("Test: Financial Metrics Scenario Detection")
    print("="*70)

    # Test case 1: financial_metrics with multiple periods
    result1 = {
        'domain': 'financial_metrics',
        'results': [
            {
                'metric_name': '净利率',
                '2024年末': 25.5,
                '2025年末': 25.5,
                '变动': 0.0,
                'metric_unit': '%'
            },
            {
                'metric_name': '增值税税负率',
                '2024年末': 3.7,
                '2025年末': 3.7,
                '变动': 0.0,
                'metric_unit': '%'
            },
            {
                'metric_name': '企业所得税税负率',
                '2024年末': 8.5,
                '2025年末': 8.5,
                '变动': 0.0,
                'metric_unit': '%'
            }
        ]
    }

    scenario1 = detect_scenario(result1)
    print(f"\nTest Case 1: Multiple metrics, multiple periods")
    print(f"  Expected: financial_metrics_multi_period")
    print(f"  Got: {scenario1['scenario']}")

    if scenario1['scenario'] == 'financial_metrics_multi_period':
        print(f"  ✅ PASSED")
    else:
        print(f"  ❌ FAILED")
        return False

    # Test case 2: financial_metrics with single period
    result2 = {
        'domain': 'financial_metrics',
        'results': [
            {
                'metric_name': '净利率',
                '2024年末': 25.5,
                'metric_unit': '%'
            },
            {
                'metric_name': '增值税税负率',
                '2024年末': 3.7,
                'metric_unit': '%'
            }
        ]
    }

    scenario2 = detect_scenario(result2)
    print(f"\nTest Case 2: Multiple metrics, single period")
    print(f"  Expected: financial_metrics_single_period")
    print(f"  Got: {scenario2['scenario']}")

    if scenario2['scenario'] == 'financial_metrics_single_period':
        print(f"  ✅ PASSED")
    else:
        print(f"  ❌ FAILED")
        return False

    # Test case 3: Non-financial_metrics domain (should use old logic)
    result3 = {
        'domain': 'vat',
        'results': [
            {
                'period_year': 2024,
                'period_month': 3,
                'tax_due_total': 1000
            },
            {
                'period_year': 2025,
                'period_month': 3,
                'tax_due_total': 1200
            }
        ]
    }

    scenario3 = detect_scenario(result3)
    print(f"\nTest Case 3: Non-financial_metrics domain")
    print(f"  Expected: single_indicator_multi_period (or similar)")
    print(f"  Got: {scenario3['scenario']}")

    if scenario3['scenario'] != 'financial_metrics_multi_period':
        print(f"  ✅ PASSED (not using financial_metrics scenario)")
    else:
        print(f"  ❌ FAILED")
        return False

    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Financial Metrics Interpretation Fix - Test Suite")
    print("="*70)

    try:
        passed = test_financial_metrics_scenario_detection()

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
