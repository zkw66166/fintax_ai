"""意图路由器：将用户查询分流到 financial_data / tax_incentive / regulation 三条路径"""
import json
import os
import re
import sqlite3
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tax_query_config.json"


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
        extra_incentive = ["加计扣除", "即征即退"]
        has_exclude = any(k in question for k in exclude_kws)

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
                # 检查是否同时含优惠/政策关键词 → 不拦截，让Layer 1处理
                all_incentive_kws = incentive_kws + extra_incentive
                if not has_exclude and any(k in question for k in all_incentive_kws):
                    pass  # 不返回financial_data，继续到Layer 1
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

        # Default → regulation
        return "regulation"

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        """热更新：检查文件 mtime，变化时重新加载"""
        try:
            mtime = os.path.getmtime(self._config_path)
        except OSError:
            mtime = 0
        if self._config is None or mtime != self._config_mtime:
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
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
