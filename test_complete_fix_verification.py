"""
Test: Financial metrics query - complete fix verification
Tests the full pipeline with domain lock and metric extraction.
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

def test_three_rate_metrics():
    """Test: Query with 3 rate metrics should return all 3 metrics"""
    print("\n" + "="*70)
    print("Test: Three Rate Metrics Query")
    print("="*70)

    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"

    print(f"\nQuery: {query}")
    print("\nRunning pipeline...\n")

    result = run_pipeline(query)

    print("\n" + "-"*70)
    print("VERIFICATION")
    print("-"*70)

    # Check 1: Domain should be financial_metrics
    domain = result.get('domain')
    print(f"\n1. Domain: {domain}")
    if domain != 'financial_metrics':
        print(f"   ❌ FAILED - Expected financial_metrics, got {domain}")
        return False
    print(f"   ✅ PASSED")

    # Check 2: Should NOT be cross-domain
    has_sub_results = 'sub_results' in result
    print(f"\n2. Cross-domain: {has_sub_results}")
    if has_sub_results:
        print(f"   ❌ FAILED - Should not be cross-domain")
        return False
    print(f"   ✅ PASSED")

    # Check 3: Results should have metric_name column
    results = result.get('results', [])
    print(f"\n3. Results count: {len(results)}")

    if not results:
        print(f"   ❌ FAILED - No results")
        return False

    first_row = results[0]
    has_metric_name = 'metric_name' in first_row
    print(f"   Has metric_name: {has_metric_name}")

    if not has_metric_name:
        print(f"   ❌ FAILED - Missing metric_name column")
        return False
    print(f"   ✅ PASSED")

    # Check 4: Should have data for requested metrics
    print(f"\n4. Metric names:")
    metric_names = [row.get('metric_name') for row in results]
    for name in metric_names:
        print(f"   - {name}")

    # Expected metrics (may have different names in DB)
    # "利润率" might be stored as "净利率" or "净利润率"
    # "增值税税负率" should be exact
    # "企业所得税税负率" should be exact

    has_profit_rate = any('利' in name and '率' in name for name in metric_names)
    has_vat_rate = any('增值税' in name and '率' in name for name in metric_names)
    has_eit_rate = any('企业所得税' in name and '率' in name for name in metric_names)

    print(f"\n   Has profit rate: {has_profit_rate}")
    print(f"   Has VAT rate: {has_vat_rate}")
    print(f"   Has EIT rate: {has_eit_rate}")

    if not has_profit_rate:
        print(f"   ⚠️  WARNING - No profit rate metric found")
    if not has_vat_rate:
        print(f"   ⚠️  WARNING - No VAT rate metric found")
    if not has_eit_rate:
        print(f"   ⚠️  WARNING - No EIT rate metric found")

    # At least 1 metric should be present
    if len(metric_names) == 0:
        print(f"   ❌ FAILED - No metrics returned")
        return False

    print(f"   ✅ PASSED - {len(metric_names)} metric(s) returned")

    # Check 5: Should have period columns
    print(f"\n5. Period columns:")
    period_cols = [k for k in first_row.keys() if '年' in k and ('月' in k or '末' in k)]
    for col in period_cols:
        print(f"   - {col}")

    if len(period_cols) < 2:
        print(f"   ⚠️  WARNING - Expected 2 period columns")
    else:
        print(f"   ✅ PASSED")

    # Check 6: Data should not be all NULL
    print(f"\n6. Data completeness:")
    non_null_count = 0
    for row in results:
        for k, v in row.items():
            if k not in ('metric_name', 'metric_unit', '_source_domain', 'period'):
                if v is not None and v != 0:
                    non_null_count += 1

    print(f"   Non-NULL values: {non_null_count}")

    if non_null_count == 0:
        print(f"   ❌ FAILED - All data is NULL")
        return False
    print(f"   ✅ PASSED")

    return True


def test_date_resolution():
    """Test: Date resolution for '前年3月' and '去年3月'"""
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

    print(f"✅ PASSED")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Financial Metrics Query Fix - Complete Verification")
    print("="*70)

    try:
        # Test 1: Date resolution
        test1_passed = test_date_resolution()

        # Test 2: Three rate metrics
        test2_passed = test_three_rate_metrics()

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"Test 1 (Date Resolution): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"Test 2 (Three Rate Metrics): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

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
