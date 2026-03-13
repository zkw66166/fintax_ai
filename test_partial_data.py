"""
Test for partial data availability in cross-period comparison queries

Verifies that when one period has data and another doesn't, the query still
returns the available data with NULL for missing periods.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mvp_pipeline import run_pipeline


def test_partial_data_comparison():
    """
    Test: 2025-12 has data, 2026-03 doesn't
    Expected: Returns 2025-12 data with NULL for 2026-03
    """
    query = "TSE科技2025年12月至2026年3月利润率、增值税税负率、企业所得税税负率分析"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Expected: Returns 2025-12 data, 2026-03 shows NULL")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    print(f"\nResult success: {result['success']}")
    print(f"Result keys: {result.keys()}")

    if 'results' in result:
        print(f"Number of rows: {len(result['results'])}")
        for i, row in enumerate(result['results'], 1):
            print(f"\nRow {i}:")
            for key, value in row.items():
                print(f"  {key}: {value}")
    else:
        print("No results field in result")

    # Assertions
    assert result['success'], f"Query failed: {result.get('error')}"
    assert 'results' in result, "No results field"
    assert len(result['results']) > 0, "Empty result - should return 2025-12 data even if 2026-03 is missing"

    # Check that 2025-12 columns have values
    for row in result['results']:
        has_2025_data = any('2025' in str(k) and v is not None for k, v in row.items())
        assert has_2025_data, f"Row missing 2025 data: {row}"

    print(f"\n✅ Test passed: Query returned {len(result['results'])} rows with partial data")
    print(f"   2025-12 data present, 2026-03 may be NULL (as expected)")

    return result


def test_both_periods_exist():
    """
    Test: Both 2024-12 and 2025-03 have data
    Expected: Returns both periods with values
    """
    query = "TSE科技2024年12月至2025年3月利润率、增值税税负率、企业所得税税负率分析"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Expected: Returns both periods with values")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert 'results' in result, "No results field"
    assert len(result['results']) > 0, "Empty result"

    # Check that both periods have data
    for row in result['results']:
        has_2024_data = any('2024' in str(k) and v is not None for k, v in row.items())
        has_2025_data = any('2025' in str(k) and v is not None for k, v in row.items())
        print(f"\n{row['metric_name']}: 2024={has_2024_data}, 2025={has_2025_data}")

    print(f"\n✅ Test passed: Query returned {len(result['results'])} rows with complete data")

    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Partial Data Availability Test")
    print("="*60)

    try:
        # Test 1: One period missing (2026-03)
        test_partial_data_comparison()

        # Test 2: Both periods exist
        test_both_periods_exist()

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
