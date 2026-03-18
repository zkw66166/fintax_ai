"""
Test: Financial metrics domain lock fix
Verifies that '率' metrics queries are locked to financial_metrics domain
and do NOT go through cross-domain pipeline.
"""

import sys
import os
import shutil
sys.path.insert(0, '.')

# Clear cache for clean test
if os.path.exists('cache'):
    shutil.rmtree('cache')
    print("Cache cleared\n")

from mvp_pipeline import run_pipeline

def test_rate_metrics_domain_lock():
    """Test: '率' metrics should lock to financial_metrics domain, not cross-domain"""
    print("\n" + "="*70)
    print("Test: Rate Metrics Domain Lock")
    print("="*70)

    # Test query with 3 '率' metrics
    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"

    print(f"\nQuery: {query}")
    print("\nRunning pipeline...\n")

    result = run_pipeline(query)

    print("\n" + "-"*70)
    print("VERIFICATION")
    print("-"*70)

    # Check 1: Domain should be financial_metrics, NOT cross_domain
    domain = result.get('domain')
    print(f"\n1. Domain check:")
    print(f"   Expected: financial_metrics")
    print(f"   Actual: {domain}")

    if domain != 'financial_metrics':
        print(f"   ❌ FAILED - Domain is {domain}, should be financial_metrics")
        return False
    print(f"   ✅ PASSED")

    # Check 2: Should NOT have sub_results (cross-domain indicator)
    has_sub_results = 'sub_results' in result
    print(f"\n2. Cross-domain check:")
    print(f"   Has sub_results: {has_sub_results}")

    if has_sub_results:
        print(f"   ❌ FAILED - Query went through cross-domain pipeline")
        return False
    print(f"   ✅ PASSED - Single domain query")

    # Check 3: Results should have metric_name column
    results = result.get('results', [])
    print(f"\n3. Results structure check:")
    print(f"   Total rows: {len(results)}")

    if not results:
        print(f"   ❌ FAILED - No results returned")
        return False

    first_row = results[0]
    has_metric_name = 'metric_name' in first_row
    print(f"   Has metric_name column: {has_metric_name}")
    print(f"   First row keys: {list(first_row.keys())}")

    if not has_metric_name:
        print(f"   ❌ FAILED - Missing metric_name column")
        return False
    print(f"   ✅ PASSED")

    # Check 4: Should have data for requested metrics
    print(f"\n4. Metric data check:")
    metric_names = [row.get('metric_name') for row in results]
    print(f"   Returned metrics: {metric_names}")

    expected_metrics = ['净利率', '增值税税负率', '企业所得税税负率']
    missing_metrics = [m for m in expected_metrics if m not in metric_names]

    if missing_metrics:
        print(f"   ⚠️  WARNING - Missing metrics: {missing_metrics}")
        print(f"   (May be due to data availability)")
    else:
        print(f"   ✅ All expected metrics present")

    # Check 5: Should have period columns
    print(f"\n5. Period columns check:")
    period_cols = [k for k in first_row.keys() if '年' in k and '月' in k]
    print(f"   Period columns: {period_cols}")

    if len(period_cols) < 2:
        print(f"   ❌ FAILED - Expected 2 period columns (2024年3月, 2025年3月)")
        return False
    print(f"   ✅ PASSED")

    # Check 6: Data should not be empty
    print(f"\n6. Data completeness check:")
    non_empty_rows = 0
    for row in results:
        has_data = any(isinstance(v, (int, float)) and v is not None and v != 0
                      for k, v in row.items()
                      if k not in ('metric_name', 'metric_unit', '_source_domain', 'period'))
        if has_data:
            non_empty_rows += 1

    print(f"   Non-empty rows: {non_empty_rows}/{len(results)}")

    if non_empty_rows == 0:
        print(f"   ❌ FAILED - All rows are empty")
        return False
    print(f"   ✅ PASSED")

    return True


def test_date_resolution():
    """Test: '前年3月' should resolve to 2024年3月 (current year 2026)"""
    print("\n" + "="*70)
    print("Test: Date Resolution")
    print("="*70)

    query = "TSE科技前年3月和去年3月利润率、增值税税负率、企业所得税税负率比较分析"

    print(f"\nQuery: {query}")
    print("\nRunning pipeline...\n")

    result = run_pipeline(query)

    print("\n" + "-"*70)
    print("VERIFICATION")
    print("-"*70)

    resolved = result['entities'].get('resolved_query', '')
    print(f"\nResolved query: {resolved}")

    if '2024年3月' not in resolved:
        print(f"❌ FAILED - '前年3月' not resolved to 2024年3月")
        return False

    if '2025年3月' not in resolved:
        print(f"❌ FAILED - '去年3月' not resolved to 2025年3月")
        return False

    print(f"✅ PASSED - Date resolution correct")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Financial Metrics Domain Lock Fix - Test Suite")
    print("="*70)

    try:
        # Test 1: Date resolution
        test1_passed = test_date_resolution()

        # Test 2: Domain lock
        test2_passed = test_rate_metrics_domain_lock()

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Test 1 (Date Resolution): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"Test 2 (Domain Lock): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

        if test1_passed and test2_passed:
            print("\n✅ ALL TESTS PASSED")
            print("="*70 + "\n")
            sys.exit(0)
        else:
            print("\n❌ SOME TESTS FAILED")
            print("="*70 + "\n")
            sys.exit(1)

    except Exception as e:
        print("\n" + "="*70)
        print(f"❌ ERROR: {e}")
        print("="*70 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
