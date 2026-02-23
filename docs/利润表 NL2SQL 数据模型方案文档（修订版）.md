# 利润表 NL2SQL 数据模型方案文档（修订版）  
**版本**：**v1.1** | **最后更新**：2026-02-17  

## 1. 项目背景与目标  

利润表是企业财务报表的核心组成部分，反映企业在一定会计期间的经营成果。包含**企业会计准则**与**小企业会计准则**两套标准，每套报表以垂直列示项目，包含**本期金额**与**本年累计金额**两列数据。未来需扩展至金融保险企业会计准则及其他会计制度。  

目标：构建一套**面向 NL2SQL 的分析型数据模型**，支持：  
- 用户通过自然语言查询任意纳税人、任意期次的利润表明细数据；  
- 兼容企业会计准则、小企业会计准则，并预留未来扩展能力；  
- ETL 可从 PDF/Excel 等异构来源稳定导入；  
- 存储紧凑、查询高效，大模型 SQL 生成准确率 ≥95%。  

## 2. 核心挑战  

| 挑战 | 描述 |  
|------|------|  
| **多准则异构性** | 两套报表项目名称、行次、数量不一致，未来可能新增其他准则，需统一建模。 |  
| **时期指标** | 利润表存储本期发生额和本年累计额，而非时点余额，需在纵表中区分指标类型。 |  
| **明细项目与合计项并存** | 报表包含大量明细项（如利息费用）和汇总项（如营业利润），需保留原始行次和层次关系。 |  
| **NL2SQL 歧义** | 用户口语化表达（如“营业收入”“第5行”“净利润”）需精准映射到具体准则下的具体项目。 |  
| **扩展性** | 未来新增准则需在不破坏已有模型的前提下无缝接入。 |  

## 3. 设计原则  

1. **存储与查询解耦**：底层采用**纵表（EAV）**存储所有准则的明细项目，保证扩展性；查询侧为每个准则构建**宽表视图**，消除 NL2SQL 的复杂性。  
2. **字段名即业务术语**：视图中的列名采用标准英文编码加后缀 `_current`（本期）和 `_cumulative`（本年累计），并通过同义词表映射用户口语。  
3. **同义词集中管理**：用单独映射表存储用户口语→标准字段的映射，支持按准则类型过滤。  
4. **维度行拍平**：每个纳税人每期每个准则的每个项目作为一行，存储本期金额与本年累计金额，彻底消除稀疏性。  
5. **一次设计，无限扩展**：新增准则只需在字典表中定义项目，并创建对应视图，不破坏已有数据与查询。  

## 4. 数据模型详细设计  

### 4.1 利润表明细表（`fs_income_statement_item`）  

存储所有准则下每个项目的本期金额与本年累计金额，支持版本追溯。  

```sql
CREATE TABLE fs_income_statement_item (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    gaap_type           TEXT NOT NULL,   -- 'CAS'（企业会计准则）, 'SAS'（小企业会计准则）, 未来可扩展
    item_code           TEXT NOT NULL,   -- 标准项目编码（如 'OPERATING_REVENUE'）

    -- 版本追溯
    revision_no         INTEGER NOT NULL DEFAULT 0,
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    source_unit         TEXT DEFAULT '元',
    etl_confidence      REAL,

    -- 指标
    current_amount      NUMERIC,         -- 本期金额
    cumulative_amount   NUMERIC,         -- 本年累计金额

    -- 冗余字段（可选，便于查询）
    item_name           TEXT,            -- 项目名称（如“营业收入”）
    line_number         INTEGER,         -- 原始行次（如 1）
    category            TEXT,            -- 项目类别，如 'OPERATING', 'NON_OPERATING', 'COMPREHENSIVE'

    PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
    CHECK (gaap_type IN ('CAS', 'SAS')),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_is_period ON fs_income_statement_item (period_year, period_month);
CREATE INDEX idx_is_taxpayer ON fs_income_statement_item (taxpayer_id);
CREATE INDEX idx_is_taxpayer_period ON fs_income_statement_item (taxpayer_id, period_year, period_month);
```

### 4.2 项目字典表（`fs_income_statement_item_dict`）  

定义每个准则下的项目编码、显示名称、行次、所属类别，用于 ETL 映射和视图生成。  

```sql
CREATE TABLE fs_income_statement_item_dict (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    gaap_type       TEXT NOT NULL,        -- 'CAS' 或 'SAS'
    item_code       TEXT NOT NULL,        -- 标准编码
    item_name       TEXT NOT NULL,        -- 该准则下的显示名称
    line_number     INTEGER,              -- 该准则下的行次
    category        TEXT,                 -- 类别，如 'OPERATING', 'NON_OPERATING', 'COMPREHENSIVE'
    display_order   INTEGER,              -- 显示顺序（用于视图列排序）
    is_total        BOOLEAN DEFAULT 0,    -- 是否为合计项（如营业利润、净利润）
    UNIQUE (gaap_type, item_code)
);
```

