"""Data browser API: tables, periods, data (general + raw format)."""
import calendar
import sqlite3
from fastapi import APIRouter, Depends, Query
from api.auth import get_current_user, require_company_access
from config.settings import DB_PATH

router = APIRouter(prefix="/data-browser", tags=["data-browser"])

# Domain → browsable config
BROWSE_DOMAINS = [
    {"key": "profit", "label": "利润表", "eav_table": "fs_income_statement_item", "dict_table": "fs_income_statement_item_dict", "views": {"CAS": "vw_profit_eas", "SAS": "vw_profit_sas"}, "raw_cols": ("current_amount", "cumulative_amount"), "raw_labels": ("本期金额", "本年累计金额")},
    {"key": "balance_sheet", "label": "资产负债表", "eav_table": "fs_balance_sheet_item", "dict_table": "fs_balance_sheet_item_dict", "views": {"ASBE": "vw_balance_sheet_eas", "ASSE": "vw_balance_sheet_sas"}, "raw_cols": ("beginning_balance", "ending_balance"), "raw_labels": ("年初余额", "期末余额")},
    {"key": "cash_flow", "label": "现金流量表", "eav_table": "fs_cash_flow_item", "dict_table": "fs_cash_flow_item_dict", "views": {"CAS": "vw_cash_flow_eas", "SAS": "vw_cash_flow_sas"}, "raw_cols": ("current_amount", "cumulative_amount"), "raw_labels": ("本期金额", "本年累计金额")},
    {"key": "vat", "label": "增值税申报表", "eav_table": None, "views": {"一般纳税人": "vw_vat_return_general", "小规模纳税人": "vw_vat_return_small"}},
    {"key": "eit_annual", "label": "企业所得税年报", "eav_table": None, "views": {"_default": "vw_eit_annual_main"}},
    {"key": "eit_quarter", "label": "企业所得税季报", "eav_table": None, "views": {"_default": "vw_eit_quarter_main"}},
    {"key": "account_balance", "label": "科目余额表", "eav_table": None, "views": {"_default": "vw_account_balance"}},
    {"key": "purchase_invoice", "label": "采购发票", "eav_table": None, "views": {"_default": "vw_inv_spec_purchase"}},
    {"key": "sales_invoice", "label": "销售发票", "eav_table": None, "views": {"_default": "vw_inv_spec_sales"}},
    {"key": "financial_metrics", "label": "财务指标", "eav_table": None, "views": {"_default": "vw_financial_metrics"}},
]

