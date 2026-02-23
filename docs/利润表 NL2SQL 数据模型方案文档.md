# 利润表 NL2SQL 数据模型方案文档（参照增值税方案设计）  
**版本**：v1.0 | **最后更新**：2026-02-14  

## 1. 项目背景与目标

利润表是企业财务三大报表之一，存在**企业会计准则**与**小企业会计准则**两套主流格式，每套格式包含数十个行次项目，且每个项目均有“本期金额”和“本年累计金额”两列数据。未来可能扩展其他准则（如个体工商户、农民专业合作社等）。  
目标：构建一套**面向 NL2SQL 的事后分析数据模型**，支持：

- 用户通过自然语言查询任意纳税人、任意期次的利润表明细数据；
- 支持跨准则（企业/小企业）的指标对比；
- ETL 能够从 Excel/PDF 等异构来源稳定导入；
- 存储紧凑、查询高效，大模型 SQL 生成准确率 ≥95%。

---

## 2. 核心挑战

| 挑战 | 描述 |
|------|------|
| **异构性** | 两套利润表的行次、项目名称、项目数量均不同，无法直接合并为同一张物理宽表而不引入大量空值 |
| **扩展性** | 未来可能新增其他会计准则或制度，要求模型能低成本扩展 |
| **NL2SQL 歧义** | 用户口语化表达（如“营业收入”“第5行”“主营业务收入”）需精准映射到物理字段 |
| **口径对齐** | 跨准则对比时，需明确“税金及附加”在企业准则中是总额，在小企业准则下可能拆分为多个明细项 |
| **时间维度** | 每张表包含“本期”和“本年累计”两个时间口径，查询时需明确区分 |

---

## 3. 设计原则

1. **存储与查询解耦**：明细表统一存储所有准则数据，通过 `accounting_standard` 字段区分；查询侧按准则创建独立视图，NL2SQL 永不直接接触明细表。  
2. **字段名即业务术语**：物理字段采用完整业务英文名（如 `operating_revenue`），大模型零学习成本。  
3. **同义词集中管理**：用映射表存储用户口语→标准字段的映射，支持前置替换，并支持按准则过滤。  
4. **维度行拍平**：将“本期/累计”两列拆分为 `time_range` 维度，每纳税人每期每准则仅 2 行数据，消除列方向稀疏性。  
5. **一次设计，无限扩展**：新增准则只需在明细表增加新列（如有全新项目）或复用已有列，并创建对应视图与映射，不破坏已有查询。  

---

## 4. 数据模型详细设计

### 4.1 利润表明细表（`fs_profit_statement_detail`）

```sql
-- 统一利润表明细表（存储企业会计准则、小企业会计准则及未来扩展准则）
CREATE TABLE fs_profit_statement_detail (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    accounting_standard TEXT NOT NULL,   -- 'ASBE'=企业会计准则, 'SAS'=小企业会计准则, 后续可扩展
    time_range          TEXT NOT NULL,   -- '本期', '本年累计'

    -- 追溯/版本
    revision_no         INTEGER NOT NULL DEFAULT 0,
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    source_unit         TEXT DEFAULT '元',
    etl_confidence      REAL,

    -- ========== 利润表项目（以企业会计准则为基础，补充小企业特有项目）==========
    -- 第一部分：收入与成本
    operating_revenue                     NUMERIC,  -- 营业收入
    operating_cost                         NUMERIC,  -- 营业成本
    taxes_and_surcharges                    NUMERIC,  -- 税金及附加
    selling_expense                         NUMERIC,  -- 销售费用
    administrative_expense                  NUMERIC,  -- 管理费用
    rd_expense                              NUMERIC,  -- 研发费用
    financial_expense                       NUMERIC,  -- 财务费用
    interest_expense                        NUMERIC,  -- 其中：利息费用
    interest_income                         NUMERIC,  -- 其中：利息收入

    -- 第二部分：各项收益/损失
    other_gains                             NUMERIC,  -- 其他收益
    investment_income                       NUMERIC,  -- 投资收益
    investment_income_associates             NUMERIC,  -- 其中：对联营/合营企业投资收益
    amortized_cost_termination_income        NUMERIC,  -- 以摊余成本计量的金融资产终止确认收益
    net_exposure_hedge_income                NUMERIC,  -- 净敞口套期收益
    fair_value_change_income                 NUMERIC,  -- 公允价值变动收益
    credit_impairment_loss                   NUMERIC,  -- 信用减值损失
    asset_impairment_loss                    NUMERIC,  -- 资产减值损失
    asset_disposal_gains                     NUMERIC,  -- 资产处置收益

    -- 第三部分：营业利润及额外项目
    operating_profit                        NUMERIC,  -- 营业利润
    non_operating_income                    NUMERIC,  -- 营业外收入
    non_operating_expense                   NUMERIC,  -- 营业外支出
    total_profit                            NUMERIC,  -- 利润总额
    income_tax_expense                       NUMERIC,  -- 所得税费用
    net_profit                              NUMERIC,  -- 净利润
    continued_ops_net_profit                 NUMERIC,  -- 持续经营净利润
    discontinued_ops_net_profit              NUMERIC,  -- 终止经营净利润

    -- 第四部分：其他综合收益
    other_comprehensive_income_net           NUMERIC,  -- 其他综合收益的税后净额
    oci_not_reclassifiable                   NUMERIC,  -- 不能重分类进损益
    oci_reclassifiable                       NUMERIC,  -- 将重分类进损益
    -- 其他综合收益明细项（可选，可按需增加）
    oci_remeasurement_pension                NUMERIC,  -- 重新计量设定受益计划变动额
    oci_equity_method_nonreclassifiable      NUMERIC,  -- 权益法下不能转损益
    oci_equity_investment_fv_change          NUMERIC,  -- 其他权益工具投资公允价值变动
    oci_credit_risk_change                   NUMERIC,  -- 企业自身信用风险公允价值变动
    oci_equity_method_reclassifiable         NUMERIC,  -- 权益法下可转损益
    oci_debt_investment_fv_change            NUMERIC,  -- 其他债权投资公允价值变动
    oci_reclassify_to_pnl                     NUMERIC,  -- 金融资产重分类计入其他综合收益
    oci_debt_impairment                       NUMERIC,  -- 其他债权投资信用减值准备
    oci_cash_flow_hedge                       NUMERIC,  -- 现金流量套期储备
    oci_foreign_currency_translation         NUMERIC,  -- 外币财务报表折算差额

    comprehensive_income_total                NUMERIC,  -- 综合收益总额

    -- 第五部分：每股收益
    eps_basic                                NUMERIC,  -- 基本每股收益
    eps_diluted                              NUMERIC,  -- 稀释每股收益

    -- ====== 小企业会计准则特有明细（企业会计准则下为空）======
    -- 税金及附加明细
    consumption_tax                          NUMERIC,  -- 消费税
    business_tax                              NUMERIC,  -- 营业税
    city_maintenance_tax                      NUMERIC,  -- 城市维护建设税
    resource_tax                              NUMERIC,  -- 资源税
    land_appreciation_tax                     NUMERIC,  -- 土地增值税
    property_related_taxes                    NUMERIC,  -- 城镇土地使用税、房产税、车船税、印花税
    education_surcharge                       NUMERIC,  -- 教育费附加
    mineral_compensation                      NUMERIC,  -- 矿产资源补偿费
    sewage_charge                             NUMERIC,  -- 排污费

    -- 销售费用明细
    goods_repair_expense                      NUMERIC,  -- 商品维修费
    advertising_expense                       NUMERIC,  -- 广告费和业务宣传费

    -- 管理费用明细
    organization_expense                      NUMERIC,  -- 开办费
    business_entertainment_expense            NUMERIC,  -- 业务招待费
    research_expense                          NUMERIC,  -- 研究费用

    -- 财务费用明细
    interest_expense_net                      NUMERIC,  -- 利息费用（收入以“-”填列）

    -- 营业外收入明细
    government_grant                          NUMERIC,  -- 政府补助

    -- 营业外支出明细
    bad_debt_loss                             NUMERIC,  -- 坏账损失
    long_term_bond_loss                       NUMERIC,  -- 无法收回的长期债券投资损失
    long_term_equity_loss                     NUMERIC,  -- 无法收回的长期股权投资损失
    force_majeure_loss                        NUMERIC,  -- 自然灾害等不可抗力造成的损失
    tax_late_payment                          NUMERIC,  -- 税收滞纳金

    -- 主键与约束
    PRIMARY KEY (taxpayer_id, period_year, period_month, accounting_standard, time_range, revision_no),
    CHECK (accounting_standard IN ('ASBE', 'SAS')),
    CHECK (time_range IN ('本期', '本年累计')),
    CHECK (revision_no >= 0)
);

-- 常用索引
CREATE INDEX idx_profit_period ON fs_profit_statement_detail (period_year, period_month);
CREATE INDEX idx_profit_taxpayer ON fs_profit_statement_detail (taxpayer_id);
CREATE INDEX idx_profit_taxpayer_period ON fs_profit_statement_detail (taxpayer_id, period_year, period_month);
CREATE INDEX idx_profit_standard ON fs_profit_statement_detail (accounting_standard);
```

