"""人事薪金示例数据：2家公司各15+员工 + 2025年1-12月薪资数据"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH

# ---------------------------------------------------------------------------
# 公司常量
# ---------------------------------------------------------------------------
HX_ID = "91310000MA1FL8XQ30"   # 华兴科技有限公司（一般纳税人，上海）
HX_NAME = "华兴科技有限公司"
HX_CODE = "HX001"

XY_ID = "92440300MA5EQXL17P"   # 鑫源贸易商行（小规模纳税人，深圳）
XY_NAME = "鑫源贸易商行"
XY_CODE = "XY001"

# ---------------------------------------------------------------------------
# 个税累进税率表（居民综合所得）
# ---------------------------------------------------------------------------
TAX_BRACKETS = [
    (36000,   0.03, 0),
    (144000,  0.10, 2520),
    (300000,  0.20, 16920),
    (420000,  0.25, 31920),
    (660000,  0.30, 52920),
    (960000,  0.35, 85920),
    (float('inf'), 0.45, 181920),
]


def _calc_annual_tax(annual_taxable):
    """根据年度应纳税所得额计算年度应纳税额"""
    if annual_taxable <= 0:
        return 0, 0, 0
    for upper, rate, quick in TAX_BRACKETS:
        if annual_taxable <= upper:
            return rate, quick, round(annual_taxable * rate - quick, 2)
    return 0.45, 181920, round(annual_taxable * 0.45 - 181920, 2)


# ---------------------------------------------------------------------------
# 员工花名册
# ---------------------------------------------------------------------------
# fmt: off
HX_EMPLOYEES = [
    # (employee_id, name, gender, birth, age, education, edu_degree, major, major_type,
    #  dept_code, dept_name, dept_level, position_code, position_name, position_type,
    #  employment_type, entry_date, work_years, total_work_years, id_card_suffix,
    #  social_insurance_city, is_on_job, resign_date,
    #  is_high_tech, ht_cert_type, ht_cert_name, ht_work_days,
    #  base_wage)
    ("HX0001", "张明",   "1", "1978-05-12", 47, "硕士", 3, "工商管理",   "经管", "D01", "总经办",   1, "P01", "总经理",     "管理", "正式", "2018-03-15", 8.0, 22.0, "0512", "上海", 1, None, 1, "职称", "高级工程师", 240, 35000),
    ("HX0002", "王丽华", "2", "1985-09-20", 40, "本科", 2, "财务管理",   "经管", "D02", "财务部",   1, "P02", "财务总监",   "管理", "正式", "2018-06-01", 7.7, 16.0, "0920", "上海", 1, None, 0, None, None, 220, 28000),
    ("HX0003", "陈建国", "1", "1990-03-08", 35, "博士", 4, "计算机科学", "理工", "D03", "研发部",   1, "P03", "技术总监",   "研发", "正式", "2019-01-10", 7.0, 12.0, "0308", "上海", 1, None, 1, "学历", "计算机博士", 250, 32000),
    ("HX0004", "刘洋",   "1", "1992-07-15", 33, "硕士", 3, "软件工程",   "理工", "D03", "研发部",   1, "P04", "高级开发",   "研发", "正式", "2019-06-15", 6.7, 10.0, "0715", "上海", 1, None, 1, "学历", "软件硕士",   245, 25000),
    ("HX0005", "赵敏",   "2", "1995-11-22", 30, "本科", 2, "软件工程",   "理工", "D03", "研发部",   1, "P05", "中级开发",   "研发", "正式", "2020-07-01", 5.6, 7.0,  "1122", "上海", 1, None, 1, "学历", "软件本科",   230, 20000),
    ("HX0006", "孙浩然", "1", "1998-02-14", 28, "本科", 2, "计算机科学", "理工", "D03", "研发部",   1, "P06", "初级开发",   "研发", "正式", "2022-07-01", 3.6, 3.6,  "0214", "上海", 1, None, 1, "学历", "计算机本科", 220, 15000),
    ("HX0007", "周婷",   "2", "1993-06-30", 32, "硕士", 3, "市场营销",   "经管", "D04", "市场部",   1, "P07", "市场经理",   "销售", "正式", "2020-03-01", 5.9, 9.0,  "0630", "上海", 1, None, 0, None, None, 200, 18000),
    ("HX0008", "吴强",   "1", "1996-12-05", 29, "大专", 1, "电子商务",   "经管", "D04", "市场部",   1, "P08", "销售专员",   "销售", "正式", "2021-09-01", 4.4, 5.0,  "1205", "上海", 1, None, 0, None, None, 180, 10000),
    ("HX0009", "郑雪",   "2", "1994-04-18", 31, "本科", 2, "人力资源",   "经管", "D05", "人事行政部",1, "P09", "HR经理",     "管理", "正式", "2020-01-15", 6.1, 8.0,  "0418", "上海", 1, None, 0, None, None, 210, 16000),
    ("HX0010", "黄磊",   "1", "1988-08-25", 37, "本科", 2, "机械工程",   "理工", "D06", "运维部",   1, "P10", "运维主管",   "生产", "正式", "2019-04-01", 6.8, 14.0, "0825", "上海", 1, None, 1, "职称", "中级工程师", 235, 17000),
    ("HX0011", "林小燕", "2", "2000-01-10", 26, "大专", 1, "行政管理",   "文科", "D05", "人事行政部",1, "P11", "行政助理",   "管理", "正式", "2023-03-01", 2.9, 2.9,  "0110", "上海", 1, None, 0, None, None, 180, 8000),
    ("HX0012", "杨帆",   "1", "1997-10-03", 28, "硕士", 3, "人工智能",   "理工", "D03", "研发部",   1, "P12", "算法工程师", "研发", "正式", "2022-01-10", 4.1, 4.1,  "1003", "上海", 1, None, 1, "学历", "AI硕士",     240, 22000),
    ("HX0013", "马超",   "1", "1991-05-28", 34, "本科", 2, "信息安全",   "理工", "D03", "研发部",   1, "P13", "安全工程师", "研发", "正式", "2021-03-15", 4.9, 10.0, "0528", "上海", 1, None, 1, "技能证书", "CISSP", 230, 21000),
    ("HX0014", "许文静", "2", "1999-08-16", 26, "中专", 0, "会计",       "经管", "D02", "财务部",   1, "P14", "出纳",       "管理", "正式", "2023-06-01", 2.7, 2.7,  "0816", "上海", 1, None, 0, None, None, 160, 7000),
    ("HX0015", "高志远", "1", "1987-12-01", 38, "本科", 2, "法学",       "文科", "D07", "法务部",   1, "P15", "法务主管",   "管理", "正式", "2020-09-01", 5.4, 14.0, "1201", "上海", 1, None, 0, None, None, 200, 18000),
    ("HX0016", "田甜",   "2", "1996-03-22", 29, "高中", 0, None,         None,   "D05", "人事行政部",1, "P16", "前台",       "管理", "劳务派遣", "2024-01-15", 2.1, 4.0, "0322", "上海", 1, None, 0, None, None, 150, 6000),
    ("HX0017", "罗鹏",   "1", "2001-07-09", 24, "本科", 2, "数据科学",   "理工", "D03", "研发部",   1, "P17", "数据分析师", "研发", "实习",  "2025-06-01", 0.7, 0.7,  "0709", "上海", 1, None, 1, "学历", "数据本科", 180, 8000),
]

XY_EMPLOYEES = [
    ("XY0001", "李芳",   "2", "1982-11-05", 43, "大专", 1, "工商管理",   "经管", "D01", "管理层",   1, "P01", "店长",       "管理", "正式", "2020-06-01", 5.7, 18.0, "1105", "深圳", 1, None, 0, None, None, 240, 15000),
    ("XY0002", "陈伟",   "1", "1988-04-12", 37, "本科", 2, "市场营销",   "经管", "D02", "采购部",   1, "P02", "采购主管",   "销售", "正式", "2020-08-01", 5.5, 12.0, "0412", "深圳", 1, None, 0, None, None, 230, 12000),
    ("XY0003", "张秀英", "2", "1990-07-20", 35, "大专", 1, "会计学",     "经管", "D03", "财务部",   1, "P03", "会计",       "管理", "正式", "2020-09-01", 5.4, 10.0, "0720", "深圳", 1, None, 0, None, None, 220, 10000),
    ("XY0004", "王强",   "1", "1993-01-15", 33, "本科", 2, "物流管理",   "经管", "D04", "仓储物流部",1, "P04", "仓库主管",   "生产", "正式", "2021-01-10", 5.0, 8.0,  "0115", "深圳", 1, None, 0, None, None, 220, 10000),
    ("XY0005", "刘美玲", "2", "1995-09-08", 30, "本科", 2, "电子商务",   "经管", "D05", "销售部",   1, "P05", "销售主管",   "销售", "正式", "2021-03-01", 4.9, 7.0,  "0908", "深圳", 1, None, 0, None, None, 220, 11000),
    ("XY0006", "赵军",   "1", "1997-06-25", 28, "大专", 1, "市场营销",   "经管", "D05", "销售部",   1, "P06", "销售员",     "销售", "正式", "2022-02-01", 3.9, 5.0,  "0625", "深圳", 1, None, 0, None, None, 200, 7500),
    ("XY0007", "孙丽",   "2", "1999-03-18", 26, "中专", 0, "文秘",       None,   "D01", "管理层",   1, "P07", "行政文员",   "管理", "正式", "2022-06-01", 3.6, 3.6,  "0318", "深圳", 1, None, 0, None, None, 200, 6500),
    ("XY0008", "周大勇", "1", "1985-10-30", 40, "初中", 0, None,         None,   "D04", "仓储物流部",1, "P08", "仓库管理员", "生产", "正式", "2021-06-01", 4.6, 15.0, "1030", "深圳", 1, None, 0, None, None, 200, 6000),
    ("XY0009", "吴小红", "2", "1996-12-12", 29, "高中", 0, None,         None,   "D05", "销售部",   1, "P09", "收银员",     "销售", "正式", "2022-09-01", 3.4, 5.0,  "1212", "深圳", 1, None, 0, None, None, 180, 5800),
    ("XY0010", "郑国强", "1", "1992-08-05", 33, "大专", 1, "汽车维修",   "理工", "D04", "仓储物流部",1, "P10", "配送司机",   "生产", "正式", "2021-11-01", 4.2, 10.0, "0805", "深圳", 1, None, 0, None, None, 200, 7000),
    ("XY0011", "黄翠花", "2", "1998-05-22", 27, "大专", 1, "电子商务",   "经管", "D05", "销售部",   1, "P11", "线上运营",   "销售", "正式", "2023-01-10", 3.1, 4.0,  "0522", "深圳", 1, None, 0, None, None, 200, 7000),
    ("XY0012", "林志明", "1", "1994-02-28", 31, "本科", 2, "国际贸易",   "经管", "D02", "采购部",   1, "P12", "采购员",     "销售", "正式", "2022-04-01", 3.8, 7.0,  "0228", "深圳", 1, None, 0, None, None, 210, 8000),
    ("XY0013", "杨秀珍", "2", "1980-06-15", 45, "初中", 0, None,         None,   "D06", "后勤部",   1, "P13", "保洁员",     "生产", "劳务派遣", "2023-03-01", 2.9, 20.0, "0615", "深圳", 1, None, 0, None, None, 180, 4500),
    ("XY0014", "马小龙", "1", "2002-09-10", 23, "高中", 0, None,         None,   "D04", "仓储物流部",1, "P14", "理货员",     "生产", "正式", "2024-02-01", 1.9, 1.9,  "0910", "深圳", 1, None, 0, None, None, 180, 5500),
    ("XY0015", "许慧",   "2", "1991-04-03", 34, "硕士", 3, "供应链管理", "经管", "D02", "采购部",   1, "P15", "采购经理",   "管理", "正式", "2021-07-01", 4.6, 10.0, "0403", "深圳", 1, None, 0, None, None, 220, 13000),
    ("XY0016", "何建华", "1", "1986-03-17", 39, "大专", 1, "机电一体化", "理工", "D04", "仓储物流部",1, "P16", "设备维护员", "生产", "正式", "2022-08-01", 3.5, 14.0, "0317", "深圳", 1, None, 0, None, None, 200, 7500),
]
# fmt: on

# ---------------------------------------------------------------------------
# 薪资参数（按城市区分社保/公积金比例）
# ---------------------------------------------------------------------------
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
}


# ---------------------------------------------------------------------------
# 专项附加扣除模板（按员工随机分配）
# ---------------------------------------------------------------------------
SPECIAL_ADD_DEDUCTION_PROFILES = {
    # profile_name: (child_edu, continue_edu, housing_loan, housing_rent, elderly_care, baby_care)
    "无":           (0,    0,    0,    0,    0,    0),
    "房贷":         (0,    0,    1000, 0,    0,    0),
    "租房":         (0,    0,    0,    1500, 0,    0),
    "房贷+子女":    (2000, 0,    1000, 0,    0,    0),
    "租房+赡养":    (0,    0,    0,    1500, 3000, 0),
    "全套":         (2000, 400,  1000, 0,    3000, 2000),
    "子女+赡养":    (2000, 0,    0,    0,    3000, 0),
    "继续教育":     (0,    400,  0,    0,    0,    0),
}

# 为每位员工分配扣除档案
HX_DEDUCTION_MAP = {
    "HX0001": "全套",       "HX0002": "房贷+子女",  "HX0003": "房贷+子女",
    "HX0004": "房贷",       "HX0005": "租房+赡养",  "HX0006": "租房",
    "HX0007": "子女+赡养",  "HX0008": "租房",       "HX0009": "房贷+子女",
    "HX0010": "全套",       "HX0011": "无",         "HX0012": "租房",
    "HX0013": "房贷",       "HX0014": "无",         "HX0015": "房贷+子女",
    "HX0016": "无",         "HX0017": "继续教育",
}

XY_DEDUCTION_MAP = {
    "XY0001": "房贷+子女",  "XY0002": "房贷",       "XY0003": "子女+赡养",
    "XY0004": "租房",       "XY0005": "房贷",       "XY0006": "租房",
    "XY0007": "无",         "XY0008": "子女+赡养",  "XY0009": "无",
    "XY0010": "租房",       "XY0011": "继续教育",   "XY0012": "租房",
    "XY0013": "无",         "XY0014": "无",         "XY0015": "房贷+子女",
    "XY0016": "租房+赡养",
}


# ---------------------------------------------------------------------------
# 插入函数
# ---------------------------------------------------------------------------
def insert_hr_data(db_path=None):
    """插入人事薪金示例数据"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    _insert_employees(cur, HX_CODE, HX_NAME, HX_EMPLOYEES)
    _insert_employees(cur, XY_CODE, XY_NAME, XY_EMPLOYEES)
    _insert_salaries(cur, HX_EMPLOYEES, HX_DEDUCTION_MAP, "上海")
    _insert_salaries(cur, XY_EMPLOYEES, XY_DEDUCTION_MAP, "深圳")

    conn.commit()
    conn.close()
    print("[sample_data_hr] 人事薪金示例数据插入完成")



