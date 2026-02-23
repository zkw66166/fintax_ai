# 利润表 NL2SQL 数据模型修改方案文档  
**版本**：**v1.1** | **最后更新**：2026-02-17  

## 1. 背景与目标  

1. **利润表数据库设计不符合业务需求**：数据库中利润表设计不符合业务需求，因为现有设计是将企业会计准则和小企业会计准则合并为一个宽表，难以支持后续利润表项目可能经常变动，以及增加更多会计准则和会计制度的利润表的业务需求。
2. **目标**：只修改利润表相关的表和索引等的设计，但保持利润表相关视图结构不变，从而实现原脚本中对视图的引用不用修改。

## 2. 基本要求  

 **多准则异构性**  两套报表项目名称、行次、数量不一致，未来可能新增其他准则，需统一建模。
 **时期指标** 利润表存储本期发生额和本年累计额，而非时点余额，需在纵表中区分指标类型。 
 **明细项目与合计项并存** 报表包含大量明细项（如利息费用）和汇总项（如营业利润），需保留原始行次和层次关系。
 **NL2SQL 歧义** 用户口语化表达（如“营业收入”“第5行”“净利润”）需精准映射到具体准则下的具体项目。
 **扩展性** 未来新增准则需在不破坏已有模型的前提下无缝接入。 

## 3. 设计原则  

1. **存储与查询解耦**：底层采用**纵表（EAV）**存储所有准则的明细项目，保证扩展性；查询侧为每个准则构建**宽表视图**，消除 NL2SQL 的复杂性。  
2. **字段名即业务术语**：视图中的列名保持原视图原样（向后兼容）。  
3. **同义词集中管理**：用单独映射表存储用户口语→标准字段的映射，支持按准则类型过滤（从原属于synonyms迁移数据）。  
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

