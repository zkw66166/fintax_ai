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
    # ── 利润表补充 ────────────────────────────────────────────
    '管理费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'administrative_expense', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '管理费用',
        'aliases': ['管理费'],
    },
    '销售费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'selling_expense', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '销售费用',
        'aliases': ['销售费'],
    },
    '财务费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'financial_expense', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '财务费用',
        'aliases': [],
    },
    '研发费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'rd_expense', 'agg': None,
        'time_range': '本期',
        'quarterly_strategy': 'quarter_end',
        'label': '研发费用',
        'aliases': ['研发支出'],
    },
    # ── 资产负债表补充 ────────────────────────────────────────
    '应付账款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'accounts_payable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应付账款',
        'aliases': ['应付账款期末', '应付款'],
    },
    '预收款项': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'advances_from_customers_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '预收款项',
        'aliases': ['预收账款'],
    },
    '未分配利润': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'retained_earnings_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '未分配利润',
        'aliases': ['留存收益'],
    },
    # ── 增值税补充 ────────────────────────────────────────────
    '进项税额转出': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'input_tax_transfer_out', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '进项税额转出',
        'aliases': ['进项转出'],
    },
    # ── 利润表 CAS 共有项补充 ─────────────────────────────────
    '营业外收入': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'non_operating_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '营业外收入',
        'aliases': ['非经营收入', '营业外收益'],
    },
    '营业外支出': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'non_operating_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '营业外支出',
        'aliases': ['非经营支出', '非营业支出'],
    },
    '利息费用': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'interest_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '利息费用',
        'aliases': ['利息支出', '借款利息'],
    },
    '利息收入': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'interest_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '利息收入',
        'aliases': ['存款利息', '利息所得'],
    },
    '投资收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'investment_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '投资收益',
        'aliases': ['投资回报', '投资所得', '理财收益'],
    },
    '其他收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'other_gains', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '其他收益',
        'aliases': ['其他利得'],
    },
    '公允价值变动收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'fair_value_change_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '公允价值变动收益',
        'aliases': ['公允价变动收益', '市价变动收益'],
    },
    '信用减值损失': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'credit_impairment_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '信用减值损失',
        'aliases': ['信用损失'],
    },
    '资产减值损失': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'asset_impairment_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '资产减值损失',
        'aliases': ['资产减值', '资产跌价损失'],
    },
    '资产处置收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'asset_disposal_gains', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '资产处置收益',
        'aliases': ['处置资产收益', '资产出售收益'],
    },
    '综合收益总额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'comprehensive_income_total', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '综合收益总额',
        'aliases': ['综合收益合计', '总综合收益'],
    },
    '持续经营净利润': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'continued_ops_net_profit', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '持续经营净利润',
        'aliases': ['持续经营净利'],
    },
    '终止经营净利润': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'discontinued_ops_net_profit', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '终止经营净利润',
        'aliases': ['终止经营净利'],
    },
    '其他综合收益的税后净额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'other_comprehensive_income_net', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '其他综合收益的税后净额',
        'aliases': ['其他综合收益净额'],
    },
    '基本每股收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'eps_basic', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '基本每股收益',
        'aliases': ['基本EPS', '每股基本收益'],
    },
    '稀释每股收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'eps_diluted', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '稀释每股收益',
        'aliases': ['稀释EPS', '每股稀释收益'],
    },
    '净敞口套期收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'net_exposure_hedge_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '净敞口套期收益',
        'aliases': ['套期收益', '敞口套期收益'],
    },
    # ── 利润表 CAS 专有项 ──────────────────────────────────────
    '以摊余成本计量的金融资产终止确认收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'amortized_cost_termination_income', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '以摊余成本计量的金融资产终止确认收益',
        'aliases': ['金融资产终止确认收益', '摊余成本资产终止收益'],
    },
    '对联营企业和合营企业的投资收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'investment_income_associates', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '对联营企业和合营企业的投资收益',
        'aliases': ['联营合营企业投资收益', '联营企业投资收益'],
    },
    '不能重分类进损益的其他综合收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_not_reclassifiable', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '不能重分类进损益的其他综合收益',
        'aliases': ['不可重分类其他综合收益'],
    },
    '将重分类进损益的其他综合收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_reclassifiable', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '将重分类进损益的其他综合收益',
        'aliases': ['可重分类其他综合收益'],
    },
    '重新计量设定受益计划变动额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_remeasurement_pension', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '重新计量设定受益计划变动额',
        'aliases': ['设定受益计划变动额'],
    },
    '权益法下不能转损益的其他综合收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_equity_method_nonreclassifiable', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '权益法下不能转损益的其他综合收益',
        'aliases': [],
    },
    '其他权益工具投资公允价值变动': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_equity_investment_fv_change', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '其他权益工具投资公允价值变动',
        'aliases': ['权益工具投资公允价变动'],
    },
    '企业自身信用风险公允价值变动': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_credit_risk_change', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '企业自身信用风险公允价值变动',
        'aliases': ['信用风险公允价值变动'],
    },
    '权益法下可转损益的其他综合收益': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_equity_method_reclassifiable', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '权益法下可转损益的其他综合收益',
        'aliases': [],
    },
    '其他债权投资公允价值变动': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_debt_investment_fv_change', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '其他债权投资公允价值变动',
        'aliases': ['债权投资公允价变动'],
    },
    '金融资产重分类计入其他综合收益的金额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_reclassify_to_pnl', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '金融资产重分类计入其他综合收益的金额',
        'aliases': ['资产重分类综合收益'],
    },
    '其他债权投资信用减值准备': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_debt_impairment', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '其他债权投资信用减值准备',
        'aliases': ['债权投资减值准备'],
    },
    '现金流量套期储备': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_cash_flow_hedge', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '现金流量套期储备',
        'aliases': ['现金流套期储备'],
    },
    '外币财务报表折算差额': {
        'domain': 'profit', 'view': 'vw_profit_eas',
        'column': 'oci_foreign_currency_translation', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '外币财务报表折算差额',
        'aliases': ['外币折算差额'],
    },
    # ── 利润表 SAS 独有项 ────────────────────────────────────
    '消费税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'consumption_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '消费税', 'aliases': ['消费税金'],
    },
    '营业税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'business_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '营业税', 'aliases': ['营业税金'],
    },
    '城市维护建设税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'city_maintenance_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '城市维护建设税', 'aliases': ['城建税'],
    },
    '资源税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'resource_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '资源税', 'aliases': ['资源税金'],
    },
    '土地增值税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'land_appreciation_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '土地增值税', 'aliases': ['土增税'],
    },
    '城镇土地使用税房产税车船税印花税': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'property_related_taxes', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '城镇土地使用税房产税车船税印花税',
        'aliases': ['小税种合计', '财产税及其他税'],
    },
    '教育费附加': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'education_surcharge', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '教育费附加', 'aliases': ['教育附加费'],
    },
    '商品维修费': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'goods_repair_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '商品维修费', 'aliases': ['产品维修费', '维修费'],
    },
    '广告费和业务宣传费': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'advertising_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '广告费和业务宣传费',
        'aliases': ['广告宣传费', '广告费', '宣传费'],
    },
    '开办费': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'organization_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '开办费', 'aliases': ['筹备费', '设立费'],
    },
    '业务招待费': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'business_entertainment_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '业务招待费', 'aliases': ['招待费', '交际费'],
    },
    '研究费用': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'research_expense', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '研究费用', 'aliases': ['研究费'],
    },
    '利息费用净额': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'interest_expense_net', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '利息费用净额', 'aliases': [],
    },
    '政府补助': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'government_grant', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '政府补助', 'aliases': ['政府补贴', '财政补助'],
    },
    '坏账损失': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'bad_debt_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '坏账损失', 'aliases': ['坏账费用'],
    },
    '无法收回的长期债券投资损失': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'long_term_bond_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '无法收回的长期债券投资损失',
        'aliases': ['长期债券投资损失'],
    },
    '无法收回的长期股权投资损失': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'long_term_equity_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '无法收回的长期股权投资损失',
        'aliases': ['长期股权投资损失'],
    },
    '自然灾害等不可抗力因素造成的损失': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'force_majeure_loss', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '自然灾害等不可抗力因素造成的损失',
        'aliases': ['不可抗力损失', '自然灾害损失'],
    },
    '税收滞纳金': {
        'domain': 'profit', 'view': 'vw_profit_sas',
        'column': 'tax_late_payment', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '税收滞纳金', 'aliases': ['滞纳金', '税务滞纳金'],
    },
    # ── 资产负债表补充（资产类）─────────────────────────────────
    '交易性金融资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'trading_financial_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '交易性金融资产', 'aliases': [],
    },
    '衍生金融资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'derivative_financial_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '衍生金融资产', 'aliases': [],
    },
    '应收票据': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'notes_receivable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应收票据', 'aliases': ['应收票据期末'],
    },
    '应收账款融资': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'accounts_receivable_financing_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应收账款融资', 'aliases': [],
    },
    '预付账款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'prepayments_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '预付账款', 'aliases': ['预付款项'],
    },
    '其他应收款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_receivables_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他应收款', 'aliases': [],
    },
    '合同资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'contract_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '合同资产', 'aliases': [],
    },
    '持有待售资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'held_for_sale_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '持有待售资产', 'aliases': [],
    },
    '一年内到期的非流动资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'current_portion_non_current_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '一年内到期的非流动资产', 'aliases': [],
    },
    '其他流动资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_current_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他流动资产', 'aliases': [],
    },
    '非流动资产合计': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'non_current_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '非流动资产合计', 'aliases': ['非流动资产'],
    },
    '债权投资': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'debt_investments_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '债权投资', 'aliases': [],
    },
    '其他债权投资': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_debt_investments_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他债权投资', 'aliases': [],
    },
    '长期应收款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'long_term_receivables_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '长期应收款', 'aliases': [],
    },
    '长期股权投资': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'long_term_equity_investments_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '长期股权投资', 'aliases': [],
    },
    '其他权益工具投资': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_equity_instruments_invest_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他权益工具投资', 'aliases': [],
    },
    '其他非流动金融资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_non_current_financial_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他非流动金融资产', 'aliases': [],
    },
    '投资性房地产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'investment_property_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '投资性房地产', 'aliases': [],
    },
    '在建工程': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'construction_in_progress_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '在建工程', 'aliases': [],
    },
    '生产性生物资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'productive_biological_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '生产性生物资产', 'aliases': [],
    },
    '油气资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'oil_and_gas_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '油气资产', 'aliases': [],
    },
    '使用权资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'right_of_use_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '使用权资产', 'aliases': [],
    },
    '无形资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'intangible_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '无形资产', 'aliases': [],
    },
    '开发支出': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'development_expenditure_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '开发支出', 'aliases': [],
    },
    '商誉': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'goodwill_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '商誉', 'aliases': [],
    },
    '长期待摊费用': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'long_term_deferred_expenses_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '长期待摊费用', 'aliases': [],
    },
    '递延所得税资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'deferred_tax_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '递延所得税资产', 'aliases': [],
    },
    '其他非流动资产': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_non_current_assets_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他非流动资产', 'aliases': [],
    },
    # ── 资产负债表补充（负债类）─────────────────────────────────
    '短期借款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'short_term_loans_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '短期借款', 'aliases': [],
    },
    '交易性金融负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'trading_financial_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '交易性金融负债', 'aliases': [],
    },
    '衍生金融负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'derivative_financial_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '衍生金融负债', 'aliases': [],
    },
    '应付票据': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'notes_payable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应付票据', 'aliases': [],
    },
    '合同负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'contract_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '合同负债', 'aliases': [],
    },
    '应付职工薪酬': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'employee_benefits_payable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应付职工薪酬', 'aliases': [],
    },
    '应交税费': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'taxes_payable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应交税费', 'aliases': [],
    },
    '其他应付款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_payables_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他应付款', 'aliases': [],
    },
    '持有待售负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'held_for_sale_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '持有待售负债', 'aliases': [],
    },
    '一年内到期的非流动负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'current_portion_non_current_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '一年内到期的非流动负债', 'aliases': [],
    },
    '其他流动负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_current_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他流动负债', 'aliases': [],
    },
    '长期借款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'long_term_loans_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '长期借款', 'aliases': [],
    },
    '应付债券': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'bonds_payable_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应付债券', 'aliases': [],
    },
    '租赁负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'lease_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '租赁负债', 'aliases': [],
    },
    '长期应付款': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'long_term_payables_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '长期应付款', 'aliases': [],
    },
    '预计负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'provisions_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '预计负债', 'aliases': [],
    },
    '递延收益': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'deferred_income_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '递延收益', 'aliases': [],
    },
    '递延所得税负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'deferred_tax_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '递延所得税负债', 'aliases': [],
    },
    '其他非流动负债': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'other_non_current_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '其他非流动负债', 'aliases': [],
    },
    '非流动负债合计': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'non_current_liabilities_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '非流动负债合计', 'aliases': ['非流动负债'],
    },
    # ── 资产负债表补充（权益类）─────────────────────────────────
    '实收资本': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'share_capital_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '实收资本', 'aliases': ['股本'],
    },
    '资本公积': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'capital_reserve_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '资本公积', 'aliases': [],
    },
    '库存股': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'treasury_stock_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '库存股', 'aliases': [],
    },
    '专项储备': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'special_reserve_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '专项储备', 'aliases': [],
    },
    '盈余公积': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'surplus_reserve_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '盈余公积', 'aliases': [],
    },
    '负债和所有者权益总计': {
        'domain': 'balance_sheet', 'view': 'vw_balance_sheet_eas',
        'column': 'liabilities_and_equity_end', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '负债和所有者权益总计', 'aliases': [],
    },
    # ── 现金流量表明细项补充 ────────────────────────────────────
    '销售商品提供劳务收到的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_inflow_sales', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '销售商品提供劳务收到的现金',
        'aliases': ['销售商品收到的现金', '经营收到的现金'],
    },
    '收到的税费返还': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_inflow_tax_refund', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '收到的税费返还', 'aliases': ['税费返还'],
    },
    '收到其他与经营活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_inflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '收到其他与经营活动有关的现金',
        'aliases': ['经营活动其他现金流入'],
    },
    '购买商品接受劳务支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_outflow_purchase', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '购买商品接受劳务支付的现金',
        'aliases': ['购买商品支付的现金'],
    },
    '支付给职工以及为职工支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_outflow_labor', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '支付给职工以及为职工支付的现金',
        'aliases': ['支付给职工的现金', '职工薪酬现金'],
    },
    '支付的各项税费': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_outflow_tax', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '支付的各项税费', 'aliases': [],
    },
    '支付其他与经营活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'operating_outflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '支付其他与经营活动有关的现金',
        'aliases': ['经营活动其他现金流出'],
    },
    '收回投资收到的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_sale_investment', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '收回投资收到的现金', 'aliases': [],
    },
    '取得投资收益收到的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_returns', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '取得投资收益收到的现金', 'aliases': ['投资收益现金'],
    },
    '处置固定资产收回的现金净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_disposal_assets', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '处置固定资产收回的现金净额',
        'aliases': ['处置固定资产收回的现金'],
    },
    '处置子公司收到的现金净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_disposal_subsidiary', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '处置子公司收到的现金净额',
        'aliases': ['处置子公司收到的现金'],
    },
    '收到其他与投资活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_inflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '收到其他与投资活动有关的现金',
        'aliases': ['投资活动其他现金流入'],
    },
    '投资支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_outflow_purchase_investment', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '投资支付的现金', 'aliases': [],
    },
    '购建固定资产支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_outflow_purchase_assets', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '购建固定资产支付的现金', 'aliases': [],
    },
    '取得子公司支付的现金净额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_outflow_acquire_subsidiary', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '取得子公司支付的现金净额', 'aliases': [],
    },
    '支付其他与投资活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'investing_outflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '支付其他与投资活动有关的现金',
        'aliases': ['投资活动其他现金流出'],
    },
    '吸收投资收到的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_inflow_capital', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '吸收投资收到的现金', 'aliases': [],
    },
    '取得借款收到的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_inflow_borrowing', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '取得借款收到的现金', 'aliases': ['借款收到的现金'],
    },
    '收到其他与筹资活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_inflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '收到其他与筹资活动有关的现金',
        'aliases': ['筹资活动其他现金流入'],
    },
    '偿还债务支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_outflow_debt_repayment', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '偿还债务支付的现金', 'aliases': [],
    },
    '分配股利利润或偿付利息支付的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_outflow_dividend_interest', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '分配股利利润或偿付利息支付的现金',
        'aliases': ['分配股利支付的现金'],
    },
    '支付其他与筹资活动有关的现金': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'financing_outflow_other', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '支付其他与筹资活动有关的现金',
        'aliases': ['筹资活动其他现金流出'],
    },
    '现金及现金等价物净增加额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'net_increase_cash', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '现金及现金等价物净增加额',
        'aliases': ['现金净增加额', '现金流净额'],
    },
    '期初现金及现金等价物余额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'beginning_cash', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '期初现金及现金等价物余额',
        'aliases': ['期初现金', '期初现金余额'],
    },
    '期末现金及现金等价物余额': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'ending_cash', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '期末现金及现金等价物余额',
        'aliases': ['期末现金', '期末现金余额'],
    },
    '汇率变动对现金的影响': {
        'domain': 'cash_flow', 'view': 'vw_cash_flow_eas',
        'column': 'fx_impact', 'agg': None,
        'time_range': '本期', 'quarterly_strategy': 'quarter_end',
        'label': '汇率变动对现金的影响', 'aliases': ['汇率变动影响'],
    },
    # ── 增值税补充（一般纳税人）─────────────────────────────────
    '应税货物销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_goods', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '应税货物销售额', 'aliases': ['货物销售额'],
    },
    '应税劳务销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_services', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '应税劳务销售额', 'aliases': ['劳务销售额'],
    },
    '一般计税销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_taxable_rate', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '一般计税销售额', 'aliases': ['按适用税率计税销售额'],
    },
    '纳税检查调整销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_adjustment_check', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '纳税检查调整销售额', 'aliases': [],
    },
    '简易计税销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_simple_method', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '简易计税销售额', 'aliases': ['简易办法销售额'],
    },
    '免抵退办法出口销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_export_credit_refund', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '免抵退办法出口销售额', 'aliases': ['出口销售额'],
    },
    '免税销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_tax_free', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '免税销售额', 'aliases': [],
    },
    '免税货物销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_tax_free_goods', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '免税货物销售额', 'aliases': [],
    },
    '免税劳务销售额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'sales_tax_free_services', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '免税劳务销售额', 'aliases': [],
    },
    '上期留抵税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'last_period_credit', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'quarter_end',
        'label': '上期留抵税额', 'aliases': ['上期留抵'],
    },
    '免抵退应退税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'export_refund', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '免抵退应退税额', 'aliases': ['出口退税额'],
    },
    '纳税检查应补缴税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'tax_check_supplement', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '纳税检查应补缴税额', 'aliases': [],
    },
    '应抵扣税额合计': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'deductible_total', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '应抵扣税额合计', 'aliases': [],
    },
    '实际抵扣税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'actual_deduct', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '实际抵扣税额', 'aliases': [],
    },
    '简易计税应纳税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'simple_tax', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '简易计税应纳税额', 'aliases': ['简易办法应纳税额'],
    },
    '减免税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'tax_reduction', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '减免税额', 'aliases': ['税额减免'],
    },
    '应纳税额合计': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'total_tax_payable', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '应纳税额合计', 'aliases': [],
    },
    '期初未缴税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'unpaid_begin', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'quarter_end',
        'label': '期初未缴税额', 'aliases': [],
    },
    '本期已缴税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'paid_current', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '本期已缴税额', 'aliases': [],
    },
    '期末未缴税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'unpaid_end', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'quarter_end',
        'label': '期末未缴税额', 'aliases': [],
    },
    '欠缴税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'arrears', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'quarter_end',
        'label': '欠缴税额', 'aliases': [],
    },
    '即征即退': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'immediate_refund', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '即征即退', 'aliases': ['即征即退税额'],
    },
    '增值税城建税': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'city_maintenance_tax', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '增值税城建税', 'aliases': [],
    },
    '增值税教育费附加': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'education_surcharge', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '增值税教育费附加', 'aliases': [],
    },
    '地方教育附加': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'local_education_surcharge', 'agg': None,
        'vat_item_type': '一般项目', 'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '地方教育附加', 'aliases': ['地方教育费附加'],
    },
    # ── 企业所得税补充（年报）─────────────────────────────────
    '纳税调整增加额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'add_tax_adjust_increase', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '纳税调整增加额', 'aliases': ['纳税调增'],
    },
    '纳税调整减少额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'less_tax_adjust_decrease', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '纳税调整减少额', 'aliases': ['纳税调减'],
    },
    '免税收入减免所得额合计': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'exempt_income_deduction_total', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '免税收入减免所得额合计', 'aliases': ['免税减免合计'],
    },
    '弥补以前年度亏损': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'less_losses_carried_forward', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'less_losses_carried_forward',
        'label': '弥补以前年度亏损', 'aliases': ['弥补亏损'],
    },
    '所得减免': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'less_income_exemption', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '所得减免', 'aliases': [],
    },
    '所得税税率': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'tax_rate', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'tax_rate',
        'label': '所得税税率', 'aliases': ['企业所得税税率'],
    },
    '减免税额合计': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'tax_credit_total', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'tax_credit_total',
        'label': '减免税额合计', 'aliases': ['税收优惠减免'],
    },
    '实际应纳所得税额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'actual_tax_payable', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'tax_payable',
        'label': '实际应纳所得税额',
        'aliases': ['实际缴纳的企业所得税额', '实际缴纳所得税额', '实际缴纳企业所得税', '实际应纳税额'],
    },
    '已预缴税额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'less_prepaid_tax', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'less_prepaid_tax_current_year',
        'label': '已预缴税额', 'aliases': ['预缴税额'],
    },
    '应补退税额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'tax_payable_or_refund', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '应补退税额', 'aliases': ['应补税额', '应退税额'],
    },
    '境外所得': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'less_foreign_income', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '境外所得', 'aliases': [],
    },
    # ── 企业所得税补充（季报独有）─────────────────────────────
    '特定业务计算的应纳税所得额': {
        'domain': 'eit', 'view': 'vw_eit_quarter_main',
        'column': 'add_specific_business_taxable_income', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '特定业务计算的应纳税所得额', 'aliases': ['特定业务应纳税所得额'],
    },
    '不征税收入': {
        'domain': 'eit', 'view': 'vw_eit_quarter_main',
        'column': 'less_non_taxable_income', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '不征税收入', 'aliases': [],
    },
    '本期应补退所得税额': {
        'domain': 'eit', 'view': 'vw_eit_quarter_main',
        'column': 'current_tax_payable_or_refund', 'agg': None,
        'quarterly_strategy': 'quarter_end',
        'label': '本期应补退所得税额', 'aliases': ['本期应补退税额'],
    },
    # ── 财务指标补充 ──────────────────────────────────────────
    '毛利率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '毛利率'},
        'quarterly_strategy': 'quarter_end',
        'label': '毛利率', 'aliases': ['销售毛利率'],
    },
    '净利率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '净利率'},
        'quarterly_strategy': 'quarter_end',
        'label': '净利率', 'aliases': ['净利润率', '销售净利率', '利润率'],
    },
    '净资产收益率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '净资产收益率(ROE)'},
        'quarterly_strategy': 'quarter_end',
        'label': '净资产收益率', 'aliases': ['ROE'],
    },
    '净利润增长率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '净利润增长率'},
        'quarterly_strategy': 'quarter_end',
        'label': '净利润增长率', 'aliases': ['利润增长率'],
    },
    '资产负债率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '资产负债率'},
        'quarterly_strategy': 'quarter_end',
        'label': '资产负债率', 'aliases': [],
    },
    '流动比率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '流动比率'},
        'quarterly_strategy': 'quarter_end',
        'label': '流动比率', 'aliases': [],
    },
    '速动比率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '速动比率'},
        'quarterly_strategy': 'quarter_end',
        'label': '速动比率', 'aliases': [],
    },
    '现金债务保障比率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '现金债务保障比率'},
        'quarterly_strategy': 'quarter_end',
        'label': '现金债务保障比率', 'aliases': [],
    },
    '总资产周转率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '总资产周转率'},
        'quarterly_strategy': 'quarter_end',
        'label': '总资产周转率', 'aliases': [],
    },
    '应收账款周转率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '应收账款周转率'},
        'quarterly_strategy': 'quarter_end',
        'label': '应收账款周转率', 'aliases': [],
    },
    '存货周转率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '存货周转率'},
        'quarterly_strategy': 'quarter_end',
        'label': '存货周转率', 'aliases': [],
    },
    '应收款周转天数': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '应收款周转天数'},
        'quarterly_strategy': 'quarter_end',
        'label': '应收款周转天数', 'aliases': ['应收账款周转天数'],
    },
    '营业收入增长率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '营业收入增长率'},
        'quarterly_strategy': 'quarter_end',
        'label': '营业收入增长率', 'aliases': ['收入增长率'],
    },
    '资产增长率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '资产增长率'},
        'quarterly_strategy': 'quarter_end',
        'label': '资产增长率', 'aliases': ['总资产增长率'],
    },
    '销售费用率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '销售费用率'},
        'quarterly_strategy': 'quarter_end',
        'label': '销售费用率', 'aliases': [],
    },
    '管理费用率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '管理费用率'},
        'quarterly_strategy': 'quarter_end',
        'label': '管理费用率', 'aliases': [],
    },
    '销售收现比': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '销售收现比'},
        'quarterly_strategy': 'quarter_end',
        'label': '销售收现比', 'aliases': [],
    },
    '销项进项配比率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '销项进项配比率'},
        'quarterly_strategy': 'quarter_end',
        'label': '销项进项配比率', 'aliases': [],
    },
    '进项税额转出占比': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '进项税额转出占比'},
        'quarterly_strategy': 'quarter_end',
        'label': '进项税额转出占比', 'aliases': [],
    },
    '应税所得率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '应税所得率'},
        'quarterly_strategy': 'quarter_end',
        'label': '应税所得率', 'aliases': [],
    },
    '发票开具异常率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '发票开具异常率'},
        'quarterly_strategy': 'quarter_end',
        'label': '发票开具异常率', 'aliases': [],
    },
    '零申报率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '零申报率'},
        'quarterly_strategy': 'quarter_end',
        'label': '零申报率', 'aliases': [],
    },

    # ── 跨域计算指标（新增）──────────────────────────────────────
    # 注意：这些指标实际上已经在 vw_financial_metrics 表中计算好了
    # 这里注册为概念是为了支持别名匹配和概念管线优化
    '所得税税负率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '企业所得税税负率'},
        'quarterly_strategy': 'quarter_end',
        'label': '所得税税负率',
        'aliases': ['EIT税负率', '企业所得税税负率', '企业所得税负担率'],
    },

    '增值税税负率': {
        'domain': 'financial_metrics', 'view': 'vw_financial_metrics',
        'column': 'metric_value', 'agg': None,
        'filter': {'metric_name': '增值税税负率'},
        'quarterly_strategy': 'quarter_end',
        'label': '增值税税负率',
        'aliases': ['VAT税负率', '增值税负担率'],
    },

    '增值税纳税额': {
        'domain': 'vat', 'view': 'vw_vat_return_general',
        'column': 'tax_payable', 'agg': None,
        'vat_item_type': '一般项目',
        'vat_time_range': '本月',
        'quarterly_strategy': 'sum_months',
        'label': '增值税纳税额',
        'aliases': ['增值税应纳税额', '实际缴纳的增值税', '增值税税额', 'VAT纳税额', 'VAT应纳税额'],
    },

    '企业所得税纳税额': {
        'domain': 'eit', 'view': 'vw_eit_annual_main',
        'column': 'actual_tax_payable', 'agg': None,
        'quarterly_view': 'vw_eit_quarter_main',
        'quarterly_column': 'tax_payable',
        'quarterly_strategy': 'quarter_end',
        'label': '企业所得税纳税额',
        'aliases': ['企业所得税应纳税额', '实际缴纳的企业所得税', '实际缴纳的企业所得税额', '所得税纳税额', 'EIT纳税额'],
    },
}


