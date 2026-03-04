"""
fill_missing_data.py — One-time migration script to fill ALL data gaps across 6 companies.
Idempotent: uses INSERT OR IGNORE / INSERT OR REPLACE, safe to run multiple times.
"""
import sqlite3
import math
import os
import sys
import random
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'fintax_ai.db')

# ── Company Master Config ──────────────────────────────────────────────
COMPANIES = {
    'C1': {
        'taxpayer_id': '91310000MA1FL8XQ30',
        'taxpayer_name': '华兴科技有限公司',
        'taxpayer_type': '一般纳税人',
        'accounting_standard': '企业会计准则',
        'gaap_bs': 'ASBE', 'gaap_pl': 'CAS',
        'base_revenue': 800000, 'cost_ratio': 0.55,
        'growth_rate': 0.02, 'seasonal_amp': 0.05,
        'employee_count': 171, 'asset_base': 5000000,
        'start_year': 2024, 'start_month': 1,
        'end_year': 2026, 'end_month': 2,
        'industry_code': '6510', 'tax_authority_code': '13101150000',
        'region_code': '310115', 'credit_grade': 'A',
        'city': '上海', 'company_code': 'HX001',
        'short_name': '华兴科技',
    },
    'C2': {
        'taxpayer_id': '92440300MA5EQXL17P',
        'taxpayer_name': '鑫源贸易商行',
        'taxpayer_type': '小规模纳税人',
        'accounting_standard': '小企业会计准则',
        'gaap_bs': 'ASSE', 'gaap_pl': 'SAS',
        'base_revenue': 80000, 'cost_ratio': 0.65,
        'growth_rate': 0.015, 'seasonal_amp': 0.04,
        'employee_count': 16, 'asset_base': 500000,
        'start_year': 2024, 'start_month': 1,
        'end_year': 2026, 'end_month': 2,
        'industry_code': '5252', 'tax_authority_code': '14403060000',
        'region_code': '440306', 'credit_grade': 'B',
        'city': '深圳', 'company_code': 'XY001',
        'short_name': '鑫源贸易',
    },
    'C3': {
        'taxpayer_id': '91330200MA2KXXXXXX',
        'taxpayer_name': '创智软件股份有限公司',
        'taxpayer_type': '一般纳税人',
        'accounting_standard': '企业会计准则',
        'gaap_bs': 'ASBE', 'gaap_pl': 'CAS',
        'base_revenue': 1800000, 'cost_ratio': 0.42,
        'growth_rate': 0.022, 'seasonal_amp': 0.07,
        'employee_count': 220, 'asset_base': 8000000,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'industry_code': '3011', 'tax_authority_code': '13302060000',
        'region_code': '330206', 'credit_grade': 'A',
        'city': '宁波', 'company_code': 'CZ001',
        'short_name': '创智软件',
        'legal_representative': '陈浩',
        'registration_type': '股份公司',
        'establish_date': '2022-03-22',
        'registered_capital': 350,
        'registered_address': '浙江省宁波市大榭开发区科技园8号楼',
        'business_scope': '软件开发；信息技术咨询服务；计算机系统集成',
        'industry_name': '软件和信息技术服务业',
    },
    'C4': {
        'taxpayer_id': '91330200MA2KYYYYYY',
        'taxpayer_name': '大华智能制造厂',
        'taxpayer_type': '小规模纳税人',
        'accounting_standard': '小企业会计准则',
        'gaap_bs': 'ASSE', 'gaap_pl': 'SAS',
        'base_revenue': 350000, 'cost_ratio': 0.72,
        'growth_rate': 0.015, 'seasonal_amp': 0.05,
        'employee_count': 86, 'asset_base': 2500000,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'industry_code': '3599', 'tax_authority_code': '13205060000',
        'region_code': '320506', 'credit_grade': 'B',
        'city': '苏州', 'company_code': 'DH001',
        'short_name': '大华制造',
        'legal_representative': '王建国',
        'registration_type': '个人独资企业',
        'establish_date': '2019-08-15',
        'registered_capital': 80,
        'registered_address': '江苏省苏州市吴中区工业园区18号',
        'business_scope': '智能设备制造；机械零部件加工；自动化设备销售',
        'industry_name': '通用设备制造业',
    },
    'C5': {
        'taxpayer_id': '91310115MA2KZZZZZZ',
        'taxpayer_name': 'TSE科技有限公司',
        'taxpayer_type': '一般纳税人',
        'accounting_standard': '企业会计准则',
        'gaap_bs': 'ASBE', 'gaap_pl': 'CAS',
        'base_revenue': 1500000, 'cost_ratio': 0.45,
        'growth_rate': 0.028, 'seasonal_amp': 0.06,
        'employee_count': 110, 'asset_base': 6000000,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'industry_code': '6510', 'tax_authority_code': '13101150000',
        'region_code': '310115', 'credit_grade': 'A',
        'city': '上海', 'company_code': 'TSE001',
        'short_name': 'TSE科技',
        'legal_representative': '李明远',
        'registration_type': '有限责任公司',
        'establish_date': '2020-01-10',
        'registered_capital': 500,
        'registered_address': '上海市浦东新区张江高科技园区碧波路690号',
        'business_scope': '集成电路设计；电子元器件研发；技术进出口',
        'industry_name': '集成电路设计',
    },
    'C6': {
        'taxpayer_id': '91330100MA2KWWWWWW',
        'taxpayer_name': '环球机械有限公司',
        'taxpayer_type': '小规模纳税人',
        'accounting_standard': '小企业会计准则',
        'gaap_bs': 'ASSE', 'gaap_pl': 'SAS',
        'base_revenue': 450000, 'cost_ratio': 0.68,
        'growth_rate': 0.018, 'seasonal_amp': 0.05,
        'employee_count': 65, 'asset_base': 3000000,
        'start_year': 2023, 'start_month': 1,
        'end_year': 2025, 'end_month': 12,
        'industry_code': '3411', 'tax_authority_code': '13301060000',
        'region_code': '330106', 'credit_grade': 'B',
        'city': '杭州', 'company_code': 'HQ001',
        'short_name': '环球机械',
        'legal_representative': '赵德明',
        'registration_type': '有限责任公司',
        'establish_date': '2017-11-08',
        'registered_capital': 120,
        'registered_address': '浙江省杭州市西湖区转塘科技经济区块18号',
        'business_scope': '通用机械制造；金属制品加工；机械设备租赁',
        'industry_name': '金属制品业',
    },
}


# ── Utility Functions ──────────────────────────────────────────────────
def _gen_months(sy, sm, ey, em):
    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _month_offset(year, month):
    return (year - 2025) * 12 + (month - 1)


def _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.05):
    growth = (1 + growth_rate) ** offset
    seasonal = 1 + seasonal_amp * math.sin(2 * math.pi * offset / 12)
    return growth * seasonal


