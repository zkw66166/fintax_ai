"""
Tax Incentive Query Diversity Sampling Test Suite

Tests the diversity sampling feature for broad tax incentive queries.
"""

from modules.tax_incentive_query import TaxIncentiveQuery


def test_broad_eit_query():
    """Test 1: Broad EIT query should return diverse policies across categories"""
    print("=" * 80)
    print("Test 1: 企业所得税优惠政策有哪些 (Broad EIT Query)")
    print("=" * 80)

    tiq = TaxIncentiveQuery()
    result = tiq.search('企业所得税优惠政策有哪些', limit=20)

    print(f"Result count: {result['result_count']}")
    print(f"Query strategy: {result['query_strategy']}")

    # Check category diversity
    categories = set()
    for r in result['raw_results']:
        cat = r.get('incentive_category', '未分类')
        if cat:
            categories.add(cat)

    print(f"\nCategories represented: {len(categories)}")
    for cat in sorted(categories):
        count = sum(1 for r in result['raw_results'] if r.get('incentive_category') == cat)
        print(f"  - {cat}: {count} policies")

    print("\nFirst 5 policies:")
    for i, r in enumerate(result['raw_results'][:5], 1):
        cat = r.get('incentive_category', '未分类')
        items = r['incentive_items'][:50]
        print(f"  {i}. [{cat}] {items}...")

    # Assertions
    assert result['result_count'] == 20, "Should return 20 policies"
    assert result['query_strategy'] == 'structured', "Should use structured search"
    assert len(categories) >= 5, f"Should have at least 5 categories, got {len(categories)}"

    print("\n✅ Test 1 PASSED: Broad EIT query returns diverse policies\n")


def test_broad_vat_query():
    """Test 2: Broad VAT query should return diverse policies across categories"""
    print("=" * 80)
    print("Test 2: 增值税优惠政策有哪些 (Broad VAT Query)")
    print("=" * 80)

    tiq = TaxIncentiveQuery()
    result = tiq.search('增值税优惠政策有哪些', limit=20)

    print(f"Result count: {result['result_count']}")
    print(f"Query strategy: {result['query_strategy']}")

    # Check category diversity
    categories = set()
    for r in result['raw_results']:
        cat = r.get('incentive_category', '未分类')
        if cat:
            categories.add(cat)

    print(f"\nCategories represented: {len(categories)}")
    for cat in sorted(categories):
        count = sum(1 for r in result['raw_results'] if r.get('incentive_category') == cat)
        print(f"  - {cat}: {count} policies")

    print("\nFirst 5 policies:")
    for i, r in enumerate(result['raw_results'][:5], 1):
        cat = r.get('incentive_category', '未分类')
        items = r['incentive_items'][:50]
        print(f"  {i}. [{cat}] {items}...")

    # Assertions
    assert result['result_count'] == 20, "Should return 20 policies"
    assert result['query_strategy'] == 'structured', "Should use structured search"
    assert len(categories) >= 5, f"Should have at least 5 categories, got {len(categories)}"

    print("\n✅ Test 2 PASSED: Broad VAT query returns diverse policies\n")


def test_specific_xiawei_query():
    """Test 3: Specific query with entity keyword should NOT use diversity sampling"""
    print("=" * 80)
    print("Test 3: 小微企业企业所得税优惠 (Specific Query)")
    print("=" * 80)

    tiq = TaxIncentiveQuery()
    result = tiq.search('小微企业企业所得税优惠', limit=20)

    print(f"Result count: {result['result_count']}")
    print(f"Query strategy: {result['query_strategy']}")

    print("\nAll policies:")
    for i, r in enumerate(result['raw_results'], 1):
        items = r['incentive_items'][:60]
        print(f"  {i}. {items}...")

    # Assertions
    assert result['query_strategy'] == 'structured', "Should use structured search"
    assert result['result_count'] <= 5, "Should return focused results (no diversity)"

    # Verify all results are related to 小微企业
    for r in result['raw_results']:
        items = r.get('incentive_items', '')
        keywords = r.get('keywords', '') or ''
        qualification = r.get('qualification', '') or ''
        combined = items + keywords + qualification
        assert any(kw in combined for kw in ['小微企业', '小型微利']), \
            f"Result should contain 小微企业 or 小型微利: {items}"

    print("\n✅ Test 3 PASSED: Specific query returns focused results (no diversity)\n")


def test_specific_ic_query():
    """Test 4: Specific query with entity keyword should NOT use diversity sampling"""
    print("=" * 80)
    print("Test 4: 集成电路增值税优惠 (Specific Query)")
    print("=" * 80)

    tiq = TaxIncentiveQuery()
    result = tiq.search('集成电路增值税优惠', limit=20)

    print(f"Result count: {result['result_count']}")
    print(f"Query strategy: {result['query_strategy']}")

    print("\nAll policies:")
    for i, r in enumerate(result['raw_results'], 1):
        items = r['incentive_items'][:60]
        print(f"  {i}. {items}...")

    # Assertions
    assert result['query_strategy'] == 'structured', "Should use structured search"
    assert result['result_count'] <= 5, "Should return focused results (no diversity)"

    print("\n✅ Test 4 PASSED: Specific query returns focused results (no diversity)\n")


def test_broad_pit_query():
    """Test 5: Broad PIT query should return diverse policies across categories"""
    print("=" * 80)
    print("Test 5: 个人所得税优惠政策有哪些 (Broad PIT Query)")
    print("=" * 80)

    tiq = TaxIncentiveQuery()
    result = tiq.search('个人所得税优惠政策有哪些', limit=20)

    print(f"Result count: {result['result_count']}")
    print(f"Query strategy: {result['query_strategy']}")

    # Check category diversity
    categories = set()
    for r in result['raw_results']:
        cat = r.get('incentive_category', '未分类')
        if cat:
            categories.add(cat)

    print(f"\nCategories represented: {len(categories)}")
    for cat in sorted(categories):
        count = sum(1 for r in result['raw_results'] if r.get('incentive_category') == cat)
        print(f"  - {cat}: {count} policies")

    print("\nFirst 5 policies:")
    for i, r in enumerate(result['raw_results'][:5], 1):
        cat = r.get('incentive_category', '未分类')
        items = r['incentive_items'][:50]
        print(f"  {i}. [{cat}] {items}...")

    # Assertions
    assert result['result_count'] == 20, "Should return 20 policies"
    assert result['query_strategy'] == 'structured', "Should use structured search"
    assert len(categories) >= 5, f"Should have at least 5 categories, got {len(categories)}"

    print("\n✅ Test 5 PASSED: Broad PIT query returns diverse policies\n")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("TAX INCENTIVE DIVERSITY SAMPLING TEST SUITE")
    print("=" * 80 + "\n")

    try:
        test_broad_eit_query()
        test_broad_vat_query()
        test_specific_xiawei_query()
        test_specific_ic_query()
        test_broad_pit_query()

        print("=" * 80)
        print("ALL TESTS PASSED ✅")
        print("=" * 80)
        print("\nSummary:")
        print("- Broad queries (企业所得税/增值税/个人所得税优惠政策有哪些) return diverse policies")
        print("- Specific queries (小微企业/集成电路) return focused results")
        print("- Diversity sampling works across all tax types")
        print("- No impact on specific entity-based queries")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
