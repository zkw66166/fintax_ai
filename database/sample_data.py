"""示例数据：2个纳税人 + 3个月VAT申报数据 + 修订测试数据"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def insert_sample_data(db_path=None):
    """插入测试用纳税人和VAT/EIT申报数据"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    _insert_taxpayers(cur)
    _insert_general_vat(cur)
    _insert_small_vat(cur)
    _insert_eit_annual(cur)
    _insert_eit_quarter(cur)
    _insert_account_balance(cur)
    _insert_balance_sheet(cur)
    _insert_profit_statement(cur)
    _insert_cash_flow(cur)
    _insert_invoice_purchase(cur)
    _insert_invoice_sales(cur)

    conn.commit()
    conn.close()
    print("[sample_data] 示例数据插入完成")

    # 插入扩展数据（2024.01-2026.02）
    from database.sample_data_extended import insert_extended_data
    insert_extended_data(db_path)

    # 插入人事薪金数据
    from database.sample_data_hr import insert_hr_data
    insert_hr_data(db_path)


def _insert_taxpayers(cur):
    """2个纳税人"""
    taxpayers = [
        ('91310000MA1FL8XQ30', '华兴科技有限公司', '一般纳税人', '有限责任公司',
         '张明', '2018-03-15', 'I6510', '软件和信息技术服务业',
         '13101040000', '国家税务总局上海市浦东新区税务局', '区县',
         '310115', '浦东新区', 'A', 2024, '企业会计准则', 'active'),
        ('92440300MA5EQXL17P', '鑫源贸易商行', '小规模纳税人', '个体工商户',
         '李芳', '2020-06-01', 'F5191', '其他综合零售',
         '14403040000', '国家税务总局深圳市南山区税务局', '区县',
         '440305', '南山区', 'B', 2024, '小企业会计准则', 'active'),
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO taxpayer_info
        (taxpayer_id, taxpayer_name, taxpayer_type, registration_type,
         legal_representative, establish_date, industry_code, industry_name,
         tax_authority_code, tax_authority_name, tax_bureau_level,
         region_code, region_name, credit_grade_current, credit_grade_year,
         accounting_standard, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        taxpayers
    )
    print("  纳税人: 2 户")


def _insert_general_vat(cur):
    """华兴科技 一般纳税人 3个月数据 + 修订版本"""
    tid = '91310000MA1FL8XQ30'
    # (taxpayer_id, period_year, period_month, item_type, time_range, revision_no,
    #  submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
    #  41 indicator columns...)
    # 只填关键指标，其余为None
    def row(month, item_type, time_range, rev, **kw):
        base = {
            'sales_taxable_rate': None, 'sales_goods': None, 'sales_services': None,
            'sales_adjustment_check': None, 'sales_simple_method': None,
            'sales_simple_adjust_check': None, 'sales_export_credit_refund': None,
            'sales_tax_free': None, 'sales_tax_free_goods': None, 'sales_tax_free_services': None,
            'output_tax': None, 'input_tax': None, 'last_period_credit': None,
            'transfer_out': None, 'export_refund': None, 'tax_check_supplement': None,
            'deductible_total': None, 'actual_deduct': None, 'tax_payable': None,
            'end_credit': None, 'simple_tax': None, 'simple_tax_check_supplement': None,
            'tax_reduction': None, 'total_tax_payable': None, 'unpaid_begin': None,
            'export_receipt_tax': None, 'paid_current': None, 'prepaid_installment': None,
            'prepaid_export_receipt': None, 'paid_last_period': None, 'paid_arrears': None,
            'unpaid_end': None, 'arrears': None, 'supplement_refund': None,
            'immediate_refund': None, 'unpaid_check_begin': None, 'paid_check_current': None,
            'unpaid_check_end': None, 'city_maintenance_tax': None,
            'education_surcharge': None, 'local_education_surcharge': None,
        }
        base.update(kw)
        cols = list(base.keys())
        vals = [base[c] for c in cols]
        return (tid, 2025, month, item_type, time_range, rev,
                None, 'ETL_SAMPLE', None, '元', 1.0, *vals)

    rows = [
        # 2025-01 一般项目 本月
        row(1, '一般项目', '本月', 0,
            sales_taxable_rate=1000000, output_tax=130000, input_tax=95000,
            transfer_out=2000, export_refund=0, tax_payable=37000,
            total_tax_payable=37000, end_credit=0, supplement_refund=37000,
            city_maintenance_tax=2590, education_surcharge=1110, local_education_surcharge=740),
        # 2025-01 一般项目 累计
        row(1, '一般项目', '累计', 0,
            sales_taxable_rate=1000000, output_tax=130000, input_tax=95000,
            transfer_out=2000, tax_payable=37000, total_tax_payable=37000),
        # 2025-01 即征即退 本月/累计 (全零)
        row(1, '即征即退项目', '本月', 0),
        row(1, '即征即退项目', '累计', 0),

        # 2025-02 一般项目 本月
        row(2, '一般项目', '本月', 0,
            sales_taxable_rate=1150000, output_tax=150000, input_tax=110000,
            transfer_out=3000, export_refund=0, tax_payable=43000,
            total_tax_payable=43000, end_credit=0, supplement_refund=43000,
            city_maintenance_tax=3010, education_surcharge=1290, local_education_surcharge=860),
        # 2025-02 一般项目 累计
        row(2, '一般项目', '累计', 0,
            sales_taxable_rate=2150000, output_tax=280000, input_tax=205000,
            transfer_out=5000, tax_payable=80000, total_tax_payable=80000),
        row(2, '即征即退项目', '本月', 0),
        row(2, '即征即退项目', '累计', 0),

        # 2025-03 一般项目 本月 rev=0 (原始申报)
        row(3, '一般项目', '本月', 0,
            sales_taxable_rate=1380000, output_tax=180000, input_tax=140000,
            transfer_out=5000, export_refund=0, tax_payable=45000,
            total_tax_payable=45000, end_credit=0, supplement_refund=45000,
            city_maintenance_tax=3150, education_surcharge=1350, local_education_surcharge=900),
        # 2025-03 一般项目 本月 rev=1 (更正申报 — 测试修订版本)
        row(3, '一般项目', '本月', 1,
            sales_taxable_rate=1420000, output_tax=185000, input_tax=140000,
            transfer_out=5000, export_refund=0, tax_payable=50000,
            total_tax_payable=50000, end_credit=0, supplement_refund=50000,
            city_maintenance_tax=3500, education_surcharge=1500, local_education_surcharge=1000),
        # 2025-03 一般项目 累计
        row(3, '一般项目', '累计', 0,
            sales_taxable_rate=3530000, output_tax=460000, input_tax=345000,
            transfer_out=10000, tax_payable=125000, total_tax_payable=125000),
        row(3, '即征即退项目', '本月', 0),
        row(3, '即征即退项目', '累计', 0),
    ]

    cols_count = 11 + 41  # 6 dims + 5 meta + 41 indicators
    placeholders = ','.join(['?'] * cols_count)
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_general VALUES ({placeholders})", rows)
    print(f"  一般纳税人VAT: {len(rows)} 行（含rev=1修订）")


def _insert_small_vat(cur):
    """鑫源贸易 小规模纳税人 3个月数据"""
    tid = '92440300MA5EQXL17P'

    def row(month, item_type, time_range, rev, **kw):
        base = {
            'sales_3percent': None, 'sales_3percent_invoice_spec': None,
            'sales_3percent_invoice_other': None, 'sales_5percent': None,
            'sales_5percent_invoice_spec': None, 'sales_5percent_invoice_other': None,
            'sales_used_assets': None, 'sales_used_assets_invoice_other': None,
            'sales_tax_free': None, 'sales_tax_free_micro': None,
            'sales_tax_free_threshold': None, 'sales_tax_free_other': None,
            'sales_export_tax_free': None, 'sales_export_tax_free_invoice_other': None,
            'tax_due_current': None, 'tax_due_reduction': None,
            'tax_free_amount': None, 'tax_free_micro': None, 'tax_free_threshold': None,
            'tax_due_total': None, 'tax_prepaid': None, 'tax_supplement_refund': None,
            'city_maintenance_tax': None, 'education_surcharge': None,
            'local_education_surcharge': None,
        }
        base.update(kw)
        cols = list(base.keys())
        vals = [base[c] for c in cols]
        return (tid, 2025, month, item_type, time_range, rev,
                None, 'ETL_SAMPLE', None, '元', 1.0, *vals)

    rows = [
        # 2025-01 货物及劳务 本期
        row(1, '货物及劳务', '本期', 0,
            sales_3percent=200000, sales_3percent_invoice_spec=120000,
            sales_3percent_invoice_other=80000,
            tax_due_current=6000, tax_due_total=6000, tax_prepaid=0,
            tax_supplement_refund=6000,
            city_maintenance_tax=420, education_surcharge=180, local_education_surcharge=120),
        # 2025-01 货物及劳务 累计
        row(1, '货物及劳务', '累计', 0,
            sales_3percent=200000, tax_due_current=6000, tax_due_total=6000,
            tax_supplement_refund=6000),
        row(1, '服务不动产无形资产', '本期', 0),
        row(1, '服务不动产无形资产', '累计', 0),

        # 2025-02 货物及劳务 本期
        row(2, '货物及劳务', '本期', 0,
            sales_3percent=250000, sales_3percent_invoice_spec=150000,
            sales_3percent_invoice_other=100000,
            tax_due_current=7500, tax_due_total=7500, tax_prepaid=0,
            tax_supplement_refund=7500,
            city_maintenance_tax=525, education_surcharge=225, local_education_surcharge=150),
        row(2, '货物及劳务', '累计', 0,
            sales_3percent=450000, tax_due_current=13500, tax_due_total=13500,
            tax_supplement_refund=13500),
        row(2, '服务不动产无形资产', '本期', 0),
        row(2, '服务不动产无形资产', '累计', 0),

        # 2025-03 货物及劳务 本期
        row(3, '货物及劳务', '本期', 0,
            sales_3percent=180000, sales_3percent_invoice_spec=100000,
            sales_3percent_invoice_other=80000,
            tax_due_current=5400, tax_due_total=5400, tax_prepaid=0,
            tax_supplement_refund=5400,
            city_maintenance_tax=378, education_surcharge=162, local_education_surcharge=108),
        row(3, '货物及劳务', '累计', 0,
            sales_3percent=630000, tax_due_current=18900, tax_due_total=18900,
            tax_supplement_refund=18900),
        row(3, '服务不动产无形资产', '本期', 0),
        row(3, '服务不动产无形资产', '累计', 0),
    ]

    cols_count = 11 + 25  # 6 dims + 5 meta + 25 indicators
    placeholders = ','.join(['?'] * cols_count)
    cur.executemany(f"INSERT OR REPLACE INTO vat_return_small VALUES ({placeholders})", rows)
    print(f"  小规模纳税人VAT: {len(rows)} 行")


def _insert_eit_annual(cur):
    """华兴科技 2024+2025年度企业所得税（满足A100000计算逻辑校验）"""
    tid = '91310000MA1FL8XQ30'

    # ========== 2024年度 ==========
    filing_id = f'{tid}_2024_0'

    # 年度申报主记录
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_filing
        (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
         preparer, submitted_at, etl_batch_id, etl_confidence)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (filing_id, tid, 2024, 0, '元', '张明', '2025-05-20', 'ETL_SAMPLE', 1.0)
    )

    # 年度基础信息
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_basic_info
        (filing_id, tax_return_type_code, asset_avg, employee_avg, industry_code,
         restricted_or_prohibited, small_micro_enterprise, listed_company)
        VALUES (?,?,?,?,?,?,?,?)""",
        (filing_id, 'A', 2000, 85, 'I6510', 0, 0, '否')
    )

    # 年度主表 — A100000 计算逻辑校验:
    # Row15 = R1-R2-R3-R4-R5-R6-R7+R8+R9+R10+R11+R12+R13+R14
    #       = 12000000-8400000-150000-500000-800000-300000-100000+50000+80000+0+0+(-20000)+(-10000)+5000
    #       = 1855000
    # Row18 = R15+R16-R17 = 1855000+30000-5000 = 1880000
    # Row24 = R18-R19+R20-R21-R22+R23 = 1880000-0+120000-30000-0+0 = 1970000
    # Row28 = R24-R25-R26-R27 = 1970000-0-0-0 = 1970000
    # Row30 = R28*R29 = 1970000*0.25 = 492500
    # Row33 = R30-R31-R32 = 492500-0-0 = 492500
    # Row36 = R33+R34-R35 = 492500+0-0 = 492500
    # Row38 = R36-R37 = 492500-370000 = 122500
    # Row45 = R38-R42-R43-R44 = 122500-0-0-0 = 122500
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
         12000000, 8400000, 150000, 500000, 800000,    # R1-R5
         300000, 100000, 50000, 80000,                   # R6-R9
         0, 0, -20000, -10000, 5000,                     # R10-R14
         1855000, 30000, 5000, 1880000,                  # R15-R18
         0, 120000, 30000, 0, 0, 1970000,                # R19-R24
         0, 0, 0, 1970000,                               # R25-R28
         0.25, 492500,                                    # R29-R30
         0, 0, 492500,                                    # R31-R33
         0, 0, 492500,                                    # R34-R36
         370000, 122500,                                  # R37-R38
         0, 0, 0,                                         # R39-R41
         0, 0, 0, 122500)                                 # R42-R45
    )

    # 股东分红明细
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_shareholder
        (filing_id, shareholder_name, id_type, id_number, investment_ratio, dividend_amount, nationality_or_address)
        VALUES (?,?,?,?,?,?,?)""",
        (filing_id, '张明', '居民身份证', '310***1234', 60.0, 300000, '中国上海')
    )
    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_shareholder
        (filing_id, shareholder_name, id_type, id_number, investment_ratio, dividend_amount, nationality_or_address)
        VALUES (?,?,?,?,?,?,?)""",
        (filing_id, '李华', '居民身份证', '310***5678', 40.0, 200000, '中国上海')
    )

    print(f"  EIT年度: 华兴科技2024年度 (filing_id={filing_id})")

    # ========== 2025年度 ==========
    # 基于利润表全年数据推算（华兴科技ASBE 3个月累计×4≈全年估算）
    # 利润表3月本年累计: revenue=2,750,000, cost=1,650,000, total_profit=495,545
    # 全年估算: revenue≈11,000,000, cost≈6,600,000
    filing_id_2025 = f'{tid}_2025_0'

    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_filing
        (filing_id, taxpayer_id, period_year, revision_no, amount_unit,
         preparer, submitted_at, etl_batch_id, etl_confidence)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (filing_id_2025, tid, 2025, 0, '元', '张明', '2026-05-15', 'ETL_SAMPLE', 1.0)
    )

    cur.execute(
        """INSERT OR REPLACE INTO eit_annual_basic_info
        (filing_id, tax_return_type_code, asset_avg, employee_avg, industry_code,
         restricted_or_prohibited, small_micro_enterprise, listed_company)
        VALUES (?,?,?,?,?,?,?,?)""",
        (filing_id_2025, 'A', 2200, 90, 'I6510', 0, 0, '否')
    )

    # A100000 计算逻辑:
    # R15 = 11000000-6600000-330000-550000-880000-330000-110000+55000+88000+0+0+(-22000)+(-11000)+5500
    #      = 2315500
    # R18 = 2315500+33000-5500 = 2343000
    # R24 = 2343000-0+132000-33000-0+0 = 2442000
    # R28 = 2442000-0-0-0 = 2442000
    # R30 = 2442000*0.25 = 610500
    # R33 = 610500-0-0 = 610500
    # R36 = 610500+0-0 = 610500
    # R38 = 610500-400000 = 210500
    # R45 = 210500-0-0-0 = 210500
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
        (filing_id_2025,
         11000000, 6600000, 330000, 550000, 880000,     # R1-R5
         330000, 110000, 55000, 88000,                    # R6-R9
         0, 0, -22000, -11000, 5500,                      # R10-R14
         2315500, 33000, 5500, 2343000,                   # R15-R18
         0, 132000, 33000, 0, 0, 2442000,                 # R19-R24
         0, 0, 0, 2442000,                                # R25-R28
         0.25, 610500,                                     # R29-R30
         0, 0, 610500,                                     # R31-R33
         0, 0, 610500,                                     # R34-R36
         400000, 210500,                                   # R37-R38
         0, 0, 0,                                          # R39-R41
         0, 0, 0, 210500)                                  # R42-R45
    )

    print(f"  EIT年度: 华兴科技2025年度 (filing_id={filing_id_2025})")


def _insert_eit_quarter(cur):
    """华兴科技 2025年Q1季度预缴（与VAT月度数据对应）"""
    tid = '91310000MA1FL8XQ30'
    filing_id = f'{tid}_2025Q1_0'

    cur.execute(
        """INSERT OR REPLACE INTO eit_quarter_filing
        (filing_id, taxpayer_id, period_year, period_quarter, revision_no,
         amount_unit, preparer, submitted_at, etl_batch_id, etl_confidence)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (filing_id, tid, 2025, 1, 0, '元', '张明', '2025-04-15', 'ETL_SAMPLE', 1.0)
    )

    # 季度主表
    # revenue=3600000 (略高于VAT应税销售额3530000，含非增值税收入)
    # total_profit=450000
    # actual_profit = 3-4+5+6+7+8+9 = 450000+0-0-0-0-0-0 = 450000
    # tax_payable = actual_profit * tax_rate = 450000 * 0.25 = 112500
    # current_tax_payable_or_refund = 12-13-14-15 = 112500-0-0-0 = 112500
    # final = 16-23 = 112500-0 = 112500
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
        (filing_id, 82, 1950.0, 0, 0,
         3600000, 2520000, 450000,
         0, 0, 0, 0, 0, 0,
         450000, 0.25, 112500,
         0, 0, 0, 112500,
         0, 0, 0, 0, 0, 0, 0, 112500)
    )

    print(f"  EIT季度: 华兴科技2025Q1 (filing_id={filing_id})")


