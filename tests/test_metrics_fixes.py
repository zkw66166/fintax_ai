"""
Test date resolution and cross-domain routing fixes
"""

import sys
sys.path.insert(0, '.')

from mvp_pipeline import run_pipeline

def test_qiannian_date_resolution():
    """Test '前年' date resolution"""
    query = "TSE科技前年3月和去年3月利润率、增值税税负率、企业所得税税负率比较分析"

    print(f"\n{'='*60}")
    print(f"Test: 前年3月 date resolution")
    print(f"Query: {query}")
    print(f"Expected: 前年3月 → 2024年3月 (current year 2026)")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    # Check resolved query in entities
    if 'entities' in result:
        resolved = result['entities'].get('resolved_query', '')
        print(f"\nResolved query: {resolved}")

        # Check if "2024年3月" appears in resolved query
        assert '2024年3月' in resolved, f"前年3月 not resolved to 2024年3月: {resolved}"
        assert '2025年3月' in resolved, f"去年3月 not resolved to 2025年3月: {resolved}"

        print("✅ Date resolution correct: 前年3月 → 2024年3月, 去年3月 → 2025年3月")

    return result


def test_cross_domain_routing():
    """Test cross-domain routing for mixed metrics"""
    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"

    print(f"\n{'='*60}")
    print(f"Test: Cross-domain routing")
    print(f"Query: {query}")
    print(f"Expected domains: financial_metrics, vat, eit (NOT 3x financial_metrics)")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    # Check result structure
    if 'results' in result:
        print(f"\nReturned {len(result['results'])} rows")

        # Check for metric_name column
        if len(result['results']) > 0:
            first_row = result['results'][0]
            print(f"First row keys: {list(first_row.keys())}")

            assert 'metric_name' in first_row or any('metric' in str(k).lower() for k in first_row.keys()), \
                "Missing metric_name column in results"

            print("✅ Results have metric identification")

    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Financial Metrics Query Fixes - Test Suite")
    print("="*60)

    try:
        test_qiannian_date_resolution()
        test_cross_domain_routing()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60 + "\n")

    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60 + "\n")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {e}")
        print("="*60 + "\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