# Comprehensive Column Chinese Name Dictionary
_COLUMN_CHINESE_NAMES = {
    # 公共字段
    "taxpayer_id": "纳税人识别号",
    "taxpayer_name": "纳税人名称",
    "period_year": "年度",
    "period_month": "月份",
    "period_quarter": "季度",
    "taxpayer_type": "纳税人类型",
    "filing_id": "申报编号",
    "item_type": "项目类型",
    
    # 科目余额表 (vw_account_balance)
    "account_code": "科目代码",
    "account_name": "科目名称",
    "level": "科目级次",
    "category": "科目类别",
    "balance_direction": "余额方向",
    "is_gaap": "是否企业会计准则",
    "is_small": "是否小企业会计准则",
    "opening_balance": "期初余额",
    "debit_amount": "借方发生额",
    "credit_amount": "贷方发生额",
    "closing_balance": "期末余额",

    # 利润表 (vw_profit_eas / vw_profit_sas)
    "operating_revenue": "营业收入",
    "operating_cost": "营业成本",
    "taxes_and_surcharges": "税金及附加",
    "selling_expense": "销售费用",
    "administrative_expense": "管理费用",
    "rd_expense": "研发费用",
    "financial_expense": "财务费用",
    "interest_expense": "其中：利息费用",
    "interest_income": "利息收入",
    "other_gains": "其他收益",
    "investment_income": "投资收益",
    "investment_income_associates": "其中：对联营企业和合营企业的投资收益",
    "amortized_cost_termination_income": "以摊余成本计量的金融资产终止确认收益",
    "net_exposure_hedge_income": "净敞口套期收益",
    "fair_value_change_income": "公允价值变动收益",
    "credit_impairment_loss": "信用减值损失",
    "asset_impairment_loss": "资产减值损失",
    "asset_disposal_gains": "资产处置收益",
    "operating_profit": "营业利润",
    "non_operating_income": "营业外收入",
    "non_operating_expense": "营业外支出",
    "total_profit": "利润总额",
    "income_tax_expense": "所得税费用",
    "net_profit": "净利润",
    "continued_ops_net_profit": "持续经营净利润",
    "discontinued_ops_net_profit": "终止经营净利润",
    "other_comprehensive_income_net": "其他综合收益的税后净额",
    "oci_not_reclassifiable": "不能重分类进损益的净额",
    "oci_reclassifiable": "将重分类进损益的净额",
    "comprehensive_income_total": "综合收益总额",
    "eps_basic": "基本每股收益",
    "eps_diluted": "稀释每股收益",
    "oci_remeasurement_pension": "重新计量设定受益计划变动",
    "oci_equity_method_nonreclassifiable": "权益法下不能重分类进损益的份额",
    "oci_equity_investment_fv_change": "其他权益工具投资公允价值变动",
    "oci_credit_risk_change": "自身信用风险公允价值变动",
    "oci_equity_method_reclassifiable": "权益法下以后将重分类进损益的份额",
    "oci_debt_investment_fv_change": "其他债权投资公允价值变动",
    "oci_reclassify_to_pnl": "可供出售金融资产公允价值变动损益",
    "oci_debt_impairment": "持有至到期投资重分类为可供出售金融资产损益",
    "oci_cash_flow_hedge": "现金流量套期损益的有效部分",
    "oci_foreign_currency_translation": "外币财务报表折算差额",

    # 资产负债表 (vw_balance_sheet_eas / vw_balance_sheet_sas)
    "cash_begin": "货币资金(年初)",
    "cash_end": "货币资金(期末)",
    "trading_financial_assets_begin": "交易性金融资产(年初)",
    "trading_financial_assets_end": "交易性金融资产(期末)",
    "derivative_financial_assets_begin": "衍生金融资产(年初)",
    "derivative_financial_assets_end": "衍生金融资产(期末)",
    "notes_receivable_begin": "应收票据(年初)",
    "notes_receivable_end": "应收票据(期末)",
    "accounts_receivable_begin": "应收账款(年初)",
    "accounts_receivable_end": "应收账款(期末)",
    "accounts_receivable_financing_begin": "应收款项融资(年初)",
    "accounts_receivable_financing_end": "应收款项融资(期末)",
    "prepayments_begin": "预付款项(年初)",
    "prepayments_end": "预付款项(期末)",
    "other_receivables_begin": "其他应收款(年初)",
    "other_receivables_end": "其他应收款(期末)",
    "inventory_begin": "存货(年初)",
    "inventory_end": "存货(期末)",
    "contract_assets_begin": "合同资产(年初)",
    "contract_assets_end": "合同资产(期末)",
    "held_for_sale_assets_begin": "持有待售资产(年初)",
    "held_for_sale_assets_end": "持有待售资产(期末)",
    "current_portion_non_current_assets_begin": "一年内到期的非流动资产(年初)",
    "current_portion_non_current_assets_end": "一年内到期的非流动资产(期末)",
    "other_current_assets_begin": "其他流动资产(年初)",
    "other_current_assets_end": "其他流动资产(期末)",
    "current_assets_begin": "流动资产合计(年初)",
    "current_assets_end": "流动资产合计(期末)",
    "debt_investments_begin": "债权投资(年初)",
    "debt_investments_end": "债权投资(期末)",
    "other_debt_investments_begin": "其他债权投资(年初)",
    "other_debt_investments_end": "其他债权投资(期末)",
    "long_term_receivables_begin": "长期应收款(年初)",
    "long_term_receivables_end": "长期应收款(期末)",
    "long_term_equity_investments_begin": "长期股权投资(年初)",
    "long_term_equity_investments_end": "长期股权投资(期末)",
    "other_equity_instruments_invest_begin": "其他权益工具投资(年初)",
    "other_equity_instruments_invest_end": "其他权益工具投资(期末)",
    "other_non_current_financial_assets_begin": "其他非流动金融资产(年初)",
    "other_non_current_financial_assets_end": "其他非流动金融资产(期末)",
    "investment_property_begin": "投资性房地产(年初)",
    "investment_property_end": "投资性房地产(期末)",
    "fixed_assets_begin": "固定资产(年初)",
    "fixed_assets_end": "固定资产(期末)",
    "construction_in_progress_begin": "在建工程(年初)",
    "construction_in_progress_end": "在建工程(期末)",
    "productive_biological_assets_begin": "生产性生物资产(年初)",
    "productive_biological_assets_end": "生产性生物资产(期末)",
    "oil_and_gas_assets_begin": "油气资产(年初)",
    "oil_and_gas_assets_end": "油气资产(期末)",
    "right_of_use_assets_begin": "使用权资产(年初)",
    "right_of_use_assets_end": "使用权资产(期末)",
    "intangible_assets_begin": "无形资产(年初)",
    "intangible_assets_end": "无形资产(期末)",
    "development_expenditure_begin": "开发支出(年初)",
    "development_expenditure_end": "开发支出(期末)",
    "goodwill_begin": "商誉(年初)",
    "goodwill_end": "商誉(期末)",
    "long_term_deferred_expenses_begin": "长期待摊费用(年初)",
    "long_term_deferred_expenses_end": "长期待摊费用(期末)",
    "deferred_tax_assets_begin": "递延所得税资产(年初)",
    "deferred_tax_assets_end": "递延所得税资产(期末)",
    "other_non_current_assets_begin": "其他非流动资产(年初)",
    "other_non_current_assets_end": "其他非流动资产(期末)",
    "non_current_assets_begin": "非流动资产合计(年初)",
    "non_current_assets_end": "非流动资产合计(期末)",
    "assets_begin": "资产总计(年初)",
    "assets_end": "资产总计(期末)",
    "short_term_loans_begin": "短期借款(年初)",
    "short_term_loans_end": "短期借款(期末)",
    "trading_financial_liabilities_begin": "交易性金融负债(年初)",
    "trading_financial_liabilities_end": "交易性金融负债(期末)",
    "derivative_financial_liabilities_begin": "衍生金融负债(年初)",
    "derivative_financial_liabilities_end": "衍生金融负债(期末)",
    "notes_payable_begin": "应付票据(年初)",
    "notes_payable_end": "应付票据(期末)",
    "accounts_payable_begin": "应付账款(年初)",
    "accounts_payable_end": "应付账款(期末)",
    "advances_from_customers_begin": "预收款项(年初)",
    "advances_from_customers_end": "预收款项(期末)",
    "contract_liabilities_begin": "合同负债(年初)",
    "contract_liabilities_end": "合同负债(期末)",
    "employee_benefits_payable_begin": "应付职工薪酬(年初)",
    "employee_benefits_payable_end": "应付职工薪酬(期末)",
    "taxes_payable_begin": "应交税费(年初)",
    "taxes_payable_end": "应交税费(期末)",
    "other_payables_begin": "其他应付款(年初)",
    "other_payables_end": "其他应付款(期末)",
    "held_for_sale_liabilities_begin": "持有待售负债(年初)",
    "held_for_sale_liabilities_end": "持有待售负债(期末)",
    "current_portion_non_current_liabilities_begin": "一年内到期的非流动负债(年初)",
    "current_portion_non_current_liabilities_end": "一年内到期的非流动负债(期末)",
    "other_current_liabilities_begin": "其他流动负债(年初)",
    "other_current_liabilities_end": "其他流动负债(期末)",
    "current_liabilities_begin": "流动负债合计(年初)",
    "current_liabilities_end": "流动负债合计(期末)",
    "long_term_loans_begin": "长期借款(年初)",
    "long_term_loans_end": "长期借款(期末)",
    "bonds_payable_begin": "应付债券(年初)",
    "bonds_payable_end": "应付债券(期末)",
    "lease_liabilities_begin": "租赁负债(年初)",
    "lease_liabilities_end": "租赁负债(期末)",
    "long_term_payables_begin": "长期应付款(年初)",
    "long_term_payables_end": "长期应付款(期末)",
    "provisions_begin": "预计负债(年初)",
    "provisions_end": "预计负债(期末)",
    "deferred_income_begin": "递延收益(年初)",
    "deferred_income_end": "递延收益(期末)",
    "deferred_tax_liabilities_begin": "递延所得税负债(年初)",
    "deferred_tax_liabilities_end": "递延所得税负债(期末)",
    "other_non_current_liabilities_begin": "其他非流动负债(年初)",
    "other_non_current_liabilities_end": "其他非流动负债(期末)",
    "non_current_liabilities_begin": "非流动负债合计(年初)",
    "non_current_liabilities_end": "非流动负债合计(期末)",
    "liabilities_begin": "负债合计(年初)",
    "liabilities_end": "负债合计(期末)",
    "share_capital_begin": "实收资本(年初)",
    "share_capital_end": "实收资本(期末)",
    "capital_reserve_begin": "资本公积(年初)",
    "capital_reserve_end": "资本公积(期末)",
    "treasury_stock_begin": "减：库存股(年初)",
    "treasury_stock_end": "减：库存股(期末)",
    "other_comprehensive_income_begin": "其他综合收益(年初)",
    "other_comprehensive_income_end": "其他综合收益(期末)",
    "special_reserve_begin": "专项储备(年初)",
    "special_reserve_end": "专项储备(期末)",
    "surplus_reserve_begin": "盈余公积(年初)",
    "surplus_reserve_end": "盈余公积(期末)",
    "retained_earnings_begin": "未分配利润(年初)",
    "retained_earnings_end": "未分配利润(期末)",
    "equity_begin": "所有者权益合计(年初)",
    "equity_end": "所有者权益合计(期末)",
    "liabilities_and_equity_begin": "负债和所有者权益总计(年初)",
    "liabilities_and_equity_end": "负债和所有者权益总计(期末)",

    # 现金流量表 (vw_cash_flow_eas / vw_cash_flow_sas)
    "operating_inflow_sales": "销售商品、提供劳务收到的现金",
    "operating_inflow_tax_refund": "收到的税费返还",
    "operating_inflow_other": "经营活动收到的其他现金",
    "operating_inflow_subtotal": "经营活动现金流入小计",
    "operating_outflow_purchase": "购买商品、接受劳务支付的现金",
    "operating_outflow_labor": "支付给职工为职工支付的现金",
    "operating_outflow_tax": "支付的各项税费",
    "operating_outflow_other": "经营活动支付的其他现金",
    "operating_outflow_subtotal": "经营活动现金流出小计",
    "operating_net_cash": "经营活动现金流量净额",
    "investing_inflow_sale_investment": "收回投资收到的现金",
    "investing_inflow_returns": "取得投资收益收到的现金",
    "investing_inflow_disposal_assets": "处置固定资产等收回的现金净额",
    "investing_inflow_disposal_subsidiary": "处置子公司等收到的现金净额",
    "investing_inflow_other": "投资活动收到的其他现金",
    "investing_inflow_subtotal": "投资活动现金流入小计",
    "investing_outflow_purchase_assets": "购建固定资产等支付的现金",
    "investing_outflow_purchase_investment": "投资支付的现金",
    "investing_outflow_acquire_subsidiary": "取得子公司等支付的现金净额",
    "investing_outflow_other": "投资活动支付的其他现金",
    "investing_outflow_subtotal": "投资活动现金流出小计",
    "investing_net_cash": "投资活动现金流量净额",
    "financing_inflow_capital": "吸收投资收到的现金",
    "financing_inflow_borrowing": "取得借款收到的现金",
    "financing_inflow_other": "筹资活动收到的其他现金",
    "financing_inflow_subtotal": "筹资活动现金流入小计",
    "financing_outflow_debt_repayment": "偿还债务支付的现金",
    "financing_outflow_dividend_interest": "分配股利利润或付息支付现金",
    "financing_outflow_other": "筹资活动支付的其他现金",
    "financing_outflow_subtotal": "筹资活动现金流出小计",
    "financing_net_cash": "筹资活动现金流量净额",
    "fx_impact": "汇率变动对现金的影响",
    "net_increase_cash": "现金及等价物净增加额",
    "beginning_cash": "期初现金及等价物余额",
    "ending_cash": "期末现金及等价物余额",

    # 发票 (vw_inv_spec_purchase 等)
    "invoice_format": "发票格式",
    "invoice_pk": "发票主键",
    "line_no": "明细序号",
    "invoice_code": "发票代码",
    "invoice_number": "发票号码",
    "digital_invoice_no": "全电发票号码",
    "seller_tax_id": "销方税号",
    "seller_name": "销方名称",
    "buyer_tax_id": "购方税号",
    "buyer_name": "购方名称",
    "invoice_date": "开票日期",
    "tax_category_code": "税收分类编码",
    "special_business_type": "特殊业务",
    "goods_name": "项目名称",
    "specification": "规格型号",
    "unit": "单位",
    "quantity": "数量",
    "unit_price": "单价",
    "amount": "金额",
    "tax_rate": "税率",
    "tax_amount": "税额",
    "total_amount": "价税合计",
    "invoice_source": "发票来源",
    "invoice_type": "票种",
    "invoice_status": "发票状态",
    "is_positive": "正数标志",
    "risk_level": "风险等级",
    "issuer": "开票人",
    "remark": "备注",

    # 财务指标 (vw_financial_metrics)
    "period_type": "期间类型",
    "metric_category": "指标分类",
    "metric_code": "指标代码",
    "metric_name": "指标名称",
    "metric_value": "指标值",
    "metric_unit": "指标单位",
    "evaluation_level": "评估等级",
    "calculated_at": "计算时间",

    # 企业所得税季报等特有字段
    "employee_quarter_avg": "季度平均职工人数",
    "asset_quarter_avg": "季度平均资产总额",
    "restricted_or_prohibited_industry": "限制或禁止行业",
    "small_micro_enterprise": "小型微利企业"
}