def _insert_account_balance(cur):
    """华兴科技（企业会计准则）+ 鑫源贸易（小企业会计准则）各3个月科目余额
    数据逻辑：
    - 借贷平衡：资产类 期初+借方-贷方=期末；负债/权益类 期初-借方+贷方=期末
    - 与VAT数据呼应：应交增值税≈VAT应纳税额，主营业务收入≈VAT销售额
    - 与EIT数据呼应：Q1累计收入≈EIT季度revenue
    """
    tid_hx = '91310000MA1FL8XQ30'  # 华兴科技
    tid_xy = '92440300MA5EQXL17P'  # 鑫源贸易

    rows = []

    # ========== 华兴科技 2025年1-3月 ==========
    # 1月：VAT销售额100万，销项税13万，进项税9.5万，应纳税额3.7万
    hx_m1 = [
        # (account_code, opening, debit, credit, closing)
        ('1001', 50000, 20000, 15000, 55000),           # 库存现金
        ('1002', 2000000, 1200000, 850000, 2350000),     # 银行存款
        ('1122', 500000, 1000000, 800000, 700000),       # 应收账款
        ('1403', 300000, 200000, 180000, 320000),        # 原材料
        ('1601', 5000000, 0, 0, 5000000),                # 固定资产
        ('1602', 1000000, 0, 50000, 1050000),            # 累计折旧（贷方余额）
        ('1701', 800000, 0, 0, 800000),                  # 无形资产
        ('1702', 200000, 0, 20000, 220000),              # 累计摊销（贷方余额）
        ('2202', 400000, 350000, 500000, 550000),        # 应付账款
        ('2211', 200000, 180000, 250000, 270000),        # 应付职工薪酬
        ('2221', 50000, 50000, 37000, 37000),            # 应交税费（应纳增值税3.7万）
        ('222101', 30000, 95000, 130000, 65000),         # 应交增值税（进项9.5万借，销项13万贷）
        ('4001', 3000000, 0, 0, 3000000),                # 实收资本
        ('4002', 500000, 0, 0, 500000),                  # 资本公积
        ('4103', 0, 0, 200000, 200000),                  # 本年利润（1月利润结转）
        ('6001', 0, 0, 1000000, 1000000),                # 主营业务收入（=VAT销售额100万）
        ('6401', 0, 700000, 0, 700000),                  # 主营业务成本
        ('6602', 0, 60000, 0, 60000),                    # 管理费用
        ('6603', 0, 10000, 0, 10000),                    # 财务费用
        ('6601', 0, 30000, 0, 30000),                    # 销售费用
    ]

    # 2月：VAT销售额115万，销项税15万，进项税11万，应纳税额4.3万
    hx_m2 = [
        ('1001', 55000, 25000, 18000, 62000),
        ('1002', 2350000, 1380000, 980000, 2750000),
        ('1122', 700000, 1150000, 900000, 950000),
        ('1403', 320000, 250000, 220000, 350000),
        ('1601', 5000000, 0, 0, 5000000),
        ('1602', 1050000, 0, 50000, 1100000),
        ('1701', 800000, 0, 0, 800000),
        ('1702', 220000, 0, 20000, 240000),
        ('2202', 550000, 400000, 600000, 750000),
        ('2211', 270000, 250000, 300000, 320000),
        ('2221', 37000, 37000, 43000, 43000),
        ('222101', 65000, 110000, 150000, 105000),
        ('4001', 3000000, 0, 0, 3000000),
        ('4002', 500000, 0, 0, 500000),
        ('4103', 200000, 0, 250000, 450000),
        ('6001', 1000000, 0, 1150000, 2150000),
        ('6401', 700000, 800000, 0, 1500000),
        ('6602', 60000, 65000, 0, 125000),
        ('6603', 10000, 12000, 0, 22000),
        ('6601', 30000, 33000, 0, 63000),
    ]

    # 3月：VAT销售额142万(rev1)，销项税18.5万，进项税14万，应纳税额5万
    hx_m3 = [
        ('1001', 62000, 30000, 22000, 70000),
        ('1002', 2750000, 1650000, 1200000, 3200000),
        ('1122', 950000, 1420000, 1100000, 1270000),
        ('1403', 350000, 280000, 260000, 370000),
        ('1601', 5000000, 0, 0, 5000000),
        ('1602', 1100000, 0, 50000, 1150000),
        ('1701', 800000, 0, 0, 800000),
        ('1702', 240000, 0, 20000, 260000),
        ('2202', 750000, 500000, 700000, 950000),
        ('2211', 320000, 300000, 350000, 370000),
        ('2221', 43000, 43000, 50000, 50000),
        ('222101', 105000, 140000, 185000, 150000),
        ('4001', 3000000, 0, 0, 3000000),
        ('4002', 500000, 0, 0, 500000),
        ('4103', 450000, 0, 330000, 780000),
        ('6001', 2150000, 0, 1420000, 3570000),
        ('6401', 1500000, 990000, 0, 2490000),
        ('6602', 125000, 70000, 0, 195000),
        ('6603', 22000, 15000, 0, 37000),
        ('6601', 63000, 35000, 0, 98000),
    ]

    for month, data in [(1, hx_m1), (2, hx_m2), (3, hx_m3)]:
        for code, opening, debit, credit, closing in data:
            rows.append((tid_hx, 2025, month, code, 0,
                         None, 'ETL_SAMPLE', None, '元', 1.0,
                         opening, debit, credit, closing))

    # ========== 鑫源贸易 2025年1-3月（小企业会计准则）==========
    # 1月：VAT 3%销售额20万，应纳税额0.6万
    xy_m1 = [
        ('1001', 20000, 10000, 8000, 22000),
        ('1002', 300000, 230000, 180000, 350000),
        ('1122', 80000, 200000, 150000, 130000),
        ('1405', 150000, 120000, 100000, 170000),
        ('2202', 100000, 80000, 130000, 150000),
        ('2211', 30000, 25000, 35000, 40000),
        ('2221', 8000, 8000, 6000, 6000),
        ('4001', 200000, 0, 0, 200000),
        ('4103', 0, 0, 40000, 40000),
        ('6001', 0, 0, 200000, 200000),
        ('6401', 0, 140000, 0, 140000),
        ('5602', 0, 15000, 0, 15000),
        ('6603', 0, 5000, 0, 5000),
    ]

    # 2月：VAT 3%销售额25万，应纳税额0.75万
    xy_m2 = [
        ('1001', 22000, 12000, 9000, 25000),
        ('1002', 350000, 280000, 210000, 420000),
        ('1122', 130000, 250000, 180000, 200000),
        ('1405', 170000, 140000, 120000, 190000),
        ('2202', 150000, 100000, 160000, 210000),
        ('2211', 40000, 35000, 42000, 47000),
        ('2221', 6000, 6000, 7500, 7500),
        ('4001', 200000, 0, 0, 200000),
        ('4103', 40000, 0, 52500, 92500),
        ('6001', 200000, 0, 250000, 450000),
        ('6401', 140000, 175000, 0, 315000),
        ('5602', 15000, 17000, 0, 32000),
        ('6603', 5000, 5500, 0, 10500),
    ]

    # 3月：VAT 3%销售额18万，应纳税额0.54万
    xy_m3 = [
        ('1001', 25000, 8000, 10000, 23000),
        ('1002', 420000, 210000, 180000, 450000),
        ('1122', 200000, 180000, 160000, 220000),
        ('1405', 190000, 100000, 110000, 180000),
        ('2202', 210000, 120000, 140000, 230000),
        ('2211', 47000, 42000, 48000, 53000),
        ('2221', 7500, 7500, 5400, 5400),
        ('4001', 200000, 0, 0, 200000),
        ('4103', 92500, 0, 37100, 129600),
        ('6001', 450000, 0, 180000, 630000),
        ('6401', 315000, 126000, 0, 441000),
        ('5602', 32000, 12000, 0, 44000),
        ('6603', 5500, 4900, 0, 10400),
    ]

    for month, data in [(1, xy_m1), (2, xy_m2), (3, xy_m3)]:
        for code, opening, debit, credit, closing in data:
            rows.append((tid_xy, 2025, month, code, 0,
                         None, 'ETL_SAMPLE', None, '元', 1.0,
                         opening, debit, credit, closing))

    placeholders = ','.join(['?'] * 14)
    cur.executemany(
        f"INSERT OR REPLACE INTO account_balance VALUES ({placeholders})", rows
    )
    print(f"  科目余额: {len(rows)} 行（华兴科技+鑫源贸易 各3个月）")


