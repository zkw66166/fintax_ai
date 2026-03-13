"""测试概念外置化与细分功能"""
import pytest
import sys
from pathlib import Path

# 确保项目根目录在path中
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.concept_registry import (
    CONCEPT_REGISTRY,
    resolve_concepts,
    load_concepts_from_config,
    _CONCEPT_ALIASES
)


class TestConceptLoading:
    """测试概念从JSON加载"""

    def test_total_concepts_loaded(self):
        """验证总概念数量"""
        assert len(CONCEPT_REGISTRY) == 326, f"Expected 326 concepts, got {len(CONCEPT_REGISTRY)}"

    def test_domain_distribution(self):
        """验证各域概念数量"""
        from collections import Counter
        domains = Counter(d.get('domain') for d in CONCEPT_REGISTRY.values())

        expected = {
            'balance_sheet': 108,  # 68 EAS + 40 SAS
            'profit': 93,          # 61 EAS + 32 SAS
            'cash_flow': 41,       # 35 EAS + 6 SAS
            'vat': 34,             # 30 General + 4 Small
            'eit': 18,
            'invoice': 6,
            'financial_metrics': 26
        }

        for domain, count in expected.items():
            assert domains[domain] == count, f"Domain {domain}: expected {count}, got {domains[domain]}"

    def test_eas_sas_variants_exist(self):
        """验证EAS/SAS变体都存在"""
        # 检查资产负债表概念
        assert '货币资金' in CONCEPT_REGISTRY
        assert '货币资金_SAS' in CONCEPT_REGISTRY
        assert CONCEPT_REGISTRY['货币资金']['accounting_standard'] == '企业会计准则'
        assert CONCEPT_REGISTRY['货币资金_SAS']['accounting_standard'] == '小企业会计准则'

        # 检查利润表概念
        assert '营业收入' in CONCEPT_REGISTRY
        assert '营业收入_SAS' in CONCEPT_REGISTRY
        assert CONCEPT_REGISTRY['营业收入']['accounting_standard'] == '企业会计准则'
        assert CONCEPT_REGISTRY['营业收入_SAS']['accounting_standard'] == '小企业会计准则'

    def test_vat_variants_exist(self):
        """验证VAT一般/小规模变体都存在"""
        assert '销项税额' in CONCEPT_REGISTRY
        assert CONCEPT_REGISTRY['销项税额']['taxpayer_type'] == '一般纳税人'

        assert '免税销售额_小规模' in CONCEPT_REGISTRY
        assert CONCEPT_REGISTRY['免税销售额_小规模']['taxpayer_type'] == '小规模纳税人'

    def test_unified_domains_no_suffix(self):
        """验证统一域（EIT/invoice/financial_metrics）无后缀"""
        # EIT概念
        assert '应纳税所得额' in CONCEPT_REGISTRY
        assert '应纳税所得额_SAS' not in CONCEPT_REGISTRY
        assert '应纳税所得额_小规模' not in CONCEPT_REGISTRY

        # Invoice概念
        assert '采购金额' in CONCEPT_REGISTRY
        assert '采购金额_SAS' not in CONCEPT_REGISTRY

        # Financial metrics概念
        assert '企业所得税税负率' in CONCEPT_REGISTRY
        assert '企业所得税税负率_SAS' not in CONCEPT_REGISTRY