#### 4.2.1 企业会计准则（CAS）字典数据  

```sql
INSERT INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES
('CAS', 'OPERATING_REVENUE', '营业收入', 1, 'OPERATING', 10, 0),
('CAS', 'OPERATING_COST', '减：营业成本', 2, 'OPERATING', 20, 0),
('CAS', 'TAXES_AND_SURCHARGES', '税金及附加', 3, 'OPERATING', 30, 0),
('CAS', 'SELLING_EXPENSE', '销售费用', 4, 'OPERATING', 40, 0),
('CAS', 'ADMINISTRATIVE_EXPENSE', '管理费用', 5, 'OPERATING', 50, 0),
('CAS', 'RD_EXPENSE', '研发费用', 6, 'OPERATING', 60, 0),
('CAS', 'FINANCIAL_EXPENSE', '财务费用', 7, 'OPERATING', 70, 0),
('CAS', 'INTEREST_EXPENSE', '其中：利息费用', 8, 'OPERATING', 80, 0),
('CAS', 'INTEREST_INCOME', '利息收入', 9, 'OPERATING', 90, 0),
('CAS', 'OTHER_GAINS', '其他收益', 10, 'OPERATING', 100, 0),
('CAS', 'INVESTMENT_INCOME', '投资收益（损失以“－”号填列）', 11, 'OPERATING', 110, 0),
('CAS', 'INVESTMENT_INCOME_ASSOCIATES_JV', '其中：对联营企业和合营企业的投资收益', 12, 'OPERATING', 120, 0),
('CAS', 'GAINS_ON_DERECOGNITION_AC', '以摊余成本计量的金融资产终止确认收益', 13, 'OPERATING', 130, 0),
('CAS', 'NET_OPEN_HEDGE_GAINS', '净敞口套期收益', 14, 'OPERATING', 140, 0),
('CAS', 'FAIR_VALUE_CHANGE_GAINS', '公允价值变动收益', 15, 'OPERATING', 150, 0),
('CAS', 'CREDIT_IMPAIRMENT_LOSS', '信用减值损失', 16, 'OPERATING', 160, 0),
('CAS', 'ASSET_IMPAIRMENT_LOSS', '资产减值损失', 17, 'OPERATING', 170, 0),
('CAS', 'ASSET_DISPOSAL_GAINS', '资产处置收益', 18, 'OPERATING', 180, 0),
('CAS', 'OPERATING_PROFIT', '营业利润（亏损以“－”号填列）', 19, 'OPERATING', 190, 1),
('CAS', 'NON_OPERATING_INCOME', '营业外收入', 20, 'NON_OPERATING', 200, 0),
('CAS', 'NON_OPERATING_EXPENSE', '营业外支出', 21, 'NON_OPERATING', 210, 0),
('CAS', 'PROFIT_BEFORE_TAX', '利润总额（亏损总额以“－”号填列）', 22, 'PROFIT', 220, 1),
('CAS', 'INCOME_TAX_EXPENSE', '所得税费用', 23, 'PROFIT', 230, 0),
('CAS', 'NET_PROFIT', '净利润（净亏损以“－”号填列）', 24, 'PROFIT', 240, 1),
('CAS', 'NET_PROFIT_CONTINUING', '（一）持续经营净利润', 25, 'PROFIT', 250, 0),
('CAS', 'NET_PROFIT_DISCONTINUING', '（二）终止经营净利润', 26, 'PROFIT', 260, 0),
('CAS', 'OTHER_COMPREHENSIVE_INCOME', '五、其他综合收益的税后净额', 27, 'COMPREHENSIVE', 270, 1),
('CAS', 'OCI_NON_RECLASS', '（一）不能重分类进损益的其他综合收益', 28, 'COMPREHENSIVE', 280, 1),
('CAS', 'OCI_REMEASUREMENT_DEFINED_BENEFIT', '1.重新计量设定受益计划变动额', 29, 'COMPREHENSIVE', 290, 0),
('CAS', 'OCI_EQ_METHOD_NON_RECLASS', '2.权益法下不能转损益的其他综合收益', 30, 'COMPREHENSIVE', 300, 0),
('CAS', 'OCI_FAIR_VALUE_CHANGE_OTHER_EQUITY', '3.其他权益工具投资公允价值变动', 31, 'COMPREHENSIVE', 310, 0),
('CAS', 'OCI_CREDIT_RISK_CHANGE', '4.企业自身信用风险公允价值变动', 32, 'COMPREHENSIVE', 320, 0),
('CAS', 'OCI_RECLASS', '（二）将重分类进损益的其他综合收益', 33, 'COMPREHENSIVE', 330, 1),
('CAS', 'OCI_EQ_METHOD_RECLASS', '1.权益法下可转损益的其他综合收益', 34, 'COMPREHENSIVE', 340, 0),
('CAS', 'OCI_FAIR_VALUE_CHANGE_OTHER_DEBT', '2.其他债权投资公允价值变动', 35, 'COMPREHENSIVE', 350, 0),
('CAS', 'OCI_RECLASSIFICATION_ADJUSTMENT', '3.金融资产重分类计入其他综合收益的金额', 36, 'COMPREHENSIVE', 360, 0),
('CAS', 'OCI_CREDIT_IMPAIRMENT_OTHER_DEBT', '4.其他债权投资信用减值准备', 37, 'COMPREHENSIVE', 370, 0),
('CAS', 'OCI_CASH_FLOW_HEDGE_RESERVE', '5.现金流量套期储备', 38, 'COMPREHENSIVE', 380, 0),
('CAS', 'OCI_FOREIGN_CURRENCY_TRANSLATION', '6.外币财务报表折算差额', 39, 'COMPREHENSIVE', 390, 0),
('CAS', 'TOTAL_COMPREHENSIVE_INCOME', '六、综合收益总额', 40, 'COMPREHENSIVE', 400, 1),
('CAS', 'BASIC_EPS', '(一) 基本每股收益', 42, 'EPS', 410, 0),
('CAS', 'DILUTED_EPS', '(二) 稀释每股收益', 43, 'EPS', 420, 0);
```