def _exists(conn, table, where, params):
    r = conn.execute(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1", params).fetchone()
    return r is not None


# ── Section A: Business Registration for C3-C6 ────────────────────────
def fill_business_registration(conn):
    print("[A] Filling company_business_registration for C3-C6...")
    cols = (
        'company_name, english_name, unified_social_credit_code, company_type,'
        'operation_status, established_date, approval_date, legal_representative,'
        'registered_capital, paid_in_capital, insured_count, company_scale,'
        'business_scope, registered_address, business_term, source, taxpayer_id,'
        'industry_commerce_reg_no, organization_code, contact_phone, email,'
        'taxpayer_qualification, former_name, province, city, district, website,'
        'industry, industry_level1, industry_level2, industry_level3,'
        'registration_authority, longitude, latitude, extra'
    )
    records = [
        # C3 创智软件
        ('创智软件股份有限公司', 'Chuangzhi Software Co., Ltd.',
         '91330200MA2KXXXXXX', '股份有限公司(非上市)', '存续',
         '2022-03-22', '2024-01-10', '陈浩',
         '3500万人民币', '2800万人民币', 220, '中型企业',
         '软件开发；信息技术咨询服务；计算机系统集成；数据处理和存储支持服务',
         '浙江省宁波市大榭开发区科技园8号楼',
         '2022-03-22 至 无固定期限', '国家企业信用信息公示系统',
         '91330200MA2KXXXXXX', '330200000XXXXXX', 'MA2KXXXX-X',
         '0574-8765-XXXX', 'info@chuangzhi-soft.com', '一般纳税人', None,
         '浙江省', '宁波市', '大榭开发区', 'www.chuangzhi-soft.com',
         '软件和信息技术服务业', '信息传输、软件和信息技术服务业',
         '软件和信息技术服务业', '应用软件开发',
         '宁波市大榭开发区市场监督管理局', 121.9567, 29.9345, None),
        # C4 大华智能制造
        ('大华智能制造厂', 'Dahua Intelligent Manufacturing',
         '91330200MA2KYYYYYY', '个人独资企业', '存续',
         '2019-08-15', '2023-05-20', '王建国',
         '800万人民币', '800万人民币', 86, '小型企业',
         '智能设备制造；机械零部件加工；自动化设备销售；技术咨询服务',
         '江苏省苏州市吴中区工业园区18号',
         '2019-08-15 至 无固定期限', '国家企业信用信息公示系统',
         '91330200MA2KYYYYYY', '320506000YYYYYY', 'MA2KYYYY-Y',
         '0512-6543-XXXX', 'info@dahua-mfg.com', '小规模纳税人', None,
         '江苏省', '苏州市', '吴中区', None,
         '通用设备制造业', '制造业', '通用设备制造业', '其他通用设备制造',
         '苏州市吴中区市场监督管理局', 120.6319, 31.2638, None),
        # C5 TSE科技
        ('TSE科技有限公司', 'TSE Technology Co., Ltd.',
         '91310115MA2KZZZZZZ', '有限责任公司(自然人投资或控股)', '存续',
         '2020-01-10', '2024-03-15', '李明远',
         '5000万人民币', '4000万人民币', 110, '中型企业',
         '集成电路设计；电子元器件研发；技术进出口；软件开发',
         '上海市浦东新区张江高科技园区碧波路690号',
         '2020-01-10 至 无固定期限', '国家企业信用信息公示系统',
         '91310115MA2KZZZZZZ', '310115000ZZZZZZ', 'MA2KZZZZ-Z',
         '021-5080-XXXX', 'info@tse-tech.com', '一般纳税人', None,
         '上海市', '浦东新区', '张江镇', 'www.tse-tech.com',
         '集成电路设计', '信息传输、软件和信息技术服务业',
         '软件和信息技术服务业', '集成电路设计',
         '上海市浦东新区市场监督管理局', 121.5907, 31.2045, None),
        # C6 环球机械
        ('环球机械有限公司', 'Global Machinery Co., Ltd.',
         '91330100MA2KWWWWWW', '有限责任公司(自然人投资或控股)', '存续',
         '2017-11-08', '2023-08-22', '赵德明',
         '1200万人民币', '1000万人民币', 65, '小型企业',
         '通用机械制造；金属制品加工；机械设备租赁；五金交电销售',
         '浙江省杭州市西湖区转塘科技经济区块18号',
         '2017-11-08 至 无固定期限', '国家企业信用信息公示系统',
         '91330100MA2KWWWWWW', '330100000WWWWWW', 'MA2KWWWW-W',
         '0571-8765-XXXX', 'info@global-mach.com', '小规模纳税人', None,
         '浙江省', '杭州市', '西湖区', None,
         '金属制品业', '制造业', '金属制品业', '金属工具制造',
         '杭州市西湖区市场监督管理局', 120.1290, 30.2084, None),
    ]
    inserted = 0
    for rec in records:
        tid = rec[2]  # unified_social_credit_code = taxpayer_id
        if _exists(conn, 'company_business_registration',
                   'unified_social_credit_code=?', (tid,)):
            continue
        placeholders = ','.join(['?'] * len(rec))
        conn.execute(
            f"INSERT INTO company_business_registration ({cols}) VALUES ({placeholders})",
            rec)
        inserted += 1
    print(f"  → Inserted {inserted} business registration records")


# ── Section B: EIT Annual + Quarterly for C2 ───────────────────────────
def fill_eit_c2(conn):
    print("[B] Filling EIT annual + quarterly for C2 (鑫源贸易)...")
    co = COMPANIES['C2']
    tid = co['taxpayer_id']
    base_rev = co['base_revenue']
    gr = co['growth_rate']
    cr = co['cost_ratio']
    tax_rate = 0.05  # 小微企业

    inserted_a = 0
    inserted_q = 0
    for year in [2023, 2024, 2025]:
        fid = f'{tid}_{year}_0'
        if _exists(conn, 'eit_annual_filing', 'filing_id=?', (fid,)):
            continue

        year_offset = (year - 2025)
        yf = (1 + gr) ** (year_offset * 12)
        annual_rev = round(base_rev * 12 * yf)
        annual_cost = round(annual_rev * cr)

        taxes_sur = round(annual_rev * 0.025)
        sell_exp = round(annual_rev * 0.05)
        admin_exp = round(annual_rev * 0.08)
        rd_exp = round(annual_rev * 0.02)
        fin_exp = round(annual_rev * 0.01)
        other_gains = round(annual_rev * 0.005)
        inv_income = round(annual_rev * 0.003)
        credit_imp = round(annual_rev * -0.002)
        asset_imp = round(annual_rev * -0.001)
        asset_disp = round(annual_rev * 0.001)

        op_profit = (annual_rev - annual_cost - taxes_sur - sell_exp - admin_exp
                     - rd_exp - fin_exp + other_gains + inv_income
                     + credit_imp + asset_imp + asset_disp)
        non_op_inc = round(annual_rev * 0.002)
        non_op_exp = round(annual_rev * 0.001)
        total_profit = op_profit + non_op_inc - non_op_exp

        tax_adjust_inc = round(total_profit * 0.04)
        tax_adjust_dec = round(total_profit * 0.01)
        adjusted = total_profit + tax_adjust_inc - tax_adjust_dec
        taxable_income = max(adjusted, 0)
        tax_payable = round(taxable_income * tax_rate)
        prepaid = round(tax_payable * 0.8)
        final_tax = tax_payable - prepaid

        # eit_annual_filing
        conn.execute(
            "INSERT OR REPLACE INTO eit_annual_filing "
            "(filing_id, taxpayer_id, period_year, revision_no, amount_unit,"
            " preparer, submitted_at, etl_batch_id, etl_confidence) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (fid, tid, year, 0, '元', '系统', f'{year+1}-05-15', 'ETL_FILL', 1.0))

        # eit_annual_basic_info
        asset_avg = round(co['asset_base'] * yf)
        conn.execute(
            "INSERT OR REPLACE INTO eit_annual_basic_info "
            "(filing_id, tax_return_type_code, asset_avg, employee_avg,"
            " industry_code, restricted_or_prohibited, small_micro_enterprise, listed_company) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (fid, 'A', asset_avg, co['employee_count'],
             co['industry_code'], 0, 1, 0))

        # eit_annual_main
        conn.execute(
            "INSERT OR REPLACE INTO eit_annual_main "
            "(filing_id, revenue, cost, taxes_surcharges, selling_expenses, admin_expenses,"
            " rd_expenses, financial_expenses, other_gains, investment_income,"
            " net_exposure_hedge_gains, fair_value_change_gains,"
            " credit_impairment_loss, asset_impairment_loss, asset_disposal_gains,"
            " operating_profit, non_operating_income, non_operating_expenses, total_profit,"
            " less_foreign_income, add_tax_adjust_increase, less_tax_adjust_decrease,"
            " exempt_income_deduction_total, add_foreign_tax_offset, adjusted_taxable_income,"
            " less_income_exemption, less_losses_carried_forward, less_taxable_income_deduction,"
            " taxable_income, tax_rate, tax_payable,"
            " tax_credit_total, less_foreign_tax_credit, tax_due,"
            " add_foreign_tax_due, less_foreign_tax_credit_amount, actual_tax_payable,"
            " less_prepaid_tax, tax_payable_or_refund,"
            " hq_share, fiscal_central_share, hq_dept_share,"
            " less_ethnic_autonomous_relief, less_audit_adjustment, less_special_adjustment,"
            " final_tax_payable_or_refund) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, annual_rev, annual_cost, taxes_sur, sell_exp, admin_exp,
             rd_exp, fin_exp, other_gains, inv_income, 0, 0,
             credit_imp, asset_imp, asset_disp,
             op_profit, non_op_inc, non_op_exp, total_profit,
             0, tax_adjust_inc, tax_adjust_dec,
             0, 0, adjusted,
             0, 0, 0,
             taxable_income, tax_rate, tax_payable,
             0, 0, tax_payable,
             0, 0, tax_payable,
             prepaid, final_tax,
             0, 0, 0, 0, 0, 0, final_tax))
        inserted_a += 1

        # Quarterly
        for q in range(1, 5):
            qfid = f'{tid}_{year}Q{q}_0'
            if _exists(conn, 'eit_quarter_filing', 'filing_id=?', (qfid,)):
                continue
            q_rev = round(annual_rev * q / 4)
            q_cost = round(annual_cost * q / 4)
            q_profit = round(total_profit * q / 4)
            q_taxable = max(q_profit, 0)
            q_tax = round(q_taxable * tax_rate)
            q_prepaid = round(q_tax * (q - 1) / max(q, 1)) if q > 1 else 0
            q_due = q_tax - q_prepaid

            conn.execute(
                "INSERT OR REPLACE INTO eit_quarter_filing "
                "(filing_id, taxpayer_id, period_year, period_quarter, revision_no,"
                " amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (qfid, tid, year, q, 0, '元', '系统',
                 f'{year}-{q*3:02d}-20', 'ETL_FILL', 1.0))

            conn.execute(
                "INSERT OR REPLACE INTO eit_quarter_main "
                "(filing_id, revenue, cost, total_profit, tax_rate,"
                " tax_payable, less_prepaid_tax_current_year,"
                " current_tax_payable_or_refund, final_tax_payable_or_refund) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (qfid, q_rev, q_cost, q_profit, tax_rate,
                 q_tax, q_prepaid, q_due, q_due))
            inserted_q += 1

    print(f"  → Inserted {inserted_a} annual + {inserted_q} quarterly EIT records for C2")


