"""为4家新企业生成2023-2025年全域模拟数据
企业：创智软件(一般纳税人/EAS)、大华智能制造(小规模/SAS)、TSE科技(一般/EAS)、环球机械(小规模/SAS)
覆盖：taxpayer_info、VAT、EIT、科目余额、资产负债表、利润表、现金流量表、发票、画像快照、信用等级
验证规则：BS恒等式、利润计算逻辑、现金流勾稽、VAT税额计算、EIT A100000校验
"""
import sqlite3
import math
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH

# ============================================================
# 企业定义
# ============================================================
COMPANIES = [
    {
        'taxpayer_id': '91330200MA2KXXXXXX',
        'taxpayer_name': '创智软件股份有限公司',
        'taxpayer_type': '一般纳税人',
        'registration_type': '股份公司',
        'legal_representative': '陈浩',
        'establish_date': '2022-03-22',
        'industry_code': '3011',
        'industry_name': '软件和信息技术服务业',
        'tax_authority_code': '13302060000',
        'tax_authority_name': '国家税务总局宁波市大榭开发区税务局',
        'tax_bureau_level': '区县',
        'region_code': '330206',
        'region_name': '大榭开发区',
        'credit_grade_current': 'A',
        'credit_grade_year': 2024,
        'accounting_standard': '企业会计准则',
        'registered_capital': 350,
        'registered_address': '浙江省宁波市大榭开发区',
        'business_scope': '软件和信息技术服务业',
        'operating_status': '存续',
        'collection_method': '查账征收',
        # 数据生成参数
        'gaap_bs': 'ASBE', 'gaap_pl': 'CAS',
        'base_revenue': 1800000,
        'cost_ratio': 0.42,
        'growth_rate': 0.022,
        'seasonal_amp': 0.07,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'employee_count': 220,
        'asset_base': 8000000,
        'share_capital': 3500000,
        'capital_reserve': 800000,
        'surplus_reserve': 300000,
        'short_name': '创智软件',
    },
    {
        'taxpayer_id': '91330200MA2KYYYYYY',
        'taxpayer_name': '大华智能制造厂',
        'taxpayer_type': '小规模纳税人',
        'registration_type': '有限责任公司',
        'legal_representative': '周宏',
        'establish_date': '2020-08-04',
        'industry_code': '3511',
        'industry_name': '通用设备制造业',
        'tax_authority_code': '13205060000',
        'tax_authority_name': '国家税务总局苏州市吴中区税务局',
        'tax_bureau_level': '区县',
        'region_code': '320506',
        'region_name': '吴中区',
        'credit_grade_current': 'B',
        'credit_grade_year': 2024,
        'accounting_standard': '小企业会计准则',
        'registered_capital': 500,
        'registered_address': '苏州吴中区',
        'business_scope': '通用设备制造业',
        'operating_status': '存续',
        'collection_method': '查账征收',
        'gaap_bs': 'ASSE', 'gaap_pl': 'SAS',
        'base_revenue': 350000,
        'cost_ratio': 0.72,
        'growth_rate': 0.015,
        'seasonal_amp': 0.05,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'employee_count': 86,
        'asset_base': 2500000,
        'share_capital': 500000,
        'capital_reserve': 0,
        'surplus_reserve': 50000,
        'short_name': '大华制造',
    },
    {
        'taxpayer_id': '91310115MA2KZZZZZZ',
        'taxpayer_name': 'TSE科技有限公司',
        'taxpayer_type': '一般纳税人',
        'registration_type': '股份公司',
        'legal_representative': 'TSE',
        'establish_date': '2019-09-15',
        'industry_code': '3011',
        'industry_name': '软件和信息技术服务业',
        'tax_authority_code': '13101150000',
        'tax_authority_name': '国家税务总局上海市浦东新区税务局',
        'tax_bureau_level': '区县',
        'region_code': '310115',
        'region_name': '浦东新区',
        'credit_grade_current': 'A',
        'credit_grade_year': 2024,
        'accounting_standard': '企业会计准则',
        'registered_capital': 200,
        'registered_address': '上海市浦东新区高桥镇',
        'business_scope': '软件和信息技术服务业',
        'operating_status': '存续',
        'collection_method': '查账征收',
        'gaap_bs': 'ASBE', 'gaap_pl': 'CAS',
        'base_revenue': 1500000,
        'cost_ratio': 0.45,
        'growth_rate': 0.028,
        'seasonal_amp': 0.06,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'employee_count': 110,
        'asset_base': 6000000,
        'share_capital': 2000000,
        'capital_reserve': 600000,
        'surplus_reserve': 200000,
        'short_name': 'TSE科技',
    },
    {
        'taxpayer_id': '91330100MA2KWWWWWW',
        'taxpayer_name': '环球机械有限公司',
        'taxpayer_type': '小规模纳税人',
        'registration_type': '有限责任公司',
        'legal_representative': '李环球',
        'establish_date': '2015-10-11',
        'industry_code': '3511',
        'industry_name': '机械制造',
        'tax_authority_code': '13301080000',
        'tax_authority_name': '国家税务总局杭州市滨江区税务局',
        'tax_bureau_level': '区县',
        'region_code': '330108',
        'region_name': '滨江区',
        'credit_grade_current': 'B',
        'credit_grade_year': 2024,
        'accounting_standard': '小企业会计准则',
        'registered_capital': 800,
        'registered_address': '杭州市滨江区',
        'business_scope': '机械制造',
        'operating_status': '存续',
        'collection_method': '查账征收',
        'gaap_bs': 'ASSE', 'gaap_pl': 'SAS',
        'base_revenue': 450000,
        'cost_ratio': 0.68,
        'growth_rate': 0.018,
        'seasonal_amp': 0.06,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'employee_count': 210,
        'asset_base': 4000000,
        'share_capital': 800000,
        'capital_reserve': 200000,
        'surplus_reserve': 100000,
        'short_name': '环球机械',
    },
]

# ============================================================
# 工具函数
# ============================================================
def _monthly_factor(base_month_offset, growth_rate=0.02, seasonal_amp=0.05):
    growth = (1 + growth_rate) ** base_month_offset
    seasonal = 1 + seasonal_amp * math.sin(2 * math.pi * base_month_offset / 12)
    return growth * seasonal

def _month_offset(year, month, ref_year=2025, ref_month=1):
    return (year - ref_year) * 12 + (month - ref_month)

def _gen_months(start_year, start_month, end_year, end_month):
    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

def _safe_round(val, digits=0):
    return round(val, digits) if val is not None else None


# ============================================================
# ASBE / ASSE 项目元数据
# ============================================================
ASBE_META = {
    'CASH': ('货币资金', 1, 'ASSET'),
    'ACCOUNTS_RECEIVABLE': ('应收账款', 5, 'ASSET'),
    'PREPAYMENTS': ('预付账款', 7, 'ASSET'),
    'OTHER_RECEIVABLES': ('其他应收款', 8, 'ASSET'),
    'INVENTORY': ('存货', 9, 'ASSET'),
    'OTHER_CURRENT_ASSETS': ('其他流动资产', 13, 'ASSET'),
    'CURRENT_ASSETS': ('流动资产合计', 14, 'ASSET'),
    'FIXED_ASSETS': ('固定资产', 22, 'ASSET'),
    'INTANGIBLE_ASSETS': ('无形资产', 27, 'ASSET'),
    'LONG_TERM_DEFERRED_EXPENSES': ('长期待摊费用', 30, 'ASSET'),
    'NON_CURRENT_ASSETS': ('非流动资产合计', 33, 'ASSET'),
    'ASSETS': ('资产总计', 34, 'ASSET'),
    'SHORT_TERM_LOANS': ('短期借款', 35, 'LIABILITY'),
    'ACCOUNTS_PAYABLE': ('应付账款', 39, 'LIABILITY'),
    'EMPLOYEE_BENEFITS_PAYABLE': ('应付职工薪酬', 42, 'LIABILITY'),
    'TAXES_PAYABLE': ('应交税费', 43, 'LIABILITY'),
    'OTHER_PAYABLES': ('其他应付款', 44, 'LIABILITY'),
    'CURRENT_LIABILITIES': ('流动负债合计', 48, 'LIABILITY'),
    'LIABILITIES': ('负债合计', 58, 'LIABILITY'),
    'SHARE_CAPITAL': ('实收资本', 59, 'EQUITY'),
    'CAPITAL_RESERVE': ('资本公积', 60, 'EQUITY'),
    'SURPLUS_RESERVE': ('盈余公积', 64, 'EQUITY'),
    'RETAINED_EARNINGS': ('未分配利润', 65, 'EQUITY'),
    'EQUITY': ('所有者权益合计', 66, 'EQUITY'),
    'LIABILITIES_AND_EQUITY': ('负债和所有者权益总计', 67, 'LIABILITY_EQUITY'),
}

