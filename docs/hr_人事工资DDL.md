 根据下面DDL创建人事薪金表：

CREATE TABLE hr_employee_info (
  id INTEGER PRIMARY KEY AUTOINCREMENT COMMENT '主键ID',
  company_code TEXT NOT NULL COMMENT '公司编码（多公司场景）',
  company_name TEXT NOT NULL COMMENT '公司名称',
  dept_code TEXT NOT NULL COMMENT '部门编码',
  dept_name TEXT NOT NULL COMMENT '部门名称',
  dept_level INTEGER NOT NULL COMMENT '部门层级（1=一级部门，2=二级部门...）',
  employee_id TEXT NOT NULL COMMENT '员工工号（唯一）',
  employee_name TEXT NOT NULL COMMENT '员工姓名',
  id_card TEXT NOT NULL COMMENT '身份证号（建议脱敏：前6后4，中间*）',
  gender TEXT NOT NULL COMMENT '性别（1=男，2=女）',
  birth_date DATE NOT NULL COMMENT '出生日期',
  age INTEGER NOT NULL COMMENT '年龄（可自动计算）',
  education TEXT NOT NULL COMMENT '学历（本科/硕士/博士/大专等）',
  education_degree INTEGER NOT NULL COMMENT '学历编码（1=大专，2=本科，3=硕士，4=博士）',
  major TEXT COMMENT '所学专业',
  major_type TEXT COMMENT '专业类型（理工/文科/经管等，高新判定用）',
  entry_date DATE NOT NULL COMMENT '入职日期',
  work_years DECIMAL(4,1) NOT NULL COMMENT '司龄（年，保留1位小数）',
  total_work_years DECIMAL(4,1) COMMENT '总工作年限（年）',
  position_code TEXT NOT NULL COMMENT '岗位编码',
  position_name TEXT NOT NULL COMMENT '岗位名称',
  position_type TEXT NOT NULL COMMENT '岗位类型（研发/生产/销售/管理等，高新核心）',
  employment_type TEXT NOT NULL COMMENT '用工类型（正式/劳务派遣/实习/外包）',
  social_insurance_city TEXT COMMENT '社保缴纳城市',
  is_on_the_job INTEGER NOT NULL COMMENT '是否在职（1=是，0=否）',
  resign_date DATE COMMENT '离职日期',
  -- 高新判定核心字段
  is_high_tech_person INTEGER COMMENT '是否符合高新人员要求（1=是，0=否）',
  high_tech_cert_type TEXT COMMENT '高新认定资质类型（职称/学历/技能证书）',
  high_tech_cert_name TEXT COMMENT '高新认定资质名称（如：中级工程师/计算机硕士）',
  high_tech_work_days INTEGER COMMENT '年度在企业累计工作天数（高新要求≥183天）',
  -- 审计字段
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据更新时间',

  -- 唯一索引
  UNIQUE(employee_id)
);

-- 创建索引
CREATE INDEX idx_dept_code ON hr_employee_info(dept_code);
CREATE INDEX idx_position_type ON hr_employee_info(position_type);
CREATE INDEX idx_is_high_tech_person ON hr_employee_info(is_high_tech_person);
CREATE INDEX idx_is_on_the_job ON hr_employee_info(is_on_the_job);


----

