"""
Test script to verify domain detection and quarterly period handling fixes.

Test Case 1: Domain Detection Fix
Query: "TSE科技有限公司 去年第四季度总资产、净利润、应纳企业所得税额情况"
Expected: cross_domain_list = ["balance_sheet", "eit", "profit"] (NOT invoice)

Test Case 2: Quarterly Period Handling Fix
Query: "TSE科技有限公司 去年第四季度总资产、净利润、应纳企业所得税额情况"
Expected:
- balance_sheet: 1 row (month 12 only)
- profit: 1 row (month 12, time_range='本年累计')
- eit: 1 row (Q4 summary)

Test Case 3: All Quarters Query (Regression Test)
Query: "TSE科技有限公司 2025年各季度总资产、净利润情况"
Expected:
- balance_sheet: 4 rows (months 3, 6, 9, 12)
- profit: 4 rows (months 3, 6, 9, 12, time_range='本年累计')
"""

import sys
import json
from modules.entity_preprocessor import detect_entities
from modules.intent_parser import parse_intent
from modules.cross_domain_calculator import execute_cross_domain_query
from database.db_utils import get_db_connection

def test_domain_detection():
    """Test Case 1: Domain Detection Fix"""
    print("\n" + "="*80)
    print("Test Case 1: Domain Detection Fix")
    print("="*80)

    query = "TSE科技有限公司 去年第四季度总资产、净利润、应纳企业所得税额情况"
    print(f"Query: {query}")

    # Step 1: Entity preprocessing
    conn = get_db_connection()
    try:
        entities = detect_entities(query, conn)
    finally:
        conn.close()

    print(f"\nEntity Preprocessing Result:")
    print(f"  taxpayer_id: {entities.get('taxpayer_id')}")
    print(f"  period_year: {entities.get('period_year')}")
    print(f"  period_quarter: {entities.get('period_quarter')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_end_month: {entities.get('period_end_month')}")
    print(f"  quarter_mode: {entities.get('quarter_mode')}")
    print(f"  domain_hint: {entities.get('domain_hint')}")

    # Step 2: Intent parsing
    intent = parse_intent(query, entities)
    print(f"\nIntent Parsing Result:")
    print(f"  domain: {intent.get('domain')}")
    print(f"  cross_domain_list: {intent.get('cross_domain_list')}")

    # Verify
    expected_domains = ["balance_sheet", "eit", "profit"]
    actual_domains = intent.get('cross_domain_list', [])

    if set(actual_domains) == set(expected_domains):
        print(f"\n✅ PASS: Domain detection correct")
        print(f"   Expected: {sorted(expected_domains)}")
        print(f"   Actual:   {sorted(actual_domains)}")
    else:
        print(f"\n❌ FAIL: Domain detection incorrect")
        print(f"   Expected: {sorted(expected_domains)}")
        print(f"   Actual:   {sorted(actual_domains)}")
        if 'invoice' in actual_domains:
            print(f"   ERROR: 'invoice' should NOT be in cross_domain_list")

    return intent, entities

def test_quarterly_period_handling(intent, entities):
    """Test Case 2: Quarterly Period Handling Fix"""
    print("\n" + "="*80)
    print("Test Case 2: Quarterly Period Handling Fix")
    print("="*80)

    # Execute cross-domain query
    conn = get_db_connection()
    try:
        result = execute_cross_domain_query(
            intent=intent,
            entities=entities,
            conn=conn
        )

        print(f"\nExecution Result:")
        print(f"  success: {result.get('success')}")

        if result.get('success'):
            sub_results = result.get('sub_results', {})
            print(f"\nSub-domain Results:")

            for domain, sub_result in sub_results.items():
                rows = sub_result.get('rows', [])
                print(f"\n  {domain}:")
                print(f"    Row count: {len(rows)}")

                if rows:
                    # Show period info
                    if domain == 'balance_sheet':
                        months = [row.get('period_month') for row in rows]
                        print(f"    Months: {months}")
                        expected_count = 1
                        expected_months = [12]
                    elif domain == 'profit':
                        months = [row.get('period_month') for row in rows]
                        time_ranges = [row.get('time_range') for row in rows]
                        print(f"    Months: {months}")
                        print(f"    Time ranges: {time_ranges}")
                        expected_count = 1
                        expected_months = [12]
                    elif domain == 'eit':
                        quarters = [row.get('period_quarter') for row in rows]
                        print(f"    Quarters: {quarters}")
                        expected_count = 1

                    # Verify
                    if domain in ['balance_sheet', 'profit']:
                        if len(rows) == expected_count and months == expected_months:
                            print(f"    ✅ PASS: Correct period handling")
                        else:
                            print(f"    ❌ FAIL: Expected {expected_count} row(s) with month(s) {expected_months}")
                    elif domain == 'eit':
                        if len(rows) == expected_count:
                            print(f"    ✅ PASS: Correct period handling")
                        else:
                            print(f"    ❌ FAIL: Expected {expected_count} row(s)")
        else:
            print(f"  error: {result.get('error')}")
            print(f"\n❌ FAIL: Query execution failed")

    finally:
        conn.close()

