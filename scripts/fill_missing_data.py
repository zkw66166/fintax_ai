#!/usr/bin/env python3
"""
fill_missing_data.py — 补全 fintax_ai.db 中缺失的示例数据

目标企业：
1. 博雅文化传媒有限公司 (91110108MA01AAAAA1) — 小规模纳税人/企业会计准则
2. 恒泰建材有限公司 (91320200MA02BBBBB2) — 一般纳税人/小企业会计准则
3. 华兴科技/鑫源贸易 — 补充2024年HR薪资数据

原则：
- 只做 INSERT，不做 UPDATE/DELETE
- 先检查是否已存在，避免重复插入
- 数据与已有财务数据保持一致
"""

import sqlite3
import os
import sys
import random
import hashlib
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'fintax_ai.db')

# ── 企业基本信息 ──────────────────────────────────────────────
BY_ID = '91110108MA01AAAAA1'  # 博雅文化传媒
HT_ID = '91320200MA02BBBBB2'  # 恒泰建材
HX_ID = '91310000MA1FL8XQ30'  # 华兴科技
XY_ID = '92440300MA5EQXL17P'  # 鑫源贸易

ETL_BATCH = 'ETL_FILL_20260314'


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def row_exists(cur, table, where_clause, params):
    cur.execute(f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1", params)
    return cur.fetchone() is not None


# ═══════════════════════════════════════════════════════════════
# 1. EIT 年报数据
# ═══════════════════════════════════════════════════════════════

def get_profit_annual(cur, taxpayer_id, year):
    """从利润表获取年度累计数据作为EIT参考"""
    cur.execute("""
        SELECT item_name, cumulative_amount FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY item_name ORDER BY revision_no DESC
            ) rn FROM fs_income_statement_item
            WHERE taxpayer_id=? AND period_year=? AND period_month=12
        ) WHERE rn=1
    """, (taxpayer_id, year))
    return {r['item_name']: r['cumulative_amount'] or 0 for r in cur.fetchall()}


def fill_eit_annual(cur, taxpayer_id, years, company_info):
    """插入EIT年报: filing + main + basic_info + shareholder"""
    info = company_info
    for year in years:
        filing_id = f"{taxpayer_id}_{year}_0"
        if row_exists(cur, 'eit_annual_filing', 'filing_id=?', (filing_id,)):
            print(f"  [skip] eit_annual_filing {filing_id} already exists")
            continue

        profit = get_profit_annual(cur, taxpayer_id, year)
        revenue = profit.get('一、营业收入', profit.get('营业收入', 0))
        cost = profit.get('减：营业成本', profit.get('营业成本', 0))
        tax_surcharge = profit.get('税金及附加', 0)
        selling_exp = profit.get('销售费用', 0)
        admin_exp = profit.get('管理费用', 0)
        rd_exp = profit.get('研发费用', 0)
        fin_exp = profit.get('财务费用', 0)
        op_profit = profit.get('三、营业利润', profit.get('营业利润', 0))
        non_op_income = profit.get('加：营业外收入', 0)
        non_op_exp = profit.get('减：营业外支出', 0)
        total_profit = profit.get('四、利润总额', profit.get('利润总额', 0))
        net_profit = profit.get('五、净利润', profit.get('净利润', 0))

        # filing
        cur.execute("""
            INSERT INTO eit_annual_filing
            (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
             preparer, submitted_at, etl_batch_id, etl_confidence)
            VALUES (?,?,?,0,'元',?,?,?,1.0)
        """, (filing_id, taxpayer_id, year, info['legal_rep'],
              f"{year+1}-05-15", ETL_BATCH))

        # main
        tax_rate = info['eit_rate']
        taxable_income = max(total_profit, 0)
        tax_payable = round(taxable_income * tax_rate, 2)
        prepaid = round(tax_payable * 0.95, 2)  # 预缴约95%

        cur.execute("""
            INSERT INTO eit_annual_main
            (filing_id, revenue, cost, taxes_surcharges, selling_expenses,
             admin_expenses, rd_expenses, financial_expenses,
             operating_profit, non_operating_income, non_operating_expenses,
             total_profit, taxable_income, tax_rate, tax_payable,
             less_prepaid_tax, tax_payable_or_refund, final_tax_payable_or_refund)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (filing_id, revenue, cost, tax_surcharge, selling_exp,
              admin_exp, rd_exp, fin_exp, op_profit, non_op_income, non_op_exp,
              total_profit, taxable_income, tax_rate, tax_payable,
              prepaid, round(tax_payable - prepaid, 2),
              round(tax_payable - prepaid, 2)))

        # basic_info
        cur.execute("""
            INSERT INTO eit_annual_basic_info
            (filing_id, tax_return_type_code, asset_avg, employee_avg,
             industry_code, small_micro_enterprise, listed_company,
             accounting_standard_code)
            VALUES (?,?,?,?,?,?,?,?)
        """, (filing_id, 'A', info['asset_avg'], info['employee_avg'],
              info['industry_code'], info['small_micro'], '否',
              info['acct_std_code']))

        # shareholders
        for sh in info['shareholders']:
            if row_exists(cur, 'eit_annual_shareholder',
                          'filing_id=? AND shareholder_name=?',
                          (filing_id, sh['name'])):
                continue
            cur.execute("""
                INSERT INTO eit_annual_shareholder
                (filing_id, shareholder_name, id_type, id_number,
                 investment_ratio, nationality_or_address)
                VALUES (?,?,?,?,?,?)
            """, (filing_id, sh['name'], sh['id_type'], sh['id_number'],
                  sh['ratio'], sh['address']))

        print(f"  [ok] eit_annual {filing_id}")


def fill_eit_quarter(cur, taxpayer_id, year_quarters, company_info):
    """插入EIT季报: filing + main"""
    info = company_info
    for year, quarter in year_quarters:
        filing_id = f"{taxpayer_id}_{year}Q{quarter}_0"
        if row_exists(cur, 'eit_quarter_filing', 'filing_id=?', (filing_id,)):
            print(f"  [skip] eit_quarter {filing_id}")
            continue

        # 从利润表获取该季度累计数据
        end_month = quarter * 3
        cur.execute("""
            SELECT item_name, cumulative_amount FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY item_name ORDER BY revision_no DESC
                ) rn FROM fs_income_statement_item
                WHERE taxpayer_id=? AND period_year=? AND period_month=?
            ) WHERE rn=1
        """, (taxpayer_id, year, end_month))
        profit = {r['item_name']: r['cumulative_amount'] or 0 for r in cur.fetchall()}

        revenue = profit.get('一、营业收入', profit.get('营业收入', 0))
        cost = profit.get('减：营业成本', profit.get('营业成本', 0))
        total_profit = profit.get('四、利润总额', profit.get('利润总额', 0))

        tax_rate = info['eit_rate']
        actual_profit = max(total_profit, 0)
        tax_payable = round(actual_profit * tax_rate, 2)
        # 前几季度已预缴
        prev_prepaid = 0
        for pq in range(1, quarter):
            prev_fid = f"{taxpayer_id}_{year}Q{pq}_0"
            cur.execute("SELECT current_tax_payable_or_refund FROM eit_quarter_main WHERE filing_id=?", (prev_fid,))
            r = cur.fetchone()
            if r:
                prev_prepaid += (r[0] or 0)

        current_due = round(tax_payable - prev_prepaid, 2)

        # filing
        submit_month = end_month + 1
        submit_year = year if submit_month <= 12 else year + 1
        if submit_month > 12:
            submit_month -= 12
        cur.execute("""
            INSERT INTO eit_quarter_filing
            (filing_id, taxpayer_id, period_year, period_quarter, revision_no,
             amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence)
            VALUES (?,?,?,?,0,'元',?,?,?,1.0)
        """, (filing_id, taxpayer_id, year, quarter, info['legal_rep'],
              f"{submit_year}-{submit_month:02d}-15", ETL_BATCH))

        # main
        cur.execute("""
            INSERT INTO eit_quarter_main
            (filing_id, employee_quarter_avg, asset_quarter_avg,
             small_micro_enterprise, revenue, cost, total_profit,
             actual_profit, tax_rate, tax_payable,
             less_prepaid_tax_current_year, current_tax_payable_or_refund,
             final_tax_payable_or_refund)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (filing_id, info['employee_avg'], info['asset_avg'],
              info['small_micro'], revenue, cost, total_profit,
              actual_profit, tax_rate, tax_payable,
              prev_prepaid, current_due, current_due))

        print(f"  [ok] eit_quarter {filing_id}")