# ── Section C: EIT Shareholder Data (All 6 companies) ──────────────────
def fill_eit_shareholders(conn):
    print("[C] Filling eit_annual_shareholder for all companies...")
    shareholders_map = {
        'C1': [('陈浩', '自然人', 40.0), ('张伟', '自然人', 35.0), ('上海创投基金', '法人', 25.0)],
        'C2': [('林小明', '自然人', 60.0), ('陈丽华', '自然人', 40.0)],
        'C3': [('陈浩', '自然人', 30.0), ('宁波创新投资', '法人', 45.0), ('李强', '自然人', 25.0)],
        'C4': [('王建国', '自然人', 100.0)],
        'C5': [('李明远', '自然人', 35.0), ('上海科创基金', '法人', 40.0), ('赵磊', '自然人', 25.0)],
        'C6': [('赵德明', '自然人', 55.0), ('钱国强', '自然人', 45.0)],
    }
    inserted = 0
    for ckey, co in COMPANIES.items():
        tid = co['taxpayer_id']
        sy = co['start_year']
        ey = co['end_year']
        shareholders = shareholders_map[ckey]
        for year in range(sy, ey + 1):
            fid = f'{tid}_{year}_0'
            if _exists(conn, 'eit_annual_shareholder',
                       'filing_id=? AND shareholder_name=?',
                       (fid, shareholders[0][0])):
                continue
            # Ensure filing exists
            if not _exists(conn, 'eit_annual_filing', 'filing_id=?', (fid,)):
                continue
            for idx, (name, stype, ratio) in enumerate(shareholders):
                conn.execute(
                    "INSERT OR REPLACE INTO eit_annual_shareholder "
                    "(filing_id, shareholder_name, id_type, id_number,"
                    " investment_ratio, dividend_amount, nationality_or_address) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (fid, name,
                     '居民身份证' if stype == '自然人' else '统一社会信用代码',
                     f'XXXXXX{idx+1:04d}', ratio, 0, '中国'))
                inserted += 1
    print(f"  → Inserted {inserted} shareholder records")


