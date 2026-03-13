"""
Quick verification: Show that extract_all_rate_metrics() now finds all 3 metrics
"""

import sys
sys.path.insert(0, '.')

from modules.metric_calculator import extract_all_rate_metrics

print("\n" + "="*70)
print("Quick Verification: Metric Extraction")
print("="*70)

query = "利润率、增值税税负率、企业所得税税负率比较分析"

print(f"\nQuery: {query}")
print("\nExtracting metrics...")

metrics = extract_all_rate_metrics(query)

print(f"\nFound {len(metrics)} metrics:")
for i, metric in enumerate(metrics, 1):
    print(f"  {i}. {metric}")

print("\n" + "="*70)
if len(metrics) == 3:
    print("✅ SUCCESS - All 3 metrics extracted")
else:
    print(f"❌ FAILED - Expected 3 metrics, got {len(metrics)}")
print("="*70 + "\n")
