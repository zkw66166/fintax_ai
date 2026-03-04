"""扩展样本数据：为华兴科技生成 2024.01-2026.02 全域数据（覆盖57题测试需求）
数据生成策略：
- 以现有 2025年1月数据为基准值
- 按月递增 1.5-3% + 季节性波动（sin函数）
- 向前推算 2024 年数据（基准值 / 增长因子）
- 向后推算 2026 年数据（基准值 × 增长因子）
- 保持跨域一致性
"""
import sqlite3
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH

HX_ID = '91310000MA1FL8XQ30'  # 华兴科技
XY_ID = '92440300MA5EQXL17P'  # 鑫源贸易

# 月度增长率 + 季节性波动
def _monthly_factor(base_month_offset, growth_rate=0.02, seasonal_amp=0.05):
    """计算相对于基准月(2025-01=0)的乘数因子
    base_month_offset: 距离2025-01的月数（负=过去，正=未来）
    """
    growth = (1 + growth_rate) ** base_month_offset
    seasonal = 1 + seasonal_amp * math.sin(2 * math.pi * base_month_offset / 12)
    return growth * seasonal


def _month_offset(year, month):
    """计算(year,month)相对于2025-01的偏移月数"""
    return (year - 2025) * 12 + (month - 1)


# ============================================================
# 生成月份列表
# ============================================================
def _gen_months(start_year, start_month, end_year, end_month):
    """生成(year, month)列表"""
    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

ALL_MONTHS = _gen_months(2024, 1, 2026, 2)  # 26个月


# ============================================================
# VAT 一般纳税人扩展数据
# ============================================================
# ============================================================
# VAT 一般纳税人扩展数据
# ============================================================
def _insert_general_vat_extended(cur):
    """华兴科技 一般纳税人 2024.01-2026.02 VAT数据"""
    # 基准值（2025-01）
    BASE_SALES = 1000000
    BASE_OUTPUT = 130000
    BASE_INPUT = 95000
    BASE_TRANSFER = 2000

    rows = []
    cum_sales, cum_output, cum_input, cum_transfer, cum_tax = 0, 0, 0, 0, 0

    for year, month in ALL_MONTHS:
        # 跳过已有数据
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.08)

        sales = round(BASE_SALES * f)
        output = round(BASE_OUTPUT * f)
        inp = round(BASE_INPUT * f)
        transfer = round(BASE_TRANSFER * f)
        tax_payable = output - inp + transfer

        # 累计（每年1月重置）
        if month == 1:
            cum_sales, cum_output, cum_input, cum_transfer, cum_tax = 0, 0, 0, 0, 0
        cum_sales += sales
        cum_output += output
        cum_input += inp
        cum_transfer += transfer
        cum_tax += tax_payable

        city_tax = round(tax_payable * 0.07)
        edu = round(tax_payable * 0.03)
        local_edu = round(tax_payable * 0.02)

        def _row(m, it, tr, rev, **kw):
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
            return (HX_ID, year, m, it, tr, rev,
                    None, 'ETL_EXT', None, '元', 1.0, *vals)

        # 本月
        rows.append(_row(month, '一般项目', '本月', 0,
            sales_taxable_rate=sales, output_tax=output, input_tax=inp,
            transfer_out=transfer, tax_payable=tax_payable,
            total_tax_payable=tax_payable, end_credit=0,
            supplement_refund=tax_payable,
            city_maintenance_tax=city_tax, education_surcharge=edu,
            local_education_surcharge=local_edu))
        # 累计
        rows.append(_row(month, '一般项目', '累计', 0,
            sales_taxable_rate=cum_sales, output_tax=cum_output,
            input_tax=cum_input, transfer_out=cum_transfer,
            tax_payable=cum_tax, total_tax_payable=cum_tax))
        # 即征即退（空）
        rows.append(_row(month, '即征即退项目', '本月', 0))
        rows.append(_row(month, '即征即退项目', '累计', 0))

    cols_count = 11 + 41
    placeholders = ','.join(['?'] * cols_count)
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_general VALUES ({placeholders})", rows)
    print(f"  一般纳税人VAT扩展: {len(rows)} 行")


# ============================================================
# VAT 小规模纳税人扩展数据
# ============================================================
def _insert_small_vat_extended(cur):
    """鑫源贸易 小规模纳税人 2024.01-2026.02"""
    BASE_SALES = 200000

    rows = []
    cum_sales, cum_tax = 0, 0

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.015, seasonal_amp=0.06)

        sales = round(BASE_SALES * f)
        spec = round(sales * 0.6)
        other = sales - spec
        tax = round(sales * 0.03)

        if month == 1:
            cum_sales, cum_tax = 0, 0
        cum_sales += sales
        cum_tax += tax

        city_tax = round(tax * 0.07)
        edu = round(tax * 0.03)
        local_edu = round(tax * 0.02)

        def _row(m, it, tr, rev, **kw):
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
            return (XY_ID, year, m, it, tr, rev,
                    None, 'ETL_EXT', None, '元', 1.0, *vals)

        rows.append(_row(month, '货物及劳务', '本期', 0,
            sales_3percent=sales, sales_3percent_invoice_spec=spec,
            sales_3percent_invoice_other=other,
            tax_due_current=tax, tax_due_total=tax, tax_prepaid=0,
            tax_supplement_refund=tax,
            city_maintenance_tax=city_tax, education_surcharge=edu,
            local_education_surcharge=local_edu))
        rows.append(_row(month, '货物及劳务', '累计', 0,
            sales_3percent=cum_sales, tax_due_current=cum_tax,
            tax_due_total=cum_tax, tax_supplement_refund=cum_tax))
        rows.append(_row(month, '服务不动产无形资产', '本期', 0))
        rows.append(_row(month, '服务不动产无形资产', '累计', 0))

    cols_count = 11 + 25
    placeholders = ','.join(['?'] * cols_count)
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_small VALUES ({placeholders})", rows)
    print(f"  小规模纳税人VAT扩展: {len(rows)} 行")