def _insert_balance_sheet(cur):
    """华兴科技（ASBE企业会计准则）+ 鑫源贸易（ASSE小企业会计准则）各3个月资产负债表
    数据逻辑：
    - 恒等式：资产总计 = 负债合计 + 所有者权益合计
    - 与科目余额表呼应：货币资金=库存现金+银行存款，应收账款=科目余额应收账款期末等
    - 年初余额为各月相同（同一会计年度年初数不变）
    """
    tid_hx = '91310000MA1FL8XQ30'  # 华兴科技 ASBE
    tid_xy = '92440300MA5EQXL17P'  # 鑫源贸易 ASSE

    rows = []

    def bs_row(tid, year, month, gaap, code, rev, begin, end, name, line, section):
        return (tid, year, month, gaap, code, rev,
                None, 'ETL_SAMPLE', None, '元', 1.0,
                begin, end, name, line, section)

    # ========== 华兴科技 ASBE 2025年1-3月 ==========
    # 年初余额（3个月相同）基于2024年末假设
    # 期末余额根据科目余额表推算
    hx_begin = {
        'CASH': 2050000, 'ACCOUNTS_RECEIVABLE': 500000, 'PREPAYMENTS': 80000,
        'OTHER_RECEIVABLES': 50000, 'INVENTORY': 300000,
        'OTHER_CURRENT_ASSETS': 20000, 'CURRENT_ASSETS': 3000000,
        'FIXED_ASSETS': 4000000, 'INTANGIBLE_ASSETS': 600000,
        'LONG_TERM_DEFERRED_EXPENSES': 30000,
        'NON_CURRENT_ASSETS': 4630000, 'ASSETS': 7630000,
        'ACCOUNTS_PAYABLE': 400000, 'EMPLOYEE_BENEFITS_PAYABLE': 200000,
        'TAXES_PAYABLE': 50000, 'OTHER_PAYABLES': 80000,
        'CURRENT_LIABILITIES': 730000, 'LIABILITIES': 730000,
        'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
        'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': 3200000,
        'EQUITY': 6900000, 'LIABILITIES_AND_EQUITY': 7630000,
    }

    # 月末数据：从科目余额表推算
    # 1月末：cash=55000+2350000=2405000, AR=700000, inventory=320000
    #   fixed=5000000-1050000=3950000, intangible=800000-220000=580000
    hx_m1_end = {
        'CASH': 2405000, 'ACCOUNTS_RECEIVABLE': 700000, 'PREPAYMENTS': 80000,
        'OTHER_RECEIVABLES': 50000, 'INVENTORY': 320000,
        'OTHER_CURRENT_ASSETS': 20000,
        'CURRENT_ASSETS': 3575000,
        'FIXED_ASSETS': 3950000, 'INTANGIBLE_ASSETS': 580000,
        'LONG_TERM_DEFERRED_EXPENSES': 30000,
        'NON_CURRENT_ASSETS': 4560000, 'ASSETS': 8135000,
        'ACCOUNTS_PAYABLE': 550000, 'EMPLOYEE_BENEFITS_PAYABLE': 270000,
        'TAXES_PAYABLE': 37000, 'OTHER_PAYABLES': 80000,
        'CURRENT_LIABILITIES': 937000, 'LIABILITIES': 937000,
        'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
        'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': 3498000,
        'EQUITY': 7198000, 'LIABILITIES_AND_EQUITY': 8135000,
    }

    # 2月末：cash=62000+2750000=2812000, AR=950000, inventory=350000
    #   fixed=5000000-1100000=3900000, intangible=800000-240000=560000
    hx_m2_end = {
        'CASH': 2812000, 'ACCOUNTS_RECEIVABLE': 950000, 'PREPAYMENTS': 80000,
        'OTHER_RECEIVABLES': 50000, 'INVENTORY': 350000,
        'OTHER_CURRENT_ASSETS': 20000,
        'CURRENT_ASSETS': 4262000,
        'FIXED_ASSETS': 3900000, 'INTANGIBLE_ASSETS': 560000,
        'LONG_TERM_DEFERRED_EXPENSES': 30000,
        'NON_CURRENT_ASSETS': 4490000, 'ASSETS': 8752000,
        'ACCOUNTS_PAYABLE': 750000, 'EMPLOYEE_BENEFITS_PAYABLE': 320000,
        'TAXES_PAYABLE': 43000, 'OTHER_PAYABLES': 80000,
        'CURRENT_LIABILITIES': 1193000, 'LIABILITIES': 1193000,
        'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
        'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': 3859000,
        'EQUITY': 7559000, 'LIABILITIES_AND_EQUITY': 8752000,
    }

    # 3月末：cash=70000+3200000=3270000, AR=1270000, inventory=370000
    #   fixed=5000000-1150000=3850000, intangible=800000-260000=540000
    hx_m3_end = {
        'CASH': 3270000, 'ACCOUNTS_RECEIVABLE': 1270000, 'PREPAYMENTS': 80000,
        'OTHER_RECEIVABLES': 50000, 'INVENTORY': 370000,
        'OTHER_CURRENT_ASSETS': 20000,
        'CURRENT_ASSETS': 5060000,
        'FIXED_ASSETS': 3850000, 'INTANGIBLE_ASSETS': 540000,
        'LONG_TERM_DEFERRED_EXPENSES': 30000,
        'NON_CURRENT_ASSETS': 4420000, 'ASSETS': 9480000,
        'ACCOUNTS_PAYABLE': 950000, 'EMPLOYEE_BENEFITS_PAYABLE': 370000,
        'TAXES_PAYABLE': 50000, 'OTHER_PAYABLES': 80000,
        'CURRENT_LIABILITIES': 1450000, 'LIABILITIES': 1450000,
        'SHARE_CAPITAL': 3000000, 'CAPITAL_RESERVE': 500000,
        'SURPLUS_RESERVE': 200000, 'RETAINED_EARNINGS': 5330000,
        'EQUITY': 9030000 - 1000000,  # adjust
        'LIABILITIES_AND_EQUITY': 9480000,
    }
    # Fix: equity = assets - liabilities = 9480000 - 1450000 = 8030000
    hx_m3_end['EQUITY'] = 8030000
    hx_m3_end['RETAINED_EARNINGS'] = 8030000 - 3000000 - 500000 - 200000  # = 4330000

    # ASBE项目映射 (item_code -> (item_name, line_number, section))
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

    for month, end_data in [(1, hx_m1_end), (2, hx_m2_end), (3, hx_m3_end)]:
        for code, (name, line, section) in asbe_meta.items():
            begin_val = hx_begin.get(code, 0)
            end_val = end_data.get(code, 0)
            rows.append(bs_row(tid_hx, 2025, month, 'ASBE', code, 0,
                               begin_val, end_val, name, line, section))

    # ========== 鑫源贸易 ASSE 2025年1-3月 ==========
    xy_begin = {
        'CASH': 320000, 'ACCOUNTS_RECEIVABLE': 80000, 'INVENTORY': 150000,
        'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': 560000,
        'LONG_TERM_EQUITY_INVESTMENTS': 0,
        'FIXED_ASSETS_ORIGINAL': 0, 'ACCUMULATED_DEPRECIATION': 0,
        'FIXED_ASSETS_NET': 0,
        'NON_CURRENT_ASSETS': 0, 'ASSETS': 560000,
        'ACCOUNTS_PAYABLE': 100000, 'EMPLOYEE_BENEFITS_PAYABLE': 30000,
        'TAXES_PAYABLE': 8000, 'OTHER_PAYABLES': 22000,
        'CURRENT_LIABILITIES': 160000, 'LIABILITIES': 160000,
        'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
        'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': 180000,
        'EQUITY': 400000, 'LIABILITIES_AND_EQUITY': 560000,
    }

    # 1月末：cash=22000+350000=372000, AR=130000, inventory=170000
    xy_m1_end = {
        'CASH': 372000, 'ACCOUNTS_RECEIVABLE': 130000, 'INVENTORY': 170000,
        'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': 682000,
        'NON_CURRENT_ASSETS': 0, 'ASSETS': 682000,
        'ACCOUNTS_PAYABLE': 150000, 'EMPLOYEE_BENEFITS_PAYABLE': 40000,
        'TAXES_PAYABLE': 6000, 'OTHER_PAYABLES': 22000,
        'CURRENT_LIABILITIES': 218000, 'LIABILITIES': 218000,
        'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
        'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': 244000,
        'EQUITY': 464000, 'LIABILITIES_AND_EQUITY': 682000,
    }

    # 2月末：cash=25000+420000=445000, AR=200000, inventory=190000
    xy_m2_end = {
        'CASH': 445000, 'ACCOUNTS_RECEIVABLE': 200000, 'INVENTORY': 190000,
        'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': 845000,
        'NON_CURRENT_ASSETS': 0, 'ASSETS': 845000,
        'ACCOUNTS_PAYABLE': 210000, 'EMPLOYEE_BENEFITS_PAYABLE': 47000,
        'TAXES_PAYABLE': 7500, 'OTHER_PAYABLES': 22000,
        'CURRENT_LIABILITIES': 286500, 'LIABILITIES': 286500,
        'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
        'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': 338500,
        'EQUITY': 558500, 'LIABILITIES_AND_EQUITY': 845000,
    }

    # 3月末：cash=23000+450000=473000, AR=220000, inventory=180000
    xy_m3_end = {
        'CASH': 473000, 'ACCOUNTS_RECEIVABLE': 220000, 'INVENTORY': 180000,
        'OTHER_CURRENT_ASSETS': 10000, 'CURRENT_ASSETS': 883000,
        'NON_CURRENT_ASSETS': 0, 'ASSETS': 883000,
        'ACCOUNTS_PAYABLE': 230000, 'EMPLOYEE_BENEFITS_PAYABLE': 53000,
        'TAXES_PAYABLE': 5400, 'OTHER_PAYABLES': 22000,
        'CURRENT_LIABILITIES': 310400, 'LIABILITIES': 310400,
        'SHARE_CAPITAL': 200000, 'CAPITAL_RESERVE': 0,
        'SURPLUS_RESERVE': 20000, 'RETAINED_EARNINGS': 352600,
        'EQUITY': 572600, 'LIABILITIES_AND_EQUITY': 883000,
    }

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

    for month, end_data in [(1, xy_m1_end), (2, xy_m2_end), (3, xy_m3_end)]:
        for code, (name, line, section) in asse_meta.items():
            begin_val = xy_begin.get(code, 0)
            end_val = end_data.get(code, 0)
            rows.append(bs_row(tid_xy, 2025, month, 'ASSE', code, 0,
                               begin_val, end_val, name, line, section))

    placeholders = ','.join(['?'] * 16)
    cur.executemany(
        f"INSERT OR REPLACE INTO fs_balance_sheet_item VALUES ({placeholders})", rows
    )
    print(f"  资产负债表: {len(rows)} 行（华兴科技ASBE+鑫源贸易ASSE 各3个月）")


