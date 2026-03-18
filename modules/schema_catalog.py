"""静态白名单：域→视图、视图→列、黑名单"""

from pathlib import Path as _Path
from config.config_loader import load_json as _load_json

_SCHEMA_DIR = _Path(__file__).resolve().parent.parent / "config" / "schema"
_CFG_domain_views = _load_json(_SCHEMA_DIR / "domain_views.json", {})
_CFG_view_columns = _load_json(_SCHEMA_DIR / "view_columns.json", {})
_CFG_blacklists = _load_json(_SCHEMA_DIR / "security_blacklists.json", {})
_CFG_dimensions = _load_json(_SCHEMA_DIR / "dimension_columns.json", {})

# 域 → 允许视图
DOMAIN_VIEWS = _CFG_domain_views.get("domain_views", {
    "vat": ["vw_vat_return_general", "vw_vat_return_small"],
    "eit": ["vw_eit_annual_main", "vw_eit_quarter_main"],
    "balance_sheet": ["vw_balance_sheet_eas", "vw_balance_sheet_sas"],
    "profit": ["vw_profit_eas", "vw_profit_sas"],
    "cash_flow": ["vw_cash_flow_eas", "vw_cash_flow_sas"],
    "account_balance": ["vw_account_balance"],
    "invoice": ["vw_inv_spec_purchase", "vw_inv_spec_sales"],
    "profile": ["vw_enterprise_profile"],
    "financial_metrics": ["vw_financial_metrics"],
    "cross_domain": [],  # 动态组合
})