# ============================================================
# EIT 扩展数据
# ============================================================
def _insert_eit_extended(cur):
    """华兴科技 EIT 2023年度 + 2023-2025各季度预缴"""
    # 2023年度汇算清缴
    filing_id = f'{HX_ID}_2023_0'
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_filing
        (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
         preparer, submitted_at, etl_batch_id, etl_confidence)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (filing_id, HX_ID, 2023, 0, '元', '张明', '2024-05-20', 'ETL_EXT', 1.0)
    )
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_basic_info
        (filing_id, tax_return_type_code, asset_avg, employee_avg, industry_code,
         restricted_or_prohibited, small_micro_enterprise, listed_company)
        VALUES (?,?,?,?,?,?,?,?)""",
        (filing_id, 'A', 1800, 78, 'I6510', 0, 0, '否')
    )
    # 2023年度主表
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
         10000000, 7000000, 130000, 420000, 680000,
         250000, 85000, 42000, 68000,
         0, 0, -17000, -8500, 4200,
         1523700, 25000, 4200, 1544500,
         0, 100000, 25000, 0, 0, 1619500,
         0, 0, 0, 1619500,
         0.25, 404875,
         0, 0, 404875,
         0, 0, 404875,
         310000, 94875,
         0, 0, 0,
         0, 0, 0, 94875)
    )
    print(f"  EIT年度: 华兴科技2023年度")

    # 季度预缴数据：2023Q1-Q4, 2024Q1-Q4, 2025Q2-Q4
    quarter_data = [
        # (year, quarter, revenue, cost, total_profit, tax_rate, prepaid)
        (2023, 1, 2400000, 1680000, 300000, 0.25, 75000),
        (2023, 2, 5000000, 3500000, 625000, 0.25, 156250),
        (2023, 3, 7600000, 5320000, 950000, 0.25, 237500),
        (2023, 4, 10000000, 7000000, 1250000, 0.25, 312500),
        (2024, 1, 2800000, 1960000, 350000, 0.25, 87500),
        (2024, 2, 5800000, 4060000, 725000, 0.25, 181250),
        (2024, 3, 8900000, 6230000, 1112500, 0.25, 278125),
        (2024, 4, 12000000, 8400000, 1500000, 0.25, 375000),
        (2025, 2, 7200000, 5040000, 900000, 0.25, 225000),
        (2025, 3, 10800000, 7560000, 1350000, 0.25, 337500),
        (2025, 4, 14400000, 10080000, 1800000, 0.25, 450000),
    ]

    for yr, qtr, rev, cost, tp, rate, prepaid in quarter_data:
        fid = f'{HX_ID}_{yr}Q{qtr}_0'
        actual_profit = tp
        tax_payable = round(actual_profit * rate)

        cur.execute(
            """INSERT OR REPLACE INTO eit_quarter_filing
            (filing_id, taxpayer_id, period_year, period_quarter, revision_no,
             amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (fid, HX_ID, yr, qtr, 0, '元', '张明', f'{yr}-{qtr*3+1:02d}-15', 'ETL_EXT', 1.0)
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
            (fid, 80 + yr - 2023, 1900 + (yr - 2023) * 100, 0, 0,
             rev, cost, tp,
             0, 0, 0, 0, 0, 0,
             actual_profit, rate, tax_payable,
             0, 0, 0, tax_payable,
             0, 0, 0, 0, 0, 0, 0, tax_payable)
        )
    print(f"  EIT季度: {len(quarter_data)} 条")