# ── Section D: Invoices for C1 (missing months) and C2 (all months) ───
def fill_invoices(conn):
    print("[D] Filling invoices for C1 and C2...")
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
    goods_names = ['电子元器件', '服务器设备', '物流服务', '软件许可', '办公用品']

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

    configs = [
        ('C1', 2024, 1, 2024, 12, 5, True),   # C1: fill 2024.01-2024.12, 5 per month
        ('C2', 2024, 1, 2026, 2, 3, False),    # C2: fill all 26 months, 3 per month
    ]

    total_p = 0
    total_s = 0
    for ckey, sy, sm, ey, em, count, is_general in configs:
        co = COMPANIES[ckey]
        tid = co['taxpayer_id']
        base_rev = co['base_revenue']
        gr = co['growth_rate']
        sa = co['seasonal_amp']

        for year, month in _gen_months(sy, sm, ey, em):
            # Check if already has invoices for this month
            if _exists(conn, 'inv_spec_purchase',
                       'taxpayer_id=? AND period_year=? AND period_month=?',
                       (tid, year, month)):
                continue

            offset = _month_offset(year, month)
            f = _monthly_factor(offset, gr, sa)
            base_amt = round(base_rev * 0.3 * f)

            # Purchase invoices
            for i in range(count):
                seller = sellers[i % len(sellers)]
                pk = f'{tid[-4:]}{year}{month:02d}P{i+1:03d}'
                amt = round(base_amt * (1 + i * 0.3))
                if is_general:
                    rate_str = '13%' if i < 3 else '6%'
                    rate_val = 0.13 if i < 3 else 0.06
                else:
                    rate_str = '3%'
                    rate_val = 0.03
                tax_amt = round(amt * rate_val)
                qty = max(1, round(amt / 500))
                up = round(amt / qty, 2) if qty > 0 else float(amt)
                day = min(28, (i + 1) * 8)
                inv_date = f'{year}-{month:02d}-{day:02d}'

                conn.execute(
                    f"INSERT OR REPLACE INTO inv_spec_purchase ({p_cols}) "
                    f"VALUES ({','.join(['?']*34)})",
                    (tid, year, month, '数电', pk, 1,
                     '', '', pk,
                     seller[0], seller[1], tid, co['taxpayer_name'],
                     inv_date, f'10{i+1}', '',
                     goods_names[i % 5], f'SPEC-{i+1}', '个', qty, up,
                     amt, rate_str, tax_amt, amt + tax_amt,
                     '电子发票服务平台', '增值税专用发票', '正常', 1, '无风险',
                     '系统', '', f'{inv_date} 10:00:00', 'ETL_FILL'))
                total_p += 1

            # Sales invoices
            for i in range(count):
                buyer = buyers[i % len(buyers)]
                pk = f'{tid[-4:]}{year}{month:02d}S{i+1:03d}'
                amt = round(base_amt * 1.5 * (1 + i * 0.4))
                if is_general:
                    rate_val = 0.13 if i < 3 else 0.06
                else:
                    rate_val = 0.03
                tax_amt = round(amt * rate_val)
                day = min(28, (i + 1) * 7)
                inv_date = f'{year}-{month:02d}-{day:02d}'

                conn.execute(
                    f"INSERT OR REPLACE INTO inv_spec_sales ({s_cols}) "
                    f"VALUES ({','.join(['?']*26)})",
                    (tid, year, month, '数电', pk, 1,
                     '', '', pk,
                     tid, co['taxpayer_name'], buyer[0], buyer[1],
                     inv_date, amt, tax_amt, amt + tax_amt,
                     '电子发票服务平台', '增值税专用发票', '正常', 1, '无风险',
                     '系统', '', f'{inv_date} 10:00:00', 'ETL_FILL'))
                total_s += 1

    print(f"  → Inserted {total_p} purchase + {total_s} sales invoices")


# ── Section E: Profile Snapshots + Credit Grades for C1, C2 ───────────
def fill_profile_and_credit(conn):
    print("[E] Filling profile snapshots + credit grades for C1, C2...")
    inserted_p = 0
    inserted_c = 0
    for ckey in ['C1', 'C2']:
        co = COMPANIES[ckey]
        tid = co['taxpayer_id']
        emp_count = co['employee_count']

        if emp_count <= 10: emp_scale = '1-10'
        elif emp_count <= 50: emp_scale = '11-50'
        elif emp_count <= 100: emp_scale = '51-100'
        elif emp_count <= 300: emp_scale = '101-300'
        else: emp_scale = '300以上'

        base_annual_rev = co['base_revenue'] * 12
        if base_annual_rev < 1000000: rev_scale = '100万以下'
        elif base_annual_rev < 5000000: rev_scale = '100-500万'
        elif base_annual_rev < 20000000: rev_scale = '500-2000万'
        else: rev_scale = '2000万以上'

        # Monthly profile snapshots
        for year, month in _gen_months(co['start_year'], co['start_month'],
                                       co['end_year'], co['end_month']):
            if _exists(conn, 'taxpayer_profile_snapshot_month',
                       'taxpayer_id=? AND period_year=? AND period_month=?',
                       (tid, year, month)):
                continue
            conn.execute(
                "INSERT OR REPLACE INTO taxpayer_profile_snapshot_month "
                "(taxpayer_id, period_year, period_month, industry_code,"
                " tax_authority_code, region_code, credit_grade,"
                " employee_scale, revenue_scale, source_doc_id, etl_batch_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (tid, year, month, co['industry_code'],
                 co['tax_authority_code'], co['region_code'], co['credit_grade'],
                 emp_scale, rev_scale, f'PROF_{tid}_{year}{month:02d}', 'ETL_FILL'))
            inserted_p += 1

        # Annual credit grades
        for year in range(co['start_year'], co['end_year'] + 1):
            if _exists(conn, 'taxpayer_credit_grade_year',
                       'taxpayer_id=? AND year=?', (tid, year)):
                continue
            conn.execute(
                "INSERT OR REPLACE INTO taxpayer_credit_grade_year "
                "(taxpayer_id, year, credit_grade, published_at, source_doc_id, etl_batch_id) "
                "VALUES (?,?,?,?,?,?)",
                (tid, year, co['credit_grade'], f'{year}-06-01',
                 f'CREDIT_{tid}_{year}', 'ETL_FILL'))
            inserted_c += 1

    print(f"  → Inserted {inserted_p} profile snapshots + {inserted_c} credit grades")


# ── Section F: HR Employee + Salary Data for C3-C6 ────────────────────
TAX_BRACKETS = [
    (36000,   0.03, 0),
    (144000,  0.10, 2520),
    (300000,  0.20, 16920),
    (420000,  0.25, 31920),
    (660000,  0.30, 52920),
    (960000,  0.35, 85920),
    (float('inf'), 0.45, 181920),
]

CITY_PARAMS = {
    "上海": {
        "si_pension_emp": 0.08, "si_medical_emp": 0.02, "si_unemployment_emp": 0.005,
        "housing_fund_emp": 0.07,
        "si_pension_co": 0.16, "si_medical_co": 0.095, "si_unemployment_co": 0.005,
        "si_injury_co": 0.004, "si_maternity_co": 0.01, "housing_fund_co": 0.07,
    },
    "深圳": {
        "si_pension_emp": 0.08, "si_medical_emp": 0.02, "si_unemployment_emp": 0.003,
        "housing_fund_emp": 0.05,
        "si_pension_co": 0.15, "si_medical_co": 0.06, "si_unemployment_co": 0.007,
        "si_injury_co": 0.003, "si_maternity_co": 0.005, "housing_fund_co": 0.05,
    },
    "宁波": {
        "si_pension_emp": 0.08, "si_medical_emp": 0.02, "si_unemployment_emp": 0.005,
        "housing_fund_emp": 0.07,
        "si_pension_co": 0.16, "si_medical_co": 0.085, "si_unemployment_co": 0.005,
        "si_injury_co": 0.004, "si_maternity_co": 0.008, "housing_fund_co": 0.07,
    },
    "苏州": {
        "si_pension_emp": 0.08, "si_medical_emp": 0.02, "si_unemployment_emp": 0.005,
        "housing_fund_emp": 0.07,
        "si_pension_co": 0.16, "si_medical_co": 0.08, "si_unemployment_co": 0.005,
        "si_injury_co": 0.004, "si_maternity_co": 0.008, "housing_fund_co": 0.07,
    },
    "杭州": {
        "si_pension_emp": 0.08, "si_medical_emp": 0.02, "si_unemployment_emp": 0.005,
        "housing_fund_emp": 0.07,
        "si_pension_co": 0.16, "si_medical_co": 0.085, "si_unemployment_co": 0.005,
        "si_injury_co": 0.004, "si_maternity_co": 0.008, "housing_fund_co": 0.07,
    },
}

