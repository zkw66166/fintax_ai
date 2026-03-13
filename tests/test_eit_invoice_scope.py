"""测试EIT和发票域的视图选择逻辑

验证：
1. EIT年报/季报根据period_quarter正确路由
2. 发票采购/销售根据概念名称正确路由
3. get_scope_view()函数正确工作
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.entity_preprocessor import get_scope_view
from modules.concept_registry import CONCEPT_REGISTRY, resolve_concepts


class TestEITViewSelection:
    """测试EIT域视图选择（年报/季报）"""

    def test_eit_annual_view_selection(self):
        """年度查询选择年报视图"""
        # report_type=None 或不传 → 年报
        view = get_scope_view('', domain='eit', report_type=None)
        assert view == 'vw_eit_annual_main'

    def test_eit_quarterly_view_selection(self):
        """季度查询选择季报视图"""
        # report_type='quarter' → 季报
        view = get_scope_view('', domain='eit', report_type='quarter')
        assert view == 'vw_eit_quarter_main'

    def test_eit_all_quarters(self):
        """验证所有季度都选择季报视图"""
        # 所有季度都使用 report_type='quarter'
        view = get_scope_view('', domain='eit', report_type='quarter')
        assert view == 'vw_eit_quarter_main'


class TestInvoiceViewSelection:
    """测试发票域视图选择（采购/销售）"""

    def test_purchase_invoice_concepts(self):
        """采购发票概念指向采购视图"""
        purchase_concepts = ['采购金额', '采购税额', '采购价税合计']

        for concept_name in purchase_concepts:
            assert concept_name in CONCEPT_REGISTRY, f"{concept_name} not found"
            concept_def = CONCEPT_REGISTRY[concept_name]
            assert concept_def['domain'] == 'invoice'
            assert concept_def['view'] == 'vw_inv_spec_purchase', \
                f"{concept_name} should use purchase view"

    def test_sales_invoice_concepts(self):
        """销售发票概念指向销售视图"""
        sales_concepts = ['销售金额', '销售税额', '销售价税合计']

        for concept_name in sales_concepts:
            assert concept_name in CONCEPT_REGISTRY, f"{concept_name} not found"
            concept_def = CONCEPT_REGISTRY[concept_name]
            assert concept_def['domain'] == 'invoice'
            assert concept_def['view'] == 'vw_inv_spec_sales', \
                f"{concept_name} should use sales view"

    def test_purchase_query_matches_purchase_concepts(self):
        """采购查询匹配采购概念"""
        query = '华兴科技2025年3月采购金额'
        entities = {
            'taxpayer_id': 'HX001',
            'period_year': 2025,
            'period_month': 3
        }

        concepts = resolve_concepts(query, entities)
        assert len(concepts) == 1
        assert concepts[0]['name'] == '采购金额'
        assert concepts[0]['def']['view'] == 'vw_inv_spec_purchase'

    def test_sales_query_matches_sales_concepts(self):
        """销售查询匹配销售概念"""
        query = '华兴科技2025年3月销售金额'
        entities = {
            'taxpayer_id': 'HX001',
            'period_year': 2025,
            'period_month': 3
        }

        concepts = resolve_concepts(query, entities)
        assert len(concepts) == 1
        assert concepts[0]['name'] == '销售金额'
        assert concepts[0]['def']['view'] == 'vw_inv_spec_sales'


class TestGetScopeViewFunction:
    """测试get_scope_view()函数的完整性"""

    def test_balance_sheet_eas(self):
        """资产负债表EAS"""
        view = get_scope_view('', domain='balance_sheet', accounting_standard='企业会计准则')
        assert view == 'vw_balance_sheet_eas'

    def test_balance_sheet_sas(self):
        """资产负债表SAS"""
        view = get_scope_view('', domain='balance_sheet', accounting_standard='小企业会计准则')
        assert view == 'vw_balance_sheet_sas'

    def test_profit_eas(self):
        """利润表EAS"""
        view = get_scope_view('', domain='profit', accounting_standard='企业会计准则')
        assert view == 'vw_profit_eas'

    def test_profit_sas(self):
        """利润表SAS"""
        view = get_scope_view('', domain='profit', accounting_standard='小企业会计准则')
        assert view == 'vw_profit_sas'

    def test_vat_general(self):
        """增值税一般纳税人"""
        view = get_scope_view('一般纳税人')
        assert view == 'vw_vat_return_general'

    def test_vat_small(self):
        """增值税小规模纳税人"""
        view = get_scope_view('小规模纳税人')
        assert view == 'vw_vat_return_small'

    def test_eit_annual(self):
        """企业所得税年报"""
        view = get_scope_view('', domain='eit')
        assert view == 'vw_eit_annual_main'

    def test_eit_quarterly(self):
        """企业所得税季报"""
        view = get_scope_view('', domain='eit', report_type='quarter')
        assert view == 'vw_eit_quarter_main'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