# ============================================================
# 科目余额扩展数据
# ============================================================
def _insert_account_balance_extended(cur):
    """华兴科技 + 鑫源贸易 科目余额 2024.01-2026.02"""
    # 华兴科技基准值（2025-01 opening）
    HX_BASE = {
        '1001': (50000, '借'),    # 库存现金
        '1002': (2000000, '借'),  # 银行存款
        '1122': (500000, '借'),   # 应收账款
        '1403': (300000, '借'),   # 原材料
        '1601': (5000000, '借'),  # 固定资产
        '1602': (1000000, '贷'),  # 累计折旧
        '1701': (800000, '借'),   # 无形资产
        '1702': (200000, '贷'),   # 累计摊销
        '2202': (400000, '贷'),   # 应付账款
        '2211': (200000, '贷'),   # 应付职工薪酬
        '2221': (50000, '贷'),    # 应交税费
        '222101': (30000, '贷'),  # 应交增值税
        '4001': (3000000, '贷'),  # 实收资本
        '4002': (500000, '贷'),   # 资本公积
        '4103': (0, '贷'),        # 本年利润
        '6001': (0, '贷'),        # 主营业务收入
        '6401': (0, '借'),        # 主营业务成本
        '6602': (0, '借'),        # 管理费用
        '6603': (0, '借'),        # 财务费用
        '6601': (0, '借'),        # 销售费用
    }

    rows = []
    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.05)

        # 动态计算各科目
        cash = round(50000 * f)
        bank = round(2000000 * f)
        ar = round(500000 * f)
        raw_mat = round(300000 * f)
        ap = round(400000 * f)
        emp_pay = round(200000 * f)
        tax_pay = round(50000 * f)
        vat_pay = round(30000 * f)

        # 收入/成本（本月发生额）
        revenue_m = round(1000000 * f)
        cost_m = round(700000 * f)
        admin_m = round(60000 * f)
        fin_m = round(10000 * f)
        sell_m = round(30000 * f)

        # 累计（年初重置）
        if month == 1:
            cum_rev, cum_cost, cum_admin, cum_fin, cum_sell = 0, 0, 0, 0, 0
            cum_profit = 0
        cum_rev += revenue_m
        cum_cost += cost_m
        cum_admin += admin_m
        cum_fin += fin_m
        cum_sell += sell_m
        cum_profit += (revenue_m - cost_m - admin_m - fin_m - sell_m)

        # 期初=上月期末（简化：用因子推算）
        prev_f = _monthly_factor(offset - 1, growth_rate=0.02, seasonal_amp=0.05)

        accts = [
            ('1001', round(50000*prev_f), round(20000*f), round(15000*f), cash),
            ('1002', round(2000000*prev_f), round(1200000*f), round(850000*f), bank),
            ('1122', round(500000*prev_f), round(revenue_m), round(revenue_m*0.8), ar),
            ('1403', round(300000*prev_f), round(200000*f), round(180000*f), raw_mat),
            ('1601', 5000000, 0, 0, 5000000),
            ('1602', round(1000000 + 50000*(offset if offset > 0 else 0)), 0, 50000,
             round(1000000 + 50000*((offset+1) if offset >= 0 else 0))),
            ('1701', 800000, 0, 0, 800000),
            ('1702', round(200000 + 20000*(offset if offset > 0 else 0)), 0, 20000,
             round(200000 + 20000*((offset+1) if offset >= 0 else 0))),
            ('2202', round(400000*prev_f), round(350000*f), round(500000*f), ap),
            ('2211', round(200000*prev_f), round(180000*f), round(250000*f), emp_pay),
            ('2221', round(50000*prev_f), round(50000*f), round(tax_pay), tax_pay),
            ('222101', round(30000*prev_f), round(95000*f), round(130000*f), vat_pay),
            ('4001', 3000000, 0, 0, 3000000),
            ('4002', 500000, 0, 0, 500000),
            ('4103', round(cum_profit - (revenue_m - cost_m - admin_m - fin_m - sell_m)),
             0, round(revenue_m - cost_m - admin_m - fin_m - sell_m), round(cum_profit)),
            ('6001', round(cum_rev - revenue_m), 0, revenue_m, cum_rev),
            ('6401', round(cum_cost - cost_m), cost_m, 0, cum_cost),
            ('6602', round(cum_admin - admin_m), admin_m, 0, cum_admin),
            ('6603', round(cum_fin - fin_m), fin_m, 0, cum_fin),
            ('6601', round(cum_sell - sell_m), sell_m, 0, cum_sell),
        ]

        for code, opening, debit, credit, closing in accts:
            rows.append((HX_ID, year, month, code, 0,
                         None, 'ETL_EXT', None, '元', 1.0,
                         opening, debit, credit, closing))

    # 鑫源贸易简化版
    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.015, seasonal_amp=0.04)

        revenue_m = round(200000 * f)
        cost_m = round(140000 * f)

        xy_accts = [
            ('1001', round(20000*f), round(10000*f), round(8000*f), round(22000*f)),
            ('1002', round(300000*f), round(230000*f), round(180000*f), round(350000*f)),
            ('1122', round(80000*f), round(revenue_m), round(revenue_m*0.75), round(130000*f)),
            ('1405', round(150000*f), round(120000*f), round(100000*f), round(170000*f)),
            ('2202', round(100000*f), round(80000*f), round(130000*f), round(150000*f)),
            ('2211', round(30000*f), round(25000*f), round(35000*f), round(40000*f)),
            ('2221', round(8000*f), round(8000*f), round(6000*f), round(6000*f)),
            ('4001', 200000, 0, 0, 200000),
            ('4103', 0, 0, round(40000*f), round(40000*f)),
            ('6001', 0, 0, revenue_m, revenue_m),
            ('6401', 0, cost_m, 0, cost_m),
            ('5602', 0, round(15000*f), 0, round(15000*f)),
            ('6603', 0, round(5000*f), 0, round(5000*f)),
        ]

        for code, opening, debit, credit, closing in xy_accts:
            rows.append((XY_ID, year, month, code, 0,
                         None, 'ETL_EXT', None, '元', 1.0,
                         opening, debit, credit, closing))

    placeholders = ','.join(['?'] * 14)
    cur.executemany(f"INSERT OR REPLACE INTO account_balance VALUES ({placeholders})", rows)
    print(f"  科目余额扩展: {len(rows)} 行")


