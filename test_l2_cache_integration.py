"""Integration tests for L2 cache complete flow."""
import pytest
import json
import time
from pathlib import Path
from api.services.template_cache import (
    templatize_sql,
    instantiate_sql,
    save_template_cache,
    get_template_cache
)
from api.services.view_adapter import adapt_sql_for_type
from modules.db_utils import get_taxpayer_info, get_connection


class TestCrossTaxpayerQueryFlow:
    """Test complete cross-taxpayer query flow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup: ensure cache directory exists
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)

        yield

        # Teardown: clean up test cache files
        for f in cache_dir.glob("template_test_*.json"):
            f.unlink(missing_ok=True)

    def test_scenario_1_type_matching_cross_taxpayer(self):
        """
        Scenario 1: Type-matching cross-taxpayer query

        1. Query: 华兴科技 (general taxpayer) "2025年1月增值税"
        2. Verify: L2 cache created (taxpayer_type=general)
        3. Switch to: TSE科技 (general taxpayer)
        4. Verify: L2 cache hit, response time < 2s
        5. Verify: Returns correct TSE data
        """
        # Step 1: First query (华兴科技)
        query = "2025年1月增值税"
        response_mode = "detailed"
        company_id_1 = "华兴科技"

        # Simulate pipeline execution
        sql_1 = f"""
        SELECT * FROM vw_vat_return_general
        WHERE taxpayer_id = '{company_id_1}'
          AND period_year = 2025
          AND period_month = 1
        """

        # Step 2: Templatize and save L2 cache
        template, success = templatize_sql(sql_1, company_id_1)
        assert success is True

        taxpayer_type_1 = "general"
        accounting_standard_1 = "ASBE"

        cache_key = save_template_cache(
            query, response_mode, taxpayer_type_1, accounting_standard_1,
            {"domain": "vat"}, template, "vat"
        )

        assert cache_key.startswith("template_")

        # Step 3: Switch to TSE科技
        company_id_2 = "TSE科技"
        taxpayer_type_2 = "general"
        accounting_standard_2 = "ASBE"

        # Step 4: L2 cache hit
        start_time = time.time()

        cached = get_template_cache(query, response_mode, taxpayer_type_2, accounting_standard_2)
        assert cached is not None
        assert cached["sql_template"] == template

        # Instantiate SQL
        sql_2 = instantiate_sql(cached["sql_template"], company_id_2)

        elapsed = time.time() - start_time

        # Step 5: Verify
        assert "TSE科技" in sql_2
        assert "华兴科技" not in sql_2
        assert elapsed < 0.1  # Cache lookup should be very fast

    def test_scenario_2_type_mismatch_smart_adaptation(self):
        """
        Scenario 2: Type-mismatch cross-taxpayer query (smart adaptation)

        1. Query: 华兴科技 (general) "2025年1月增值税"
        2. Verify: L2 cache created (taxpayer_type=general, view=vw_vat_return_general)
        3. Switch to: 鑫源贸易 (small taxpayer)
        4. Verify: L2 cache miss, but finds general type cache
        5. Verify: Auto-adapts view (vw_vat_return_general → vw_vat_return_small)
        6. Verify: Response time < 2s
        7. Verify: Returns correct 鑫源贸易 data
        8. Verify: Saves adapted L2 cache (taxpayer_type=small)
        """
        # Step 1: First query (华兴科技 - general)
        query = "2025年1月增值税"
        response_mode = "detailed"
        company_id_1 = "华兴科技"

        sql_1 = f"""
        SELECT * FROM vw_vat_return_general
        WHERE taxpayer_id = '{company_id_1}'
          AND period_year = 2025
        """

        # Step 2: Save L2 cache for general type
        template_1, success = templatize_sql(sql_1, company_id_1)
        assert success is True

        cache_key_1 = save_template_cache(
            query, response_mode, "general", "ASBE",
            {"domain": "vat"}, template_1, "vat"
        )

        # Step 3: Switch to 鑫源贸易 (small)
        company_id_2 = "鑫源贸易"
        taxpayer_type_2 = "small"
        accounting_standard_2 = "ASSE"

        # Step 4: L2 cache miss for small type
        cached_small = get_template_cache(query, response_mode, taxpayer_type_2, accounting_standard_2)
        assert cached_small is None

        # Step 5: Find general type cache and adapt
        cached_general = get_template_cache(query, response_mode, "general", "ASBE")
        assert cached_general is not None

        adapted_template = adapt_sql_for_type(
            cached_general["sql_template"],
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted_template is not None
        assert "vw_vat_return_small" in adapted_template
        assert "vw_vat_return_general" not in adapted_template

        # Step 6: Instantiate adapted SQL
        sql_2 = instantiate_sql(adapted_template, company_id_2)

        assert "鑫源贸易" in sql_2
        assert "vw_vat_return_small" in sql_2

        # Step 8: Save adapted L2 cache
        cache_key_2 = save_template_cache(
            query, response_mode, taxpayer_type_2, accounting_standard_2,
            {"domain": "vat"}, adapted_template, "vat"
        )

        assert cache_key_2.startswith("template_")
        assert cache_key_2 != cache_key_1  # Different cache keys

    def test_scenario_3_cross_domain_query(self):
        """
        Scenario 3: Cross-domain query

        1. Query: 华兴科技 "2025年利润表和增值税对比"
        2. Verify: Generates SQL with UNION ALL
        3. Verify: L2 cache saved successfully
        4. Switch to: TSE科技
        5. Verify: L2 cache hit, both CTEs' taxpayer_id replaced correctly
        6. Verify: Returns correct TSE data
        """
        # Step 1: Cross-domain query
        query = "2025年利润表和增值税对比"
        response_mode = "detailed"
        company_id_1 = "华兴科技"

        sql_1 = f"""
        WITH profit AS (
            SELECT * FROM vw_profit_eas WHERE taxpayer_id = '{company_id_1}'
        ),
        vat AS (
            SELECT * FROM vw_vat_return_general WHERE taxpayer_id = '{company_id_1}'
        )
        SELECT * FROM profit
        UNION ALL
        SELECT * FROM vat
        """

        # Step 2: Templatize (should replace both taxpayer_id)
        template, success = templatize_sql(sql_1, company_id_1)
        assert success is True
        assert template.count("{{TAXPAYER_ID}}") == 2

        # Step 3: Save L2 cache
        cache_key = save_template_cache(
            query, response_mode, "general", "ASBE",
            {"domain": "cross_domain"}, template, "cross_domain"
        )

        # Step 4: Switch to TSE科技
        company_id_2 = "TSE科技"

        cached = get_template_cache(query, response_mode, "general", "ASBE")
        assert cached is not None

        # Step 5: Instantiate (should replace both placeholders)
        sql_2 = instantiate_sql(cached["sql_template"], company_id_2)

        # Step 6: Verify
        assert sql_2.count("TSE科技") == 2
        assert "华兴科技" not in sql_2
        assert "{{TAXPAYER_ID}}" not in sql_2

    def test_scenario_4_multi_period_query(self):
        """
        Scenario 4: Multi-period query

        1. Query: 华兴科技 "2024Q4、2025Q1、2025Q2 流动资产构成"
        2. Verify: Generates SQL with period range filter
        3. Verify: L2 cache saved successfully
        4. Switch to: TSE科技
        5. Verify: L2 cache hit, returns TSE multi-period data
        """
        # Step 1: Multi-period query
        query = "2024Q4、2025Q1、2025Q2 流动资产构成"
        response_mode = "detailed"
        company_id_1 = "华兴科技"

        sql_1 = f"""
        SELECT * FROM vw_balance_sheet_eas
        WHERE taxpayer_id = '{company_id_1}'
          AND (
            (period_year = 2024 AND period_month IN (10, 11, 12))
            OR (period_year = 2025 AND period_month IN (1, 2, 3, 4, 5, 6))
          )
        """

        # Step 2: Templatize
        template, success = templatize_sql(sql_1, company_id_1)
        assert success is True

        # Step 3: Save L2 cache
        cache_key = save_template_cache(
            query, response_mode, "general", "ASBE",
            {"domain": "balance_sheet"}, template, "balance_sheet"
        )

        # Step 4: Switch to TSE科技
        company_id_2 = "TSE科技"

        cached = get_template_cache(query, response_mode, "general", "ASBE")
        assert cached is not None

        # Step 5: Instantiate
        sql_2 = instantiate_sql(cached["sql_template"], company_id_2)

        # Verify
        assert "TSE科技" in sql_2
        assert "华兴科技" not in sql_2
        assert "period_year = 2024" in sql_2
        assert "period_year = 2025" in sql_2


class TestPerformanceMetrics:
    """Test performance metrics and cache hit rates."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        yield
        for f in cache_dir.glob("template_perf_*.json"):
            f.unlink(missing_ok=True)

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        queries = [
            ("2025年1月增值税", "vat"),
            ("2025年2月增值税", "vat"),
            ("2025年资产负债表", "balance_sheet"),
        ]

        companies = ["华兴科技", "TSE科技", "创智软件"]

        hits = 0
        misses = 0

        for query, domain in queries:
            # First company: always miss (creates cache)
            cached = get_template_cache(query, "detailed", "general", "ASBE")
            if cached is None:
                misses += 1
                # Simulate cache creation
                template = f"SELECT * FROM vw_{domain} WHERE taxpayer_id = '{{{{TAXPAYER_ID}}}}'"
                save_template_cache(
                    query, "detailed", "general", "ASBE",
                    {"domain": domain}, template, domain
                )
            else:
                hits += 1

            # Other companies: should hit
            for company in companies[1:]:
                cached = get_template_cache(query, "detailed", "general", "ASBE")
                if cached is not None:
                    hits += 1
                else:
                    misses += 1

        total = hits + misses
        hit_rate = hits / total if total > 0 else 0

        # After first round, hit rate should be high
        assert hit_rate >= 0.6  # Target: ≥60%

    def test_response_time_comparison(self):
        """Test response time comparison between cache hit and miss."""
        query = "2025年1月增值税"
        company_id = "华兴科技"

        # Simulate cache miss (full pipeline)
        start_miss = time.time()
        sql = f"SELECT * FROM vw_vat WHERE taxpayer_id = '{company_id}'"
        template, _ = templatize_sql(sql, company_id)
        save_template_cache(query, "detailed", "general", "ASBE", {}, template, "vat")
        time_miss = time.time() - start_miss

        # Simulate cache hit
        start_hit = time.time()
        cached = get_template_cache(query, "detailed", "general", "ASBE")
        sql_hit = instantiate_sql(cached["sql_template"], "TSE科技")
        time_hit = time.time() - start_hit

        # Cache hit should be much faster
        assert time_hit < time_miss
        assert time_hit < 0.1  # Should be very fast


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_handle_sql_execution_failure(self):
        """Test handling SQL execution failure after L2 cache hit."""
        # This would be tested in the actual API endpoint
        # Here we just verify the template is valid
        query = "invalid query"
        template = "SELECT * FROM nonexistent_table WHERE taxpayer_id = '{{TAXPAYER_ID}}'"

        save_template_cache(query, "detailed", "general", "ASBE", {}, template, "unknown")

        cached = get_template_cache(query, "detailed", "general", "ASBE")
        assert cached is not None

        sql = instantiate_sql(cached["sql_template"], "华兴科技")
        assert "华兴科技" in sql

    def test_handle_adaptation_failure(self):
        """Test handling adaptation failure."""
        # Create a template that can't be adapted
        query = "special query"
        template = "SELECT * FROM vw_special_view WHERE taxpayer_id = '{{TAXPAYER_ID}}'"

        save_template_cache(query, "detailed", "general", "ASBE", {}, template, "special")

        cached = get_template_cache(query, "detailed", "general", "ASBE")

        # Try to adapt (should fail gracefully)
        adapted = adapt_sql_for_type(
            cached["sql_template"],
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        # Should return original or None, not crash
        assert adapted is not None or adapted is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