# ═══════════════════════════════════════════════════════════════
# 2. 发票数据
# ═══════════════════════════════════════════════════════════════

def get_vat_monthly(cur, taxpayer_id, year, month):
    """从VAT申报获取月度销售额/税额"""
    # 尝试小规模
    cur.execute("""
        SELECT sales_3percent, tax_due_current
        FROM vw_vat_return_small
        WHERE taxpayer_id=? AND period_year=? AND period_month=?
        LIMIT 1
    """, (taxpayer_id, year, month))
    r = cur.fetchone()
    if r:
        return {'sales': r[0] or 0, 'tax': r[1] or 0, 'rate': '3%', 'type': 'small'}
    # 尝试一般纳税人
    cur.execute("""
        SELECT sales_taxable_rate, output_tax, input_tax
        FROM vw_vat_return_general
        WHERE taxpayer_id=? AND period_year=? AND period_month=?
        LIMIT 1
    """, (taxpayer_id, year, month))
    r = cur.fetchone()
    if r:
        return {'sales': r[0] or 0, 'output_tax': r[1] or 0,
                'input_tax': r[2] or 0, 'rate': '13%', 'type': 'general'}
    return None


PURCHASE_SELLERS = [
    ("北京创意设计有限公司", "91110105MA01CCCC01"),
    ("上海文化用品有限公司", "91310000MA01DDDD02"),
    ("广州印刷包装有限公司", "91440100MA01EEEE03"),
    ("深圳数码科技有限公司", "91440300MA01FFFF04"),
    ("杭州办公设备有限公司", "91330100MA01GGGG05"),
]

SALES_BUYERS = [
    ("北京阳光传媒集团", "91110000MA01HHHH01"),
    ("上海文化发展有限公司", "91310000MA01IIII02"),
    ("广州新视界广告有限公司", "91440100MA01JJJJ03"),
    ("深圳创新文化有限公司", "91440300MA01KKKK04"),
    ("成都天府文化传播有限公司", "91510100MA01LLLL05"),
]

HT_PURCHASE_SELLERS = [
    ("江苏华建水泥有限公司", "91320000MA02CCCC01"),
    ("浙江永固钢材有限公司", "91330000MA02DDDD02"),
    ("山东鲁能建材有限公司", "91370000MA02EEEE03"),
    ("安徽皖南砂石有限公司", "91340000MA02FFFF04"),
    ("上海宝钢金属材料有限公司", "91310000MA02GGGG05"),
]

HT_SALES_BUYERS = [
    ("无锡万达建设工程有限公司", "91320200MA02HHHH01"),
    ("苏州恒基房地产开发有限公司", "91320500MA02IIII02"),
    ("南京城建集团有限公司", "91320100MA02JJJJ03"),
    ("常州龙城建筑有限公司", "91320400MA02KKKK04"),
    ("上海浦东建设有限公司", "91310000MA02LLLL05"),
]

GOODS_BY = ["广告设计服务", "视频制作服务", "活动策划服务", "品牌推广服务", "新媒体运营服务"]
GOODS_HT = ["普通硅酸盐水泥", "螺纹钢HRB400", "中砂", "石子", "防水涂料"]