#### 4.2.2 小企业会计准则（SAS）字典数据  

```sql
INSERT INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES
('SAS', 'OPERATING_REVENUE', '一、营业收入', 1, 'OPERATING', 10, 0),
('SAS', 'OPERATING_COST', '减：营业成本', 2, 'OPERATING', 20, 0),
('SAS', 'TAXES_AND_SURCHARGES', '税金及附加', 3, 'OPERATING', 30, 0),
('SAS', 'CONSUMPTION_TAX', '其中：消费税', 4, 'OPERATING', 40, 0),
('SAS', 'BUSINESS_TAX', '营业税', 5, 'OPERATING', 50, 0),
('SAS', 'CITY_MAINTENANCE_TAX', '城市维护建设税', 6, 'OPERATING', 60, 0),
('SAS', 'RESOURCE_TAX', '资源税', 7, 'OPERATING', 70, 0),
('SAS', 'LAND_APPRECIATION_TAX', '土地增值税', 8, 'OPERATING', 80, 0),
('SAS', 'PROPERTY_AND_OTHER_TAXES', '城镇土地使用税、房产税、车船税、印花税', 9, 'OPERATING', 90, 0),
('SAS', 'EDUCATION_SURCHARGE_AND_OTHER', '教育费附加、矿产资源补偿费、排污费', 10, 'OPERATING', 100, 0),
('SAS', 'SELLING_EXPENSE', '销售费用', 11, 'OPERATING', 110, 0),
('SAS', 'SELLING_EXPENSE_REPAIR', '其中：商品维修费', 12, 'OPERATING', 120, 0),
('SAS', 'SELLING_EXPENSE_ADVERTISING', '广告费和业务宣传费', 13, 'OPERATING', 130, 0),
('SAS', 'ADMINISTRATIVE_EXPENSE', '管理费用', 14, 'OPERATING', 140, 0),
('SAS', 'ADMINISTRATIVE_EXPENSE_ORGANIZATION', '其中：开办费', 15, 'OPERATING', 150, 0),
('SAS', 'ADMINISTRATIVE_EXPENSE_ENTERTAINMENT', '业务招待费', 16, 'OPERATING', 160, 0),
('SAS', 'ADMINISTRATIVE_EXPENSE_RESEARCH', '研究费用', 17, 'OPERATING', 170, 0),
('SAS', 'FINANCIAL_EXPENSE', '财务费用', 18, 'OPERATING', 180, 0),
('SAS', 'INTEREST_EXPENSE', '其中：利息费用（收入以“-”号填列）', 19, 'OPERATING', 190, 0),
('SAS', 'INVESTMENT_INCOME', '加：投资收益（亏损以“-”号填列）', 20, 'OPERATING', 200, 0),
('SAS', 'OPERATING_PROFIT', '二、营业利润（亏损以“-”号填列）', 21, 'OPERATING', 210, 1),
('SAS', 'NON_OPERATING_INCOME', '加：营业外收入', 22, 'NON_OPERATING', 220, 0),
('SAS', 'NON_OPERATING_INCOME_GOV_GRANT', '其中：政府补助', 23, 'NON_OPERATING', 230, 0),
('SAS', 'NON_OPERATING_EXPENSE', '减：营业外支出', 24, 'NON_OPERATING', 240, 0),
('SAS', 'NON_OPERATING_EXPENSE_BAD_DEBT', '其中：坏账损失', 25, 'NON_OPERATING', 250, 0),
('SAS', 'NON_OPERATING_EXPENSE_LOSS_LONG_TERM_BOND', '无法收回的长期债券投资损失', 26, 'NON_OPERATING', 260, 0),
('SAS', 'NON_OPERATING_EXPENSE_LOSS_LONG_TERM_EQUITY', '无法收回的长期股权投资损失', 27, 'NON_OPERATING', 270, 0),
('SAS', 'NON_OPERATING_EXPENSE_FORCE_MAJEURE', '自然灾害等不可抗力因素造成的损失', 28, 'NON_OPERATING', 280, 0),
('SAS', 'NON_OPERATING_EXPENSE_TAX_LATE_FEE', '税收滞纳金', 29, 'NON_OPERATING', 290, 0),
('SAS', 'PROFIT_BEFORE_TAX', '三、利润总额（亏损总额以“-”号填列）', 30, 'PROFIT', 300, 1),
('SAS', 'INCOME_TAX_EXPENSE', '减：所得税费用', 31, 'PROFIT', 310, 0),
('SAS', 'NET_PROFIT', '四、净利润（净亏损以“-”号填列）', 32, 'PROFIT', 320, 1);
```

