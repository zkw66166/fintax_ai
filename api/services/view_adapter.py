"""视图适配器 - 支持跨纳税人类型的 SQL 适配（域感知）

⚠️ DEPRECATED (2026-03-08): 此模块已废弃，不再使用。

原因：
- 会计准则差异：企业会计准则 vs 小企业会计准则有20%列结构不同
- VAT差异：一般纳税人 vs 小规模纳税人列结构完全不同
- 智能适配只能替换视图名称，无法处理列结构差异

新策略：
- 财务报表：每个查询2个模板（按会计准则区分）
- VAT：每个查询2个模板（按纳税人类型区分）
- EIT：每个查询1个模板（无类型/准则区分）
- 跨域：每个查询4个模板（保守策略）

保留此文件仅用于向后兼容，避免破坏性修改。

注意：
- 财务报表视图按会计准则适配（企业会计准则 ↔ 小企业会计准则）
- VAT视图因列结构差异过大，不支持自动适配
- EIT视图无需适配（不区分纳税人类型或会计准则）
"""
import re
from typing import Optional, Dict, Tuple

# ---------- 财务报表视图映射（按会计准则，与纳税人类型无关） ----------
FINANCIAL_STATEMENT_VIEWS = {
    "企业会计准则": {
        "vw_balance_sheet_eas": "vw_balance_sheet_eas",
        "vw_balance_sheet_sas": "vw_balance_sheet_eas",
        "vw_profit_eas": "vw_profit_eas",
        "vw_profit_sas": "vw_profit_eas",
        "vw_cash_flow_eas": "vw_cash_flow_eas",
        "vw_cash_flow_sas": "vw_cash_flow_eas"
    },
    "小企业会计准则": {
        "vw_balance_sheet_eas": "vw_balance_sheet_sas",
        "vw_balance_sheet_sas": "vw_balance_sheet_sas",
        "vw_profit_eas": "vw_profit_sas",
        "vw_profit_sas": "vw_profit_sas",
        "vw_cash_flow_eas": "vw_cash_flow_sas",
        "vw_cash_flow_sas": "vw_cash_flow_sas"
    }
}

# ---------- 旧版视图映射表（保留向后兼容） ----------
# 注意：仅包含财务报表视图，不包含VAT视图
VIEW_MAPPING = {
    ("一般纳税人", "企业会计准则"): {
        "vw_balance_sheet_eas": "vw_balance_sheet_eas",
        "vw_balance_sheet_sas": "vw_balance_sheet_eas",
        "vw_profit_eas": "vw_profit_eas",
        "vw_profit_sas": "vw_profit_eas",
        "vw_cash_flow_eas": "vw_cash_flow_eas",
        "vw_cash_flow_sas": "vw_cash_flow_eas"
    },
    ("小规模纳税人", "小企业会计准则"): {
        "vw_balance_sheet_eas": "vw_balance_sheet_sas",
        "vw_balance_sheet_sas": "vw_balance_sheet_sas",
        "vw_profit_eas": "vw_profit_sas",
        "vw_profit_sas": "vw_profit_sas",
        "vw_cash_flow_eas": "vw_cash_flow_sas",
        "vw_cash_flow_sas": "vw_cash_flow_sas"
    }
}


def _replace_views_in_sql(sql_template: str, view_map: Dict[str, str]) -> Optional[str]:
    """将 SQL 模板中的视图名称替换为目标视图

    Args:
        sql_template: 源 SQL 模板
        view_map: 源视图→目标视图映射

    Returns:
        替换后的 SQL，如果无任何替换则返回 None
    """
    adapted = sql_template
    for from_view, to_view in view_map.items():
        if from_view in adapted and from_view != to_view:
            pattern = rf"\b{re.escape(from_view)}\b"
            adapted = re.sub(pattern, to_view, adapted, flags=re.IGNORECASE)

    if adapted == sql_template:
        return None
    return adapted


def adapt_sql_for_financial_statement(sql_template: str, from_standard: str,
                                       to_standard: str) -> Optional[str]:
    """将财务报表 SQL 从一种会计准则适配到另一种

    仅适配视图名称（_eas ↔ _sas），不修改列名。

    Args:
        sql_template: 源 SQL 模板
        from_standard: 源会计准则 (企业会计准则/小企业会计准则)
        to_standard: 目标会计准则 (企业会计准则/小企业会计准则)

    Returns:
        适配后的 SQL，如果无法适配则返回 None
    """
    if from_standard == to_standard:
        return None

    from_views = FINANCIAL_STATEMENT_VIEWS.get(from_standard)
    to_views = FINANCIAL_STATEMENT_VIEWS.get(to_standard)
    if not from_views or not to_views:
        return None

    # 构建从源视图到目标视图的映射
    # 先找出 SQL 中实际使用的源视图，然后映射到目标
    view_map = {}
    for src_view in from_views.values():
        # 对于源会计准则的每个规范视图，找到目标会计准则对应的视图
        # src_view 是 from_standard 下的规范视图（如 vw_profit_eas）
        # 我们需要找到 to_standard 下对应的视图（如 vw_profit_sas）
        if src_view in sql_template:
            target_view = to_views.get(src_view, src_view)
            if target_view != src_view:
                view_map[src_view] = target_view

    if not view_map:
        return None

    return _replace_views_in_sql(sql_template, view_map)


def adapt_sql_for_type(sql_template: str, from_type: str, to_type: str,
                        from_standard: str, to_standard: str) -> Optional[str]:
    """将 SQL 模板从一种类型适配到另一种类型（旧版接口，保留向后兼容）

    Args:
        sql_template: 源 SQL 模板
        from_type: 源纳税人类型 (一般纳税人/小规模纳税人)
        to_type: 目标纳税人类型 (一般纳税人/小规模纳税人)
        from_standard: 源会计准则 (企业会计准则/小企业会计准则)
        to_standard: 目标会计准则 (企业会计准则/小企业会计准则)

    Returns:
        适配后的 SQL，如果无法适配则返回 None

    Note:
        推荐使用 adapt_sql_for_financial_statement() 替代此函数。
        仅支持财务报表视图的适配（资产负债表、利润表、现金流量表）
        VAT视图因列结构差异过大，不支持自动适配
    """
    # 优先尝试新版域感知适配
    if from_standard != to_standard:
        result = adapt_sql_for_financial_statement(sql_template, from_standard, to_standard)
        if result:
            return result

    # 旧版逻辑保底
    from_key = (from_type, from_standard)
    to_key = (to_type, to_standard)

    if from_key not in VIEW_MAPPING or to_key not in VIEW_MAPPING:
        return None

    from_views = VIEW_MAPPING[from_key]
    to_views = VIEW_MAPPING[to_key]

    adapted_sql = sql_template

    # 替换所有视图名称
    for from_view, canonical_view in from_views.items():
        to_view = to_views.get(from_view)
        if to_view and from_view in adapted_sql:
            # 使用单词边界确保完整匹配
            pattern = rf"\b{re.escape(from_view)}\b"
            adapted_sql = re.sub(pattern, to_view, adapted_sql, flags=re.IGNORECASE)

    # 验证是否有实际替换
    if adapted_sql == sql_template:
        return None

    return adapted_sql