### 4.2.1 企业会计准则（cas）字典数据
```sql
INSERT INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES
('cas', 'operating_revenue', '营业收入', 1, 'operating', 10, 0),
('cas', 'operating_cost', '减：营业成本', 2, 'operating', 20, 0),
('cas', 'taxes_and_surcharges', '税金及附加', 3, 'operating', 30, 0),
('cas', 'selling_expense', '销售费用', 4, 'operating', 40, 0),
('cas', 'administrative_expense', '管理费用', 5, 'operating', 50, 0),
('cas', 'rd_expense', '研发费用', 6, 'operating', 60, 0),
('cas', 'financial_expense', '财务费用', 7, 'operating', 70, 0),
('cas', 'interest_expense', '其中：利息费用', 8, 'operating', 80, 0),
('cas', 'interest_income', '利息收入', 9, 'operating', 90, 0),
('cas', 'other_gains', '其他收益', 10, 'operating', 100, 0),
('cas', 'investment_income', '投资收益（损失以“－”号填列）', 11, 'operating', 110, 0),
('cas', 'investment_income_associates', '其中：对联营企业和合营企业的投资收益', 12, 'operating', 120, 0),
('cas', 'amortized_cost_termination_income', '以摊余成本计量的金融资产终止确认收益', 13, 'operating', 130, 0),
('cas', 'net_exposure_hedge_income', '净敞口套期收益', 14, 'operating', 140, 0),
('cas', 'fair_value_change_income', '公允价值变动收益', 15, 'operating', 150, 0),
('cas', 'credit_impairment_loss', '信用减值损失', 16, 'operating', 160, 0),
('cas', 'asset_impairment_loss', '资产减值损失', 17, 'operating', 170, 0),
('cas', 'asset_disposal_gains', '资产处置收益', 18, 'operating', 180, 0),
('cas', 'operating_profit', '营业利润（亏损以“－”号填列）', 19, 'operating', 190, 1),
('cas', 'non_operating_income', '营业外收入', 20, 'non_operating', 200, 0),
('cas', 'non_operating_expense', '营业外支出', 21, 'non_operating', 210, 0),
('cas', 'total_profit', '利润总额（亏损总额以“－”号填列）', 22, 'profit', 220, 1),
('cas', 'income_tax_expense', '所得税费用', 23, 'profit', 230, 0),
('cas', 'net_profit', '净利润（净亏损以“－”号填列）', 24, 'profit', 240, 1),
('cas', 'continued_ops_net_profit', '（一）持续经营净利润', 25, 'profit', 250, 0),
('cas', 'discontinued_ops_net_profit', '（二）终止经营净利润', 26, 'profit', 260, 0),
('cas', 'other_comprehensive_income_net', '五、其他综合收益的税后净额', 27, 'comprehensive', 270, 1),
('cas', 'oci_non_reclass', '（一）不能重分类进损益的其他综合收益', 28, 'comprehensive', 280, 1),
('cas', 'oci_remeasurement_defined_benefit', '1.重新计量设定受益计划变动额', 29, 'comprehensive', 290, 0),
('cas', 'oci_eq_method_non_reclass', '2.权益法下不能转损益的其他综合收益', 30, 'comprehensive', 300, 0),
('cas', 'oci_fair_value_change_other_equity', '3.其他权益工具投资公允价值变动', 31, 'comprehensive', 310, 0),
('cas', 'oci_credit_risk_change', '4.企业自身信用风险公允价值变动', 32, 'comprehensive', 320, 0),
('cas', 'oci_reclass', '（二）将重分类进损益的其他综合收益', 33, 'comprehensive', 330, 1),
('cas', 'oci_eq_method_reclass', '1.权益法下可转损益的其他综合收益', 34, 'comprehensive', 340, 0),
('cas', 'oci_fair_value_change_other_debt', '2.其他债权投资公允价值变动', 35, 'comprehensive', 350, 0),
('cas', 'oci_reclassification_adjustment', '3.金融资产重分类计入其他综合收益的金额', 36, 'comprehensive', 360, 0),
('cas', 'oci_credit_impairment_other_debt', '4.其他债权投资信用减值准备', 37, 'comprehensive', 370, 0),
('cas', 'oci_cash_flow_hedge_reserve', '5.现金流量套期储备', 38, 'comprehensive', 380, 0),
('cas', 'oci_foreign_currency_translation', '6.外币财务报表折算差额', 39, 'comprehensive', 390, 0),
('cas', 'comprehensive_income_total', '六、综合收益总额', 40, 'comprehensive', 400, 1),
('cas', 'eps_basic', '(一) 基本每股收益', 42, 'eps', 410, 0),
('cas', 'eps_diluted', '(二) 稀释每股收益', 43, 'eps', 420, 0);
```