### 4.3 同义词映射表（`fs_income_statement_synonyms`）  

将用户口语化表达（含栏次号、简称）映射到标准字段名（视图中的列名），支持按准则过滤。  

```sql
CREATE TABLE fs_income_statement_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,               -- 用户输入短语，如“营业收入”“第1行”“净利润”
    column_name TEXT NOT NULL,               -- 映射到的标准列名，如 'operating_revenue_current' 或 'net_profit_cumulative'
    gaap_type   TEXT,                         -- 适用准则，NULL 表示通用
    priority    INTEGER DEFAULT 1,
    UNIQUE(phrase, column_name)
);

CREATE INDEX idx_is_synonyms_phrase ON fs_income_statement_synonyms(phrase);
CREATE INDEX idx_is_synonyms_gaap ON fs_income_statement_synonyms(gaap_type, priority);
```

#### 4.3.1 同义词生成规则与完整映射表  

为便于维护，同义词映射表可通过脚本根据字典表自动生成。基本规则如下：  
- 对于每个准则的每个项目（字典表中的记录），生成以下同义词：  
  - **项目名称** → `{item_code}_current`（默认映射到本期金额，优先级2）  
  - 项目名称 + “本期” → `{item_code}_current`（优先级2）  
  - 项目名称 + “累计” / “本年累计” → `{item_code}_cumulative`（优先级2）  
  - **行次**（如“第1行”“1行”） → `{item_code}_current`（优先级3）  
  - 常用简称（如“营收”映射到 `operating_revenue_current`）需人工补充。  

以下为按此规则生成的完整同义词映射表（仅列出每个项目的核心映射，实际使用时可扩展）。  

##### 企业会计准则（CAS）同义词映射  