def _insert_profit_statement(cur):
    """利润表示例数据（EAV格式）：华兴科技(CAS) + 鑫源贸易(SAS) 各3个月
    写入 fs_income_statement_item 纵表，每个科目一行，含 current_amount 和 cumulative_amount。
    """
    hx_id = '91310000MA1FL8XQ30'
    xy_id = '92440300MA5EQXL17P'

    # ── CAS 科目元数据: item_code → (item_name, line_number, category) ──
    cas_meta = {
        'operating_revenue':                ('一、营业收入', 1, '一、营业收入'),
        'operating_cost':                   ('减：营业成本', 2, '一、营业收入'),
        'taxes_and_surcharges':             ('税金及附加', 3, '一、营业收入'),
        'selling_expense':                  ('销售费用', 4, '一、营业收入'),
        'administrative_expense':           ('管理费用', 5, '一、营业收入'),
        'rd_expense':                       ('研发费用', 6, '一、营业收入'),
        'financial_expense':                ('财务费用', 7, '一、营业收入'),
        'interest_expense':                 ('其中：利息费用', 8, '一、营业收入'),
        'interest_income':                  ('利息收入', 9, '一、营业收入'),
        'other_gains':                      ('加：其他收益', 10, '一、营业收入'),
        'investment_income':                ('投资收益', 11, '一、营业收入'),
        'investment_income_associates':     ('其中：对联营企业和合营企业的投资收益', 12, '一、营业收入'),
        'amortized_cost_termination_income': ('以摊余成本计量的金融资产终止确认收益', 13, '一、营业收入'),
        'net_exposure_hedge_income':        ('净敞口套期收益', 14, '一、营业收入'),
        'fair_value_change_income':         ('公允价值变动收益', 15, '一、营业收入'),
        'credit_impairment_loss':           ('信用减值损失', 16, '一、营业收入'),
        'asset_impairment_loss':            ('资产减值损失', 17, '一、营业收入'),
        'asset_disposal_gains':             ('资产处置收益', 18, '一、营业收入'),
        'operating_profit':                 ('二、营业利润', 19, '二、营业利润'),
        'non_operating_income':             ('加：营业外收入', 20, '二、营业利润'),
        'non_operating_expense':            ('减：营业外支出', 21, '二、营业利润'),
        'total_profit':                     ('三、利润总额', 22, '三、利润总额'),
        'income_tax_expense':               ('减：所得税费用', 23, '三、利润总额'),
        'net_profit':                       ('四、净利润', 24, '四、净利润'),
        'continued_ops_net_profit':         ('（一）持续经营净利润', 25, '四、净利润'),
        'discontinued_ops_net_profit':      ('（二）终止经营净利润', 26, '四、净利润'),
        'other_comprehensive_income_net':   ('五、其他综合收益的税后净额', 27, '五、其他综合收益'),
        'oci_not_reclassifiable':           ('（一）不能重分类进损益的其他综合收益', 28, '五、其他综合收益'),
        'oci_reclassifiable':               ('（二）将重分类进损益的其他综合收益', 29, '五、其他综合收益'),
        'comprehensive_income_total':       ('六、综合收益总额', 30, '六、综合收益总额'),
    }

    # ── SAS 科目元数据 ──
    sas_meta = {
        'operating_revenue':            ('一、营业收入', 1, '一、营业收入'),
        'operating_cost':               ('减：营业成本', 2, '一、营业收入'),
        'taxes_and_surcharges':         ('税金及附加', 3, '一、营业收入'),
        'consumption_tax':              ('其中：消费税', 4, '一、营业收入'),
        'city_maintenance_tax':         ('城市维护建设税', 5, '一、营业收入'),
        'education_surcharge':          ('教育费附加', 6, '一、营业收入'),
        'selling_expense':              ('销售费用', 7, '一、营业收入'),
        'advertising_expense':          ('其中：商品维修费', 8, '一、营业收入'),
        'administrative_expense':       ('管理费用', 9, '一、营业收入'),
        'business_entertainment_expense': ('其中：业务招待费', 10, '一、营业收入'),
        'financial_expense':            ('财务费用', 11, '一、营业收入'),
        'interest_expense_net':         ('其中：利息费用（净额）', 12, '一、营业收入'),
        'investment_income':            ('加：投资收益', 13, '一、营业收入'),
        'operating_profit':             ('二、营业利润', 14, '二、营业利润'),
        'non_operating_income':         ('加：营业外收入', 15, '二、营业利润'),
        'government_grant':             ('其中：政府补助', 16, '二、营业利润'),
        'non_operating_expense':        ('减：营业外支出', 17, '二、营业利润'),
        'total_profit':                 ('三、利润总额', 18, '三、利润总额'),
        'income_tax_expense':           ('减：所得税费用', 19, '三、利润总额'),
        'net_profit':                   ('四、净利润', 20, '四、净利润'),
    }

    # ── 华兴科技 CAS 月度数据: {month: {item_code: (current, cumulative)}} ──
    hx_months = {
        1: {
            'operating_revenue': (850000, 850000),
            'operating_cost': (510000, 510000),
            'taxes_and_surcharges': (25500, 25500),
            'selling_expense': (42500, 42500),
            'administrative_expense': (85000, 85000),
            'rd_expense': (51000, 51000),
            'financial_expense': (8500, 8500),
            'interest_expense': (3400, 3400),
            'interest_income': (1700, 1700),
            'other_gains': (5100, 5100),
            'investment_income': (8500, 8500),
            'investment_income_associates': (0, 0),
            'amortized_cost_termination_income': (0, 0),
            'net_exposure_hedge_income': (0, 0),
            'fair_value_change_income': (4250, 4250),
            'credit_impairment_loss': (-2550, -2550),
            'asset_impairment_loss': (-1700, -1700),
            'asset_disposal_gains': (850, 850),
            'operating_profit': (150950, 150950),
            'non_operating_income': (4250, 4250),
            'non_operating_expense': (2125, 2125),
            'total_profit': (153075, 153075),
            'income_tax_expense': (38269, 38269),
            'net_profit': (114806, 114806),
            'continued_ops_net_profit': (114806, 114806),
            'discontinued_ops_net_profit': (0, 0),
            'other_comprehensive_income_net': (850, 850),
            'oci_not_reclassifiable': (0, 0),
            'oci_reclassifiable': (850, 850),
            'comprehensive_income_total': (115656, 115656),
        },
        2: {
            'operating_revenue': (920000, 1770000),
            'operating_cost': (552000, 1062000),
            'taxes_and_surcharges': (27600, 53100),
            'selling_expense': (46000, 88500),
            'administrative_expense': (92000, 177000),
            'rd_expense': (55200, 106200),
            'financial_expense': (9200, 17700),
            'interest_expense': (3680, 7080),
            'interest_income': (1840, 3540),
            'other_gains': (5520, 10620),
            'investment_income': (9200, 17700),
            'investment_income_associates': (0, 0),
            'amortized_cost_termination_income': (0, 0),
            'net_exposure_hedge_income': (0, 0),
            'fair_value_change_income': (4600, 8850),
            'credit_impairment_loss': (-2760, -5310),
            'asset_impairment_loss': (-1840, -3540),
            'asset_disposal_gains': (920, 1770),
            'operating_profit': (163560, 314510),
            'non_operating_income': (4600, 8850),
            'non_operating_expense': (2300, 4425),
            'total_profit': (165860, 318935),
            'income_tax_expense': (41465, 79734),
            'net_profit': (124395, 239201),
            'continued_ops_net_profit': (124395, 239201),
            'discontinued_ops_net_profit': (0, 0),
            'other_comprehensive_income_net': (920, 1770),
            'oci_not_reclassifiable': (0, 0),
            'oci_reclassifiable': (920, 1770),
            'comprehensive_income_total': (125315, 240971),
        },
        3: {
            'operating_revenue': (980000, 2750000),
            'operating_cost': (588000, 1650000),
            'taxes_and_surcharges': (29400, 82500),
            'selling_expense': (49000, 137500),
            'administrative_expense': (98000, 275000),
            'rd_expense': (58800, 165000),
            'financial_expense': (9800, 27500),
            'interest_expense': (3920, 11000),
            'interest_income': (1960, 5500),
            'other_gains': (5880, 16500),
            'investment_income': (9800, 27500),
            'investment_income_associates': (0, 0),
            'amortized_cost_termination_income': (0, 0),
            'net_exposure_hedge_income': (0, 0),
            'fair_value_change_income': (4900, 13750),
            'credit_impairment_loss': (-2940, -8250),
            'asset_impairment_loss': (-1960, -5500),
            'asset_disposal_gains': (980, 2750),
            'operating_profit': (174160, 488670),
            'non_operating_income': (4900, 13750),
            'non_operating_expense': (2450, 6875),
            'total_profit': (176610, 495545),
            'income_tax_expense': (44153, 123886),
            'net_profit': (132458, 371659),
            'continued_ops_net_profit': (132458, 371659),
            'discontinued_ops_net_profit': (0, 0),
            'other_comprehensive_income_net': (980, 2750),
            'oci_not_reclassifiable': (0, 0),
            'oci_reclassifiable': (980, 2750),
            'comprehensive_income_total': (133438, 374409),
        },
    }

    # ── 鑫源贸易 SAS 月度数据 ──
    xy_months = {
        1: {
            'operating_revenue': (320000, 320000),
            'operating_cost': (224000, 224000),
            'taxes_and_surcharges': (9600, 9600),
            'consumption_tax': (9600, 9600),
            'city_maintenance_tax': (2880, 2880),
            'education_surcharge': (960, 960),
            'selling_expense': (16000, 16000),
            'advertising_expense': (4800, 4800),
            'administrative_expense': (32000, 32000),
            'business_entertainment_expense': (1600, 1600),
            'financial_expense': (6400, 6400),
            'interest_expense_net': (6400, 6400),
            'investment_income': (3200, 3200),
            'operating_profit': (35200, 35200),
            'non_operating_income': (1600, 1600),
            'government_grant': (1600, 1600),
            'non_operating_expense': (800, 800),
            'total_profit': (36000, 36000),
            'income_tax_expense': (1800, 1800),
            'net_profit': (34200, 34200),
        },
        2: {
            'operating_revenue': (350000, 670000),
            'operating_cost': (245000, 469000),
            'taxes_and_surcharges': (10500, 20100),
            'consumption_tax': (10500, 20100),
            'city_maintenance_tax': (3150, 6030),
            'education_surcharge': (1050, 2010),
            'selling_expense': (17500, 33500),
            'advertising_expense': (5250, 10050),
            'administrative_expense': (35000, 67000),
            'business_entertainment_expense': (1750, 3350),
            'financial_expense': (7000, 13400),
            'interest_expense_net': (7000, 13400),
            'investment_income': (3500, 6700),
            'operating_profit': (38500, 73700),
            'non_operating_income': (1750, 3350),
            'government_grant': (1750, 3350),
            'non_operating_expense': (875, 1675),
            'total_profit': (39375, 75375),
            'income_tax_expense': (1969, 3769),
            'net_profit': (37406, 71606),
        },
        3: {
            'operating_revenue': (380000, 1050000),
            'operating_cost': (266000, 735000),
            'taxes_and_surcharges': (11400, 31500),
            'consumption_tax': (11400, 31500),
            'city_maintenance_tax': (3420, 9450),
            'education_surcharge': (1140, 3150),
            'selling_expense': (19000, 52500),
            'advertising_expense': (5700, 15750),
            'administrative_expense': (38000, 105000),
            'business_entertainment_expense': (1900, 5250),
            'financial_expense': (7600, 21000),
            'interest_expense_net': (7600, 21000),
            'investment_income': (3800, 10500),
            'operating_profit': (41800, 115500),
            'non_operating_income': (1900, 5250),
            'government_grant': (1900, 5250),
            'non_operating_expense': (950, 2625),
            'total_profit': (42750, 118125),
            'income_tax_expense': (2138, 5906),
            'net_profit': (40613, 112219),
        },
    }

    # ── 组装 EAV 行 ──
    rows = []

    def add_rows(tid, year, gaap, meta, months_data):
        for month, items in months_data.items():
            for code, (cur_amt, cum_amt) in items.items():
                if cur_amt is None and cum_amt is None:
                    continue
                m = meta[code]
                rows.append((
                    tid, year, month, gaap, code, 0,
                    None, None, None, '元', None,
                    cur_amt, cum_amt,
                    m[0], m[1], m[2],
                ))

    add_rows(hx_id, 2025, 'CAS', cas_meta, hx_months)
    add_rows(xy_id, 2025, 'SAS', sas_meta, xy_months)

    placeholders = ','.join(['?'] * 16)
    cur.executemany(
        f"INSERT OR REPLACE INTO fs_income_statement_item VALUES ({placeholders})",
        rows,
    )
    print(f"  利润表: {len(rows)} 行（华兴科技CAS+鑫源贸易SAS 各3个月, EAV格式）")