**设计说明**：
- 采用宽表模式，将两套利润表的所有可能项目均设计为独立列。企业会计准则数据填充对应列，小企业会计准则特有列留空（反之亦然）。这种稀疏性在合理范围内（约80列），可接受。
- `accounting_standard` 字段区分准则，便于视图过滤。
- `time_range` 区分“本期”和“本年累计”，每准则每期产生2行数据，消除原表中的列方向冗余。

---

### 4.2 栏次-字段映射表（ETL 专用）

#### 企业会计准则映射表（`fs_profit_eas_line_mapping`）
```sql
CREATE TABLE IF NOT EXISTS fs_profit_eas_line_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

-- 插入企业会计准则43条映射记录（示例，完整列表参照Excel）
INSERT OR REPLACE INTO fs_profit_eas_line_mapping (line_number, column_name, business_name) VALUES
(1,  'operating_revenue', '营业收入'),
(2,  'operating_cost', '营业成本'),
(3,  'taxes_and_surcharges', '税金及附加'),
(4,  'selling_expense', '销售费用'),
(5,  'administrative_expense', '管理费用'),
(6,  'rd_expense', '研发费用'),
(7,  'financial_expense', '财务费用'),
(8,  'interest_expense', '其中：利息费用'),
(9,  'interest_income', '利息收入'),
(10, 'other_gains', '其他收益'),
(11, 'investment_income', '投资收益'),
(12, 'investment_income_associates', '其中：对联营企业和合营企业的投资收益'),
(13, 'amortized_cost_termination_income', '以摊余成本计量的金融资产终止确认收益'),
(14, 'net_exposure_hedge_income', '净敞口套期收益'),
(15, 'fair_value_change_income', '公允价值变动收益'),
(16, 'credit_impairment_loss', '信用减值损失'),
(17, 'asset_impairment_loss', '资产减值损失'),
(18, 'asset_disposal_gains', '资产处置收益'),
(19, 'operating_profit', '营业利润'),
(20, 'non_operating_income', '营业外收入'),
(21, 'non_operating_expense', '营业外支出'),
(22, 'total_profit', '利润总额'),
(23, 'income_tax_expense', '所得税费用'),
(24, 'net_profit', '净利润'),
(25, 'continued_ops_net_profit', '持续经营净利润'),
(26, 'discontinued_ops_net_profit', '终止经营净利润'),
(27, 'other_comprehensive_income_net', '其他综合收益的税后净额'),
(28, 'oci_not_reclassifiable', '不能重分类进损益的其他综合收益'),
(29, 'oci_remeasurement_pension', '重新计量设定受益计划变动额'),
(30, 'oci_equity_method_nonreclassifiable', '权益法下不能转损益的其他综合收益'),
(31, 'oci_equity_investment_fv_change', '其他权益工具投资公允价值变动'),
(32, 'oci_credit_risk_change', '企业自身信用风险公允价值变动'),
(33, 'oci_reclassifiable', '将重分类进损益的其他综合收益'),
(34, 'oci_equity_method_reclassifiable', '权益法下可转损益的其他综合收益'),
(35, 'oci_debt_investment_fv_change', '其他债权投资公允价值变动'),
(36, 'oci_reclassify_to_pnl', '金融资产重分类计入其他综合收益的金额'),
(37, 'oci_debt_impairment', '其他债权投资信用减值准备'),
(38, 'oci_cash_flow_hedge', '现金流量套期储备'),
(39, 'oci_foreign_currency_translation', '外币财务报表折算差额'),
(40, 'comprehensive_income_total', '综合收益总额'),
(41, 'eps_basic', '基本每股收益'),
(42, 'eps_diluted', '稀释每股收益'),
(43, 'eps_basic', '七、每股收益：');  -- 注意：行次41是标题，42/43为具体值，此处映射到eps_basic/eps_diluted，可根据实际调整
-- 注：行次41为“七、每股收益：”无数值，故可不映射，或映射为NULL
```