def build_single_point_sql(concept_def: dict, entities: dict) -> tuple:
    """为单概念单期间查询生成确定性SQL（无时间粒度，直接取值）。

    Returns:
        (sql: str, params: dict) 或 (None, None) 如果无法构建
    """
    if concept_def.get('type') == 'computed':
        return None, None

    view = _get_view(concept_def, entities)
    column = concept_def['column']
    agg = concept_def.get('agg')
    domain = concept_def['domain']

    where_parts = []
    params = {}
    if entities.get('taxpayer_id'):
        where_parts.append('taxpayer_id = :taxpayer_id')
        params['taxpayer_id'] = entities['taxpayer_id']

    if entities.get('period_year'):
        where_parts.append('period_year = :year')
        params['year'] = entities['period_year']

    if domain == 'vat':
        item_type = concept_def.get('vat_item_type', '一般项目')
        where_parts.append("item_type = :vat_item_type")
        params['vat_item_type'] = item_type
        where_parts.append("time_range = :vat_time_range")
        params['vat_time_range'] = concept_def.get('vat_time_range', '本月')
        if entities.get('period_month'):
            where_parts.append('period_month = :month')
            params['month'] = entities['period_month']

    elif domain in ('profit', 'cash_flow'):
        tr = concept_def.get('time_range', '本期')
        where_parts.append("time_range = :time_range")
        params['time_range'] = tr
        if entities.get('period_month'):
            where_parts.append('period_month = :month')
            params['month'] = entities['period_month']

    elif domain == 'balance_sheet':
        if entities.get('period_month'):
            where_parts.append('period_month = :month')
            params['month'] = entities['period_month']

    elif domain == 'eit':
        if entities.get('period_quarter'):
            where_parts.append('period_quarter = :quarter')
            params['quarter'] = entities['period_quarter']

    elif domain == 'financial_metrics':
        extra_filter = concept_def.get('filter', {})
        for fk, fv in extra_filter.items():
            param_key = f'filter_{fk}'
            where_parts.append(f"{fk} = :{param_key}")
            params[param_key] = fv
        if entities.get('period_month'):
            where_parts.append('period_month = :month')
            params['month'] = entities['period_month']

    elif domain == 'invoice':
        if entities.get('period_month'):
            where_parts.append('period_month = :month')
            params['month'] = entities['period_month']

    where_clause = ' AND '.join(where_parts) if where_parts else '1=1'

    if agg:
        sql = (f"SELECT {agg}({column}) AS value "
               f"FROM {view} WHERE {where_clause}")
    else:
        sql = (f"SELECT {column} AS value "
               f"FROM {view} WHERE {where_clause} LIMIT 1")

    return sql, params


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
        # 指定了具体季度（如 Q4）→ quarterly（单季度查询也视为季度粒度）
        if entities.get('period_quarter'):
            return 'quarterly'
        # 单年无显式月份/季度 → yearly（"2025年销售额"）
        if (entities.get('period_year') and not entities.get('period_years')
                and not entities.get('period_quarter')
                and not re.search(r'\d{1,2}\s*月', query)):
            return 'yearly'
    return None


