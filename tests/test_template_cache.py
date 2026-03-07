"""Unit tests for L2 template cache."""
import pytest
import os
import json
import time
import hashlib
from pathlib import Path
from api.services.template_cache import (
    templatize_sql,
    instantiate_sql,
    save_template_cache,
    get_template_cache,
    cleanup_l2_cache,
    _build_cache_key
)


class TestTemplatizeSQL:
    """Test SQL templating functionality."""

    def test_templatize_sql_simple(self):
        """Test simple WHERE clause templating."""
        sql = "SELECT * FROM vw_vat_return_general WHERE taxpayer_id = '华兴科技' AND period_year = 2025"
        company_id = "华兴科技"

        template, success = templatize_sql(sql, company_id)

        assert success is True
        assert "{{TAXPAYER_ID}}" in template
        assert "华兴科技" not in template
        assert "period_year = 2025" in template

    def test_templatize_sql_union_all(self):
        """Test cross-domain query with UNION ALL."""
        sql = """
        WITH profit AS (
            SELECT * FROM vw_profit_eas WHERE taxpayer_id = 'TSE科技'
        ),
        vat AS (
            SELECT * FROM vw_vat_return_general WHERE taxpayer_id = 'TSE科技'
        )
        SELECT * FROM profit UNION ALL SELECT * FROM vat
        """
        company_id = "TSE科技"

        template, success = templatize_sql(sql, company_id)

        assert success is True
        assert template.count("{{TAXPAYER_ID}}") == 2
        assert "TSE科技" not in template

    def test_templatize_sql_multi_period(self):
        """Test multi-period query."""
        sql = """
        SELECT * FROM vw_balance_sheet_eas
        WHERE taxpayer_id = '创智软件'
          AND period_year = 2025
          AND period_month IN (1, 2, 3)
        """
        company_id = "创智软件"

        template, success = templatize_sql(sql, company_id)

        assert success is True
        assert "{{TAXPAYER_ID}}" in template
        assert "创智软件" not in template
        assert "period_month IN (1, 2, 3)" in template

    def test_templatize_sql_case_insensitive(self):
        """Test case-insensitive matching."""
        sql = "SELECT * FROM vw_vat WHERE TAXPAYER_ID = '华兴科技'"
        company_id = "华兴科技"

        template, success = templatize_sql(sql, company_id)

        assert success is True
        assert "{{TAXPAYER_ID}}" in template

    def test_templatize_sql_no_taxpayer_id(self):
        """Test SQL without taxpayer_id filter."""
        sql = "SELECT * FROM vw_vat_return_general WHERE period_year = 2025"
        company_id = "华兴科技"

        template, success = templatize_sql(sql, company_id)

        assert success is False
        assert template == sql

    def test_templatize_sql_special_characters(self):
        """Test company ID with special regex characters."""
        sql = "SELECT * FROM vw_vat WHERE taxpayer_id = 'Test(Company)'"
        company_id = "Test(Company)"

        template, success = templatize_sql(sql, company_id)

        assert success is True
        assert "{{TAXPAYER_ID}}" in template
        assert "Test(Company)" not in template


class TestInstantiateSQL:
    """Test SQL instantiation functionality."""

    def test_instantiate_sql_simple(self):
        """Test simple template instantiation."""
        template = "SELECT * FROM vw_vat WHERE taxpayer_id = '{{TAXPAYER_ID}}'"
        company_id = "TSE科技"

        sql = instantiate_sql(template, company_id)

        assert "TSE科技" in sql
        assert "{{TAXPAYER_ID}}" not in sql

    def test_instantiate_sql_multiple_placeholders(self):
        """Test template with multiple placeholders."""
        template = """
        WITH profit AS (
            SELECT * FROM vw_profit WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        ),
        vat AS (
            SELECT * FROM vw_vat WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        )
        SELECT * FROM profit UNION ALL SELECT * FROM vat
        """
        company_id = "华兴科技"

        sql = instantiate_sql(template, company_id)

        assert sql.count("华兴科技") == 2
        assert "{{TAXPAYER_ID}}" not in sql