#### 小企业会计准则映射表（`profit_sas_line_mapping`）
```sql
CREATE TABLE IF NOT EXISTS profit_sas_line_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

-- 插入小企业会计准则32条映射记录（示例，完整列表参照Excel）
INSERT OR REPLACE INTO profit_sas_line_mapping (line_number, column_name, business_name) VALUES
(1,  'operating_revenue', '营业收入'),
(2,  'operating_cost', '营业成本'),
(3,  'taxes_and_surcharges', '税金及附加'),
(4,  'consumption_tax', '消费税'),
(5,  'business_tax', '营业税'),
(6,  'city_maintenance_tax', '城市维护建设税'),
(7,  'resource_tax', '资源税'),
(8,  'land_appreciation_tax', '土地增值税'),
(9,  'property_related_taxes', '城镇土地使用税、房产税、车船税、印花税'),
(10, 'education_surcharge', '教育费附加、矿产资源补偿费、排污费'),
(11, 'selling_expense', '销售费用'),
(12, 'goods_repair_expense', '其中：商品维修费'),
(13, 'advertising_expense', '广告费和业务宣传费'),
(14, 'administrative_expense', '管理费用'),
(15, 'organization_expense', '其中：开办费'),
(16, 'business_entertainment_expense', '业务招待费'),
(17, 'research_expense', '研究费用'),
(18, 'financial_expense', '财务费用'),
(19, 'interest_expense_net', '其中：利息费用（收入以“-”号填列）'),
(20, 'investment_income', '加：投资收益（亏损以“-”号填列）'),
(21, 'operating_profit', '二、营业利润'),
(22, 'non_operating_income', '加：营业外收入'),
(23, 'government_grant', '其中：政府补助'),
(24, 'non_operating_expense', '减：营业外支出'),
(25, 'bad_debt_loss', '其中：坏账损失'),
(26, 'long_term_bond_loss', '无法收回的长期债券投资损失'),
(27, 'long_term_equity_loss', '无法收回的长期股权投资损失'),
(28, 'force_majeure_loss', '自然灾害等不可抗力因素造成的损失'),
(29, 'tax_late_payment', '税收滞纳金'),
(30, 'total_profit', '三、利润总额'),
(31, 'income_tax_expense', '减：所得税费用'),
(32, 'net_profit', '四、净利润');
```

**作用**：ETL 解析 Excel 时，根据行次号直接获取目标字段名，完成行列转换。

---

### 4.3 同义词映射表（NL2SQL 专用）

复用增值税的同义词表结构，增加 `scope_view` 和 `accounting_standard` 字段（可用 `taxpayer_type` 类比，但这里用 `accounting_standard`）。为简化，可扩展 `vat_synonyms` 表或新建 `fs_profit_synonyms` 表。此处新建专用表。

```sql
CREATE TABLE IF NOT EXISTS fs_profit_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,
    column_name TEXT NOT NULL,
    priority    INTEGER DEFAULT 1,
    accounting_standard TEXT,   -- 'ASBE'/'SAS'/NULL(通用)
    scope_view  TEXT,            -- 'vw_profit_eas'/'vw_profit_sas'/NULL(通用)
    UNIQUE(phrase, column_name)
);
CREATE INDEX idx_fs_profit_synonyms_phrase ON fs_profit_synonyms(phrase);
CREATE INDEX idx_fs_profit_synonyms_scope ON fs_profit_synonyms(scope_view, accounting_standard, priority);
```

