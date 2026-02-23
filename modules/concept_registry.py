"""概念注册表：跨域财务概念 → 确定性SQL映射

将常见财务概念（如"采购金额"、"销售金额"、"存货增加额"）映射到
{域, 视图, 列, 聚合方式, 计算公式}，跨域查询时绕过LLM直接生成精确SQL。
"""
import re
import sqlite3
from modules.entity_preprocessor import get_scope_view

# ── 概念注册表 ──────────────────────────────────────────────────
# 概念类型:
#   直接取值 (agg=None)  — 报表类，直接SELECT某列
#   聚合取值 (agg='SUM') — 明细类，需要GROUP BY聚合
#   计算型   (type='computed') — 多数据点 + Python公式
#
# 季度策略 (quarterly_strategy):
#   sum_months  — 汇总季度内3个月（发票、科目余额发生额）
#   quarter_end — 取季末月数据（资产负债表、现金流量表本期、利润表本期）

CONCEPT_REGISTRY = {
    # ── 发票域 ──────────────────────────────────────────────
    '采购金额': {
        'domain': 'invoice', 'view': 'vw_inv_spec_purchase',
        'column': 'amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '采购金额',
        'aliases': ['采购额', '进项金额', '采购不含税金额'],
    },
    '销售金额': {
        'domain': 'invoice', 'view': 'vw_inv_spec_sales',
        'column': 'amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '销售金额',
        'aliases': ['销售额', '销项金额', '销售不含税金额'],
    },
    '采购税额': {
        'domain': 'invoice', 'view': 'vw_inv_spec_purchase',
        'column': 'tax_amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '采购税额',
        'aliases': ['进项发票税额'],
    },
    '销售税额': {
        'domain': 'invoice', 'view': 'vw_inv_spec_sales',
        'column': 'tax_amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '销售税额',
        'aliases': ['销项发票税额'],
    },
    '采购价税合计': {
        'domain': 'invoice', 'view': 'vw_inv_spec_purchase',
        'column': 'total_amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '采购价税合计',
        'aliases': ['采购含税金额'],
    },
    '销售价税合计': {
        'domain': 'invoice', 'view': 'vw_inv_spec_sales',
        'column': 'total_amount', 'agg': 'SUM',
        'quarterly_strategy': 'sum_months',
        'label': '销售价税合计',
        'aliases': ['销售含税金额'],
    },
    # ── 增值税域 ────────────────────────────────────────────
    '销项税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'output_tax', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '销项税额',
        'aliases': ['增值税销项税', '增值税销项税额'],
    },
    '进项税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'input_tax', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '进项税额',
        'aliases': ['增值税进项税', '增值税进项税额'],
    },
    '增值税应纳税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'tax_payable', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '增值税应纳税额',
        'aliases': ['应纳增值税', '增值税税额'],
    },
    '留抵税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'end_credit', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'quarter_end',
        'label': '期末留抵税额',
        'aliases': ['期末留抵', '留抵'],
    },
    # ── 资产负债表域 ────────────────────────────────────────
    '货币资金': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'cash_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '货币资金',
        'aliases': ['现金及等价物', '货币资金期末'],
    },
    '应收账款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'accounts_receivable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应收账款',
        'aliases': ['应收账款期末', '应收款'],
    },
    '存货': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'inventory_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '存货',
        'aliases': ['存货期末', '库存'],
    },
    '固定资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'fixed_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '固定资产',
        'aliases': ['固定资产期末'],
    },
    '总资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '总资产',
        'aliases': ['资产总计', '资产合计', '资产总额'],
    },
    '总负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '总负债',
        'aliases': ['负债合计', '负债总额', '负债总计'],
    },
    '所有者权益': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'equity_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '所有者权益',
        'aliases': ['股东权益', '净资产', '权益合计', '所有者权益合计'],
    },
    '流动资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'current_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '流动资产',
        'aliases': ['流动资产合计'],
    },
    '流动负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'current_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '流动负债',
        'aliases': ['流动负债合计'],
    },
    # ── 资产负债表计算型 ────────────────────────────────────
    '存货增加额': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'type': 'computed',
        'sources': {
            'end': {'column': 'inventory_end', 'period': 'current'},
            'begin': {'column': 'inventory_end', 'period': 'previous'},
        },
        'formula': 'end - begin',
        'quarterly_strategy': 'quarter_end',
        'label': '存货增加额',
        'aliases': ['存货增加', '存货变动额', '存货变动'],
    },
    '应收账款变动额': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'type': 'computed',
        'sources': {
            'end': {'column': 'accounts_receivable_end', 'period': 'current'},
            'begin': {'column': 'accounts_receivable_end', 'period': 'previous'},
        },
        'formula': 'end - begin',
        'quarterly_strategy': 'quarter_end',
        'label': '应收账款变动额',
        'aliases': ['应收账款增加额', '应收账款变动'],
    },
    # ── 利润表域 ────────────────────────────────────────────
    '营业收入': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'operating_revenue', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '营业收入',
        'aliases': ['收入', '主营收入'],
    },
    '营业成本': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'operating_cost', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '营业成本',
        'aliases': ['成本', '主营成本'],
    },
    '营业利润': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'operating_profit', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '营业利润',
        'aliases': [],
    },
    '利润总额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'total_profit', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '利润总额',
        'aliases': ['税前利润'],
    },
    '净利润': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'net_profit', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '净利润',
        'aliases': ['税后利润'],
    },
    '所得税费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'income_tax_expense', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '所得税费用',
        'aliases': [],
    },
    '税金及附加': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'taxes_and_surcharges', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '税金及附加',
        'aliases': [],
    },
    # ── 现金流量表域 ────────────────────────────────────────
    '经营活动现金流入': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_inflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '经营活动现金流入小计',
        'aliases': ['经营现金流入', '经营活动现金流入小计'],
    },
    '经营活动现金流出': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_outflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '经营活动现金流出小计',
        'aliases': ['经营现金流出', '经营活动现金支出', '经营活动现金流出小计'],
    },
    '经营活动现金流量净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_net_cash', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '经营活动现金流量净额',
        'aliases': ['经营现金净额', '经营活动净现金', '经营现金流净额'],
    },
    '投资活动现金流入': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '投资活动现金流入小计',
        'aliases': ['投资现金流入', '投资活动现金流入小计'],
    },
    '投资活动现金流出': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_outflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '投资活动现金流出小计',
        'aliases': ['投资现金流出', '投资活动现金支出', '投资活动现金流出小计'],
    },
    '投资活动现金流量净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_net_cash', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '投资活动现金流量净额',
        'aliases': ['投资现金净额', '投资活动净现金', '投资现金流净额'],
    },
    '筹资活动现金流入': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_inflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '筹资活动现金流入小计',
        'aliases': ['筹资现金流入', '筹资活动现金流入小计'],
    },
    '筹资活动现金流出': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_outflow_subtotal', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '筹资活动现金流出小计',
        'aliases': ['筹资现金流出', '筹资活动现金支出', '筹资活动现金流出小计'],
    },
    '筹资活动现金流量净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_net_cash', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '筹资活动现金流量净额',
        'aliases': ['筹资现金净额', '筹资活动净现金', '筹资现金流净额'],
    },
    # ── 企业所得税域 ────────────────────────────────────────
    '应纳税所得额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'taxable_income', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'actual_profit',
        'label': '应纳税所得额',
        'aliases': [],
    },
    '应纳所得税额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'tax_payable', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'tax_payable',
        'label': '应纳所得税额',
        'aliases': ['应纳企业所得税'],
    },
    '实际利润额': {
        'domain': 'eit', 'view': 'vw_eit_quarter_main',
        'column': 'actual_profit', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '实际利润额',
        'aliases': [],
    },
    # ── 财务指标域 ────────────────────────────────────────
    '企业所得税税负率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '企业所得税税负率'},
        'quarterly_strategy': 'quarter_end',
        'label': '企业所得税税负率',
        'aliases': ['所得税税负率', '所得税税负'],
    },
    '增值税税负率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '增值税税负率'},
        'quarterly_strategy': 'quarter_end',
        'label': '增值税税负率',
        'aliases': ['VAT税负率', '增值税税负'],
    },
    '综合税负率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '综合税负率'},
        'quarterly_strategy': 'quarter_end',
        'label': '综合税负率',
        'aliases': ['综合税负'],
    },
}