# 视图 → 允许列（从JSON加载，过滤掉_comment等内部key）
_vc_raw = {k: v for k, v in _CFG_view_columns.items() if not k.startswith("_")} if _CFG_view_columns else {}
VIEW_COLUMNS = _vc_raw if _vc_raw else {
    "vw_vat_return_general": [
        "taxpayer_id", "taxpayer_name", "period_year", "period_month",
        "item_type", "time_range", "taxpayer_type", "revision_no",
        "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
        "sales_taxable_rate", "sales_goods", "sales_services",
        "sales_adjustment_check", "sales_simple_method", "sales_simple_adjust_check",
        "sales_export_credit_refund", "sales_tax_free", "sales_tax_free_goods",
        "sales_tax_free_services", "output_tax", "input_tax", "last_period_credit",
        "transfer_out", "export_refund", "tax_check_supplement", "deductible_total",
        "actual_deduct", "tax_payable", "end_credit", "simple_tax",
        "simple_tax_check_supplement", "tax_reduction", "total_tax_payable",
        "unpaid_begin", "export_receipt_tax", "paid_current", "prepaid_installment",
        "prepaid_export_receipt", "paid_last_period", "paid_arrears", "unpaid_end",
        "arrears", "supplement_refund", "immediate_refund", "unpaid_check_begin",
        "paid_check_current", "unpaid_check_end", "city_maintenance_tax",
        "education_surcharge", "local_education_surcharge",
    ],
    "vw_vat_return_small": [
        "taxpayer_id", "taxpayer_name", "period_year", "period_month",
        "item_type", "time_range", "taxpayer_type", "revision_no",
        "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
        "sales_3percent", "sales_3percent_invoice_spec", "sales_3percent_invoice_other",
        "sales_5percent", "sales_5percent_invoice_spec", "sales_5percent_invoice_other",
        "sales_used_assets", "sales_used_assets_invoice_other",
        "sales_tax_free", "sales_tax_free_micro", "sales_tax_free_threshold",
        "sales_tax_free_other", "sales_export_tax_free",
        "sales_export_tax_free_invoice_other",
        "tax_due_current", "tax_due_reduction", "tax_free_amount",
        "tax_free_micro", "tax_free_threshold", "tax_due_total",
        "tax_prepaid", "tax_supplement_refund",
        "city_maintenance_tax", "education_surcharge", "local_education_surcharge",
    ],
    "vw_eit_annual_main": [
        "filing_id", "taxpayer_id", "taxpayer_name", "taxpayer_type",
        "period_year", "revision_no",
        "submitted_at", "etl_batch_id", "source_doc_id", "etl_confidence",
        "revenue", "cost", "taxes_surcharges",
        "selling_expenses", "admin_expenses", "rd_expenses", "financial_expenses",
        "other_gains", "investment_income", "net_exposure_hedge_gains",
        "fair_value_change_gains", "credit_impairment_loss", "asset_impairment_loss",
        "asset_disposal_gains", "operating_profit",
        "non_operating_income", "non_operating_expenses", "total_profit",
        "less_foreign_income", "add_tax_adjust_increase", "less_tax_adjust_decrease",
        "exempt_income_deduction_total", "add_foreign_tax_offset",
        "adjusted_taxable_income", "less_income_exemption",
        "less_losses_carried_forward", "less_taxable_income_deduction",
        "taxable_income", "tax_rate", "tax_payable",
        "tax_credit_total", "less_foreign_tax_credit", "tax_due",
        "add_foreign_tax_due", "less_foreign_tax_credit_amount",
        "actual_tax_payable", "less_prepaid_tax", "tax_payable_or_refund",
        "hq_share", "fiscal_central_share", "hq_dept_share",
        "less_ethnic_autonomous_relief", "less_audit_adjustment",
        "less_special_adjustment", "final_tax_payable_or_refund",
    ],
    "vw_eit_quarter_main": [
        "filing_id", "taxpayer_id", "taxpayer_name", "taxpayer_type",
        "period_year", "period_quarter", "revision_no",
        "submitted_at", "etl_batch_id", "source_doc_id", "etl_confidence",
        "employee_quarter_avg", "asset_quarter_avg",
        "restricted_or_prohibited_industry", "small_micro_enterprise",
        "revenue", "cost", "total_profit",
        "add_specific_business_taxable_income", "less_non_taxable_income",
        "less_accelerated_depreciation", "tax_free_income_deduction_total",
        "income_exemption_total", "less_losses_carried_forward",
        "actual_profit", "tax_rate", "tax_payable",
        "tax_credit_total", "less_prepaid_tax_current_year",
        "less_specific_business_prepaid", "current_tax_payable_or_refund",
        "hq_share_total", "hq_share", "fiscal_central_share",
        "hq_business_dept_share", "branch_share_ratio", "branch_share_amount",
        "ethnic_autonomous_relief_amount", "final_tax_payable_or_refund",
    ],
    "vw_account_balance": [
        "taxpayer_id", "taxpayer_name", "accounting_standard",
        "period_year", "period_month",
        "account_code", "account_name", "level", "category", "balance_direction",
        "is_gaap", "is_small", "revision_no",
        "opening_balance", "debit_amount", "credit_amount", "closing_balance",
        "source_unit",
    ],
    "vw_inv_spec_purchase": [
        "taxpayer_id", "taxpayer_name", "taxpayer_type",
        "period_year", "period_month",
        "invoice_format", "invoice_pk", "line_no",
        "invoice_code", "invoice_number", "digital_invoice_no",
        "seller_tax_id", "seller_name", "buyer_tax_id", "buyer_name",
        "invoice_date",
        "tax_category_code", "special_business_type",
        "goods_name", "specification", "unit", "quantity", "unit_price",
        "amount", "tax_rate", "tax_amount", "total_amount",
        "invoice_source", "invoice_type", "invoice_status",
        "is_positive", "risk_level", "issuer", "remark",
    ],
    "vw_inv_spec_sales": [
        "taxpayer_id", "taxpayer_name", "taxpayer_type",
        "period_year", "period_month",
        "invoice_format", "invoice_pk", "line_no",
        "invoice_code", "invoice_number", "digital_invoice_no",
        "seller_tax_id", "seller_name", "buyer_tax_id", "buyer_name",
        "invoice_date",
        "amount", "tax_amount", "total_amount",
        "invoice_source", "invoice_type", "invoice_status",
        "is_positive", "risk_level", "issuer", "remark",
    ],
}

# 动态生成资产负债表视图列
def _bs_view_columns(items):
    """生成资产负债表视图的列名列表"""
    base = [
        "taxpayer_id", "taxpayer_name", "accounting_standard",
        "period_year", "period_month", "revision_no",
        "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
    ]
    for code in items:
        col = code.lower()
        base.append(f"{col}_begin")
        base.append(f"{col}_end")
    return base