| phrase | column_name | gaap_type | priority |
|--------|-------------|-----------|----------|
| 营业收入 | operating_revenue_current | CAS | 2 |
| 营业收入本期 | operating_revenue_current | CAS | 2 |
| 营业收入累计 | operating_revenue_cumulative | CAS | 2 |
| 第1行 | operating_revenue_current | CAS | 3 |
| 1行 | operating_revenue_current | CAS | 3 |
| 营业成本 | operating_cost_current | CAS | 2 |
| 营业成本本期 | operating_cost_current | CAS | 2 |
| 营业成本累计 | operating_cost_cumulative | CAS | 2 |
| 第2行 | operating_cost_current | CAS | 3 |
| 税金及附加 | taxes_and_surcharges_current | CAS | 2 |
| 第3行 | taxes_and_surcharges_current | CAS | 3 |
| 销售费用 | selling_expense_current | CAS | 2 |
| 第4行 | selling_expense_current | CAS | 3 |
| 管理费用 | administrative_expense_current | CAS | 2 |
| 第5行 | administrative_expense_current | CAS | 3 |
| 研发费用 | rd_expense_current | CAS | 2 |
| 第6行 | rd_expense_current | CAS | 3 |
| 财务费用 | financial_expense_current | CAS | 2 |
| 第7行 | financial_expense_current | CAS | 3 |
| 利息费用 | interest_expense_current | CAS | 2 |
| 第8行 | interest_expense_current | CAS | 3 |
| 利息收入 | interest_income_current | CAS | 2 |
| 第9行 | interest_income_current | CAS | 3 |
| 其他收益 | other_gains_current | CAS | 2 |
| 第10行 | other_gains_current | CAS | 3 |
| 投资收益 | investment_income_current | CAS | 2 |
| 第11行 | investment_income_current | CAS | 3 |
| 对联营企业和合营企业的投资收益 | investment_income_associates_jv_current | CAS | 2 |
| 第12行 | investment_income_associates_jv_current | CAS | 3 |
| 以摊余成本计量的金融资产终止确认收益 | gains_on_derecognition_ac_current | CAS | 2 |
| 第13行 | gains_on_derecognition_ac_current | CAS | 3 |
| 净敞口套期收益 | net_open_hedge_gains_current | CAS | 2 |
| 第14行 | net_open_hedge_gains_current | CAS | 3 |
| 公允价值变动收益 | fair_value_change_gains_current | CAS | 2 |
| 第15行 | fair_value_change_gains_current | CAS | 3 |
| 信用减值损失 | credit_impairment_loss_current | CAS | 2 |
| 第16行 | credit_impairment_loss_current | CAS | 3 |
| 资产减值损失 | asset_impairment_loss_current | CAS | 2 |
| 第17行 | asset_impairment_loss_current | CAS | 3 |
| 资产处置收益 | asset_disposal_gains_current | CAS | 2 |
| 第18行 | asset_disposal_gains_current | CAS | 3 |
| 营业利润 | operating_profit_current | CAS | 2 |
| 营业利润本期 | operating_profit_current | CAS | 2 |
| 营业利润累计 | operating_profit_cumulative | CAS | 2 |
| 第19行 | operating_profit_current | CAS | 3 |
| 营业外收入 | non_operating_income_current | CAS | 2 |
| 第20行 | non_operating_income_current | CAS | 3 |
| 营业外支出 | non_operating_expense_current | CAS | 2 |
| 第21行 | non_operating_expense_current | CAS | 3 |
| 利润总额 | profit_before_tax_current | CAS | 2 |
| 第22行 | profit_before_tax_current | CAS | 3 |
| 所得税费用 | income_tax_expense_current | CAS | 2 |
| 第23行 | income_tax_expense_current | CAS | 3 |
| 净利润 | net_profit_current | CAS | 2 |
| 净利润本期 | net_profit_current | CAS | 2 |
| 净利润累计 | net_profit_cumulative | CAS | 2 |
| 第24行 | net_profit_current | CAS | 3 |
| 持续经营净利润 | net_profit_continuing_current | CAS | 2 |
| 第25行 | net_profit_continuing_current | CAS | 3 |
| 终止经营净利润 | net_profit_discontinuing_current | CAS | 2 |
| 第26行 | net_profit_discontinuing_current | CAS | 3 |
| 其他综合收益 | other_comprehensive_income_current | CAS | 2 |
| 第27行 | other_comprehensive_income_current | CAS | 3 |
| 不能重分类进损益的其他综合收益 | oci_non_reclass_current | CAS | 2 |
| 第28行 | oci_non_reclass_current | CAS | 3 |
| 重新计量设定受益计划变动额 | oci_remeasurement_defined_benefit_current | CAS | 2 |
| 第29行 | oci_remeasurement_defined_benefit_current | CAS | 3 |
| 权益法下不能转损益的其他综合收益 | oci_eq_method_non_reclass_current | CAS | 2 |
| 第30行 | oci_eq_method_non_reclass_current | CAS | 3 |
| 其他权益工具投资公允价值变动 | oci_fair_value_change_other_equity_current | CAS | 2 |
| 第31行 | oci_fair_value_change_other_equity_current | CAS | 3 |
| 企业自身信用风险公允价值变动 | oci_credit_risk_change_current | CAS | 2 |
| 第32行 | oci_credit_risk_change_current | CAS | 3 |
| 将重分类进损益的其他综合收益 | oci_reclass_current | CAS | 2 |
| 第33行 | oci_reclass_current | CAS | 3 |
| 权益法下可转损益的其他综合收益 | oci_eq_method_reclass_current | CAS | 2 |
| 第34行 | oci_eq_method_reclass_current | CAS | 3 |
| 其他债权投资公允价值变动 | oci_fair_value_change_other_debt_current | CAS | 2 |
| 第35行 | oci_fair_value_change_other_debt_current | CAS | 3 |
| 金融资产重分类计入其他综合收益的金额 | oci_reclassification_adjustment_current | CAS | 2 |
| 第36行 | oci_reclassification_adjustment_current | CAS | 3 |
| 其他债权投资信用减值准备 | oci_credit_impairment_other_debt_current | CAS | 2 |
| 第37行 | oci_credit_impairment_other_debt_current | CAS | 3 |
| 现金流量套期储备 | oci_cash_flow_hedge_reserve_current | CAS | 2 |
| 第38行 | oci_cash_flow_hedge_reserve_current | CAS | 3 |
| 外币财务报表折算差额 | oci_foreign_currency_translation_current | CAS | 2 |
| 第39行 | oci_foreign_currency_translation_current | CAS | 3 |
| 综合收益总额 | total_comprehensive_income_current | CAS | 2 |
| 第40行 | total_comprehensive_income_current | CAS | 3 |
| 基本每股收益 | basic_eps_current | CAS | 2 |
| 第42行 | basic_eps_current | CAS | 3 |
| 稀释每股收益 | diluted_eps_current | CAS | 2 |
| 第43行 | diluted_eps_current | CAS | 3 |