**同义词数据**（完整版）：
```sql
-- ============================================
-- 利润表同义词数据（完整版）
-- ============================================

-- 1. 营业收入 operating_revenue
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第1行', 'operating_revenue', 3),
    ('1行', 'operating_revenue', 3),
    ('行次1', 'operating_revenue', 3),
    ('营业收入', 'operating_revenue', 2),
    ('收入', 'operating_revenue', 1),
    ('主营业务收入', 'operating_revenue', 1),
    ('销售收入', 'operating_revenue', 1),
    ('营业额', 'operating_revenue', 1);

-- 2. 营业成本 operating_cost
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第2行', 'operating_cost', 3),
    ('2行', 'operating_cost', 3),
    ('行次2', 'operating_cost', 3),
    ('营业成本', 'operating_cost', 2),
    ('成本', 'operating_cost', 1),
    ('主营业务成本', 'operating_cost', 1),
    ('销售成本', 'operating_cost', 1);

-- 3. 税金及附加 taxes_and_surcharges
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第3行', 'taxes_and_surcharges', 3),
    ('3行', 'taxes_and_surcharges', 3),
    ('行次3', 'taxes_and_surcharges', 3),
    ('税金及附加', 'taxes_and_surcharges', 2),
    ('税金', 'taxes_and_surcharges', 1),
    ('附加税', 'taxes_and_surcharges', 1),
    ('营业税金及附加', 'taxes_and_surcharges', 1);  -- 旧称

-- 4. 销售费用 selling_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第4行', 'selling_expense', 3),
    ('4行', 'selling_expense', 3),
    ('行次4', 'selling_expense', 3),
    ('销售费用', 'selling_expense', 2),
    ('销售费', 'selling_expense', 1),
    ('营业费用', 'selling_expense', 1);  -- 旧称

-- 5. 管理费用 administrative_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第5行', 'administrative_expense', 3),
    ('5行', 'administrative_expense', 3),
    ('行次5', 'administrative_expense', 3),
    ('管理费用', 'administrative_expense', 2),
    ('管理费', 'administrative_expense', 1),
    ('行政费用', 'administrative_expense', 1);

-- 6. 研发费用 rd_expense（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第6行', 'rd_expense', 3),
    ('6行', 'rd_expense', 3),
    ('行次6', 'rd_expense', 3),
    ('研发费用', 'rd_expense', 2),
    ('研发费', 'rd_expense', 1),
    ('研究开发费用', 'rd_expense', 1),
    ('技术研发费', 'rd_expense', 1);

-- 7. 财务费用 financial_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第7行', 'financial_expense', 3),
    ('7行', 'financial_expense', 3),
    ('行次7', 'financial_expense', 3),
    ('财务费用', 'financial_expense', 2),
    ('财务费', 'financial_expense', 1),
    ('融资费用', 'financial_expense', 1);

-- 8. 利息费用 interest_expense（企业会计准则）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第8行', 'interest_expense', 3),
    ('8行', 'interest_expense', 3),
    ('行次8', 'interest_expense', 3),
    ('其中：利息费用', 'interest_expense', 2),
    ('利息费用', 'interest_expense', 2),  -- 去除“其中：”
    ('利息支出', 'interest_expense', 1),
    ('借款利息', 'interest_expense', 1);

-- 9. 利息收入 interest_income（企业会计准则）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第9行', 'interest_income', 3),
    ('9行', 'interest_income', 3),
    ('行次9', 'interest_income', 3),
    ('利息收入', 'interest_income', 2),
    ('利息收益', 'interest_income', 1),
    ('存款利息', 'interest_income', 1);

-- 10. 其他收益 other_gains（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第10行', 'other_gains', 3),
    ('10行', 'other_gains', 3),
    ('行次10', 'other_gains', 3),
    ('其他收益', 'other_gains', 2),
    ('其他利得', 'other_gains', 1),
    ('政府补助', 'other_gains', 1);  -- 部分政府补助在此列

-- 11. 投资收益 investment_income
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第11行', 'investment_income', 3),
    ('11行', 'investment_income', 3),
    ('行次11', 'investment_income', 3),
    ('投资收益', 'investment_income', 2),
    ('投资利得', 'investment_income', 1),
    ('投资净收益', 'investment_income', 1);

-- 12. 对联营企业和合营企业的投资收益 investment_income_associates（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第12行', 'investment_income_associates', 3),
    ('12行', 'investment_income_associates', 3),
    ('行次12', 'investment_income_associates', 3),
    ('其中：对联营企业和合营企业的投资收益', 'investment_income_associates', 2),
    ('对联营合营投资收益', 'investment_income_associates', 1),
    ('权益法投资收益', 'investment_income_associates', 1);

-- 13. 以摊余成本计量的金融资产终止确认收益 amortized_cost_termination_income（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第13行', 'amortized_cost_termination_income', 3),
    ('13行', 'amortized_cost_termination_income', 3),
    ('行次13', 'amortized_cost_termination_income', 3),
    ('以摊余成本计量的金融资产终止确认收益', 'amortized_cost_termination_income', 2),
    ('摊余成本终止确认收益', 'amortized_cost_termination_income', 1);

-- 14. 净敞口套期收益 net_exposure_hedge_income（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第14行', 'net_exposure_hedge_income', 3),
    ('14行', 'net_exposure_hedge_income', 3),
    ('行次14', 'net_exposure_hedge_income', 3),
    ('净敞口套期收益', 'net_exposure_hedge_income', 2),
    ('套期收益', 'net_exposure_hedge_income', 1);

-- 15. 公允价值变动收益 fair_value_change_income（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第15行', 'fair_value_change_income', 3),
    ('15行', 'fair_value_change_income', 3),
    ('行次15', 'fair_value_change_income', 3),
    ('公允价值变动收益', 'fair_value_change_income', 2),
    ('公允价变动收益', 'fair_value_change_income', 1),
    ('公允价值变动损益', 'fair_value_change_income', 1);

-- 16. 信用减值损失 credit_impairment_loss（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第16行', 'credit_impairment_loss', 3),
    ('16行', 'credit_impairment_loss', 3),
    ('行次16', 'credit_impairment_loss', 3),
    ('信用减值损失', 'credit_impairment_loss', 2),
    ('信用减值', 'credit_impairment_loss', 1),
    ('坏账损失', 'credit_impairment_loss', 1);  -- 近似

-- 17. 资产减值损失 asset_impairment_loss（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第17行', 'asset_impairment_loss', 3),
    ('17行', 'asset_impairment_loss', 3),
    ('行次17', 'asset_impairment_loss', 3),
    ('资产减值损失', 'asset_impairment_loss', 2),
    ('资产减值', 'asset_impairment_loss', 1);

-- 18. 资产处置收益 asset_disposal_gains（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第18行', 'asset_disposal_gains', 3),
    ('18行', 'asset_disposal_gains', 3),
    ('行次18', 'asset_disposal_gains', 3),
    ('资产处置收益', 'asset_disposal_gains', 2),
    ('资产处置利得', 'asset_disposal_gains', 1),
    ('处置固定资产收益', 'asset_disposal_gains', 1);

-- 19. 营业利润 operating_profit
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第19行', 'operating_profit', 3),
    ('19行', 'operating_profit', 3),
    ('行次19', 'operating_profit', 3),
    ('营业利润', 'operating_profit', 2),
    ('经营利润', 'operating_profit', 1);

-- 20. 营业外收入 non_operating_income
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第20行', 'non_operating_income', 3),
    ('20行', 'non_operating_income', 3),
    ('行次20', 'non_operating_income', 3),
    ('营业外收入', 'non_operating_income', 2),
    ('营业外利得', 'non_operating_income', 1),
    ('非经常性收入', 'non_operating_income', 1);

-- 21. 营业外支出 non_operating_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第21行', 'non_operating_expense', 3),
    ('21行', 'non_operating_expense', 3),
    ('行次21', 'non_operating_expense', 3),
    ('营业外支出', 'non_operating_expense', 2),
    ('营业外损失', 'non_operating_expense', 1),
    ('非经常性支出', 'non_operating_expense', 1);

-- 22. 利润总额 total_profit
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第22行', 'total_profit', 3),
    ('22行', 'total_profit', 3),
    ('行次22', 'total_profit', 3),
    ('利润总额', 'total_profit', 2),
    ('税前利润', 'total_profit', 1),
    ('会计利润', 'total_profit', 1);

-- 23. 所得税费用 income_tax_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第23行', 'income_tax_expense', 3),
    ('23行', 'income_tax_expense', 3),
    ('行次23', 'income_tax_expense', 3),
    ('所得税费用', 'income_tax_expense', 2),
    ('所得税', 'income_tax_expense', 1),
    ('企业所得税', 'income_tax_expense', 1);

-- 24. 净利润 net_profit
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第24行', 'net_profit', 3),
    ('24行', 'net_profit', 3),
    ('行次24', 'net_profit', 3),
    ('净利润', 'net_profit', 2),
    ('净利', 'net_profit', 1),
    ('税后利润', 'net_profit', 1);

-- 25. 持续经营净利润 continued_ops_net_profit（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第25行', 'continued_ops_net_profit', 3),
    ('25行', 'continued_ops_net_profit', 3),
    ('行次25', 'continued_ops_net_profit', 3),
    ('持续经营净利润', 'continued_ops_net_profit', 2),
    ('持续经营净利', 'continued_ops_net_profit', 1);

-- 26. 终止经营净利润 discontinued_ops_net_profit（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第26行', 'discontinued_ops_net_profit', 3),
    ('26行', 'discontinued_ops_net_profit', 3),
    ('行次26', 'discontinued_ops_net_profit', 3),
    ('终止经营净利润', 'discontinued_ops_net_profit', 2),
    ('终止经营净利', 'discontinued_ops_net_profit', 1);

-- 27. 其他综合收益的税后净额 other_comprehensive_income_net（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第27行', 'other_comprehensive_income_net', 3),
    ('27行', 'other_comprehensive_income_net', 3),
    ('行次27', 'other_comprehensive_income_net', 3),
    ('其他综合收益的税后净额', 'other_comprehensive_income_net', 2),
    ('其他综合收益', 'other_comprehensive_income_net', 1),
    ('综合收益（税后）', 'other_comprehensive_income_net', 1);

-- 28. 不能重分类进损益的其他综合收益 oci_not_reclassifiable（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第28行', 'oci_not_reclassifiable', 3),
    ('28行', 'oci_not_reclassifiable', 3),
    ('行次28', 'oci_not_reclassifiable', 3),
    ('不能重分类进损益的其他综合收益', 'oci_not_reclassifiable', 2),
    ('不能重分类进损益', 'oci_not_reclassifiable', 1);

-- 29. 重新计量设定受益计划变动额 oci_remeasurement_pension（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第29行', 'oci_remeasurement_pension', 3),
    ('29行', 'oci_remeasurement_pension', 3),
    ('行次29', 'oci_remeasurement_pension', 3),
    ('重新计量设定受益计划变动额', 'oci_remeasurement_pension', 2),
    ('设定受益计划变动', 'oci_remeasurement_pension', 1);

-- 30. 权益法下不能转损益的其他综合收益 oci_equity_method_nonreclassifiable（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第30行', 'oci_equity_method_nonreclassifiable', 3),
    ('30行', 'oci_equity_method_nonreclassifiable', 3),
    ('行次30', 'oci_equity_method_nonreclassifiable', 3),
    ('权益法下不能转损益的其他综合收益', 'oci_equity_method_nonreclassifiable', 2),
    ('权益法不能转损益', 'oci_equity_method_nonreclassifiable', 1);

-- 31. 其他权益工具投资公允价值变动 oci_equity_investment_fv_change（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第31行', 'oci_equity_investment_fv_change', 3),
    ('31行', 'oci_equity_investment_fv_change', 3),
    ('行次31', 'oci_equity_investment_fv_change', 3),
    ('其他权益工具投资公允价值变动', 'oci_equity_investment_fv_change', 2),
    ('权益工具公允价变动', 'oci_equity_investment_fv_change', 1);

-- 32. 企业自身信用风险公允价值变动 oci_credit_risk_change（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第32行', 'oci_credit_risk_change', 3),
    ('32行', 'oci_credit_risk_change', 3),
    ('行次32', 'oci_credit_risk_change', 3),
    ('企业自身信用风险公允价值变动', 'oci_credit_risk_change', 2),
    ('信用风险公允价变动', 'oci_credit_risk_change', 1);

-- 33. 将重分类进损益的其他综合收益 oci_reclassifiable（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第33行', 'oci_reclassifiable', 3),
    ('33行', 'oci_reclassifiable', 3),
    ('行次33', 'oci_reclassifiable', 3),
    ('将重分类进损益的其他综合收益', 'oci_reclassifiable', 2),
    ('将重分类进损益', 'oci_reclassifiable', 1);

-- 34. 权益法下可转损益的其他综合收益 oci_equity_method_reclassifiable（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第34行', 'oci_equity_method_reclassifiable', 3),
    ('34行', 'oci_equity_method_reclassifiable', 3),
    ('行次34', 'oci_equity_method_reclassifiable', 3),
    ('权益法下可转损益的其他综合收益', 'oci_equity_method_reclassifiable', 2),
    ('权益法可转损益', 'oci_equity_method_reclassifiable', 1);

-- 35. 其他债权投资公允价值变动 oci_debt_investment_fv_change（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第35行', 'oci_debt_investment_fv_change', 3),
    ('35行', 'oci_debt_investment_fv_change', 3),
    ('行次35', 'oci_debt_investment_fv_change', 3),
    ('其他债权投资公允价值变动', 'oci_debt_investment_fv_change', 2),
    ('债权投资公允价变动', 'oci_debt_investment_fv_change', 1);

-- 36. 金融资产重分类计入其他综合收益的金额 oci_reclassify_to_pnl（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第36行', 'oci_reclassify_to_pnl', 3),
    ('36行', 'oci_reclassify_to_pnl', 3),
    ('行次36', 'oci_reclassify_to_pnl', 3),
    ('金融资产重分类计入其他综合收益的金额', 'oci_reclassify_to_pnl', 2),
    ('重分类计入综合收益', 'oci_reclassify_to_pnl', 1);

-- 37. 其他债权投资信用减值准备 oci_debt_impairment（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第37行', 'oci_debt_impairment', 3),
    ('37行', 'oci_debt_impairment', 3),
    ('行次37', 'oci_debt_impairment', 3),
    ('其他债权投资信用减值准备', 'oci_debt_impairment', 2),
    ('债权投资信用减值', 'oci_debt_impairment', 1);

-- 38. 现金流量套期储备 oci_cash_flow_hedge（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第38行', 'oci_cash_flow_hedge', 3),
    ('38行', 'oci_cash_flow_hedge', 3),
    ('行次38', 'oci_cash_flow_hedge', 3),
    ('现金流量套期储备', 'oci_cash_flow_hedge', 2),
    ('套期储备', 'oci_cash_flow_hedge', 1);

-- 39. 外币财务报表折算差额 oci_foreign_currency_translation（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第39行', 'oci_foreign_currency_translation', 3),
    ('39行', 'oci_foreign_currency_translation', 3),
    ('行次39', 'oci_foreign_currency_translation', 3),
    ('外币财务报表折算差额', 'oci_foreign_currency_translation', 2),
    ('外币折算差额', 'oci_foreign_currency_translation', 1);

-- 40. 综合收益总额 comprehensive_income_total（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第40行', 'comprehensive_income_total', 3),
    ('40行', 'comprehensive_income_total', 3),
    ('行次40', 'comprehensive_income_total', 3),
    ('综合收益总额', 'comprehensive_income_total', 2),
    ('总综合收益', 'comprehensive_income_total', 1),
    ('综合收益合计', 'comprehensive_income_total', 1);

-- 42. 基本每股收益 eps_basic（企业会计准则特有，行次42）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第42行', 'eps_basic', 3),
    ('42行', 'eps_basic', 3),
    ('行次42', 'eps_basic', 3),
    ('基本每股收益', 'eps_basic', 2),
    ('每股收益', 'eps_basic', 1),
    ('EPS', 'eps_basic', 1);

-- 43. 稀释每股收益 eps_diluted（企业会计准则特有）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第43行', 'eps_diluted', 3),
    ('43行', 'eps_diluted', 3),
    ('行次43', 'eps_diluted', 3),
    ('稀释每股收益', 'eps_diluted', 2),
    ('稀释EPS', 'eps_diluted', 1);

-- ========== 小企业会计准则特有字段 ==========

-- 4. 消费税 consumption_tax
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第4行', 'consumption_tax', 3),
    ('4行', 'consumption_tax', 3),
    ('行次4', 'consumption_tax', 3),
    ('消费税', 'consumption_tax', 2),
    ('消费税额', 'consumption_tax', 1);

-- 5. 营业税 business_tax（已取消，但保留）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第5行', 'business_tax', 3),
    ('5行', 'business_tax', 3),
    ('行次5', 'business_tax', 3),
    ('营业税', 'business_tax', 2),
    ('营业税额', 'business_tax', 1);

-- 6. 城市维护建设税 city_maintenance_tax
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第6行', 'city_maintenance_tax', 3),
    ('6行', 'city_maintenance_tax', 3),
    ('行次6', 'city_maintenance_tax', 3),
    ('城市维护建设税', 'city_maintenance_tax', 2),
    ('城建税', 'city_maintenance_tax', 1);

-- 7. 资源税 resource_tax
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第7行', 'resource_tax', 3),
    ('7行', 'resource_tax', 3),
    ('行次7', 'resource_tax', 3),
    ('资源税', 'resource_tax', 2),
    ('资源税额', 'resource_tax', 1);

-- 8. 土地增值税 land_appreciation_tax
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第8行', 'land_appreciation_tax', 3),
    ('8行', 'land_appreciation_tax', 3),
    ('行次8', 'land_appreciation_tax', 3),
    ('土地增值税', 'land_appreciation_tax', 2),
    ('土地增值税额', 'land_appreciation_tax', 1);

-- 9. 城镇土地使用税、房产税、车船税、印花税 property_related_taxes
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第9行', 'property_related_taxes', 3),
    ('9行', 'property_related_taxes', 3),
    ('行次9', 'property_related_taxes', 3),
    ('城镇土地使用税、房产税、车船税、印花税', 'property_related_taxes', 2),
    ('城镇土地使用税', 'property_related_taxes', 1),
    ('房产税', 'property_related_taxes', 1),
    ('车船税', 'property_related_taxes', 1),
    ('印花税', 'property_related_taxes', 1),
    ('土地使用税', 'property_related_taxes', 1);

-- 10. 教育费附加 education_surcharge（注意：第10行中文名含三项，但字段对应教育费附加）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第10行', 'education_surcharge', 3),
    ('10行', 'education_surcharge', 3),
    ('行次10', 'education_surcharge', 3),
    ('教育费附加', 'education_surcharge', 2),
    ('教育附加', 'education_surcharge', 1);

-- 矿产资源补偿费 mineral_compensation（未直接对应行次，但作为第10行的组成部分）
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('矿产资源补偿费', 'mineral_compensation', 2),
    ('矿补费', 'mineral_compensation', 1);

-- 排污费 sewage_charge
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('排污费', 'sewage_charge', 2),
    ('排污费', 'sewage_charge', 1);  -- 无行次

-- 11. 销售费用 selling_expense（已在企业部分存在，但小企业也有，字段相同，无需重复）

-- 12. 其中：商品维修费 goods_repair_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第12行', 'goods_repair_expense', 3),
    ('12行', 'goods_repair_expense', 3),
    ('行次12', 'goods_repair_expense', 3),
    ('其中：商品维修费', 'goods_repair_expense', 2),
    ('商品维修费', 'goods_repair_expense', 1),
    ('维修费', 'goods_repair_expense', 1);

-- 13. 广告费和业务宣传费 advertising_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第13行', 'advertising_expense', 3),
    ('13行', 'advertising_expense', 3),
    ('行次13', 'advertising_expense', 3),
    ('广告费和业务宣传费', 'advertising_expense', 2),
    ('广告费', 'advertising_expense', 1),
    ('宣传费', 'advertising_expense', 1),
    ('广宣费', 'advertising_expense', 1);

-- 14. 管理费用 administrative_expense（已在企业部分存在）

-- 15. 其中：开办费 organization_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第15行', 'organization_expense', 3),
    ('15行', 'organization_expense', 3),
    ('行次15', 'organization_expense', 3),
    ('其中：开办费', 'organization_expense', 2),
    ('开办费', 'organization_expense', 1),
    ('开办费用', 'organization_expense', 1);

-- 16. 业务招待费 business_entertainment_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第16行', 'business_entertainment_expense', 3),
    ('16行', 'business_entertainment_expense', 3),
    ('行次16', 'business_entertainment_expense', 3),
    ('业务招待费', 'business_entertainment_expense', 2),
    ('招待费', 'business_entertainment_expense', 1);

-- 17. 研究费用 research_expense
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第17行', 'research_expense', 3),
    ('17行', 'research_expense', 3),
    ('行次17', 'research_expense', 3),
    ('研究费用', 'research_expense', 2),
    ('研究费', 'research_expense', 1);

-- 18. 财务费用 financial_expense（已在企业部分存在）

-- 19. 其中：利息费用（收入以“-”号填列） interest_expense_net
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第19行', 'interest_expense_net', 3),
    ('19行', 'interest_expense_net', 3),
    ('行次19', 'interest_expense_net', 3),
    ('其中：利息费用（收入以“-”号填列）', 'interest_expense_net', 2),
    ('利息费用净额', 'interest_expense_net', 1),
    ('利息收支净额', 'interest_expense_net', 1),
    ('净利息费用', 'interest_expense_net', 1);

-- 20. 投资收益 investment_income（已在企业部分存在）

-- 21. 二、营业利润 operating_profit（已在企业部分存在）

-- 22. 加：营业外收入 non_operating_income（已在企业部分存在）

-- 23. 其中：政府补助 government_grant
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第23行', 'government_grant', 3),
    ('23行', 'government_grant', 3),
    ('行次23', 'government_grant', 3),
    ('其中：政府补助', 'government_grant', 2),
    ('政府补助', 'government_grant', 1),
    ('补助收入', 'government_grant', 1),
    ('财政补贴', 'government_grant', 1);

-- 24. 减：营业外支出 non_operating_expense（已在企业部分存在）

-- 25. 其中：坏账损失 bad_debt_loss
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第25行', 'bad_debt_loss', 3),
    ('25行', 'bad_debt_loss', 3),
    ('行次25', 'bad_debt_loss', 3),
    ('其中：坏账损失', 'bad_debt_loss', 2),
    ('坏账损失', 'bad_debt_loss', 1),
    ('坏账', 'bad_debt_loss', 1);

-- 26. 无法收回的长期债券投资损失 long_term_bond_loss
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第26行', 'long_term_bond_loss', 3),
    ('26行', 'long_term_bond_loss', 3),
    ('行次26', 'long_term_bond_loss', 3),
    ('无法收回的长期债券投资损失', 'long_term_bond_loss', 2),
    ('长期债券损失', 'long_term_bond_loss', 1),
    ('债券投资损失', 'long_term_bond_loss', 1);

-- 27. 无法收回的长期股权投资损失 long_term_equity_loss
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第27行', 'long_term_equity_loss', 3),
    ('27行', 'long_term_equity_loss', 3),
    ('行次27', 'long_term_equity_loss', 3),
    ('无法收回的长期股权投资损失', 'long_term_equity_loss', 2),
    ('长期股权损失', 'long_term_equity_loss', 1),
    ('股权投资损失', 'long_term_equity_loss', 1);

-- 28. 自然灾害等不可抗力因素造成的损失 force_majeure_loss
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第28行', 'force_majeure_loss', 3),
    ('28行', 'force_majeure_loss', 3),
    ('行次28', 'force_majeure_loss', 3),
    ('自然灾害等不可抗力因素造成的损失', 'force_majeure_loss', 2),
    ('灾害损失', 'force_majeure_loss', 1),
    ('不可抗力损失', 'force_majeure_loss', 1);

-- 29. 税收滞纳金 tax_late_payment
INSERT OR IGNORE INTO fs_profit_synonyms (phrase, column_name, priority) VALUES
    ('第29行', 'tax_late_payment', 3),
    ('29行', 'tax_late_payment', 3),
    ('行次29', 'tax_late_payment', 3),
    ('税收滞纳金', 'tax_late_payment', 2),
    ('滞纳金', 'tax_late_payment', 1),
    ('税务滞纳金', 'tax_late_payment', 1);

-- 30. 三、利润总额 total_profit（已在企业部分存在）

-- 31. 减：所得税费用 income_tax_expense（已在企业部分存在）

-- 32. 四、净利润 net_profit（已在企业部分存在）

-- 注意：对于小企业第10行拆分的 mineral_compensation 和 sewage_charge 没有单独行次，但已添加短语。

-- 部分字段可能遗漏，可根据实际需要补充。
```