_ASBE_ITEMS = [
    'CASH', 'TRADING_FINANCIAL_ASSETS', 'DERIVATIVE_FINANCIAL_ASSETS',
    'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE', 'ACCOUNTS_RECEIVABLE_FINANCING',
    'PREPAYMENTS', 'OTHER_RECEIVABLES', 'INVENTORY', 'CONTRACT_ASSETS',
    'HELD_FOR_SALE_ASSETS', 'CURRENT_PORTION_NON_CURRENT_ASSETS',
    'OTHER_CURRENT_ASSETS', 'CURRENT_ASSETS',
    'DEBT_INVESTMENTS', 'OTHER_DEBT_INVESTMENTS', 'LONG_TERM_RECEIVABLES',
    'LONG_TERM_EQUITY_INVESTMENTS', 'OTHER_EQUITY_INSTRUMENTS_INVEST',
    'OTHER_NON_CURRENT_FINANCIAL_ASSETS', 'INVESTMENT_PROPERTY',
    'FIXED_ASSETS', 'CONSTRUCTION_IN_PROGRESS', 'PRODUCTIVE_BIOLOGICAL_ASSETS',
    'OIL_AND_GAS_ASSETS', 'RIGHT_OF_USE_ASSETS', 'INTANGIBLE_ASSETS',
    'DEVELOPMENT_EXPENDITURE', 'GOODWILL', 'LONG_TERM_DEFERRED_EXPENSES',
    'DEFERRED_TAX_ASSETS', 'OTHER_NON_CURRENT_ASSETS', 'NON_CURRENT_ASSETS',
    'ASSETS',
    'SHORT_TERM_LOANS', 'TRADING_FINANCIAL_LIABILITIES',
    'DERIVATIVE_FINANCIAL_LIABILITIES', 'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE',
    'ADVANCES_FROM_CUSTOMERS', 'CONTRACT_LIABILITIES',
    'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE', 'OTHER_PAYABLES',
    'HELD_FOR_SALE_LIABILITIES', 'CURRENT_PORTION_NON_CURRENT_LIABILITIES',
    'OTHER_CURRENT_LIABILITIES', 'CURRENT_LIABILITIES',
    'LONG_TERM_LOANS', 'BONDS_PAYABLE', 'LEASE_LIABILITIES',
    'LONG_TERM_PAYABLES', 'PROVISIONS', 'DEFERRED_INCOME',
    'DEFERRED_TAX_LIABILITIES', 'OTHER_NON_CURRENT_LIABILITIES',
    'NON_CURRENT_LIABILITIES', 'LIABILITIES',
    'SHARE_CAPITAL', 'CAPITAL_RESERVE', 'TREASURY_STOCK',
    'OTHER_COMPREHENSIVE_INCOME', 'SPECIAL_RESERVE', 'SURPLUS_RESERVE',
    'RETAINED_EARNINGS', 'EQUITY', 'LIABILITIES_AND_EQUITY',
]

_ASSE_ITEMS = [
    'CASH', 'SHORT_TERM_INVESTMENTS', 'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE',
    'PREPAYMENTS', 'DIVIDENDS_RECEIVABLE', 'INTEREST_RECEIVABLE',
    'OTHER_RECEIVABLES', 'INVENTORY', 'RAW_MATERIALS', 'WORK_IN_PROCESS',
    'FINISHED_GOODS', 'TURNOVER_MATERIALS', 'OTHER_CURRENT_ASSETS',
    'CURRENT_ASSETS',
    'LONG_TERM_BOND_INVESTMENTS', 'LONG_TERM_EQUITY_INVESTMENTS',
    'FIXED_ASSETS_ORIGINAL', 'ACCUMULATED_DEPRECIATION', 'FIXED_ASSETS_NET',
    'CONSTRUCTION_IN_PROGRESS', 'ENGINEERING_MATERIALS',
    'FIXED_ASSETS_LIQUIDATION', 'PRODUCTIVE_BIOLOGICAL_ASSETS',
    'INTANGIBLE_ASSETS', 'DEVELOPMENT_EXPENDITURE',
    'LONG_TERM_DEFERRED_EXPENSES', 'OTHER_NON_CURRENT_ASSETS',
    'NON_CURRENT_ASSETS', 'ASSETS',
    'SHORT_TERM_LOANS', 'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE',
    'ADVANCES_FROM_CUSTOMERS', 'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE',
    'INTEREST_PAYABLE', 'PROFIT_PAYABLE', 'OTHER_PAYABLES',
    'OTHER_CURRENT_LIABILITIES', 'CURRENT_LIABILITIES',
    'LONG_TERM_LOANS', 'LONG_TERM_PAYABLES', 'DEFERRED_INCOME',
    'OTHER_NON_CURRENT_LIABILITIES', 'NON_CURRENT_LIABILITIES', 'LIABILITIES',
    'SHARE_CAPITAL', 'CAPITAL_RESERVE', 'SURPLUS_RESERVE',
    'RETAINED_EARNINGS', 'EQUITY', 'LIABILITIES_AND_EQUITY',
]

VIEW_COLUMNS["vw_balance_sheet_eas"] = _bs_view_columns(_ASBE_ITEMS)
VIEW_COLUMNS["vw_balance_sheet_sas"] = _bs_view_columns(_ASSE_ITEMS)