##### 小企业会计准则（SAS）同义词映射  

| phrase | column_name | gaap_type | priority |
|--------|-------------|-----------|----------|
| 营业收入 | operating_revenue_current | SAS | 2 |
| 营业收入本期 | operating_revenue_current | SAS | 2 |
| 营业收入累计 | operating_revenue_cumulative | SAS | 2 |
| 第1行 | operating_revenue_current | SAS | 3 |
| 营业成本 | operating_cost_current | SAS | 2 |
| 第2行 | operating_cost_current | SAS | 3 |
| 税金及附加 | taxes_and_surcharges_current | SAS | 2 |
| 第3行 | taxes_and_surcharges_current | SAS | 3 |
| 消费税 | consumption_tax_current | SAS | 2 |
| 第4行 | consumption_tax_current | SAS | 3 |
| 营业税 | business_tax_current | SAS | 2 |
| 第5行 | business_tax_current | SAS | 3 |
| 城市维护建设税 | city_maintenance_tax_current | SAS | 2 |
| 第6行 | city_maintenance_tax_current | SAS | 3 |
| 资源税 | resource_tax_current | SAS | 2 |
| 第7行 | resource_tax_current | SAS | 3 |
| 土地增值税 | land_appreciation_tax_current | SAS | 2 |
| 第8行 | land_appreciation_tax_current | SAS | 3 |
| 城镇土地使用税、房产税、车船税、印花税 | property_and_other_taxes_current | SAS | 2 |
| 第9行 | property_and_other_taxes_current | SAS | 3 |
| 教育费附加、矿产资源补偿费、排污费 | education_surcharge_and_other_current | SAS | 2 |
| 第10行 | education_surcharge_and_other_current | SAS | 3 |
| 销售费用 | selling_expense_current | SAS | 2 |
| 第11行 | selling_expense_current | SAS | 3 |
| 商品维修费 | selling_expense_repair_current | SAS | 2 |
| 第12行 | selling_expense_repair_current | SAS | 3 |
| 广告费和业务宣传费 | selling_expense_advertising_current | SAS | 2 |
| 第13行 | selling_expense_advertising_current | SAS | 3 |
| 管理费用 | administrative_expense_current | SAS | 2 |
| 第14行 | administrative_expense_current | SAS | 3 |
| 开办费 | administrative_expense_organization_current | SAS | 2 |
| 第15行 | administrative_expense_organization_current | SAS | 3 |
| 业务招待费 | administrative_expense_entertainment_current | SAS | 2 |
| 第16行 | administrative_expense_entertainment_current | SAS | 3 |
| 研究费用 | administrative_expense_research_current | SAS | 2 |
| 第17行 | administrative_expense_research_current | SAS | 3 |
| 财务费用 | financial_expense_current | SAS | 2 |
| 第18行 | financial_expense_current | SAS | 3 |
| 利息费用 | interest_expense_current | SAS | 2 |
| 第19行 | interest_expense_current | SAS | 3 |
| 投资收益 | investment_income_current | SAS | 2 |
| 第20行 | investment_income_current | SAS | 3 |
| 营业利润 | operating_profit_current | SAS | 2 |
| 第21行 | operating_profit_current | SAS | 3 |
| 营业外收入 | non_operating_income_current | SAS | 2 |
| 第22行 | non_operating_income_current | SAS | 3 |
| 政府补助 | non_operating_income_gov_grant_current | SAS | 2 |
| 第23行 | non_operating_income_gov_grant_current | SAS | 3 |
| 营业外支出 | non_operating_expense_current | SAS | 2 |
| 第24行 | non_operating_expense_current | SAS | 3 |
| 坏账损失 | non_operating_expense_bad_debt_current | SAS | 2 |
| 第25行 | non_operating_expense_bad_debt_current | SAS | 3 |
| 无法收回的长期债券投资损失 | non_operating_expense_loss_long_term_bond_current | SAS | 2 |
| 第26行 | non_operating_expense_loss_long_term_bond_current | SAS | 3 |
| 无法收回的长期股权投资损失 | non_operating_expense_loss_long_term_equity_current | SAS | 2 |
| 第27行 | non_operating_expense_loss_long_term_equity_current | SAS | 3 |
| 自然灾害等不可抗力因素造成的损失 | non_operating_expense_force_majeure_current | SAS | 2 |
| 第28行 | non_operating_expense_force_majeure_current | SAS | 3 |
| 税收滞纳金 | non_operating_expense_tax_late_fee_current | SAS | 2 |
| 第29行 | non_operating_expense_tax_late_fee_current | SAS | 3 |
| 利润总额 | profit_before_tax_current | SAS | 2 |
| 第30行 | profit_before_tax_current | SAS | 3 |
| 所得税费用 | income_tax_expense_current | SAS | 2 |
| 第31行 | income_tax_expense_current | SAS | 3 |
| 净利润 | net_profit_current | SAS | 2 |
| 第32行 | net_profit_current | SAS | 3 |

