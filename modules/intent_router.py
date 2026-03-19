"""意图路由器：将用户查询分流到 financial_data / tax_incentive / regulation 三条路径"""
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_query_config.json"

# 路由正确性依赖的关键配置 key
_REQUIRED_CONFIG_KEYS = [
    "incentive_keywords",
    "financial_db_priority_keywords",
    "financial_tax_type_keywords",
    "knowledge_base_priority_keywords",
    "exclude_from_incentive",
]


class IntentRouter:
    def __init__(self, config_path: str = None):
        self._config_path = config_path or str(_CONFIG_PATH)
        self._config = None
        self._config_mtime = 0
        self._taxpayer_names = None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def classify(self, question: str, db_conn=None) -> str:
        """返回 'financial_data' | 'tax_incentive' | 'regulation'"""
        cfg = self._load_config()

        # Layer -2: 财务数据优先 — 数据类关键词 + 税种/财务术语同时出现
        db_kws = cfg.get("financial_db_priority_keywords", [])
        tax_kws = cfg.get("financial_tax_type_keywords", [])
        if any(k in question for k in db_kws) and any(k in question for k in tax_kws):
            return "financial_data"

        # Layer -1: 知识库优先 — 流程/操作类关键词
        kb_kws = cfg.get("knowledge_base_priority_keywords", [])
        if any(k in question for k in kb_kws):
            return "regulation"

        # 提前加载优惠关键词（Layer 0 需要用来做政策意图检查）
        incentive_kws = cfg.get("incentive_keywords", [])
        exclude_kws = cfg.get("exclude_from_incentive", [])
        extra_incentive = cfg.get("extra_incentive_keywords", [])
        regulation_pass_kws = cfg.get("regulation_passthrough_keywords", [])
        has_exclude = any(k in question for k in exclude_kws)

        # 提前加载类别/实体路由关键词（Layer 0 和 Layer 1.5/1.6 共用）
        routing_cat_kws = cfg.get("routing_category_keywords",
                                  cfg.get("category_keywords", []))
        routing_ent_kws = cfg.get("routing_entity_keywords", [])
        policy_patterns = cfg.get("policy_query_patterns", [])

        # Layer 0: 企业数据查询 — 纳税人名称匹配（含模糊前缀）或 时间+金额模式
        if db_conn is not None:
            names = self._get_taxpayer_names(db_conn)
            matched = False
            for n in names:
                if n in question:
                    matched = True
                    break
                # 模糊前缀匹配（与 entity_preprocessor 一致）
                for length in range(len(n), 1, -1):
                    if n[:length] in question and length >= 2:
                        matched = True
                        break
                if matched:
                    break
            if matched:
                # 检查是否同时含优惠/政策/法规关键词 → 不拦截，让后续Layer处理
                all_incentive_kws = incentive_kws + extra_incentive
                has_incentive = not has_exclude and any(k in question for k in all_incentive_kws)
                has_regulation = any(k in question for k in regulation_pass_kws)
                # Layer 0 扩展：类别/实体 + 政策模式 也应放行
                has_policy_intent = (
                    (any(k in question for k in routing_cat_kws)
                     or any(k in question for k in routing_ent_kws))
                    and any(p in question for p in policy_patterns)
                )
                has_category_alone = any(k in question for k in routing_cat_kws)
                if has_incentive or has_regulation or has_policy_intent or has_category_alone:
                    pass  # 不返回financial_data，继续到Layer 1 / 1.5 / 1.6
                else:
                    return "financial_data"
        if re.search(r'\d{4}年.*多少', question):
            return "financial_data"

        # Layer 1: 税收优惠 — 优惠关键词（排除 exclude 列表）
        # incentive_kws, exclude_kws, has_exclude 已在 Layer 0 前加载
        if not has_exclude and any(k in question for k in incentive_kws):
            return "tax_incentive"
        # 加计扣除等复合关键词单独检查
        if not has_exclude and any(k in question for k in extra_incentive):
            return "tax_incentive"

        # Layer 1.5: 政策类别/实体 + 政策查询模式 → tax_incentive
        # 捕获 "节能环保政策有哪些"、"高新技术有什么优惠" 等查询
        has_cat_or_ent = (
            any(k in question for k in routing_cat_kws)
            or any(k in question for k in routing_ent_kws)
        )
        has_policy_pattern = any(p in question for p in policy_patterns)
        if has_cat_or_ent and has_policy_pattern:
            return "tax_incentive"

        # Layer 1.6: 纯类别关键词 → tax_incentive
        # "改善民生"、"节能环保" 等类别词本身就暗示税收优惠语境
        if not has_exclude and any(k in question for k in routing_cat_kws):
            return "tax_incentive"

        # Default → regulation
        return "regulation"

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        """热更新：检查文件 mtime，变化时重新加载；解析失败保留上次有效配置"""
        try:
            mtime = os.path.getmtime(self._config_path)
        except OSError:
            mtime = 0
        if self._config is None or mtime != self._config_mtime:
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                # 验证关键 key
                missing = [k for k in _REQUIRED_CONFIG_KEYS if not new_config.get(k)]
                if missing:
                    logger.warning("[IntentRouter] 配置缺少关键字段: %s", missing)
                self._config = new_config
                self._config_mtime = mtime
            except json.JSONDecodeError as e:
                logger.error("[IntentRouter] JSON解析失败: %s — %s", self._config_path, e)
                if self._config is not None:
                    logger.warning("[IntentRouter] 保留上次有效配置")
                else:
                    logger.error("[IntentRouter] 无历史有效配置，使用空配置（路由将不准确）")
                    self._config = {}
                self._config_mtime = mtime
            except Exception as e:
                logger.error("[IntentRouter] 配置加载异常: %s", e)
                if self._config is None:
                    self._config = {}
                self._config_mtime = mtime
        return self._config

    def _get_taxpayer_names(self, db_conn: sqlite3.Connection) -> list:
        """从 entity_preprocessor 复用纳税人缓存，返回名称列表"""
        if self._taxpayer_names is None:
            try:
                from modules.entity_preprocessor import _load_taxpayer_cache
                rows = _load_taxpayer_cache(db_conn)
                self._taxpayer_names = [r[1] for r in rows]  # taxpayer_name
            except Exception:
                self._taxpayer_names = []
        return self._taxpayer_names

    def reload_config(self) -> dict:
        """
        强制重新加载配置文件

        Returns:
            {
                'success': bool,
                'config_path': str,
                'config_version': str,
                'loaded_at': str,
                'message': str
            }
        """
        import datetime

        try:
            # 强制重新加载配置
            with open(self._config_path, "r", encoding="utf-8") as f:
                new_config = json.load(f)

            # 验证关键 key
            missing = [k for k in _REQUIRED_CONFIG_KEYS if not new_config.get(k)]
            if missing:
                logger.warning("[IntentRouter] reload: 配置缺少关键字段: %s", missing)

            self._config = new_config

            # 更新 mtime
            self._config_mtime = os.path.getmtime(self._config_path)

            # 清空纳税人名称缓存（如果配置影响纳税人数据）
            self._taxpayer_names = None

            # 生成配置版本标识（使用文件修改时间）
            config_version = datetime.datetime.fromtimestamp(self._config_mtime).strftime('%Y%m%d_%H%M%S')

            return {
                'success': True,
                'config_path': self._config_path,
                'config_version': config_version,
                'loaded_at': datetime.datetime.now().isoformat(),
                'message': f'成功重载配置文件: {os.path.basename(self._config_path)}'
            }

        except Exception as e:
            return {
                'success': False,
                'config_path': self._config_path,
                'config_version': None,
                'loaded_at': datetime.datetime.now().isoformat(),
                'message': f'配置重载失败: {str(e)}'
            }