# 利润表视图列
VIEW_COLUMNS["vw_profit_eas"] = [
    "taxpayer_id", "taxpayer_name", "period_year", "period_month",
    "time_range", "accounting_standard_name", "revision_no",
    "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
    "operating_revenue", "operating_cost", "taxes_and_surcharges",
    "selling_expense", "administrative_expense", "rd_expense",
    "financial_expense", "interest_expense", "interest_income",
    "other_gains", "investment_income", "investment_income_associates",
    "amortized_cost_termination_income", "net_exposure_hedge_income",
    "fair_value_change_income", "credit_impairment_loss", "asset_impairment_loss",
    "asset_disposal_gains", "operating_profit",
    "non_operating_income", "non_operating_expense",
    "total_profit", "income_tax_expense", "net_profit",
    "continued_ops_net_profit", "discontinued_ops_net_profit",
    "other_comprehensive_income_net", "oci_not_reclassifiable", "oci_reclassifiable",
    "comprehensive_income_total", "eps_basic", "eps_diluted",
    "oci_remeasurement_pension", "oci_equity_method_nonreclassifiable",
    "oci_equity_investment_fv_change", "oci_credit_risk_change",
    "oci_equity_method_reclassifiable", "oci_debt_investment_fv_change",
    "oci_reclassify_to_pnl", "oci_debt_impairment",
    "oci_cash_flow_hedge", "oci_foreign_currency_translation",
]
VIEW_COLUMNS["vw_profit_sas"] = [
    "taxpayer_id", "taxpayer_name", "period_year", "period_month",
    "time_range", "accounting_standard_name", "revision_no",
    "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
    "operating_revenue", "operating_cost", "taxes_and_surcharges",
    "consumption_tax", "business_tax", "city_maintenance_tax",
    "resource_tax", "land_appreciation_tax", "property_related_taxes",
    "education_surcharge",
    "selling_expense", "goods_repair_expense", "advertising_expense",
    "administrative_expense", "organization_expense",
    "business_entertainment_expense", "research_expense",
    "financial_expense", "interest_expense_net",
    "investment_income", "operating_profit",
    "non_operating_income", "government_grant",
    "non_operating_expense", "bad_debt_loss",
    "long_term_bond_loss", "long_term_equity_loss",
    "force_majeure_loss", "tax_late_payment",
    "total_profit", "income_tax_expense", "net_profit",
]

# 现金流量表视图列
VIEW_COLUMNS["vw_cash_flow_eas"] = [
    "taxpayer_id", "taxpayer_name", "period_year", "period_month",
    "time_range", "taxpayer_type", "accounting_standard", "revision_no",
    "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
    "operating_inflow_sales", "operating_inflow_tax_refund", "operating_inflow_other",
    "operating_inflow_subtotal",
    "operating_outflow_purchase", "operating_outflow_labor", "operating_outflow_tax",
    "operating_outflow_other", "operating_outflow_subtotal", "operating_net_cash",
    "investing_inflow_sale_investment", "investing_inflow_returns",
    "investing_inflow_disposal_assets", "investing_inflow_disposal_subsidiary",
    "investing_inflow_other", "investing_inflow_subtotal",
    "investing_outflow_purchase_assets", "investing_outflow_purchase_investment",
    "investing_outflow_acquire_subsidiary", "investing_outflow_other",
    "investing_outflow_subtotal", "investing_net_cash",
    "financing_inflow_capital", "financing_inflow_borrowing", "financing_inflow_other",
    "financing_inflow_subtotal",
    "financing_outflow_debt_repayment", "financing_outflow_dividend_interest",
    "financing_outflow_other", "financing_outflow_subtotal", "financing_net_cash",
    "fx_impact", "net_increase_cash", "beginning_cash", "ending_cash",
]
VIEW_COLUMNS["vw_cash_flow_sas"] = [
    "taxpayer_id", "taxpayer_name", "period_year", "period_month",
    "time_range", "taxpayer_type", "accounting_standard", "revision_no",
    "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", "etl_confidence",
    "operating_receipts_sales", "operating_receipts_other",
    "operating_payments_purchase", "operating_payments_staff",
    "operating_payments_tax", "operating_payments_other", "operating_net_cash",
    "investing_receipts_disposal_investment", "investing_receipts_returns",
    "investing_receipts_disposal_assets",
    "investing_payments_purchase_investment", "investing_payments_purchase_assets",
    "investing_net_cash",
    "financing_receipts_borrowing", "financing_receipts_capital",
    "financing_payments_debt_principal", "financing_payments_debt_interest",
    "financing_payments_dividend", "financing_net_cash",
    "net_increase_cash", "beginning_cash", "ending_cash",
]