# Column Chinese name cache
_col_name_cache = {}


def _get_conn():
    from modules.db_utils import get_connection
    return get_connection()


def _resolve_view(domain_cfg, taxpayer_type, accounting_standard):
    """Pick the correct view based on taxpayer attributes."""
    views = domain_cfg.get("views", {})
    if "_default" in views:
        return views["_default"]
    # EAV domains: use gaap_type mapping
    key = domain_cfg["key"]
    if key in ("profit", "cash_flow"):
        gaap = "CAS" if accounting_standard == "企业会计准则" else "SAS"
        return views.get(gaap, list(views.values())[0])
    if key == "balance_sheet":
        gaap = "ASBE" if accounting_standard == "企业会计准则" else "ASSE"
        return views.get(gaap, list(views.values())[0])
    if key == "vat":
        return views.get(taxpayer_type, list(views.values())[0])
    return list(views.values())[0]


def _resolve_gaap(domain_key, accounting_standard):
    """Get gaap_type for EAV queries."""
    if domain_key in ("profit", "cash_flow"):
        return "CAS" if accounting_standard == "企业会计准则" else "SAS"
    if domain_key == "balance_sheet":
        return "ASBE" if accounting_standard == "企业会计准则" else "ASSE"
    return None


def _get_chinese_col_name(conn, col_name, view_name):
    """Get Chinese name for a column, checking static dict first, then DB mapping tables."""
    cache_key = f"{view_name}:{col_name}"
    if cache_key in _col_name_cache:
        return _col_name_cache[cache_key]

    # 1. Check static comprehensive dictionary
    if col_name in _COLUMN_CHINESE_NAMES:
        _col_name_cache[cache_key] = _COLUMN_CHINESE_NAMES[col_name]
        return _COLUMN_CHINESE_NAMES[col_name]
        
    # 2. Check semantic mapping
    try:
        r = conn.execute(
            "SELECT business_term FROM nl2sql_semantic_mapping WHERE source_column = ? AND is_primary = 1",
            (col_name,)
        ).fetchone()
        if r:
            _col_name_cache[cache_key] = r[0]
            return r[0]
    except Exception:
        pass

    # 3. Fallback: query DB mapping tables
    for mapping_table in ["vat_general_column_mapping", "vat_small_column_mapping", 
                          "eit_annual_main_column_mapping", "eit_quarter_main_column_mapping"]:
        try:
            r = conn.execute(
                f"SELECT business_name FROM {mapping_table} WHERE column_name = ?",
                (col_name,)
            ).fetchone()
            if r:
                _col_name_cache[cache_key] = r[0]
                return r[0]
        except Exception:
            pass

    # Fallback: use column name as-is
    _col_name_cache[cache_key] = col_name
    return col_name


