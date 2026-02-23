"""display_formatter 单元测试"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.display_formatter import (
    format_number, format_display, _is_percentage_col,
    _filter_columns, HIDDEN_COLUMNS, ColumnMapper, COMMON_COLUMN_CN,
)


class TestFormatNumber(unittest.TestCase):
    def test_none(self):
        self.assertEqual(format_number(None), '-')

    def test_string(self):
        self.assertEqual(format_number('abc'), 'abc')

    def test_zero(self):
        self.assertEqual(format_number(0), '0.00')

    def test_yi(self):
        """≥1亿 → X.XX亿"""
        r = format_number(150000000.0)
        self.assertIn('亿', r)
        self.assertIn('1.50', r)

    def test_wan(self):
        """≥1万 → X.XX万"""
        r = format_number(123456.78)
        self.assertIn('万', r)
        self.assertIn('12.35', r)

    def test_small_number(self):
        r = format_number(1234.5)
        self.assertEqual(r, '1,234.50')

    def test_negative_yi(self):
        r = format_number(-200000000)
        self.assertIn('亿', r)
        self.assertIn('-2.00', r)

    def test_percentage(self):
        self.assertEqual(format_number(25.5, is_percentage=True), '25.50%')

    def test_percentage_zero(self):
        self.assertEqual(format_number(0, is_percentage=True), '0.00%')


class TestPercentageDetection(unittest.TestCase):
    def test_explicit_set(self):
        self.assertTrue(_is_percentage_col('tax_rate'))

    def test_suffix_rate(self):
        self.assertTrue(_is_percentage_col('branch_share_rate'))

    def test_suffix_ratio(self):
        self.assertTrue(_is_percentage_col('debt_ratio'))

    def test_paren_suffix(self):
        self.assertTrue(_is_percentage_col('some_col(%)'))

    def test_normal_col(self):
        self.assertFalse(_is_percentage_col('output_tax'))


class TestHiddenColumns(unittest.TestCase):
    def test_filter(self):
        row = {
            'taxpayer_name': '华兴科技',
            'output_tax': 100000,
            'revision_no': 1,
            'etl_batch_id': 'b001',
            'etl_confidence': 0.99,
        }
        filtered = _filter_columns(row)
        self.assertIn('taxpayer_name', filtered)
        self.assertIn('output_tax', filtered)
        self.assertNotIn('revision_no', filtered)
        self.assertNotIn('etl_batch_id', filtered)
        self.assertNotIn('etl_confidence', filtered)


class TestColumnMapper(unittest.TestCase):
    def test_common_column(self):
        """通用列映射不需要数据库"""
        mapper = ColumnMapper()
        # 强制标记已加载，避免连接数据库
        mapper._loaded = True
        self.assertEqual(mapper.translate('taxpayer_name'), '纳税人名称')
        self.assertEqual(mapper.translate('period_year'), '年度')

    def test_unknown_fallback(self):
        mapper = ColumnMapper()
        mapper._loaded = True
        self.assertEqual(mapper.translate('xyz_unknown_col'), 'xyz_unknown_col')


class TestFormatDisplay(unittest.TestCase):
    def test_empty_results(self):
        result = {'success': True, 'results': []}
        self.assertEqual(format_display(result), '无数据')

    def test_single_row_kv(self):
        """单行少列 → KV 列表"""
        result = {
            'success': True,
            'results': [{'taxpayer_name': '华兴科技', 'output_tax': 150000}],
            'intent': {'domain': 'vat'},
        }
        out = format_display(result)
        self.assertIn('纳税人名称', out)
        self.assertIn('华兴科技', out)
        self.assertIn('15.00万', out)

    def test_multi_row_table(self):
        """多行 → Markdown 表格"""
        result = {
            'success': True,
            'results': [
                {'taxpayer_name': '华兴科技', 'period_month': 1, 'output_tax': 100000},
                {'taxpayer_name': '华兴科技', 'period_month': 2, 'output_tax': 200000},
                {'taxpayer_name': '华兴科技', 'period_month': 3, 'output_tax': 300000},
            ],
            'intent': {'domain': 'vat'},
        }
        out = format_display(result)
        self.assertIn('纳税人名称', out)
        self.assertIn('月份', out)
        self.assertIn('|', out)

    def test_hidden_cols_not_in_output(self):
        result = {
            'success': True,
            'results': [{'taxpayer_name': '华兴', 'output_tax': 100, 'revision_no': 1}],
            'intent': {'domain': 'vat'},
        }
        out = format_display(result)
        self.assertNotIn('revision_no', out)

    def test_metric_result(self):
        """计算指标展示"""
        result = {
            'success': True,
            'results': [{'label': '资产负债率', 'value': 45.67, 'unit': '%'}],
            'metric_results': [
                {'label': '资产负债率', 'value': 45.67, 'unit': '%',
                 'sources': {'total_liabilities': 456700, 'total_assets': 1000000}},
            ],
        }
        out = format_display(result)
        self.assertIn('资产负债率', out)
        self.assertIn('45.67%', out)
        self.assertIn('计算依据', out)

    def test_cross_domain(self):
        """跨域结果展示"""
        result = {
            'success': True,
            'results': [
                {'指标': '营业收入', '值': 5000000, '_source_domain': 'profit'},
                {'指标': '销项税额', '值': 650000, '_source_domain': 'vat'},
            ],
            'cross_domain_summary': '利润表 vs 增值税对比',
            'sub_results': [{'domain': 'profit'}, {'domain': 'vat'}],
            'intent': {'domain': 'cross_domain'},
        }
        out = format_display(result)
        self.assertIn('利润表 vs 增值税对比', out)
        self.assertIn('|', out)

    def test_none_values_display_dash(self):
        result = {
            'success': True,
            'results': [{'taxpayer_name': '华兴', 'output_tax': None}],
            'intent': {'domain': 'vat'},
        }
        out = format_display(result)
        self.assertIn('-', out)


if __name__ == '__main__':
    unittest.main()