# VAT 维度有效值
VAT_GENERAL_ITEM_TYPES = ["一般项目", "即征即退项目"]
VAT_GENERAL_TIME_RANGES = ["本月", "累计"]
VAT_SMALL_ITEM_TYPES = ["货物及劳务", "服务不动产无形资产"]
VAT_SMALL_TIME_RANGES = ["本期", "累计"]

# 危险关键字黑名单
DENIED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "MERGE", "REPLACE",
    "CREATE", "ALTER", "DROP", "TRUNCATE",
    "GRANT", "REVOKE", "PRAGMA", "ATTACH", "DETACH",
    "VACUUM", "LOAD_EXTENSION",
]

DENIED_FUNCTIONS = ["randomblob", "load_extension"]

SYSTEM_TABLES = ["sqlite_master", "sqlite_sequence", "sqlite_temp_master"]

# 发票维度列
INVOICE_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'taxpayer_type',
    'period_year', 'period_month',
    'invoice_format', 'invoice_pk', 'line_no',
    'invoice_code', 'invoice_number', 'digital_invoice_no',
    'seller_tax_id', 'seller_name', 'buyer_tax_id', 'buyer_name',
    'invoice_date', 'invoice_source', 'invoice_type', 'invoice_status',
    'is_positive', 'risk_level', 'issuer', 'remark',
]

# 域名称映射（中文→英文）
DOMAIN_CN_MAP = {
    "增值税": "vat", "增值税申报": "vat", "VAT": "vat",
    "企业所得税": "eit", "所得税": "eit", "EIT": "eit",
    "企业所得税年报": "eit", "企业所得税季报": "eit",
    "年度所得税": "eit", "季度所得税": "eit", "所得税申报": "eit",
    "资产负债表": "balance_sheet", "资产负债": "balance_sheet",
    "利润表": "profit", "损益表": "profit",
    "现金流量表": "cash_flow", "现金流量": "cash_flow",
    "科目余额": "account_balance", "科目": "account_balance",
    "科目余额表": "account_balance", "余额表": "account_balance",
    "会计科目": "account_balance",
    "发票": "invoice",
    "进项发票": "invoice", "销项发票": "invoice",
    "采购发票": "invoice", "销售发票": "invoice",
    "专用发票": "invoice", "普通发票": "invoice", "数电票": "invoice",
    "企业画像": "profile", "画像": "profile",
    "净利润率": "financial_metrics", "净利率": "financial_metrics",
    "财务指标": "financial_metrics", "财务比率": "financial_metrics",
    "财税指标": "financial_metrics", "指标分析": "financial_metrics",
}

# EIT 维度列（用于constraint_injector区分维度和指标）
EIT_ANNUAL_DIM_COLS = [
    'filing_id', 'taxpayer_id', 'taxpayer_name', 'taxpayer_type',
    'period_year', 'revision_no',
]
EIT_QUARTER_DIM_COLS = [
    'filing_id', 'taxpayer_id', 'taxpayer_name', 'taxpayer_type',
    'period_year', 'period_quarter', 'revision_no',
]

# 科目余额维度列
ACCOUNT_BALANCE_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'accounting_standard',
    'period_year', 'period_month',
    'account_code', 'account_name', 'level', 'category', 'balance_direction',
    'is_gaap', 'is_small', 'revision_no',
]

# 资产负债表维度列
BALANCE_SHEET_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'accounting_standard',
    'period_year', 'period_month', 'revision_no',
]

# 利润表维度列
PROFIT_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'period_year', 'period_month',
    'time_range', 'accounting_standard_name', 'revision_no',
]

# 利润表 time_range 有效值
PROFIT_TIME_RANGES = ["本期", "本年累计"]

# 现金流量表维度列
CASH_FLOW_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'period_year', 'period_month',
    'time_range', 'taxpayer_type', 'accounting_standard', 'revision_no',
]

# 现金流量表 time_range 有效值
CASH_FLOW_TIME_RANGES = ["本期", "本年累计"]

# 财务指标视图列
VIEW_COLUMNS["vw_financial_metrics"] = [
    "taxpayer_id", "taxpayer_name", "taxpayer_type", "accounting_standard",
    "period_year", "period_month", "period_type",
    "metric_category", "metric_code", "metric_name",
    "metric_value", "metric_unit", "evaluation_level",
    "calculated_at",
]

# 财务指标维度列
FINANCIAL_METRICS_DIM_COLS = [
    'taxpayer_id', 'taxpayer_name', 'taxpayer_type', 'accounting_standard',
    'period_year', 'period_month', 'period_type',
    'metric_category', 'metric_code', 'metric_name',
]