def _insert_employees(cur, company_code, company_name, employees):
    """插入员工信息"""
    cols = (
        "company_code, company_name, dept_code, dept_name, dept_level, "
        "employee_id, employee_name, id_card, gender, birth_date, age, "
        "education, education_degree, major, major_type, "
        "entry_date, work_years, total_work_years, "
        "position_code, position_name, position_type, "
        "employment_type, social_insurance_city, is_on_the_job, resign_date, "
        "is_high_tech_person, high_tech_cert_type, high_tech_cert_name, high_tech_work_days"
    )
    rows = []
    for e in employees:
        (eid, name, gender, birth, age, edu, edu_deg, major, major_type,
         dept_code, dept_name, dept_level, pos_code, pos_name, pos_type,
         emp_type, entry, wyears, twyears, id_suffix,
         city, on_job, resign,
         is_ht, ht_type, ht_name, ht_days, _base_wage) = e
        id_card = f"310101{'19' if int(birth[:4]) < 2000 else '20'}{birth[2:4]}{birth[5:7]}{birth[8:10]}{id_suffix}"
        rows.append((
            company_code, company_name, dept_code, dept_name, dept_level,
            eid, name, id_card, gender, birth, age,
            edu, edu_deg, major, major_type,
            entry, wyears, twyears,
            pos_code, pos_name, pos_type,
            emp_type, city, on_job, resign,
            is_ht, ht_type, ht_name, ht_days,
        ))
    placeholders = ",".join(["?"] * 29)
    cur.executemany(
        f"INSERT OR REPLACE INTO hr_employee_info ({cols}) VALUES ({placeholders})",
        rows,
    )
    print(f"  员工信息({company_name}): {len(rows)} 人")