def _is_numeric_col(col_name):
    """Heuristic: columns that should be right-aligned."""
    numeric_suffixes = ("_amount", "_tax", "_total", "_balance", "_begin", "_end", "_rate", "_ratio",
                        "_revenue", "_cost", "_expense", "_profit", "_income", "_loss", "_value",
                        "_count", "_avg", "_payable", "_credit", "_debit", "_refund",
                        "_gains", "_expenses", "_surcharges", "_relief", "_adjustment",
                        "_share", "_due", "_exemption", "_decrease", "_increase",
                        "_offset", "_deduction", "_depreciation", "_prepaid")
    numeric_names = {"amount", "tax_amount", "total_amount", "quantity", "unit_price", "line_no",
                     "period_year", "period_month", "period_quarter", "revision_no", "metric_value",
                     "revenue", "cost", "tax_due",
                     "less_losses_carried_forward", "less_prepaid_tax_current_year"}
    if col_name in numeric_names:
        return True
    for suffix in numeric_suffixes:
        if col_name.endswith(suffix):
            return True
    return False


def _classify_col_type(col_name):
    """Classify column into semantic type for frontend width strategy."""
    _id_cols = {
        'taxpayer_id', 'invoice_pk', 'digital_invoice_no', 'invoice_code',
        'invoice_number', 'seller_tax_id', 'buyer_tax_id', 'account_code',
        'tax_category_code', 'metric_code', 'filing_id', 'item_code',
    }
    _name_cols = {
        'taxpayer_name', 'seller_name', 'buyer_name', 'account_name',
        'goods_name', 'metric_name', 'item_name', 'business_scope',
        'registered_address', 'remark',
    }
    _enum_cols = {
        'period_year', 'period_month', 'period_quarter', 'period_type',
        'period', 'taxpayer_type', 'invoice_format', 'invoice_type',
        'invoice_status', 'invoice_source', 'is_positive', 'risk_level',
        'balance_direction', 'category', 'level', 'metric_category',
        'metric_unit', 'evaluation_level', 'operating_status',
        'collection_method', 'item_type', 'time_range', 'unit',
        'issuer', 'specification', 'special_business_type',
        'invoice_date', 'calculated_at', 'gaap_type',
    }
    if col_name in _id_cols:
        return 'id'
    if col_name in _name_cols:
        return 'name'
    if col_name in _enum_cols:
        return 'enum'
    if _is_numeric_col(col_name):
        return 'amount'
    return 'text'