### 4.4 分准则宽表视图  

为每个准则创建一个视图，将纵表数据透视成宽表，每个项目对应两列：`{item_code}_current` 和 `{item_code}_cumulative`。  

#### 4.4.1 企业会计准则视图（`vw_income_statement_cas`）  

```sql
CREATE VIEW vw_income_statement_cas AS
SELECT
    i.taxpayer_id,
    t.taxpayer_name,
    i.period_year,
    i.period_month,
    i.revision_no,
    i.submitted_at,
    i.etl_batch_id,
    i.source_doc_id,
    i.source_unit,
    i.etl_confidence,
    -- 动态生成每个项目的本期和累计列（此处以部分项目为例，完整视图需用代码生成）
    MAX(CASE WHEN i.item_code = 'OPERATING_REVENUE' THEN i.current_amount END) AS operating_revenue_current,
    MAX(CASE WHEN i.item_code = 'OPERATING_REVENUE' THEN i.cumulative_amount END) AS operating_revenue_cumulative,
    MAX(CASE WHEN i.item_code = 'OPERATING_COST' THEN i.current_amount END) AS operating_cost_current,
    MAX(CASE WHEN i.item_code = 'OPERATING_COST' THEN i.cumulative_amount END) AS operating_cost_cumulative,
    MAX(CASE WHEN i.item_code = 'TAXES_AND_SURCHARGES' THEN i.current_amount END) AS taxes_and_surcharges_current,
    MAX(CASE WHEN i.item_code = 'TAXES_AND_SURCHARGES' THEN i.cumulative_amount END) AS taxes_and_surcharges_cumulative,
    -- ... 继续列出所有企业会计准则项目
    MAX(CASE WHEN i.item_code = 'NET_PROFIT' THEN i.current_amount END) AS net_profit_current,
    MAX(CASE WHEN i.item_code = 'NET_PROFIT' THEN i.cumulative_amount END) AS net_profit_cumulative,
    MAX(CASE WHEN i.item_code = 'TOTAL_COMPREHENSIVE_INCOME' THEN i.current_amount END) AS total_comprehensive_income_current,
    MAX(CASE WHEN i.item_code = 'TOTAL_COMPREHENSIVE_INCOME' THEN i.cumulative_amount END) AS total_comprehensive_income_cumulative
FROM fs_income_statement_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
WHERE i.gaap_type = 'CAS'
GROUP BY i.taxpayer_id, i.period_year, i.period_month, i.revision_no, i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence;
```

#### 4.4.2 小企业会计准则视图（`vw_income_statement_sas`）  

```sql
CREATE VIEW vw_income_statement_sas AS
SELECT
    i.taxpayer_id,
    t.taxpayer_name,
    i.period_year,
    i.period_month,
    i.revision_no,
    i.submitted_at,
    i.etl_batch_id,
    i.source_doc_id,
    i.source_unit,
    i.etl_confidence,
    MAX(CASE WHEN i.item_code = 'OPERATING_REVENUE' THEN i.current_amount END) AS operating_revenue_current,
    MAX(CASE WHEN i.item_code = 'OPERATING_REVENUE' THEN i.cumulative_amount END) AS operating_revenue_cumulative,
    MAX(CASE WHEN i.item_code = 'OPERATING_COST' THEN i.current_amount END) AS operating_cost_current,
    MAX(CASE WHEN i.item_code = 'OPERATING_COST' THEN i.cumulative_amount END) AS operating_cost_cumulative,
    MAX(CASE WHEN i.item_code = 'TAXES_AND_SURCHARGES' THEN i.current_amount END) AS taxes_and_surcharges_current,
    MAX(CASE WHEN i.item_code = 'TAXES_AND_SURCHARGES' THEN i.cumulative_amount END) AS taxes_and_surcharges_cumulative,
    -- 税金及附加明细
    MAX(CASE WHEN i.item_code = 'CONSUMPTION_TAX' THEN i.current_amount END) AS consumption_tax_current,
    MAX(CASE WHEN i.item_code = 'CONSUMPTION_TAX' THEN i.cumulative_amount END) AS consumption_tax_cumulative,
    -- ... 其他项目
    MAX(CASE WHEN i.item_code = 'NET_PROFIT' THEN i.current_amount END) AS net_profit_current,
    MAX(CASE WHEN i.item_code = 'NET_PROFIT' THEN i.cumulative_amount END) AS net_profit_cumulative
FROM fs_income_statement_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
WHERE i.gaap_type = 'SAS'
GROUP BY i.taxpayer_id, i.period_year, i.period_month, i.revision_no, i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence;
```

> **说明**：视图列名采用 `{item_code}_current` 和 `{item_code}_cumulative`，与同义词表中的 `column_name` 一致。实际开发时，可通过读取字典表动态生成视图 DDL。

