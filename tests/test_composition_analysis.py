#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for composition/structure analysis queries
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mvp_pipeline import run_pipeline
from config.settings import DB_PATH


def test_query(query_name, query, expected_min_rows=2):
    """Test a single composition query"""
    print(f"\n{'='*80}")
    print(f"TEST: {query_name}")
    print(f"{'='*80}")
    print(f"Query: {query}")

    try:
        result = run_pipeline(
            user_query=query,
            db_path=str(DB_PATH),
            conversation_history=[]
        )

        success = result.get("success", False)
        data = result.get("results") or result.get("data", [])
        sql = result.get("sql", "")
        intent = result.get("intent", {})

        # Check query_type
        query_type = intent.get("query_type")
        composition_target = intent.get("composition_target")

        print(f"\n✓ Success: {success}")
        print(f"✓ Query Type: {query_type}")
        print(f"✓ Composition Target: {composition_target}")
        print(f"✓ SQL uses UNION ALL: {'UNION ALL' in sql.upper() if sql else False}")
        print(f"✓ Result rows: {len(data)}")

        if data:
            print(f"\nFirst 3 rows:")
            for i, row in enumerate(data[:3], 1):
                print(f"  {i}. {row}")

        # Validation
        passed = True
        errors = []

        if not success:
            passed = False
            errors.append("Pipeline failed")

        if query_type != "composition":
            passed = False
            errors.append(f"Expected query_type='composition', got '{query_type}'")

        if not composition_target:
            passed = False
            errors.append("Missing composition_target")

        if sql and "UNION ALL" not in sql.upper():
            passed = False
            errors.append("SQL does not use UNION ALL pattern")

        if len(data) < expected_min_rows:
            passed = False
            errors.append(f"Expected at least {expected_min_rows} rows, got {len(data)}")

        if passed:
            print(f"\n✅ PASSED")
            return True
        else:
            print(f"\n❌ FAILED:")
            for error in errors:
                print(f"  - {error}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all composition analysis tests"""
    print("="*80)
    print("COMPOSITION ANALYSIS TEST SUITE")
    print("="*80)

    tests = [
        # Test 1: Single target, single period
        ("单目标单期间 - 总资产构成", "TSE科技2025年末的总资产构成分析", 2),

        # Test 2: Single target, single period - different keyword
        ("单目标单期间 - 总资产结构", "TSE科技2025年末的总资产结构", 2),

        # Test 3: Single target, single period - different keyword
        ("单目标单期间 - 总资产占比", "TSE科技2025年末的总资产占比分析", 2),

        # Test 4: Different target - liabilities
        ("单目标单期间 - 总负债构成", "TSE科技2025年末的总负债构成分析", 2),

        # Test 5: Multi-level - current assets
        ("多层级 - 流动资产构成", "TSE科技2025年末的流动资产构成分析", 3),

        # Test 6: Multi-target
        ("多目标 - 总资产和总负债", "TSE科技2025年末的总资产和总负债构成分析", 4),

        # Test 7: Different company
        ("不同公司 - 华兴科技", "华兴科技2025年末的总资产构成分析", 2),

        # Test 8: Different period
        ("不同期间 - 2024年末", "TSE科技2024年末的总资产构成分析", 2),
    ]

    results = []
    for test_name, query, expected_rows in tests:
        passed = test_query(test_name, query, expected_rows)
        results.append((test_name, passed))

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\n{passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
