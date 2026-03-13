#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick validation of composition analysis fix"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from mvp_pipeline import run_pipeline

def quick_test(query):
    """Quick test of a single query"""
    print(f"\nQuery: {query}")
    result = run_pipeline(query)
    success = result.get('success')
    rows = len(result.get('results', []))
    intent = result.get('intent', {})
    query_type = intent.get('query_type')

    print(f"  Success: {success} | Query Type: {query_type} | Rows: {rows}")

    if rows > 0:
        data = result.get('results', [])
        for i, row in enumerate(data[:3], 1):
            print(f"    {i}. {row}")

    return success and rows >= 2

# Run tests
print("="*80)
print("COMPOSITION ANALYSIS VALIDATION")
print("="*80)

tests = [
    "TSE科技2025年末的总资产构成分析",
    "TSE科技2025年末的总资产结构",
    "TSE科技2025年末的总负债构成分析",
]

results = []
for query in tests:
    passed = quick_test(query)
    results.append(passed)

print(f"\n{'='*80}")
print(f"Results: {sum(results)}/{len(results)} passed")
if all(results):
    print("✅ ALL TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