ASSE_META = {
    'CASH': ('货币资金', 1, 'ASSET'),
    'ACCOUNTS_RECEIVABLE': ('应收账款', 4, 'ASSET'),
    'INVENTORY': ('存货', 9, 'ASSET'),
    'OTHER_CURRENT_ASSETS': ('其他流动资产', 14, 'ASSET'),
    'CURRENT_ASSETS': ('流动资产合计', 15, 'ASSET'),
    'FIXED_ASSETS_NET': ('固定资产', 20, 'ASSET'),
    'NON_CURRENT_ASSETS': ('非流动资产合计', 29, 'ASSET'),
    'ASSETS': ('资产合计', 30, 'ASSET'),
    'SHORT_TERM_LOANS': ('短期借款', 31, 'LIABILITY'),
    'ACCOUNTS_PAYABLE': ('应付账款', 33, 'LIABILITY'),
    'EMPLOYEE_BENEFITS_PAYABLE': ('应付职工薪酬', 35, 'LIABILITY'),
    'TAXES_PAYABLE': ('应交税费', 36, 'LIABILITY'),
    'OTHER_PAYABLES': ('其他应付款', 39, 'LIABILITY'),
    'CURRENT_LIABILITIES': ('流动负债合计', 41, 'LIABILITY'),
    'LIABILITIES': ('负债合计', 47, 'LIABILITY'),
    'SHARE_CAPITAL': ('实收资本', 48, 'EQUITY'),
    'CAPITAL_RESERVE': ('资本公积', 49, 'EQUITY'),
    'SURPLUS_RESERVE': ('盈余公积', 50, 'EQUITY'),
    'RETAINED_EARNINGS': ('未分配利润', 51, 'EQUITY'),
    'EQUITY': ('所有者权益合计', 52, 'EQUITY'),
    'LIABILITIES_AND_EQUITY': ('负债和所有者权益总计', 53, 'LIABILITY_EQUITY'),
}

CAS_META = {
    'operating_revenue': ('一、营业收入', 1, '一、营业收入'),
    'operating_cost': ('减：营业成本', 2, '一、营业收入'),
    'taxes_and_surcharges': ('税金及附加', 3, '一、营业收入'),
    'selling_expense': ('销售费用', 4, '一、营业收入'),
    'administrative_expense': ('管理费用', 5, '一、营业收入'),
    'rd_expense': ('研发费用', 6, '一、营业收入'),
    'financial_expense': ('财务费用', 7, '一、营业收入'),
    'interest_expense': ('其中：利息费用', 8, '一、营业收入'),
    'interest_income': ('利息收入', 9, '一、营业收入'),
    'other_gains': ('加：其他收益', 10, '一、营业收入'),
    'investment_income': ('投资收益', 11, '一、营业收入'),
    'investment_income_associates': ('其中：对联营企业和合营企业的投资收益', 12, '一、营业收入'),
    'amortized_cost_termination_income': ('以摊余成本计量的金融资产终止确认收益', 13, '一、营业收入'),
    'net_exposure_hedge_income': ('净敞口套期收益', 14, '一、营业收入'),
    'fair_value_change_income': ('公允价值变动收益', 15, '一、营业收入'),
    'credit_impairment_loss': ('信用减值损失', 16, '一、营业收入'),
    'asset_impairment_loss': ('资产减值损失', 17, '一、营业收入'),
    'asset_disposal_gains': ('资产处置收益', 18, '一、营业收入'),
    'operating_profit': ('二、营业利润', 19, '二、营业利润'),
    'non_operating_income': ('加：营业外收入', 20, '二、营业利润'),
    'non_operating_expense': ('减：营业外支出', 21, '二、营业利润'),
    'total_profit': ('三、利润总额', 22, '三、利润总额'),
    'income_tax_expense': ('减：所得税费用', 23, '三、利润总额'),
    'net_profit': ('四、净利润', 24, '四、净利润'),
    'continued_ops_net_profit': ('（一）持续经营净利润', 25, '四、净利润'),
    'discontinued_ops_net_profit': ('（二）终止经营净利润', 26, '四、净利润'),
    'other_comprehensive_income_net': ('五、其他综合收益的税后净额', 27, '五、其他综合收益'),
    'oci_not_reclassifiable': ('（一）不能重分类进损益的其他综合收益', 28, '五、其他综合收益'),
    'oci_reclassifiable': ('（二）将重分类进损益的其他综合收益', 29, '五、其他综合收益'),
    'comprehensive_income_total': ('六、综合收益总额', 30, '六、综合收益总额'),
}

SAS_META = {
    'operating_revenue': ('一、营业收入', 1, '一、营业收入'),
    'operating_cost': ('减：营业成本', 2, '一、营业收入'),
    'taxes_and_surcharges': ('税金及附加', 3, '一、营业收入'),
    'consumption_tax': ('其中：消费税', 4, '一、营业收入'),
    'city_maintenance_tax': ('城市维护建设税', 5, '一、营业收入'),
    'education_surcharge': ('教育费附加', 6, '一、营业收入'),
    'selling_expense': ('销售费用', 7, '一、营业收入'),
    'advertising_expense': ('其中：商品维修费', 8, '一、营业收入'),
    'administrative_expense': ('管理费用', 9, '一、营业收入'),
    'business_entertainment_expense': ('其中：业务招待费', 10, '一、营业收入'),
    'financial_expense': ('财务费用', 11, '一、营业收入'),
    'interest_expense_net': ('其中：利息费用（净额）', 12, '一、营业收入'),
    'investment_income': ('加：投资收益', 13, '一、营业收入'),
    'operating_profit': ('二、营业利润', 14, '二、营业利润'),
    'non_operating_income': ('加：营业外收入', 15, '二、营业利润'),
    'government_grant': ('其中：政府补助', 16, '二、营业利润'),
    'non_operating_expense': ('减：营业外支出', 17, '二、营业利润'),
    'total_profit': ('三、利润总额', 18, '三、利润总额'),
    'income_tax_expense': ('减：所得税费用', 19, '三、利润总额'),
    'net_profit': ('四、净利润', 20, '四、净利润'),
}

CAS_CF_META = {
    'operating_inflow_sales': ('销售商品、提供劳务收到的现金', 1, '经营活动'),
    'operating_inflow_tax_refund': ('收到的税费返还', 2, '经营活动'),
    'operating_inflow_other': ('收到其他与经营活动有关的现金', 3, '经营活动'),
    'operating_inflow_subtotal': ('经营活动现金流入小计', 4, '经营活动'),
    'operating_outflow_purchase': ('购买商品、接受劳务支付的现金', 5, '经营活动'),
    'operating_outflow_labor': ('支付给职工以及为职工支付的现金', 6, '经营活动'),
    'operating_outflow_tax': ('支付的各项税费', 7, '经营活动'),
    'operating_outflow_other': ('支付其他与经营活动有关的现金', 8, '经营活动'),
    'operating_outflow_subtotal': ('经营活动现金流出小计', 9, '经营活动'),
    'operating_net_cash': ('经营活动产生的现金流量净额', 10, '经营活动'),
    'investing_inflow_sale_investment': ('收回投资收到的现金', 11, '投资活动'),
    'investing_inflow_returns': ('取得投资收益收到的现金', 12, '投资活动'),
    'investing_inflow_disposal_assets': ('处置固定资产收回的现金净额', 13, '投资活动'),
    'investing_inflow_disposal_subsidiary': ('处置子公司收到的现金净额', 14, '投资活动'),
    'investing_inflow_other': ('收到其他与投资活动有关的现金', 15, '投资活动'),
    'investing_inflow_subtotal': ('投资活动现金流入小计', 16, '投资活动'),
    'investing_outflow_purchase_assets': ('购建固定资产支付的现金', 17, '投资活动'),
    'investing_outflow_purchase_investment': ('投资支付的现金', 18, '投资活动'),
    'investing_outflow_acquire_subsidiary': ('取得子公司支付的现金净额', 19, '投资活动'),
    'investing_outflow_other': ('支付其他与投资活动有关的现金', 20, '投资活动'),
    'investing_outflow_subtotal': ('投资活动现金流出小计', 21, '投资活动'),
    'investing_net_cash': ('投资活动产生的现金流量净额', 22, '投资活动'),
    'financing_inflow_capital': ('吸收投资收到的现金', 23, '筹资活动'),
    'financing_inflow_borrowing': ('取得借款收到的现金', 24, '筹资活动'),
    'financing_inflow_other': ('收到其他与筹资活动有关的现金', 25, '筹资活动'),
    'financing_inflow_subtotal': ('筹资活动现金流入小计', 26, '筹资活动'),
    'financing_outflow_debt_repayment': ('偿还债务支付的现金', 27, '筹资活动'),
    'financing_outflow_dividend_interest': ('分配股利、利润或偿付利息支付的现金', 28, '筹资活动'),
    'financing_outflow_other': ('支付其他与筹资活动有关的现金', 29, '筹资活动'),
    'financing_outflow_subtotal': ('筹资活动现金流出小计', 30, '筹资活动'),
    'financing_net_cash': ('筹资活动产生的现金流量净额', 31, '筹资活动'),
    'fx_impact': ('汇率变动对现金及现金等价物的影响', 32, '汇总'),
    'net_increase_cash': ('现金及现金等价物净增加额', 33, '汇总'),
    'beginning_cash': ('期初现金及现金等价物余额', 34, '汇总'),
    'ending_cash': ('期末现金及现金等价物余额', 35, '汇总'),
}

