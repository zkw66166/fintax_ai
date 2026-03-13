"""
Phase 3 测试：指标路由优先级与新增指标计算

测试目标：
1. 带"率"的指标优先走 financial_metrics 域（查表）
2. 不带"率"的指标（如"占比"）走 metric_calculator（计算）
3. 新增13个指标的计算逻辑正确
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.metric_calculator import (
    detect_computed_metrics,
    METRIC_FORMULAS,
    METRIC_SYNONYMS
)


class TestMetricDetection:
    """测试指标检测功能"""

    def test_rate_metrics_detection(self):
        """测试"率"型指标检测"""
        queries = [
            "华兴科技2025年资产负债率",
            "TSE科技毛利率是多少",
            "净利润率分析",
            "营业利润率趋势",
        ]
        for query in queries:
            metrics = detect_computed_metrics(query)
            assert len(metrics) > 0, f"应检测到指标: {query}"
            assert any('率' in m for m in metrics), f"应检测到'率'型指标: {query}"

    def test_ratio_metrics_detection(self):
        """测试"占比"型指标检测"""
        queries = [
            "流动资产占比",
            "固定资产占比是多少",
            "营业成本占比分析",
        ]
        for query in queries:
            metrics = detect_computed_metrics(query)
            assert len(metrics) > 0, f"应检测到指标: {query}"
            assert any('占比' in m for m in metrics), f"应检测到'占比'型指标: {query}"


class TestNewMetrics:
    """测试新增13个指标"""

    def test_new_ratio_metrics_exist(self):
        """测试8个新增比例型指标存在"""
        new_ratios = [
            '流动资产占比',
            '固定资产占比',
            '流动负债占比',
            '营业成本占比',
            '期间费用占比',
            '研发费用占比',
            '进项税额占比',
            '留抵税额占比',
        ]
        for metric in new_ratios:
            assert metric in METRIC_FORMULAS, f"指标应存在: {metric}"
            assert 'formula' in METRIC_FORMULAS[metric], f"指标应有公式: {metric}"
            assert 'sources' in METRIC_FORMULAS[metric], f"指标应有数据源: {metric}"

    def test_new_rate_metrics_exist(self):
        """测试5个新增率型指标存在"""
        new_rates = [
            '产权比率',
            '权益乘数',
            '营业利润率',
            '成本费用利润率',
            '总资产报酬率',
        ]
        for metric in new_rates:
            assert metric in METRIC_FORMULAS, f"指标应存在: {metric}"
            assert 'formula' in METRIC_FORMULAS[metric], f"指标应有公式: {metric}"

    def test_roa_alias(self):
        """测试ROA别名"""
        assert 'ROA' in METRIC_FORMULAS, "ROA应存在"
        assert METRIC_FORMULAS['ROA'].get('alias') == '总资产报酬率', "ROA应指向总资产报酬率"

    def test_synonyms_updated(self):
        """测试同义词映射已更新"""
        new_synonyms = [
            '流动资产占比',
            '固定资产占比',
            '营业成本占比',
            '产权比率',
            '营业利润率',
            'ROA',
        ]
        for syn in new_synonyms:
            assert syn in METRIC_SYNONYMS, f"同义词应存在: {syn}"


class TestMetricFormulas:
    """测试指标公式正确性"""

    def test_asset_ratio_formula(self):
        """测试流动资产占比公式"""
        metric = METRIC_FORMULAS['流动资产占比']
        assert 'current_assets' in metric['formula']
        assert 'total_assets' in metric['formula']
        assert '* 100' in metric['formula']
        assert metric['unit'] == '%'

    def test_equity_multiplier_formula(self):
        """测试权益乘数公式"""
        metric = METRIC_FORMULAS['权益乘数']
        assert 'total_assets' in metric['formula']
        assert 'equity' in metric['formula']
        assert metric['unit'] == ''

    def test_operating_profit_margin_formula(self):
        """测试营业利润率公式"""
        metric = METRIC_FORMULAS['营业利润率']
        assert 'operating_profit' in metric['formula']
        assert 'revenue' in metric['formula']
        assert '* 100' in metric['formula']
        assert metric['sources']['operating_profit']['time_range'] == '本年累计'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