---

### 4.4 分准则视图（NL2SQL 入口）

#### 企业会计准则视图（`vw_profit_eas`）
```sql
CREATE VIEW vw_profit_eas AS
SELECT
    taxpayer_id,
    t.taxpayer_name,
    period_year,
    period_month,
    time_range,
    '企业会计准则' AS accounting_standard_name,
    -- 企业会计准则相关列（仅列出该准则使用的列，避免模型混淆）
    operating_revenue,
    operating_cost,
    taxes_and_surcharges,
    selling_expense,
    administrative_expense,
    rd_expense,
    financial_expense,
    interest_expense,
    interest_income,
    other_gains,
    investment_income,
    investment_income_associates,
    amortized_cost_termination_income,
    net_exposure_hedge_income,
    fair_value_change_income,
    credit_impairment_loss,
    asset_impairment_loss,
    asset_disposal_gains,
    operating_profit,
    non_operating_income,
    non_operating_expense,
    total_profit,
    income_tax_expense,
    net_profit,
    continued_ops_net_profit,
    discontinued_ops_net_profit,
    other_comprehensive_income_net,
    oci_not_reclassifiable,
    oci_reclassifiable,
    comprehensive_income_total,
    eps_basic,
    eps_diluted,
    -- 其他明细项可根据需要选择加入
    oci_remeasurement_pension,
    oci_equity_method_nonreclassifiable,
    oci_equity_investment_fv_change,
    oci_credit_risk_change,
    oci_equity_method_reclassifiable,
    oci_debt_investment_fv_change,
    oci_reclassify_to_pnl,
    oci_debt_impairment,
    oci_cash_flow_hedge,
    oci_foreign_currency_translation
FROM fs_profit_statement_detail p
JOIN taxpayer_info t ON p.taxpayer_id = t.taxpayer_id
WHERE p.accounting_standard = 'ASBE';
```