if __name__ == "__main__":
    insert_sample_data()


def _insert_cash_flow(cur):
    """现金流量表示例数据（EAV格式）：华兴科技(CAS) + 鑫源贸易(SAS) 各3个月
    写入 fs_cash_flow_item 纵表，每个科目一行，含 current_amount 和 cumulative_amount。
    数据逻辑：
    - 期末现金 = 期初现金 + 现金净增加额
    - 与资产负债表呼应：期末现金 ≈ BS货币资金期末余额
    - 与利润表呼应：经营活动现金流入 ≈ 营业收入（含税）
    """
    hx_id = '91310000MA1FL8XQ30'
    xy_id = '92440300MA5EQXL17P'

    # CAS 科目元数据: item_code → (item_name, line_number, category)
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

    # SAS 科目元数据
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

    # ── 华兴科技 CAS 月度数据: {month: {item_code: (current, cumulative)}} ──
    # BS货币资金: 年初2,050,000; 1月末2,405,000; 2月末2,812,000; 3月末3,270,000
    hx_months = {
        1: {
            'operating_inflow_sales': (960500, 960500),
            'operating_inflow_tax_refund': (0, 0),
            'operating_inflow_other': (15000, 15000),
            'operating_inflow_subtotal': (975500, 975500),
            'operating_outflow_purchase': (565000, 565000),
            'operating_outflow_labor': (85000, 85000),
            'operating_outflow_tax': (37000, 37000),
            'operating_outflow_other': (18500, 18500),
            'operating_outflow_subtotal': (705500, 705500),
            'operating_net_cash': (270000, 270000),
            'investing_inflow_sale_investment': (0, 0),
            'investing_inflow_returns': (1700, 1700),
            'investing_inflow_disposal_assets': (0, 0),
            'investing_inflow_disposal_subsidiary': (0, 0),
            'investing_inflow_other': (0, 0),
            'investing_inflow_subtotal': (1700, 1700),
            'investing_outflow_purchase_assets': (50000, 50000),
            'investing_outflow_purchase_investment': (0, 0),
            'investing_outflow_acquire_subsidiary': (0, 0),
            'investing_outflow_other': (0, 0),
            'investing_outflow_subtotal': (50000, 50000),
            'investing_net_cash': (-48300, -48300),
            'financing_inflow_capital': (0, 0),
            'financing_inflow_borrowing': (200000, 200000),
            'financing_inflow_other': (0, 0),
            'financing_inflow_subtotal': (200000, 200000),
            'financing_outflow_debt_repayment': (50000, 50000),
            'financing_outflow_dividend_interest': (8200, 8200),
            'financing_outflow_other': (0, 0),
            'financing_outflow_subtotal': (58200, 58200),
            'financing_net_cash': (141800, 141800),
            'fx_impact': (0, 0),
            'net_increase_cash': (355000, 355000),
            'beginning_cash': (2050000, 2050000),
            'ending_cash': (2405000, 2405000),
        },
        2: {
            'operating_inflow_sales': (1039600, 2000100),
            'operating_inflow_tax_refund': (0, 0),
            'operating_inflow_other': (18000, 33000),
            'operating_inflow_subtotal': (1057600, 2033100),
            'operating_outflow_purchase': (620000, 1185000),
            'operating_outflow_labor': (92000, 177000),
            'operating_outflow_tax': (43000, 80000),
            'operating_outflow_other': (22000, 40500),
            'operating_outflow_subtotal': (777000, 1482500),
            'operating_net_cash': (280600, 550600),
            'investing_inflow_sale_investment': (0, 0),
            'investing_inflow_returns': (1840, 3540),
            'investing_inflow_disposal_assets': (0, 0),
            'investing_inflow_disposal_subsidiary': (0, 0),
            'investing_inflow_other': (0, 0),
            'investing_inflow_subtotal': (1840, 3540),
            'investing_outflow_purchase_assets': (60000, 110000),
            'investing_outflow_purchase_investment': (0, 0),
            'investing_outflow_acquire_subsidiary': (0, 0),
            'investing_outflow_other': (0, 0),
            'investing_outflow_subtotal': (60000, 110000),
            'investing_net_cash': (-58160, -106460),
            'financing_inflow_capital': (0, 0),
            'financing_inflow_borrowing': (250000, 450000),
            'financing_inflow_other': (0, 0),
            'financing_inflow_subtotal': (250000, 450000),
            'financing_outflow_debt_repayment': (80000, 130000),
            'financing_outflow_dividend_interest': (9440, 17640),
            'financing_outflow_other': (0, 0),
            'financing_outflow_subtotal': (89440, 147640),
            'financing_net_cash': (160560, 302360),
            'fx_impact': (0, 0),
            'net_increase_cash': (407000, 762000),
            'beginning_cash': (2405000, 2050000),
            'ending_cash': (2812000, 2812000),
        },
        3: {
            'operating_inflow_sales': (1107400, 3107500),
            'operating_inflow_tax_refund': (0, 0),
            'operating_inflow_other': (20000, 53000),
            'operating_inflow_subtotal': (1127400, 3160500),
            'operating_outflow_purchase': (660000, 1845000),
            'operating_outflow_labor': (98000, 275000),
            'operating_outflow_tax': (50000, 130000),
            'operating_outflow_other': (25000, 65500),
            'operating_outflow_subtotal': (833000, 2315500),
            'operating_net_cash': (294400, 845000),
            'investing_inflow_sale_investment': (0, 0),
            'investing_inflow_returns': (1960, 5500),
            'investing_inflow_disposal_assets': (0, 0),
            'investing_inflow_disposal_subsidiary': (0, 0),
            'investing_inflow_other': (0, 0),
            'investing_inflow_subtotal': (1960, 5500),
            'investing_outflow_purchase_assets': (70000, 180000),
            'investing_outflow_purchase_investment': (0, 0),
            'investing_outflow_acquire_subsidiary': (0, 0),
            'investing_outflow_other': (0, 0),
            'investing_outflow_subtotal': (70000, 180000),
            'investing_net_cash': (-68040, -174500),
            'financing_inflow_capital': (0, 0),
            'financing_inflow_borrowing': (300000, 750000),
            'financing_inflow_other': (0, 0),
            'financing_inflow_subtotal': (300000, 750000),
            'financing_outflow_debt_repayment': (100000, 230000),
            'financing_outflow_dividend_interest': (10360, 28000),
            'financing_outflow_other': (0, 0),
            'financing_outflow_subtotal': (110360, 258000),
            'financing_net_cash': (189640, 492000),
            'fx_impact': (0, 0),
            'net_increase_cash': (458000, 1220000),
            'beginning_cash': (2812000, 2050000),
            'ending_cash': (3270000, 3270000),
        },
    }

    # ── 鑫源贸易 SAS 月度数据 ──
    # BS货币资金: 年初320,000; 1月末372,000; 2月末445,000; 3月末473,000
    xy_months = {
        1: {
            'operating_receipts_sales': (329600, 329600),
            'operating_receipts_other': (5000, 5000),
            'operating_payments_purchase': (230000, 230000),
            'operating_payments_staff': (25000, 25000),
            'operating_payments_tax': (6000, 6000),
            'operating_payments_other': (8000, 8000),
            'operating_net_cash': (65600, 65600),
            'investing_receipts_disposal_investment': (0, 0),
            'investing_receipts_returns': (0, 0),
            'investing_receipts_disposal_assets': (0, 0),
            'investing_payments_purchase_investment': (0, 0),
            'investing_payments_purchase_assets': (5000, 5000),
            'investing_net_cash': (-5000, -5000),
            'financing_receipts_borrowing': (0, 0),
            'financing_receipts_capital': (0, 0),
            'financing_payments_debt_principal': (0, 0),
            'financing_payments_debt_interest': (0, 0),
            'financing_payments_dividend': (0, 0),
            'financing_net_cash': (0, 0),
            'net_increase_cash': (52000, 52000),
            'beginning_cash': (320000, 320000),
            'ending_cash': (372000, 372000),
        },
        2: {
            'operating_receipts_sales': (360500, 690100),
            'operating_receipts_other': (6000, 11000),
            'operating_payments_purchase': (255000, 485000),
            'operating_payments_staff': (35000, 60000),
            'operating_payments_tax': (7500, 13500),
            'operating_payments_other': (9000, 17000),
            'operating_net_cash': (60000, 125600),
            'investing_receipts_disposal_investment': (0, 0),
            'investing_receipts_returns': (0, 0),
            'investing_receipts_disposal_assets': (0, 0),
            'investing_payments_purchase_investment': (0, 0),
            'investing_payments_purchase_assets': (8000, 13000),
            'investing_net_cash': (-8000, -13000),
            'financing_receipts_borrowing': (50000, 50000),
            'financing_receipts_capital': (0, 0),
            'financing_payments_debt_principal': (0, 0),
            'financing_payments_debt_interest': (0, 0),
            'financing_payments_dividend': (0, 0),
            'financing_net_cash': (50000, 50000),
            'net_increase_cash': (73000, 125000),
            'beginning_cash': (372000, 320000),
            'ending_cash': (445000, 445000),
        },
        3: {
            'operating_receipts_sales': (391400, 1081500),
            'operating_receipts_other': (4000, 15000),
            'operating_payments_purchase': (270000, 755000),
            'operating_payments_staff': (42000, 102000),
            'operating_payments_tax': (5400, 18900),
            'operating_payments_other': (10000, 27000),
            'operating_net_cash': (68000, 193600),
            'investing_receipts_disposal_investment': (0, 0),
            'investing_receipts_returns': (0, 0),
            'investing_receipts_disposal_assets': (0, 0),
            'investing_payments_purchase_investment': (0, 0),
            'investing_payments_purchase_assets': (6000, 19000),
            'investing_net_cash': (-6000, -19000),
            'financing_receipts_borrowing': (0, 50000),
            'financing_receipts_capital': (0, 0),
            'financing_payments_debt_principal': (20000, 20000),
            'financing_payments_debt_interest': (2000, 2000),
            'financing_payments_dividend': (0, 0),
            'financing_net_cash': (-22000, 28000),
            'net_increase_cash': (28000, 153000),
            'beginning_cash': (445000, 320000),
            'ending_cash': (473000, 473000),
        },
    }

    # ── 组装 EAV 行 ──
    rows = []

    def add_cf_rows(tid, year, gaap, meta, months_data):
        for month, items in months_data.items():
            for code, (cur_amt, cum_amt) in items.items():
                m = meta[code]
                rows.append((
                    tid, year, month, gaap, code, 0,
                    None, 'ETL_SAMPLE', None, '元', None,
                    cur_amt, cum_amt,
                    m[0], m[1], m[2],
                ))

    add_cf_rows(hx_id, 2025, 'CAS', cas_meta, hx_months)
    add_cf_rows(xy_id, 2025, 'SAS', sas_meta, xy_months)

    placeholders = ','.join(['?'] * 16)
    cur.executemany(
        f"INSERT OR REPLACE INTO fs_cash_flow_item VALUES ({placeholders})",
        rows,
    )
    print(f"  现金流量表: {len(rows)} 行（华兴科技CAS+鑫源贸易SAS 各3个月, EAV格式）")