# ── 反向别名索引（自动构建）──────────────────────────────────

def _build_alias_index():
    """从 CONCEPT_REGISTRY 构建 alias → canonical_name 映射"""
    idx = {}
    for name, defn in CONCEPT_REGISTRY.items():
        idx[name] = name  # 概念名本身也是索引
        for alias in defn.get('aliases', []):
            idx[alias] = name
    return idx

_CONCEPT_ALIASES = _build_alias_index()

# 按长度降序排列的所有概念名/别名（最长匹配优先）
_SORTED_CONCEPT_NAMES = sorted(_CONCEPT_ALIASES.keys(), key=len, reverse=True)


# ── 时间粒度检测 ────────────────────────────────────────────

_QUARTERLY_PATTERNS = re.compile(
    r'各季度?|每个?季度?|按季度?|分季度?|逐季度?|季度对比|季度趋势|季度变化'
)
_MONTHLY_PATTERNS = re.compile(
    r'各月|每个?月|按月|分月|逐月|月度对比|月度趋势|月度变化'
)
_YEARLY_PATTERNS = re.compile(
    r'各年|每年|按年|分年|逐年|年度对比|年度趋势|年度变化'
)


def detect_time_granularity(query: str, entities: dict = None) -> str:
    """从查询文本检测时间粒度。

    Returns: 'quarterly' | 'monthly' | 'yearly' | None
    """
    if _QUARTERLY_PATTERNS.search(query):
        return 'quarterly'
    if _MONTHLY_PATTERNS.search(query):
        return 'monthly'
    if _YEARLY_PATTERNS.search(query):
        return 'yearly'
    if entities:
        # 多年范围（如 period_years=[2023,2024,2025]）隐含yearly粒度
        if entities.get('period_years') and len(entities['period_years']) > 1:
            return 'yearly'
        # 单年无显式月份/季度 → yearly（"2025年销售额"）
        if (entities.get('period_year') and not entities.get('period_years')
                and not entities.get('period_quarter')
                and not re.search(r'\d{1,2}\s*月', query)):
            return 'yearly'
    return None