def fill_invoices(cur, taxpayer_id, months, company_info):
    """插入进项/销项发票"""
    info = company_info
    sellers = info['purchase_sellers']
    buyers = info['sales_buyers']
    goods_list = info['goods']

    for year, month in months:
        vat = get_vat_monthly(cur, taxpayer_id, year, month)
        if not vat:
            continue

        # ── 进项发票 ──
        inv_pk_p = f"INV_P_{taxpayer_id}_{year}{month:02d}_001"
        if not row_exists(cur, 'inv_spec_purchase',
                          'taxpayer_id=? AND period_year=? AND period_month=?',
                          (taxpayer_id, year, month)):
            seller = sellers[(year * 12 + month) % len(sellers)]
            goods = goods_list[(year * 12 + month) % len(goods_list)]

            if vat['type'] == 'small':
                # 小规模进项：按成本的60%估算
                amount = round(vat['sales'] * 0.6, 2)
                tax_rate_str = '3%'
                tax_amt = round(amount * 0.03, 2)
            else:
                amount = round(vat.get('input_tax', 0) / 0.13, 2) if vat.get('input_tax') else round(vat['sales'] * 0.7, 2)
                tax_rate_str = '13%'
                tax_amt = round(amount * 0.13, 2)

            cur.execute("""
                INSERT INTO inv_spec_purchase
                (taxpayer_id, period_year, period_month, invoice_format,
                 invoice_pk, line_no, seller_tax_id, seller_name,
                 buyer_tax_id, buyer_name, invoice_date,
                 goods_name, amount, tax_rate, tax_amount, total_amount,
                 invoice_type, invoice_status, is_positive, invoice_source,
                 submitted_at, etl_batch_id)
                VALUES (?,?,?,'数电',?,1,?,?,?,?,?,?,?,?,?,?,
                        '增值税专用发票','正常','Y','认证',?,?)
            """, (taxpayer_id, year, month, inv_pk_p,
                  seller[1], seller[0], taxpayer_id, info['name'],
                  f"{year}-{month:02d}-15", goods,
                  amount, tax_rate_str, tax_amt, round(amount + tax_amt, 2),
                  f"{year}-{month:02d}-20", ETL_BATCH))

        # ── 销项发票 ──
        inv_pk_s = f"INV_S_{taxpayer_id}_{year}{month:02d}_001"
        if not row_exists(cur, 'inv_spec_sales',
                          'taxpayer_id=? AND period_year=? AND period_month=?',
                          (taxpayer_id, year, month)):
            buyer = buyers[(year * 12 + month) % len(buyers)]

            if vat['type'] == 'small':
                amount = round(vat['sales'], 2)
                tax_amt = round(vat['tax'], 2)
            else:
                amount = round(vat['sales'], 2)
                tax_amt = round(vat.get('output_tax', amount * 0.13), 2)

            cur.execute("""
                INSERT INTO inv_spec_sales
                (taxpayer_id, period_year, period_month, invoice_format,
                 invoice_pk, line_no, seller_tax_id, seller_name,
                 buyer_tax_id, buyer_name, invoice_date,
                 amount, tax_amount, total_amount,
                 invoice_type, invoice_status, is_positive, invoice_source,
                 submitted_at, etl_batch_id)
                VALUES (?,?,?,'数电',?,1,?,?,?,?,?,?,?,?,
                        '增值税专用发票','正常','Y','开具',?,?)
            """, (taxpayer_id, year, month, inv_pk_s,
                  taxpayer_id, info['name'], buyer[1], buyer[0],
                  f"{year}-{month:02d}-10",
                  amount, tax_amt, round(amount + tax_amt, 2),
                  f"{year}-{month:02d}-15", ETL_BATCH))

    print(f"  [ok] invoices for {taxpayer_id}")


# ═══════════════════════════════════════════════════════════════
# 3. 财务指标数据
# ═══════════════════════════════════════════════════════════════

METRICS_DEF = [
    # (metric_code, metric_name, metric_category, metric_unit)
    # — must match financial_metrics_item_dict exactly
    ("current_ratio", "流动比率", "偿债能力", ""),
    ("quick_ratio", "速动比率", "偿债能力", ""),
    ("debt_ratio", "资产负债率", "偿债能力", "%"),
    ("cash_debt_coverage", "现金债务保障比率", "偿债能力", "%"),
    ("gross_margin", "毛利率", "盈利能力", "%"),
    ("net_margin", "净利率", "盈利能力", "%"),
    ("roe", "净资产收益率(ROE)", "盈利能力", "%"),
    ("net_profit_growth", "净利润增长率", "盈利能力", "%"),
    ("asset_turnover", "总资产周转率", "营运能力", "次"),
    ("inventory_turnover", "存货周转率", "营运能力", "次"),
    ("ar_turnover", "应收账款周转率", "营运能力", "次"),
    ("ar_days", "应收款周转天数", "营运能力", "天"),
    ("revenue_growth", "营业收入增长率", "成长能力", "%"),
    ("asset_growth", "资产增长率", "成长能力", "%"),
    ("cash_to_revenue", "销售收现比", "现金流", ""),
    ("admin_expense_ratio", "管理费用率", "费用控制", "%"),
    ("sales_expense_ratio", "销售费用率", "费用控制", "%"),
    ("vat_burden", "增值税税负率", "税负率类", "%"),
    ("eit_burden", "企业所得税税负率", "税负率类", "%"),
    ("total_tax_burden", "综合税负率", "税负率类", "%"),
    ("output_input_ratio", "销项进项配比率", "增值税重点指标", ""),
    ("transfer_out_ratio", "进项税额转出占比", "增值税重点指标", "%"),
    ("taxable_income_ratio", "应税所得率", "所得税重点指标", "%"),
    ("invoice_anomaly_ratio", "发票开具异常率", "风险预警类", "%"),
    ("zero_filing_ratio", "零申报率", "风险预警类", "%"),
]


def eval_level(code, value):
    """简单评级"""
    if code == 'debt_ratio':
        if value < 40: return '优'
        if value < 60: return '良'
        if value < 70: return '中'
        return '差'
    if code in ('gross_margin', 'net_margin', 'roe', 'roa'):
        if value > 20: return '优'
        if value > 10: return '良'
        if value > 5: return '中'
        return '差'
    if code == 'current_ratio':
        if value > 2: return '优'
        if value > 1.5: return '良'
        if value > 1: return '中'
        return '差'
    return '良'