# ============================================================
# 资产负债表扩展数据
# ============================================================
def _insert_balance_sheet_extended(cur):
    """华兴科技(ASBE) + 鑫源贸易(ASSE) 资产负债表 2024.01-2026.02"""
    rows = []

    # ASBE项目元数据
    asbe_meta = {
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

    # 华兴科技年初基准（2025年初）
    hx_begin_2025 = {
        'CASH': 2050000, 'ACCOUNTS_RECEIVABLE': 500000, 'PREPAYMENTS': 80000,
        'OTHER_RECEIVABLES': 50000, 'INVENTORY': 300000, 'OTHER_CURRENT_ASSETS': 20000,
        'CURRENT_ASSETS': 3000000, 'FIXED_ASSETS': 4000000, 'INTANGIBLE_ASSETS': 600000,
        'LONG_TERM_DEFERRED_EXPENSES': 30000, 'NON_CURRENT_ASSETS': 4630000,
        'ASSETS': 7630000, 'SHORT_TERM_LOANS': 0,
        'ACCOUNTS_PAYABLE': 400000, 'EMPLOYEE_BENEFITS_PAYABLE': 200000,
        'TAXES_PAYABLE': 50000, 'OTHER_PAYABLES': 80000,
        'CURRENT_LIABILITIES': 730000, 'LIABILITIES': 730000,
        'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
        'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': 3200000,
        'EQUITY': 6900000, 'LIABILITIES_AND_EQUITY': 7630000,
    }

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.05)
        # 年初因子（该年1月的因子）
        begin_offset = _month_offset(year, 1)
        bf = _monthly_factor(begin_offset, growth_rate=0.02, seasonal_amp=0.0)

        # 动态计算期末值
        cash_end = round(2050000 * f)
        ar_end = round(500000 * f * 1.1)
        inv_end = round(300000 * f)
        fixed_end = round(4000000 - 50000 * max(0, offset + 1))
        intang_end = round(600000 - 20000 * max(0, offset + 1))
        if fixed_end < 2000000: fixed_end = 2000000
        if intang_end < 200000: intang_end = 200000

        current_assets = cash_end + ar_end + 80000 + 50000 + inv_end + 20000
        non_current = fixed_end + intang_end + 30000
        total_assets = current_assets + non_current

        short_loans = round(500000 * f) if offset >= 6 else 0
        ap_end = round(400000 * f)
        emp_end = round(200000 * f)
        tax_end = round(50000 * f)
        current_liab = short_loans + ap_end + emp_end + tax_end + 80000
        total_liab = current_liab

        equity = total_assets - total_liab
        retained = equity - 3000000 - 500000 - 200000

        # 年初值
        cash_begin = round(2050000 * bf)
        ar_begin = round(500000 * bf * 1.1)
        inv_begin = round(300000 * bf)
        fixed_begin = round(4000000 - 50000 * max(0, begin_offset))
        intang_begin = round(600000 - 20000 * max(0, begin_offset))
        if fixed_begin < 2000000: fixed_begin = 2000000
        if intang_begin < 200000: intang_begin = 200000

        ca_begin = cash_begin + ar_begin + 80000 + 50000 + inv_begin + 20000
        nca_begin = fixed_begin + intang_begin + 30000
        ta_begin = ca_begin + nca_begin

        sl_begin = round(500000 * bf) if begin_offset >= 6 else 0
        ap_begin = round(400000 * bf)
        emp_begin = round(200000 * bf)
        tax_begin = round(50000 * bf)
        cl_begin = sl_begin + ap_begin + emp_begin + tax_begin + 80000
        tl_begin = cl_begin
        eq_begin = ta_begin - tl_begin
        re_begin = eq_begin - 3000000 - 500000 - 200000

        end_data = {
            'CASH': cash_end, 'ACCOUNTS_RECEIVABLE': ar_end, 'PREPAYMENTS': 80000,
            'OTHER_RECEIVABLES': 50000, 'INVENTORY': inv_end, 'OTHER_CURRENT_ASSETS': 20000,
            'CURRENT_ASSETS': current_assets, 'FIXED_ASSETS': fixed_end,
            'INTANGIBLE_ASSETS': intang_end, 'LONG_TERM_DEFERRED_EXPENSES': 30000,
            'NON_CURRENT_ASSETS': non_current, 'ASSETS': total_assets,
            'SHORT_TERM_LOANS': short_loans,
            'ACCOUNTS_PAYABLE': ap_end, 'EMPLOYEE_BENEFITS_PAYABLE': emp_end,
            'TAXES_PAYABLE': tax_end, 'OTHER_PAYABLES': 80000,
            'CURRENT_LIABILITIES': current_liab, 'LIABILITIES': total_liab,
            'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
            'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': retained,
            'EQUITY': equity, 'LIABILITIES_AND_EQUITY': total_assets,
        }
        begin_data = {
            'CASH': cash_begin, 'ACCOUNTS_RECEIVABLE': ar_begin, 'PREPAYMENTS': 80000,
            'OTHER_RECEIVABLES': 50000, 'INVENTORY': inv_begin, 'OTHER_CURRENT_ASSETS': 20000,
            'CURRENT_ASSETS': ca_begin, 'FIXED_ASSETS': fixed_begin,
            'INTANGIBLE_ASSETS': intang_begin, 'LONG_TERM_DEFERRED_EXPENSES': 30000,
            'NON_CURRENT_ASSETS': nca_begin, 'ASSETS': ta_begin,
            'SHORT_TERM_LOANS': sl_begin,
            'ACCOUNTS_PAYABLE': ap_begin, 'EMPLOYEE_BENEFITS_PAYABLE': emp_begin,
            'TAXES_PAYABLE': tax_begin, 'OTHER_PAYABLES': 80000,
            'CURRENT_LIABILITIES': cl_begin, 'LIABILITIES': tl_begin,
            'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
            'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': re_begin,
            'EQUITY': eq_begin, 'LIABILITIES_AND_EQUITY': ta_begin,
        }

        for code, (name, line, section) in asbe_meta.items():
            rows.append((HX_ID, year, month, 'ASBE', code, 0,
                         None, 'ETL_EXT', None, '元', 1.0,
                         begin_data.get(code, 0), end_data.get(code, 0),
                         name, line, section))

    # 鑫源贸易 ASSE 简化版
    asse_meta = {
        'CASH': ('货币资金', 1, 'ASSET'),
        'ACCOUNTS_RECEIVABLE': ('应收账款', 4, 'ASSET'),
        'INVENTORY': ('存货', 9, 'ASSET'),
        'OTHER_CURRENT_ASSETS': ('其他流动资产', 14, 'ASSET'),
        'CURRENT_ASSETS': ('流动资产合计', 15, 'ASSET'),
        'NON_CURRENT_ASSETS': ('非流动资产合计', 29, 'ASSET'),
        'ASSETS': ('资产合计', 30, 'ASSET'),
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

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.015, seasonal_amp=0.04)
        bf = _monthly_factor(_month_offset(year, 1), growth_rate=0.015, seasonal_amp=0.0)

        cash_e = round(320000 * f)
        ar_e = round(80000 * f)
        inv_e = round(150000 * f)
        ca_e = cash_e + ar_e + inv_e + 10000
        ta_e = ca_e

        ap_e = round(100000 * f)
        emp_e = round(30000 * f)
        tax_e = round(8000 * f)
        cl_e = ap_e + emp_e + tax_e + 22000
        tl_e = cl_e
        eq_e = ta_e - tl_e
        re_e = eq_e - 200000 - 20000

        cash_b = round(320000 * bf)
        ar_b = round(80000 * bf)
        inv_b = round(150000 * bf)
        ca_b = cash_b + ar_b + inv_b + 10000
        ta_b = ca_b
        ap_b = round(100000 * bf)
        emp_b = round(30000 * bf)
        tax_b = round(8000 * bf)
        cl_b = ap_b + emp_b + tax_b + 22000
        tl_b = cl_b
        eq_b = ta_b - tl_b
        re_b = eq_b - 200000 - 20000

        xy_end = {
            'CASH': cash_e, 'ACCOUNTS_RECEIVABLE': ar_e, 'INVENTORY': inv_e,
            'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': ca_e,
            'NON_CURRENT_ASSETS': 0, 'ASSETS': ta_e,
            'ACCOUNTS_PAYABLE': ap_e, 'EMPLOYEE_BENEFITS_PAYABLE': emp_e,
            'TAXES_PAYABLE': tax_e, 'OTHER_PAYABLES': 22000,
            'CURRENT_LIABILITIES': cl_e, 'LIABILITIES': tl_e,
            'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
            'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': re_e,
            'EQUITY': eq_e, 'LIABILITIES_AND_EQUITY': ta_e,
        }
        xy_begin = {
            'CASH': cash_b, 'ACCOUNTS_RECEIVABLE': ar_b, 'INVENTORY': inv_b,
            'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': ca_b,
            'NON_CURRENT_ASSETS': 0, 'ASSETS': ta_b,
            'ACCOUNTS_PAYABLE': ap_b, 'EMPLOYEE_BENEFITS_PAYABLE': emp_b,
            'TAXES_PAYABLE': tax_b, 'OTHER_PAYABLES': 22000,
            'CURRENT_LIABILITIES': cl_b, 'LIABILITIES': tl_b,
            'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
            'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': re_b,
            'EQUITY': eq_b, 'LIABILITIES_AND_EQUITY': ta_b,
        }

        for code, (name, line, section) in asse_meta.items():
            rows.append((XY_ID, year, month, 'ASSE', code, 0,
                         None, 'ETL_EXT', None, '元', 1.0,
                         xy_begin.get(code, 0), xy_end.get(code, 0),
                         name, line, section))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_balance_sheet_item VALUES ({placeholders})", rows)
    print(f"  资产负债表扩展: {len(rows)} 行")