### 4.5 纳税人信息表（`taxpayer_info`）  

复用资产负债表方案中的纳税人信息表。  

```sql
CREATE TABLE taxpayer_info (
    taxpayer_id           TEXT PRIMARY KEY,
    taxpayer_name         TEXT NOT NULL,
    taxpayer_type         TEXT NOT NULL,   -- '一般纳税人'/'小规模纳税人'
    -- 其他字段（行业、信用等级等）可根据需要添加
);
```

### 4.6 用户查询日志表（`user_query_log`）与未匹配短语表（`unmatched_phrases`）  

```sql
CREATE TABLE user_query_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT,
    query_text      TEXT NOT NULL,
    domain          TEXT,                   -- 'income_statement', 'balance_sheet' 等
    interpreted_json TEXT,
    generated_sql   TEXT,
    execution_time_ms INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE unmatched_phrases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase          TEXT NOT NULL,
    context         TEXT,
    occurrence_count INTEGER DEFAULT 1,
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved        BOOLEAN DEFAULT 0
);
```

## 5. ETL 流程设计（PDF/Excel → 明细表）  

### 5.1 输入解析  
- 识别报表类型（企业会计准则/小企业会计准则）、纳税人识别号、所属期（年月）。  
- 解析表格，提取每一行的项目名称、行次（若有）、本期金额、本年累计金额。  

### 5.2 行列转换  
- 遍历每一行，提取项目名称、行次、本期金额、本年累计金额。  
- 根据项目名称和准则类型，通过字典表匹配标准 `item_code`；若无法匹配，记录错误并跳过。  
- 将数据组织为 `(taxpayer_id, period, gaap_type, item_code, current_amount, cumulative_amount)` 的形式。  

### 5.3 写入明细表  
- 使用 `INSERT OR REPLACE` 按主键批量 upsert，支持更正申报（`revision_no` 递增）。  

### 5.4 数据质量校验  
- 检查营业利润、利润总额、净利润等勾稽关系（例如：营业利润 = 营业收入 - 营业成本 - 税金及附加 - 销售费用 - 管理费用 - 研发费用 - 财务费用 + 其他收益 + 投资收益 + ...）。允许少量误差。  
- 若从 PDF 解析，记录置信度字段。  

## 6. NL2SQL 应用流程（适配利润表）  

### 6.1 实体识别与同义词标准化  
1. 从用户问题中提取纳税人、期次、准则类型（通过关键词如“小企业”“一般企业”或默认为企业会计准则）。  
2. 根据准则类型选择对应的视图（`vw_income_statement_cas` 或 `vw_income_statement_sas`）。  
3. 使用同义词表进行“最长匹配优先 + 不重叠替换”，将用户口语映射到视图列名（如 `operating_revenue_current`）。  

### 6.2 大模型 Prompt 设计（两阶段受控生成）  
- **阶段1（意图解析）**：输出 JSON，包含 `domain='income_statement'`、`gaap_type`、需查询的列（metrics/dimensions）、过滤条件（纳税人、期次）、是否需要澄清。  
- **约束注入器**：根据阶段1 JSON 注入允许的视图和列白名单。  
- **阶段2（SQL 生成）**：在动态 schema 白名单约束下生成 SQLite SQL。  

### 6.3 SQL 审核器规则  
- 只允许 SELECT 查询，禁止修改语句。  
- 必须包含 `taxpayer_id = :taxpayer_id` 和期间过滤（`period_year = :year AND period_month = :month` 或范围）。  
- 禁止 `SELECT *`，列必须在白名单内。  
- 明细查询必须带 `LIMIT`（默认 1000）。  
- 若请求跨准则对比，需通过 UNION 对齐输出（如两个视图分别查询后合并）。  

### 6.4 执行与反馈  
- 执行 SQL 并返回结果，记录日志和未匹配短语。  

## 7. 方案优势总结  

| 维度 | 本方案优势 |  
|------|------------|  
| **扩展性** | 底层纵表 + 字典表，支持任意新增准则，无需修改表结构。 |  
| **NL2SQL 准确率** | 分准则宽表视图 + 同义词映射，模型无需理解纵表复杂逻辑。 |  
| **查询性能** | 视图基于纵表实时聚合，但数据量小（每户每月几十行），性能可接受；可进一步物化视图加速。 |  
| **ETL 维护** | 通过字典表映射，解析逻辑清晰，易于适配新报表格式。 |  
| **合规性** | 审核器确保数据安全，只读且限定企业范围。 |  

## 8. 后续扩展建议  

- 增加现金流量表、所有者权益变动表等财务报表，采用相同建模思路。  
- 构建统一的企业画像维度表，增强跨表分析能力。  
- 实现自动化的未匹配短语闭环处理，持续丰富同义词库。  

---  

**附录**：项目字典表完整数据、同义词表示例（已插入文档）。