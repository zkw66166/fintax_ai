## 企业所得税申报数据库设计文档

## （一）企业所得税年度申报数据库设计

### 1. 纳税人信息表（复用增值税方案）
```sql
-- 复用增值税设计中的 taxpayer_info 表
-- 略，参见增值税文档
```

### 2. 年度申报主记录表（封面信息）
```sql
CREATE TABLE eit_annual_filing (
    filing_id           TEXT PRIMARY KEY,                -- 申报实例唯一ID（可基于纳税人+年度+版本生成）
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,                 -- 税款所属年度
    revision_no         INTEGER NOT NULL DEFAULT 0,       -- 更正版本号
    -- 封面信息
    amount_unit         TEXT DEFAULT '元',                 -- 金额单位
    preparer            TEXT,                              -- 经办人
    preparer_id         TEXT,                              -- 经办人身份证号
    agent_organization  TEXT,                              -- 代理机构签章（名称）
    agent_credit_code   TEXT,                              -- 代理机构统一社会信用代码
    taxpayer_sign_date  DATE,                              -- 纳税人签章日期
    accepted_by         TEXT,                              -- 受理人
    accepting_tax_office TEXT,                              -- 受理税务机关（章）
    date_accepted       DATE,                              -- 受理日期
    -- ETL/元数据字段
    submitted_at        TIMESTAMP,                         -- 申报提交时间
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    etl_confidence      REAL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 主键约束：每个纳税人每年每个版本唯一
    UNIQUE (taxpayer_id, period_year, revision_no)
);

CREATE INDEX idx_eit_annual_filing_taxpayer ON eit_annual_filing(taxpayer_id);
CREATE INDEX idx_eit_annual_filing_period ON eit_annual_filing(period_year);
```

### 3. 年度基础信息表（EIT-A000000）
```sql
CREATE TABLE eit_annual_basic_info (
    filing_id           TEXT PRIMARY KEY REFERENCES eit_annual_filing(filing_id),

    -- 基本经营情况（必填）
    tax_return_type_code        TEXT,    -- 101 纳税申报企业类型（代码）
    branch_tax_payment_ratio    NUMERIC, -- 102 分支机构就地纳税比例（%）
    asset_avg                   NUMERIC, -- 103 资产总额平均值（万元）
    employee_avg                INTEGER, -- 104 从业人数平均值（人）
    industry_code               TEXT,    -- 105 所属国民经济行业（代码）
    restricted_or_prohibited    BOOLEAN, -- 106 从事国家限制或禁止行业（是/否）
    accounting_standard_code    TEXT,    -- 107 适用会计准则或会计制度（代码）
    use_general_fs_2019         BOOLEAN, -- 108 采用一般企业财务报表格式（2019年版）
    small_micro_enterprise      BOOLEAN, -- 109 小型微利企业
    listed_company              TEXT,    -- 110 上市公司：'境内'/'境外'/'否'

    -- 有关涉税事项情况（存在即填）
    equity_investment_business   BOOLEAN, -- 201 从事股权投资业务
    overseas_related_transaction BOOLEAN, -- 202 存在境外关联交易

    -- 203 境外所得信息（嵌套结构）
    foreign_tax_credit_method    TEXT,    -- 203-1 境外所得抵免方式：'分国不分项'/'不分国不分项'
    hainan_ftz_foreign_invest    BOOLEAN, -- 203-2 海南自贸港新增境外直接投资
    hainan_ftz_industry_category TEXT,    -- 若为是，产业类别：'旅游业'/'现代服务业'/'高新技术产业'

    venture_investment_partner   BOOLEAN, -- 204 有限合伙制创业投资企业的法人合伙人
    venture_investment_enterprise BOOLEAN, -- 205 创业投资企业
    tas_enterprise_type          TEXT,    -- 206 技术先进型服务企业类型（代码）
    non_profit_org               BOOLEAN, -- 207 非营利组织
    software_ic_enterprise_type  TEXT,    -- 208 软件、集成电路企业类型（代码）
    ic_project_type              TEXT,    -- 209 集成电路生产项目类型：'130纳米'/'65纳米'/'28纳米'

    -- 210 科技型中小企业
    tech_sme_reg_no1             TEXT,    -- 210-1 申报所属期年度入库编号1
    tech_sme_reg_date1           DATE,    -- 210-2 入库时间1
    tech_sme_reg_no2             TEXT,    -- 210-3 所属期下一年度入库编号2
    tech_sme_reg_date2           DATE,    -- 210-4 入库时间2

    -- 211 高新技术企业
    hi_tech_cert_no1             TEXT,    -- 211-1 证书编号1
    hi_tech_cert_date1           DATE,    -- 211-2 发证时间1
    hi_tech_cert_no2             TEXT,    -- 211-3 证书编号2
    hi_tech_cert_date2           DATE,    -- 211-4 发证时间2

    -- 212-214 重组事项
    reorganization_tax_treatment TEXT,    -- 212 重组事项税务处理方式：'一般性'/'特殊性'
    reorganization_type_code     TEXT,    -- 213 重组交易类型（代码）
    reorganization_party_type    TEXT,    -- 214 重组当事方类型（代码）

    -- 215-217 政策性搬迁
    relocation_start_date        DATE,    -- 215 政策性搬迁开始时间
    relocation_no_income_year    BOOLEAN, -- 216 发生政策性搬迁且停止生产经营无所得年度
    relocation_loss_deduction_year INTEGER, -- 217 政策性搬迁损失分期扣除年度

    -- 218-219 非货币性资产投资递延纳税
    nonmonetary_asset_invest     BOOLEAN, -- 218 发生非货币性资产对外投资递延纳税事项
    nonmonetary_asset_defer_year INTEGER, -- 219 非货币性资产对外投资转让所得递延纳税年度

    -- 220-221 技术成果投资入股递延纳税
    tech_achievement_invest      BOOLEAN, -- 220 发生技术成果投资入股递延纳税事项
    tech_achievement_defer_year  INTEGER, -- 221 技术成果投资入股递延纳税年度

    -- 222 资产（股权）划转特殊性税务处理
    asset_transfer_special_treatment BOOLEAN, -- 222 发生资产（股权）划转特殊性税务处理事项

    -- 223 债务重组所得递延纳税年度
    debt_restructuring_defer_year INTEGER, -- 223 债务重组所得递延纳税年度

    -- 元数据
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 注意：主要股东分红情况单独建表
```

### 4. 年度股东分红明细表
```sql
CREATE TABLE eit_annual_shareholder (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           TEXT NOT NULL REFERENCES eit_annual_filing(filing_id),
    shareholder_name    TEXT NOT NULL,      -- 股东名称
    id_type             TEXT,               -- 证件种类
    id_number           TEXT,               -- 证件号码
    investment_ratio    NUMERIC,            -- 投资比例(%)
    dividend_amount     NUMERIC,            -- 当年（决议日）分配的股息、红利等权益性投资收益金额
    nationality_or_address TEXT,            -- 国籍/注册地址
    is_remaining_total  BOOLEAN DEFAULT 0,  -- 是否为“其余股东合计”行
    UNIQUE (filing_id, shareholder_name, id_number)
);

CREATE INDEX idx_eit_annual_shareholder_filing ON eit_annual_shareholder(filing_id);
```