SPECIAL_ADD_DEDUCTION_PROFILES = {
    "无":           (0,    0,    0,    0,    0,    0),
    "房贷":         (0,    0,    1000, 0,    0,    0),
    "租房":         (0,    0,    0,    1500, 0,    0),
    "房贷+子女":    (2000, 0,    1000, 0,    0,    0),
    "租房+赡养":    (0,    0,    0,    1500, 3000, 0),
    "全套":         (2000, 400,  1000, 0,    3000, 2000),
    "子女+赡养":    (2000, 0,    0,    0,    3000, 0),
    "继续教育":     (0,    400,  0,    0,    0,    0),
}


def _calc_annual_tax(annual_taxable):
    if annual_taxable <= 0:
        return 0, 0, 0
    for upper, rate, quick in TAX_BRACKETS:
        if annual_taxable <= upper:
            return rate, quick, round(annual_taxable * rate - quick, 2)
    return 0.45, 181920, round(annual_taxable * 0.45 - 181920, 2)


# Employee templates for C3-C6
HR_TEMPLATES = {
    'C3': {  # 创智软件 - 15 employees, software company
        'company_code': 'CZ001', 'company_name': '创智软件股份有限公司',
        'city': '宁波',
        'employees': [
            ("CZ0001", "周明", "1", "1975-08-15", 50, "博士", 4, "计算机科学", "理工",
             "D01", "总经办", 1, "P01", "总经理", "管理", "正式", "2022-03-22", 4.0, 25.0,
             "0815", 1, None, 1, "职称", "教授级高工", 240, 38000, "全套"),
            ("CZ0002", "吴芳", "2", "1982-03-20", 43, "硕士", 3, "财务管理", "经管",
             "D02", "财务部", 1, "P02", "财务总监", "管理", "正式", "2022-04-10", 3.9, 18.0,
             "0320", 1, None, 0, None, None, 0, 28000, "房贷+子女"),
            ("CZ0003", "郑伟", "1", "1985-11-05", 40, "硕士", 3, "软件工程", "理工",
             "D03", "研发部", 1, "P03", "技术总监", "研发", "正式", "2022-03-25", 3.9, 15.0,
             "1105", 1, None, 1, "职称", "高级工程师", 240, 35000, "子女+赡养"),
            ("CZ0004", "孙丽", "2", "1990-06-18", 35, "本科", 2, "人力资源", "经管",
             "D04", "人事行政部", 1, "P04", "HR经理", "管理", "正式", "2022-05-15", 3.8, 12.0,
             "0618", 1, None, 0, None, None, 0, 15000, "房贷"),
            ("CZ0005", "钱磊", "1", "1988-01-22", 38, "硕士", 3, "计算机", "理工",
             "D03", "研发部", 1, "P05", "高级开发", "研发", "正式", "2022-06-01", 3.7, 13.0,
             "0122", 1, None, 1, "证书", "系统架构师", 240, 25000, "租房+赡养"),
            ("CZ0006", "冯静", "2", "1992-09-10", 33, "本科", 2, "会计学", "经管",
             "D02", "财务部", 1, "P06", "会计", "管理", "正式", "2022-07-01", 3.5, 10.0,
             "0910", 1, None, 0, None, None, 0, 12000, "租房"),
            ("CZ0007", "陈刚", "1", "1991-04-25", 34, "硕士", 3, "人工智能", "理工",
             "D03", "研发部", 1, "P07", "算法工程师", "研发", "正式", "2022-08-15", 3.5, 9.0,
             "0425", 1, None, 1, "证书", "深度学习工程师", 240, 22000, "房贷"),
            ("CZ0008", "王小红", "2", "1995-12-03", 30, "本科", 2, "市场营销", "经管",
             "D05", "市场部", 1, "P08", "市场经理", "销售", "正式", "2023-01-10", 3.0, 7.0,
             "1203", 1, None, 0, None, None, 0, 16000, "继续教育"),
            ("CZ0009", "李华", "1", "1993-07-15", 32, "本科", 2, "计算机", "理工",
             "D03", "研发部", 1, "P09", "中级开发", "研发", "正式", "2023-03-01", 2.8, 8.0,
             "0715", 1, None, 0, None, None, 0, 18000, "房贷"),
            ("CZ0010", "赵敏", "2", "1996-02-28", 29, "本科", 2, "软件工程", "理工",
             "D03", "研发部", 1, "P10", "中级开发", "研发", "正式", "2023-06-15", 2.5, 5.0,
             "0228", 1, None, 0, None, None, 0, 16000, "租房"),
            ("CZ0011", "黄强", "1", "1997-10-08", 28, "本科", 2, "网络安全", "理工",
             "D06", "运维部", 1, "P11", "运维工程师", "研发", "正式", "2023-09-01", 2.3, 4.0,
             "1008", 1, None, 0, None, None, 0, 14000, "无"),
            ("CZ0012", "刘洋", "1", "1998-05-20", 27, "本科", 2, "计算机", "理工",
             "D03", "研发部", 1, "P12", "初级开发", "研发", "正式", "2024-01-15", 1.9, 3.0,
             "0520", 1, None, 0, None, None, 0, 11000, "无"),
            ("CZ0013", "张雪", "2", "1999-08-12", 26, "本科", 2, "行政管理", "经管",
             "D04", "人事行政部", 1, "P13", "行政助理", "管理", "正式", "2024-03-01", 1.8, 2.0,
             "0812", 1, None, 0, None, None, 0, 8000, "无"),
            ("CZ0014", "杨帆", "1", "1994-11-30", 31, "硕士", 3, "数据科学", "理工",
             "D03", "研发部", 1, "P14", "数据分析师", "研发", "正式", "2023-04-01", 2.7, 7.0,
             "1130", 1, None, 1, "证书", "数据分析师", 200, 20000, "房贷+子女"),
            ("CZ0015", "徐婷", "2", "2000-03-15", 25, "本科", 2, "英语", "文史",
             "D05", "市场部", 1, "P15", "销售专员", "销售", "正式", "2024-06-01", 1.5, 2.0,
             "0315", 1, None, 0, None, None, 0, 9000, "无"),
        ],
    },
    'C4': {  # 大华智能制造 - 12 employees, small manufacturer
        'company_code': 'DH001', 'company_name': '大华智能制造厂',
        'city': '苏州',
        'employees': [
            ("DH0001", "王建国", "1", "1970-03-10", 55, "大专", 1, "机械工程", "理工",
             "D01", "管理层", 1, "P01", "厂长", "管理", "正式", "2019-08-15", 6.4, 30.0,
             "0310", 1, None, 0, None, None, 0, 18000, "子女+赡养"),
            ("DH0002", "李秀英", "2", "1980-07-22", 45, "大专", 1, "会计", "经管",
             "D02", "财务部", 1, "P02", "会计", "管理", "正式", "2019-09-01", 6.3, 20.0,
             "0722", 1, None, 0, None, None, 0, 10000, "房贷+子女"),
            ("DH0003", "张大力", "1", "1978-12-05", 47, "中专", 0, "机械加工", "理工",
             "D03", "生产部", 1, "P03", "车间主任", "生产", "正式", "2019-10-01", 6.2, 25.0,
             "1205", 1, None, 0, None, None, 0, 12000, "房贷"),
            ("DH0004", "陈小明", "1", "1985-04-18", 40, "大专", 1, "电气自动化", "理工",
             "D03", "生产部", 1, "P04", "技术员", "生产", "正式", "2020-03-01", 5.8, 15.0,
             "0418", 1, None, 1, "证书", "电工技师", 240, 10000, "租房"),
            ("DH0005", "刘芳", "2", "1988-09-25", 37, "大专", 1, "行政管理", "经管",
             "D04", "行政部", 1, "P05", "行政文员", "管理", "正式", "2020-06-01", 5.5, 12.0,
             "0925", 1, None, 0, None, None, 0, 7000, "房贷"),
            ("DH0006", "赵铁柱", "1", "1982-01-15", 44, "中专", 0, "焊接", "理工",
             "D03", "生产部", 1, "P06", "焊工", "生产", "正式", "2020-01-15", 5.9, 20.0,
             "0115", 1, None, 0, None, None, 0, 9000, "租房+赡养"),
            ("DH0007", "孙国庆", "1", "1990-06-08", 35, "大专", 1, "数控技术", "理工",
             "D03", "生产部", 1, "P07", "数控操作员", "生产", "正式", "2021-03-01", 4.8, 10.0,
             "0608", 1, None, 0, None, None, 0, 8500, "无"),
            ("DH0008", "周丽萍", "2", "1992-11-20", 33, "大专", 1, "采购管理", "经管",
             "D05", "采购部", 1, "P08", "采购员", "销售", "正式", "2021-06-01", 4.5, 8.0,
             "1120", 1, None, 0, None, None, 0, 7500, "继续教育"),
            ("DH0009", "马强", "1", "1995-03-12", 30, "大专", 1, "物流管理", "经管",
             "D06", "仓储部", 1, "P09", "仓库管理员", "生产", "正式", "2022-01-10", 3.9, 6.0,
             "0312", 1, None, 0, None, None, 0, 6500, "无"),
            ("DH0010", "吴小燕", "2", "1997-08-05", 28, "大专", 1, "质量管理", "理工",
             "D03", "生产部", 1, "P10", "质检员", "生产", "正式", "2022-06-01", 3.5, 4.0,
             "0805", 1, None, 0, None, None, 0, 7000, "无"),
            ("DH0011", "郑伟民", "1", "1993-02-28", 32, "本科", 2, "机械设计", "理工",
             "D03", "生产部", 1, "P11", "设备维护员", "生产", "正式", "2023-01-15", 2.9, 7.0,
             "0228", 1, None, 0, None, None, 0, 8000, "房贷"),
            ("DH0012", "何小丽", "2", "1998-12-10", 27, "大专", 1, "文秘", "文史",
             "D04", "行政部", 1, "P12", "前台", "管理", "正式", "2023-06-01", 2.5, 3.0,
             "1210", 1, None, 0, None, None, 0, 5500, "无"),
        ],
    },
    'C5': {  # TSE科技 - 14 employees, chip design company
        'company_code': 'TSE001', 'company_name': 'TSE科技有限公司',
        'city': '上海',
        'employees': [
            ("TSE0001", "李明远", "1", "1976-02-14", 49, "博士", 4, "微电子", "理工",
             "D01", "总经办", 1, "P01", "总经理", "管理", "正式", "2020-01-10", 6.0, 24.0,
             "0214", 1, None, 1, "职称", "教授级高工", 240, 42000, "全套"),
            ("TSE0002", "张丽华", "2", "1983-05-30", 42, "硕士", 3, "财务管理", "经管",
             "D02", "财务部", 1, "P02", "财务总监", "管理", "正式", "2020-02-15", 5.9, 17.0,
             "0530", 1, None, 0, None, None, 0, 30000, "房贷+子女"),
            ("TSE0003", "王志强", "1", "1984-09-08", 41, "博士", 4, "集成电路", "理工",
             "D03", "研发部", 1, "P03", "技术总监", "研发", "正式", "2020-01-15", 6.0, 16.0,
             "0908", 1, None, 1, "职称", "高级工程师", 240, 38000, "子女+赡养"),
            ("TSE0004", "刘婷", "2", "1989-12-20", 36, "硕士", 3, "人力资源", "经管",
             "D04", "人事行政部", 1, "P04", "HR经理", "管理", "正式", "2020-04-01", 5.7, 11.0,
             "1220", 1, None, 0, None, None, 0, 18000, "房贷"),
            ("TSE0005", "陈建华", "1", "1987-03-15", 38, "硕士", 3, "微电子", "理工",
             "D03", "研发部", 1, "P05", "高级芯片设计师", "研发", "正式", "2020-06-01", 5.5, 13.0,
             "0315", 1, None, 1, "证书", "IC设计工程师", 240, 32000, "租房+赡养"),
            ("TSE0006", "赵雪梅", "2", "1991-07-22", 34, "本科", 2, "会计学", "经管",
             "D02", "财务部", 1, "P06", "会计", "管理", "正式", "2020-09-01", 5.3, 9.0,
             "0722", 1, None, 0, None, None, 0, 14000, "租房"),
            ("TSE0007", "黄伟", "1", "1990-10-05", 35, "硕士", 3, "电子工程", "理工",
             "D03", "研发部", 1, "P07", "芯片验证工程师", "研发", "正式", "2021-01-15", 4.9, 10.0,
             "1005", 1, None, 1, "证书", "验证工程师", 240, 26000, "房贷"),
            ("TSE0008", "林小燕", "2", "1993-04-18", 32, "本科", 2, "市场营销", "经管",
             "D05", "市场部", 1, "P08", "市场经理", "销售", "正式", "2021-06-01", 4.5, 8.0,
             "0418", 1, None, 0, None, None, 0, 18000, "继续教育"),
            ("TSE0009", "吴浩然", "1", "1992-08-25", 33, "硕士", 3, "微电子", "理工",
             "D03", "研发部", 1, "P09", "中级设计师", "研发", "正式", "2021-09-01", 4.3, 8.0,
             "0825", 1, None, 0, None, None, 0, 22000, "房贷"),
            ("TSE0010", "郑小丽", "2", "1995-01-10", 31, "本科", 2, "电子信息", "理工",
             "D03", "研发部", 1, "P10", "版图工程师", "研发", "正式", "2022-03-01", 3.8, 6.0,
             "0110", 1, None, 0, None, None, 0, 18000, "租房"),
            ("TSE0011", "马天宇", "1", "1996-06-15", 29, "硕士", 3, "计算机", "理工",
             "D06", "测试部", 1, "P11", "测试工程师", "研发", "正式", "2022-06-01", 3.5, 5.0,
             "0615", 1, None, 0, None, None, 0, 16000, "无"),
            ("TSE0012", "孙小明", "1", "1997-11-28", 28, "本科", 2, "电子工程", "理工",
             "D03", "研发部", 1, "P12", "初级设计师", "研发", "正式", "2023-01-10", 2.9, 4.0,
             "1128", 1, None, 0, None, None, 0, 14000, "无"),
            ("TSE0013", "周小红", "2", "1999-03-05", 26, "本科", 2, "行政管理", "经管",
             "D04", "人事行政部", 1, "P13", "行政助理", "管理", "正式", "2023-06-01", 2.5, 3.0,
             "0305", 1, None, 0, None, None, 0, 9000, "无"),
            ("TSE0014", "钱伟", "1", "1994-07-20", 31, "硕士", 3, "半导体物理", "理工",
             "D03", "研发部", 1, "P14", "工艺工程师", "研发", "正式", "2022-09-01", 3.3, 7.0,
             "0720", 1, None, 1, "证书", "半导体工艺师", 200, 24000, "房贷+子女"),
        ],
    },
    'C6': {  # 环球机械 - 10 employees, small machinery company
        'company_code': 'HQ001', 'company_name': '环球机械有限公司',
        'city': '杭州',
        'employees': [
            ("HQ0001", "赵德明", "1", "1972-06-20", 53, "大专", 1, "机械工程", "理工",
             "D01", "管理层", 1, "P01", "总经理", "管理", "正式", "2017-11-08", 8.3, 28.0,
             "0620", 1, None, 0, None, None, 0, 20000, "子女+赡养"),
            ("HQ0002", "钱国强", "1", "1975-10-15", 50, "大专", 1, "财务", "经管",
             "D02", "财务部", 1, "P02", "财务经理", "管理", "正式", "2018-01-10", 8.1, 25.0,
             "1015", 1, None, 0, None, None, 0, 13000, "房贷+子女"),
            ("HQ0003", "孙建军", "1", "1980-03-08", 45, "中专", 0, "机械加工", "理工",
             "D03", "生产部", 1, "P03", "车间主任", "生产", "正式", "2018-03-01", 7.9, 22.0,
             "0308", 1, None, 0, None, None, 0, 11000, "房贷"),
            ("HQ0004", "李小芳", "2", "1986-08-22", 39, "大专", 1, "会计", "经管",
             "D02", "财务部", 1, "P04", "会计", "管理", "正式", "2018-06-01", 7.7, 15.0,
             "0822", 1, None, 0, None, None, 0, 9000, "租房"),
            ("HQ0005", "王铁军", "1", "1983-01-12", 43, "中专", 0, "钳工", "理工",
             "D03", "生产部", 1, "P05", "高级钳工", "生产", "正式", "2018-09-01", 7.4, 20.0,
             "0112", 1, None, 0, None, None, 0, 9500, "租房+赡养"),
            ("HQ0006", "张小燕", "2", "1990-05-18", 35, "大专", 1, "行政管理", "经管",
             "D04", "行政部", 1, "P06", "行政文员", "管理", "正式", "2019-03-01", 6.8, 10.0,
             "0518", 1, None, 0, None, None, 0, 7000, "继续教育"),
            ("HQ0007", "陈大伟", "1", "1988-11-25", 37, "大专", 1, "焊接技术", "理工",
             "D03", "生产部", 1, "P07", "焊工", "生产", "正式", "2019-06-01", 6.5, 13.0,
             "1125", 1, None, 0, None, None, 0, 8500, "房贷"),
            ("HQ0008", "刘小明", "1", "1993-07-30", 32, "大专", 1, "数控技术", "理工",
             "D03", "生产部", 1, "P08", "数控操作员", "生产", "正式", "2020-01-15", 5.9, 8.0,
             "0730", 1, None, 0, None, None, 0, 7500, "无"),
            ("HQ0009", "周小丽", "2", "1996-02-14", 29, "大专", 1, "采购管理", "经管",
             "D05", "采购部", 1, "P09", "采购员", "销售", "正式", "2021-03-01", 4.8, 5.0,
             "0214", 1, None, 0, None, None, 0, 7000, "无"),
            ("HQ0010", "马小强", "1", "1997-09-08", 28, "大专", 1, "仓储管理", "经管",
             "D06", "仓储部", 1, "P10", "仓库管理员", "生产", "正式", "2022-06-01", 3.5, 4.0,
             "0908", 1, None, 0, None, None, 0, 6000, "无"),
        ],
    },
}