def fill_financial_metrics(cur, taxpayer_id, months):
    """基于已有财务数据计算并插入财务指标"""
    for year, month in months:
        if row_exists(cur, 'financial_metrics_item',
                      'taxpayer_id=? AND period_year=? AND period_month=?',
                      (taxpayer_id, year, month)):
            continue

        # 获取资产负债表
        cur.execute("""
            SELECT item_name, ending_balance, beginning_balance FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY item_name ORDER BY revision_no DESC
                ) rn FROM fs_balance_sheet_item
                WHERE taxpayer_id=? AND period_year=? AND period_month=?
            ) WHERE rn=1
        """, (taxpayer_id, year, month))
        bs = {}
        for r in cur.fetchall():
            bs[r['item_name']] = {'end': r['ending_balance'] or 0, 'begin': r['beginning_balance'] or 0}

        # 获取利润表(本年累计)
        cur.execute("""
            SELECT item_name, cumulative_amount FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY item_name ORDER BY revision_no DESC
                ) rn FROM fs_income_statement_item
                WHERE taxpayer_id=? AND period_year=? AND period_month=?
            ) WHERE rn=1
        """, (taxpayer_id, year, month))
        pl = {r['item_name']: r['cumulative_amount'] or 0 for r in cur.fetchall()}

        # 获取现金流量表(本年累计)
        cur.execute("""
            SELECT item_name, cumulative_amount FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY item_name ORDER BY revision_no DESC
                ) rn FROM fs_cash_flow_item
                WHERE taxpayer_id=? AND period_year=? AND period_month=?
            ) WHERE rn=1
        """, (taxpayer_id, year, month))
        cf = {r['item_name']: r['cumulative_amount'] or 0 for r in cur.fetchall()}

        # 提取关键数值
        def bs_val(name):
            return bs.get(name, {}).get('end', 0)

        total_assets = bs_val('资产合计') or bs_val('资产总计')
        total_liab = bs_val('负债合计') or bs_val('负债总计')
        equity = bs_val('所有者权益合计') or bs_val('所有者权益（或股东权益）合计') or (total_assets - total_liab)
        current_assets = bs_val('流动资产合计')
        current_liab = bs_val('流动负债合计')
        inventory = bs_val('存货')
        ar = bs_val('应收账款')
        cash = bs_val('货币资金')

        revenue = pl.get('一、营业收入', pl.get('营业收入', 0))
        cost = pl.get('减：营业成本', pl.get('营业成本', 0))
        net_profit = pl.get('五、净利润', pl.get('净利润', 0))
        op_profit = pl.get('三、营业利润', pl.get('营业利润', 0))
        total_profit = pl.get('四、利润总额', pl.get('利润总额', 0))
        selling_exp = pl.get('销售费用', 0)
        admin_exp = pl.get('管理费用', 0)
        rd_exp = pl.get('研发费用', 0)
        fin_exp = pl.get('财务费用', 0)

        op_cash = cf.get('经营活动产生的现金流量净额', 0)

        # 获取VAT税额
        cur.execute("""
            SELECT tax_supplement_refund FROM vw_vat_return_small
            WHERE taxpayer_id=? AND period_year=? AND period_month=? LIMIT 1
        """, (taxpayer_id, year, month))
        r = cur.fetchone()
        vat_tax = r[0] if r else 0
        if not vat_tax:
            cur.execute("""
                SELECT supplement_refund FROM vw_vat_return_general
                WHERE taxpayer_id=? AND period_year=? AND period_month=? LIMIT 1
            """, (taxpayer_id, year, month))
            r = cur.fetchone()
            vat_tax = r[0] if r else 0

        # 计算指标
        def safe_div(a, b):
            return round(a / b, 2) if b and b != 0 else 0

        annualize = 12 / month if month > 0 else 1
        total_cost = cost + selling_exp + admin_exp + fin_exp

        metrics = {
            'current_ratio': safe_div(current_assets, current_liab),
            'quick_ratio': safe_div(current_assets - inventory, current_liab),
            'debt_ratio': safe_div(total_liab * 100, total_assets),
            'cash_debt_coverage': safe_div(op_cash * 100, total_liab) if total_liab else 0,
            'gross_margin': safe_div((revenue - cost) * 100, revenue),
            'net_margin': safe_div(net_profit * 100, revenue),
            'roe': safe_div(net_profit * annualize * 100, equity),
            'net_profit_growth': 0,  # 需要上年同期
            'asset_turnover': safe_div(revenue * annualize, total_assets),
            'inventory_turnover': safe_div(cost * annualize, inventory) if inventory else 0,
            'ar_turnover': safe_div(revenue * annualize, ar) if ar else 0,
            'ar_days': safe_div(ar * month * 30, revenue) if revenue else 0,
            'revenue_growth': 0,
            'asset_growth': 0,
            'cash_to_revenue': safe_div(op_cash, revenue / month) if revenue and month else 0,
            'admin_expense_ratio': safe_div(admin_exp * 100, revenue),
            'sales_expense_ratio': safe_div(selling_exp * 100, revenue),
            'vat_burden': safe_div(vat_tax * 100, revenue / month) if revenue else 0,
            'eit_burden': None,  # 月度不计算
            'total_tax_burden': safe_div((vat_tax + safe_div(total_profit * 0.25, 12)) * 100, revenue / month) if revenue else 0,
            'output_input_ratio': 1.2,  # 默认值
            'transfer_out_ratio': 2.0,  # 默认值
            'taxable_income_ratio': None,  # 月度不计算
            'invoice_anomaly_ratio': 0,
            'zero_filing_ratio': None,  # 月度不计算
        }

        # 尝试计算增长率（需要上年同期）
        for growth_code, growth_item, source in [
            ('revenue_growth', '一、营业收入', 'pl'),
            ('net_profit_growth', '五、净利润', 'pl'),
            ('asset_growth', '资产合计', 'bs'),
        ]:
            if source == 'pl':
                cur.execute("""
                    SELECT cumulative_amount FROM fs_income_statement_item
                    WHERE taxpayer_id=? AND period_year=? AND period_month=?
                      AND item_name=?
                    ORDER BY revision_no DESC LIMIT 1
                """, (taxpayer_id, year - 1, month, growth_item))
            else:
                cur.execute("""
                    SELECT ending_balance FROM fs_balance_sheet_item
                    WHERE taxpayer_id=? AND period_year=? AND period_month=?
                      AND item_name=?
                    ORDER BY revision_no DESC LIMIT 1
                """, (taxpayer_id, year - 1, month, growth_item))
            r = cur.fetchone()
            if r and r[0] and r[0] != 0:
                current_val = pl.get(growth_item, 0) if source == 'pl' else bs_val(growth_item)
                metrics[growth_code] = safe_div((current_val - r[0]) * 100, abs(r[0]))

        # 插入
        for mdef in METRICS_DEF:
            code, name, category, unit = mdef
            val = metrics.get(code)
            display_val = round(val, 2) if val is not None else None
            cur.execute("""
                INSERT INTO financial_metrics_item
                (taxpayer_id, period_year, period_month, period_type,
                 metric_code, metric_name, metric_category,
                 metric_value, metric_unit, evaluation_level)
                VALUES (?,?,?,'monthly',?,?,?,?,?,?)
            """, (taxpayer_id, year, month, code, name, category,
                  display_val, unit, eval_level(code, val) if val is not None else None))

    print(f"  [ok] financial_metrics for {taxpayer_id}")


# ═══════════════════════════════════════════════════════════════
# 4. HR 员工 & 薪资数据
# ═══════════════════════════════════════════════════════════════

BY_EMPLOYEES = [
    # (employee_id, name, gender, birth, edu, edu_deg, major, entry, position_code, position_name, position_type, dept_code, dept_name, is_high_tech)
    ("BY0001", "李明", "1", "1978-05-12", "硕士", 3, "工商管理", "2020-03-15", "GM001", "总经理", "管理", "D01", "总经办", 0),
    ("BY0002", "王芳", "2", "1985-08-20", "本科", 2, "财务管理", "2020-04-01", "FIN01", "财务经理", "管理", "D02", "财务部", 0),
    ("BY0003", "张伟", "1", "1990-03-15", "本科", 2, "广告学", "2020-06-01", "MKT01", "策划总监", "管理", "D03", "策划部", 0),
    ("BY0004", "刘洋", "1", "1992-11-08", "本科", 2, "视觉传达", "2021-01-10", "DES01", "设计师", "研发", "D04", "设计部", 0),
    ("BY0005", "陈静", "2", "1993-06-25", "大专", 1, "市场营销", "2021-03-15", "SAL01", "销售专员", "销售", "D05", "市场部", 0),
    ("BY0006", "赵磊", "1", "1995-01-18", "本科", 2, "新闻传播", "2021-09-01", "MED01", "新媒体运营", "研发", "D03", "策划部", 0),
    ("BY0007", "孙丽", "2", "1994-04-30", "本科", 2, "会计学", "2022-02-15", "FIN02", "出纳", "管理", "D02", "财务部", 0),
    ("BY0008", "周涛", "1", "1991-09-10", "本科", 2, "摄影摄像", "2022-06-01", "MED02", "摄影师", "研发", "D04", "设计部", 0),
]