#### 4.2.2 小企业会计准则（sas）字典数据
```sql
INSERT INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES
('sas', 'operating_revenue', '一、营业收入', 1, 'operating', 10, 0),
('sas', 'operating_cost', '减：营业成本', 2, 'operating', 20, 0),
('sas', 'taxes_and_surcharges', '税金及附加', 3, 'operating', 30, 0),
('sas', 'consumption_tax', '其中：消费税', 4, 'operating', 40, 0),
('sas', 'business_tax', '营业税', 5, 'operating', 50, 0),
('sas', 'city_maintenance_tax', '城市维护建设税', 6, 'operating', 60, 0),
('sas', 'resource_tax', '资源税', 7, 'operating', 70, 0),
('sas', 'land_appreciation_tax', '土地增值税', 8, 'operating', 80, 0),
('sas', 'property_and_other_taxes', '城镇土地使用税、房产税、车船税、印花税', 9, 'operating', 90, 0),
('sas', 'education_surcharge_and_other', '教育费附加、矿产资源补偿费、排污费', 10, 'operating', 100, 0),
('sas', 'selling_expense', '销售费用', 11, 'operating', 110, 0),
('sas', 'selling_expense_repair', '其中：商品维修费', 12, 'operating', 120, 0),
('sas', 'selling_expense_advertising', '广告费和业务宣传费', 13, 'operating', 130, 0),
('sas', 'administrative_expense', '管理费用', 14, 'operating', 140, 0),
('sas', 'administrative_expense_organization', '其中：开办费', 15, 'operating', 150, 0),
('sas', 'administrative_expense_entertainment', '业务招待费', 16, 'operating', 160, 0),
('sas', 'administrative_expense_research', '研究费用', 17, 'operating', 170, 0),
('sas', 'financial_expense', '财务费用', 18, 'operating', 180, 0),
('sas', 'interest_expense', '其中：利息费用（收入以“-”号填列）', 19, 'operating', 190, 0),
('sas', 'investment_income', '加：投资收益（亏损以“-”号填列）', 20, 'operating', 200, 0),
('sas', 'operating_profit', '二、营业利润（亏损以“-”号填列）', 21, 'operating', 210, 1),
('sas', 'non_operating_income', '加：营业外收入', 22, 'non_operating', 220, 0),
('sas', 'non_operating_income_gov_grant', '其中：政府补助', 23, 'non_operating', 230, 0),
('sas', 'non_operating_expense', '减：营业外支出', 24, 'non_operating', 240, 0),
('sas', 'non_operating_expense_bad_debt', '其中：坏账损失', 25, 'non_operating', 250, 0),
('sas', 'non_operating_expense_loss_long_term_bond', '无法收回的长期债券投资损失', 26, 'non_operating', 260, 0),
('sas', 'non_operating_expense_loss_long_term_equity', '无法收回的长期股权投资损失', 27, 'non_operating', 270, 0),
('sas', 'non_operating_expense_force_majeure', '自然灾害等不可抗力因素造成的损失', 28, 'non_operating', 280, 0),
('sas', 'non_operating_expense_tax_late_fee', '税收滞纳金', 29, 'non_operating', 290, 0),
('sas', 'total_profit', '三、利润总额（亏损总额以“-”号填列）', 30, 'profit', 300, 1),
('sas', 'income_tax_expense', '减：所得税费用', 31, 'profit', 310, 0),
('sas', 'net_profit', '四、净利润（净亏损以“-”号填列）', 32, 'profit', 320, 1);
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

执行sql插入（以下为示例，完整的同义词见附件）：
```
-- 企业会计准则（cas）同义词插入语句
INSERT INTO fs_income_statement_synonyms (phrase, column_name, gaap_type, priority) VALUES
-- 营业收入
('营业收入', 'operating_revenue_current', 'cas', 2),
('营业收入本期', 'operating_revenue_current', 'cas', 2),
('营业收入累计', 'operating_revenue_cumulative', 'cas', 2),
('营收', 'operating_revenue_current', 'cas', 2),
('经营收入', 'operating_revenue_current', 'cas', 2),
('主营收入', 'operating_revenue_current', 'cas', 2),
('第1行', 'operating_revenue_current', 'cas', 3),
('1行', 'operating_revenue_current', 'cas', 3),
('第一行', 'operating_revenue_current', 'cas', 3),
```

#### 4.4 数据迁移

1. **迁移示例数据**：将原fs_profit_statement_detail中的数据导入到fs_income_statement_item

2. **新建索引**： 基于更新后的表重建索引，删除原利润表相关索引。

### 4.5 分准则宽表视图  

为每个准则创建一个视图，将纵表数据透视成宽表，每个项目对应两列：`{item_code}_current` 和 `{item_code}_cumulative`。  

#### 4.5.1 企业会计准则视图（`vw_profit_eas`）  

备份原vw_profit_eas，基于更新的利润表生成新的vw_profit_eas，确保与原vw_profit_eas一样的结构和字段名，从而实现原脚本中对视图的引用不变。

#### 4.5.2 小企业会计准则视图（`vw_profit_sas`）  

备份原vw_profit_sas，基于更新的利润表生成新的vw_profit_sas，确保与原vw_profit_sas一样的结构和字段名，从而实现原脚本中对视图的引用不变。


### 4.7 更新financial_matrics计算脚本

备份原financial_matrics，更新financial_matrics计算脚本。
验证新脚本计算结果后删除原financial_matrics备份。

### 4.6 其他事项

**检查并更新整个项目**：检查利润表更新是否涉及到整个项目的其他各个方面，更新各个需要修改的地方并验证。


### 4.7 附录

**完整的同义词**：完整的同义词insert SQL