SAS_CF_META = {
    'operating_receipts_sales': ('销售产成品、商品、提供劳务收到的现金', 1, '经营活动'),
    'operating_receipts_other': ('收到其他与经营活动有关的现金', 2, '经营活动'),
    'operating_payments_purchase': ('购买原材料、商品、接受劳务支付的现金', 3, '经营活动'),
    'operating_payments_staff': ('支付的职工薪酬', 4, '经营活动'),
    'operating_payments_tax': ('支付的税费', 5, '经营活动'),
    'operating_payments_other': ('支付其他与经营活动有关的现金', 6, '经营活动'),
    'operating_net_cash': ('经营活动产生的现金流量净额', 7, '经营活动'),
    'investing_receipts_disposal_investment': ('收回投资收到的现金', 8, '投资活动'),
    'investing_receipts_returns': ('取得投资收益收到的现金', 9, '投资活动'),
    'investing_receipts_disposal_assets': ('处置固定资产收回的现金净额', 10, '投资活动'),
    'investing_payments_purchase_investment': ('投资支付的现金', 11, '投资活动'),
    'investing_payments_purchase_assets': ('购建固定资产支付的现金', 12, '投资活动'),
    'investing_net_cash': ('投资活动产生的现金流量净额', 13, '投资活动'),
    'financing_receipts_borrowing': ('取得借款收到的现金', 14, '筹资活动'),
    'financing_receipts_capital': ('吸收投资者投资收到的现金', 15, '筹资活动'),
    'financing_payments_debt_principal': ('偿还借款本金支付的现金', 16, '筹资活动'),
    'financing_payments_debt_interest': ('偿还借款利息支付的现金', 17, '筹资活动'),
    'financing_payments_dividend': ('分配利润支付的现金', 18, '筹资活动'),
    'financing_net_cash': ('筹资活动产生的现金流量净额', 19, '筹资活动'),
    'net_increase_cash': ('现金净增加额', 20, '汇总'),
    'beginning_cash': ('期初现金余额', 21, '汇总'),
    'ending_cash': ('期末现金余额', 22, '汇总'),
}


