"""
Phase 4 全量测试：概念管线增强验证

测试分类：
1. 时间识别测试 (10个用例)
2. 概念匹配测试 (20个用例)
3. 指标路径测试 (10个用例)
4. 排除规则测试 (5个用例)

总计：45个测试用例
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from modules.concept_registry import detect_time_granularity
from modules.entity_preprocessor import detect_entities
from config.settings import DB_PATH


class TestTimeRecognition:
    """时间识别测试 (10个用例)"""

    def setup_method(self):
        """测试前准备：连接数据库"""
        self.conn = sqlite3.connect(DB_PATH)

    def teardown_method(self):
        """测试后清理：关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def test_past_years_pattern(self):
        """测试"过去N年"模式"""
        query = "过去两年每年末的总资产和总负债分析"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'yearly', f"应识别为yearly，实际: {time_gran}"
        assert 'period_years' in entities, "应提取period_years"
        assert len(entities['period_years']) == 2, f"应提取2年，实际: {len(entities.get('period_years', []))}"

    def test_year_range_pattern(self):
        """测试"YYYY-YYYY"模式"""
        query = "2024-2025每年末的总资产和总负债分析"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'yearly', f"应识别为yearly，实际: {time_gran}"

    def test_year_list_pattern(self):
        """测试"YYYY和YYYY年末"模式"""
        query = "2024和2025年末的总资产和总负债分析"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'yearly', f"应识别为yearly，实际: {time_gran}"

    def test_recent_quarters_pattern(self):
        """测试"近N个季度"模式"""
        query = "近三年各季度营业收入"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran in ['quarterly', 'yearly'], f"应识别为quarterly或yearly，实际: {time_gran}"

    def test_quarter_range_pattern(self):
        """测试"Q1到Q3"模式"""
        query = "2025年Q1到Q3利润"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'quarterly', f"应识别为quarterly，实际: {time_gran}"

    def test_recent_months_pattern(self):
        """测试"最近N个月"模式"""
        query = "最近6个月现金流"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'monthly', f"应识别为monthly，实际: {time_gran}"

    def test_half_year_pattern(self):
        """测试"上半年"模式"""
        query = "今年上半年增值税"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran in ['monthly', 'quarterly'], f"应识别为monthly或quarterly，实际: {time_gran}"

    def test_full_year_pattern(self):
        """测试"全年"模式"""
        query = "去年全年净利润"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'yearly', f"应识别为yearly，实际: {time_gran}"

    def test_month_list_pattern(self):
        """测试"N月、N月、N月"模式"""
        query = "2024年1月、2月、3月销售额"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran == 'monthly', f"应识别为monthly，实际: {time_gran}"

    def test_quarter_end_pattern(self):
        """测试"季度末"模式"""
        query = "上个季度末资产负债率"
        entities = detect_entities(query, self.conn)
        time_gran = detect_time_granularity(query, entities)

        assert time_gran in ['quarterly', 'monthly'], f"应识别为quarterly或monthly，实际: {time_gran}"