def resolve_concepts(query: str, entities: dict) -> list:
    """从查询文本提取匹配的概念列表（最长匹配优先，不重叠）。

    Args:
        query: 日期解析后的查询文本
        entities: detect_entities() 的输出

    Returns:
        [{'name': str, 'def': dict}, ...]  匹配到的概念列表
    """
    occupied = [False] * len(query)
    hits = []  # (start, end, canonical_name)

    for phrase in _SORTED_CONCEPT_NAMES:
        start = 0
        while True:
            idx = query.find(phrase, start)
            if idx == -1:
                break
            end = idx + len(phrase)
            if not any(occupied[idx:end]):
                canonical = _CONCEPT_ALIASES[phrase]
                # 避免同一概念重复匹配
                if not any(h[2] == canonical for h in hits):
                    hits.append((idx, end, canonical))
                    for i in range(idx, end):
                        occupied[i] = True
            start = idx + 1

    # 按出现顺序排列
    hits.sort(key=lambda x: x[0])
    return [{'name': h[2], 'def': CONCEPT_REGISTRY[h[2]]} for h in hits]


# ── 视图选择 ────────────────────────────────────────────────

def _get_view(concept_def: dict, entities: dict) -> str:
    """根据概念定义 + 纳税人类型动态选择视图（eas/sas切换）"""
    domain = concept_def['domain']
    # 发票/VAT视图不受会计准则影响，直接返回
    if domain in ('invoice', 'vat'):
        return concept_def['view']
    # EIT视图不受会计准则影响
    if domain == 'eit':
        return concept_def['view']
    # 财务指标视图不受会计准则影响
    if domain == 'financial_metrics':
        return concept_def['view']
    # 资产负债表/利润表/现金流量表：根据纳税人类型切换
    tp_type = entities.get('taxpayer_type')
    acct_std = None
    if tp_type == '小规模纳税人':
        acct_std = '小企业会计准则'
    return get_scope_view(tp_type, domain=domain, accounting_standard=acct_std) \
        or concept_def['view']


# ── SQL构建 ─────────────────────────────────────────────────

