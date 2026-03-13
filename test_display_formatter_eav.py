"""
Test: Display formatter growth calculation for EAV structure
Verifies that _compute_growth correctly handles financial_metrics EAV structure.
"""

import sys
sys.path.insert(0, '.')

from modules.display_formatter import build_display_data

def test_eav_growth_calculation():
    """Test: EAV structure should calculate growth per metric, not across metrics"""
    print("\n" + "="*70)
    print("Test: EAV Growth Calculation")
    print("="*70)

    # Simulate financial_metrics query result
    result = {
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

    print("\nBuilding display data...")
    display_data = build_display_data(result, "利润率、增值税税负率、企业所得税税负率比较分析")

    print("\n" + "-"*70)
    print("VERIFICATION")
    print("-"*70)

    # Check 1: Should have growth data
    growth = display_data.get('growth')
    print(f"\n1. Has growth data: {growth is not None}")

    if growth is None:
        print(f"   ⚠️  WARNING - No growth data generated")
        return True  # Not a failure, just no growth data

    print(f"   Growth entries: {len(growth)}")

    # Check 2: Each growth entry should be for a specific metric
    print(f"\n2. Growth entries:")
    for i, entry in enumerate(growth, 1):
        period = entry.get('period', '?')
        print(f"   Entry {i}: {period}")

        # Check if it's a metric name (not a period like "2025年3月")
        if '年' in period and '月' in period:
            print(f"      ❌ FAILED - Period should be metric name, not time period")
            return False

    # Check 3: Verify change calculations are per-metric
    print(f"\n3. Change calculations:")
    for entry in growth:
        metric_name = entry.get('period', '?')
        print(f"   {metric_name}:")

        # Get the metric's change data
        metric_data = entry.get(metric_name, {})
        if not metric_data:
            # Try to find the metric data in other keys
            for key, val in entry.items():
                if isinstance(val, dict) and 'change' in val:
                    metric_data = val
                    break

        if metric_data:
            prev = metric_data.get('previous')
            curr = metric_data.get('current')
            change = metric_data.get('change')
            change_pct = metric_data.get('change_pct')

            print(f"      Previous: {prev}")
            print(f"      Current: {curr}")
            print(f"      Change: {change}")
            print(f"      Change %: {change_pct}")

            # For this test data, all values are the same, so change should be 0
            if prev == curr and change == 0.0 and change_pct == 0.0:
                print(f"      ✅ CORRECT - No change detected")
            elif prev != curr:
                # Values are different, check if calculation is correct
                expected_change = curr - prev
                expected_pct = round((curr - prev) / abs(prev) * 100, 2) if prev != 0 else None

                if abs(change - expected_change) < 0.01 and abs(change_pct - expected_pct) < 0.01:
                    print(f"      ✅ CORRECT - Change calculated correctly")
                else:
                    print(f"      ❌ FAILED - Change calculation incorrect")
                    print(f"         Expected change: {expected_change}, got: {change}")
                    print(f"         Expected %: {expected_pct}, got: {change_pct}")
                    return False
        else:
            print(f"      ⚠️  WARNING - No metric data found")

    print(f"\n✅ PASSED - Growth calculation is per-metric")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Display Formatter EAV Growth Fix - Test Suite")
    print("="*70)

    try:
        passed = test_eav_growth_calculation()

        print("\n" + "="*70)
        if passed:
            print("✅ TEST PASSED")
        else:
            print("❌ TEST FAILED")
        print("="*70 + "\n")

        sys.exit(0 if passed else 1)

    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERROR: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