HT_EMPLOYEES = [
    ("HT0001", "张伟", "1", "1975-03-20", "本科", 2, "土木工程", "2018-06-20", "GM001", "总经理", "管理", "D01", "总经办", 0),
    ("HT0002", "李娜", "2", "1982-07-15", "本科", 2, "财务管理", "2018-07-01", "FIN01", "财务经理", "管理", "D02", "财务部", 0),
    ("HT0003", "王强", "1", "1980-11-05", "大专", 1, "建筑材料", "2018-08-01", "SAL01", "销售经理", "销售", "D03", "销售部", 0),
    ("HT0004", "赵敏", "2", "1988-02-28", "本科", 2, "物流管理", "2019-01-10", "WH001", "仓库主管", "生产", "D04", "仓储部", 0),
    ("HT0005", "刘建国", "1", "1983-06-12", "大专", 1, "机械工程", "2019-03-01", "DRV01", "司机班长", "生产", "D05", "运输部", 0),
    ("HT0006", "陈芳", "2", "1990-09-18", "本科", 2, "会计学", "2019-06-15", "FIN02", "会计", "管理", "D02", "财务部", 0),
    ("HT0007", "杨军", "1", "1986-12-03", "大专", 1, "市场营销", "2019-09-01", "SAL02", "销售专员", "销售", "D03", "销售部", 0),
    ("HT0008", "吴涛", "1", "1992-04-22", "大专", 1, "仓储管理", "2020-01-15", "WH002", "仓管员", "生产", "D04", "仓储部", 0),
    ("HT0009", "孙明", "1", "1985-08-10", "大专", 1, "汽车驾驶", "2020-03-01", "DRV02", "司机", "生产", "D05", "运输部", 0),
    ("HT0010", "周丽", "2", "1993-01-25", "本科", 2, "电子商务", "2020-06-01", "SAL03", "销售专员", "销售", "D03", "销售部", 0),
    ("HT0011", "马超", "1", "1987-05-15", "大专", 1, "建筑工程", "2020-09-01", "WH003", "仓管员", "生产", "D04", "仓储部", 0),
    ("HT0012", "黄蓉", "2", "1995-10-08", "本科", 2, "人力资源", "2021-01-10", "HR001", "人事专员", "管理", "D01", "总经办", 0),
    ("HT0013", "林峰", "1", "1989-07-20", "大专", 1, "物流管理", "2021-04-01", "DRV03", "司机", "生产", "D05", "运输部", 0),
    ("HT0014", "郑伟", "1", "1991-03-12", "大专", 1, "建材销售", "2021-08-01", "SAL04", "销售专员", "销售", "D03", "销售部", 0),
    ("HT0015", "何芳", "2", "1994-12-05", "大专", 1, "行政管理", "2022-01-15", "ADM01", "行政文员", "管理", "D01", "总经办", 0),
]

# 薪资基准（月薪，元）
BY_SALARY_BASE = {
    "BY0001": 18000, "BY0002": 12000, "BY0003": 14000, "BY0004": 10000,
    "BY0005": 7000, "BY0006": 8000, "BY0007": 7500, "BY0008": 9000,
}

HT_SALARY_BASE = {
    "HT0001": 20000, "HT0002": 12000, "HT0003": 14000, "HT0004": 9000,
    "HT0005": 7000, "HT0006": 8000, "HT0007": 7500, "HT0008": 5500,
    "HT0009": 6000, "HT0010": 7000, "HT0011": 5500, "HT0012": 7000,
    "HT0013": 6000, "HT0014": 7000, "HT0015": 5000,
}


def calc_age(birth_str, ref_date='2025-12-31'):
    b = datetime.strptime(birth_str, '%Y-%m-%d')
    r = datetime.strptime(ref_date, '%Y-%m-%d')
    return r.year - b.year - ((r.month, r.day) < (b.month, b.day))


def calc_work_years(entry_str, ref_date='2025-12-31'):
    e = datetime.strptime(entry_str, '%Y-%m-%d')
    r = datetime.strptime(ref_date, '%Y-%m-%d')
    return round((r - e).days / 365.25, 1)


def fill_hr_employees(cur, company_code, company_name, employees):
    """插入员工信息"""
    for emp in employees:
        eid = emp[0]
        if row_exists(cur, 'hr_employee_info', 'employee_id=?', (eid,)):
            continue
        age = calc_age(emp[3])
        wyears = calc_work_years(emp[7])
        cur.execute("""
            INSERT INTO hr_employee_info
            (company_code, company_name, dept_code, dept_name, dept_level,
             employee_id, employee_name, id_card, gender, birth_date, age,
             education, education_degree, major, entry_date, work_years,
             total_work_years, position_code, position_name, position_type,
             employment_type, social_insurance_city, is_on_the_job,
             is_high_tech_person)
            VALUES (?,?,?,?,1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'正式',?,1,?)
        """, (company_code, company_name, emp[11], emp[12],
              eid, emp[1], f"{'1' * 15}{emp[3][:4]}{emp[3][5:7]}", emp[2], emp[3], age,
              emp[4], emp[5], emp[6], emp[7], wyears, wyears + 2,
              emp[8], emp[9], emp[10],
              '北京' if company_code == 'BY001' else '无锡',
              emp[13]))
    print(f"  [ok] hr_employee_info for {company_code}")