_QUARTER_END_MONTHS = (3, 6, 9, 12)


def build_concept_sql(concept_def: dict, entities: dict,
                      time_granularity: str) -> tuple:
    """根据概念定义生成确定性SQL。

    Args:
        concept_def: CONCEPT_REGISTRY 中的概念定义
        entities: detect_entities() 的输出
        time_granularity: 'quarterly' | 'monthly' | 'yearly'

    Returns:
        (sql: str, params: dict)
        对于 computed 类型返回 None（需要特殊处理）
    """
    if concept_def.get('type') == 'computed':
        return None, None

    view = _get_view(concept_def, entities)
    column = concept_def['column']
    agg = concept_def.get('agg')
    domain = concept_def['domain']
    strategy = concept_def.get('quarterly_strategy', 'quarter_end')

    # 基础WHERE条件
    where_parts = []
    params = {}
    if entities.get('taxpayer_id'):
        where_parts.append('taxpayer_id = :taxpayer_id')
        params['taxpayer_id'] = entities['taxpayer_id']

    # 多年支持
    period_years = entities.get('period_years')
    if period_years and len(period_years) > 1:
        placeholders = ', '.join(f':year_{i}' for i in range(len(period_years)))
        where_parts.append(f'period_year IN ({placeholders})')
        for i, y in enumerate(period_years):
            params[f'year_{i}'] = y
    elif entities.get('period_year'):
        where_parts.append('period_year = :year')
        params['year'] = entities['period_year']

    # 域特定过滤
    if domain == 'vat':
        item_type = concept_def.get('vat_item_type', '一般项目')
        where_parts.append("item_type = :vat_item_type")
        params['vat_item_type'] = item_type
        where_parts.append("time_range = :vat_time_range")
        params['vat_time_range'] = concept_def.get('vat_time_range', '本月')

    if domain in ('profit', 'cash_flow'):
        tr = concept_def.get('time_range', '本期')
        where_parts.append("time_range = :time_range")
        params['time_range'] = tr

    # 概念级额外过滤（如 financial_metrics 的 metric_name）
    extra_filter = concept_def.get('filter', {})
    for fk, fv in extra_filter.items():
        param_key = f'filter_{fk}'
        where_parts.append(f"{fk} = :{param_key}")
        params[param_key] = fv

    where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
    multi_year = period_years and len(period_years) > 1

    # 根据时间粒度 + 策略生成SQL
    if time_granularity == 'quarterly':
        return _build_quarterly_sql(
            view, column, agg, strategy, domain, where_clause, params,
            concept_def=concept_def, multi_year=multi_year
        )
    elif time_granularity == 'monthly':
        return _build_monthly_sql(
            view, column, agg, domain, where_clause, params,
            multi_year=multi_year
        )
    else:  # yearly
        return _build_yearly_sql(
            view, column, agg, domain, where_clause, params,
            multi_year=multi_year
        )


def _build_quarterly_sql(view, column, agg, strategy, domain, where, params,
                         concept_def=None, multi_year=False):
    """季度粒度SQL"""
    year_col = 'period_year, ' if multi_year else ''

    if domain == 'eit':
        # EIT季度查询：优先使用季度视图
        q_view = (concept_def or {}).get('quarterly_view', view)
        q_column = (concept_def or {}).get('quarterly_column', column)
        # 替换WHERE中的视图相关条件（view可能已变）
        sql = (f"SELECT {year_col}period_quarter AS quarter, {q_column} AS value "
               f"FROM {q_view} WHERE {where} "
               f"ORDER BY {year_col}period_quarter")
        return sql, params

    if domain == 'financial_metrics':
        # financial_metrics 有 period_month 列，取季末月
        sql = (f"SELECT {year_col}period_month, {column} AS value "
               f"FROM {view} WHERE {where} "
               f"AND period_month IN (3,6,9,12) "
               f"ORDER BY {year_col}period_month")
        return sql, params

    if agg and strategy == 'sum_months':
        # 聚合型：按季度汇总（发票、VAT本月数据）
        sql = (f"SELECT {year_col}((period_month-1)/3+1) AS quarter, "
               f"{agg}({column}) AS value "
               f"FROM {view} WHERE {where} "
               f"GROUP BY {year_col}((period_month-1)/3+1) ORDER BY {year_col}quarter")
        return sql, params

    # 直接取值 + quarter_end：取季末月数据
    sql = (f"SELECT {year_col}period_month, {column} AS value "
           f"FROM {view} WHERE {where} "
           f"AND period_month IN (3,6,9,12) "
           f"ORDER BY {year_col}period_month")
    return sql, params