### 5. 年度主表（EIT-A100000）
```sql
CREATE TABLE eit_annual_main (
    filing_id           TEXT PRIMARY KEY REFERENCES eit_annual_filing(filing_id),

    -- 利润总额计算（行次1-18）
    revenue                     NUMERIC, -- 1
    cost                        NUMERIC, -- 2
    taxes_surcharges            NUMERIC, -- 3
    selling_expenses            NUMERIC, -- 4
    admin_expenses              NUMERIC, -- 5
    rd_expenses                 NUMERIC, -- 6
    financial_expenses          NUMERIC, -- 7
    other_gains                 NUMERIC, -- 8
    investment_income           NUMERIC, -- 9
    net_exposure_hedge_gains    NUMERIC, -- 10
    fair_value_change_gains     NUMERIC, -- 11
    credit_impairment_loss      NUMERIC, -- 12
    asset_impairment_loss       NUMERIC, -- 13
    asset_disposal_gains        NUMERIC, -- 14
    operating_profit            NUMERIC, -- 15
    non_operating_income        NUMERIC, -- 16
    non_operating_expenses      NUMERIC, -- 17
    total_profit                NUMERIC, -- 18

    -- 应纳税所得额计算（行次19-28）
    less_foreign_income         NUMERIC, -- 19
    add_tax_adjust_increase     NUMERIC, -- 20
    less_tax_adjust_decrease    NUMERIC, -- 21
    -- 22行（免税、减计收入及加计扣除）合计值
    exempt_income_deduction_total NUMERIC, -- 22
    add_foreign_tax_offset      NUMERIC, -- 23
    adjusted_taxable_income     NUMERIC, -- 24
    less_income_exemption       NUMERIC, -- 25
    less_losses_carried_forward NUMERIC, -- 26
    less_taxable_income_deduction NUMERIC, -- 27
    taxable_income              NUMERIC, -- 28

    -- 应纳税额计算（行次29-35）
    tax_rate                    NUMERIC, -- 29 (25%)
    tax_payable                 NUMERIC, -- 30 (28×29)
    -- 31行（减免所得税额）合计值
    tax_credit_total            NUMERIC, -- 31
    less_foreign_tax_credit     NUMERIC, -- 32
    tax_due                     NUMERIC, -- 33 (30-31-32)
    add_foreign_tax_due         NUMERIC, -- 34
    less_foreign_tax_credit_amount NUMERIC, -- 35

    -- 实际应补退税额计算（行次36-45）
    actual_tax_payable          NUMERIC, -- 36 (33+34-35)
    less_prepaid_tax            NUMERIC, -- 37
    tax_payable_or_refund       NUMERIC, -- 38 (36-37)
    hq_share                    NUMERIC, -- 39
    fiscal_central_share        NUMERIC, -- 40
    hq_dept_share               NUMERIC, -- 41
    less_ethnic_autonomous_relief NUMERIC, -- 42
    less_audit_adjustment       NUMERIC, -- 43
    less_special_adjustment     NUMERIC, -- 44
    final_tax_payable_or_refund NUMERIC, -- 45 (38-42-43-44)

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6. 年度优惠事项明细表（动态子行22.x、31.x）
```sql
CREATE TABLE eit_annual_incentive_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           TEXT NOT NULL REFERENCES eit_annual_filing(filing_id),
    section             TEXT NOT NULL,      -- 所属部分：'22'（免税、减计收入及加计扣除）或 '31'（减免所得税额）
    line_number         TEXT NOT NULL,      -- 子行号，如 '22.1', '22.2', '31.1', '31.2'
    incentive_name      TEXT NOT NULL,      -- 优惠事项名称
    amount              NUMERIC,            -- 金额（根据行次性质，可能是减免额或扣除额）
    UNIQUE (filing_id, section, line_number)
);

CREATE INDEX idx_eit_annual_incentive_filing ON eit_annual_incentive_items(filing_id);
```

---

## （二）企业所得税季度预缴申报数据库设计

### 1. 季度申报主记录表（封面信息）
```sql
CREATE TABLE eit_quarter_filing (
    filing_id           TEXT PRIMARY KEY,
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_quarter      INTEGER NOT NULL,   -- 1,2,3,4
    revision_no         INTEGER NOT NULL DEFAULT 0,
    -- 封面信息（参考年度）
    amount_unit         TEXT DEFAULT '元',
    preparer            TEXT,
    preparer_id         TEXT,
    agent_organization  TEXT,
    agent_credit_code   TEXT,
    taxpayer_sign_date  DATE,
    accepted_by         TEXT,
    accepting_tax_office TEXT,
    date_accepted       DATE,  
    -- ETL元数据
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    etl_confidence      REAL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (taxpayer_id, period_year, period_quarter, revision_no)
);