# ---------------------------------------------------------------------------
# Raw format helpers
# ---------------------------------------------------------------------------

def _parse_monthly_period(period, conn, company_id, eav_table, gaap):
    """Parse YYYY-MM period string; fallback to latest available."""
    year, month = None, None
    if period and period != "all" and "-" in period and "Q" not in period:
        parts = period.split("-")
        year, month = int(parts[0]), int(parts[1])
    if not year or not month:
        row = conn.execute(
            f"SELECT period_year, period_month FROM {eav_table} "
            f"WHERE taxpayer_id = ? AND gaap_type = ? "
            f"ORDER BY period_year DESC, period_month DESC LIMIT 1",
            (company_id, gaap),
        ).fetchone()
        if row:
            year, month = row["period_year"], row["period_month"]
    return year, month


def _raw_eav_handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg):
    """Raw format for profit statement and cash flow statement (EAV domains)."""
    domain = domain_cfg["key"]
    eav_table = domain_cfg["eav_table"]
    dict_table = domain_cfg["dict_table"]
    raw_cols = domain_cfg["raw_cols"]
    raw_labels = domain_cfg["raw_labels"]
    gaap = _resolve_gaap(domain, acc_std)

    year, month = _parse_monthly_period(period, conn, company_id, eav_table, gaap)
    if not year or not month:
        return {"domain": domain, "format_type": "income_statement" if domain == "profit" else "cash_flow",
                "company_name": company_name, "period_label": "", "unit": "元", "gaap_type": gaap, "items": []}

    items = conn.execute(
        f"SELECT d.item_name, d.line_number, COALESCE(d.is_total, 0) AS is_total, "
        f"d.display_order, COALESCE(d.category, '') AS category, "
        f"i.{raw_cols[0]} AS col1, i.{raw_cols[1]} AS col2 "
        f"FROM {dict_table} d "
        f"LEFT JOIN (SELECT * FROM {eav_table} WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? AND gaap_type = ? "
        f"  AND revision_no = (SELECT MAX(r.revision_no) FROM {eav_table} r "
        f"    WHERE r.taxpayer_id = {eav_table}.taxpayer_id AND r.period_year = {eav_table}.period_year "
        f"    AND r.period_month = {eav_table}.period_month AND r.gaap_type = {eav_table}.gaap_type "
        f"    AND r.item_code = {eav_table}.item_code)) i "
        f"ON d.item_code = i.item_code AND d.gaap_type = i.gaap_type "
        f"WHERE d.gaap_type = ? "
        f"ORDER BY d.display_order, d.line_number",
        (company_id, year, month, gaap, gaap),
    ).fetchall()

    result_items = []
    for it in items:
        result_items.append({
            "item_name": it["item_name"],
            "line_number": it["line_number"],
            "is_total": bool(it["is_total"]),
            "category": it["category"],
            raw_cols[0]: float(it["col1"]) if it["col1"] is not None else None,
            raw_cols[1]: float(it["col2"]) if it["col2"] is not None else None,
        })

    fmt = "income_statement" if domain == "profit" else "cash_flow"
    return {
        "domain": domain,
        "format_type": fmt,
        "company_name": company_name,
        "period_label": f"{year}年{month}月",
        "unit": "元",
        "gaap_type": gaap,
        "items": result_items,
        "raw_labels": list(raw_labels),
    }


def _raw_balance_sheet_handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg):
    """Raw format for balance sheet — dual-column (left=assets, right=liabilities+equity)."""
    eav_table = domain_cfg["eav_table"]
    dict_table = domain_cfg["dict_table"]
    gaap = _resolve_gaap("balance_sheet", acc_std)

    year, month = _parse_monthly_period(period, conn, company_id, eav_table, gaap)
    if not year or not month:
        return {"domain": "balance_sheet", "format_type": "balance_sheet",
                "company_name": company_name, "period_label": "", "unit": "元",
                "gaap_type": gaap, "left_items": [], "right_items": []}

    items = conn.execute(
        f"SELECT d.item_name, d.line_number, d.is_total, d.display_order, d.section, "
        f"i.beginning_balance, i.ending_balance "
        f"FROM {dict_table} d "
        f"LEFT JOIN (SELECT * FROM {eav_table} WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? AND gaap_type = ? "
        f"  AND revision_no = (SELECT MAX(r.revision_no) FROM {eav_table} r "
        f"    WHERE r.taxpayer_id = {eav_table}.taxpayer_id AND r.period_year = {eav_table}.period_year "
        f"    AND r.period_month = {eav_table}.period_month AND r.gaap_type = {eav_table}.gaap_type "
        f"    AND r.item_code = {eav_table}.item_code)) i "
        f"ON d.item_code = i.item_code AND d.gaap_type = i.gaap_type "
        f"WHERE d.gaap_type = ? "
        f"ORDER BY d.display_order, d.line_number",
        (company_id, year, month, gaap, gaap),
    ).fetchall()

    left_items, right_items = [], []
    for it in items:
        entry = {
            "item_name": it["item_name"],
            "line_number": it["line_number"],
            "is_total": bool(it["is_total"]),
            "ending_balance": float(it["ending_balance"]) if it["ending_balance"] is not None else None,
            "beginning_balance": float(it["beginning_balance"]) if it["beginning_balance"] is not None else None,
        }
        if it["section"] == "ASSET":
            left_items.append(entry)
        else:
            right_items.append(entry)

    return {
        "domain": "balance_sheet",
        "format_type": "balance_sheet",
        "company_name": company_name,
        "period_label": f"{year}年{month}月{calendar.monthrange(year, month)[1]}日",
        "unit": "元",
        "gaap_type": gaap,
        "left_items": left_items,
        "right_items": right_items,
    }