def _build_monthly_sql(view, column, agg, domain, where, params,
                       multi_year=False):
    """月度粒度SQL"""
    year_col = 'period_year, ' if multi_year else ''

    if domain == 'eit':
        # EIT无月度数据，回退到季度
        sql = (f"SELECT {year_col}period_quarter AS quarter, {column} AS value "
               f"FROM {view} WHERE {where} "
               f"ORDER BY {year_col}period_quarter")
        return sql, params

    if agg:
        sql = (f"SELECT {year_col}period_month, {agg}({column}) AS value "
               f"FROM {view} WHERE {where} "
               f"GROUP BY {year_col}period_month ORDER BY {year_col}period_month")
    else:
        sql = (f"SELECT {year_col}period_month, {column} AS value "
               f"FROM {view} WHERE {where} "
               f"ORDER BY {year_col}period_month")
    return sql, params


def _build_yearly_sql(view, column, agg, domain, where, params,
                      multi_year=False):
    """年度粒度SQL"""
    if domain == 'eit':
        sql = (f"SELECT period_year, {column} AS value "
               f"FROM {view} WHERE {where} "
               f"ORDER BY period_year")
        return sql, params

    if agg:
        sql = (f"SELECT period_year, {agg}({column}) AS value "
               f"FROM {view} WHERE {where} "
               f"GROUP BY period_year ORDER BY period_year")
    else:
        # 报表类取12月数据（本年累计）
        sql = (f"SELECT period_year, {column} AS value "
               f"FROM {view} WHERE {where} AND period_month = 12 "
               f"ORDER BY period_year")
    return sql, params


# ── 计算型概念执行 ──────────────────────────────────────────

def execute_computed_concept(conn: sqlite3.Connection, concept_def: dict,
                             entities: dict, time_granularity: str) -> list:
    """执行计算型概念，返回 [{period_key: int, value: float}, ...]。

    计算型概念需要取多期数据，然后在Python端计算差值。
    例如"存货增加额" = 本期存货 - 上期存货。
    """
    view = _get_view(concept_def, entities)
    sources = concept_def['sources']
    formula = concept_def['formula']

    # 所有source共用同一列（当前只支持 end-begin 差值模式）
    columns = set()
    for src in sources.values():
        columns.add(src['column'])
    select_cols = ', '.join(columns)

    # 构建WHERE
    where_parts = []
    params = {}
    if entities.get('taxpayer_id'):
        where_parts.append('taxpayer_id = :taxpayer_id')
        params['taxpayer_id'] = entities['taxpayer_id']

    year = entities.get('period_year')
    if not year:
        return []

    if time_granularity == 'quarterly':
        # 取季末月 + 上年末（用于计算Q1差值）
        where_parts.append(
            "((period_year = :year AND period_month IN (3,6,9,12))"
            " OR (period_year = :prev_year AND period_month = 12))"
        )
        params['year'] = year
        params['prev_year'] = year - 1
    elif time_granularity == 'monthly':
        # 取全年 + 上年12月
        where_parts.append(
            "((period_year = :year)"
            " OR (period_year = :prev_year AND period_month = 12))"
        )
        params['year'] = year
        params['prev_year'] = year - 1
    else:  # yearly
        # 取当年12月 + 上年12月
        where_parts.append(
            "((period_year = :year AND period_month = 12)"
            " OR (period_year = :prev_year AND period_month = 12))"
        )
        params['year'] = year
        params['prev_year'] = year - 1

    where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
    sql = (f"SELECT period_year, period_month, {select_cols} "
           f"FROM {view} WHERE {where_clause} "
           f"ORDER BY period_year, period_month")

    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        print(f"    [computed] SQL执行失败: {e}")
        return []

    if not rows:
        return []

    # 按 (year, month) 索引
    data_by_period = {}
    col_name = list(columns)[0]  # 取第一个列名
    for row in rows:
        r = dict(row)
        key = (r['period_year'], r['period_month'])
        data_by_period[key] = r.get(col_name, 0) or 0

    # 计算差值
    results = []
    if time_granularity == 'quarterly':
        prev_key = (year - 1, 12)
        for qm in _QUARTER_END_MONTHS:
            cur_key = (year, qm)
            end_val = data_by_period.get(cur_key)
            begin_val = data_by_period.get(prev_key)
            if end_val is not None and begin_val is not None:
                value = _eval_formula(formula, end_val, begin_val)
                quarter = qm // 3
                results.append({'quarter': quarter, 'value': value})
            prev_key = cur_key
    elif time_granularity == 'monthly':
        prev_key = (year - 1, 12)
        for m in range(1, 13):
            cur_key = (year, m)
            end_val = data_by_period.get(cur_key)
            begin_val = data_by_period.get(prev_key)
            if end_val is not None and begin_val is not None:
                value = _eval_formula(formula, end_val, begin_val)
                results.append({'period_month': m, 'value': value})
            prev_key = cur_key
    else:  # yearly
        end_val = data_by_period.get((year, 12))
        begin_val = data_by_period.get((year - 1, 12))
        if end_val is not None and begin_val is not None:
            value = _eval_formula(formula, end_val, begin_val)
            results.append({'period_year': year, 'value': value})

    return results