#### 小企业会计准则视图（`vw_profit_sas`）
```sql
CREATE VIEW vw_profit_sas AS
SELECT
    taxpayer_id,
    t.taxpayer_name,
    period_year,
    period_month,
    time_range,
    '小企业会计准则' AS accounting_standard_name,
    -- 小企业会计准则相关列
    operating_revenue,
    operating_cost,
    taxes_and_surcharges,
    consumption_tax,
    business_tax,
    city_maintenance_tax,
    resource_tax,
    land_appreciation_tax,
    property_related_taxes,
    education_surcharge,
    selling_expense,
    goods_repair_expense,
    advertising_expense,
    administrative_expense,
    organization_expense,
    business_entertainment_expense,
    research_expense,
    financial_expense,
    interest_expense_net,
    investment_income,
    operating_profit,
    non_operating_income,
    government_grant,
    non_operating_expense,
    bad_debt_loss,
    long_term_bond_loss,
    long_term_equity_loss,
    force_majeure_loss,
    tax_late_payment,
    total_profit,
    income_tax_expense,
    net_profit
FROM fs_profit_statement_detail p
JOIN taxpayer_info t ON p.taxpayer_id = t.taxpayer_id
WHERE p.accounting_standard = 'SAS';
```

---

### 4.5 跨准则对比（UNION ALL）