CREATE TABLE hr_employee_salary (
  id INTEGER PRIMARY KEY AUTOINCREMENT COMMENT '主键ID',
  employee_id TEXT NOT NULL COMMENT '员工工号（关联hr_employee_info）',
  salary_month TEXT NOT NULL COMMENT '薪资所属月份（格式：YYYYMM，如202602）',

  -- ===================== 收入额计算 =====================
  income_wage DECIMAL(12,2) COMMENT '工资薪金收入（对应申报表“收入”）',
  income_bonus_yearly DECIMAL(12,2) COMMENT '全年一次性奖金',
  income_bonus_quarterly DECIMAL(12,2) COMMENT '季度奖',
  income_bonus_monthly DECIMAL(12,2) COMMENT '月度奖',
  income_bonus_performance DECIMAL(12,2) COMMENT '绩效奖金',
  income_bonus_other DECIMAL(12,2) COMMENT '其他奖金',
  allowance_transport DECIMAL(12,2) COMMENT '交通补贴',
  allowance_meal DECIMAL(12,2) COMMENT '餐补',
  allowance_housing DECIMAL(12,2) COMMENT '住房补贴',
  allowance_high_temp DECIMAL(12,2) COMMENT '高温补贴',
  allowance_shift DECIMAL(12,2) COMMENT '夜班/加班补贴',
  allowance_other DECIMAL(12,2) COMMENT '其他补贴',
  total_income DECIMAL(12,2) NOT NULL COMMENT '收入合计（对应申报表“收入”）',
  cost_deductible DECIMAL(12,2) COMMENT '减除费用（如5000元起征点）',
  tax_free_income DECIMAL(12,2) COMMENT '免税收入',
  other_income_deduct DECIMAL(12,2) COMMENT '其他减除费用',

  -- ===================== 专项扣除 =====================
  deduction_si_pension DECIMAL(12,2) COMMENT '基本养老保险费',
  deduction_si_medical DECIMAL(12,2) COMMENT '基本医疗保险费',
  deduction_si_unemployment DECIMAL(12,2) COMMENT '失业保险费',
  deduction_housing_fund DECIMAL(12,2) COMMENT '住房公积金',
  total_special_deduction DECIMAL(12,2) COMMENT '专项扣除合计',

  -- ===================== 专项附加扣除 =====================
  deduction_child_edu DECIMAL(12,2) COMMENT '子女教育专项附加扣除',
  deduction_continue_edu DECIMAL(12,2) COMMENT '继续教育专项附加扣除',
  deduction_housing_loan DECIMAL(12,2) COMMENT '住房贷款利息专项附加扣除',
  deduction_housing_rent DECIMAL(12,2) COMMENT '住房租金专项附加扣除',
  deduction_elderly_care DECIMAL(12,2) COMMENT '赡养老人专项附加扣除',
  deduction_3yo_child_care DECIMAL(12,2) COMMENT '3岁以下婴幼儿照护专项附加扣除',
  total_special_add_deduction DECIMAL(12,2) COMMENT '专项附加扣除合计',

  -- ===================== 其他扣除 =====================
  deduction_enterprise_annuity DECIMAL(12,2) COMMENT '企业年金/职业年金',
  deduction_commercial_health DECIMAL(12,2) COMMENT '商业健康保险',
  deduction_tax_deferred_pension DECIMAL(12,2) COMMENT '税收递延型商业养老保险',
  deduction_other_allowable DECIMAL(12,2) COMMENT '其他允许扣除的税费',
  total_other_deduction DECIMAL(12,2) COMMENT '其他扣除合计',

  -- ===================== 准予扣除的捐赠额 =====================
  donation_allowable DECIMAL(12,2) COMMENT '准予扣除的捐赠额',

  -- ===================== 税款计算 =====================
  taxable_income DECIMAL(12,2) NOT NULL COMMENT '应纳税所得额',
  tax_rate DECIMAL(5,2) COMMENT '税率（如3%、10%等）',
  quick_deduction DECIMAL(12,2) COMMENT '速算扣除数',
  tax_payable DECIMAL(12,2) NOT NULL COMMENT '应纳税额',
  tax_reduction DECIMAL(12,2) COMMENT '减免税额',
  tax_withheld DECIMAL(12,2) COMMENT '已预缴税额',
  tax_refund_or_pay DECIMAL(12,2) COMMENT '应补/退税额',

  -- ===================== 公司承担部分 =====================
  company_si_pension DECIMAL(12,2) COMMENT '公司承担养老保险',
  company_si_medical DECIMAL(12,2) COMMENT '公司承担医疗保险',
  company_si_unemployment DECIMAL(12,2) COMMENT '公司承担失业保险',
  company_si_injury DECIMAL(12,2) COMMENT '公司承担工伤保险',
  company_si_maternity DECIMAL(12,2) COMMENT '公司承担生育保险',
  company_housing_fund DECIMAL(12,2) COMMENT '公司承担住房公积金',
  company_total_benefit DECIMAL(12,2) COMMENT '公司承担五险一金合计',

  -- ===================== 实发与备注 =====================
  gross_salary DECIMAL(12,2) NOT NULL COMMENT '应发工资总额',
  net_salary DECIMAL(12,2) NOT NULL COMMENT '实发工资',
  remark TEXT COMMENT '备注',

  -- ===================== 审计字段 =====================
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据创建时间',
  update_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据更新时间',

  -- 唯一索引（SQLite通过UNIQUE约束实现）
  UNIQUE(employee_id, salary_month)
);

-- 创建索引提升查询效率（SQLite索引语法）
CREATE INDEX idx_salary_month ON hr_employee_salary(salary_month);
CREATE INDEX idx_employee_id ON hr_employee_salary(employee_id);

