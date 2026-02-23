"""概念注册表单元测试"""
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_PATH
from modules.concept_registry import (
    CONCEPT_REGISTRY, resolve_concepts, detect_time_granularity,
    build_concept_sql, execute_computed_concept, merge_concept_results,
    _CONCEPT_ALIASES,
)
from modules.entity_preprocessor import detect_entities


class TestConceptRegistry(unittest.TestCase):
    """概念注册表数据结构测试"""

    def test_registry_not_empty(self):
        self.assertGreater(len(CONCEPT_REGISTRY), 30)

    def test_all_concepts_have_required_fields(self):
        for name, defn in CONCEPT_REGISTRY.items():
            self.assertIn('domain', defn, f"{name} missing domain")
            self.assertIn('label', defn, f"{name} missing label")
            self.assertIn('quarterly_strategy', defn, f"{name} missing quarterly_strategy")
            if defn.get('type') != 'computed':
                self.assertIn('column', defn, f"{name} missing column")

    def test_alias_index_covers_all(self):
        for name, defn in CONCEPT_REGISTRY.items():
            self.assertIn(name, _CONCEPT_ALIASES)
            for alias in defn.get('aliases', []):
                self.assertIn(alias, _CONCEPT_ALIASES)
                self.assertEqual(_CONCEPT_ALIASES[alias], name)


class TestTimeGranularity(unittest.TestCase):
    """时间粒度检测测试"""

    def test_quarterly(self):
        self.assertEqual(detect_time_granularity('各季度的采购金额'), 'quarterly')
        self.assertEqual(detect_time_granularity('每季度销售额'), 'quarterly')

    def test_monthly(self):
        self.assertEqual(detect_time_granularity('各月的采购金额'), 'monthly')
        self.assertEqual(detect_time_granularity('按月统计'), 'monthly')

    def test_yearly(self):
        self.assertEqual(detect_time_granularity('各年的营业收入'), 'yearly')
        self.assertEqual(detect_time_granularity('按年对比'), 'yearly')

    def test_none(self):
        self.assertIsNone(detect_time_granularity('华兴科技2025年3月营业收入'))


class TestResolveConcepts(unittest.TestCase):
    """概念提取测试"""

    def test_basic_extraction(self):
        entities = {}
        concepts = resolve_concepts('采购金额和销售金额的关系', entities)
        names = [c['name'] for c in concepts]
        self.assertIn('采购金额', names)
        self.assertIn('销售金额', names)

    def test_alias_matching(self):
        concepts = resolve_concepts('进项金额和销项金额对比', {})
        names = [c['name'] for c in concepts]
        self.assertIn('采购金额', names)  # 进项金额 → 采购金额
        self.assertIn('销售金额', names)  # 销项金额 → 销售金额

    def test_four_concepts(self):
        query = '采购金额、销售金额、存货增加额和经营现金流出'
        concepts = resolve_concepts(query, {})
        names = [c['name'] for c in concepts]
        self.assertEqual(len(names), 4)
        self.assertIn('采购金额', names)
        self.assertIn('销售金额', names)
        self.assertIn('存货增加额', names)
        self.assertIn('经营活动现金流出', names)

    def test_no_duplicate(self):
        concepts = resolve_concepts('采购金额和采购金额', {})
        names = [c['name'] for c in concepts]
        self.assertEqual(names.count('采购金额'), 1)

    def test_longest_match(self):
        """经营活动现金流出 should match before 经营现金流出"""
        concepts = resolve_concepts('经营活动现金流出小计', {})
        names = [c['name'] for c in concepts]
        self.assertIn('经营活动现金流出', names)