# VAT section definitions
_VAT_GENERAL_SECTIONS = [
    ("销售额", 1, 10),
    ("税款计算", 11, 24),
    ("税款缴纳", 25, 38),
    ("附加税费", 39, 41),
]
_VAT_SMALL_SECTIONS = [
    ("计税依据", 1, 14),
    ("税款计算", 15, 22),
    ("附加税费", 23, 25),
]


def _raw_vat_handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg):
    """Raw format for VAT return — pivot wide-table rows into per-field rows."""
    is_general = tp_type == "一般纳税人"
    view = "vw_vat_return_general" if is_general else "vw_vat_return_small"
    mapping_table = "vat_general_column_mapping" if is_general else "vat_small_column_mapping"
    sections = _VAT_GENERAL_SECTIONS if is_general else _VAT_SMALL_SECTIONS
    format_type = "vat_general" if is_general else "vat_small"

    # Parse period
    year, month = None, None
    if period and period != "all" and "-" in period and "Q" not in period:
        parts = period.split("-")
        year, month = int(parts[0]), int(parts[1])
    if not year or not month:
        row = conn.execute(
            f"SELECT period_year, period_month FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC, period_month DESC LIMIT 1",
            (company_id,),
        ).fetchone()
        if row:
            year, month = row["period_year"], row["period_month"]
        else:
            return {"domain": "vat", "format_type": format_type, "company_name": company_name,
                    "taxpayer_id": company_id, "period_label": "", "unit": "元", "rows": []}

    # Get 4 data rows (2 item_type x 2 time_range)
    data_rows = conn.execute(
        f"SELECT * FROM {view} WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?",
        (company_id, year, month),
    ).fetchall()

    # Index by (item_type, time_range)
    data_map = {}
    for r in data_rows:
        data_map[(r["item_type"], r["time_range"])] = r

    if is_general:
        type1, type2 = "一般项目", "即征即退项目"
        tr1, tr2 = "本月", "累计"
    else:
        type1, type2 = "货物及劳务", "服务不动产无形资产"
        tr1, tr2 = "本期", "累计"

    r_t1_tr1 = data_map.get((type1, tr1))
    r_t1_tr2 = data_map.get((type1, tr2))
    r_t2_tr1 = data_map.get((type2, tr1))
    r_t2_tr2 = data_map.get((type2, tr2))

    # Get column mapping
    col_map = conn.execute(
        f"SELECT line_number, column_name, business_name FROM {mapping_table} ORDER BY line_number"
    ).fetchall()

    def _safe_float(row, col):
        if row is None:
            return None
        val = row[col]
        return float(val) if val is not None else None

    # Pre-compute actual row counts per section (based on col_map entries, not line_number range)
    all_line_numbers = [cm["line_number"] for cm in col_map]
    section_row_counts = {}
    for sn, s_start, s_end in sections:
        section_row_counts[sn] = sum(1 for ln in all_line_numbers if s_start <= ln <= s_end)

    result_rows = []
    for cm in col_map:
        ln = cm["line_number"]
        col = cm["column_name"]
        name = cm["business_name"]

        # Determine section
        sec_name, sec_span = "", 0
        for sn, s_start, s_end in sections:
            if s_start <= ln <= s_end:
                if ln == s_start:
                    sec_name = sn
                    sec_span = section_row_counts.get(sn, 0)
                break

        row_data = {
            "line_number": ln,
            "item_name": name,
            "section": sec_name,
            "section_span": sec_span,
        }

        if is_general:
            row_data["general_current"] = _safe_float(r_t1_tr1, col)
            row_data["general_cumulative"] = _safe_float(r_t1_tr2, col)
            row_data["immediate_current"] = _safe_float(r_t2_tr1, col)
            row_data["immediate_cumulative"] = _safe_float(r_t2_tr2, col)
        else:
            row_data["goods_current"] = _safe_float(r_t1_tr1, col)
            row_data["goods_cumulative"] = _safe_float(r_t1_tr2, col)
            row_data["services_current"] = _safe_float(r_t2_tr1, col)
            row_data["services_cumulative"] = _safe_float(r_t2_tr2, col)

        result_rows.append(row_data)

    return {
        "domain": "vat",
        "format_type": format_type,
        "taxpayer_type": tp_type,
        "company_name": company_name,
        "taxpayer_id": company_id,
        "period_label": f"{year}年{month}月",
        "unit": "元",
        "rows": result_rows,
    }


# EIT section definitions
_EIT_ANNUAL_SECTIONS = [
    ("利润总额计算", 1, 18),
    ("应纳税所得额计算", 19, 28),
    ("应纳税额计算", 29, 45),
]
_EIT_QUARTER_SECTIONS = [
    ("按照实际利润额预缴", 1, 16),
    ("汇总纳税", 17, 24),
]