CITY_PREFIX = {
    '上海': '310101', '深圳': '440300', '宁波': '330200',
    '苏州': '320506', '杭州': '330100',
}


# ══════════════════════════════════════════════════════════════════════════
# Section F: HR employee info + salary for C3-C6
# ══════════════════════════════════════════════════════════════════════════
def fill_hr_data(conn):
    print("[F] Filling hr_employee_info + hr_employee_salary for C3-C6...")
    cur = conn.cursor()

    for ckey in ('C3', 'C4', 'C5', 'C6'):
        tpl = HR_TEMPLATES[ckey]
        company_code = tpl['company_code']
        company_name = tpl['company_name']
        city = tpl['city']
        city_pfx = CITY_PREFIX[city]
        cp = CITY_PARAMS[city]

        # Skip if already populated
        cur.execute(
            "SELECT COUNT(*) FROM hr_employee_info WHERE company_code = ?",
            (company_code,),
        )
        if cur.fetchone()[0] > 0:
            print(f"  {company_name} already has HR data, skipping.")
            continue

        for emp in tpl['employees']:
            (eid, name, gender, birth, age, edu, edu_deg, major, major_type,
             dept_code, dept_name, dept_level, pos_code, pos_name, pos_type,
             emp_type, entry_date, work_years, total_work_years,
             id_suffix, is_on_job, resign_date,
             is_ht, ht_cert_type, ht_cert_name, ht_work_days,
             base_wage, sad_profile) = emp

            # Generate id_card: city_prefix + birth(YYYYMMDD) + id_suffix + check
            birth_digits = birth.replace('-', '')
            id_card = f"{city_pfx}{birth_digits}{id_suffix}X"

            # ── INSERT employee info ──
            cur.execute("""
                INSERT OR REPLACE INTO hr_employee_info (
                    company_code, company_name, dept_code, dept_name, dept_level,
                    employee_id, employee_name, id_card, gender, birth_date, age,
                    education, education_degree, major, major_type,
                    entry_date, work_years, total_work_years,
                    position_code, position_name, position_type, employment_type,
                    social_insurance_city,
                    is_on_the_job, resign_date,
                    is_high_tech_person, high_tech_cert_type,
                    high_tech_cert_name, high_tech_work_days
                ) VALUES (?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?,?, ?, ?,?, ?,?,?,?)
            """, (
                company_code, company_name, dept_code, dept_name, dept_level,
                eid, name, id_card, gender, birth, age,
                edu, edu_deg, major, major_type,
                entry_date, work_years, total_work_years,
                pos_code, pos_name, pos_type, emp_type,
                city,
                is_on_job, resign_date,
                is_ht, ht_cert_type, ht_cert_name, ht_work_days,
            ))

            # ── Generate 36 months salary (2023-01 to 2025-12) ──
            sad = SPECIAL_ADD_DEDUCTION_PROFILES.get(sad_profile, (0,0,0,0,0,0))
            sad_child, sad_cont_edu, sad_loan, sad_rent, sad_elderly, sad_3yo = sad
            total_sad_monthly = sum(sad)

            for year in (2023, 2024, 2025):
                cum_income = 0.0
                cum_deduction = 0.0
                cum_tax = 0.0

                for month in range(1, 13):
                    salary_month = f"{year}{month:02d}"

                    # ── Income ──
                    wage = round(base_wage, 2)
                    bonus_quarterly = round(base_wage * 0.05, 2) if month % 3 == 0 else 0.0
                    bonus_yearly = round(base_wage * 0.10, 2) if month == 12 else 0.0
                    allowance_transport = 500.0
                    allowance_meal = 300.0
                    allowance_housing = 0.0
                    allowance_high_temp = 300.0 if month in (6, 7, 8, 9) else 0.0
                    allowance_shift = 0.0
                    allowance_other = 0.0
                    total_income = round(
                        wage + bonus_quarterly + bonus_yearly
                        + allowance_transport + allowance_meal
                        + allowance_housing + allowance_high_temp
                        + allowance_shift + allowance_other, 2
                    )

                    # ── Employee social insurance deductions ──
                    si_pension_emp = round(base_wage * cp['si_pension_emp'], 2)
                    si_medical_emp = round(base_wage * cp['si_medical_emp'], 2)
                    si_unemployment_emp = round(base_wage * cp['si_unemployment_emp'], 2)
                    housing_fund_emp = round(base_wage * cp['housing_fund_emp'], 2)
                    total_special_deduction = round(
                        si_pension_emp + si_medical_emp
                        + si_unemployment_emp + housing_fund_emp, 2
                    )

                    # ── Enterprise annuity (4% if wage >= 20000) ──
                    annuity = round(base_wage * 0.04, 2) if base_wage >= 20000 else 0.0
                    total_other_deduction = annuity

                    # ── Cost deductible (5000/month standard) ──
                    cost_deductible = 5000.0

                    # ── Cumulative withholding calculation ──
                    month_deduction = (
                        cost_deductible + total_special_deduction
                        + total_sad_monthly + total_other_deduction
                    )
                    cum_income += total_income
                    cum_deduction += month_deduction

                    cum_taxable = round(cum_income - cum_deduction, 2)
                    if cum_taxable < 0:
                        cum_taxable = 0.0

                    rate, quick, cum_tax_due = _calc_annual_tax(cum_taxable)
                    tax_this_month = round(cum_tax_due - cum_tax, 2)
                    if tax_this_month < 0:
                        tax_this_month = 0.0
                    cum_tax += tax_this_month

                    taxable_income_month = round(
                        total_income - cost_deductible
                        - total_special_deduction - total_sad_monthly
                        - total_other_deduction, 2
                    )

                    # ── Company contributions ──
                    co_pension = round(base_wage * cp['si_pension_co'], 2)
                    co_medical = round(base_wage * cp['si_medical_co'], 2)
                    co_unemployment = round(base_wage * cp['si_unemployment_co'], 2)
                    co_injury = round(base_wage * cp['si_injury_co'], 2)
                    co_maternity = round(base_wage * cp['si_maternity_co'], 2)
                    co_housing = round(base_wage * cp['housing_fund_co'], 2)
                    co_total = round(
                        co_pension + co_medical + co_unemployment
                        + co_injury + co_maternity + co_housing, 2
                    )

                    # ── Gross / Net ──
                    gross_salary = total_income
                    net_salary = round(
                        total_income - total_special_deduction
                        - total_sad_monthly - total_other_deduction
                        - tax_this_month, 2
                    )

                    cur.execute("""
                        INSERT OR REPLACE INTO hr_employee_salary (
                            employee_id, salary_month,
                            income_wage, income_bonus_yearly,
                            income_bonus_quarterly, income_bonus_monthly,
                            income_bonus_performance, income_bonus_other,
                            allowance_transport, allowance_meal,
                            allowance_housing, allowance_high_temp,
                            allowance_shift, allowance_other,
                            total_income, cost_deductible,
                            tax_free_income, other_income_deduct,
                            deduction_si_pension, deduction_si_medical,
                            deduction_si_unemployment, deduction_housing_fund,
                            total_special_deduction,
                            deduction_child_edu, deduction_continue_edu,
                            deduction_housing_loan, deduction_housing_rent,
                            deduction_elderly_care, deduction_3yo_child_care,
                            total_special_add_deduction,
                            deduction_enterprise_annuity,
                            deduction_commercial_health,
                            deduction_tax_deferred_pension,
                            deduction_other_allowable,
                            total_other_deduction,
                            donation_allowable,
                            taxable_income, tax_rate, quick_deduction,
                            tax_payable, tax_reduction,
                            tax_withheld, tax_refund_or_pay,
                            company_si_pension, company_si_medical,
                            company_si_unemployment, company_si_injury,
                            company_si_maternity, company_housing_fund,
                            company_total_benefit,
                            gross_salary, net_salary, remark
                        ) VALUES (
                            ?,?, ?,?,?,?, ?,?, ?,?, ?,?,?,?, ?,?, ?,?,
                            ?,?,?,?, ?, ?,?,?,?,?,?, ?, ?,?,?,?, ?, ?,
                            ?,?,?, ?,?, ?,?, ?,?,?,?,?,?, ?, ?,?,?
                        )
                    """, (
                        eid, salary_month,
                        wage, bonus_yearly,
                        bonus_quarterly, 0.0,
                        0.0, 0.0,
                        allowance_transport, allowance_meal,
                        allowance_housing, allowance_high_temp,
                        allowance_shift, allowance_other,
                        total_income, cost_deductible,
                        0.0, 0.0,
                        si_pension_emp, si_medical_emp,
                        si_unemployment_emp, housing_fund_emp,
                        total_special_deduction,
                        sad_child, sad_cont_edu,
                        sad_loan, sad_rent,
                        sad_elderly, sad_3yo,
                        total_sad_monthly,
                        annuity,
                        0.0,
                        0.0,
                        0.0,
                        total_other_deduction,
                        0.0,
                        taxable_income_month, rate, quick,
                        tax_this_month, 0.0,
                        cum_tax, tax_this_month,
                        co_pension, co_medical,
                        co_unemployment, co_injury,
                        co_maternity, co_housing,
                        co_total,
                        gross_salary, net_salary, None,
                    ))

        print(f"  {company_name}: {len(tpl['employees'])} employees x 36 months done.")

    print("[F] HR data fill complete.")


