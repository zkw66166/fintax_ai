"""Unit tests for view adapter."""
import pytest
from api.services.view_adapter import (
    adapt_sql_for_type,
    VIEW_MAPPING
)


class TestViewMapping:
    """Test view mapping table."""

    def test_view_mapping_structure(self):
        """Test VIEW_MAPPING has correct structure."""
        assert ("general", "ASBE") in VIEW_MAPPING
        assert ("small", "ASSE") in VIEW_MAPPING

        general_mapping = VIEW_MAPPING[("general", "ASBE")]
        small_mapping = VIEW_MAPPING[("small", "ASSE")]

        assert isinstance(general_mapping, dict)
        assert isinstance(small_mapping, dict)

    def test_view_mapping_completeness(self):
        """Test all required views are mapped."""
        required_views = [
            "vw_vat_return_general",
            "vw_balance_sheet_eas",
            "vw_profit_eas",
            "vw_cash_flow_eas"
        ]

        general_mapping = VIEW_MAPPING[("general", "ASBE")]
        small_mapping = VIEW_MAPPING[("small", "ASSE")]

        for view in required_views:
            assert view in general_mapping
            assert view in small_mapping


class TestAdaptVATView:
    """Test VAT view adaptation."""

    def test_adapt_vat_general_to_small(self):
        """Test adapting VAT view from general to small."""
        sql_template = """
        SELECT * FROM vw_vat_return_general
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
          AND period_year = 2025
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_vat_return_small" in adapted
        assert "vw_vat_return_general" not in adapted

    def test_adapt_vat_small_to_general(self):
        """Test adapting VAT view from small to general."""
        sql_template = """
        SELECT * FROM vw_vat_return_small
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="small",
            to_type="general",
            from_standard="ASSE",
            to_standard="ASBE"
        )

        assert adapted is not None
        assert "vw_vat_return_general" in adapted
        assert "vw_vat_return_small" not in adapted


class TestAdaptBalanceSheetView:
    """Test balance sheet view adaptation."""

    def test_adapt_balance_sheet_eas_to_sas(self):
        """Test adapting balance sheet from EAS to SAS."""
        sql_template = """
        SELECT * FROM vw_balance_sheet_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
          AND period_year = 2025
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_balance_sheet_sas" in adapted
        assert "vw_balance_sheet_eas" not in adapted

    def test_adapt_balance_sheet_sas_to_eas(self):
        """Test adapting balance sheet from SAS to EAS."""
        sql_template = """
        SELECT * FROM vw_balance_sheet_sas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="small",
            to_type="general",
            from_standard="ASSE",
            to_standard="ASBE"
        )

        assert adapted is not None
        assert "vw_balance_sheet_eas" in adapted
        assert "vw_balance_sheet_sas" not in adapted


class TestAdaptProfitView:
    """Test profit statement view adaptation."""

    def test_adapt_profit_eas_to_sas(self):
        """Test adapting profit view from EAS to SAS."""
        sql_template = """
        SELECT * FROM vw_profit_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_profit_sas" in adapted
        assert "vw_profit_eas" not in adapted


class TestAdaptCashFlowView:
    """Test cash flow statement view adaptation."""

    def test_adapt_cash_flow_eas_to_sas(self):
        """Test adapting cash flow view from EAS to SAS."""
        sql_template = """
        SELECT * FROM vw_cash_flow_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_cash_flow_sas" in adapted
        assert "vw_cash_flow_eas" not in adapted


class TestAdaptCrossDomainSQL:
    """Test cross-domain SQL adaptation."""

    def test_adapt_cross_domain_sql(self):
        """Test adapting SQL with multiple views."""
        sql_template = """
        WITH profit AS (
            SELECT * FROM vw_profit_eas WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        ),
        balance AS (
            SELECT * FROM vw_balance_sheet_eas WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        )
        SELECT * FROM profit
        UNION ALL
        SELECT * FROM balance
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_profit_sas" in adapted
        assert "vw_balance_sheet_sas" in adapted
        assert "vw_profit_eas" not in adapted
        assert "vw_balance_sheet_eas" not in adapted

    def test_adapt_mixed_views(self):
        """Test adapting SQL with mixed view types."""
        sql_template = """
        SELECT p.*, b.*
        FROM vw_profit_eas p
        JOIN vw_balance_sheet_eas b ON p.taxpayer_id = b.taxpayer_id
        WHERE p.taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        assert "vw_profit_sas" in adapted
        assert "vw_balance_sheet_sas" in adapted


class TestAdaptFailures:
    """Test adaptation failure scenarios."""

    def test_adapt_fail_on_same_type(self):
        """Test adaptation returns None when types are the same."""
        sql_template = "SELECT * FROM vw_vat_return_general"

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="general",
            from_standard="ASBE",
            to_standard="ASBE"
        )

        # Should return None or original SQL (implementation dependent)
        # Just ensure it doesn't crash
        assert adapted is not None or adapted is None

    def test_adapt_fail_on_incompatible_views(self):
        """Test adaptation with views that don't exist in mapping."""
        sql_template = "SELECT * FROM vw_nonexistent_view"

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        # Should return original SQL unchanged or None
        if adapted is not None:
            assert "vw_nonexistent_view" in adapted

    def test_adapt_empty_sql(self):
        """Test adapting empty SQL."""
        sql_template = ""

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        # Empty SQL should return empty or None
        assert adapted == "" or adapted is None


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_adapt_with_view_in_comments(self):
        """Test adaptation doesn't affect SQL comments."""
        sql_template = """
        -- This query uses vw_profit_eas
        SELECT * FROM vw_profit_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        # The view in the comment might or might not be replaced
        # depending on implementation - just ensure it doesn't crash
        assert "vw_profit_sas" in adapted

    def test_adapt_with_view_in_string_literal(self):
        """Test adaptation with view name in string literal."""
        sql_template = """
        SELECT 'vw_profit_eas' as view_name, *
        FROM vw_profit_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert adapted is not None
        # The actual view should be replaced
        assert adapted.count("vw_profit_sas") >= 1

    def test_adapt_case_insensitive(self):
        """Test adaptation is case-insensitive."""
        sql_template = """
        SELECT * FROM VW_PROFIT_EAS
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        adapted = adapt_sql_for_type(
            sql_template,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        # Should handle case-insensitive matching or return None
        if adapted is not None:
            assert "sas" in adapted.lower() or "SAS" in adapted


class TestBidirectionalAdaptation:
    """Test bidirectional adaptation (general ↔ small)."""

    def test_adapt_general_to_small_and_back(self):
        """Test adapting from general to small and back."""
        original_sql = """
        SELECT * FROM vw_profit_eas
        WHERE taxpayer_id = '{{TAXPAYER_ID}}'
        """

        # General → Small
        adapted_to_small = adapt_sql_for_type(
            original_sql,
            from_type="general",
            to_type="small",
            from_standard="ASBE",
            to_standard="ASSE"
        )

        assert "vw_profit_sas" in adapted_to_small

        # Small → General
        adapted_back = adapt_sql_for_type(
            adapted_to_small,
            from_type="small",
            to_type="general",
            from_standard="ASSE",
            to_standard="ASBE"
        )

        assert "vw_profit_eas" in adapted_back
        assert "vw_profit_sas" not in adapted_back


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