def _insert_invoice_purchase(cur):
    """10条进项发票（华兴科技，2025年12月）"""
    hx_id = '91310000MA1FL8XQ30'
    cols = (
        'taxpayer_id, period_year, period_month, invoice_format, invoice_pk, line_no,'
        'invoice_code, invoice_number, digital_invoice_no,'
        'seller_tax_id, seller_name, buyer_tax_id, buyer_name,'
        'invoice_date, tax_category_code, special_business_type,'
        'goods_name, specification, unit, quantity, unit_price,'
        'amount, tax_rate, tax_amount, total_amount,'
        'invoice_source, invoice_type, invoice_status, is_positive, risk_level,'
        'issuer, remark, submitted_at, etl_batch_id'
    )
    rows = [
        # 1. 数电专票 — 多行明细 line 1
        (hx_id, 2025, 12, '数电', '2025120100001', 1,
         None, None, '2025120100001',
         '91310000MA1ABC1230', '上海明远电子有限公司', hx_id, '华兴科技有限公司',
         '2025-12-03', '1090511', None,
         '集成电路', 'IC-7805', '个', 500, 12.00,
         6000.00, '13%', 780.00, 6780.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '王磊', None, '2025-12-04 10:00:00', 'ETL_SAMPLE'),
        # 2. 数电专票 — 多行明细 line 2（同一张发票）
        (hx_id, 2025, 12, '数电', '2025120100001', 2,
         None, None, '2025120100001',
         '91310000MA1ABC1230', '上海明远电子有限公司', hx_id, '华兴科技有限公司',
         '2025-12-03', '1090512', None,
         '电阻器', 'R-100K', '个', 2000, 0.50,
         1000.00, '13%', 130.00, 1130.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '王磊', None, '2025-12-04 10:00:00', 'ETL_SAMPLE'),
        # 3. 非数电专票
        (hx_id, 2025, 12, '非数电', '04712345', 1,
         '3100211130', '04712345', None,
         '91310000MA1DEF4560', '杭州恒通科技有限公司', hx_id, '华兴科技有限公司',
         '2025-12-05', '1060101', None,
         '办公电脑', 'ThinkPad T14', '台', 5, 5200.00,
         26000.00, '13%', 3380.00, 29380.00,
         '增值税发票管理系统', '增值税专用发票', '正常', '是', '无风险',
         '陈静', None, '2025-12-06 09:00:00', 'ETL_SAMPLE'),
        # 4. 数电普票
        (hx_id, 2025, 12, '数电', '2025120100002', 1,
         None, None, '2025120100002',
         '91310000MA1GHI7890', '上海快捷物流有限公司', hx_id, '华兴科技有限公司',
         '2025-12-08', '3040101', None,
         '国内货物运输服务', None, '次', 1, 3500.00,
         3500.00, '9%', 315.00, 3815.00,
         '电子发票服务平台', '增值税普通发票', '正常', '是', '无风险',
         '赵强', None, '2025-12-09 14:00:00', 'ETL_SAMPLE'),
        # 5. 数电专票 — 红冲
        (hx_id, 2025, 12, '数电', '2025120100003', 1,
         None, None, '2025120100003',
         '91310000MA1ABC1230', '上海明远电子有限公司', hx_id, '华兴科技有限公司',
         '2025-12-10', '1090511', None,
         '集成电路', 'IC-7805', '个', -100, 12.00,
         -1200.00, '13%', -156.00, -1356.00,
         '电子发票服务平台', '增值税专用发票', '正常', '否', '无风险',
         '王磊', '红冲2025120100001部分退货', '2025-12-11 10:00:00', 'ETL_SAMPLE'),
        # 6. 数电专票 — 大额采购
        (hx_id, 2025, 12, '数电', '2025120100004', 1,
         None, None, '2025120100004',
         '91310000MA1JKL0120', '北京中科软件集团', hx_id, '华兴科技有限公司',
         '2025-12-12', '1060201', None,
         '软件授权许可', 'Oracle DB Enterprise', '套', 1, 120000.00,
         120000.00, '6%', 7200.00, 127200.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '刘洋', None, '2025-12-13 11:00:00', 'ETL_SAMPLE'),
        # 7. 数电普票 — 办公用品
        (hx_id, 2025, 12, '数电', '2025120100005', 1,
         None, None, '2025120100005',
         '91310000MA1MNO3450', '上海文汇办公用品有限公司', hx_id, '华兴科技有限公司',
         '2025-12-15', '1060501', None,
         '办公用品', 'A4打印纸', '箱', 50, 120.00,
         6000.00, '13%', 780.00, 6780.00,
         '电子发票服务平台', '增值税普通发票', '正常', '是', '无风险',
         '孙丽', None, '2025-12-16 09:30:00', 'ETL_SAMPLE'),
        # 8. 非数电专票 — 服务费
        (hx_id, 2025, 12, '非数电', '04712346', 1,
         '3100211130', '04712346', None,
         '91310000MA1PQR6780', '上海智远咨询有限公司', hx_id, '华兴科技有限公司',
         '2025-12-18', '3040801', None,
         '技术咨询服务', None, '项', 1, 45000.00,
         45000.00, '6%', 2700.00, 47700.00,
         '增值税发票管理系统', '增值税专用发票', '正常', '是', '无风险',
         '周明', None, '2025-12-19 15:00:00', 'ETL_SAMPLE'),
        # 9. 数电专票 — 有风险标记
        (hx_id, 2025, 12, '数电', '2025120100006', 1,
         None, None, '2025120100006',
         '91310000MA1STU9010', '深圳鹏达贸易有限公司', hx_id, '华兴科技有限公司',
         '2025-12-20', '1090101', None,
         '服务器配件', 'SSD 1TB', '块', 20, 800.00,
         16000.00, '13%', 2080.00, 18080.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '中风险',
         '黄伟', None, '2025-12-21 10:00:00', 'ETL_SAMPLE'),
        # 10. 数电专票 — 小额
        (hx_id, 2025, 12, '数电', '2025120100007', 1,
         None, None, '2025120100007',
         '91310000MA1VWX2340', '上海云端网络科技有限公司', hx_id, '华兴科技有限公司',
         '2025-12-22', '3040201', None,
         '云服务器租赁', '标准型S5', '月', 3, 2000.00,
         6000.00, '6%', 360.00, 6360.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '吴芳', None, '2025-12-23 08:30:00', 'ETL_SAMPLE'),
    ]
    placeholders = ','.join(['?'] * 34)
    cur.executemany(
        f"INSERT OR REPLACE INTO inv_spec_purchase ({cols}) VALUES ({placeholders})",
        rows,
    )
    print(f"  进项发票: {len(rows)} 行")