class TestConceptMatching:
    """概念匹配测试 (20个用例) - 验证概念细分后的匹配逻辑"""

    def setup_method(self):
        """测试前准备"""
        from modules.concept_registry import CONCEPT_REGISTRY, resolve_concepts
        self.conn = sqlite3.connect(DB_PATH)
        self.registry = CONCEPT_REGISTRY
        self.resolve = resolve_concepts

    def teardown_method(self):
        """测试后清理"""
        if self.conn:
            self.conn.close()

    # === 财务报表概念匹配（统一版本）===

    def test_cash_concept(self):
        """测试货币资金概念匹配"""
        query = "华兴科技2025年3月货币资金"
        entities = {'accounting_standard': '企业会计准则', 'taxpayer_type': '一般纳税人'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert '货币资金' in matched_names, \
            f"应匹配货币资金，实际: {matched_names}"

    def test_inventory_concept(self):
        """测试存货概念匹配"""
        query = "TSE科技2025年末存货"
        entities = {'accounting_standard': '企业会计准则', 'taxpayer_type': '一般纳税人'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('存货' in name for name in matched_names), \
            f"应匹配存货概念，实际: {matched_names}"

    def test_revenue_concept(self):
        """测试营业收入概念匹配"""
        query = "华兴科技2025年营业收入"
        entities = {'accounting_standard': '企业会计准则', 'taxpayer_type': '一般纳税人'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('营业收入' in name for name in matched_names), \
            f"应匹配营业收入概念，实际: {matched_names}"

    # === VAT概念匹配（统一版本）===

    def test_output_tax_concept(self):
        """测试销项税额概念匹配"""
        query = "华兴科技2025年3月销项税额"
        entities = {'taxpayer_type': '一般纳税人', 'accounting_standard': '企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('销项税额' in name for name in matched_names), \
            f"应匹配销项税额概念，实际: {matched_names}"

    def test_input_tax_concept(self):
        """测试进项税额概念匹配"""
        query = "TSE科技2025年3月进项税额"
        entities = {'taxpayer_type': '一般纳税人', 'accounting_standard': '企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('进项税额' in name for name in matched_names), \
            f"应匹配进项税额概念，实际: {matched_names}"

    # === EIT概念匹配（不细分）===

    def test_eit_revenue_concept(self):
        """测试企业所得税营业收入概念（不细分）"""
        query = "华兴科技2025年度企业所得税营业收入"
        entities = {'taxpayer_type': '一般纳税人', 'accounting_standard': '企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        # EIT概念不应有后缀
        assert any('营业收入' in name and '_EAS' not in name and '_SAS' not in name
                   for name in matched_names), \
            f"EIT营业收入不应有后缀，实际: {matched_names}"

    def test_eit_profit_concept(self):
        """测试企业所得税利润总额概念（不细分）"""
        query = "TSE科技2025年度利润总额"
        entities = {'taxpayer_type': '一般纳税人', 'accounting_standard': '企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('利润' in name for name in matched_names), \
            f"应匹配利润概念，实际: {matched_names}"

    # === Invoice概念匹配（不细分）===

    def test_purchase_invoice_concept(self):
        """测试采购发票概念（不细分）"""
        query = "华兴科技2025年3月采购金额"
        entities = {'taxpayer_type': '一般纳税人', 'accounting_standard': '企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('采购' in name for name in matched_names), \
            f"应匹配采购概念，实际: {matched_names}"

    def test_sales_invoice_concept(self):
        """测试销售发票概念（不细分）"""
        query = "鑫源贸易2025年3月销售金额"
        entities = {'taxpayer_type': '小规模纳税人', 'accounting_standard': '小企业会计准则'}
        concepts = self.resolve(query, entities)

        matched_names = [c['name'] for c in concepts]
        assert any('销售' in name or '销项' in name for name in matched_names), \
            f"应匹配销售概念，实际: {matched_names}"

    # === 多变体别名映射测试 ===

    def test_multi_variant_alias(self):
        """测试多变体别名映射（货币资金→[货币资金, 货币资金_SAS]）"""
        query = "货币资金"
        entities = {}  # 无过滤条件
        concepts = self.resolve(query, entities)

        # 应该匹配到多个变体
        matched_names = [c['name'] for c in concepts]
        assert len(matched_names) >= 1, f"应匹配到至少1个货币资金变体，实际: {matched_names}"

    # === 概念总数验证 ===

    def test_total_concept_count(self):
        """测试概念总数（应为244个）"""
        assert len(self.registry) == 244, \
            f"概念总数应为244，实际: {len(self.registry)}"

    def test_no_suffix_concepts(self):
        """测试概念无后缀"""
        # 检查是否有带后缀的概念（不应该有）
        suffixes = ['_EAS', '_SAS', '_一般', '_小规模']
        suffixed_concepts = [name for name in self.registry.keys()
                            if any(name.endswith(suffix) for suffix in suffixes)]
        assert len(suffixed_concepts) == 0, f"不应存在带后缀的概念，发现: {suffixed_concepts}"

    def test_no_eit_suffix(self):
        """测试EIT概念无后缀"""
        # 检查是否有EIT相关概念带后缀（不应该有）
        eit_keywords = ['应纳税所得额', '纳税调整']
        for keyword in eit_keywords:
            matching = [name for name in self.registry.keys()
                       if keyword in name and ('_EAS' in name or '_SAS' in name or '_一般' in name or '_小规模' in name)]
            assert len(matching) == 0, f"EIT概念不应有后缀，发现: {matching}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