# ══════════════════════════════════════════════════════════════════════════
# Section G: Recalculate financial_metrics_item for C1 and C2
# ══════════════════════════════════════════════════════════════════════════
def fill_metrics_v2(conn):
    print("[G] Recalculating financial_metrics_item for C1 and C2...")
    # Must commit pending changes before calling external module
    conn.commit()

    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database.calculate_metrics_v2 import calculate_and_save_v2

    c1_id = COMPANIES['C1']['taxpayer_id']
    c2_id = COMPANIES['C2']['taxpayer_id']

    print(f"  Calculating metrics for C1 ({c1_id})...")
    calculate_and_save_v2(db_path=DB_PATH, taxpayer_id=c1_id)
    print(f"  Calculating metrics for C2 ({c2_id})...")
    calculate_and_save_v2(db_path=DB_PATH, taxpayer_id=c2_id)

    print("[G] Metrics v2 recalculation complete.")


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════
def main():
    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        fill_business_registration(conn)   # A
        fill_eit_c2(conn)                  # B
        fill_eit_shareholders(conn)        # C
        fill_invoices(conn)                # D
        fill_profile_and_credit(conn)      # E
        fill_hr_data(conn)                 # F
        conn.commit()
        fill_metrics_v2(conn)              # G (commits internally)

        # ── Verification ──
        print("\n=== Verification ===")
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM company_business_registration")
        print(f"  company_business_registration rows: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM eit_annual_shareholder")
        print(f"  eit_annual_shareholder rows: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(DISTINCT company_code) FROM hr_employee_info")
        print(f"  hr_employee_info companies: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM hr_employee_info")
        print(f"  hr_employee_info rows: {cur.fetchone()[0]}")

        cur.execute("SELECT COUNT(*) FROM hr_employee_salary")
        print(f"  hr_employee_salary rows: {cur.fetchone()[0]}")

        cur.execute(
            "SELECT COUNT(DISTINCT taxpayer_id) FROM financial_metrics_item"
        )
        print(f"  financial_metrics_item taxpayers: {cur.fetchone()[0]}")

        print("\nAll fill operations completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