def _raw_eit_annual_handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg):
    """Raw format for EIT annual return."""
    view = "vw_eit_annual_main"

    # Parse period (year only)
    year = None
    if period and period != "all":
        year = int(period.split("-")[0]) if "-" in period else int(period)
    if not year:
        row = conn.execute(
            f"SELECT period_year FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC LIMIT 1",
            (company_id,),
        ).fetchone()
        year = row["period_year"] if row else None
    if not year:
        return {"domain": "eit_annual", "format_type": "eit_annual", "company_name": company_name,
                "taxpayer_id": company_id, "period_label": "", "unit": "元", "rows": []}

    data_row = conn.execute(
        f"SELECT * FROM {view} WHERE taxpayer_id = ? AND period_year = ? LIMIT 1",
        (company_id, year),
    ).fetchone()
    if not data_row:
        return {"domain": "eit_annual", "format_type": "eit_annual", "company_name": company_name,
                "taxpayer_id": company_id, "period_label": f"{year}年度", "unit": "元", "rows": []}

    col_map = conn.execute(
        "SELECT line_number, column_name, business_name FROM eit_annual_main_column_mapping ORDER BY line_number"
    ).fetchall()

    result_rows = []
    for cm in col_map:
        ln = cm["line_number"]
        col = cm["column_name"]
        name = cm["business_name"]
        val = data_row[col]

        sec_name, sec_span = "", 0
        for sn, s_start, s_end in _EIT_ANNUAL_SECTIONS:
            if s_start <= ln <= s_end:
                if ln == s_start:
                    sec_name = sn
                    sec_span = s_end - s_start + 1
                break

        result_rows.append({
            "line_number": ln,
            "item_name": name,
            "amount": float(val) if val is not None else None,
            "section": sec_name,
            "section_span": sec_span,
        })

    return {
        "domain": "eit_annual",
        "format_type": "eit_annual",
        "company_name": company_name,
        "taxpayer_id": company_id,
        "period_label": f"{year}年度",
        "unit": "元",
        "rows": result_rows,
    }


def _raw_eit_quarter_handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg):
    """Raw format for EIT quarterly return."""
    view = "vw_eit_quarter_main"

    # Parse period (YYYY-Q#)
    year, quarter = None, None
    if period and period != "all":
        if "-Q" in period:
            parts = period.split("-Q")
            year, quarter = int(parts[0]), int(parts[1])
        elif "-" in period:
            parts = period.split("-")
            year = int(parts[0])
    if not year:
        row = conn.execute(
            f"SELECT period_year, period_quarter FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC, period_quarter DESC LIMIT 1",
            (company_id,),
        ).fetchone()
        if row:
            year, quarter = row["period_year"], row["period_quarter"]
    if not year or not quarter:
        return {"domain": "eit_quarter", "format_type": "eit_quarter", "company_name": company_name,
                "taxpayer_id": company_id, "period_label": "", "unit": "元", "rows": [], "extra_info": {}}

    data_row = conn.execute(
        f"SELECT * FROM {view} WHERE taxpayer_id = ? AND period_year = ? AND period_quarter = ? LIMIT 1",
        (company_id, year, quarter),
    ).fetchone()
    if not data_row:
        return {"domain": "eit_quarter", "format_type": "eit_quarter", "company_name": company_name,
                "taxpayer_id": company_id, "period_label": f"{year}年第{quarter}季度", "unit": "元", "rows": [], "extra_info": {}}

    col_map = conn.execute(
        "SELECT line_number, column_name, business_name FROM eit_quarter_main_column_mapping ORDER BY line_number"
    ).fetchall()

    result_rows = []
    for cm in col_map:
        ln = cm["line_number"]
        col = cm["column_name"]
        name = cm["business_name"]
        val = data_row[col]

        sec_name, sec_span = "", 0
        for sn, s_start, s_end in _EIT_QUARTER_SECTIONS:
            if s_start <= ln <= s_end:
                if ln == s_start:
                    sec_name = sn
                    sec_span = s_end - s_start + 1
                break

        result_rows.append({
            "line_number": ln,
            "item_name": name,
            "amount": float(val) if val is not None else None,
            "section": sec_name,
            "section_span": sec_span,
        })

    # Extra info fields not in column_mapping
    extra_info = {}
    for field in ("employee_quarter_avg", "asset_quarter_avg", "small_micro_enterprise"):
        try:
            extra_info[field] = data_row[field]
        except (IndexError, KeyError):
            pass

    return {
        "domain": "eit_quarter",
        "format_type": "eit_quarter",
        "company_name": company_name,
        "taxpayer_id": company_id,
        "period_label": f"{year}年第{quarter}季度",
        "unit": "元",
        "rows": result_rows,
        "extra_info": extra_info,
    }


# Handler dispatch map
_RAW_HANDLERS = {
    "profit": _raw_eav_handler,
    "balance_sheet": _raw_balance_sheet_handler,
    "cash_flow": _raw_eav_handler,
    "vat": _raw_vat_handler,
    "eit_annual": _raw_eit_annual_handler,
    "eit_quarter": _raw_eit_quarter_handler,
}


@router.get("/tables")
async def list_tables(company_id: str = Query(""), user: dict = Depends(get_current_user)):
    require_company_access(user, company_id)
    conn = _get_conn()
    try:
        # Get company info
        company_name = ""
        taxpayer_type = "一般纳税人"
        accounting_standard = "企业会计准则"
        if company_id:
            info = conn.execute(
                "SELECT taxpayer_name, taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
                (company_id,)
            ).fetchone()
            if info:
                company_name = info["taxpayer_name"]
                taxpayer_type = info["taxpayer_type"]
                accounting_standard = info["accounting_standard"]

        tables = []
        for d in BROWSE_DOMAINS:
            view = _resolve_view(d, taxpayer_type, accounting_standard)
            try:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {view} WHERE taxpayer_id = ?", (company_id,)).fetchone()[0]
                if cnt > 0:
                    tables.append({"key": d["key"], "label": d["label"]})
            except Exception:
                pass

        return {"tables": tables, "company_name": company_name}
    finally:
        conn.close()


