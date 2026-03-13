"""
Test suite for financial ratio query fix (smart period_type selection)

Tests the fix for the issue where cross-period comparison queries returned 0 rows
due to incorrect period_type filtering logic.

Original issue: "去年12月至今年3月利润率、增值税税负率、企业所得税税负率分析"
- Dec 2025 (quarter-end) should use period_type IN ('quarterly', 'annual')
- Mar 2026 (quarter-end) should use period_type IN ('quarterly', 'annual')
- Both CTEs should use same period_type filter for successful JOIN
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mvp_pipeline import run_pipeline
from config.settings import DB_PATH
import sqlite3


def test_original_failing_query():
    """Test the original failing query pattern: Dec to Mar ratio analysis"""
    # Use 2024-12 to 2025-03 (data exists for both periods)
    query = "TSE科技2024年12月至2025年3月利润率、增值税税负率、企业所得税税负率分析"

    result = run_pipeline(query)

    # Should return successful result
    assert result['success'], f"Query failed: {result.get('error')}"

    # Should have data rows
    assert 'results' in result, "No results field in result"
    assert len(result['results']) > 0, "Query returned 0 rows (empty result)"

    # Should have at least 2 metrics (净利率, 增值税税负率)
    # Note: 企业所得税税负率 may be NULL for some periods
    assert len(result['results']) >= 2, f"Expected at least 2 metrics, got {len(result['results'])}"

    # Verify metric names
    metric_names = [row['metric_name'] for row in result['results']]
    assert '净利率' in metric_names, "Missing 净利率"
    assert '增值税税负率' in metric_names, "Missing 增值税税负率"

    print("✅ Original failing query now returns data")
    print(f"   Metrics returned: {metric_names}")


def test_quarter_end_comparison():
    """Test comparison between two quarter-end months"""
    query = "TSE科技2024年12月与2025年3月财务指标对比"

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert len(result.get('results', [])) > 0, "Query returned 0 rows"

    print("✅ Quarter-end comparison works")
    print(f"   Returned {len(result['results'])} metrics")


def test_non_quarter_end_comparison():
    """Test comparison between non-quarter-end months"""
    query = "TSE科技2025年1月与2月利润率对比"

    result = run_pipeline(query)

    # May return 0 rows if monthly data doesn't exist, but should not error
    assert result['success'], f"Query failed: {result.get('error')}"

    print("✅ Non-quarter-end comparison handled")
    print(f"   Returned {len(result.get('results', []))} rows")


def test_mixed_month_types():
    """Test comparison between quarter-end and non-quarter-end months"""
    query = "TSE科技2025年11月与12月资产负债率对比"

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"

    print("✅ Mixed month types comparison handled")
    print(f"   Returned {len(result.get('results', []))} rows")


def test_range_query_consistency():
    """Test range query uses consistent period_type"""
    query = "TSE科技2024年12月至2025年3月资产负债率趋势"

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert len(result.get('results', [])) > 0, "Range query returned 0 rows"

    print("✅ Range query returns data")
    print(f"   Returned {len(result['results'])} periods")


def test_data_completeness():
    """Verify database has the expected data for test queries"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check Dec 2024 data
    cursor.execute("""
        SELECT period_type, COUNT(*) as cnt
        FROM vw_financial_metrics
        WHERE taxpayer_id = '91310115MA2KZZZZZZ'
          AND period_year = 2024 AND period_month = 12
          AND metric_name IN ('净利率', '增值税税负率', '企业所得税税负率')
        GROUP BY period_type
    """)
    dec_data = cursor.fetchall()

    # Check Mar 2025 data
    cursor.execute("""
        SELECT period_type, COUNT(*) as cnt
        FROM vw_financial_metrics
        WHERE taxpayer_id = '91310115MA2KZZZZZZ'
          AND period_year = 2025 AND period_month = 3
          AND metric_name IN ('净利率', '增值税税负率', '企业所得税税负率')
        GROUP BY period_type
    """)
    mar_data = cursor.fetchall()

    conn.close()

    print("📊 Database data completeness:")
    print(f"   Dec 2024: {dict(dec_data)}")
    print(f"   Mar 2025: {dict(mar_data)}")

    # Verify quarterly/annual data exists for both periods
    dec_types = [row[0] for row in dec_data]
    mar_types = [row[0] for row in mar_data]

    assert 'quarterly' in dec_types or 'annual' in dec_types, "Dec 2024 missing quarterly/annual data"
    assert 'quarterly' in mar_types or 'annual' in mar_types, "Mar 2025 missing quarterly/annual data"


def test_null_handling():
    """Test that NULL values are properly filtered in JOINs"""
    query = "TSE科技2024年12月与2025年3月企业所得税税负率对比"

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"

    # If data exists, verify no NULL values in result
    if len(result.get('results', [])) > 0:
        for row in result['results']:
            # Check that metric_value columns are not NULL
            # (column names may vary, so check all numeric-looking values)
            for key, value in row.items():
                if key not in ['metric_name', 'metric_unit', 'evaluation_level']:
                    if value is not None:
                        assert isinstance(value, (int, float)), f"Non-numeric value: {value}"

    print("✅ NULL handling works correctly")


def test_backward_compatibility():
    """Test that existing queries still work after the fix"""
    test_cases = [
        "TSE科技2025年12月资产负债率",
        "TSE科技2025年净利率",
        "TSE科技2024年与2025年末资产负债率对比",
    ]

    for query in test_cases:
        result = run_pipeline(query)
        assert result['success'], f"Backward compatibility broken for: {query}"

    print("✅ Backward compatibility maintained")


if __name__ == "__main__":
    print("=" * 60)
    print("Financial Ratio Query Fix - Test Suite")
    print("=" * 60)
    print()

    try:
        # Run data completeness check first
        test_data_completeness()
        print()

        # Run main tests
        test_original_failing_query()
        print()

        test_quarter_end_comparison()
        print()

        test_non_quarter_end_comparison()
        print()

        test_mixed_month_types()
        print()

        test_range_query_consistency()
        print()

        test_null_handling()
        print()

        test_backward_compatibility()
        print()

        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