def fill_hr_salary(cur, salary_base, salary_months):
    """插入员工薪资数据"""
    count = 0
    for eid, base in salary_base.items():
        for year, month in salary_months:
            sm = f"{year}{month:02d}"
            if row_exists(cur, 'hr_employee_salary',
                          'employee_id=? AND salary_month=?', (eid, sm)):
                continue

            # 年度调薪：每年涨5%
            adj = 1 + 0.05 * (year - 2023)
            wage = round(base * adj, 2)
            # 季度奖金
            bonus_q = round(wage * 0.1, 2) if month in (3, 6, 9, 12) else 0
            # 月度绩效
            bonus_perf = round(wage * 0.08 * (0.9 + random.random() * 0.2), 2)
            # 补贴
            transport = 500
            meal = 600
            housing_allow = 800 if base >= 10000 else 400

            total_income = round(wage + bonus_q + bonus_perf + transport + meal + housing_allow, 2)

            # 五险一金（个人）
            si_pension = round(wage * 0.08, 2)
            si_medical = round(wage * 0.02, 2)
            si_unemploy = round(wage * 0.005, 2)
            housing_fund = round(wage * 0.07, 2)
            total_special = round(si_pension + si_medical + si_unemploy + housing_fund, 2)

            # 专项附加扣除（简化）
            child_edu = 2000 if base >= 12000 else 0
            housing_loan = 1000
            elderly_care = 3000 if base >= 15000 else 1500
            total_special_add = child_edu + housing_loan + elderly_care

            # 应纳税所得额（累计预扣法简化为月度）
            cost_deduct = 5000
            taxable = max(total_income - cost_deduct - total_special - total_special_add, 0)

            # 个税（简化月度税率）
            if taxable <= 3000:
                tax = round(taxable * 0.03, 2)
                qd = 0
                rate = 3
            elif taxable <= 12000:
                tax = round(taxable * 0.10 - 210, 2)
                qd = 210
                rate = 10
            elif taxable <= 25000:
                tax = round(taxable * 0.20 - 1410, 2)
                qd = 1410
                rate = 20
            elif taxable <= 35000:
                tax = round(taxable * 0.25 - 2660, 2)
                qd = 2660
                rate = 25
            else:
                tax = round(taxable * 0.30 - 4410, 2)
                qd = 4410
                rate = 30
            tax = max(tax, 0)

            # 企业五险一金
            co_pension = round(wage * 0.16, 2)
            co_medical = round(wage * 0.095, 2)
            co_unemploy = round(wage * 0.005, 2)
            co_injury = round(wage * 0.004, 2)
            co_maternity = round(wage * 0.008, 2)
            co_housing = round(wage * 0.07, 2)
            co_total = round(co_pension + co_medical + co_unemploy + co_injury + co_maternity + co_housing, 2)

            net = round(total_income - total_special - tax, 2)

            cur.execute("""
                INSERT INTO hr_employee_salary
                (employee_id, salary_month, income_wage,
                 income_bonus_quarterly, income_bonus_performance,
                 allowance_transport, allowance_meal, allowance_housing,
                 total_income, cost_deductible,
                 deduction_si_pension, deduction_si_medical,
                 deduction_si_unemployment, deduction_housing_fund,
                 total_special_deduction,
                 deduction_child_edu, deduction_housing_loan,
                 deduction_elderly_care, total_special_add_deduction,
                 taxable_income, tax_rate, quick_deduction,
                 tax_payable, tax_withheld, tax_refund_or_pay,
                 company_si_pension, company_si_medical,
                 company_si_unemployment, company_si_injury,
                 company_si_maternity, company_housing_fund,
                 company_total_benefit, gross_salary, net_salary)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (eid, sm, wage, bonus_q, bonus_perf,
                  transport, meal, housing_allow, total_income, cost_deduct,
                  si_pension, si_medical, si_unemploy, housing_fund, total_special,
                  child_edu, housing_loan, elderly_care, total_special_add,
                  taxable, rate, qd, tax, tax, 0,
                  co_pension, co_medical, co_unemploy, co_injury,
                  co_maternity, co_housing, co_total, total_income, net))
            count += 1

    print(f"  [ok] hr_employee_salary: {count} records inserted")


# ═══════════════════════════════════════════════════════════════
# 5. 工商登记、纳税信用、画像快照
# ═══════════════════════════════════════════════════════════════

def fill_business_registration(cur, taxpayer_id, info):
    """插入工商登记信息"""
    if row_exists(cur, 'company_business_registration',
                  'taxpayer_id=?', (taxpayer_id,)):
        print(f"  [skip] business_registration for {taxpayer_id}")
        return
    cur.execute("""
        INSERT INTO company_business_registration
        (company_name, unified_social_credit_code, company_type,
         operation_status, established_date, legal_representative,
         registered_capital, paid_in_capital, insured_count,
         company_scale, business_scope, registered_address,
         business_term, taxpayer_id, taxpayer_qualification,
         province, city, district, industry,
         industry_level1, industry_level2)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (info['name'], taxpayer_id, info['company_type'],
          '存续', info['establish_date'], info['legal_rep'],
          info['reg_capital_str'], info['paid_capital_str'],
          info['employee_avg'], info['company_scale'],
          info['business_scope'], info['address'],
          f"{info['establish_date']} 至 长期", taxpayer_id,
          info['taxpayer_qual'],
          info['province'], info['city'], info['district'],
          info['industry_name'], info['industry_l1'], info['industry_l2']))
    print(f"  [ok] business_registration for {taxpayer_id}")


def fill_credit_grade(cur, taxpayer_id, years_grades):
    """插入纳税信用等级"""
    for year, grade in years_grades:
        if row_exists(cur, 'taxpayer_credit_grade_year',
                      'taxpayer_id=? AND year=?', (taxpayer_id, year)):
            continue
        cur.execute("""
            INSERT INTO taxpayer_credit_grade_year
            (taxpayer_id, year, credit_grade, published_at, etl_batch_id)
            VALUES (?,?,?,?,?)
        """, (taxpayer_id, year, grade, f"{year}-06-01", ETL_BATCH))
    print(f"  [ok] credit_grade for {taxpayer_id}")