当用户需要对比两类准则的同一指标（如净利润）时，推荐使用 `UNION ALL` 对齐输出：

```sql
WITH asbe AS (
    SELECT
        taxpayer_id,
        period_year,
        period_month,
        '企业会计准则' AS standard,
        time_range,
        net_profit
    FROM vw_profit_eas
    WHERE taxpayer_id = :taxpayer_id
      AND period_year = :year AND period_month = :month
      AND time_range = '本期'
),
sas AS (
    SELECT
        taxpayer_id,
        period_year,
        period_month,
        '小企业会计准则' AS standard,
        time_range,
        net_profit
    FROM vw_profit_sas
    WHERE taxpayer_id = :taxpayer_id
      AND period_year = :year AND period_month = :month
      AND time_range = '本期'
)
SELECT * FROM asbe
UNION ALL
SELECT * FROM sas
ORDER BY standard;
```

---

### 4.6 用户查询日志与未匹配短语表

复用增值税的 `user_query_log` 和 `unmatched_phrases` 表结构（可增加字段 `domain` 标识 'profit'）。

---

## 5. ETL 流程设计（Excel → 明细表）

1. **输入解析**  
   - 识别报表类型（企业会计准则/小企业会计准则）、纳税人识别号、所属期（年月）、单位等。  
   - 提取二维表格：行 = 行次，列 = 两列数据（本期金额、本年累计金额）。

