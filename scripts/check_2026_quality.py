"""Run data quality checks on 2026 data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.services.data_quality import DataQualityChecker

checker = DataQualityChecker()

companies = [
    ('91310115MA2KZZZZZZ', 'TSE科技'),
    ('91330100MA2KWWWWWW', '环球机械'),
    ('91330200MA2KXXXXXX', '创智软件'),
    ('91330200MA2KYYYYYY', '大华智能制造'),
]

print("="*80)
print("Data Quality Check - 2026 Data")
print("="*80)

for tid, name in companies:
    print(f"\n{name} ({tid}):")
    print("-"*80)

    # Run full check (all periods)
    result = checker.check_all(tid)

    if 'error' in result:
        print(f"  Error: {result['error']}")
        continue

    # Summary
    summary = result['summary']
    print(f"  Total: {summary['total_checks']} checks")
    print(f"  Passed: {summary['passed']} ({summary['pass_rate']}%)")
    print(f"  Failed: {summary['failed']}")
    print(f"  Warned: {summary['warned']}")

    # Show failures by domain
    for domain in result['domains']:
        if domain['failed'] > 0:
            print(f"\n  {domain['domain_name_cn']}: {domain['failed']} failures")
            for detail in domain['details'][:5]:  # Show first 5
                if detail['status'] == 'fail':
                    print(f"    - {detail['rule_name_cn']}: {detail['message']}")

print("\n" + "="*80)
print("Data quality check complete!")
print("="*80)
