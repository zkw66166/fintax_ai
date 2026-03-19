"""意图路由器修复验证测试

测试 Layer 0 放行扩展、Layer 1.5/1.6 新增路由、配置防御性增强。
"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "tax_query_config.json"


def _make_mock_db_conn(names=None):
    """创建模拟 db_conn，返回指定纳税人名称列表"""
    if names is None:
        names = ["华兴科技", "鑫源贸易", "创智软件", "大华智能制造", "TSE科技", "环球机械"]
    conn = MagicMock(spec=sqlite3.Connection)
    # mock _load_taxpayer_cache 返回 (taxpayer_id, taxpayer_name, ...) 元组
    rows = [(f"ID{i}", n, "一般纳税人", "企业会计准则") for i, n in enumerate(names)]
    return conn, rows


class TestIntentRouterFix(unittest.TestCase):
    """验证路由修复后的正确性"""

    def setUp(self):
        from modules.intent_router import IntentRouter
        self.router = IntentRouter()
        # 预加载有效配置
        self.router._load_config()

    def _classify_with_names(self, question, names=None):
        """带纳税人名称模拟的 classify"""
        conn, rows = _make_mock_db_conn(names)
        with patch("modules.entity_preprocessor._load_taxpayer_cache", return_value=rows):
            # 清除缓存以使 mock 生效
            self.router._taxpayer_names = None
            return self.router.classify(question, db_conn=conn)

    # ---- 核心修复验证 ----

    def test_01_company_prefix_policy_query(self):
        """华兴科技 改善民生政策有哪些 → tax_incentive（非 financial_data）"""
        result = self._classify_with_names("华兴科技 改善民生政策有哪些")
        self.assertEqual(result, "tax_incentive",
                         "公司名前缀 + 政策类别查询应路由到 tax_incentive")

    def test_02_category_keyword_with_pattern(self):
        """节能环保政策有哪些 → tax_incentive"""
        result = self._classify_with_names("节能环保政策有哪些")
        self.assertEqual(result, "tax_incentive",
                         "类别关键词 + 政策模式应路由到 tax_incentive")

    def test_03_entity_keyword_with_pattern(self):
        """高新技术有什么优惠 → tax_incentive"""
        result = self._classify_with_names("高新技术有什么优惠")
        self.assertEqual(result, "tax_incentive",
                         "实体关键词 + 政策模式应路由到 tax_incentive")

    # ---- 既有路由不受影响 ----

    def test_04_layer1_preserved(self):
        """增值税减免 → tax_incentive（Layer 1 不变）"""
        result = self._classify_with_names("增值税减免")
        self.assertEqual(result, "tax_incentive")

    def test_05_layer_neg2_preserved(self):
        """增值税多少 → financial_data（Layer -2 不变）"""
        result = self._classify_with_names("增值税多少")
        self.assertEqual(result, "financial_data")

    def test_06_layer_neg1_preserved(self):
        """申报流程 → regulation（Layer -1 不变）"""
        result = self._classify_with_names("增值税申报流程")
        self.assertEqual(result, "regulation")

    def test_07_layer0_normal_financial(self):
        """华兴科技2025年1月增值税 → financial_data（Layer 0 正常财务查询不变）"""
        result = self._classify_with_names("华兴科技2025年1月增值税")
        self.assertEqual(result, "financial_data")

    # ---- Layer 1.6 类别词单独触发 ----

    def test_08_category_alone(self):
        """改善民生 → tax_incentive（Layer 1.6 类别词）"""
        result = self._classify_with_names("改善民生")
        self.assertEqual(result, "tax_incentive")

    def test_09_entity_alone_no_trigger(self):
        """高新技术 → 不应误路由到 financial_data"""
        result = self._classify_with_names("高新技术")
        # 实体词单独出现不触发 tax_incentive（太模糊），应走 default
        self.assertNotEqual(result, "financial_data",
                            "实体词单独出现不应路由到 financial_data")

    # ---- 配置防御性 ----

    def test_10_config_fallback_on_json_error(self):
        """JSON 损坏时保留上次有效配置"""
        from modules.intent_router import IntentRouter
        router = IntentRouter()
        # 先加载有效配置
        valid_cfg = router._load_config()
        self.assertTrue(len(valid_cfg.get("incentive_keywords", [])) > 0,
                        "有效配置应包含 incentive_keywords")

        # 模拟 JSON 损坏
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8") as f:
            f.write('{"broken": true')  # 无效 JSON
            bad_path = f.name

        try:
            router._config_path = bad_path
            router._config_mtime = 0  # 强制重新加载
            cfg = router._load_config()
            # 应保留上次有效配置，不是空 dict
            self.assertTrue(len(cfg.get("incentive_keywords", [])) > 0,
                            "JSON 损坏时应保留上次有效配置")
        finally:
            os.unlink(bad_path)

    # ---- 更多同类查询验证 ----

    def test_11_support_sannong(self):
        """支持三农政策有哪些 → tax_incentive"""
        result = self._classify_with_names("支持三农政策有哪些")
        self.assertEqual(result, "tax_incentive")

    def test_12_promote_regional_development(self):
        """促进区域发展有哪些优惠 → tax_incentive"""
        result = self._classify_with_names("促进区域发展有哪些优惠")
        self.assertEqual(result, "tax_incentive")

    def test_13_company_prefix_entity_pattern(self):
        """TSE科技 可以享受什么高新技术优惠 → tax_incentive"""
        result = self._classify_with_names("TSE科技 可以享受什么高新技术优惠")
        self.assertEqual(result, "tax_incentive")


class TestJsonConfigValid(unittest.TestCase):
    """验证 JSON 配置文件语法正确"""

    def test_config_parseable(self):
        """tax_query_config.json 应能正常解析"""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIsInstance(cfg, dict)

    def test_required_keys_present(self):
        """关键配置项应存在且非空"""
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        required = [
            "incentive_keywords", "financial_db_priority_keywords",
            "financial_tax_type_keywords", "knowledge_base_priority_keywords",
            "exclude_from_incentive", "category_keywords",
            "extra_incentive_keywords", "routing_entity_keywords",
            "policy_query_patterns",
        ]
        for key in required:
            self.assertTrue(len(cfg.get(key, [])) > 0,
                            f"配置项 {key} 应存在且非空")


if __name__ == "__main__":
    unittest.main()