2. **行列转换**  
   ```python
   rows_dict = {}  # key = (纳税人, 所属期, 准则, 时间范围)
   for 行次号, 数值 in 行数据.items():
       field_name = mapping[行次号]['column_name']   # 从对应准则映射表获取
       for 列标题 in ['本期金额', '本年累计金额']:
           time_range = '本期' if 列标题 == '本期金额' else '本年累计'
           key = (taxpayer_id, period, accounting_standard, time_range)
           rows_dict[key][field_name] = 数值
   ```

3. **写入明细表**  
   - 使用 `INSERT OR REPLACE` 按主键批量 upsert。

4. **ETL 校验**（可选）  
   - 检查勾稽关系：如营业利润 = 营业收入 - 营业成本 - 税金及附加 - 费用等（允许误差）。  
   - 单位转换：若源为“万元”，统一换算为“元”并记录 `source_unit`。

---

## 6. NL2SQL 应用流程（参照增值税方案）

完全沿用增值税方案中的**两阶段受控生成**流程：

- **阶段0（实体预处理）**：识别纳税人、期次、准则关键词（如“企业会计准则”“小规模”等）。  
- **阶段1（意图解析）**：LLM 输出 JSON，包含 `domain='profit'`、`accounting_standard`、`time_range`、指标字段、过滤条件等。  
- **约束注入器**：根据 JSON 从 `schema_catalog` 注入对应视图的白名单列。  
- **阶段2（SQL 生成）**：在白名单内生成 SQLite SQL。  
- **SQL 审核器**：按规则硬拦截（只读、单语句、必备 taxpayer_id 和期间过滤、禁止 SELECT *、LIMIT 等）。  
- **执行与反馈**。

**同义词标准化**：根据识别的准则，启用对应视图的同义词进行替换。

---

## 7. 方案对比分析

| 对比维度 | **本方案（统一明细表 + 分准则视图 + 两阶段生成）** | **独立两张宽表** | **全纵表（一行一项目）** |
|----------|-----------------------------------------------|------------------|--------------------------|
| **NL2SQL 表选择复杂度** | ⭐⭐⭐⭐⭐（准则由视图固定，模型无需选择） | ⭐⭐⭐（模型需判断用哪张表） | ⭐⭐（需理解项目名称） |
| **字段语义明确性** | ⭐⭐⭐⭐⭐（视图仅含本准则字段，无干扰） | ⭐⭐⭐⭐⭐ | ⭐⭐（项目名称需映射） |
| **存储效率** | ⭐⭐⭐（宽表有一定稀疏性，但列数可控） | ⭐⭐⭐⭐（无跨准则稀疏） | ⭐⭐⭐⭐⭐ |
| **ETL 维护成本** | ⭐⭐⭐（需维护映射表，但一次配置） | ⭐⭐⭐⭐（两套独立导入） | ⭐⭐⭐（需 unpivot） |
| **跨准则比较** | ⭐⭐⭐⭐（UNION ALL 对齐口径） | ⭐⭐（需跨表 UNION，列名不同） | ⭐⭐⭐（需按项目过滤） |
| **扩展新准则** | ⭐⭐⭐⭐（新增列+视图+映射，无需改应用） | ⭐⭐（需新建表并调整路由） | ⭐⭐⭐（新增项目即可） |
| **大模型准确率** | **≥95% 目标** | 90~95% | 70~80% |

---

## 8. 总结与扩展建议

本方案参照增值税 NL2SQL 模型，为利润表提供了：

- 统一明细表 `fs_profit_statement_detail`，容纳企业会计准则和小企业会计准则所有项目；
- 两张分准则查询视图 `vw_profit_eas` 和 `vw_profit_sas`，隔离模型与底层存储；
- 映射表与同义词表，支撑 ETL 和 NL2SQL 语义映射；
- 完整的两阶段受控生成流程，确保高准确率和安全性。

**下一步扩展**：
1. 增加资产负债表、现金流量表等，复用相同模式。
2. 构建跨报表指标字典（如“净利润”在利润表和现金流量表中的口径差异）。
3. 基于 `unmatched_phrases` 持续优化同义词库。

---

## 附录：与增值税方案差异说明

- 增值税方案中每个纳税人每期有 4 行（2 个项目类型 × 2 个时间范围），利润表每准则每期有 2 行（2 个时间范围），行数更少。
- 利润表统一明细表列数较多（约80列），但仍在可控范围，通过视图屏蔽了无关列。
- 同义词表增加了 `accounting_standard` 字段，实现准则级路由。