def _insert_invoice_sales(cur):
    """10条销项发票（华兴科技，2025年12月）"""
    hx_id = '91310000MA1FL8XQ30'
    cols = (
        'taxpayer_id, period_year, period_month, invoice_format, invoice_pk, line_no,'
        'invoice_code, invoice_number, digital_invoice_no,'
        'seller_tax_id, seller_name, buyer_tax_id, buyer_name,'
        'invoice_date, amount, tax_amount, total_amount,'
        'invoice_source, invoice_type, invoice_status, is_positive, risk_level,'
        'issuer, remark, submitted_at, etl_batch_id'
    )
    rows = [
        # 1. 数电专票 — 软件销售
        (hx_id, 2025, 12, '数电', '2025120200001', 1,
         None, None, '2025120200001',
         hx_id, '华兴科技有限公司', '91310000MA1AAA1110', '上海锦程信息技术有限公司',
         '2025-12-02', 85000.00, 11050.00, 96050.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '张明', None, '2025-12-02 16:00:00', 'ETL_SAMPLE'),
        # 2. 数电专票 — 技术服务
        (hx_id, 2025, 12, '数电', '2025120200002', 1,
         None, None, '2025120200002',
         hx_id, '华兴科技有限公司', '91310000MA1BBB2220', '杭州数联科技有限公司',
         '2025-12-05', 50000.00, 3000.00, 53000.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '张明', None, '2025-12-05 11:00:00', 'ETL_SAMPLE'),
        # 3. 数电普票 — 小额服务
        (hx_id, 2025, 12, '数电', '2025120200003', 1,
         None, None, '2025120200003',
         hx_id, '华兴科技有限公司', '91310000MA1CCC3330', '苏州创新科技有限公司',
         '2025-12-08', 8000.00, 480.00, 8480.00,
         '电子发票服务平台', '增值税普通发票', '正常', '是', '无风险',
         '张明', None, '2025-12-08 14:30:00', 'ETL_SAMPLE'),
        # 4. 数电专票 — 大额项目
        (hx_id, 2025, 12, '数电', '2025120200004', 1,
         None, None, '2025120200004',
         hx_id, '华兴科技有限公司', '91310000MA1DDD4440', '广州智慧城市运营有限公司',
         '2025-12-10', 200000.00, 12000.00, 212000.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '张明', None, '2025-12-10 09:00:00', 'ETL_SAMPLE'),
        # 5. 数电专票 — 红冲
        (hx_id, 2025, 12, '数电', '2025120200005', 1,
         None, None, '2025120200005',
         hx_id, '华兴科技有限公司', '91310000MA1AAA1110', '上海锦程信息技术有限公司',
         '2025-12-12', -20000.00, -2600.00, -22600.00,
         '电子发票服务平台', '增值税专用发票', '正常', '否', '无风险',
         '张明', '红冲部分退款', '2025-12-12 10:00:00', 'ETL_SAMPLE'),
        # 6. 数电专票 — 运维服务
        (hx_id, 2025, 12, '数电', '2025120200006', 1,
         None, None, '2025120200006',
         hx_id, '华兴科技有限公司', '91310000MA1EEE5550', '南京东方数据有限公司',
         '2025-12-15', 35000.00, 2100.00, 37100.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '张明', None, '2025-12-15 16:00:00', 'ETL_SAMPLE'),
        # 7. 数电普票 — 培训服务
        (hx_id, 2025, 12, '数电', '2025120200007', 1,
         None, None, '2025120200007',
         hx_id, '华兴科技有限公司', '91310000MA1FFF6660', '武汉光谷教育科技有限公司',
         '2025-12-18', 15000.00, 900.00, 15900.00,
         '电子发票服务平台', '增值税普通发票', '正常', '是', '无风险',
         '张明', None, '2025-12-18 11:30:00', 'ETL_SAMPLE'),
        # 8. 数电专票 — 系统集成
        (hx_id, 2025, 12, '数电', '2025120200008', 1,
         None, None, '2025120200008',
         hx_id, '华兴科技有限公司', '91310000MA1GGG7770', '成都天府软件园有限公司',
         '2025-12-20', 150000.00, 9000.00, 159000.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '无风险',
         '张明', None, '2025-12-20 15:00:00', 'ETL_SAMPLE'),
        # 9. 数电专票 — 有风险标记
        (hx_id, 2025, 12, '数电', '2025120200009', 1,
         None, None, '2025120200009',
         hx_id, '华兴科技有限公司', '91310000MA1HHH8880', '深圳前海数字有限公司',
         '2025-12-22', 60000.00, 7800.00, 67800.00,
         '电子发票服务平台', '增值税专用发票', '正常', '是', '中风险',
         '张明', None, '2025-12-22 10:00:00', 'ETL_SAMPLE'),
        # 10. 数电普票 — 小额
        (hx_id, 2025, 12, '数电', '2025120200010', 1,
         None, None, '2025120200010',
         hx_id, '华兴科技有限公司', '91310000MA1III9990', '上海浦江创意设计有限公司',
         '2025-12-25', 5000.00, 300.00, 5300.00,
         '电子发票服务平台', '增值税普通发票', '正常', '是', '无风险',
         '张明', None, '2025-12-25 09:00:00', 'ETL_SAMPLE'),
    ]
    placeholders = ','.join(['?'] * 26)
    cur.executemany(
        f"INSERT OR REPLACE INTO inv_spec_sales ({cols}) VALUES ({placeholders})",
        rows,
    )
    print(f"  销项发票: {len(rows)} 行")
