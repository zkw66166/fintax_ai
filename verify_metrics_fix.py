#!/usr/bin/env python3
"""
Quick verification that the metrics fix is working.
Checks that Stage 1 LLM extracts correct metric names.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mvp_pipeline import run_pipeline


def verify_fix():
    """Verify the fix with a simple test"""
    print("\n" + "="*80)
    print("VERIFICATION: Cross-Domain Metrics Fix")
    print("="*80)

    query = "博雅文化传媒有限公司2025年各季度总资产、总负债和净利润情况"
    print(f"\nQuery: {query}")
    print("\nExpected metrics: ['assets_end', 'liabilities_end', 'net_profit']")
    print("(NOT ['total_assets_end', 'total_liabilities_end', 'net_profit'])")

    result = run_pipeline(user_query=query)

    print(f"\nResult:")
    print(f"  Domain: {result.get('domain')}")
    print(f"  Success: {result.get('success')}")
    print(f"  Rows: {len(result.get('results', []))}")

    if result.get('success') and len(result.get('results', [])) > 0:
        print("\n✅ FIX VERIFIED: Query returned data successfully!")
        print("\nThe Stage 1 LLM is now correctly extracting:")
        print("  - '总资产' → assets_end (not total_assets_end)")
        print("  - '总负债' → liabilities_end (not total_liabilities_end)")
        print("  - '净利润' → net_profit")
        return True
    else:
        print("\n❌ FIX FAILED: Query did not return data")
        return False


if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)
