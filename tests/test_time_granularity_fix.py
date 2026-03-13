"""测试时间粒度检测增强功能"""
import pytest
from modules.concept_registry import detect_time_granularity
from modules.entity_preprocessor import _resolve_relative_dates, detect_entities
import sqlite3
from datetime import date


class TestTimeGranularityEnhancement:
    """测试时间粒度检测的新增模式"""

    def test_yearly_patterns_new(self):
        """测试新增的yearly模式"""
        from datetime import date
        today = date(2026, 3, 10)

        # 过去N年（需要先经过相对日期解析）
        resolved1 = _resolve_relative_dates("过去两年销售额", today)
        assert detect_time_granularity(resolved1) == 'yearly'

        resolved2 = _resolve_relative_dates("过去三年利润", today)
        assert detect_time_granularity(resolved2) == 'yearly'

        resolved3 = _resolve_relative_dates("近两年增长率", today)
        assert detect_time_granularity(resolved3) == 'yearly'

        resolved4 = _resolve_relative_dates("最近三年趋势", today)
        assert detect_time_granularity(resolved4) == 'yearly'

        # 年份范围（直接匹配正则）
        assert detect_time_granularity("2024-2025年末总资产") == 'yearly'
        assert detect_time_granularity("2024到2025年利润") == 'yearly'
        assert detect_time_granularity("2024和2025年对比") == 'yearly'

        # 年末/年初
        assert detect_time_granularity("每年末资产负债率") == 'yearly'
        assert detect_time_granularity("各年底存货") == 'yearly'
        assert detect_time_granularity("每年初现金") == 'yearly'

    def test_quarterly_patterns_new(self):
        """测试新增的quarterly模式"""
        assert detect_time_granularity("Q1销售额") == 'quarterly'
        assert detect_time_granularity("Q4利润") == 'quarterly'
        assert detect_time_granularity("第一季度收入") == 'quarterly'
        assert detect_time_granularity("季度走势分析") == 'quarterly'

    def test_monthly_patterns_new(self):
        """测试新增的monthly模式"""
        assert detect_time_granularity("月度走势") == 'monthly'
        assert detect_time_granularity("每月末库存") == 'monthly'
        assert detect_time_granularity("各月底余额") == 'monthly'

    def test_entities_inference_rules(self):
        """测试新增的entities推断规则"""
        # 规则1: period_end_year != period_year
        entities1 = {'period_year': 2024, 'period_end_year': 2025}
        assert detect_time_granularity("总资产", entities1) == 'yearly'

        # 规则2: "年末" + 多年
        entities2 = {'period_years': [2024, 2025]}
        assert detect_time_granularity("年末总资产", entities2) == 'yearly'

        # 规则3: period_months 多个
        entities3 = {'period_months': [1, 2, 3]}
        assert detect_time_granularity("销售额", entities3) == 'monthly'

        # 规则4: period_end_month != period_month
        entities4 = {'period_month': 1, 'period_end_month': 3}
        assert detect_time_granularity("收入", entities4) == 'monthly'


class TestRelativeDateResolution:
    """测试相对日期解析增强"""

    def test_past_n_years(self):
        """测试"过去N年"解析"""
        today = date(2026, 3, 10)

        # 过去两年 → 2024年到2025年
        result = _resolve_relative_dates("过去两年销售额", today)
        assert "2024年到2025年" in result

        # 过去三年 → 2023年到2025年
        result = _resolve_relative_dates("过去三年利润", today)
        assert "2023年到2025年" in result

        # 过去一年 → 2025年
        result = _resolve_relative_dates("过去一年增长率", today)
        assert "2025年" in result

    def test_past_n_tax_years(self):
        """测试"过去N个纳税年度"解析（已有功能，确保不破坏）"""
        today = date(2026, 3, 10)

        result = _resolve_relative_dates("过去两个纳税年度", today)
        assert "2024年到2025年" in result

    def test_recent_n_years(self):
        """测试"近N年"/"最近N年"解析（已有功能，确保不破坏）"""
        today = date(2026, 3, 10)

        result = _resolve_relative_dates("近两年销售额", today)
        assert "2025年到2026年" in result

        result = _resolve_relative_dates("最近三年利润", today)
        assert "2024年到2026年" in result


class TestIntegrationScenarios:
    """测试完整场景（问题案例）"""

    @pytest.fixture
    def db_conn(self):
        """创建测试数据库连接"""
        conn = sqlite3.connect(':memory:')
        # 创建测试表
        conn.execute("""
            CREATE TABLE taxpayer_info (
                taxpayer_id TEXT PRIMARY KEY,
                taxpayer_name TEXT,
                taxpayer_type TEXT,
                accounting_standard TEXT
            )
        """)
        conn.execute("""
            INSERT INTO taxpayer_info VALUES
            ('HX001', '华兴科技', '一般纳税人', '企业会计准则')
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_scenario_1_past_two_years_year_end(self, db_conn):
        """场景1: "过去两年每年末的总资产和总负债分析" """
        today = date(2026, 3, 10)
        query = "华兴科技过去两年每年末的总资产和总负债分析"

        # Step 1: 相对日期解析
        resolved = _resolve_relative_dates(query, today)
        assert "2024年到2025年" in resolved

        # Step 2: 实体检测
        entities = detect_entities(resolved, db_conn)
        assert entities['taxpayer_id'] == 'HX001'
        assert entities['period_years'] == [2024, 2025]

        # Step 3: 时间粒度检测
        time_gran = detect_time_granularity(resolved, entities)
        assert time_gran == 'yearly'

    def test_scenario_2_year_range_year_end(self, db_conn):
        """场景2: "2024-2025每年末的总资产和总负债分析" """
        query = "华兴科技2024-2025每年末的总资产和总负债分析"

        # Step 1: 实体检测（年份范围已在entity_preprocessor中处理）
        entities = detect_entities(query, db_conn)
        assert entities['taxpayer_id'] == 'HX001'
        # 检查是否提取到年份范围
        assert entities.get('period_year') == 2024
        assert entities.get('period_years') == [2024, 2025]

        # Step 2: 时间粒度检测
        time_gran = detect_time_granularity(query, entities)
        assert time_gran == 'yearly'

    def test_scenario_3_year_list_year_end(self, db_conn):
        """场景3: "2024和2025年末的总资产和总负债分析" """
        query = "华兴科技2024和2025年末的总资产和总负债分析"

        # Step 1: 实体检测
        entities = detect_entities(query, db_conn)
        assert entities['taxpayer_id'] == 'HX001'
        # 检查是否提取到年份列表
        assert entities.get('period_years') == [2024, 2025]

        # Step 2: 时间粒度检测
        time_gran = detect_time_granularity(query, entities)
        assert time_gran == 'yearly'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