CREATE INDEX idx_eit_quarter_filing_taxpayer ON eit_quarter_filing(taxpayer_id);
CREATE INDEX idx_eit_quarter_filing_period ON eit_quarter_filing(period_year, period_quarter);
```

### 2. 季度主表（EIT-A200000）
```sql
CREATE TABLE eit_quarter_main (
    filing_id           TEXT PRIMARY KEY REFERENCES eit_quarter_filing(filing_id),

    -- 基础信息（季度申报表内置）
    -- 从业人数（季初/季末/季度平均值）
    employee_q1_begin   INTEGER, employee_q1_end   INTEGER,
    employee_q2_begin   INTEGER, employee_q2_end   INTEGER,
    employee_q3_begin   INTEGER, employee_q3_end   INTEGER,
    employee_q4_begin   INTEGER, employee_q4_end   INTEGER,
    employee_quarter_avg INTEGER,  -- 季度平均值

    -- 资产总额（万元）
    asset_q1_begin      NUMERIC, asset_q1_end      NUMERIC,
    asset_q2_begin      NUMERIC, asset_q2_end      NUMERIC,
    asset_q3_begin      NUMERIC, asset_q3_end      NUMERIC,
    asset_q4_begin      NUMERIC, asset_q4_end      NUMERIC,
    asset_quarter_avg   NUMERIC,  -- 季度平均值（万元）

    restricted_or_prohibited_industry BOOLEAN, -- 国家限制或禁止行业
    small_micro_enterprise           BOOLEAN, -- 小型微利企业

    -- 附报事项（事项1、事项2）——名称和金额，也可以拆分子表，这里先用字段存储
    attached_matter1_name   TEXT,
    attached_matter1_amount NUMERIC,
    attached_matter2_name   TEXT,
    attached_matter2_amount NUMERIC,

    -- 预缴税款计算（行次1-16，本年累计）
    revenue                         NUMERIC, -- 1
    cost                            NUMERIC, -- 2
    total_profit                    NUMERIC, -- 3
    add_specific_business_taxable_income NUMERIC, -- 4
    less_non_taxable_income         NUMERIC, -- 5
    less_accelerated_depreciation   NUMERIC, -- 6
    -- 7行（免税收入、减计收入、加计扣除）合计
    tax_free_income_deduction_total NUMERIC, -- 7
    -- 8行（所得减免）合计
    income_exemption_total          NUMERIC, -- 8
    less_losses_carried_forward     NUMERIC, -- 9
    actual_profit                   NUMERIC, -- 10
    tax_rate                        NUMERIC, -- 11 (25%)
    tax_payable                     NUMERIC, -- 12
    -- 13行（减免所得税额）合计
    tax_credit_total                NUMERIC, -- 13
    less_prepaid_tax_current_year   NUMERIC, -- 14
    less_specific_business_prepaid  NUMERIC, -- 15
    current_tax_payable_or_refund   NUMERIC, -- 16

    -- 总分机构税款计算（行次17-22）
    hq_share_total                  NUMERIC, -- 17
    hq_share                        NUMERIC, -- 18
    fiscal_central_share            NUMERIC, -- 19
    hq_business_dept_share          NUMERIC, -- 20
    branch_share_ratio              NUMERIC, -- 21
    branch_share_amount             NUMERIC, -- 22

    -- 实际缴纳企业所得税计算（行次23-24）
    -- 民族自治区减免
    ethnic_autonomous_relief_type   TEXT,    -- '免征'/'减征' / NULL
    ethnic_autonomous_relief_rate   NUMERIC, -- 减征幅度（%）
    ethnic_autonomous_relief_amount NUMERIC, -- 本年累计应减免金额
    final_tax_payable_or_refund     NUMERIC, -- 24

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. 季度优惠事项明细表（动态子行7.x、8.x、13.x）
```sql
CREATE TABLE eit_quarter_incentive_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           TEXT NOT NULL REFERENCES eit_quarter_filing(filing_id),
    section             TEXT NOT NULL,      -- '7'（免税收入、减计收入、加计扣除）, '8'（所得减免）, '13'（减免所得税额）
    line_number         TEXT NOT NULL,      -- 如 '7.1', '7.2', '8.1', '13.1' 等
    incentive_name      TEXT NOT NULL,
    amount              NUMERIC,
    UNIQUE (filing_id, section, line_number)
);

CREATE INDEX idx_eit_quarter_incentive_filing ON eit_quarter_incentive_items(filing_id);
```

### 4. 季度附报事项明细表（可选，若附报事项超过2个）
```sql
CREATE TABLE eit_quarter_attached_matters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           TEXT NOT NULL REFERENCES eit_quarter_filing(filing_id),
    matter_index        INTEGER,            -- 事项序号（1,2,3...）
    matter_name         TEXT,
    amount_or_option    TEXT,               -- 金额或选项（例如“是/否”或具体金额）
    UNIQUE (filing_id, matter_index)
);

CREATE INDEX idx_eit_quarter_matters_filing ON eit_quarter_attached_matters(filing_id);
```

---

## 关于动态子行的处理说明

年度主表和季度主表中的动态子行（如22.1、31.1等）具有不确定性和可扩展性，因此采用**子表存储**的方式，将每个优惠事项作为独立记录。这样避免了在物理表中预定义大量可能用不到的列，也便于NL2SQL查询时动态匹配。

- `section` 字段标识所属的行次大类（如22、31），`line_number` 保留原报表子行号（如22.1、22.2）。
- 在NL2SQL生成时，如果需要按具体优惠事项名称筛选，可以通过关联子表实现；如果需要获取合计值，可以直接使用主表中的合计字段（如 `exempt_income_deduction_total`）。

## 版本控制与更正申报

每张主记录表（filing表）都包含 `revision_no` 字段，主键为 `(taxpayer_id, period_year, revision_no)` 或季度为 `(taxpayer_id, period_year, period_quarter, revision_no)`。所有明细表通过 `filing_id` 关联到具体版本的申报实例。查询时默认取 `revision_no` 最大的版本（即最新更正版本）。

## 元数据字段

- `etl_batch_id`：ETL批次ID，便于追踪数据来源。
- `source_doc_id`：源文档标识（如PDF文件名或哈希）。
- `etl_confidence`：解析置信度（用于OCR等场景）。
- `submitted_at`：申报提交时间（如可获取）。
- `created_at` / `updated_at`：记录创建/更新时间。

## 后续扩展建议

1. **映射表**：可参照增值税方案建立 `eit_column_mapping` 表，将申报表栏次号映射到物理字段名，便于ETL转换。
2. **同义词表**：建立 `eit_synonyms` 表，记录用户口语化表达与标准字段名的映射，用于NL2SQL前置处理。
3. **视图**：为简化查询，可创建组合视图，例如：
   ```sql
   CREATE VIEW vw_eit_annual_full AS
   SELECT f.*, b.*, m.*
   FROM eit_annual_filing f
   LEFT JOIN eit_annual_basic_info b ON f.filing_id = b.filing_id
   LEFT JOIN eit_annual_main m ON f.filing_id = m.filing_id;
   ```
4. **校验日志表**：参考增值税方案中的 `etl_error_log`，记录ETL过程中的异常。

该设计满足企业所得税年度和季度申报表的结构化存储需求，同时为NL2SQL查询提供了良好的基础。

## 企业所得税申报数据库扩展设计（映射表、同义词表、视图、校验日志）

### 1. 栏次-字段映射表（ETL 专用）

#### 1.1 年度主表（`eit_annual_main`）映射表
```sql
-- 创建年度主表栏次映射表
CREATE TABLE IF NOT EXISTS eit_annual_main_column_mapping (
    line_number INTEGER PRIMARY KEY,    -- 行次（1~45）
    column_name TEXT NOT NULL,          -- 物理字段名（对应 eit_annual_main 中的字段）
    business_name TEXT                  -- 业务中文名（描述）
);

-- 插入年度主表映射记录
INSERT OR REPLACE INTO eit_annual_main_column_mapping (line_number, column_name, business_name) VALUES
(1, 'revenue', '营业收入'),
(2, 'cost', '营业成本'),
(3, 'taxes_surcharges', '税金及附加'),
(4, 'selling_expenses', '销售费用'),
(5, 'admin_expenses', '管理费用'),
(6, 'rd_expenses', '研发费用'),
(7, 'financial_expenses', '财务费用'),
(8, 'other_gains', '其他收益'),
(9, 'investment_income', '投资收益'),
(10, 'net_exposure_hedge_gains', '净敞口套期收益'),
(11, 'fair_value_change_gains', '公允价值变动收益'),
(12, 'credit_impairment_loss', '信用减值损失'),
(13, 'asset_impairment_loss', '资产减值损失'),
(14, 'asset_disposal_gains', '资产处置收益'),
(15, 'operating_profit', '营业利润'),
(16, 'non_operating_income', '营业外收入'),
(17, 'non_operating_expenses', '营业外支出'),
(18, 'total_profit', '利润总额'),
(19, 'less_foreign_income', '减：境外所得'),
(20, 'add_tax_adjust_increase', '加：纳税调整增加额'),
(21, 'less_tax_adjust_decrease', '减：纳税调整减少额'),
(22, 'exempt_income_deduction_total', '减：免税、减计收入及加计扣除'),
(23, 'add_foreign_tax_offset', '加：境外应税所得抵减境内亏损'),
(24, 'adjusted_taxable_income', '纳税调整后所得'),
(25, 'less_income_exemption', '减：所得减免'),
(26, 'less_losses_carried_forward', '减：弥补以前年度亏损'),
(27, 'less_taxable_income_deduction', '减：抵扣应纳税所得额'),
(28, 'taxable_income', '应纳税所得额'),
(29, 'tax_rate', '税率'),
(30, 'tax_payable', '应纳税所得额（原主表为30行）'),
(31, 'tax_credit_total', '减：减免所得税额'),
(32, 'less_foreign_tax_credit', '减：抵免所得税额'),
(33, 'tax_due', '应纳税额'),
(34, 'add_foreign_tax_due', '加：境外所得应纳所得税额'),
(35, 'less_foreign_tax_credit_amount', '减：境外所得抵免所得税额'),
(36, 'actual_tax_payable', '实际应纳所得税额'),
(37, 'less_prepaid_tax', '减：本年累计预缴所得税额'),
(38, 'tax_payable_or_refund', '本年应补（退）所得税额'),
(39, 'hq_share', '总机构分摊本年应补（退）所得税额'),
(40, 'fiscal_central_share', '财政集中分配本年应补（退）所得税额'),
(41, 'hq_dept_share', '总机构主体生产经营部门分摊本年应补（退）所得税额'),
(42, 'less_ethnic_autonomous_relief', '减：民族自治地区企业所得税地方分享部分'),
(43, 'less_audit_adjustment', '减：稽查查补（退）所得税额'),
(44, 'less_special_adjustment', '减：特别纳税调整补（退）所得税额'),
(45, 'final_tax_payable_or_refund', '本年实际应补（退）所得税额');
```

#### 1.2 季度主表（`eit_quarter_main`）映射表
```sql
-- 创建季度主表栏次映射表
CREATE TABLE IF NOT EXISTS eit_quarter_main_column_mapping (
    line_number INTEGER PRIMARY KEY,    -- 行次（1~24）
    column_name TEXT NOT NULL,
    business_name TEXT
);

INSERT OR REPLACE INTO eit_quarter_main_column_mapping (line_number, column_name, business_name) VALUES
(1, 'revenue', '营业收入'),
(2, 'cost', '营业成本'),
(3, 'total_profit', '利润总额'),
(4, 'add_specific_business_taxable_income', '加：特定业务计算的应纳税所得额'),
(5, 'less_non_taxable_income', '减：不征税收入'),
(6, 'less_accelerated_depreciation', '减：资产加速折旧、摊销（扣除）调减额'),
(7, 'tax_free_income_deduction_total', '减：免税收入、减计收入、加计扣除'),
(8, 'income_exemption_total', '减：所得减免'),
(9, 'less_losses_carried_forward', '减：弥补以前年度亏损'),
(10, 'actual_profit', '实际利润额'),
(11, 'tax_rate', '税率'),
(12, 'tax_payable', '应纳所得税额'),
(13, 'tax_credit_total', '减：减免所得税额'),
(14, 'less_prepaid_tax_current_year', '减：本年实际已缴纳所得税额'),
(15, 'less_specific_business_prepaid', '减：特定业务预缴（征）所得税额'),
(16, 'current_tax_payable_or_refund', '本期应补（退）所得税额'),
(17, 'hq_share_total', '总机构本期分摊应补（退）所得税额'),
(18, 'hq_share', '总机构分摊应补（退）所得税额'),
(19, 'fiscal_central_share', '财政集中分配应补（退）所得税额'),
(20, 'hq_business_dept_share', '总机构具有主体生产经营职能的部门分摊所得税额'),
(21, 'branch_share_ratio', '分支机构本期分摊比例'),
(22, 'branch_share_amount', '分支机构本期分摊应补（退）所得税额'),
(23, 'ethnic_autonomous_relief_amount', '民族自治地区企业所得税地方分享部分减免金额'),
(24, 'final_tax_payable_or_refund', '实际应补（退）所得税额');
```

> 注：季报主表中的 23 行在物理表中为 `ethnic_autonomous_relief_amount`，24 行为 `final_tax_payable_or_refund`。

---

### 2. 同义词映射表（NL2SQL 专用）

#### 2.1 表结构增强（支持分视图/分类型）
```sql
CREATE TABLE IF NOT EXISTS eit_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,            -- 用户口语化短语
    column_name TEXT NOT NULL,            -- 映射的目标字段名
    priority    INTEGER DEFAULT 1,        -- 优先级（数值越大越优先）
    scope_view  TEXT,                     -- 适用的视图名称：'vw_eit_annual_main'/'vw_eit_quarter_main'/NULL(通用)
    taxpayer_type TEXT,                    -- 纳税人类型：'一般纳税人'/'小规模纳税人'/NULL(通用)（企业所得税不区分，但保留以扩展）
    UNIQUE(phrase, column_name, scope_view)
);
CREATE INDEX idx_eit_synonyms_phrase ON eit_synonyms(phrase);
CREATE INDEX idx_eit_synonyms_scope ON eit_synonyms(scope_view, priority);
```

#### 2.2 年度主表同义词（示例节选，实际需全量插入）
```sql
-- 年度主表同义词
-- 第1栏：revenue
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第1栏', 'revenue', 3, 'vw_eit_annual_main'),
    ('1栏', 'revenue', 3, 'vw_eit_annual_main'),
    ('营业收入', 'revenue', 2, 'vw_eit_annual_main'),
    ('收入', 'revenue', 1, 'vw_eit_annual_main'),
    ('主营收入', 'revenue', 1, 'vw_eit_annual_main');

-- 第2栏：cost
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第2栏', 'cost', 3, 'vw_eit_annual_main'),
    ('2栏', 'cost', 3, 'vw_eit_annual_main'),
    ('营业成本', 'cost', 2, 'vw_eit_annual_main'),
    ('成本', 'cost', 1, 'vw_eit_annual_main'),
    ('主营业务成本', 'cost', 1, 'vw_eit_annual_main');

-- 第3栏：taxes_surcharges
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第3栏', 'taxes_surcharges', 3, 'vw_eit_annual_main'),
    ('3栏', 'taxes_surcharges', 3, 'vw_eit_annual_main'),
    ('税金及附加', 'taxes_surcharges', 2, 'vw_eit_annual_main'),
    ('税金', 'taxes_surcharges', 1, 'vw_eit_annual_main'),
    ('附加税', 'taxes_surcharges', 1, 'vw_eit_annual_main');

-- 第4栏：selling_expenses
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第4栏', 'selling_expenses', 3, 'vw_eit_annual_main'),
    ('4栏', 'selling_expenses', 3, 'vw_eit_annual_main'),
    ('销售费用', 'selling_expenses', 2, 'vw_eit_annual_main'),
    ('销售费', 'selling_expenses', 1, 'vw_eit_annual_main');

-- 第5栏：admin_expenses
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第5栏', 'admin_expenses', 3, 'vw_eit_annual_main'),
    ('5栏', 'admin_expenses', 3, 'vw_eit_annual_main'),
    ('管理费用', 'admin_expenses', 2, 'vw_eit_annual_main'),
    ('管理费', 'admin_expenses', 1, 'vw_eit_annual_main');

-- 第6栏：rd_expenses
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第6栏', 'rd_expenses', 3, 'vw_eit_annual_main'),
    ('6栏', 'rd_expenses', 3, 'vw_eit_annual_main'),
    ('研发费用', 'rd_expenses', 2, 'vw_eit_annual_main'),
    ('研发费', 'rd_expenses', 1, 'vw_eit_annual_main'),
    ('R&D费用', 'rd_expenses', 1, 'vw_eit_annual_main');

-- 第7栏：financial_expenses
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第7栏', 'financial_expenses', 3, 'vw_eit_annual_main'),
    ('7栏', 'financial_expenses', 3, 'vw_eit_annual_main'),
    ('财务费用', 'financial_expenses', 2, 'vw_eit_annual_main'),
    ('财务费', 'financial_expenses', 1, 'vw_eit_annual_main'),
    ('利息支出', 'financial_expenses', 1, 'vw_eit_annual_main'); -- 注意：财务费用包含利息，但不完全等同，需谨慎

-- 第8栏：other_gains
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第8栏', 'other_gains', 3, 'vw_eit_annual_main'),
    ('8栏', 'other_gains', 3, 'vw_eit_annual_main'),
    ('其他收益', 'other_gains', 2, 'vw_eit_annual_main'),
    ('其他利得', 'other_gains', 1, 'vw_eit_annual_main');

-- 第9栏：investment_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第9栏', 'investment_income', 3, 'vw_eit_annual_main'),
    ('9栏', 'investment_income', 3, 'vw_eit_annual_main'),
    ('投资收益', 'investment_income', 2, 'vw_eit_annual_main'),
    ('投资净收益', 'investment_income', 1, 'vw_eit_annual_main');

-- 第10栏：net_exposure_hedge_gains
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第10栏', 'net_exposure_hedge_gains', 3, 'vw_eit_annual_main'),
    ('10栏', 'net_exposure_hedge_gains', 3, 'vw_eit_annual_main'),
    ('净敞口套期收益', 'net_exposure_hedge_gains', 2, 'vw_eit_annual_main'),
    ('套期收益', 'net_exposure_hedge_gains', 1, 'vw_eit_annual_main');

-- 第11栏：fair_value_change_gains
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第11栏', 'fair_value_change_gains', 3, 'vw_eit_annual_main'),
    ('11栏', 'fair_value_change_gains', 3, 'vw_eit_annual_main'),
    ('公允价值变动收益', 'fair_value_change_gains', 2, 'vw_eit_annual_main'),
    ('公允价值变动', 'fair_value_change_gains', 1, 'vw_eit_annual_main');

-- 第12栏：credit_impairment_loss
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第12栏', 'credit_impairment_loss', 3, 'vw_eit_annual_main'),
    ('12栏', 'credit_impairment_loss', 3, 'vw_eit_annual_main'),
    ('信用减值损失', 'credit_impairment_loss', 2, 'vw_eit_annual_main'),
    ('信用损失', 'credit_impairment_loss', 1, 'vw_eit_annual_main'),
    ('坏账损失', 'credit_impairment_loss', 1, 'vw_eit_annual_main'); -- 注意：信用减值损失包含坏账，但需确认口径

-- 第13栏：asset_impairment_loss
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第13栏', 'asset_impairment_loss', 3, 'vw_eit_annual_main'),
    ('13栏', 'asset_impairment_loss', 3, 'vw_eit_annual_main'),
    ('资产减值损失', 'asset_impairment_loss', 2, 'vw_eit_annual_main'),
    ('资产减值', 'asset_impairment_loss', 1, 'vw_eit_annual_main');

-- 第14栏：asset_disposal_gains
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第14栏', 'asset_disposal_gains', 3, 'vw_eit_annual_main'),
    ('14栏', 'asset_disposal_gains', 3, 'vw_eit_annual_main'),
    ('资产处置收益', 'asset_disposal_gains', 2, 'vw_eit_annual_main'),
    ('资产处置利得', 'asset_disposal_gains', 1, 'vw_eit_annual_main');

-- 第15栏：operating_profit
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第15栏', 'operating_profit', 3, 'vw_eit_annual_main'),
    ('15栏', 'operating_profit', 3, 'vw_eit_annual_main'),
    ('营业利润', 'operating_profit', 2, 'vw_eit_annual_main'),
    ('经营利润', 'operating_profit', 1, 'vw_eit_annual_main');

-- 第16栏：non_operating_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第16栏', 'non_operating_income', 3, 'vw_eit_annual_main'),
    ('16栏', 'non_operating_income', 3, 'vw_eit_annual_main'),
    ('营业外收入', 'non_operating_income', 2, 'vw_eit_annual_main'),
    ('营业外收益', 'non_operating_income', 1, 'vw_eit_annual_main');

-- 第17栏：non_operating_expenses
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第17栏', 'non_operating_expenses', 3, 'vw_eit_annual_main'),
    ('17栏', 'non_operating_expenses', 3, 'vw_eit_annual_main'),
    ('营业外支出', 'non_operating_expenses', 2, 'vw_eit_annual_main'),
    ('营业外费用', 'non_operating_expenses', 1, 'vw_eit_annual_main');

-- 第18栏：total_profit
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第18栏', 'total_profit', 3, 'vw_eit_annual_main'),
    ('18栏', 'total_profit', 3, 'vw_eit_annual_main'),
    ('利润总额', 'total_profit', 2, 'vw_eit_annual_main'),
    ('税前利润', 'total_profit', 1, 'vw_eit_annual_main'),
    ('会计利润', 'total_profit', 1, 'vw_eit_annual_main');

-- 第19栏：less_foreign_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第19栏', 'less_foreign_income', 3, 'vw_eit_annual_main'),
    ('19栏', 'less_foreign_income', 3, 'vw_eit_annual_main'),
    ('减境外所得', 'less_foreign_income', 2, 'vw_eit_annual_main'),
    ('境外所得', 'less_foreign_income', 1, 'vw_eit_annual_main'); -- 注意："减：境外所得"是减去项，用户可能只说"境外所得"，需上下文判断

-- 第20栏：add_tax_adjust_increase
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第20栏', 'add_tax_adjust_increase', 3, 'vw_eit_annual_main'),
    ('20栏', 'add_tax_adjust_increase', 3, 'vw_eit_annual_main'),
    ('纳税调整增加额', 'add_tax_adjust_increase', 2, 'vw_eit_annual_main'),
    ('调增', 'add_tax_adjust_increase', 1, 'vw_eit_annual_main'),
    ('纳税调增', 'add_tax_adjust_increase', 1, 'vw_eit_annual_main');

-- 第21栏：less_tax_adjust_decrease
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第21栏', 'less_tax_adjust_decrease', 3, 'vw_eit_annual_main'),
    ('21栏', 'less_tax_adjust_decrease', 3, 'vw_eit_annual_main'),
    ('纳税调整减少额', 'less_tax_adjust_decrease', 2, 'vw_eit_annual_main'),
    ('调减', 'less_tax_adjust_decrease', 1, 'vw_eit_annual_main'),
    ('纳税调减', 'less_tax_adjust_decrease', 1, 'vw_eit_annual_main');

-- 第22栏：exempt_income_deduction_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第22栏', 'exempt_income_deduction_total', 3, 'vw_eit_annual_main'),
    ('22栏', 'exempt_income_deduction_total', 3, 'vw_eit_annual_main'),
    ('免税减计收入加计扣除', 'exempt_income_deduction_total', 2, 'vw_eit_annual_main'),
    ('免税收入', 'exempt_income_deduction_total', 1, 'vw_eit_annual_main'), -- 注意：22栏是合计，可能需拆分子项，但同义词可指向合计
    ('减计收入', 'exempt_income_deduction_total', 1, 'vw_eit_annual_main'),
    ('加计扣除', 'exempt_income_deduction_total', 1, 'vw_eit_annual_main');

-- 第23栏：add_foreign_tax_offset
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第23栏', 'add_foreign_tax_offset', 3, 'vw_eit_annual_main'),
    ('23栏', 'add_foreign_tax_offset', 3, 'vw_eit_annual_main'),
    ('境外应税所得抵减境内亏损', 'add_foreign_tax_offset', 2, 'vw_eit_annual_main'),
    ('境外所得抵亏', 'add_foreign_tax_offset', 1, 'vw_eit_annual_main');

-- 第24栏：adjusted_taxable_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第24栏', 'adjusted_taxable_income', 3, 'vw_eit_annual_main'),
    ('24栏', 'adjusted_taxable_income', 3, 'vw_eit_annual_main'),
    ('纳税调整后所得', 'adjusted_taxable_income', 2, 'vw_eit_annual_main'),
    ('调整后所得', 'adjusted_taxable_income', 1, 'vw_eit_annual_main');

-- 第25栏：less_income_exemption
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第25栏', 'less_income_exemption', 3, 'vw_eit_annual_main'),
    ('25栏', 'less_income_exemption', 3, 'vw_eit_annual_main'),
    ('所得减免', 'less_income_exemption', 2, 'vw_eit_annual_main'),
    ('减免所得', 'less_income_exemption', 1, 'vw_eit_annual_main');

-- 第26栏：less_losses_carried_forward
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第26栏', 'less_losses_carried_forward', 3, 'vw_eit_annual_main'),
    ('26栏', 'less_losses_carried_forward', 3, 'vw_eit_annual_main'),
    ('弥补以前年度亏损', 'less_losses_carried_forward', 2, 'vw_eit_annual_main'),
    ('弥补亏损', 'less_losses_carried_forward', 1, 'vw_eit_annual_main'),
    ('补亏', 'less_losses_carried_forward', 1, 'vw_eit_annual_main');

-- 第27栏：less_taxable_income_deduction
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第27栏', 'less_taxable_income_deduction', 3, 'vw_eit_annual_main'),
    ('27栏', 'less_taxable_income_deduction', 3, 'vw_eit_annual_main'),
    ('抵扣应纳税所得额', 'less_taxable_income_deduction', 2, 'vw_eit_annual_main'),
    ('抵扣所得', 'less_taxable_income_deduction', 1, 'vw_eit_annual_main'),
    ('投资抵扣', 'less_taxable_income_deduction', 1, 'vw_eit_annual_main'); -- 如创业投资抵扣

-- 第28栏：taxable_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第28栏', 'taxable_income', 3, 'vw_eit_annual_main'),
    ('28栏', 'taxable_income', 3, 'vw_eit_annual_main'),
    ('应纳税所得额', 'taxable_income', 2, 'vw_eit_annual_main'),
    ('应税所得', 'taxable_income', 1, 'vw_eit_annual_main'),
    ('计税基础', 'taxable_income', 1, 'vw_eit_annual_main');

-- 第29栏：tax_rate
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第29栏', 'tax_rate', 3, 'vw_eit_annual_main'),
    ('29栏', 'tax_rate', 3, 'vw_eit_annual_main'),
    ('税率', 'tax_rate', 2, 'vw_eit_annual_main'),
    ('所得税率', 'tax_rate', 1, 'vw_eit_annual_main');

-- 第30栏：tax_payable
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第30栏', 'tax_payable', 3, 'vw_eit_annual_main'),
    ('30栏', 'tax_payable', 3, 'vw_eit_annual_main'),
    ('应纳税额', 'tax_payable', 2, 'vw_eit_annual_main'),
    ('应纳所得税额', 'tax_payable', 1, 'vw_eit_annual_main'),
    ('所得税额', 'tax_payable', 1, 'vw_eit_annual_main');

-- 第31栏：tax_credit_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第31栏', 'tax_credit_total', 3, 'vw_eit_annual_main'),
    ('31栏', 'tax_credit_total', 3, 'vw_eit_annual_main'),
    ('减免所得税额', 'tax_credit_total', 2, 'vw_eit_annual_main'),
    ('所得税减免', 'tax_credit_total', 1, 'vw_eit_annual_main'),
    ('减免税额', 'tax_credit_total', 1, 'vw_eit_annual_main');

-- 第32栏：less_foreign_tax_credit
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第32栏', 'less_foreign_tax_credit', 3, 'vw_eit_annual_main'),
    ('32栏', 'less_foreign_tax_credit', 3, 'vw_eit_annual_main'),
    ('抵免所得税额', 'less_foreign_tax_credit', 2, 'vw_eit_annual_main'),
    ('境外抵免', 'less_foreign_tax_credit', 1, 'vw_eit_annual_main');

-- 第33栏：tax_due
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第33栏', 'tax_due', 3, 'vw_eit_annual_main'),
    ('33栏', 'tax_due', 3, 'vw_eit_annual_main'),
    ('应纳税额（33栏）', 'tax_due', 2, 'vw_eit_annual_main'),
    ('应纳所得税（33）', 'tax_due', 1, 'vw_eit_annual_main');

-- 第34栏：add_foreign_tax_due
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第34栏', 'add_foreign_tax_due', 3, 'vw_eit_annual_main'),
    ('34栏', 'add_foreign_tax_due', 3, 'vw_eit_annual_main'),
    ('境外所得应纳所得税额', 'add_foreign_tax_due', 2, 'vw_eit_annual_main'),
    ('境外应纳税', 'add_foreign_tax_due', 1, 'vw_eit_annual_main');

-- 第35栏：less_foreign_tax_credit_amount
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第35栏', 'less_foreign_tax_credit_amount', 3, 'vw_eit_annual_main'),
    ('35栏', 'less_foreign_tax_credit_amount', 3, 'vw_eit_annual_main'),
    ('境外所得抵免所得税额', 'less_foreign_tax_credit_amount', 2, 'vw_eit_annual_main'),
    ('境外抵免额', 'less_foreign_tax_credit_amount', 1, 'vw_eit_annual_main');

-- 第36栏：actual_tax_payable
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第36栏', 'actual_tax_payable', 3, 'vw_eit_annual_main'),
    ('36栏', 'actual_tax_payable', 3, 'vw_eit_annual_main'),
    ('实际应纳所得税额', 'actual_tax_payable', 2, 'vw_eit_annual_main'),
    ('实际应纳税', 'actual_tax_payable', 1, 'vw_eit_annual_main');

-- 第37栏：less_prepaid_tax
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第37栏', 'less_prepaid_tax', 3, 'vw_eit_annual_main'),
    ('37栏', 'less_prepaid_tax', 3, 'vw_eit_annual_main'),
    ('本年累计预缴所得税额', 'less_prepaid_tax', 2, 'vw_eit_annual_main'),
    ('预缴税额', 'less_prepaid_tax', 1, 'vw_eit_annual_main'),
    ('已预缴', 'less_prepaid_tax', 1, 'vw_eit_annual_main');

-- 第38栏：tax_payable_or_refund
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第38栏', 'tax_payable_or_refund', 3, 'vw_eit_annual_main'),
    ('38栏', 'tax_payable_or_refund', 3, 'vw_eit_annual_main'),
    ('本年应补退所得税额', 'tax_payable_or_refund', 2, 'vw_eit_annual_main'),
    ('应补退税', 'tax_payable_or_refund', 1, 'vw_eit_annual_main'),
    ('应补退', 'tax_payable_or_refund', 1, 'vw_eit_annual_main');

-- 第39栏：hq_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第39栏', 'hq_share', 3, 'vw_eit_annual_main'),
    ('39栏', 'hq_share', 3, 'vw_eit_annual_main'),
    ('总机构分摊', 'hq_share', 2, 'vw_eit_annual_main'),
    ('总部应补退', 'hq_share', 1, 'vw_eit_annual_main');

-- 第40栏：fiscal_central_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第40栏', 'fiscal_central_share', 3, 'vw_eit_annual_main'),
    ('40栏', 'fiscal_central_share', 3, 'vw_eit_annual_main'),
    ('财政集中分配', 'fiscal_central_share', 2, 'vw_eit_annual_main'),
    ('财政分配', 'fiscal_central_share', 1, 'vw_eit_annual_main');

-- 第41栏：hq_dept_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第41栏', 'hq_dept_share', 3, 'vw_eit_annual_main'),
    ('41栏', 'hq_dept_share', 3, 'vw_eit_annual_main'),
    ('总机构主体部门分摊', 'hq_dept_share', 2, 'vw_eit_annual_main'),
    ('总部部门分摊', 'hq_dept_share', 1, 'vw_eit_annual_main');

-- 第42栏：less_ethnic_autonomous_relief
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第42栏', 'less_ethnic_autonomous_relief', 3, 'vw_eit_annual_main'),
    ('42栏', 'less_ethnic_autonomous_relief', 3, 'vw_eit_annual_main'),
    ('民族自治地方减免', 'less_ethnic_autonomous_relief', 2, 'vw_eit_annual_main'),
    ('民族减免', 'less_ethnic_autonomous_relief', 1, 'vw_eit_annual_main');

-- 第43栏：less_audit_adjustment
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第43栏', 'less_audit_adjustment', 3, 'vw_eit_annual_main'),
    ('43栏', 'less_audit_adjustment', 3, 'vw_eit_annual_main'),
    ('稽查查补退税额', 'less_audit_adjustment', 2, 'vw_eit_annual_main'),
    ('稽查补退税', 'less_audit_adjustment', 1, 'vw_eit_annual_main');

-- 第44栏：less_special_adjustment
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第44栏', 'less_special_adjustment', 3, 'vw_eit_annual_main'),
    ('44栏', 'less_special_adjustment', 3, 'vw_eit_annual_main'),
    ('特别纳税调整补退税', 'less_special_adjustment', 2, 'vw_eit_annual_main'),
    ('特别调整', 'less_special_adjustment', 1, 'vw_eit_annual_main');

-- 第45栏：final_tax_payable_or_refund
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第45栏', 'final_tax_payable_or_refund', 3, 'vw_eit_annual_main'),
    ('45栏', 'final_tax_payable_or_refund', 3, 'vw_eit_annual_main'),
    ('本年实际应补退所得税额', 'final_tax_payable_or_refund', 2, 'vw_eit_annual_main'),
    ('最终应补退税', 'final_tax_payable_or_refund', 1, 'vw_eit_annual_main'),
    ('实际应补退', 'final_tax_payable_or_refund', 1, 'vw_eit_annual_main');
```

#### 2.3 季度主表同义词（示例）
```sql

-- 季度主表同义词（基于 eit_quarter_main_column_mapping）
-- 第1栏：revenue
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第1栏', 'revenue', 3, 'vw_eit_quarter_main'),
    ('1栏', 'revenue', 3, 'vw_eit_quarter_main'),
    ('营业收入', 'revenue', 2, 'vw_eit_quarter_main'),
    ('收入', 'revenue', 1, 'vw_eit_quarter_main');

-- 第2栏：cost
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第2栏', 'cost', 3, 'vw_eit_quarter_main'),
    ('2栏', 'cost', 3, 'vw_eit_quarter_main'),
    ('营业成本', 'cost', 2, 'vw_eit_quarter_main'),
    ('成本', 'cost', 1, 'vw_eit_quarter_main');

-- 第3栏：total_profit
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第3栏', 'total_profit', 3, 'vw_eit_quarter_main'),
    ('3栏', 'total_profit', 3, 'vw_eit_quarter_main'),
    ('利润总额', 'total_profit', 2, 'vw_eit_quarter_main'),
    ('利润', 'total_profit', 1, 'vw_eit_quarter_main'),
    ('税前利润', 'total_profit', 1, 'vw_eit_quarter_main');

-- 第4栏：add_specific_business_taxable_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第4栏', 'add_specific_business_taxable_income', 3, 'vw_eit_quarter_main'),
    ('4栏', 'add_specific_business_taxable_income', 3, 'vw_eit_quarter_main'),
    ('特定业务计算的应纳税所得额', 'add_specific_business_taxable_income', 2, 'vw_eit_quarter_main'),
    ('特定业务所得', 'add_specific_business_taxable_income', 1, 'vw_eit_quarter_main');

-- 第5栏：less_non_taxable_income
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第5栏', 'less_non_taxable_income', 3, 'vw_eit_quarter_main'),
    ('5栏', 'less_non_taxable_income', 3, 'vw_eit_quarter_main'),
    ('不征税收入', 'less_non_taxable_income', 2, 'vw_eit_quarter_main'),
    ('不征税', 'less_non_taxable_income', 1, 'vw_eit_quarter_main');

-- 第6栏：less_accelerated_depreciation
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第6栏', 'less_accelerated_depreciation', 3, 'vw_eit_quarter_main'),
    ('6栏', 'less_accelerated_depreciation', 3, 'vw_eit_quarter_main'),
    ('资产加速折旧调减额', 'less_accelerated_depreciation', 2, 'vw_eit_quarter_main'),
    ('加速折旧', 'less_accelerated_depreciation', 1, 'vw_eit_quarter_main');

-- 第7栏：tax_free_income_deduction_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第7栏', 'tax_free_income_deduction_total', 3, 'vw_eit_quarter_main'),
    ('7栏', 'tax_free_income_deduction_total', 3, 'vw_eit_quarter_main'),
    ('免税收入减计收入加计扣除', 'tax_free_income_deduction_total', 2, 'vw_eit_quarter_main'),
    ('免税收入', 'tax_free_income_deduction_total', 1, 'vw_eit_quarter_main'),
    ('减计收入', 'tax_free_income_deduction_total', 1, 'vw_eit_quarter_main'),
    ('加计扣除', 'tax_free_income_deduction_total', 1, 'vw_eit_quarter_main');

-- 第8栏：income_exemption_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第8栏', 'income_exemption_total', 3, 'vw_eit_quarter_main'),
    ('8栏', 'income_exemption_total', 3, 'vw_eit_quarter_main'),
    ('所得减免', 'income_exemption_total', 2, 'vw_eit_quarter_main'),
    ('减免所得', 'income_exemption_total', 1, 'vw_eit_quarter_main');

-- 第9栏：less_losses_carried_forward
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第9栏', 'less_losses_carried_forward', 3, 'vw_eit_quarter_main'),
    ('9栏', 'less_losses_carried_forward', 3, 'vw_eit_quarter_main'),
    ('弥补以前年度亏损', 'less_losses_carried_forward', 2, 'vw_eit_quarter_main'),
    ('弥补亏损', 'less_losses_carried_forward', 1, 'vw_eit_quarter_main');

-- 第10栏：actual_profit
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第10栏', 'actual_profit', 3, 'vw_eit_quarter_main'),
    ('10栏', 'actual_profit', 3, 'vw_eit_quarter_main'),
    ('实际利润额', 'actual_profit', 2, 'vw_eit_quarter_main'),
    ('实际利润', 'actual_profit', 1, 'vw_eit_quarter_main'),
    ('实际所得', 'actual_profit', 1, 'vw_eit_quarter_main');

-- 第11栏：tax_rate
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第11栏', 'tax_rate', 3, 'vw_eit_quarter_main'),
    ('11栏', 'tax_rate', 3, 'vw_eit_quarter_main'),
    ('税率', 'tax_rate', 2, 'vw_eit_quarter_main'),
    ('所得税率', 'tax_rate', 1, 'vw_eit_quarter_main');

-- 第12栏：tax_payable
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第12栏', 'tax_payable', 3, 'vw_eit_quarter_main'),
    ('12栏', 'tax_payable', 3, 'vw_eit_quarter_main'),
    ('应纳所得税额', 'tax_payable', 2, 'vw_eit_quarter_main'),
    ('应纳税额', 'tax_payable', 1, 'vw_eit_quarter_main');

-- 第13栏：tax_credit_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第13栏', 'tax_credit_total', 3, 'vw_eit_quarter_main'),
    ('13栏', 'tax_credit_total', 3, 'vw_eit_quarter_main'),
    ('减免所得税额', 'tax_credit_total', 2, 'vw_eit_quarter_main'),
    ('减免税额', 'tax_credit_total', 1, 'vw_eit_quarter_main');

-- 第14栏：less_prepaid_tax_current_year
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第14栏', 'less_prepaid_tax_current_year', 3, 'vw_eit_quarter_main'),
    ('14栏', 'less_prepaid_tax_current_year', 3, 'vw_eit_quarter_main'),
    ('本年实际已缴纳所得税额', 'less_prepaid_tax_current_year', 2, 'vw_eit_quarter_main'),
    ('已预缴', 'less_prepaid_tax_current_year', 1, 'vw_eit_quarter_main'),
    ('本年已缴', 'less_prepaid_tax_current_year', 1, 'vw_eit_quarter_main');

-- 第15栏：less_specific_business_prepaid
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第15栏', 'less_specific_business_prepaid', 3, 'vw_eit_quarter_main'),
    ('15栏', 'less_specific_business_prepaid', 3, 'vw_eit_quarter_main'),
    ('特定业务预缴所得税额', 'less_specific_business_prepaid', 2, 'vw_eit_quarter_main'),
    ('特定预缴', 'less_specific_business_prepaid', 1, 'vw_eit_quarter_main');

-- 第16栏：current_tax_payable_or_refund
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第16栏', 'current_tax_payable_or_refund', 3, 'vw_eit_quarter_main'),
    ('16栏', 'current_tax_payable_or_refund', 3, 'vw_eit_quarter_main'),
    ('本期应补退所得税额', 'current_tax_payable_or_refund', 2, 'vw_eit_quarter_main'),
    ('本期应补退税', 'current_tax_payable_or_refund', 1, 'vw_eit_quarter_main'),
    ('应补退', 'current_tax_payable_or_refund', 1, 'vw_eit_quarter_main');

-- 第17栏：hq_share_total
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第17栏', 'hq_share_total', 3, 'vw_eit_quarter_main'),
    ('17栏', 'hq_share_total', 3, 'vw_eit_quarter_main'),
    ('总机构本期分摊应补退所得税额', 'hq_share_total', 2, 'vw_eit_quarter_main'),
    ('总机构分摊', 'hq_share_total', 1, 'vw_eit_quarter_main');

-- 第18栏：hq_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第18栏', 'hq_share', 3, 'vw_eit_quarter_main'),
    ('18栏', 'hq_share', 3, 'vw_eit_quarter_main'),
    ('总机构分摊应补退所得税额', 'hq_share', 2, 'vw_eit_quarter_main'),
    ('总机构部分', 'hq_share', 1, 'vw_eit_quarter_main');

-- 第19栏：fiscal_central_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第19栏', 'fiscal_central_share', 3, 'vw_eit_quarter_main'),
    ('19栏', 'fiscal_central_share', 3, 'vw_eit_quarter_main'),
    ('财政集中分配应补退所得税额', 'fiscal_central_share', 2, 'vw_eit_quarter_main'),
    ('财政分配', 'fiscal_central_share', 1, 'vw_eit_quarter_main');

-- 第20栏：hq_business_dept_share
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第20栏', 'hq_business_dept_share', 3, 'vw_eit_quarter_main'),
    ('20栏', 'hq_business_dept_share', 3, 'vw_eit_quarter_main'),
    ('总机构主体生产经营部门分摊', 'hq_business_dept_share', 2, 'vw_eit_quarter_main'),
    ('总部部门分摊', 'hq_business_dept_share', 1, 'vw_eit_quarter_main');

-- 第21栏：branch_share_ratio
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第21栏', 'branch_share_ratio', 3, 'vw_eit_quarter_main'),
    ('21栏', 'branch_share_ratio', 3, 'vw_eit_quarter_main'),
    ('分支机构本期分摊比例', 'branch_share_ratio', 2, 'vw_eit_quarter_main'),
    ('分支比例', 'branch_share_ratio', 1, 'vw_eit_quarter_main');

-- 第22栏：branch_share_amount
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第22栏', 'branch_share_amount', 3, 'vw_eit_quarter_main'),
    ('22栏', 'branch_share_amount', 3, 'vw_eit_quarter_main'),
    ('分支机构本期分摊应补退所得税额', 'branch_share_amount', 2, 'vw_eit_quarter_main'),
    ('分支分摊', 'branch_share_amount', 1, 'vw_eit_quarter_main');

-- 第23栏：ethnic_autonomous_relief_amount
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第23栏', 'ethnic_autonomous_relief_amount', 3, 'vw_eit_quarter_main'),
    ('23栏', 'ethnic_autonomous_relief_amount', 3, 'vw_eit_quarter_main'),
    ('民族自治地区减免金额', 'ethnic_autonomous_relief_amount', 2, 'vw_eit_quarter_main'),
    ('民族减免', 'ethnic_autonomous_relief_amount', 1, 'vw_eit_quarter_main');

-- 第24栏：final_tax_payable_or_refund
INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES
    ('第24栏', 'final_tax_payable_or_refund', 3, 'vw_eit_quarter_main'),
    ('24栏', 'final_tax_payable_or_refund', 3, 'vw_eit_quarter_main'),
    ('实际应补退所得税额', 'final_tax_payable_or_refund', 2, 'vw_eit_quarter_main'),
    ('最终应补退', 'final_tax_payable_or_refund', 1, 'vw_eit_quarter_main');
```

> 同义词表的构建可结合映射表，通过脚本批量生成常见的“第X栏”、“X栏”、“栏次X”以及标准中文名称。同时，可根据业务反馈不断补充用户常用短语。

---

### 3. 视图（简化查询入口）

#### 3.1 年度申报综合视图
```sql
CREATE VIEW vw_eit_annual_full AS
SELECT
    f.*,                             -- eit_annual_filing 所有字段（含封面信息）
    b.* EXCLUDE (filing_id),         -- eit_annual_basic_info 除 filing_id 外所有字段
    m.* EXCLUDE (filing_id)          -- eit_annual_main 除 filing_id 外所有字段
FROM eit_annual_filing f
LEFT JOIN eit_annual_basic_info b ON f.filing_id = b.filing_id
LEFT JOIN eit_annual_main m ON f.filing_id = m.filing_id;
```

#### 3.2 年度主表单独视图（方便NL2SQL指定）
```sql
CREATE VIEW vw_eit_annual_main AS
SELECT
    f.filing_id,
    f.taxpayer_id,
    f.period_year,
    f.revision_no,
    f.preparer,
    f.受理税务机关,
    f.受理日期,
    f.submitted_at,
    f.etl_batch_id,
    f.source_doc_id,
    m.*
FROM eit_annual_filing f
JOIN eit_annual_main m ON f.filing_id = m.filing_id;
```

#### 3.3 年度基础信息视图
```sql
CREATE VIEW vw_eit_annual_basic AS
SELECT
    f.filing_id,
    f.taxpayer_id,
    f.period_year,
    f.revision_no,
    b.*
FROM eit_annual_filing f
JOIN eit_annual_basic_info b ON f.filing_id = b.filing_id;
```

#### 3.4 年度股东分红明细视图
```sql
CREATE VIEW vw_eit_annual_shareholder AS
SELECT
    f.taxpayer_id,
    f.period_year,
    f.revision_no,
    s.*
FROM eit_annual_filing f
JOIN eit_annual_shareholder s ON f.filing_id = s.filing_id;
```

#### 3.5 年度优惠事项明细视图
```sql
CREATE VIEW vw_eit_annual_incentive AS
SELECT
    f.taxpayer_id,
    f.period_year,
    f.revision_no,
    i.*
FROM eit_annual_filing f
JOIN eit_annual_incentive_items i ON f.filing_id = i.filing_id;
```

#### 3.6 季度申报综合视图
```sql
CREATE VIEW vw_eit_quarter_full AS
SELECT
    f.*,
    m.* EXCLUDE (filing_id)
FROM eit_quarter_filing f
LEFT JOIN eit_quarter_main m ON f.filing_id = m.filing_id;
```

#### 3.7 季度主表视图
```sql
CREATE VIEW vw_eit_quarter_main AS
SELECT
    f.filing_id,
    f.taxpayer_id,
    f.period_year,
    f.period_quarter,
    f.revision_no,
    f.preparer,
    f.受理税务机关,
    f.受理日期,
    f.submitted_at,
    f.etl_batch_id,
    f.source_doc_id,
    m.*
FROM eit_quarter_filing f
JOIN eit_quarter_main m ON f.filing_id = m.filing_id;
```

#### 3.8 季度优惠事项明细视图
```sql
CREATE VIEW vw_eit_quarter_incentive AS
SELECT
    f.taxpayer_id,
    f.period_year,
    f.period_quarter,
    f.revision_no,
    i.*
FROM eit_quarter_filing f
JOIN eit_quarter_incentive_items i ON f.filing_id = i.filing_id;
```

---

### 4. ETL 校验日志表（复用并适配）

建议复用增值税方案中的 `etl_error_log`，但可添加 `tax_type` 字段区分税种，或直接使用同一张表并在 `table_name` 中注明。

```sql
CREATE TABLE IF NOT EXISTS etl_error_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    etl_batch_id  TEXT,
    source_doc_id TEXT,
    taxpayer_id   TEXT,
    period_year   INTEGER,
    period_month  INTEGER,      -- 对年报可能为空
    table_name    TEXT,          -- 例如 'eit_annual_main', 'eit_quarter_main'
    error_type    TEXT,          -- 'parse', 'validate', 'unit', 'constraint', 'missing_required'
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_etl_error_batch ON etl_error_log(etl_batch_id);
CREATE INDEX IF NOT EXISTS idx_etl_error_taxpayer ON etl_error_log(taxpayer_id);
```

对于季度数据，可复用 `period_month` 字段存储季度数（如1,2,3,4）或添加 `period_quarter` 字段。根据实际需求调整。

---

### 5. 总结

通过以上补充，企业所得税申报数据库具备了完整的ETL映射、NL2SQL同义词支持、便捷查询视图以及错误追踪能力。整体设计遵循了增值税方案的分层原则，为后续的智能查询和数据分析奠定了坚实基础。