class TestConceptFiltering:
    """测试概念匹配过滤"""

    def test_eas_company_matches_eas_concepts(self):
        """EAS公司匹配EAS概念"""
        query = '华兴科技2025年3月货币资金'
        entities = {
            'taxpayer_id': 'HX001',
            'taxpayer_type': '一般纳税人',
            'accounting_standard': '企业会计准则',
            'period_year': 2025,
            'period_month': 3
        }
        concepts = resolve_concepts(query, entities)

        assert len(concepts) == 1
        assert concepts[0]['name'] == '货币资金'
        assert concepts[0]['def']['view'] == 'vw_balance_sheet_eas'
        assert concepts[0]['def']['accounting_standard'] == '企业会计准则'

    def test_sas_company_matches_sas_concepts(self):
        """SAS公司匹配SAS概念"""
        query = '鑫源贸易2025年3月货币资金'
        entities = {
            'taxpayer_id': 'XY001',
            'taxpayer_type': '小规模纳税人',
            'accounting_standard': '小企业会计准则',
            'period_year': 2025,
            'period_month': 3
        }
        concepts = resolve_concepts(query, entities)

        assert len(concepts) == 1
        assert concepts[0]['name'] == '货币资金_SAS'
        assert concepts[0]['def']['view'] == 'vw_balance_sheet_sas'
        assert concepts[0]['def']['accounting_standard'] == '小企业会计准则'

    def test_general_taxpayer_matches_general_vat(self):
        """一般纳税人匹配一般纳税人VAT概念"""
        query = '华兴科技2025年3月销项税额'
        entities = {
            'taxpayer_id': 'HX001',
            'taxpayer_type': '一般纳税人',
            'period_year': 2025,
            'period_month': 3
        }
        concepts = resolve_concepts(query, entities)

        assert len(concepts) == 1
        assert concepts[0]['name'] == '销项税额'
        assert concepts[0]['def']['view'] == 'vw_vat_return_general'
        assert concepts[0]['def']['taxpayer_type'] == '一般纳税人'

    def test_small_taxpayer_matches_small_vat(self):
        """小规模纳税人匹配小规模VAT概念"""
        query = '鑫源贸易2025年3月免税销售额'
        entities = {
            'taxpayer_id': 'XY001',
            'taxpayer_type': '小规模纳税人',
            'period_year': 2025,
            'period_month': 3
        }
        concepts = resolve_concepts(query, entities)

        assert len(concepts) == 1
        assert concepts[0]['name'] == '免税销售额_小规模'
        assert concepts[0]['def']['view'] == 'vw_vat_return_small'
        assert concepts[0]['def']['taxpayer_type'] == '小规模纳税人'

    def test_unified_domain_matches_regardless_of_standard(self):
        """统一域概念不受准则/类型限制"""
        # EIT概念
        query1 = '华兴科技2025年应纳税所得额'
        entities1 = {
            'taxpayer_id': 'HX001',
            'taxpayer_type': '一般纳税人',
            'accounting_standard': '企业会计准则',
            'period_year': 2025
        }
        concepts1 = resolve_concepts(query1, entities1)
        assert len(concepts1) == 1
        assert concepts1[0]['name'] == '应纳税所得额'

        # 同一概念，SAS公司也能匹配
        query2 = '鑫源贸易2025年应纳税所得额'
        entities2 = {
            'taxpayer_id': 'XY001',
            'taxpayer_type': '小规模纳税人',
            'accounting_standard': '小企业会计准则',
            'period_year': 2025
        }
        concepts2 = resolve_concepts(query2, entities2)
        assert len(concepts2) == 1
        assert concepts2[0]['name'] == '应纳税所得额'

    def test_cross_standard_filtering(self):
        """验证跨准则过滤：EAS公司不匹配SAS概念"""
        query = '华兴科技2025年3月货币资金和营业收入'
        entities = {
            'taxpayer_id': 'HX001',
            'taxpayer_type': '一般纳税人',
            'accounting_standard': '企业会计准则',
            'period_year': 2025,
            'period_month': 3
        }
        concepts = resolve_concepts(query, entities)

        # 应该匹配2个EAS概念，不匹配SAS概念
        assert len(concepts) == 2
        concept_names = [c['name'] for c in concepts]
        assert '货币资金' in concept_names
        assert '营业收入' in concept_names
        assert '货币资金_SAS' not in concept_names
        assert '营业收入_SAS' not in concept_names


class TestAliasMapping:
    """测试别名映射"""

    def test_base_name_maps_to_multiple_variants(self):
        """基础名称映射到多个变体"""
        assert '货币资金' in _CONCEPT_ALIASES
        aliases = _CONCEPT_ALIASES['货币资金']
        assert isinstance(aliases, list)
        assert '货币资金' in aliases
        assert '货币资金_SAS' in aliases

    def test_suffixed_name_maps_to_itself(self):
        """带后缀名称映射到自己"""
        assert '货币资金_SAS' in _CONCEPT_ALIASES
        aliases = _CONCEPT_ALIASES['货币资金_SAS']
        assert isinstance(aliases, list)
        assert '货币资金_SAS' in aliases

    def test_alias_maps_to_all_variants(self):
        """别名映射到所有变体"""
        assert '现金及等价物' in _CONCEPT_ALIASES  # 货币资金的别名
        aliases = _CONCEPT_ALIASES['现金及等价物']
        assert isinstance(aliases, list)
        assert len(aliases) >= 2  # 至少包含EAS和SAS


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