def _insert_salaries(cur, employees, deduction_map, city):
    """为员工生成2025年1-12月薪资数据（累计预扣法）"""
    params = CITY_PARAMS[city]
    cols = (
        "employee_id, salary_month, "
        "income_wage, income_bonus_monthly, income_bonus_performance, "
        "allowance_transport, allowance_meal, allowance_housing, total_income, "
        "cost_deductible, tax_free_income, other_income_deduct, "
        "deduction_si_pension, deduction_si_medical, deduction_si_unemployment, "
        "deduction_housing_fund, total_special_deduction, "
        "deduction_child_edu, deduction_continue_edu, deduction_housing_loan, "
        "deduction_housing_rent, deduction_elderly_care, deduction_3yo_child_care, "
        "total_special_add_deduction, "
        "deduction_enterprise_annuity, deduction_commercial_health, "
        "deduction_tax_deferred_pension, deduction_other_allowable, total_other_deduction, "
        "donation_allowable, "
        "taxable_income, tax_rate, quick_deduction, tax_payable, "
        "tax_reduction, tax_withheld, tax_refund_or_pay, "
        "company_si_pension, company_si_medical, company_si_unemployment, "
        "company_si_injury, company_si_maternity, company_housing_fund, company_total_benefit, "
        "gross_salary, net_salary"
    )
    rows = []
    for e in employees:
        eid = e[0]
        base_wage = e[-1]  # 最后一个元素是 base_wage
        profile_name = deduction_map.get(eid, "无")
        sad = SPECIAL_ADD_DEDUCTION_PROFILES[profile_name]

        cumulative_income = 0.0
        cumulative_deduction = 0.0
        cumulative_tax = 0.0

        for month in range(1, 13):
            # 月度收入构成
            wage = base_wage
            bonus_monthly = round(base_wage * 0.05, 2) if month % 3 == 0 else 0  # 季末月度奖
            bonus_perf = round(base_wage * 0.10, 2) if month == 12 else 0  # 年末绩效奖
            allow_transport = 500 if base_wage >= 8000 else 300
            allow_meal = 600 if base_wage >= 8000 else 400
            allow_housing = 1000 if base_wage >= 15000 else 0
            total_income = wage + bonus_monthly + bonus_perf + allow_transport + allow_meal + allow_housing

            # 减除费用
            cost_deductible = 5000

            # 专项扣除（个人部分）
            si_pension = round(base_wage * params["si_pension_emp"], 2)
            si_medical = round(base_wage * params["si_medical_emp"], 2)
            si_unemp = round(base_wage * params["si_unemployment_emp"], 2)
            hf = round(base_wage * params["housing_fund_emp"], 2)
            total_special = round(si_pension + si_medical + si_unemp + hf, 2)

            # 专项附加扣除
            child_edu, cont_edu, h_loan, h_rent, elderly, baby = sad
            total_sad = child_edu + cont_edu + h_loan + h_rent + elderly + baby

            # 其他扣除（简化：仅高薪员工有企业年金）
            annuity = round(base_wage * 0.04, 2) if base_wage >= 20000 else 0
            total_other = annuity

            # 累计预扣法计算
            cumulative_income += total_income
            month_deduction = cost_deductible + total_special + total_sad + total_other
            cumulative_deduction += month_deduction

            cum_taxable = round(cumulative_income - cumulative_deduction, 2)
            if cum_taxable < 0:
                cum_taxable = 0
            rate, quick, cum_tax_total = _calc_annual_tax(cum_taxable)
            tax_this_month = round(cum_tax_total - cumulative_tax, 2)
            if tax_this_month < 0:
                tax_this_month = 0
            cumulative_tax += tax_this_month

            # 月度应纳税所得额（用于记录）
            monthly_taxable = round(total_income - cost_deductible - total_special - total_sad - total_other, 2)
            if monthly_taxable < 0:
                monthly_taxable = 0

            # 公司承担部分
            co_pension = round(base_wage * params["si_pension_co"], 2)
            co_medical = round(base_wage * params["si_medical_co"], 2)
            co_unemp = round(base_wage * params["si_unemployment_co"], 2)
            co_injury = round(base_wage * params["si_injury_co"], 2)
            co_maternity = round(base_wage * params["si_maternity_co"], 2)
            co_hf = round(base_wage * params["housing_fund_co"], 2)
            co_total = round(co_pension + co_medical + co_unemp + co_injury + co_maternity + co_hf, 2)

            gross = total_income
            net = round(total_income - total_special - tax_this_month, 2)

            salary_month = f"2025{month:02d}"
            rows.append((
                eid, salary_month,
                wage, bonus_monthly, bonus_perf,
                allow_transport, allow_meal, allow_housing, total_income,
                cost_deductible, 0, 0,
                si_pension, si_medical, si_unemp, hf, total_special,
                child_edu, cont_edu, h_loan, h_rent, elderly, baby, total_sad,
                annuity, 0, 0, 0, total_other,
                0,  # donation
                monthly_taxable, rate, quick, tax_this_month,
                0, 0, 0,  # tax_reduction, tax_withheld, tax_refund_or_pay
                co_pension, co_medical, co_unemp, co_injury, co_maternity, co_hf, co_total,
                gross, net,
            ))

    placeholders = ",".join(["?"] * 46)
    cur.executemany(
        f"INSERT OR REPLACE INTO hr_employee_salary ({cols}) VALUES ({placeholders})",
        rows,
    )
    print(f"  薪资数据({city}): {len(rows)} 条（{len(employees)}人 × 12月）")


if __name__ == "__main__":
    insert_hr_data()