@router.get("/periods")
async def list_periods(company_id: str = Query(""), domain: str = Query(""), user: dict = Depends(get_current_user)):
    require_company_access(user, company_id)
    conn = _get_conn()
    try:
        domain_cfg = next((d for d in BROWSE_DOMAINS if d["key"] == domain), None)
        if not domain_cfg:
            return []

        info = conn.execute(
            "SELECT taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?", (company_id,)
        ).fetchone()
        tp_type = info["taxpayer_type"] if info else "一般纳税人"
        acc_std = info["accounting_standard"] if info else "企业会计准则"
        view = _resolve_view(domain_cfg, tp_type, acc_std)

        # Check if view has period_month
        has_month = True
        has_quarter = False
        try:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({view})").fetchall()]
            has_month = "period_month" in cols
            has_quarter = "period_quarter" in cols
        except Exception:
            pass

        periods = []
        if has_month:
            rows = conn.execute(
                f"SELECT DISTINCT period_year, period_month FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC, period_month DESC",
                (company_id,)
            ).fetchall()
            for r in rows:
                periods.append({"value": f"{r['period_year']}-{str(r['period_month']).zfill(2)}", "label": f"{r['period_year']}年{r['period_month']}月"})
        elif has_quarter:
            rows = conn.execute(
                f"SELECT DISTINCT period_year, period_quarter FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC, period_quarter DESC",
                (company_id,)
            ).fetchall()
            for r in rows:
                periods.append({"value": f"{r['period_year']}-Q{r['period_quarter']}", "label": f"{r['period_year']}年第{r['period_quarter']}季度"})
        else:
            rows = conn.execute(
                f"SELECT DISTINCT period_year FROM {view} WHERE taxpayer_id = ? ORDER BY period_year DESC",
                (company_id,)
            ).fetchall()
            for r in rows:
                periods.append({"value": str(r["period_year"]), "label": f"{r['period_year']}年"})

        return periods
    finally:
        conn.close()


@router.get("/data")
async def get_data(
    company_id: str = Query(""),
    domain: str = Query(""),
    period: str = Query("all"),
    format: str = Query("general"),
    user: dict = Depends(get_current_user),
):
    require_company_access(user, company_id)
    conn = _get_conn()
    try:
        domain_cfg = next((d for d in BROWSE_DOMAINS if d["key"] == domain), None)
        if not domain_cfg:
            return {"error": "Unknown domain"}

        info = conn.execute(
            "SELECT taxpayer_name, taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
            (company_id,)
        ).fetchone()
        if not info:
            return {"error": "Company not found"}
        company_name = info["taxpayer_name"]
        tp_type = info["taxpayer_type"]
        acc_std = info["accounting_standard"]

        # --- RAW FORMAT ---
        if format == "raw":
            handler = _RAW_HANDLERS.get(domain)
            if handler:
                return handler(conn, company_id, company_name, tp_type, acc_std, period, domain_cfg)
            return {"error": "该数据表不支持原表格式", "domain": domain}

        # --- GENERAL FORMAT ---
        view = _resolve_view(domain_cfg, tp_type, acc_std)

        # Build WHERE clause
        where = "WHERE taxpayer_id = ?"
        params = [company_id]

        if period and period != "all":
            if "-Q" in period:
                parts = period.split("-Q")
                where += " AND period_year = ? AND period_quarter = ?"
                params.extend([int(parts[0]), int(parts[1])])
            elif "-" in period:
                parts = period.split("-")
                where += " AND period_year = ? AND period_month = ?"
                params.extend([int(parts[0]), int(parts[1])])
            else:
                where += " AND period_year = ?"
                params.append(int(period))

        # For profit/cash_flow views, filter to '本期' time_range for general view
        # VAT views also have time_range but use '本月'/'累计', so only filter for EAV domains
        view_cols = [r[1] for r in conn.execute(f"PRAGMA table_info({view})").fetchall()]
        if "time_range" in view_cols and domain_cfg.get("eav_table"):
            where += " AND time_range = '本期'"

        # Build dynamic ORDER BY based on available columns
        order_parts = ["period_year DESC"]
        if "period_quarter" in view_cols:
            order_parts.append("period_quarter DESC")
        if "period_month" in view_cols:
            order_parts.append("period_month DESC")
        order_by = ", ".join(order_parts)

        rows = conn.execute(
            f"SELECT * FROM {view} {where} ORDER BY {order_by} LIMIT 500",
            params
        ).fetchall()

        if not rows:
            return {"domain": domain, "total_rows": 0, "columns": [], "rows": []}

        # Build columns with Chinese names
        col_keys = [desc[0] for desc in conn.execute(f"SELECT * FROM {view} LIMIT 0").description]
        # Filter out internal columns
        skip_cols = {"revision_no", "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence", "time_range", "accounting_standard_name", "accounting_standard"}
        columns = []
        for ck in col_keys:
            if ck in skip_cols:
                continue
            label = _get_chinese_col_name(conn, ck, view)
            align = "right" if _is_numeric_col(ck) else "left"
            columns.append({"key": ck, "label": label, "align": align, "col_type": _classify_col_type(ck)})

        # Build rows
        result_rows = []
        for r in rows:
            row_dict = {}
            for col in columns:
                val = r[col["key"]]
                row_dict[col["key"]] = val
            result_rows.append(row_dict)

        return {
            "domain": domain,
            "total_rows": len(result_rows),
            "columns": columns,
            "rows": result_rows,
        }
    finally:
        conn.close()