def _eval_formula(formula: str, end: float, begin: float) -> float:
    """安全执行计算公式"""
    try:
        return eval(formula, {"__builtins__": {}}, {'end': end, 'begin': begin})
    except Exception:
        return None


# ── 结果合并 ────────────────────────────────────────────────

def _period_key_from_row(row: dict, time_granularity: str):
    """从SQL结果行提取统一的期间键（支持多年复合键）"""
    year = row.get('period_year')

    if time_granularity == 'quarterly':
        # 可能是 quarter 列（聚合型）或 period_month 列（quarter_end型）
        q = None
        if 'quarter' in row:
            q = row['quarter']
        else:
            pm = row.get('period_month')
            if pm:
                q = (pm - 1) // 3 + 1
            else:
                pq = row.get('period_quarter')
                if pq:
                    q = pq
        if q is None:
            return None
        return (year, q) if year else q
    elif time_granularity == 'monthly':
        m = row.get('period_month')
        if m is None:
            return None
        return (year, m) if year else m
    else:
        return row.get('period_year')


def _period_label(key, time_granularity: str) -> str:
    """期间键 → 显示标签（支持复合键）"""
    if time_granularity == 'quarterly':
        if isinstance(key, tuple):
            return f'{key[0]}Q{key[1]}'
        return f'Q{key}'
    elif time_granularity == 'monthly':
        if isinstance(key, tuple):
            return f'{key[0]}年{key[1]}月'
        return f'{key}月'
    else:
        return f'{key}年'


def merge_concept_results(concept_results: list, time_granularity: str) -> list:
    """按期间对齐各概念结果，输出统一表格行。

    Args:
        concept_results: [{'name': str, 'label': str, 'data': [row_dict, ...]}, ...]
        time_granularity: 'quarterly' | 'monthly' | 'yearly'

    Returns:
        [{'period': 'Q1', '采购金额': 123.45, '销售金额': 234.56, ...}, ...]
    """
    # 收集所有期间键
    all_keys = set()
    for cr in concept_results:
        for row in cr['data']:
            key = _period_key_from_row(row, time_granularity)
            if key is not None:
                all_keys.add(key)

    if not all_keys:
        return []

    # 按期间键索引每个概念的数据
    indexed = {}  # {concept_name: {period_key: value}}
    for cr in concept_results:
        name = cr['label']
        idx = {}
        for row in cr['data']:
            key = _period_key_from_row(row, time_granularity)
            if key is not None:
                idx[key] = row.get('value')
        indexed[name] = idx

    # 合并为统一行
    merged = []
    for key in sorted(all_keys):
        row = {'period': _period_label(key, time_granularity)}
        for cr in concept_results:
            label = cr['label']
            row[label] = indexed.get(label, {}).get(key)
        merged.append(row)

    return merged