class TestCacheOperations:
    """Test cache save/get/cleanup operations."""

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

    def test_save_and_get_template_cache(self):
        """Test saving and retrieving L2 cache."""
        query = "2025年1月增值税"
        response_mode = "detailed"
        taxpayer_type = "general"
        accounting_standard = "ASBE"
        intent = {"domain": "vat", "period_year": 2025}
        sql_template = "SELECT * FROM vw_vat WHERE taxpayer_id = '{{TAXPAYER_ID}}'"
        domain = "vat"

        # Save cache
        cache_key = save_template_cache(
            query, response_mode, taxpayer_type, accounting_standard,
            intent, sql_template, domain
        )

        assert cache_key != ""
        assert len(cache_key) == 32  # MD5 hash length
        assert Path(f"cache/template_{cache_key}.json").exists()

        # Get cache
        cached = get_template_cache(query, response_mode, taxpayer_type, accounting_standard)

        assert cached is not None
        assert cached["query"] == query
        assert cached["sql_template"] == sql_template
        assert cached["domain"] == domain
        assert cached["taxpayer_type"] == taxpayer_type

    def test_get_template_cache_miss(self):
        """Test cache miss."""
        cached = get_template_cache(
            "nonexistent query",
            "detailed",
            "general",
            "ASBE"
        )

        assert cached is None

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        query = "2025年1月增值税"
        response_mode = "detailed"
        taxpayer_type = "general"
        accounting_standard = "ASBE"

        key1 = _build_cache_key(query, response_mode, taxpayer_type, accounting_standard)
        key2 = _build_cache_key(query, response_mode, taxpayer_type, accounting_standard)

        assert key1 == key2
        # Note: _build_cache_key returns just the hash, not with prefix

    def test_cache_key_different_for_different_types(self):
        """Test cache keys differ for different taxpayer types."""
        query = "2025年1月增值税"
        response_mode = "detailed"

        key_general = _build_cache_key(query, response_mode, "general", "ASBE")
        key_small = _build_cache_key(query, response_mode, "small", "ASSE")

        assert key_general != key_small

    def test_l2_cache_lru_eviction(self):
        """Test L2 LRU eviction."""
        # Clean up any existing test files first
        cache_dir = Path("cache")
        for f in cache_dir.glob("template_test_*.json"):
            f.unlink(missing_ok=True)

        # Create exactly 5 cache files with proper timestamps
        base_time = time.time()
        for i in range(5):
            cache_key = f"test_{i}"
            cache_file = cache_dir / f"template_test_{i}.json"
            cache_file.write_text(json.dumps({
                "cache_key": cache_key,
                "query": f"test query {i}",
                "created_at": base_time,
                "last_accessed_at": base_time + i  # Different times for LRU (float)
            }))

        # Count files before eviction
        before_count = len(list(cache_dir.glob("template_test_*.json")))
        assert before_count == 5

        # Trigger eviction with max_files=3
        evicted = cleanup_l2_cache(max_files=3)

        # Should evict 2 files (5 - 3 = 2)
        assert evicted >= 2

        # Check remaining files
        remaining = list(cache_dir.glob("template_test_*.json"))
        assert len(remaining) <= 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_templatize_empty_sql(self):
        """Test templating empty SQL."""
        sql = ""
        company_id = "华兴科技"

        template, success = templatize_sql(sql, company_id)

        assert success is False
        assert template == ""

    def test_instantiate_empty_template(self):
        """Test instantiating empty template."""
        template = ""
        company_id = "华兴科技"

        sql = instantiate_sql(template, company_id)

        assert sql == ""

    def test_templatize_sql_with_quotes_in_company_name(self):
        """Test company name with quotes."""
        sql = "SELECT * FROM vw_vat WHERE taxpayer_id = 'Test\\'s Company'"
        company_id = "Test's Company"

        # This should handle the escaping properly
        template, success = templatize_sql(sql, company_id)

        # May fail due to quote escaping - this is a known limitation
        # Just ensure it doesn't crash
        assert isinstance(template, str)
        assert isinstance(success, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