# ============================================================
# 1. 纳税人信息
# ============================================================
def _insert_taxpayers(cur):
    for c in COMPANIES:
        cur.execute(
            """INSERT OR REPLACE INTO taxpayer_info
            (taxpayer_id, taxpayer_name, taxpayer_type, registration_type,
             legal_representative, establish_date, industry_code, industry_name,
             tax_authority_code, tax_authority_name, tax_bureau_level,
             region_code, region_name, credit_grade_current, credit_grade_year,
             accounting_standard, status,
             registered_capital, registered_address, business_scope,
             operating_status, collection_method)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (c['taxpayer_id'], c['taxpayer_name'], c['taxpayer_type'],
             c['registration_type'], c['legal_representative'], c['establish_date'],
             c['industry_code'], c['industry_name'],
             c['tax_authority_code'], c['tax_authority_name'], c['tax_bureau_level'],
             c['region_code'], c['region_name'],
             c['credit_grade_current'], c['credit_grade_year'],
             c['accounting_standard'], 'active',
             c['registered_capital'], c['registered_address'], c['business_scope'],
             c['operating_status'], c['collection_method'])
        )
    print(f"  纳税人: {len(COMPANIES)} 户")


# ============================================================
# 2. VAT 一般纳税人
# ============================================================
def _insert_general_vat(cur, co):
    tid = co['taxpayer_id']
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []
    cum_sales = cum_output = cum_input = cum_transfer = cum_tax = 0

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])

        sales = round(co['base_revenue'] * f)
        output = round(sales * 0.13)
        inp = round(output * 0.73)
        transfer = round(inp * 0.02)
        tax_payable = output - inp + transfer
        if tax_payable < 0:
            tax_payable = 0

        if month == 1:
            cum_sales = cum_output = cum_input = cum_transfer = cum_tax = 0
        cum_sales += sales
        cum_output += output
        cum_input += inp
        cum_transfer += transfer
        cum_tax += tax_payable

        city_tax = round(tax_payable * 0.07)
        edu = round(tax_payable * 0.03)
        local_edu = round(tax_payable * 0.02)

        def _row(it, tr, rev, **kw):
            base = {k: None for k in [
                'sales_taxable_rate', 'sales_goods', 'sales_services',
                'sales_adjustment_check', 'sales_simple_method',
                'sales_simple_adjust_check', 'sales_export_credit_refund',
                'sales_tax_free', 'sales_tax_free_goods', 'sales_tax_free_services',
                'output_tax', 'input_tax', 'last_period_credit',
                'transfer_out', 'export_refund', 'tax_check_supplement',
                'deductible_total', 'actual_deduct', 'tax_payable', 'end_credit',
                'simple_tax', 'simple_tax_check_supplement', 'tax_reduction',
                'total_tax_payable', 'unpaid_begin', 'export_receipt_tax',
                'paid_current', 'prepaid_installment', 'prepaid_export_receipt',
                'paid_last_period', 'paid_arrears', 'unpaid_end', 'arrears',
                'supplement_refund', 'immediate_refund', 'unpaid_check_begin',
                'paid_check_current', 'unpaid_check_end',
                'city_maintenance_tax', 'education_surcharge', 'local_education_surcharge',
            ]}
            base.update(kw)
            vals = [base[c] for c in base]
            return (tid, year, month, it, tr, rev,
                    None, 'ETL_NEW4', None, '元', 1.0, *vals)

        rows.append(_row('一般项目', '本月', 0,
            sales_taxable_rate=sales, output_tax=output, input_tax=inp,
            transfer_out=transfer, tax_payable=tax_payable,
            total_tax_payable=tax_payable, end_credit=0,
            supplement_refund=tax_payable,
            city_maintenance_tax=city_tax, education_surcharge=edu,
            local_education_surcharge=local_edu))
        rows.append(_row('一般项目', '累计', 0,
            sales_taxable_rate=cum_sales, output_tax=cum_output,
            input_tax=cum_input, transfer_out=cum_transfer,
            tax_payable=cum_tax, total_tax_payable=cum_tax))
        rows.append(_row('即征即退项目', '本月', 0))
        rows.append(_row('即征即退项目', '累计', 0))

    placeholders = ','.join(['?'] * (11 + 41))
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_general VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 一般纳税人VAT: {len(rows)} 行")


# ============================================================
# 3. VAT 小规模纳税人
# ============================================================
def _insert_small_vat(cur, co):
    tid = co['taxpayer_id']
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []
    cum_sales = cum_tax = 0

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])

        sales = round(co['base_revenue'] * f)
        spec = round(sales * 0.6)
        other = sales - spec
        tax = round(sales * 0.03)

        if month == 1:
            cum_sales = cum_tax = 0
        cum_sales += sales
        cum_tax += tax

        city_tax = round(tax * 0.07)
        edu = round(tax * 0.03)
        local_edu = round(tax * 0.02)

        def _row(it, tr, rev, **kw):
            base = {k: None for k in [
                'sales_3percent', 'sales_3percent_invoice_spec',
                'sales_3percent_invoice_other', 'sales_5percent',
                'sales_5percent_invoice_spec', 'sales_5percent_invoice_other',
                'sales_used_assets', 'sales_used_assets_invoice_other',
                'sales_tax_free', 'sales_tax_free_micro',
                'sales_tax_free_threshold', 'sales_tax_free_other',
                'sales_export_tax_free', 'sales_export_tax_free_invoice_other',
                'tax_due_current', 'tax_due_reduction',
                'tax_free_amount', 'tax_free_micro', 'tax_free_threshold',
                'tax_due_total', 'tax_prepaid', 'tax_supplement_refund',
                'city_maintenance_tax', 'education_surcharge', 'local_education_surcharge',
            ]}
            base.update(kw)
            vals = [base[c] for c in base]
            return (tid, year, month, it, tr, rev,
                    None, 'ETL_NEW4', None, '元', 1.0, *vals)

        rows.append(_row('货物及劳务', '本期', 0,
            sales_3percent=sales, sales_3percent_invoice_spec=spec,
            sales_3percent_invoice_other=other,
            tax_due_current=tax, tax_due_total=tax, tax_prepaid=0,
            tax_supplement_refund=tax,
            city_maintenance_tax=city_tax, education_surcharge=edu,
            local_education_surcharge=local_edu))
        rows.append(_row('货物及劳务', '累计', 0,
            sales_3percent=cum_sales, tax_due_current=cum_tax,
            tax_due_total=cum_tax, tax_supplement_refund=cum_tax))
        rows.append(_row('服务不动产无形资产', '本期', 0))
        rows.append(_row('服务不动产无形资产', '累计', 0))

    placeholders = ','.join(['?'] * (11 + 25))
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_small VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 小规模纳税人VAT: {len(rows)} 行")


# ============================================================
# 4. EIT 企业所得税
# ============================================================
def _insert_eit(cur, co):
    """年度汇算清缴 + 季度预缴"""
    tid = co['taxpayer_id']
    gr = co['growth_rate']
    base_rev = co['base_revenue'] * 12  # 年化基准

    for year in range(co['start_year'], co['end_year'] + 1):
        year_offset = (year - 2025)
        yf = (1 + gr) ** (year_offset * 12)
        annual_rev = round(base_rev * yf)
        annual_cost = round(annual_rev * co['cost_ratio'])

        # 年度汇算清缴
        filing_id = f'{tid}_{year}_0'
        cur.execute(
            """INSERT OR REPLACE INTO eit_annual_filing
            (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
             preparer, submitted_at, etl_batch_id, etl_confidence)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (filing_id, tid, year, 0, '元', co['legal_representative'],
             f'{year+1}-05-15', 'ETL_NEW4', 1.0)
        )
        cur.execute(
            """INSERT OR REPLACE INTO eit_annual_basic_info
            (filing_id, tax_return_type_code, asset_avg, employee_avg, industry_code,
             restricted_or_prohibited, small_micro_enterprise, listed_company)
            VALUES (?,?,?,?,?,?,?,?)""",
            (filing_id, 'A', round(co['asset_base'] * yf / 10000),
             co['employee_count'], co['industry_code'], 0, 0, '否')
        )

        # A100000 计算
        taxes_sur = round(annual_rev * 0.025)
        sell_exp = round(annual_rev * 0.05)
        admin_exp = round(annual_rev * 0.08)
        rd_exp = round(annual_rev * 0.06)
        fin_exp = round(annual_rev * 0.01)
        other_gains = round(annual_rev * 0.005)
        inv_income = round(annual_rev * 0.008)
        credit_imp = round(annual_rev * -0.003)
        asset_imp = round(annual_rev * -0.002)
        asset_disp = round(annual_rev * 0.001)

        op_profit = (annual_rev - annual_cost - taxes_sur - sell_exp - admin_exp
                     - rd_exp - fin_exp + other_gains + inv_income
                     + credit_imp + asset_imp + asset_disp)
        non_op_inc = round(annual_rev * 0.004)
        non_op_exp = round(annual_rev * 0.002)
        total_profit = op_profit + non_op_inc - non_op_exp

        tax_adjust_inc = round(total_profit * 0.06)
        tax_adjust_dec = round(total_profit * 0.015)
        adjusted = total_profit + tax_adjust_inc - tax_adjust_dec
        taxable_income = max(adjusted, 0)
        tax_rate = 0.25
        tax_payable = round(taxable_income * tax_rate)
        prepaid = round(tax_payable * 0.8)
        final = tax_payable - prepaid

        cur.execute(
            """INSERT OR REPLACE INTO eit_annual_main
            (filing_id, revenue, cost, taxes_surcharges, selling_expenses, admin_expenses,
             rd_expenses, financial_expenses, other_gains, investment_income,
             net_exposure_hedge_gains, fair_value_change_gains,
             credit_impairment_loss, asset_impairment_loss, asset_disposal_gains,
             operating_profit, non_operating_income, non_operating_expenses, total_profit,
             less_foreign_income, add_tax_adjust_increase, less_tax_adjust_decrease,
             exempt_income_deduction_total, add_foreign_tax_offset, adjusted_taxable_income,
             less_income_exemption, less_losses_carried_forward, less_taxable_income_deduction,
             taxable_income, tax_rate, tax_payable,
             tax_credit_total, less_foreign_tax_credit, tax_due,
             add_foreign_tax_due, less_foreign_tax_credit_amount, actual_tax_payable,
             less_prepaid_tax, tax_payable_or_refund,
             hq_share, fiscal_central_share, hq_dept_share,
             less_ethnic_autonomous_relief, less_audit_adjustment, less_special_adjustment,
             final_tax_payable_or_refund)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (filing_id,
             annual_rev, annual_cost, taxes_sur, sell_exp, admin_exp,
             rd_exp, fin_exp, other_gains, inv_income,
             0, 0, credit_imp, asset_imp, asset_disp,
             op_profit, non_op_inc, non_op_exp, total_profit,
             0, tax_adjust_inc, tax_adjust_dec, 0, 0, adjusted,
             0, 0, 0, taxable_income,
             tax_rate, tax_payable,
             0, 0, tax_payable,
             0, 0, tax_payable,
             prepaid, final,
             0, 0, 0,
             0, 0, 0, final)
        )

        # 季度预缴 Q1-Q4
        for q in range(1, 5):
            q_end_month = q * 3
            fid = f'{tid}_{year}Q{q}_0'
            q_rev = round(annual_rev * q / 4)
            q_cost = round(annual_cost * q / 4)
            q_profit = round(total_profit * q / 4)
            q_tax = round(q_profit * tax_rate)

            cur.execute(
                """INSERT OR REPLACE INTO eit_quarter_filing
                (filing_id, taxpayer_id, period_year, period_quarter, revision_no,
                 amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (fid, tid, year, q, 0, '元', co['legal_representative'],
                 f'{year}-{q_end_month+1:02d}-15', 'ETL_NEW4', 1.0)
            )
            cur.execute(
                """INSERT OR REPLACE INTO eit_quarter_main
                (filing_id, employee_quarter_avg, asset_quarter_avg,
                 restricted_or_prohibited_industry, small_micro_enterprise,
                 revenue, cost, total_profit,
                 add_specific_business_taxable_income, less_non_taxable_income,
                 less_accelerated_depreciation, tax_free_income_deduction_total,
                 income_exemption_total, less_losses_carried_forward,
                 actual_profit, tax_rate, tax_payable,
                 tax_credit_total, less_prepaid_tax_current_year,
                 less_specific_business_prepaid, current_tax_payable_or_refund,
                 hq_share_total, hq_share, fiscal_central_share,
                 hq_business_dept_share, branch_share_ratio, branch_share_amount,
                 ethnic_autonomous_relief_amount, final_tax_payable_or_refund)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fid, co['employee_count'], round(co['asset_base'] * yf / 10000),
                 0, 0, q_rev, q_cost, q_profit,
                 0, 0, 0, 0, 0, 0,
                 q_profit, tax_rate, q_tax,
                 0, 0, 0, q_tax,
                 0, 0, 0, 0, 0, 0, 0, q_tax)
            )

    print(f"  {co['short_name']} EIT: {co['end_year'] - co['start_year'] + 1} 年度 + 季度")


# ============================================================
# 5. 科目余额
# ============================================================
def _insert_account_balance(cur, co):
    tid = co['taxpayer_id']
    is_general = co['taxpayer_type'] == '一般纳税人'
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []

    cum_rev = cum_cost = cum_admin = cum_fin = cum_sell = cum_profit = 0

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])
        prev_f = _monthly_factor(offset - 1, co['growth_rate'], co['seasonal_amp'])

        rev_m = round(co['base_revenue'] * f)
        cost_m = round(rev_m * co['cost_ratio'])
        admin_m = round(rev_m * 0.08)
        fin_m = round(rev_m * 0.01)
        sell_m = round(rev_m * 0.05)

        if month == 1:
            cum_rev = cum_cost = cum_admin = cum_fin = cum_sell = cum_profit = 0
        cum_rev += rev_m
        cum_cost += cost_m
        cum_admin += admin_m
        cum_fin += fin_m
        cum_sell += sell_m
        cum_profit += (rev_m - cost_m - admin_m - fin_m - sell_m)

        cash = round(co['asset_base'] * 0.05 * f)
        bank = round(co['asset_base'] * 0.25 * f)
        ar = round(co['asset_base'] * 0.08 * f)
        inv = round(co['asset_base'] * 0.05 * f)
        ap = round(co['asset_base'] * 0.06 * f)
        emp_pay = round(co['asset_base'] * 0.03 * f)

        if is_general:
            vat_tax = round(rev_m * 0.13 * 0.27)
            accts = [
                ('1001', round(cash * prev_f / f), round(20000 * f), round(15000 * f), cash),
                ('1002', round(bank * prev_f / f), round(rev_m * 1.2), round(rev_m * 0.85), bank),
                ('1122', round(ar * prev_f / f), rev_m, round(rev_m * 0.8), ar),
                ('1403', round(inv * prev_f / f), round(cost_m * 0.3), round(cost_m * 0.28), inv),
                ('1601', round(co['asset_base'] * 0.5), 0, 0, round(co['asset_base'] * 0.5)),
                ('1602', round(co['asset_base'] * 0.1 + 50000 * max(0, offset)),
                 0, 50000, round(co['asset_base'] * 0.1 + 50000 * max(0, offset + 1))),
                ('1701', round(co['asset_base'] * 0.1), 0, 0, round(co['asset_base'] * 0.1)),
                ('1702', round(co['asset_base'] * 0.02 + 20000 * max(0, offset)),
                 0, 20000, round(co['asset_base'] * 0.02 + 20000 * max(0, offset + 1))),
                ('2202', round(ap * prev_f / f), round(ap * 0.8), round(ap * 1.2), ap),
                ('2211', round(emp_pay * prev_f / f), round(emp_pay * 0.9), round(emp_pay * 1.2), emp_pay),
                ('2221', round(vat_tax * prev_f / f), round(vat_tax), round(vat_tax * 0.9), round(vat_tax * 0.9)),
                ('222101', round(vat_tax * 0.5 * prev_f / f), round(rev_m * 0.13 * 0.73),
                 round(rev_m * 0.13), round(vat_tax * 0.5)),
                ('4001', co['share_capital'], 0, 0, co['share_capital']),
                ('4002', co['capital_reserve'], 0, 0, co['capital_reserve']),
                ('4103', round(cum_profit - (rev_m - cost_m - admin_m - fin_m - sell_m)),
                 0, round(rev_m - cost_m - admin_m - fin_m - sell_m), round(cum_profit)),
                ('6001', round(cum_rev - rev_m), 0, rev_m, cum_rev),
                ('6401', round(cum_cost - cost_m), cost_m, 0, cum_cost),
                ('6602', round(cum_admin - admin_m), admin_m, 0, cum_admin),
                ('6603', round(cum_fin - fin_m), fin_m, 0, cum_fin),
                ('6601', round(cum_sell - sell_m), sell_m, 0, cum_sell),
            ]
        else:
            accts = [
                ('1001', round(cash * prev_f / f), round(10000 * f), round(8000 * f), cash),
                ('1002', round(bank * prev_f / f), round(rev_m * 1.1), round(rev_m * 0.9), bank),
                ('1122', round(ar * prev_f / f), rev_m, round(rev_m * 0.75), ar),
                ('1405', round(inv * prev_f / f), round(cost_m * 0.35), round(cost_m * 0.33), inv),
                ('2202', round(ap * prev_f / f), round(ap * 0.8), round(ap * 1.3), ap),
                ('2211', round(emp_pay * prev_f / f), round(emp_pay * 0.85), round(emp_pay * 1.15), emp_pay),
                ('2221', round(rev_m * 0.03 * prev_f / f), round(rev_m * 0.03),
                 round(rev_m * 0.03 * 0.9), round(rev_m * 0.03 * 0.9)),
                ('4001', co['share_capital'], 0, 0, co['share_capital']),
                ('4103', 0, 0, round((rev_m - cost_m - admin_m - fin_m - sell_m) * 0.9),
                 round((rev_m - cost_m - admin_m - fin_m - sell_m) * 0.9)),
                ('6001', 0, 0, rev_m, rev_m),
                ('6401', 0, cost_m, 0, cost_m),
                ('5602', 0, round(sell_m * 0.8), 0, round(sell_m * 0.8)),
                ('6603', 0, fin_m, 0, fin_m),
            ]

        for code, opening, debit, credit, closing in accts:
            rows.append((tid, year, month, code, 0,
                         None, 'ETL_NEW4', None, '元', 1.0,
                         opening, debit, credit, closing))

    placeholders = ','.join(['?'] * 14)
    cur.executemany(f"INSERT OR REPLACE INTO account_balance VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 科目余额: {len(rows)} 行")


# ============================================================
# 6. 资产负债表
# ============================================================
def _insert_balance_sheet(cur, co):
    tid = co['taxpayer_id']
    gaap = co['gaap_bs']
    meta = ASBE_META if gaap == 'ASBE' else ASSE_META
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])
        bf = _monthly_factor(_month_offset(year, 1), co['growth_rate'], 0.0)

        ab = co['asset_base']
        sc = co['share_capital']
        cp = co['capital_reserve']
        sr = co['surplus_reserve']

        # 期末
        cash_e = round(ab * 0.30 * f)
        ar_e = round(ab * 0.08 * f * 1.1)
        inv_e = round(ab * 0.05 * f)
        other_ca = round(ab * 0.01)
        prep_e = round(ab * 0.01) if gaap == 'ASBE' else 0
        other_recv = round(ab * 0.005) if gaap == 'ASBE' else 0

        if gaap == 'ASBE':
            fixed_e = round(ab * 0.5 - 50000 * max(0, offset + 1))
            intang_e = round(ab * 0.1 - 20000 * max(0, offset + 1))
            fixed_e = max(fixed_e, round(ab * 0.2))
            intang_e = max(intang_e, round(ab * 0.03))
            ltde = round(ab * 0.005)
            ca_e = cash_e + ar_e + prep_e + other_recv + inv_e + other_ca
            nca_e = fixed_e + intang_e + ltde
        else:
            fixed_net_e = round(ab * 0.3 - 40000 * max(0, offset + 1))
            fixed_net_e = max(fixed_net_e, round(ab * 0.1))
            ca_e = cash_e + ar_e + inv_e + other_ca
            nca_e = fixed_net_e

        ta_e = ca_e + nca_e

        short_loans_e = round(ab * 0.05 * f) if offset >= 6 else 0
        ap_e = round(ab * 0.06 * f)
        emp_e = round(ab * 0.03 * f)
        tax_e = round(ab * 0.008 * f)
        other_pay = round(ab * 0.01)
        cl_e = short_loans_e + ap_e + emp_e + tax_e + other_pay
        tl_e = cl_e
        eq_e = ta_e - tl_e
        re_e = eq_e - sc - cp - sr

        # 年初
        cash_b = round(ab * 0.30 * bf)
        ar_b = round(ab * 0.08 * bf * 1.1)
        inv_b = round(ab * 0.05 * bf)
        if gaap == 'ASBE':
            fixed_b = round(ab * 0.5 - 50000 * max(0, _month_offset(year, 1)))
            intang_b = round(ab * 0.1 - 20000 * max(0, _month_offset(year, 1)))
            fixed_b = max(fixed_b, round(ab * 0.2))
            intang_b = max(intang_b, round(ab * 0.03))
            ca_b = cash_b + ar_b + prep_e + other_recv + inv_b + other_ca
            nca_b = fixed_b + intang_b + ltde
        else:
            fixed_net_b = round(ab * 0.3 - 40000 * max(0, _month_offset(year, 1)))
            fixed_net_b = max(fixed_net_b, round(ab * 0.1))
            ca_b = cash_b + ar_b + inv_b + other_ca
            nca_b = fixed_net_b

        ta_b = ca_b + nca_b
        sl_b = round(ab * 0.05 * bf) if _month_offset(year, 1) >= 6 else 0
        ap_b = round(ab * 0.06 * bf)
        emp_b = round(ab * 0.03 * bf)
        tax_b = round(ab * 0.008 * bf)
        cl_b = sl_b + ap_b + emp_b + tax_b + other_pay
        tl_b = cl_b
        eq_b = ta_b - tl_b
        re_b = eq_b - sc - cp - sr

        if gaap == 'ASBE':
            end_data = {
                'CASH': cash_e, 'ACCOUNTS_RECEIVABLE': ar_e, 'PREPAYMENTS': prep_e,
                'OTHER_RECEIVABLES': other_recv, 'INVENTORY': inv_e,
                'OTHER_CURRENT_ASSETS': other_ca, 'CURRENT_ASSETS': ca_e,
                'FIXED_ASSETS': fixed_e, 'INTANGIBLE_ASSETS': intang_e,
                'LONG_TERM_DEFERRED_EXPENSES': ltde,
                'NON_CURRENT_ASSETS': nca_e, 'ASSETS': ta_e,
                'SHORT_TERM_LOANS': short_loans_e,
                'ACCOUNTS_PAYABLE': ap_e, 'EMPLOYEE_BENEFITS_PAYABLE': emp_e,
                'TAXES_PAYABLE': tax_e, 'OTHER_PAYABLES': other_pay,
                'CURRENT_LIABILITIES': cl_e, 'LIABILITIES': tl_e,
                'SHARE_CAPITAL': sc, 'CAPITAL_RESERVE': cp,
                'SURPLUS_RESERVE': sr, 'RETAINED_EARNINGS': re_e,
                'EQUITY': eq_e, 'LIABILITIES_AND_EQUITY': ta_e,
            }
            begin_data = {
                'CASH': cash_b, 'ACCOUNTS_RECEIVABLE': ar_b, 'PREPAYMENTS': prep_e,
                'OTHER_RECEIVABLES': other_recv, 'INVENTORY': inv_b,
                'OTHER_CURRENT_ASSETS': other_ca, 'CURRENT_ASSETS': ca_b,
                'FIXED_ASSETS': fixed_b, 'INTANGIBLE_ASSETS': intang_b,
                'LONG_TERM_DEFERRED_EXPENSES': ltde,
                'NON_CURRENT_ASSETS': nca_b, 'ASSETS': ta_b,
                'SHORT_TERM_LOANS': sl_b,
                'ACCOUNTS_PAYABLE': ap_b, 'EMPLOYEE_BENEFITS_PAYABLE': emp_b,
                'TAXES_PAYABLE': tax_b, 'OTHER_PAYABLES': other_pay,
                'CURRENT_LIABILITIES': cl_b, 'LIABILITIES': tl_b,
                'SHARE_CAPITAL': sc, 'CAPITAL_RESERVE': cp,
                'SURPLUS_RESERVE': sr, 'RETAINED_EARNINGS': re_b,
                'EQUITY': eq_b, 'LIABILITIES_AND_EQUITY': ta_b,
            }
        else:
            end_data = {
                'CASH': cash_e, 'ACCOUNTS_RECEIVABLE': ar_e, 'INVENTORY': inv_e,
                'OTHER_CURRENT_ASSETS': other_ca, 'CURRENT_ASSETS': ca_e,
                'FIXED_ASSETS_NET': fixed_net_e,
                'NON_CURRENT_ASSETS': nca_e, 'ASSETS': ta_e,
                'SHORT_TERM_LOANS': short_loans_e,
                'ACCOUNTS_PAYABLE': ap_e, 'EMPLOYEE_BENEFITS_PAYABLE': emp_e,
                'TAXES_PAYABLE': tax_e, 'OTHER_PAYABLES': other_pay,
                'CURRENT_LIABILITIES': cl_e, 'LIABILITIES': tl_e,
                'SHARE_CAPITAL': sc, 'CAPITAL_RESERVE': cp,
                'SURPLUS_RESERVE': sr, 'RETAINED_EARNINGS': re_e,
                'EQUITY': eq_e, 'LIABILITIES_AND_EQUITY': ta_e,
            }
            begin_data = {
                'CASH': cash_b, 'ACCOUNTS_RECEIVABLE': ar_b, 'INVENTORY': inv_b,
                'OTHER_CURRENT_ASSETS': other_ca, 'CURRENT_ASSETS': ca_b,
                'FIXED_ASSETS_NET': fixed_net_b,
                'NON_CURRENT_ASSETS': nca_b, 'ASSETS': ta_b,
                'SHORT_TERM_LOANS': sl_b,
                'ACCOUNTS_PAYABLE': ap_b, 'EMPLOYEE_BENEFITS_PAYABLE': emp_b,
                'TAXES_PAYABLE': tax_b, 'OTHER_PAYABLES': other_pay,
                'CURRENT_LIABILITIES': cl_b, 'LIABILITIES': tl_b,
                'SHARE_CAPITAL': sc, 'CAPITAL_RESERVE': cp,
                'SURPLUS_RESERVE': sr, 'RETAINED_EARNINGS': re_b,
                'EQUITY': eq_b, 'LIABILITIES_AND_EQUITY': ta_b,
            }

        for code, (name, line, section) in meta.items():
            rows.append((tid, year, month, gaap, code, 0,
                         None, 'ETL_NEW4', None, '元', 1.0,
                         begin_data.get(code, 0), end_data.get(code, 0),
                         name, line, section))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_balance_sheet_item VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 资产负债表({gaap}): {len(rows)} 行")


# ============================================================
# 7. 利润表
# ============================================================
def _insert_profit_statement(cur, co):
    tid = co['taxpayer_id']
    gaap = co['gaap_pl']
    meta = CAS_META if gaap == 'CAS' else SAS_META
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []
    cum = {}

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])

        if month == 1:
            cum = {k: 0 for k in meta}

        rev = round(co['base_revenue'] * f)
        cost = round(rev * co['cost_ratio'])
        tax_sur = round(rev * 0.025)
        sell = round(rev * 0.05)
        admin = round(rev * 0.08)
        fin = round(rev * 0.01)

        if gaap == 'CAS':
            rd = round(rev * 0.06)
            interest_exp = round(fin * 0.4)
            interest_inc = round(fin * 0.2)
            other_gains = round(rev * 0.005)
            inv_income = round(rev * 0.008)
            fv_change = round(rev * 0.004)
            credit_imp = round(rev * -0.003)
            asset_imp = round(rev * -0.002)
            asset_disp = round(rev * 0.001)

            op_profit = (rev - cost - tax_sur - sell - admin - rd - fin
                         + other_gains + inv_income + fv_change
                         + credit_imp + asset_imp + asset_disp)
            non_op_inc = round(rev * 0.004)
            non_op_exp = round(rev * 0.002)
            total_profit = op_profit + non_op_inc - non_op_exp
            income_tax = round(total_profit * 0.25)
            net = total_profit - income_tax
            oci = round(rev * 0.001)

            current = {
                'operating_revenue': rev, 'operating_cost': cost,
                'taxes_and_surcharges': tax_sur, 'selling_expense': sell,
                'administrative_expense': admin, 'rd_expense': rd,
                'financial_expense': fin, 'interest_expense': interest_exp,
                'interest_income': interest_inc, 'other_gains': other_gains,
                'investment_income': inv_income, 'investment_income_associates': 0,
                'amortized_cost_termination_income': 0, 'net_exposure_hedge_income': 0,
                'fair_value_change_income': fv_change, 'credit_impairment_loss': credit_imp,
                'asset_impairment_loss': asset_imp, 'asset_disposal_gains': asset_disp,
                'operating_profit': op_profit, 'non_operating_income': non_op_inc,
                'non_operating_expense': non_op_exp, 'total_profit': total_profit,
                'income_tax_expense': income_tax, 'net_profit': net,
                'continued_ops_net_profit': net, 'discontinued_ops_net_profit': 0,
                'other_comprehensive_income_net': oci, 'oci_not_reclassifiable': 0,
                'oci_reclassifiable': oci, 'comprehensive_income_total': net + oci,
            }
        else:
            inv_inc = round(rev * 0.008)
            op_profit = rev - cost - tax_sur - sell - admin - fin + inv_inc
            non_op_inc = round(rev * 0.004)
            non_op_exp = round(rev * 0.002)
            total_profit = op_profit + non_op_inc - non_op_exp
            income_tax = round(total_profit * 0.05)
            net = total_profit - income_tax

            current = {
                'operating_revenue': rev, 'operating_cost': cost,
                'taxes_and_surcharges': tax_sur, 'consumption_tax': tax_sur,
                'city_maintenance_tax': round(tax_sur * 0.3),
                'education_surcharge': round(tax_sur * 0.1),
                'selling_expense': sell, 'advertising_expense': round(sell * 0.3),
                'administrative_expense': admin,
                'business_entertainment_expense': round(admin * 0.05),
                'financial_expense': fin, 'interest_expense_net': fin,
                'investment_income': inv_inc, 'operating_profit': op_profit,
                'non_operating_income': non_op_inc, 'government_grant': non_op_inc,
                'non_operating_expense': non_op_exp,
                'total_profit': total_profit, 'income_tax_expense': income_tax,
                'net_profit': net,
            }

        for k in current:
            cum[k] = cum.get(k, 0) + current[k]

        for code in meta:
            m = meta[code]
            rows.append((tid, year, month, gaap, code, 0,
                         None, None, None, '元', None,
                         current.get(code, 0), cum.get(code, 0),
                         m[0], m[1], m[2]))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_income_statement_item VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 利润表({gaap}): {len(rows)} 行")


# ============================================================
# 8. 现金流量表
# ============================================================
def _insert_cash_flow(cur, co):
    tid = co['taxpayer_id']
    gaap = co['gaap_pl']
    is_cas = gaap == 'CAS'
    meta = CAS_CF_META if is_cas else SAS_CF_META
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])
    rows = []

    base_cash = round(co['asset_base'] * 0.30)
    cum_cf = {}
    prev_ending = base_cash

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])

        if month == 1:
            cum_cf = {}
            begin_year = round(base_cash * _monthly_factor(
                _month_offset(year - 1, 12), co['growth_rate'], 0.0))
            prev_ending = begin_year

        rev = round(co['base_revenue'] * f)

        if is_cas:
            op_sales = round(rev * 1.13)
            op_other = round(rev * 0.015)
            op_sub = op_sales + op_other
            op_purchase = round(rev * co['cost_ratio'] * 1.13 * 0.85)
            op_labor = round(rev * 0.10)
            op_tax = round(rev * 0.04)
            op_other_out = round(rev * 0.02)
            op_out_sub = op_purchase + op_labor + op_tax + op_other_out
            op_net = op_sub - op_out_sub

            inv_returns = round(rev * 0.002)
            inv_in_sub = inv_returns
            inv_out_assets = round(rev * 0.05)
            inv_out_sub = inv_out_assets
            inv_net = inv_in_sub - inv_out_sub

            fin_borrow = round(rev * 0.2)
            fin_in_sub = fin_borrow
            fin_debt = round(rev * 0.05)
            fin_interest = round(rev * 0.008)
            fin_out_sub = fin_debt + fin_interest
            fin_net = fin_in_sub - fin_out_sub

            net_inc = op_net + inv_net + fin_net
            begin = prev_ending
            end = begin + net_inc
            prev_ending = end

            current = {
                'operating_inflow_sales': op_sales, 'operating_inflow_tax_refund': 0,
                'operating_inflow_other': op_other, 'operating_inflow_subtotal': op_sub,
                'operating_outflow_purchase': op_purchase, 'operating_outflow_labor': op_labor,
                'operating_outflow_tax': op_tax, 'operating_outflow_other': op_other_out,
                'operating_outflow_subtotal': op_out_sub, 'operating_net_cash': op_net,
                'investing_inflow_sale_investment': 0, 'investing_inflow_returns': inv_returns,
                'investing_inflow_disposal_assets': 0, 'investing_inflow_disposal_subsidiary': 0,
                'investing_inflow_other': 0, 'investing_inflow_subtotal': inv_in_sub,
                'investing_outflow_purchase_assets': inv_out_assets,
                'investing_outflow_purchase_investment': 0,
                'investing_outflow_acquire_subsidiary': 0, 'investing_outflow_other': 0,
                'investing_outflow_subtotal': inv_out_sub, 'investing_net_cash': inv_net,
                'financing_inflow_capital': 0, 'financing_inflow_borrowing': fin_borrow,
                'financing_inflow_other': 0, 'financing_inflow_subtotal': fin_in_sub,
                'financing_outflow_debt_repayment': fin_debt,
                'financing_outflow_dividend_interest': fin_interest,
                'financing_outflow_other': 0, 'financing_outflow_subtotal': fin_out_sub,
                'financing_net_cash': fin_net,
                'fx_impact': 0, 'net_increase_cash': net_inc,
                'beginning_cash': begin, 'ending_cash': end,
            }
        else:
            op_sales = round(rev * 1.03)
            op_other = round(rev * 0.015)
            op_purchase = round(rev * co['cost_ratio'] * 0.9)
            op_staff = round(rev * 0.08)
            op_tax = round(rev * 0.025)
            op_other_out = round(rev * 0.02)
            op_net = op_sales + op_other - op_purchase - op_staff - op_tax - op_other_out

            inv_assets = round(rev * 0.015)
            inv_net = -inv_assets

            fin_borrow = round(rev * 0.06) if month % 3 == 0 else 0
            fin_debt = round(rev * 0.03) if month % 4 == 0 else 0
            fin_interest = round(rev * 0.005) if month % 4 == 0 else 0
            fin_net = fin_borrow - fin_debt - fin_interest

            net_inc = op_net + inv_net + fin_net
            begin = prev_ending
            end = begin + net_inc
            prev_ending = end

            current = {
                'operating_receipts_sales': op_sales, 'operating_receipts_other': op_other,
                'operating_payments_purchase': op_purchase, 'operating_payments_staff': op_staff,
                'operating_payments_tax': op_tax, 'operating_payments_other': op_other_out,
                'operating_net_cash': op_net,
                'investing_receipts_disposal_investment': 0, 'investing_receipts_returns': 0,
                'investing_receipts_disposal_assets': 0,
                'investing_payments_purchase_investment': 0,
                'investing_payments_purchase_assets': inv_assets,
                'investing_net_cash': inv_net,
                'financing_receipts_borrowing': fin_borrow, 'financing_receipts_capital': 0,
                'financing_payments_debt_principal': fin_debt,
                'financing_payments_debt_interest': fin_interest,
                'financing_payments_dividend': 0, 'financing_net_cash': fin_net,
                'net_increase_cash': net_inc, 'beginning_cash': begin, 'ending_cash': end,
            }

        if not cum_cf:
            cum_cf = dict(current)
        else:
            for k in current:
                if k == 'beginning_cash':
                    pass
                elif k == 'ending_cash':
                    cum_cf[k] = end
                else:
                    cum_cf[k] = cum_cf.get(k, 0) + current[k]

        for code in meta:
            m = meta[code]
            rows.append((tid, year, month, gaap, code, 0,
                         None, 'ETL_NEW4', None, '元', None,
                         current.get(code, 0), cum_cf.get(code, 0),
                         m[0], m[1], m[2]))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_cash_flow_item VALUES ({placeholders})", rows)
    print(f"  {co['short_name']} 现金流量表({gaap}): {len(rows)} 行")


# ============================================================
# 9. 发票数据
# ============================================================
def _insert_invoices(cur, co):
    tid = co['taxpayer_id']
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])

    sellers = [
        ('91310000MA1ABC1230', '上海明远电子有限公司'),
        ('91310000MA1DEF4560', '杭州恒通科技有限公司'),
        ('91310000MA1GHI7890', '上海快捷物流有限公司'),
        ('91310000MA1JKL0120', '北京中科软件集团'),
        ('91310000MA1MNO3450', '上海文汇办公用品有限公司'),
    ]
    buyers = [
        ('91310000MA1AAA1110', '上海锦程信息技术有限公司'),
        ('91310000MA1BBB2220', '杭州数联科技有限公司'),
        ('91310000MA1CCC3330', '苏州创新科技有限公司'),
        ('91310000MA1DDD4440', '广州智慧城市运营有限公司'),
        ('91310000MA1EEE5550', '南京东方数据有限公司'),
    ]

    p_cols = (
        'taxpayer_id, period_year, period_month, invoice_format, invoice_pk, line_no,'
        'invoice_code, invoice_number, digital_invoice_no,'
        'seller_tax_id, seller_name, buyer_tax_id, buyer_name,'
        'invoice_date, tax_category_code, special_business_type,'
        'goods_name, specification, unit, quantity, unit_price,'
        'amount, tax_rate, tax_amount, total_amount,'
        'invoice_source, invoice_type, invoice_status, is_positive, risk_level,'
        'issuer, remark, submitted_at, etl_batch_id'
    )
    s_cols = (
        'taxpayer_id, period_year, period_month, invoice_format, invoice_pk, line_no,'
        'invoice_code, invoice_number, digital_invoice_no,'
        'seller_tax_id, seller_name, buyer_tax_id, buyer_name,'
        'invoice_date, amount, tax_amount, total_amount,'
        'invoice_source, invoice_type, invoice_status, is_positive, risk_level,'
        'issuer, remark, submitted_at, etl_batch_id'
    )

    purchase_rows = []
    sales_rows = []
    is_general = co['taxpayer_type'] == '一般纳税人'

    for year, month in months:
        offset = _month_offset(year, month)
        f = _monthly_factor(offset, co['growth_rate'], co['seasonal_amp'])
        base_amt = round(co['base_revenue'] * 0.02 * f)

        # 每月3张进项 + 3张销项
        for i in range(3):
            seller = sellers[i % len(sellers)]
            pk = f'{tid[-4:]}{year}{month:02d}P{i+1:03d}'
            amt = round(base_amt * (1 + i * 0.4))
            rate_str = '13%' if is_general and i < 2 else ('6%' if is_general else '3%')
            rate_val = 0.13 if is_general and i < 2 else (0.06 if is_general else 0.03)
            tax_amt = round(amt * rate_val)
            qty = max(1, round(amt / 500))
            up = round(amt / qty, 2) if qty > 0 else amt
            day = min(28, (i + 1) * 8)

            purchase_rows.append((
                tid, year, month, '数电', pk, 1,
                None, None, pk,
                seller[0], seller[1], tid, co['taxpayer_name'],
                f'{year}-{month:02d}-{day:02d}', '1090511', None,
                f'商品{i+1}', f'SPEC-{i+1}', '个', qty, up,
                amt, rate_str, tax_amt, amt + tax_amt,
                '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
                co['legal_representative'], None,
                f'{year}-{month:02d}-{day+1:02d} 10:00:00', 'ETL_NEW4'
            ))

        for i in range(3):
            buyer = buyers[i % len(buyers)]
            pk = f'{tid[-4:]}{year}{month:02d}S{i+1:03d}'
            amt = round(base_amt * 1.5 * (1 + i * 0.5))
            rate_val = 0.13 if is_general and i < 2 else (0.06 if is_general else 0.03)
            tax_amt = round(amt * rate_val)
            day = min(28, (i + 1) * 7)

            sales_rows.append((
                tid, year, month, '数电', pk, 1,
                None, None, pk,
                tid, co['taxpayer_name'], buyer[0], buyer[1],
                f'{year}-{month:02d}-{day:02d}',
                amt, tax_amt, amt + tax_amt,
                '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
                co['legal_representative'], None,
                f'{year}-{month:02d}-{day+1:02d} 10:00:00', 'ETL_NEW4'
            ))

    p_ph = ','.join(['?'] * 34)
    s_ph = ','.join(['?'] * 26)
    cur.executemany(f"INSERT OR REPLACE INTO inv_spec_purchase ({p_cols}) VALUES ({p_ph})", purchase_rows)
    cur.executemany(f"INSERT OR REPLACE INTO inv_spec_sales ({s_cols}) VALUES ({s_ph})", sales_rows)
    print(f"  {co['short_name']} 发票: 进项{len(purchase_rows)}张 + 销项{len(sales_rows)}张")


# ============================================================
# 10. 画像快照 + 信用等级
# ============================================================
def _insert_profile_and_credit(cur, co):
    tid = co['taxpayer_id']
    months = _gen_months(co['start_year'], co['start_month'], co['end_year'], co['end_month'])

    emp_count = co['employee_count']
    if emp_count <= 10:
        emp_scale = '1-10'
    elif emp_count <= 50:
        emp_scale = '11-50'
    elif emp_count <= 100:
        emp_scale = '51-100'
    elif emp_count <= 300:
        emp_scale = '101-300'
    else:
        emp_scale = '300以上'

    base_annual_rev = co['base_revenue'] * 12
    if base_annual_rev < 1000000:
        rev_scale = '100万以下'
    elif base_annual_rev < 5000000:
        rev_scale = '100-500万'
    elif base_annual_rev < 20000000:
        rev_scale = '500-2000万'
    else:
        rev_scale = '2000万以上'

    for year, month in months:
        cur.execute(
            """INSERT OR REPLACE INTO taxpayer_profile_snapshot_month
            (taxpayer_id, period_year, period_month, industry_code,
             tax_authority_code, region_code, credit_grade,
             employee_scale, revenue_scale, source_doc_id, etl_batch_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, year, month, co['industry_code'],
             co['tax_authority_code'], co['region_code'],
             co['credit_grade_current'], emp_scale, rev_scale,
             None, 'ETL_NEW4')
        )

    for year in range(co['start_year'], co['end_year'] + 1):
        cur.execute(
            """INSERT OR REPLACE INTO taxpayer_credit_grade_year
            (taxpayer_id, year, credit_grade, published_at, source_doc_id, etl_batch_id)
            VALUES (?,?,?,?,?,?)""",
            (tid, year, co['credit_grade_current'],
             f'{year}-06-01', None, 'ETL_NEW4')
        )

    print(f"  {co['short_name']} 画像快照: {len(months)} 月 + {co['end_year'] - co['start_year'] + 1} 年信用等级")


# ============================================================
# 主入口
# ============================================================
def insert_new4_data(db_path=None):
    """插入4家新企业的全域模拟数据"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=" * 60)
    print("插入4家新企业模拟数据 (2023-2025)")
    print("=" * 60)

    _insert_taxpayers(cur)

    for co in COMPANIES:
        print(f"\n--- {co['taxpayer_name']} ({co['taxpayer_type']}) ---")
        if co['taxpayer_type'] == '一般纳税人':
            _insert_general_vat(cur, co)
        else:
            _insert_small_vat(cur, co)
        _insert_eit(cur, co)
        _insert_account_balance(cur, co)
        _insert_balance_sheet(cur, co)
        _insert_profit_statement(cur, co)
        _insert_cash_flow(cur, co)
        _insert_invoices(cur, co)
        _insert_profile_and_credit(cur, co)

    conn.commit()
    conn.close()
    print("\n" + "=" * 60)
    print("[sample_data_new4] 4家企业数据插入完成")
    print("=" * 60)


def run_all(db_path=None):
    """插入数据 + 计算财务指标"""
    insert_new4_data(db_path)

    print("\n计算财务指标 v1...")
    from database.calculate_metrics import calculate_and_save
    for co in COMPANIES:
        calculate_and_save(db_path, taxpayer_id=co['taxpayer_id'])

    print("\n计算财务指标 v2...")
    from database.calculate_metrics_v2 import calculate_and_save_v2
    for co in COMPANIES:
        calculate_and_save_v2(db_path, taxpayer_id=co['taxpayer_id'])

    print("\n[run_all] 全部完成")


if __name__ == '__main__':
    run_all()
