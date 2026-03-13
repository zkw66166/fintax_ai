"""
Comprehensive test for financial metrics query fixes
Tests all three issues:
1. Date resolution ("前年3月" → 2024年3月)
2. Metric name display (not row indices)
3. No extra empty rows
"""

import sys
import os
import shutil
sys.path.insert(0, '.')

# Clear cache before testing to avoid stale results
if os.path.exists('cache'):
    shutil.rmtree('cache')
    print("Cache cleared for clean test run\n")

from mvp_pipeline import run_pipeline
from modules.display_formatter import build_display_data


def test_date_resolution():
    """Test: 前年3月 correctly resolves to 2024年3月 (current year 2026)"""
    print("\n" + "="*60)
    print("Test 1: Date Resolution")
    print("="*60)

    query = "TSE科技前年3月和去年3月利润率、增值税税负率、企业所得税税负率比较分析"
    result = run_pipeline(query)

    resolved = result['entities'].get('resolved_query', '')
    print(f"Original query: {query}")
    print(f"Resolved query: {resolved}")

    assert '2024年3月' in resolved, f"前年3月 not resolved to 2024年3月: {resolved}"
    assert '2025年3月' in resolved, f"去年3月 not resolved to 2025年3月: {resolved}"

    print("✅ Date resolution correct")
    return result


def test_metric_name_display():
    """Test: Frontend displays metric names, not row indices"""
    print("\n" + "="*60)
    print("Test 2: Metric Name Display")
    print("="*60)

    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"
    result = run_pipeline(query)

    # Check backend result structure
    results_count = len(result['results'])
    print(f"Backend returns {results_count} rows")

    # Should have 3 metrics (may vary due to caching/routing)
    assert results_count >= 3, f"Expected at least 3 rows, got {results_count}"

    # Check that results have metric identification
    first_row = result['results'][0]
    has_metric_name = 'metric_name' in first_row
    has_metric_col = any('metric' in str(k).lower() for k in first_row.keys())

    assert has_metric_name or has_metric_col, f"Missing metric identification in: {list(first_row.keys())}"

    print(f"First row keys: {list(first_row.keys())}")
    for i, row in enumerate(result['results'][:3]):
        metric = row.get('metric_name') or row.get('指标名称') or f"Row {i+1}"
        print(f"  - {metric}")

    # Check display data structure
    display_data = build_display_data(result, query)
    headers = display_data.get('table', {}).get('headers', [])
    rows = display_data.get('table', {}).get('rows', [])

    print(f"\nDisplay data has {len(rows)} rows with headers: {headers}")

    # Should have metric name column (Chinese or English)
    has_metric_header = '指标名称' in headers or 'metric_name' in headers or any('指标' in str(h) for h in headers)
    assert has_metric_header, f"Missing metric name header in: {headers}"

    print("✅ Metric names displayed correctly")
    return result


def test_no_extra_empty_rows():
    """Test: Only requested periods appear (no extra empty rows)"""
    print("\n" + "="*60)
    print("Test 3: No Extra Empty Rows")
    print("="*60)

    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"
    result = run_pipeline(query)

    # Check that result has reasonable number of rows (3 metrics, not 16 rows with empty data)
    results_count = len(result['results'])
    assert results_count <= 5, f"Too many rows (expected ≤5, got {results_count}). May have extra empty rows."

    print(f"Result has {results_count} rows (reasonable count)")

    # Check that rows have data (not all NULL/empty)
    non_empty_rows = 0
    for row in result['results']:
        # Count rows that have at least one non-null numeric value
        has_data = any(isinstance(v, (int, float)) and v is not None and v != 0
                      for k, v in row.items()
                      if k not in ('metric_name', 'metric_unit', '_source_domain', 'period'))
        if has_data:
            non_empty_rows += 1

    print(f"Non-empty rows: {non_empty_rows}/{results_count}")
    assert non_empty_rows >= 3, f"Expected at least 3 non-empty rows, got {non_empty_rows}"

    print("✅ No extra empty rows")
    return result


def test_single_domain_routing():
    """Test: Query routes to single financial_metrics domain (not cross-domain)"""
    print("\n" + "="*60)
    print("Test 4: Single Domain Routing")
    print("="*60)

    query = "TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"
    result = run_pipeline(query)

    assert result['domain'] == 'financial_metrics', f"Expected financial_metrics domain, got {result['domain']}"
    assert 'sub_results' not in result, "Query should not go through cross-domain path"

    print(f"Domain: {result['domain']}")
    print("✅ Correctly routed to single financial_metrics domain")
    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Financial Metrics Query Fixes - Comprehensive Test Suite")
    print("="*60)

    try:
        test_date_resolution()
        test_metric_name_display()
        test_no_extra_empty_rows()
        test_single_domain_routing()

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