# ============================================================
# 利润表扩展数据
# ============================================================
def _insert_profit_extended(cur):
    """华兴科技(CAS) + 鑫源贸易(SAS) 利润表 2024.01-2026.02"""
    # CAS 科目元数据
    cas_meta = {
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

    rows = []
    # 华兴科技 CAS 基准值（2025-01 current）
    BASE_REV = 850000
    BASE_COST = 510000

    # 累计器
    cum = {}

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.08)

        if month == 1:
            cum = {k: 0 for k in cas_meta}

        rev = round(BASE_REV * f)
        cost = round(BASE_COST * f)
        tax_sur = round(rev * 0.03)
        sell = round(rev * 0.05)
        admin = round(rev * 0.10)
        rd = round(rev * 0.06)
        fin = round(rev * 0.01)
        interest_exp = round(fin * 0.4)
        interest_inc = round(fin * 0.2)
        other_gains = round(rev * 0.006)
        inv_income = round(rev * 0.01)
        fv_change = round(rev * 0.005)
        credit_imp = round(rev * -0.003)
        asset_imp = round(rev * -0.002)
        asset_disp = round(rev * 0.001)

        op_profit = rev - cost - tax_sur - sell - admin - rd - fin + other_gains + inv_income + fv_change + credit_imp + asset_imp + asset_disp
        non_op_inc = round(rev * 0.005)
        non_op_exp = round(rev * 0.0025)
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
            'oci_reclassifiable': oci,
            'comprehensive_income_total': net + oci,
        }

        for k in current:
            cum[k] = cum.get(k, 0) + current[k]

        for code in cas_meta:
            m = cas_meta[code]
            rows.append((HX_ID, year, month, 'CAS', code, 0,
                         None, None, None, '元', None,
                         current.get(code, 0), cum.get(code, 0),
                         m[0], m[1], m[2]))

    # SAS 鑫源贸易
    sas_meta = {
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

    BASE_XY_REV = 320000
    cum_xy = {}

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.015, seasonal_amp=0.06)

        if month == 1:
            cum_xy = {k: 0 for k in sas_meta}

        rev = round(BASE_XY_REV * f)
        cost = round(rev * 0.7)
        tax_sur = round(rev * 0.03)
        sell = round(rev * 0.05)
        admin = round(rev * 0.10)
        fin = round(rev * 0.02)
        inv_inc = round(rev * 0.01)
        op_profit = rev - cost - tax_sur - sell - admin - fin + inv_inc
        non_op_inc = round(rev * 0.005)
        non_op_exp = round(rev * 0.0025)
        total_profit = op_profit + non_op_inc - non_op_exp
        income_tax = round(total_profit * 0.05)
        net = total_profit - income_tax

        current_xy = {
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

        for k in current_xy:
            cum_xy[k] = cum_xy.get(k, 0) + current_xy[k]

        for code in sas_meta:
            m = sas_meta[code]
            rows.append((XY_ID, year, month, 'SAS', code, 0,
                         None, None, None, '元', None,
                         current_xy.get(code, 0), cum_xy.get(code, 0),
                         m[0], m[1], m[2]))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_income_statement_item VALUES ({placeholders})", rows)
    print(f"  利润表扩展: {len(rows)} 行")


# ============================================================
# 现金流量表扩展数据
# ============================================================
def _insert_cash_flow_extended(cur):
    """华兴科技(CAS) + 鑫源贸易(SAS) 现金流量表 2024.01-2026.02"""
    cas_meta = {
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

    rows = []
    BASE_CASH = 2050000  # 2025年初现金

    cum_hx = {}
    prev_ending_cash = BASE_CASH

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.08)

        if month == 1:
            cum_hx = {}
            # 年初现金 = 上年末现金
            begin_cash_year = round(BASE_CASH * _monthly_factor(
                _month_offset(year - 1, 12), growth_rate=0.02, seasonal_amp=0.0))
            prev_ending_cash = begin_cash_year

        rev = round(850000 * f)
        op_inflow_sales = round(rev * 1.13)
        op_inflow_other = round(15000 * f)
        op_inflow_sub = op_inflow_sales + op_inflow_other
        op_outflow_purchase = round(rev * 0.665)
        op_outflow_labor = round(rev * 0.10)
        op_outflow_tax = round(rev * 0.044)
        op_outflow_other = round(rev * 0.022)
        op_outflow_sub = op_outflow_purchase + op_outflow_labor + op_outflow_tax + op_outflow_other
        op_net = op_inflow_sub - op_outflow_sub

        inv_returns = round(1700 * f)
        inv_inflow_sub = inv_returns
        inv_outflow_assets = round(50000 * f)
        inv_outflow_sub = inv_outflow_assets
        inv_net = inv_inflow_sub - inv_outflow_sub

        fin_borrowing = round(200000 * f)
        fin_inflow_sub = fin_borrowing
        fin_debt = round(50000 * f)
        fin_interest = round(8200 * f)
        fin_outflow_sub = fin_debt + fin_interest
        fin_net = fin_inflow_sub - fin_outflow_sub

        net_increase = op_net + inv_net + fin_net
        beginning_cash = prev_ending_cash
        ending_cash = beginning_cash + net_increase
        prev_ending_cash = ending_cash

        current = {
            'operating_inflow_sales': op_inflow_sales,
            'operating_inflow_tax_refund': 0, 'operating_inflow_other': op_inflow_other,
            'operating_inflow_subtotal': op_inflow_sub,
            'operating_outflow_purchase': op_outflow_purchase,
            'operating_outflow_labor': op_outflow_labor,
            'operating_outflow_tax': op_outflow_tax,
            'operating_outflow_other': op_outflow_other,
            'operating_outflow_subtotal': op_outflow_sub,
            'operating_net_cash': op_net,
            'investing_inflow_sale_investment': 0, 'investing_inflow_returns': inv_returns,
            'investing_inflow_disposal_assets': 0, 'investing_inflow_disposal_subsidiary': 0,
            'investing_inflow_other': 0, 'investing_inflow_subtotal': inv_inflow_sub,
            'investing_outflow_purchase_assets': inv_outflow_assets,
            'investing_outflow_purchase_investment': 0,
            'investing_outflow_acquire_subsidiary': 0, 'investing_outflow_other': 0,
            'investing_outflow_subtotal': inv_outflow_sub,
            'investing_net_cash': inv_net,
            'financing_inflow_capital': 0, 'financing_inflow_borrowing': fin_borrowing,
            'financing_inflow_other': 0, 'financing_inflow_subtotal': fin_inflow_sub,
            'financing_outflow_debt_repayment': fin_debt,
            'financing_outflow_dividend_interest': fin_interest,
            'financing_outflow_other': 0, 'financing_outflow_subtotal': fin_outflow_sub,
            'financing_net_cash': fin_net,
            'fx_impact': 0, 'net_increase_cash': net_increase,
            'beginning_cash': beginning_cash, 'ending_cash': ending_cash,
        }

        # 累计
        if not cum_hx:
            cum_hx = dict(current)
            cum_hx['beginning_cash'] = beginning_cash
        else:
            for k in current:
                if k == 'beginning_cash':
                    pass  # 保持年初值
                elif k == 'ending_cash':
                    cum_hx[k] = ending_cash
                else:
                    cum_hx[k] = cum_hx.get(k, 0) + current[k]

        for code in cas_meta:
            m = cas_meta[code]
            rows.append((HX_ID, year, month, 'CAS', code, 0,
                         None, 'ETL_EXT', None, '元', None,
                         current.get(code, 0), cum_hx.get(code, 0),
                         m[0], m[1], m[2]))

    # SAS 鑫源贸易
    sas_meta = {
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

    XY_BASE_CASH = 320000
    cum_xy = {}
    xy_prev_end = XY_BASE_CASH

    for year, month in ALL_MONTHS:
        if year == 2025 and 1 <= month <= 3:
            continue

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.015, seasonal_amp=0.06)

        if month == 1:
            cum_xy = {}
            xy_prev_end = round(XY_BASE_CASH * _monthly_factor(
                _month_offset(year - 1, 12), growth_rate=0.015, seasonal_amp=0.0))

        rev = round(320000 * f)
        op_sales = round(rev * 1.03)
        op_other = round(5000 * f)
        op_purchase = round(rev * 0.72)
        op_staff = round(rev * 0.08)
        op_tax = round(rev * 0.02)
        op_other_out = round(rev * 0.025)
        op_net = op_sales + op_other - op_purchase - op_staff - op_tax - op_other_out

        inv_assets = round(5000 * f)
        inv_net = -inv_assets

        fin_borrow = round(20000 * f) if month % 3 == 0 else 0
        fin_debt = round(10000 * f) if month % 4 == 0 else 0
        fin_interest = round(2000 * f) if month % 4 == 0 else 0
        fin_net = fin_borrow - fin_debt - fin_interest

        net_inc = op_net + inv_net + fin_net
        begin = xy_prev_end
        end = begin + net_inc
        xy_prev_end = end

        current_xy = {
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

        if not cum_xy:
            cum_xy = dict(current_xy)
        else:
            for k in current_xy:
                if k == 'beginning_cash':
                    pass
                elif k == 'ending_cash':
                    cum_xy[k] = end
                else:
                    cum_xy[k] = cum_xy.get(k, 0) + current_xy[k]

        for code in sas_meta:
            m = sas_meta[code]
            rows.append((XY_ID, year, month, 'SAS', code, 0,
                         None, 'ETL_EXT', None, '元', None,
                         current_xy.get(code, 0), cum_xy.get(code, 0),
                         m[0], m[1], m[2]))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(f"INSERT OR REPLACE INTO fs_cash_flow_item VALUES ({placeholders})", rows)
    print(f"  现金流量表扩展: {len(rows)} 行")


# ============================================================
# 发票扩展数据
# ============================================================
def _insert_invoice_extended(cur):
    """华兴科技 进项/销项发票 2025.01-2026.02（14个月）"""
    INV_MONTHS = _gen_months(2025, 1, 2026, 2)

    purchase_rows = []
    sales_rows = []

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

    for year, month in INV_MONTHS:
        if year == 2025 and month == 12:
            continue  # 已有原始数据

        offset = _month_offset(year, month)
        f = _monthly_factor(offset, growth_rate=0.02, seasonal_amp=0.08)

        # 每月5张进项发票
        for i in range(5):
            seller = sellers[i % len(sellers)]
            pk = f'{year}{month:02d}P{i+1:04d}'
            amt = round(20000 * f * (1 + i * 0.3))
            tax_rate = '13%' if i < 3 else '6%'
            rate_val = 0.13 if i < 3 else 0.06
            tax_amt = round(amt * rate_val)

            purchase_rows.append((
                HX_ID, year, month, '数电', pk, 1,
                None, None, pk,
                seller[0], seller[1], HX_ID, '华兴科技有限公司',
                f'{year}-{month:02d}-{(i+1)*5:02d}', '1090511', None,
                f'商品{i+1}', f'SPEC-{i+1}', '个', round(100 * (i+1)), round(amt / (100*(i+1))),
                amt, tax_rate, tax_amt, amt + tax_amt,
                '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
                '王磊', None, f'{year}-{month:02d}-{(i+1)*5+1:02d} 10:00:00', 'ETL_EXT'
            ))

        # 每月5张销项发票
        for i in range(5):
            buyer = buyers[i % len(buyers)]
            pk = f'{year}{month:02d}S{i+1:04d}'
            amt = round(30000 * f * (1 + i * 0.4))
            tax_rate_val = 0.13 if i < 3 else 0.06
            tax_amt = round(amt * tax_rate_val)

            sales_rows.append((
                HX_ID, year, month, '数电', pk, 1,
                None, None, pk,
                HX_ID, '华兴科技有限公司', buyer[0], buyer[1],
                f'{year}-{month:02d}-{(i+1)*4:02d}',
                amt, tax_amt, amt + tax_amt,
                '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
                '张明', None, f'{year}-{month:02d}-{(i+1)*4+1:02d} 10:00:00', 'ETL_EXT'
            ))

    p_placeholders = ','.join(['?'] * 34)
    s_placeholders = ','.join(['?'] * 26)
    cur.executemany(f"INSERT OR REPLACE INTO inv_spec_purchase ({p_cols}) VALUES ({p_placeholders})",
                    purchase_rows)
    cur.executemany(f"INSERT OR REPLACE INTO inv_spec_sales ({s_cols}) VALUES ({s_placeholders})",
                    sales_rows)
    print(f"  进项发票扩展: {len(purchase_rows)} 行, 销项发票扩展: {len(sales_rows)} 行")


# ============================================================
# 主入口
# ============================================================
def insert_extended_data(db_path=None):
    """插入扩展样本数据（2024.01-2026.02）"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 先删除已有的扩展数据（保留原始2025年1-3月数据）
    _cleanup_existing(cur)

    _insert_general_vat_extended(cur)
    _insert_small_vat_extended(cur)
    _insert_eit_extended(cur)
    _insert_account_balance_extended(cur)
    _insert_balance_sheet_extended(cur)
    _insert_profit_extended(cur)
    _insert_cash_flow_extended(cur)
    _insert_invoice_extended(cur)

    conn.commit()
    conn.close()
    print("[sample_data_extended] 扩展数据插入完成")


def _cleanup_existing(cur):
    """清理已有数据，为全量重新插入做准备"""
    tables_to_clean = [
        ('vat_return_general', HX_ID),
        ('vat_return_small', XY_ID),
        ('account_balance', HX_ID),
        ('account_balance', XY_ID),
        ('fs_balance_sheet_item', HX_ID),
        ('fs_balance_sheet_item', XY_ID),
        ('fs_income_statement_item', HX_ID),
        ('fs_income_statement_item', XY_ID),
        ('fs_cash_flow_item', HX_ID),
        ('fs_cash_flow_item', XY_ID),
        ('inv_spec_purchase', HX_ID),
        ('inv_spec_sales', HX_ID),
        ('financial_metrics', HX_ID),
        ('financial_metrics', XY_ID),
    ]
    for table, tid in tables_to_clean:
        # 只删除扩展范围内的数据（不在原始2025年1-3月范围内的）
        cur.execute(
            f"DELETE FROM {table} WHERE taxpayer_id = ? "
            f"AND NOT (period_year = 2025 AND period_month BETWEEN 1 AND 3)",
            (tid,)
        )
    # EIT需要特殊处理
    cur.execute(
        "DELETE FROM eit_quarter_main WHERE filing_id IN "
        "(SELECT filing_id FROM eit_quarter_filing WHERE taxpayer_id = ? "
        "AND NOT (period_year = 2025 AND period_quarter = 1))",
        (HX_ID,)
    )
    cur.execute(
        "DELETE FROM eit_quarter_filing WHERE taxpayer_id = ? "
        "AND NOT (period_year = 2025 AND period_quarter = 1)",
        (HX_ID,)
    )
    # EIT年度：保留2024和2025
    cur.execute(
        "DELETE FROM eit_annual_main WHERE filing_id IN "
        "(SELECT filing_id FROM eit_annual_filing WHERE taxpayer_id = ? "
        "AND period_year NOT IN (2024, 2025))",
        (HX_ID,)
    )
    cur.execute(
        "DELETE FROM eit_annual_filing WHERE taxpayer_id = ? "
        "AND period_year NOT IN (2024, 2025)",
        (HX_ID,)
    )
    print("  清理已有扩展数据完成")