def fill_profile_snapshot(cur, taxpayer_id, months, info):
    """插入画像快照"""
    count = 0
    for year, month in months:
        if row_exists(cur, 'taxpayer_profile_snapshot_month',
                      'taxpayer_id=? AND period_year=? AND period_month=?',
                      (taxpayer_id, year, month)):
            continue
        cur.execute("""
            INSERT INTO taxpayer_profile_snapshot_month
            (taxpayer_id, period_year, period_month, industry_code,
             tax_authority_code, region_code, credit_grade,
             employee_scale, revenue_scale, etl_batch_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (taxpayer_id, year, month, info['industry_code'],
              info['tax_auth_code'], info['region_code'],
              info['credit_grade'], info['employee_scale'],
              info['revenue_scale'], ETL_BATCH))
        count += 1
    print(f"  [ok] profile_snapshot for {taxpayer_id}: {count} records")


# ═══════════════════════════════════════════════════════════════
# 7. 华兴科技/鑫源贸易 2024年薪资补充
# ═══════════════════════════════════════════════════════════════

def fill_hr_salary_supplement(cur, taxpayer_id):
    """为已有员工补充2024年1-12月薪资（仅当2024年缺失时）"""
    # 通过taxpayer_info找到company_code
    company_code_map = {
        '91310000MA1FL8XQ30': 'HX001',
        '92440300MA5EQXL17P': 'XY001',
    }
    company_code = company_code_map.get(taxpayer_id)
    if not company_code:
        print(f"  [skip] hr_salary_supplement: unknown taxpayer_id {taxpayer_id}")
        return

    # 获取该企业所有员工
    cur.execute("SELECT employee_id FROM hr_employee_info WHERE company_code=?", (company_code,))
    employees = [r[0] for r in cur.fetchall()]
    if not employees:
        print(f"  [skip] hr_salary_supplement: no employees for {company_code}")
        return

    # 检查是否已有2024年薪资
    placeholders = ','.join('?' * len(employees))
    cur.execute(f"SELECT COUNT(*) FROM hr_employee_salary WHERE employee_id IN ({placeholders}) AND salary_month LIKE '2024%'", employees)
    if cur.fetchone()[0] > 0:
        print(f"  [skip] hr_salary_supplement 2024 for {company_code}")
        return

    # 获取每个员工2025年平均薪资作为基准
    count = 0
    for eid in employees:
        cur.execute("""
            SELECT AVG(income_wage), AVG(income_bonus_quarterly),
                   AVG(income_bonus_performance),
                   AVG(allowance_transport), AVG(allowance_meal), AVG(allowance_housing),
                   AVG(total_income),
                   AVG(deduction_si_pension), AVG(deduction_si_medical),
                   AVG(deduction_si_unemployment), AVG(deduction_housing_fund),
                   AVG(total_special_deduction),
                   AVG(deduction_child_edu), AVG(deduction_housing_loan),
                   AVG(deduction_elderly_care), AVG(total_special_add_deduction),
                   AVG(tax_rate), AVG(quick_deduction),
                   AVG(company_si_pension), AVG(company_si_medical),
                   AVG(company_si_unemployment), AVG(company_si_injury),
                   AVG(company_si_maternity), AVG(company_housing_fund)
            FROM hr_employee_salary
            WHERE employee_id=? AND salary_month LIKE '2025%'
        """, (eid,))
        r = cur.fetchone()
        if not r or not r[0]:
            continue

        # 2024年薪资 = 2025年 * 0.95（略低）
        wage_base = round((r[0] or 8000) * 0.95, 2)

        for month in range(1, 13):
            sm = f"2024{month:02d}"
            factor = random.uniform(0.97, 1.03)
            wage = round(wage_base * factor, 2)
            bonus_q = round((r[1] or 0) * 0.9 * factor, 2) if month in (3, 6, 9, 12) else 0
            bonus_perf = round((r[2] or 0) * 0.9 * factor, 2)
            transport = round(r[3] or 500, 2)
            meal = round(r[4] or 600, 2)
            housing_allow = round(r[5] or 400, 2)

            total_income = round(wage + bonus_q + bonus_perf + transport + meal + housing_allow, 2)

            si_pension = round(wage * 0.08, 2)
            si_medical = round(wage * 0.02, 2)
            si_unemploy = round(wage * 0.005, 2)
            housing_fund = round(wage * 0.07, 2)
            total_special = round(si_pension + si_medical + si_unemploy + housing_fund, 2)

            child_edu = round(r[12] or 0, 2)
            housing_loan = round(r[13] or 0, 2)
            elderly_care = round(r[14] or 0, 2)
            total_special_add = round(child_edu + housing_loan + elderly_care, 2)

            cost_deduct = 5000
            taxable = max(total_income - cost_deduct - total_special - total_special_add, 0)

            if taxable <= 3000:
                tax = round(taxable * 0.03, 2); qd = 0; rate = 3
            elif taxable <= 12000:
                tax = round(taxable * 0.10 - 210, 2); qd = 210; rate = 10
            elif taxable <= 25000:
                tax = round(taxable * 0.20 - 1410, 2); qd = 1410; rate = 20
            elif taxable <= 35000:
                tax = round(taxable * 0.25 - 2660, 2); qd = 2660; rate = 25
            else:
                tax = round(taxable * 0.30 - 4410, 2); qd = 4410; rate = 30
            tax = max(tax, 0)

            co_pension = round(wage * 0.16, 2)
            co_medical = round(wage * 0.095, 2)
            co_unemploy = round(wage * 0.005, 2)
            co_injury = round(wage * 0.004, 2)
            co_maternity = round(wage * 0.008, 2)
            co_housing = round(wage * 0.07, 2)
            co_total = round(co_pension + co_medical + co_unemploy + co_injury + co_maternity + co_housing, 2)

            net = round(total_income - total_special - tax, 2)

            cur.execute("""
                INSERT INTO hr_employee_salary
                (employee_id, salary_month, income_wage,
                 income_bonus_quarterly, income_bonus_performance,
                 allowance_transport, allowance_meal, allowance_housing,
                 total_income, cost_deductible,
                 deduction_si_pension, deduction_si_medical,
                 deduction_si_unemployment, deduction_housing_fund,
                 total_special_deduction,
                 deduction_child_edu, deduction_housing_loan,
                 deduction_elderly_care, total_special_add_deduction,
                 taxable_income, tax_rate, quick_deduction,
                 tax_payable, tax_withheld, tax_refund_or_pay,
                 company_si_pension, company_si_medical,
                 company_si_unemployment, company_si_injury,
                 company_si_maternity, company_housing_fund,
                 company_total_benefit, gross_salary, net_salary)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (eid, sm, wage, bonus_q, bonus_perf,
                  transport, meal, housing_allow, total_income, cost_deduct,
                  si_pension, si_medical, si_unemploy, housing_fund, total_special,
                  child_edu, housing_loan, elderly_care, total_special_add,
                  taxable, rate, qd, tax, tax, 0,
                  co_pension, co_medical, co_unemploy, co_injury,
                  co_maternity, co_housing, co_total, total_income, net))
            count += 1
    print(f"  [ok] hr_salary_supplement 2024 for {company_code}: {count} records")


# ═══════════════════════════════════════════════════════════════
# 8. 主函数
# ═══════════════════════════════════════════════════════════════