def test_all_quarters_regression():
    """Test Case 3: All Quarters Query (Regression Test)"""
    print("\n" + "="*80)
    print("Test Case 3: All Quarters Query (Regression Test)")
    print("="*80)

    query = "TSE科技有限公司 2025年各季度总资产、净利润情况"
    print(f"Query: {query}")

    # Step 1: Entity preprocessing
    conn = get_db_connection()
    try:
        entities = detect_entities(query, conn)
    finally:
        conn.close()

    print(f"\nEntity Preprocessing Result:")
    print(f"  taxpayer_id: {entities.get('taxpayer_id')}")
    print(f"  period_year: {entities.get('period_year')}")
    print(f"  period_quarter: {entities.get('period_quarter')}")
    print(f"  period_month: {entities.get('period_month')}")
    print(f"  period_end_month: {entities.get('period_end_month')}")
    print(f"  quarter_mode: {entities.get('quarter_mode')}")
    print(f"  all_quarters: {entities.get('all_quarters')}")

    # Step 2: Intent parsing
    intent = parse_intent(query, entities)
    print(f"\nIntent Parsing Result:")
    print(f"  domain: {intent.get('domain')}")
    print(f"  cross_domain_list: {intent.get('cross_domain_list')}")

    # Step 3: Execute cross-domain query
    conn = get_db_connection()
    try:
        result = execute_cross_domain_query(
            intent=intent,
            entities=entities,
            conn=conn
        )

        print(f"\nExecution Result:")
        print(f"  success: {result.get('success')}")

        if result.get('success'):
            sub_results = result.get('sub_results', {})
            print(f"\nSub-domain Results:")

            for domain, sub_result in sub_results.items():
                rows = sub_result.get('rows', [])
                print(f"\n  {domain}:")
                print(f"    Row count: {len(rows)}")

                if rows:
                    # Show period info
                    if domain == 'balance_sheet':
                        months = [row.get('period_month') for row in rows]
                        print(f"    Months: {months}")
                        expected_count = 4
                        expected_months = [3, 6, 9, 12]
                    elif domain == 'profit':
                        months = [row.get('period_month') for row in rows]
                        time_ranges = [row.get('time_range') for row in rows]
                        print(f"    Months: {months}")
                        print(f"    Time ranges: {time_ranges}")
                        expected_count = 4
                        expected_months = [3, 6, 9, 12]

                    # Verify
                    if len(rows) == expected_count and months == expected_months:
                        print(f"    ✅ PASS: Correct period handling")
                    else:
                        print(f"    ❌ FAIL: Expected {expected_count} rows with months {expected_months}")
        else:
            print(f"  error: {result.get('error')}")
            print(f"\n❌ FAIL: Query execution failed")

    finally:
        conn.close()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Domain Detection and Quarterly Period Handling Fix - Test Suite")
    print("="*80)

    # Test Case 1 & 2: Domain detection + quarterly period handling
    intent, entities = test_domain_detection()
    test_quarterly_period_handling(intent, entities)

    # Test Case 3: All quarters regression test
    test_all_quarters_regression()

    print("\n" + "="*80)
    print("Test Suite Complete")
    print("="*80)