class TestBuildConceptSQL(unittest.TestCase):
    """SQL构建测试"""

    def setUp(self):
        self.entities = {
            'taxpayer_id': 'T001',
            'taxpayer_type': '一般纳税人',
            'period_year': 2025,
        }

    def test_invoice_quarterly(self):
        cdef = CONCEPT_REGISTRY['采购金额']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIn('SUM(amount)', sql)
        self.assertIn('quarter', sql)
        self.assertIn('GROUP BY', sql)
        self.assertEqual(params['taxpayer_id'], 'T001')
        self.assertEqual(params['year'], 2025)

    def test_invoice_monthly(self):
        cdef = CONCEPT_REGISTRY['销售金额']
        sql, params = build_concept_sql(cdef, self.entities, 'monthly')
        self.assertIn('SUM(amount)', sql)
        self.assertIn('period_month', sql)

    def test_balance_sheet_quarterly(self):
        cdef = CONCEPT_REGISTRY['总资产']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIn('assets_end', sql)
        self.assertIn('IN (3,6,9,12)', sql)

    def test_profit_quarterly(self):
        cdef = CONCEPT_REGISTRY['营业收入']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIn('operating_revenue', sql)
        self.assertIn('time_range', sql)

    def test_cash_flow_quarterly(self):
        cdef = CONCEPT_REGISTRY['经营活动现金流出']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIn('operating_outflow_subtotal', sql)
        self.assertIn('IN (3,6,9,12)', sql)

    def test_computed_returns_none(self):
        cdef = CONCEPT_REGISTRY['存货增加额']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIsNone(sql)

    def test_vat_quarterly(self):
        cdef = CONCEPT_REGISTRY['销项税额']
        sql, params = build_concept_sql(cdef, self.entities, 'quarterly')
        self.assertIn('output_tax', sql)
        self.assertIn('item_type', sql)


class TestMergeResults(unittest.TestCase):
    """结果合并测试"""

    def test_quarterly_merge(self):
        results = [
            {'name': 'a', 'label': '采购金额', 'data': [
                {'quarter': 1, 'value': 100}, {'quarter': 2, 'value': 200},
            ]},
            {'name': 'b', 'label': '销售金额', 'data': [
                {'quarter': 1, 'value': 150}, {'quarter': 2, 'value': 250},
            ]},
        ]
        merged = merge_concept_results(results, 'quarterly')
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]['period'], 'Q1')
        self.assertEqual(merged[0]['采购金额'], 100)
        self.assertEqual(merged[0]['销售金额'], 150)
        self.assertEqual(merged[1]['period'], 'Q2')

    def test_monthly_merge(self):
        results = [
            {'name': 'a', 'label': '净利润', 'data': [
                {'period_month': 1, 'value': 10}, {'period_month': 2, 'value': 20},
            ]},
        ]
        merged = merge_concept_results(results, 'monthly')
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]['period'], '1月')

    def test_quarter_end_period_key(self):
        """quarter_end型数据用period_month，应正确映射到季度"""
        results = [
            {'name': 'a', 'label': '总资产', 'data': [
                {'period_month': 3, 'value': 1000},
                {'period_month': 6, 'value': 1100},
            ]},
        ]
        merged = merge_concept_results(results, 'quarterly')
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]['period'], 'Q1')
        self.assertEqual(merged[0]['总资产'], 1000)


class TestEndToEnd(unittest.TestCase):
    """端到端集成测试（需要数据库）"""

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(str(DB_PATH))
        cls.conn.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_entity_detection_cross_domain(self):
        """跨域查询应检测到time_granularity"""
        entities = detect_entities(
            '华兴科技去年各季度的采购金额、销售金额、存货增加额和经营现金流出的关系',
            self.conn
        )
        self.assertEqual(entities.get('time_granularity'), 'quarterly')

    def test_concept_resolve_target_query(self):
        """目标查询应提取4个概念"""
        query = '华兴科技2025年各季度的采购金额、销售金额、存货增加额和经营现金流出的关系'
        entities = detect_entities(query, self.conn)
        resolved = entities.get('resolved_query', query)
        concepts = resolve_concepts(resolved, entities)
        names = [c['name'] for c in concepts]
        self.assertGreaterEqual(len(names), 3)
        self.assertIn('采购金额', names)
        self.assertIn('销售金额', names)

    def test_sales_amount_not_profit_default(self):
        """销售金额不应再默认指向利润表"""
        from modules.entity_preprocessor import _PROFIT_DEFAULT_ITEMS
        self.assertNotIn('销售金额', _PROFIT_DEFAULT_ITEMS)
        self.assertNotIn('销售额', _PROFIT_DEFAULT_ITEMS)


if __name__ == '__main__':
    unittest.main()
