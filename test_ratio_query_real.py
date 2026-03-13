"""
Real-world test for financial ratio query fix

Tests with actual data periods that exist in the database.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mvp_pipeline import run_pipeline


def test_dec_to_mar_comparison():
    """Test Dec 2024 to Mar 2025 comparison (real data exists)"""
    query = "TSE科技2024年12月至2025年3月利润率、增值税税负率、企业所得税税负率分析"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert 'results' in result, "No results field"
    assert len(result['results']) > 0, f"Empty result (0 rows)"

    print(f"\n✅ Query returned {len(result['results'])} rows")
    for row in result['results']:
        print(f"   {row}")

    return result


def test_quarter_comparison():
    """Test Q4 2024 vs Q1 2025"""
    query = "TSE科技2024年12月与2025年3月财务指标对比"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert len(result.get('results', [])) > 0, "Empty result"

    print(f"\n✅ Query returned {len(result['results'])} rows")

    return result


def test_year_end_comparison():
    """Test year-end comparison 2024 vs 2025"""
    query = "TSE科技2024年末与2025年末资产负债率对比"

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")

    result = run_pipeline(query)

    assert result['success'], f"Query failed: {result.get('error')}"
    assert len(result.get('results', [])) > 0, "Empty result"

    print(f"\n✅ Query returned {len(result['results'])} rows")

    return result


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Financial Ratio Query Fix - Real Data Test")
    print("="*60)

    try:
        test_dec_to_mar_comparison()
        test_quarter_comparison()
        test_year_end_comparison()

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