def _resolve_concepts_internal(query: str):
    """核心概念匹配逻辑（最长匹配优先，不重叠）。

    Returns:
        (hits, occupied)
        hits: [(start, end, canonical_name), ...]  按出现顺序排列
        occupied: [bool, ...]  每个字符是否已被概念匹配占用
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
                if not any(h[2] == canonical for h in hits):
                    hits.append((idx, end, canonical))
                    for i in range(idx, end):
                        occupied[i] = True
            start = idx + 1

    hits.sort(key=lambda x: x[0])
    return hits, occupied


def resolve_concepts(query: str, entities: dict) -> list:
    """从查询文本提取匹配的概念列表（最长匹配优先，不重叠）。

    Args:
        query: 日期解析后的查询文本
        entities: detect_entities() 的输出

    Returns:
        [{'name': str, 'def': dict}, ...]  匹配到的概念列表
    """
    hits, _ = _resolve_concepts_internal(query)
    return [{'name': h[2], 'def': CONCEPT_REGISTRY[h[2]]} for h in hits]


# ── 未匹配项提取 ──────────────────────────────────────────────

_REMAINDER_NOISE = {'分析', '查询', '情况', '数据', '多少', '趋势', '变化',
                    '对比', '比较', '的', '和', '与', '及', '以及', '还有',
                    '怎么样', '如何', '是多少', '各', '每',
                    '各季度', '各月', '各月份', '每季度', '每月', '每月份',
                    '各年', '每年', '年度', '季度', '月份', '月度',
                    '上半年', '下半年', '全年',
                    '汇总', '合计', '总计', '明细', '详情', '列表',
                    '年末', '年初', '期末', '期初', '月末', '月初',
                    '比较年末', '对比年末', '比较期末', '对比期末'}
_DATE_PREFIX_RE = re.compile(
    r'^\d{4}年?'
    r'(?:Q\d|第?[一二三四1-4]季度?)?'
    r'(?:\d{1,2}月?\s*[到至\-]\s*\d{1,2}月?|\d{0,2}[月年度])?'
)


def resolve_concepts_with_remainder(query: str, entities: dict) -> tuple:
    """提取匹配概念 + 未匹配的查询项。

    Returns:
        (concepts, unmatched_items)
        concepts: [{'name': str, 'def': dict}, ...]
        unmatched_items: [str, ...]  未被任何概念匹配的有效查询项
    """
    hits, occupied = _resolve_concepts_internal(query)
    concepts = [{'name': h[2], 'def': CONCEPT_REGISTRY[h[2]]} for h in hits]

    if not hits:
        return concepts, []

    # 提取未占用的连续文本段
    segments = []
    i = 0
    while i < len(query):
        if not occupied[i]:
            j = i
            while j < len(query) and not occupied[j]:
                j += 1
            seg = query[i:j].strip()
            if seg:
                segments.append(seg)
            i = j
        else:
            i += 1

    # 合并后按分隔符拆分为独立项
    raw_text = '、'.join(segments)
    parts = re.split(r'[、，,\s]+', raw_text)

    unmatched = []
    tp_name = entities.get('taxpayer_name', '') if entities else ''
    for part in parts:
        part = part.strip('的和与及')
        # 先去除纳税人名称残留（在日期前缀之前，因为名称可能在日期前面）
        # 支持短名匹配：用户输入"华兴科技"但taxpayer_name是"华兴科技有限公司"
        if tp_name and (part == tp_name or tp_name in part):
            part = part.replace(tp_name, '').strip()
        elif tp_name and len(part) >= 3 and part in tp_name:
            part = ''
        elif tp_name and len(tp_name) >= 4:
            # 尝试去除公司名前缀（短名+日期粘连，如"华兴科技2024年度"）
            for plen in range(len(tp_name), 2, -1):
                prefix = tp_name[:plen]
                if part.startswith(prefix):
                    part = part[plen:].strip()
                    break
        # 去除日期前缀
        part = _DATE_PREFIX_RE.sub('', part).strip()
        if len(part) >= 2 and part not in _REMAINDER_NOISE:
            unmatched.append(part)

    return concepts, unmatched


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
    if domain == 'eit' and entities.get('period_quarter'):
        where_parts.append('period_quarter = :quarter')
        params['quarter'] = entities['period_quarter']

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