def generate_months(start_year, start_month, end_year, end_month):
    """生成 (year, month) 列表"""
    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def main():
    print("=" * 60)
    print("fill_missing_data.py — 数据缺失补全")
    print("=" * 60)

    conn = get_conn()
    cur = conn.cursor()

    # ── 博雅文化传媒 ──────────────────────────────────────────
    print("\n[1/3] 博雅文化传媒有限公司")
    by_months = generate_months(2024, 1, 2026, 2)
    by_years = [2024, 2025]

    by_info = {
        'name': '博雅文化传媒有限公司',
        'legal_rep': '李明',
        'company_type': '有限责任公司(自然人投资或控股)',
        'establish_date': '2018-03-15',
        'reg_capital_str': '100万元人民币',
        'paid_capital_str': '100万元人民币',
        'employee_avg': 9,
        'asset_avg': 800000,  # 约80万总资产
        'company_scale': '微型',
        'business_scope': '文化艺术交流策划；广告设计、制作、代理、发布；企业形象策划；市场营销策划',
        'address': '北京市海淀区中关村大街1号',
        'taxpayer_qual': '小规模纳税人',
        'province': '北京市', 'city': '北京市', 'district': '海淀区',
        'industry_name': '文化传媒', 'industry_l1': '文化、体育和娱乐业',
        'industry_l2': '广告业',
        'industry_code': 'R8530',
        'eit_rate': 0.05,  # 小微企业优惠税率
        'small_micro': '是',
        'acct_std_code': 'CAS',  # 企业会计准则
        'shareholders': [
            {'name': '李明', 'id_type': '居民身份证', 'id_number': '110108199001011234',
             'ratio': 60, 'address': '北京市海淀区'},
            {'name': '王芳', 'id_type': '居民身份证', 'id_number': '110108199205052345',
             'ratio': 40, 'address': '北京市海淀区'},
        ],
        'tax_rate': 0.03,  # 小规模3%
        'purchase_sellers': [
            ('北京印刷有限公司', '91110000AAAA000001'),
            ('北京广告材料有限公司', '91110000AAAA000002'),
            ('北京办公设备有限公司', '91110000AAAA000003'),
        ],
        'sales_buyers': [
            ('北京某文化发展有限公司', '91110000BBBB000001'),
            ('北京某教育科技有限公司', '91110000BBBB000002'),
            ('北京某商贸有限公司', '91110000BBBB000003'),
        ],
        'goods': ['广告策划服务', '品牌设计服务', '活动策划服务', '视频制作服务'],
    }

    by_profile = {
        'industry_code': 'R8530',
        'tax_auth_code': '11010800',
        'region_code': '110108',
        'credit_grade': 'B',
        'employee_scale': '10人以下',
        'revenue_scale': '500万以下',
    }

    fill_eit_annual(cur, BY_ID, by_years, by_info)
    by_quarters = [(y, q) for y in by_years for q in range(1, 5)]
    fill_eit_quarter(cur, BY_ID, by_quarters, by_info)
    fill_invoices(cur, BY_ID, by_months, by_info)
    fill_financial_metrics(cur, BY_ID, by_months)
    fill_hr_employees(cur, 'BY001', by_info['name'], BY_EMPLOYEES)
    fill_hr_salary(cur, BY_SALARY_BASE, by_months)
    fill_business_registration(cur, BY_ID, by_info)
    fill_credit_grade(cur, BY_ID, [(2024, 'B'), (2025, 'B')])
    fill_profile_snapshot(cur, BY_ID, by_months, by_profile)

    conn.commit()
    print("  [committed] 博雅文化传媒")

    # ── 恒泰建材 ──────────────────────────────────────────────
    print("\n[2/3] 恒泰建材有限公司")
    ht_months = generate_months(2023, 1, 2025, 12)
    ht_years = [2023, 2024, 2025]

    ht_info = {
        'name': '恒泰建材有限公司',
        'legal_rep': '张伟',
        'company_type': '有限责任公司(自然人投资或控股)',
        'establish_date': '2015-06-20',
        'reg_capital_str': '500万元人民币',
        'paid_capital_str': '500万元人民币',
        'employee_avg': 18,
        'asset_avg': 15000000,  # 约1500万总资产
        'company_scale': '小型',
        'business_scope': '建筑材料、装饰材料、五金交电、机电设备销售；建材技术咨询服务',
        'address': '江苏省无锡市梁溪区人民路88号',
        'taxpayer_qual': '一般纳税人',
        'province': '江苏省', 'city': '无锡市', 'district': '梁溪区',
        'industry_name': '建材批发', 'industry_l1': '批发和零售业',
        'industry_l2': '建材批发',
        'industry_code': 'F5172',
        'eit_rate': 0.25,  # 标准税率
        'small_micro': '否',
        'acct_std_code': 'SAS',  # 小企业会计准则
        'shareholders': [
            {'name': '张伟', 'id_type': '居民身份证', 'id_number': '320200198506151234',
             'ratio': 60, 'address': '江苏省无锡市'},
            {'name': '刘洋', 'id_type': '居民身份证', 'id_number': '320200199003202345',
             'ratio': 40, 'address': '江苏省无锡市'},
        ],
        'tax_rate': 0.13,  # 一般纳税人13%
        'purchase_sellers': [
            ('无锡某水泥厂', '91320200CCCC000001'),
            ('无锡某钢材有限公司', '91320200CCCC000002'),
            ('无锡某化工材料有限公司', '91320200CCCC000003'),
        ],
        'sales_buyers': [
            ('无锡某建筑工程有限公司', '91320200DDDD000001'),
            ('无锡某装饰工程有限公司', '91320200DDDD000002'),
            ('无锡某房地产开发有限公司', '91320200DDDD000003'),
        ],
        'goods': ['水泥', '钢材', '砂石', '防水材料', '保温材料'],
    }

    ht_profile = {
        'industry_code': 'F5172',
        'tax_auth_code': '32020000',
        'region_code': '320200',
        'credit_grade': 'A',
        'employee_scale': '10-50人',
        'revenue_scale': '1000-5000万',
    }

    fill_eit_annual(cur, HT_ID, ht_years, ht_info)
    ht_quarters = [(y, q) for y in ht_years for q in range(1, 5)]
    fill_eit_quarter(cur, HT_ID, ht_quarters, ht_info)
    fill_invoices(cur, HT_ID, ht_months, ht_info)
    fill_financial_metrics(cur, HT_ID, ht_months)
    fill_hr_employees(cur, 'HT001', ht_info['name'], HT_EMPLOYEES)
    fill_hr_salary(cur, HT_SALARY_BASE, ht_months)
    fill_business_registration(cur, HT_ID, ht_info)
    fill_credit_grade(cur, HT_ID, [(2023, 'A'), (2024, 'A'), (2025, 'A')])
    fill_profile_snapshot(cur, HT_ID, ht_months, ht_profile)

    conn.commit()
    print("  [committed] 恒泰建材")

    # ── 华兴科技/鑫源贸易 2024年薪资补充 ─────────────────────
    print("\n[3/3] 华兴科技/鑫源贸易 — 2024年薪资补充")
    fill_hr_salary_supplement(cur, HX_ID)
    fill_hr_salary_supplement(cur, XY_ID)

    conn.commit()
    print("  [committed] 薪资补充")

    conn.close()
    print("\n" + "=" * 60)
    print("Done! All missing data filled.")
    print("=" * 60)


if __name__ == '__main__':
    main()