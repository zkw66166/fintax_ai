# 现金流量表 NL2SQL 数据模型方案文档  
**版本**：**v1.0** | **最后更新**：2026-02-15  

## 项目背景与目标  

现金流量表是企业财务报表的重要组成部分，反映企业一定会计期间现金和现金等价物流入与流出的情况。本方案针对**企业会计准则**与**小企业会计准则**两套现金流量表主表设计 NL2SQL 数据模型，支持用户通过自然语言查询任意企业、任意期次的现金流量明细数据。  

- 企业会计准则现金流量表：35 个行次，每行对应“本年累计金额”与“本期金额”两列数据。  
- 小企业会计准则现金流量表：22 个行次，同样包含“本年累计金额”与“本期金额”两列。  

目标：  
- 支持自然语言查询（如“某公司2025年12月经营活动产生的现金流量净额是多少？”）。  
- 支持跨期对比、趋势分析。  
- 支持多企业维度筛选（行业、地区、信用等级等）。  
- ETL 能从 PDF/Excel 稳定导入。  
- 存储紧凑、查询高效，NL2SQL 准确率 ≥95%。  

---

## 核心挑战  

| 挑战 | 描述 |
|------|------|
| **两套异构表** | 企业会计准则与小企业会计准则表结构不同，行次与指标语义无法直接合并。 |
| **维度组合** | 每行次数据有“本年累计”与“本期”两个时间口径，需要合理建模消除冗余。 |
| **NL2SQL 歧义** | 用户口语化表达（如“经营性现金流”“第5行”“支付给职工”）需精准映射到物理字段。 |
| **表路由** | 必须根据企业执行的会计准则自动选择查询视图，否则易出错。 |
| **ETL 复杂性** | 原始表格为二维格式，需转换为关系模型。 |

---

## 设计原则  

1. **存储与查询解耦**：明细表按会计准则分两张存储，ETL 清晰；查询侧通过分准则视图提供入口，NL2SQL 永不直接操作明细表。  
2. **字段名即业务术语**：物理字段采用完整业务中文名英译（如 `operating_inflow_sales`），大模型零学习成本。  
3. **同义词集中管理**：单独映射表存储用户口语→标准字段的映射，支持前置替换。  
4. **维度行拍平**：将“本年累计”与“本期”两列拆分为 `time_range` 维度，每纳税人每期仅 2 行数据（每行包含全部 35/22 个指标），既消除稀疏性又保持指标列完整。  
5. **一次设计，无限扩展**：新增现金流量表其他附注资料可复用相同模式。  

---

## 4. 数据模型详细设计  

### 4.1 企业会计准则现金流量表明细表（`cf_return_general`）  

```sql
-- 企业会计准则现金流量表主表
CREATE TABLE cf_return_general (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    time_range          TEXT NOT NULL,   -- '本年累计', '本期'

    -- 追溯/版本（参考增值税方案）
    revision_no         INTEGER NOT NULL DEFAULT 0,   -- 0=原始申报，1..n=更正版本
    submitted_at        TIMESTAMP,                    -- 申报提交时间（若可获取）
    etl_batch_id        TEXT,                         -- ETL批次ID
    source_doc_id       TEXT,                         -- 来源文件ID/路径hash
    source_unit         TEXT DEFAULT '元',            -- 金额单位：'元'/'万元'
    etl_confidence      REAL,                         -- OCR/解析置信度（0~1）

    -- ========== 35个指标列（行次1～35） ==========
    -- 经营活动
    operating_inflow_sales                NUMERIC,  -- 1: 销售商品、提供劳务收到的现金
    operating_inflow_tax_refund            NUMERIC,  -- 2: 收到的税费返还
    operating_inflow_other                 NUMERIC,  -- 3: 收到其他与经营活动有关的现金
    operating_inflow_subtotal               NUMERIC,  -- 4: 经营活动现金流入小计
    operating_outflow_purchase              NUMERIC,  -- 5: 购买商品、接受劳务支付的现金
    operating_outflow_labor                 NUMERIC,  -- 6: 支付给职工以及为职工支付的现金
    operating_outflow_tax                   NUMERIC,  -- 7: 支付的各项税费
    operating_outflow_other                  NUMERIC,  -- 8: 支付其他与经营活动有关的现金
    operating_outflow_subtotal                NUMERIC,  -- 9: 经营活动现金流出小计
    operating_net_cash                       NUMERIC,  -- 10: 经营活动产生的现金流量净额

    -- 投资活动
    investing_inflow_sale_investment         NUMERIC,  -- 11: 收回投资收到的现金
    investing_inflow_returns                 NUMERIC,  -- 12: 取得投资收益收到的现金
    investing_inflow_disposal_assets         NUMERIC,  -- 13: 处置固定资产、无形资产和其他长期资产收回的现金净额
    investing_inflow_disposal_subsidiary     NUMERIC,  -- 14: 处置子公司及其他营业单位收到的现金净额
    investing_inflow_other                    NUMERIC,  -- 15: 收到其他与投资活动有关的现金
    investing_inflow_subtotal                  NUMERIC,  -- 16: 投资活动现金流入小计
    investing_outflow_purchase_assets          NUMERIC,  -- 17: 购建固定资产、无形资产和其他长期资产支付的现金
    investing_outflow_purchase_investment      NUMERIC,  -- 18: 投资支付的现金
    investing_outflow_acquire_subsidiary       NUMERIC,  -- 19: 取得子公司及其他营业单位支付的现金净额
    investing_outflow_other                     NUMERIC,  -- 20: 支付其他与投资活动有关的现金
    investing_outflow_subtotal                   NUMERIC,  -- 21: 投资活动现金流出小计
    investing_net_cash                            NUMERIC,  -- 22: 投资活动产生的现金流量净额

    -- 筹资活动
    financing_inflow_capital                   NUMERIC,  -- 23: 吸收投资收到的现金
    financing_inflow_borrowing                  NUMERIC,  -- 24: 取得借款收到的现金
    financing_inflow_other                        NUMERIC,  -- 25: 收到其他与筹资活动有关的现金
    financing_inflow_subtotal                      NUMERIC,  -- 26: 筹资活动现金流入小计
    financing_outflow_debt_repayment               NUMERIC,  -- 27: 偿还债务支付的现金
    financing_outflow_dividend_interest             NUMERIC,  -- 28: 分配股利、利润或偿付利息支付的现金
    financing_outflow_other                           NUMERIC,  -- 29: 支付其他与筹资活动有关的现金
    financing_outflow_subtotal                         NUMERIC,  -- 30: 筹资活动现金流出小计
    financing_net_cash                                  NUMERIC,  -- 31: 筹资活动产生的现金流量净额

    -- 汇率变动及现金等价物净增加额
    fx_impact                                         NUMERIC,  -- 32: 汇率变动对现金及现金等价物的影响
    net_increase_cash                                  NUMERIC,  -- 33: 现金及现金等价物净增加额
    beginning_cash                                     NUMERIC,  -- 34: 期初现金及现金等价物余额
    ending_cash                                        NUMERIC,  -- 35: 期末现金及现金等价物余额

    PRIMARY KEY (taxpayer_id, period_year, period_month, time_range, revision_no),
    CHECK (time_range IN ('本年累计', '本期')),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_cf_eas_period ON cf_return_general (period_year, period_month);
CREATE INDEX idx_cf_eas_taxpayer ON cf_return_general (taxpayer_id);
CREATE INDEX idx_cf_eas_taxpayer_period ON cf_return_general (taxpayer_id, period_year, period_month);
```

### 4.2 小企业会计准则现金流量表明细表（`cf_return_small`）  

```sql
CREATE TABLE cf_return_small (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    time_range          TEXT NOT NULL,   -- '本年累计', '本期'

    -- 追溯/版本
    revision_no         INTEGER NOT NULL DEFAULT 0,
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    source_unit         TEXT DEFAULT '元',
    etl_confidence      REAL,

    -- ========== 22个指标列（行次1～22） ==========
    -- 经营活动
    operating_receipts_sales                NUMERIC,  -- 1: 销售产成品、商品、提供劳务收到的现金
    operating_receipts_other                 NUMERIC,  -- 2: 收到其他与经营活动有关的现金
    operating_payments_purchase               NUMERIC,  -- 3: 购买原材料、商品、接受劳务支付的现金
    operating_payments_staff                  NUMERIC,  -- 4: 支付的职工薪酬
    operating_payments_tax                    NUMERIC,  -- 5: 支付的税费
    operating_payments_other                   NUMERIC,  -- 6: 支付其他与经营活动有关的现金
    operating_net_cash                          NUMERIC,  -- 7: 经营活动产生的现金流量净额

    -- 投资活动
    investing_receipts_disposal_investment     NUMERIC,  -- 8: 收回短期投资、长期债券投资和长期股权投资收到的现金
    investing_receipts_returns                 NUMERIC,  -- 9: 取得投资收益收到的现金
    investing_receipts_disposal_assets         NUMERIC,  -- 10: 处置固定资产、无形资产和其他非流动资产收回的现金净额
    investing_payments_purchase_investment     NUMERIC,  -- 11: 短期投资、长期债券投资和长期股权投资支付的现金
    investing_payments_purchase_assets         NUMERIC,  -- 12: 购建固定资产、无形资产和其他非流动资产支付的现金
    investing_net_cash                          NUMERIC,  -- 13: 投资活动产生的现金流量净额

    -- 筹资活动
    financing_receipts_borrowing               NUMERIC,  -- 14: 取得借款收到的现金
    financing_receipts_capital                  NUMERIC,  -- 15: 吸收投资者投资收到的现金
    financing_payments_debt_principal            NUMERIC,  -- 16: 偿还借款本金支付的现金
    financing_payments_debt_interest              NUMERIC,  -- 17: 偿还借款利息支付的现金
    financing_payments_dividend                   NUMERIC,  -- 18: 分配利润支付的现金
    financing_net_cash                              NUMERIC,  -- 19: 筹资活动产生的现金流量净额

    -- 现金净增加额及期末余额
    net_increase_cash                               NUMERIC,  -- 20: 现金净增加额
    beginning_cash                                  NUMERIC,  -- 21: 期初现金余额
    ending_cash                                     NUMERIC,  -- 22: 期末现金余额

    PRIMARY KEY (taxpayer_id, period_year, period_month, time_range, revision_no),
    CHECK (time_range IN ('本年累计', '本期')),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_cf_sas_period ON cf_return_small (period_year, period_month);
CREATE INDEX idx_cf_sas_taxpayer ON cf_return_small (taxpayer_id);
CREATE INDEX idx_cf_sas_taxpayer_period ON cf_return_small (taxpayer_id, period_year, period_month);
```

### 4.3 纳税人信息表（增强版，增加会计准则标识）  

在增值税文档的 `taxpayer_info` 基础上增加 `accounting_standard` 字段，用于区分企业执行的会计准则。  

```sql
CREATE TABLE taxpayer_info (
    taxpayer_id           TEXT PRIMARY KEY,
    taxpayer_name         TEXT NOT NULL,
    taxpayer_type         TEXT NOT NULL,               -- '一般纳税人'/'小规模纳税人'
    accounting_standard   TEXT,                         -- '企业会计准则'/'小企业会计准则'
    registration_type     TEXT,
    legal_representative  TEXT,
    establish_date        DATE,
    industry_code         TEXT,
    industry_name         TEXT,
    tax_authority_code    TEXT,
    tax_authority_name    TEXT,
    tax_bureau_level      TEXT,
    region_code           TEXT,
    region_name           TEXT,
    credit_grade_current  TEXT,
    credit_grade_year     INTEGER,
    status                TEXT DEFAULT 'active',
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_taxpayer_name ON taxpayer_info(taxpayer_name);
CREATE INDEX idx_taxpayer_industry ON taxpayer_info(industry_code);
CREATE INDEX idx_taxpayer_region ON taxpayer_info(region_code);
CREATE INDEX idx_taxpayer_authority ON taxpayer_info(tax_authority_code);
CREATE INDEX idx_taxpayer_accounting ON taxpayer_info(accounting_standard);
```

> **快照表**可参照增值税方案按需设计，此处略。

---

## 4.4 栏次-字段映射表（ETL 专用）  

### 4.4.1 企业会计准则映射表（`fs_cf_eas_column_mapping`）  

```sql
CREATE TABLE fs_cf_eas_column_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

INSERT OR REPLACE INTO fs_cf_eas_column_mapping (line_number, column_name, business_name) VALUES
(1,  'operating_inflow_sales', '销售商品、提供劳务收到的现金'),
(2,  'operating_inflow_tax_refund', '收到的税费返还'),
(3,  'operating_inflow_other', '收到其他与经营活动有关的现金'),
(4,  'operating_inflow_subtotal', '经营活动现金流入小计'),
(5,  'operating_outflow_purchase', '购买商品、接受劳务支付的现金'),
(6,  'operating_outflow_labor', '支付给职工以及为职工支付的现金'),
(7,  'operating_outflow_tax', '支付的各项税费'),
(8,  'operating_outflow_other', '支付其他与经营活动有关的现金'),
(9,  'operating_outflow_subtotal', '经营活动现金流出小计'),
(10, 'operating_net_cash', '经营活动产生的现金流量净额'),
(11, 'investing_inflow_sale_investment', '收回投资收到的现金'),
(12, 'investing_inflow_returns', '取得投资收益收到的现金'),
(13, 'investing_inflow_disposal_assets', '处置固定资产、无形资产和其他长期资产收回的现金净额'),
(14, 'investing_inflow_disposal_subsidiary', '处置子公司及其他营业单位收到的现金净额'),
(15, 'investing_inflow_other', '收到其他与投资活动有关的现金'),
(16, 'investing_inflow_subtotal', '投资活动现金流入小计'),
(17, 'investing_outflow_purchase_assets', '购建固定资产、无形资产和其他长期资产支付的现金'),
(18, 'investing_outflow_purchase_investment', '投资支付的现金'),
(19, 'investing_outflow_acquire_subsidiary', '取得子公司及其他营业单位支付的现金净额'),
(20, 'investing_outflow_other', '支付其他与投资活动有关的现金'),
(21, 'investing_outflow_subtotal', '投资活动现金流出小计'),
(22, 'investing_net_cash', '投资活动产生的现金流量净额'),
(23, 'financing_inflow_capital', '吸收投资收到的现金'),
(24, 'financing_inflow_borrowing', '取得借款收到的现金'),
(25, 'financing_inflow_other', '收到其他与筹资活动有关的现金'),
(26, 'financing_inflow_subtotal', '筹资活动现金流入小计'),
(27, 'financing_outflow_debt_repayment', '偿还债务支付的现金'),
(28, 'financing_outflow_dividend_interest', '分配股利、利润或偿付利息支付的现金'),
(29, 'financing_outflow_other', '支付其他与筹资活动有关的现金'),
(30, 'financing_outflow_subtotal', '筹资活动现金流出小计'),
(31, 'financing_net_cash', '筹资活动产生的现金流量净额'),
(32, 'fx_impact', '汇率变动对现金及现金等价物的影响'),
(33, 'net_increase_cash', '现金及现金等价物净增加额'),
(34, 'beginning_cash', '期初现金及现金等价物余额'),
(35, 'ending_cash', '期末现金及现金等价物余额');
```

### 4.4.2 小企业会计准则映射表（`fs_cf_sas_column_mapping`）  

```sql
CREATE TABLE fs_cf_sas_column_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

INSERT OR REPLACE INTO fs_cf_sas_column_mapping (line_number, column_name, business_name) VALUES
(1,  'operating_receipts_sales', '销售产成品、商品、提供劳务收到的现金'),
(2,  'operating_receipts_other', '收到其他与经营活动有关的现金'),
(3,  'operating_payments_purchase', '购买原材料、商品、接受劳务支付的现金'),
(4,  'operating_payments_staff', '支付的职工薪酬'),
(5,  'operating_payments_tax', '支付的税费'),
(6,  'operating_payments_other', '支付其他与经营活动有关的现金'),
(7,  'operating_net_cash', '经营活动产生的现金流量净额'),
(8,  'investing_receipts_disposal_investment', '收回短期投资、长期债券投资和长期股权投资收到的现金'),
(9,  'investing_receipts_returns', '取得投资收益收到的现金'),
(10, 'investing_receipts_disposal_assets', '处置固定资产、无形资产和其他非流动资产收回的现金净额'),
(11, 'investing_payments_purchase_investment', '短期投资、长期债券投资和长期股权投资支付的现金'),
(12, 'investing_payments_purchase_assets', '购建固定资产、无形资产和其他非流动资产支付的现金'),
(13, 'investing_net_cash', '投资活动产生的现金流量净额'),
(14, 'financing_receipts_borrowing', '取得借款收到的现金'),
(15, 'financing_receipts_capital', '吸收投资者投资收到的现金'),
(16, 'financing_payments_debt_principal', '偿还借款本金支付的现金'),
(17, 'financing_payments_debt_interest', '偿还借款利息支付的现金'),
(18, 'financing_payments_dividend', '分配利润支付的现金'),
(19, 'financing_net_cash', '筹资活动产生的现金流量净额'),
(20, 'net_increase_cash', '现金净增加额'),
(21, 'beginning_cash', '期初现金余额'),
(22, 'ending_cash', '期末现金余额');
```

---

## 4.5 同义词映射表（NL2SQL 专用）  

参考其他同义词表结构，增加 `scope_view` 和 `taxpayer_type` 字段以支持按视图过滤。  

```sql
CREATE TABLE fs_cf_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,
    column_name TEXT NOT NULL,
    priority    INTEGER DEFAULT 1,
    taxpayer_type TEXT,     -- '一般纳税人'/'小规模纳税人'/NULL(通用)
    scope_view    TEXT,     -- 'vw_cf_return_general'/'vw_cf_return_small'/NULL(通用)
    UNIQUE(phrase, column_name)
);
CREATE INDEX idx_fs_cf_synonyms_phrase ON fs_cf_synonyms(phrase);
CREATE INDEX idx_fs_cf_synonyms_scope ON fs_cf_synonyms(scope_view, taxpayer_type, priority);
```

**完整同义词**：  

```sql
-- ============================================
-- 企业会计准则（vw_cf_return_general）同义词
-- ============================================

-- 第1栏：operating_inflow_sales
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第1栏', 'operating_inflow_sales', 3, 'vw_cf_return_general'),
('1栏', 'operating_inflow_sales', 3, 'vw_cf_return_general'),
('栏次1', 'operating_inflow_sales', 3, 'vw_cf_return_general'),
('销售商品、提供劳务收到的现金', 'operating_inflow_sales', 2, 'vw_cf_return_general'),
('销售商品收到的现金', 'operating_inflow_sales', 1, 'vw_cf_return_general'),
('销售收现', 'operating_inflow_sales', 1, 'vw_cf_return_general'),
('商品销售收入现金', 'operating_inflow_sales', 1, 'vw_cf_return_general'),
('劳务收入现金', 'operating_inflow_sales', 1, 'vw_cf_return_general');

-- 第2栏：operating_inflow_tax_refund
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第2栏', 'operating_inflow_tax_refund', 3, 'vw_cf_return_general'),
('2栏', 'operating_inflow_tax_refund', 3, 'vw_cf_return_general'),
('栏次2', 'operating_inflow_tax_refund', 3, 'vw_cf_return_general'),
('收到的税费返还', 'operating_inflow_tax_refund', 2, 'vw_cf_return_general'),
('税费返还', 'operating_inflow_tax_refund', 1, 'vw_cf_return_general'),
('税收返还', 'operating_inflow_tax_refund', 1, 'vw_cf_return_general'),
('出口退税返还', 'operating_inflow_tax_refund', 1, 'vw_cf_return_general');

-- 第3栏：operating_inflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第3栏', 'operating_inflow_other', 3, 'vw_cf_return_general'),
('3栏', 'operating_inflow_other', 3, 'vw_cf_return_general'),
('栏次3', 'operating_inflow_other', 3, 'vw_cf_return_general'),
('收到其他与经营活动有关的现金', 'operating_inflow_other', 2, 'vw_cf_return_general'),
('其他经营现金流入', 'operating_inflow_other', 1, 'vw_cf_return_general'),
('经营其他收入', 'operating_inflow_other', 1, 'vw_cf_return_general'),
('政府补助收入', 'operating_inflow_other', 1, 'vw_cf_return_general');

-- 第4栏：operating_inflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第4栏', 'operating_inflow_subtotal', 3, 'vw_cf_return_general'),
('4栏', 'operating_inflow_subtotal', 3, 'vw_cf_return_general'),
('栏次4', 'operating_inflow_subtotal', 3, 'vw_cf_return_general'),
('经营活动现金流入小计', 'operating_inflow_subtotal', 2, 'vw_cf_return_general'),
('经营现金流入合计', 'operating_inflow_subtotal', 1, 'vw_cf_return_general'),
('经营流入小计', 'operating_inflow_subtotal', 1, 'vw_cf_return_general');

-- 第5栏：operating_outflow_purchase
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第5栏', 'operating_outflow_purchase', 3, 'vw_cf_return_general'),
('5栏', 'operating_outflow_purchase', 3, 'vw_cf_return_general'),
('栏次5', 'operating_outflow_purchase', 3, 'vw_cf_return_general'),
('购买商品、接受劳务支付的现金', 'operating_outflow_purchase', 2, 'vw_cf_return_general'),
('购买商品支付的现金', 'operating_outflow_purchase', 1, 'vw_cf_return_general'),
('采购付现', 'operating_outflow_purchase', 1, 'vw_cf_return_general'),
('购买原材料支付的现金', 'operating_outflow_purchase', 1, 'vw_cf_return_general'),
('接受劳务支付的现金', 'operating_outflow_purchase', 1, 'vw_cf_return_general');

-- 第6栏：operating_outflow_labor
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第6栏', 'operating_outflow_labor', 3, 'vw_cf_return_general'),
('6栏', 'operating_outflow_labor', 3, 'vw_cf_return_general'),
('栏次6', 'operating_outflow_labor', 3, 'vw_cf_return_general'),
('支付给职工以及为职工支付的现金', 'operating_outflow_labor', 2, 'vw_cf_return_general'),
('支付给职工的现金', 'operating_outflow_labor', 1, 'vw_cf_return_general'),
('职工薪酬支付', 'operating_outflow_labor', 1, 'vw_cf_return_general'),
('工资支付', 'operating_outflow_labor', 1, 'vw_cf_return_general'),
('为职工支付的现金', 'operating_outflow_labor', 1, 'vw_cf_return_general');

-- 第7栏：operating_outflow_tax
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第7栏', 'operating_outflow_tax', 3, 'vw_cf_return_general'),
('7栏', 'operating_outflow_tax', 3, 'vw_cf_return_general'),
('栏次7', 'operating_outflow_tax', 3, 'vw_cf_return_general'),
('支付的各项税费', 'operating_outflow_tax', 2, 'vw_cf_return_general'),
('支付税费', 'operating_outflow_tax', 1, 'vw_cf_return_general'),
('缴纳税款', 'operating_outflow_tax', 1, 'vw_cf_return_general'),
('税金支付', 'operating_outflow_tax', 1, 'vw_cf_return_general');

-- 第8栏：operating_outflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第8栏', 'operating_outflow_other', 3, 'vw_cf_return_general'),
('8栏', 'operating_outflow_other', 3, 'vw_cf_return_general'),
('栏次8', 'operating_outflow_other', 3, 'vw_cf_return_general'),
('支付其他与经营活动有关的现金', 'operating_outflow_other', 2, 'vw_cf_return_general'),
('其他经营现金流出', 'operating_outflow_other', 1, 'vw_cf_return_general'),
('经营其他支出', 'operating_outflow_other', 1, 'vw_cf_return_general'),
('付现费用', 'operating_outflow_other', 1, 'vw_cf_return_general');

-- 第9栏：operating_outflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第9栏', 'operating_outflow_subtotal', 3, 'vw_cf_return_general'),
('9栏', 'operating_outflow_subtotal', 3, 'vw_cf_return_general'),
('栏次9', 'operating_outflow_subtotal', 3, 'vw_cf_return_general'),
('经营活动现金流出小计', 'operating_outflow_subtotal', 2, 'vw_cf_return_general'),
('经营现金流出合计', 'operating_outflow_subtotal', 1, 'vw_cf_return_general'),
('经营流出小计', 'operating_outflow_subtotal', 1, 'vw_cf_return_general');

-- 第10栏：operating_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第10栏', 'operating_net_cash', 3, 'vw_cf_return_general'),
('10栏', 'operating_net_cash', 3, 'vw_cf_return_general'),
('栏次10', 'operating_net_cash', 3, 'vw_cf_return_general'),
('经营活动产生的现金流量净额', 'operating_net_cash', 2, 'vw_cf_return_general'),
('经营活动现金流量净额', 'operating_net_cash', 1, 'vw_cf_return_general'),
('经营净现金流', 'operating_net_cash', 1, 'vw_cf_return_general'),
('经营活动净额', 'operating_net_cash', 1, 'vw_cf_return_general'),
('CFO', 'operating_net_cash', 1, 'vw_cf_return_general');

-- 第11栏：investing_inflow_sale_investment
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第11栏', 'investing_inflow_sale_investment', 3, 'vw_cf_return_general'),
('11栏', 'investing_inflow_sale_investment', 3, 'vw_cf_return_general'),
('栏次11', 'investing_inflow_sale_investment', 3, 'vw_cf_return_general'),
('收回投资收到的现金', 'investing_inflow_sale_investment', 2, 'vw_cf_return_general'),
('收回投资现金', 'investing_inflow_sale_investment', 1, 'vw_cf_return_general'),
('投资收回', 'investing_inflow_sale_investment', 1, 'vw_cf_return_general'),
('出售投资收到的现金', 'investing_inflow_sale_investment', 1, 'vw_cf_return_general');

-- 第12栏：investing_inflow_returns
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第12栏', 'investing_inflow_returns', 3, 'vw_cf_return_general'),
('12栏', 'investing_inflow_returns', 3, 'vw_cf_return_general'),
('栏次12', 'investing_inflow_returns', 3, 'vw_cf_return_general'),
('取得投资收益收到的现金', 'investing_inflow_returns', 2, 'vw_cf_return_general'),
('投资收益现金', 'investing_inflow_returns', 1, 'vw_cf_return_general'),
('收到股利', 'investing_inflow_returns', 1, 'vw_cf_return_general'),
('收到利息', 'investing_inflow_returns', 1, 'vw_cf_return_general');

-- 第13栏：investing_inflow_disposal_assets
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第13栏', 'investing_inflow_disposal_assets', 3, 'vw_cf_return_general'),
('13栏', 'investing_inflow_disposal_assets', 3, 'vw_cf_return_general'),
('栏次13', 'investing_inflow_disposal_assets', 3, 'vw_cf_return_general'),
('处置固定资产、无形资产和其他长期资产收回的现金净额', 'investing_inflow_disposal_assets', 2, 'vw_cf_return_general'),
('处置固定资产收回的现金', 'investing_inflow_disposal_assets', 1, 'vw_cf_return_general'),
('出售固定资产现金', 'investing_inflow_disposal_assets', 1, 'vw_cf_return_general'),
('处置无形资产现金', 'investing_inflow_disposal_assets', 1, 'vw_cf_return_general'),
('资产处置净额', 'investing_inflow_disposal_assets', 1, 'vw_cf_return_general');

-- 第14栏：investing_inflow_disposal_subsidiary
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第14栏', 'investing_inflow_disposal_subsidiary', 3, 'vw_cf_return_general'),
('14栏', 'investing_inflow_disposal_subsidiary', 3, 'vw_cf_return_general'),
('栏次14', 'investing_inflow_disposal_subsidiary', 3, 'vw_cf_return_general'),
('处置子公司及其他营业单位收到的现金净额', 'investing_inflow_disposal_subsidiary', 2, 'vw_cf_return_general'),
('处置子公司现金', 'investing_inflow_disposal_subsidiary', 1, 'vw_cf_return_general'),
('出售子公司净额', 'investing_inflow_disposal_subsidiary', 1, 'vw_cf_return_general'),
('处置营业单位现金', 'investing_inflow_disposal_subsidiary', 1, 'vw_cf_return_general');

-- 第15栏：investing_inflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第15栏', 'investing_inflow_other', 3, 'vw_cf_return_general'),
('15栏', 'investing_inflow_other', 3, 'vw_cf_return_general'),
('栏次15', 'investing_inflow_other', 3, 'vw_cf_return_general'),
('收到其他与投资活动有关的现金', 'investing_inflow_other', 2, 'vw_cf_return_general'),
('其他投资现金流入', 'investing_inflow_other', 1, 'vw_cf_return_general'),
('投资其他收入', 'investing_inflow_other', 1, 'vw_cf_return_general');

-- 第16栏：investing_inflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第16栏', 'investing_inflow_subtotal', 3, 'vw_cf_return_general'),
('16栏', 'investing_inflow_subtotal', 3, 'vw_cf_return_general'),
('栏次16', 'investing_inflow_subtotal', 3, 'vw_cf_return_general'),
('投资活动现金流入小计', 'investing_inflow_subtotal', 2, 'vw_cf_return_general'),
('投资现金流入合计', 'investing_inflow_subtotal', 1, 'vw_cf_return_general'),
('投资流入小计', 'investing_inflow_subtotal', 1, 'vw_cf_return_general');

-- 第17栏：investing_outflow_purchase_assets
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第17栏', 'investing_outflow_purchase_assets', 3, 'vw_cf_return_general'),
('17栏', 'investing_outflow_purchase_assets', 3, 'vw_cf_return_general'),
('栏次17', 'investing_outflow_purchase_assets', 3, 'vw_cf_return_general'),
('购建固定资产、无形资产和其他长期资产支付的现金', 'investing_outflow_purchase_assets', 2, 'vw_cf_return_general'),
('购建固定资产支付的现金', 'investing_outflow_purchase_assets', 1, 'vw_cf_return_general'),
('购买固定资产现金', 'investing_outflow_purchase_assets', 1, 'vw_cf_return_general'),
('在建工程支出', 'investing_outflow_purchase_assets', 1, 'vw_cf_return_general'),
('无形资产购置', 'investing_outflow_purchase_assets', 1, 'vw_cf_return_general');

-- 第18栏：investing_outflow_purchase_investment
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第18栏', 'investing_outflow_purchase_investment', 3, 'vw_cf_return_general'),
('18栏', 'investing_outflow_purchase_investment', 3, 'vw_cf_return_general'),
('栏次18', 'investing_outflow_purchase_investment', 3, 'vw_cf_return_general'),
('投资支付的现金', 'investing_outflow_purchase_investment', 2, 'vw_cf_return_general'),
('投资付现', 'investing_outflow_purchase_investment', 1, 'vw_cf_return_general'),
('购买投资支付', 'investing_outflow_purchase_investment', 1, 'vw_cf_return_general'),
('对外投资现金', 'investing_outflow_purchase_investment', 1, 'vw_cf_return_general');

-- 第19栏：investing_outflow_acquire_subsidiary
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第19栏', 'investing_outflow_acquire_subsidiary', 3, 'vw_cf_return_general'),
('19栏', 'investing_outflow_acquire_subsidiary', 3, 'vw_cf_return_general'),
('栏次19', 'investing_outflow_acquire_subsidiary', 3, 'vw_cf_return_general'),
('取得子公司及其他营业单位支付的现金净额', 'investing_outflow_acquire_subsidiary', 2, 'vw_cf_return_general'),
('取得子公司支付现金', 'investing_outflow_acquire_subsidiary', 1, 'vw_cf_return_general'),
('收购子公司净额', 'investing_outflow_acquire_subsidiary', 1, 'vw_cf_return_general'),
('购买营业单位现金', 'investing_outflow_acquire_subsidiary', 1, 'vw_cf_return_general');

-- 第20栏：investing_outflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第20栏', 'investing_outflow_other', 3, 'vw_cf_return_general'),
('20栏', 'investing_outflow_other', 3, 'vw_cf_return_general'),
('栏次20', 'investing_outflow_other', 3, 'vw_cf_return_general'),
('支付其他与投资活动有关的现金', 'investing_outflow_other', 2, 'vw_cf_return_general'),
('其他投资现金流出', 'investing_outflow_other', 1, 'vw_cf_return_general'),
('投资其他支出', 'investing_outflow_other', 1, 'vw_cf_return_general');

-- 第21栏：investing_outflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第21栏', 'investing_outflow_subtotal', 3, 'vw_cf_return_general'),
('21栏', 'investing_outflow_subtotal', 3, 'vw_cf_return_general'),
('栏次21', 'investing_outflow_subtotal', 3, 'vw_cf_return_general'),
('投资活动现金流出小计', 'investing_outflow_subtotal', 2, 'vw_cf_return_general'),
('投资现金流出合计', 'investing_outflow_subtotal', 1, 'vw_cf_return_general'),
('投资流出小计', 'investing_outflow_subtotal', 1, 'vw_cf_return_general');

-- 第22栏：investing_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第22栏', 'investing_net_cash', 3, 'vw_cf_return_general'),
('22栏', 'investing_net_cash', 3, 'vw_cf_return_general'),
('栏次22', 'investing_net_cash', 3, 'vw_cf_return_general'),
('投资活动产生的现金流量净额', 'investing_net_cash', 2, 'vw_cf_return_general'),
('投资活动现金流量净额', 'investing_net_cash', 1, 'vw_cf_return_general'),
('投资净现金流', 'investing_net_cash', 1, 'vw_cf_return_general'),
('CFI', 'investing_net_cash', 1, 'vw_cf_return_general');

-- 第23栏：financing_inflow_capital
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第23栏', 'financing_inflow_capital', 3, 'vw_cf_return_general'),
('23栏', 'financing_inflow_capital', 3, 'vw_cf_return_general'),
('栏次23', 'financing_inflow_capital', 3, 'vw_cf_return_general'),
('吸收投资收到的现金', 'financing_inflow_capital', 2, 'vw_cf_return_general'),
('吸收投资现金', 'financing_inflow_capital', 1, 'vw_cf_return_general'),
('发行股票收到的现金', 'financing_inflow_capital', 1, 'vw_cf_return_general'),
('增资扩股现金', 'financing_inflow_capital', 1, 'vw_cf_return_general');

-- 第24栏：financing_inflow_borrowing
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第24栏', 'financing_inflow_borrowing', 3, 'vw_cf_return_general'),
('24栏', 'financing_inflow_borrowing', 3, 'vw_cf_return_general'),
('栏次24', 'financing_inflow_borrowing', 3, 'vw_cf_return_general'),
('取得借款收到的现金', 'financing_inflow_borrowing', 2, 'vw_cf_return_general'),
('借款收到的现金', 'financing_inflow_borrowing', 1, 'vw_cf_return_general'),
('银行贷款现金', 'financing_inflow_borrowing', 1, 'vw_cf_return_general'),
('发行债券收到的现金', 'financing_inflow_borrowing', 1, 'vw_cf_return_general');

-- 第25栏：financing_inflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第25栏', 'financing_inflow_other', 3, 'vw_cf_return_general'),
('25栏', 'financing_inflow_other', 3, 'vw_cf_return_general'),
('栏次25', 'financing_inflow_other', 3, 'vw_cf_return_general'),
('收到其他与筹资活动有关的现金', 'financing_inflow_other', 2, 'vw_cf_return_general'),
('其他筹资现金流入', 'financing_inflow_other', 1, 'vw_cf_return_general'),
('筹资其他收入', 'financing_inflow_other', 1, 'vw_cf_return_general');

-- 第26栏：financing_inflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第26栏', 'financing_inflow_subtotal', 3, 'vw_cf_return_general'),
('26栏', 'financing_inflow_subtotal', 3, 'vw_cf_return_general'),
('栏次26', 'financing_inflow_subtotal', 3, 'vw_cf_return_general'),
('筹资活动现金流入小计', 'financing_inflow_subtotal', 2, 'vw_cf_return_general'),
('筹资现金流入合计', 'financing_inflow_subtotal', 1, 'vw_cf_return_general'),
('筹资流入小计', 'financing_inflow_subtotal', 1, 'vw_cf_return_general');

-- 第27栏：financing_outflow_debt_repayment
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第27栏', 'financing_outflow_debt_repayment', 3, 'vw_cf_return_general'),
('27栏', 'financing_outflow_debt_repayment', 3, 'vw_cf_return_general'),
('栏次27', 'financing_outflow_debt_repayment', 3, 'vw_cf_return_general'),
('偿还债务支付的现金', 'financing_outflow_debt_repayment', 2, 'vw_cf_return_general'),
('偿还债务现金', 'financing_outflow_debt_repayment', 1, 'vw_cf_return_general'),
('还债付现', 'financing_outflow_debt_repayment', 1, 'vw_cf_return_general'),
('偿还借款', 'financing_outflow_debt_repayment', 1, 'vw_cf_return_general');

-- 第28栏：financing_outflow_dividend_interest
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第28栏', 'financing_outflow_dividend_interest', 3, 'vw_cf_return_general'),
('28栏', 'financing_outflow_dividend_interest', 3, 'vw_cf_return_general'),
('栏次28', 'financing_outflow_dividend_interest', 3, 'vw_cf_return_general'),
('分配股利、利润或偿付利息支付的现金', 'financing_outflow_dividend_interest', 2, 'vw_cf_return_general'),
('分配股利支付的现金', 'financing_outflow_dividend_interest', 1, 'vw_cf_return_general'),
('支付股利', 'financing_outflow_dividend_interest', 1, 'vw_cf_return_general'),
('偿付利息', 'financing_outflow_dividend_interest', 1, 'vw_cf_return_general'),
('支付利润', 'financing_outflow_dividend_interest', 1, 'vw_cf_return_general');

-- 第29栏：financing_outflow_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第29栏', 'financing_outflow_other', 3, 'vw_cf_return_general'),
('29栏', 'financing_outflow_other', 3, 'vw_cf_return_general'),
('栏次29', 'financing_outflow_other', 3, 'vw_cf_return_general'),
('支付其他与筹资活动有关的现金', 'financing_outflow_other', 2, 'vw_cf_return_general'),
('其他筹资现金流出', 'financing_outflow_other', 1, 'vw_cf_return_general'),
('筹资其他支出', 'financing_outflow_other', 1, 'vw_cf_return_general');

-- 第30栏：financing_outflow_subtotal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第30栏', 'financing_outflow_subtotal', 3, 'vw_cf_return_general'),
('30栏', 'financing_outflow_subtotal', 3, 'vw_cf_return_general'),
('栏次30', 'financing_outflow_subtotal', 3, 'vw_cf_return_general'),
('筹资活动现金流出小计', 'financing_outflow_subtotal', 2, 'vw_cf_return_general'),
('筹资现金流出合计', 'financing_outflow_subtotal', 1, 'vw_cf_return_general'),
('筹资流出小计', 'financing_outflow_subtotal', 1, 'vw_cf_return_general');

-- 第31栏：financing_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第31栏', 'financing_net_cash', 3, 'vw_cf_return_general'),
('31栏', 'financing_net_cash', 3, 'vw_cf_return_general'),
('栏次31', 'financing_net_cash', 3, 'vw_cf_return_general'),
('筹资活动产生的现金流量净额', 'financing_net_cash', 2, 'vw_cf_return_general'),
('筹资活动现金流量净额', 'financing_net_cash', 1, 'vw_cf_return_general'),
('筹资净现金流', 'financing_net_cash', 1, 'vw_cf_return_general'),
('CFF', 'financing_net_cash', 1, 'vw_cf_return_general');

-- 第32栏：fx_impact
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第32栏', 'fx_impact', 3, 'vw_cf_return_general'),
('32栏', 'fx_impact', 3, 'vw_cf_return_general'),
('栏次32', 'fx_impact', 3, 'vw_cf_return_general'),
('汇率变动对现金及现金等价物的影响', 'fx_impact', 2, 'vw_cf_return_general'),
('汇率变动影响', 'fx_impact', 1, 'vw_cf_return_general'),
('汇兑损益影响', 'fx_impact', 1, 'vw_cf_return_general'),
('外币折算差额', 'fx_impact', 1, 'vw_cf_return_general');

-- 第33栏：net_increase_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第33栏', 'net_increase_cash', 3, 'vw_cf_return_general'),
('33栏', 'net_increase_cash', 3, 'vw_cf_return_general'),
('栏次33', 'net_increase_cash', 3, 'vw_cf_return_general'),
('现金及现金等价物净增加额', 'net_increase_cash', 2, 'vw_cf_return_general'),
('现金净增加额', 'net_increase_cash', 1, 'vw_cf_return_general'),
('现金增加额', 'net_increase_cash', 1, 'vw_cf_return_general');

-- 第34栏：beginning_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第34栏', 'beginning_cash', 3, 'vw_cf_return_general'),
('34栏', 'beginning_cash', 3, 'vw_cf_return_general'),
('栏次34', 'beginning_cash', 3, 'vw_cf_return_general'),
('期初现金及现金等价物余额', 'beginning_cash', 2, 'vw_cf_return_general'),
('期初现金余额', 'beginning_cash', 1, 'vw_cf_return_general'),
('期初现金', 'beginning_cash', 1, 'vw_cf_return_general'),
('年初现金', 'beginning_cash', 1, 'vw_cf_return_general');

-- 第35栏：ending_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第35栏', 'ending_cash', 3, 'vw_cf_return_general'),
('35栏', 'ending_cash', 3, 'vw_cf_return_general'),
('栏次35', 'ending_cash', 3, 'vw_cf_return_general'),
('期末现金及现金等价物余额', 'ending_cash', 2, 'vw_cf_return_general'),
('期末现金余额', 'ending_cash', 1, 'vw_cf_return_general'),
('期末现金', 'ending_cash', 1, 'vw_cf_return_general'),
('年末现金', 'ending_cash', 1, 'vw_cf_return_general');


-- ============================================
-- 小企业会计准则（vw_cf_return_small）同义词
-- ============================================

-- 第1栏：operating_receipts_sales
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第1栏', 'operating_receipts_sales', 3, 'vw_cf_return_small'),
('1栏', 'operating_receipts_sales', 3, 'vw_cf_return_small'),
('栏次1', 'operating_receipts_sales', 3, 'vw_cf_return_small'),
('销售产成品、商品、提供劳务收到的现金', 'operating_receipts_sales', 2, 'vw_cf_return_small'),
('销售商品收到的现金', 'operating_receipts_sales', 1, 'vw_cf_return_small'),
('销售产成品收到的现金', 'operating_receipts_sales', 1, 'vw_cf_return_small'),
('销售收现', 'operating_receipts_sales', 1, 'vw_cf_return_small'),
('商品销售收入现金', 'operating_receipts_sales', 1, 'vw_cf_return_small');

-- 第2栏：operating_receipts_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第2栏', 'operating_receipts_other', 3, 'vw_cf_return_small'),
('2栏', 'operating_receipts_other', 3, 'vw_cf_return_small'),
('栏次2', 'operating_receipts_other', 3, 'vw_cf_return_small'),
('收到其他与经营活动有关的现金', 'operating_receipts_other', 2, 'vw_cf_return_small'),
('其他经营现金流入', 'operating_receipts_other', 1, 'vw_cf_return_small'),
('经营其他收入', 'operating_receipts_other', 1, 'vw_cf_return_small'),
('政府补助收入', 'operating_receipts_other', 1, 'vw_cf_return_small');

-- 第3栏：operating_payments_purchase
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第3栏', 'operating_payments_purchase', 3, 'vw_cf_return_small'),
('3栏', 'operating_payments_purchase', 3, 'vw_cf_return_small'),
('栏次3', 'operating_payments_purchase', 3, 'vw_cf_return_small'),
('购买原材料、商品、接受劳务支付的现金', 'operating_payments_purchase', 2, 'vw_cf_return_small'),
('购买原材料支付的现金', 'operating_payments_purchase', 1, 'vw_cf_return_small'),
('购买商品支付的现金', 'operating_payments_purchase', 1, 'vw_cf_return_small'),
('采购付现', 'operating_payments_purchase', 1, 'vw_cf_return_small'),
('接受劳务支付的现金', 'operating_payments_purchase', 1, 'vw_cf_return_small');

-- 第4栏：operating_payments_staff
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第4栏', 'operating_payments_staff', 3, 'vw_cf_return_small'),
('4栏', 'operating_payments_staff', 3, 'vw_cf_return_small'),
('栏次4', 'operating_payments_staff', 3, 'vw_cf_return_small'),
('支付的职工薪酬', 'operating_payments_staff', 2, 'vw_cf_return_small'),
('支付职工薪酬', 'operating_payments_staff', 1, 'vw_cf_return_small'),
('职工薪酬支付', 'operating_payments_staff', 1, 'vw_cf_return_small'),
('工资支付', 'operating_payments_staff', 1, 'vw_cf_return_small');

-- 第5栏：operating_payments_tax
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第5栏', 'operating_payments_tax', 3, 'vw_cf_return_small'),
('5栏', 'operating_payments_tax', 3, 'vw_cf_return_small'),
('栏次5', 'operating_payments_tax', 3, 'vw_cf_return_small'),
('支付的税费', 'operating_payments_tax', 2, 'vw_cf_return_small'),
('支付税费', 'operating_payments_tax', 1, 'vw_cf_return_small'),
('缴纳税款', 'operating_payments_tax', 1, 'vw_cf_return_small');

-- 第6栏：operating_payments_other
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第6栏', 'operating_payments_other', 3, 'vw_cf_return_small'),
('6栏', 'operating_payments_other', 3, 'vw_cf_return_small'),
('栏次6', 'operating_payments_other', 3, 'vw_cf_return_small'),
('支付其他与经营活动有关的现金', 'operating_payments_other', 2, 'vw_cf_return_small'),
('其他经营现金流出', 'operating_payments_other', 1, 'vw_cf_return_small'),
('经营其他支出', 'operating_payments_other', 1, 'vw_cf_return_small'),
('付现费用', 'operating_payments_other', 1, 'vw_cf_return_small');

-- 第7栏：operating_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第7栏', 'operating_net_cash', 3, 'vw_cf_return_small'),
('7栏', 'operating_net_cash', 3, 'vw_cf_return_small'),
('栏次7', 'operating_net_cash', 3, 'vw_cf_return_small'),
('经营活动产生的现金流量净额', 'operating_net_cash', 2, 'vw_cf_return_small'),
('经营活动现金流量净额', 'operating_net_cash', 1, 'vw_cf_return_small'),
('经营净现金流', 'operating_net_cash', 1, 'vw_cf_return_small'),
('CFO', 'operating_net_cash', 1, 'vw_cf_return_small');

-- 第8栏：investing_receipts_disposal_investment
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第8栏', 'investing_receipts_disposal_investment', 3, 'vw_cf_return_small'),
('8栏', 'investing_receipts_disposal_investment', 3, 'vw_cf_return_small'),
('栏次8', 'investing_receipts_disposal_investment', 3, 'vw_cf_return_small'),
('收回短期投资、长期债券投资和长期股权投资收到的现金', 'investing_receipts_disposal_investment', 2, 'vw_cf_return_small'),
('收回投资收到的现金', 'investing_receipts_disposal_investment', 1, 'vw_cf_return_small'),
('收回短期投资现金', 'investing_receipts_disposal_investment', 1, 'vw_cf_return_small'),
('收回长期投资现金', 'investing_receipts_disposal_investment', 1, 'vw_cf_return_small'),
('投资收回', 'investing_receipts_disposal_investment', 1, 'vw_cf_return_small');

-- 第9栏：investing_receipts_returns
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第9栏', 'investing_receipts_returns', 3, 'vw_cf_return_small'),
('9栏', 'investing_receipts_returns', 3, 'vw_cf_return_small'),
('栏次9', 'investing_receipts_returns', 3, 'vw_cf_return_small'),
('取得投资收益收到的现金', 'investing_receipts_returns', 2, 'vw_cf_return_small'),
('投资收益现金', 'investing_receipts_returns', 1, 'vw_cf_return_small'),
('收到股利', 'investing_receipts_returns', 1, 'vw_cf_return_small'),
('收到利息', 'investing_receipts_returns', 1, 'vw_cf_return_small');

-- 第10栏：investing_receipts_disposal_assets
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第10栏', 'investing_receipts_disposal_assets', 3, 'vw_cf_return_small'),
('10栏', 'investing_receipts_disposal_assets', 3, 'vw_cf_return_small'),
('栏次10', 'investing_receipts_disposal_assets', 3, 'vw_cf_return_small'),
('处置固定资产、无形资产和其他非流动资产收回的现金净额', 'investing_receipts_disposal_assets', 2, 'vw_cf_return_small'),
('处置固定资产收回的现金', 'investing_receipts_disposal_assets', 1, 'vw_cf_return_small'),
('出售固定资产现金', 'investing_receipts_disposal_assets', 1, 'vw_cf_return_small'),
('处置无形资产现金', 'investing_receipts_disposal_assets', 1, 'vw_cf_return_small'),
('资产处置净额', 'investing_receipts_disposal_assets', 1, 'vw_cf_return_small');

-- 第11栏：investing_payments_purchase_investment
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第11栏', 'investing_payments_purchase_investment', 3, 'vw_cf_return_small'),
('11栏', 'investing_payments_purchase_investment', 3, 'vw_cf_return_small'),
('栏次11', 'investing_payments_purchase_investment', 3, 'vw_cf_return_small'),
('短期投资、长期债券投资和长期股权投资支付的现金', 'investing_payments_purchase_investment', 2, 'vw_cf_return_small'),
('投资支付的现金', 'investing_payments_purchase_investment', 1, 'vw_cf_return_small'),
('短期投资付现', 'investing_payments_purchase_investment', 1, 'vw_cf_return_small'),
('长期投资付现', 'investing_payments_purchase_investment', 1, 'vw_cf_return_small'),
('购买债券支付', 'investing_payments_purchase_investment', 1, 'vw_cf_return_small');

-- 第12栏：investing_payments_purchase_assets
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第12栏', 'investing_payments_purchase_assets', 3, 'vw_cf_return_small'),
('12栏', 'investing_payments_purchase_assets', 3, 'vw_cf_return_small'),
('栏次12', 'investing_payments_purchase_assets', 3, 'vw_cf_return_small'),
('购建固定资产、无形资产和其他非流动资产支付的现金', 'investing_payments_purchase_assets', 2, 'vw_cf_return_small'),
('购建固定资产支付的现金', 'investing_payments_purchase_assets', 1, 'vw_cf_return_small'),
('购买固定资产现金', 'investing_payments_purchase_assets', 1, 'vw_cf_return_small'),
('无形资产购置', 'investing_payments_purchase_assets', 1, 'vw_cf_return_small'),
('在建工程支出', 'investing_payments_purchase_assets', 1, 'vw_cf_return_small');

-- 第13栏：investing_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第13栏', 'investing_net_cash', 3, 'vw_cf_return_small'),
('13栏', 'investing_net_cash', 3, 'vw_cf_return_small'),
('栏次13', 'investing_net_cash', 3, 'vw_cf_return_small'),
('投资活动产生的现金流量净额', 'investing_net_cash', 2, 'vw_cf_return_small'),
('投资活动现金流量净额', 'investing_net_cash', 1, 'vw_cf_return_small'),
('投资净现金流', 'investing_net_cash', 1, 'vw_cf_return_small'),
('CFI', 'investing_net_cash', 1, 'vw_cf_return_small');

-- 第14栏：financing_receipts_borrowing
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第14栏', 'financing_receipts_borrowing', 3, 'vw_cf_return_small'),
('14栏', 'financing_receipts_borrowing', 3, 'vw_cf_return_small'),
('栏次14', 'financing_receipts_borrowing', 3, 'vw_cf_return_small'),
('取得借款收到的现金', 'financing_receipts_borrowing', 2, 'vw_cf_return_small'),
('借款收到的现金', 'financing_receipts_borrowing', 1, 'vw_cf_return_small'),
('银行贷款现金', 'financing_receipts_borrowing', 1, 'vw_cf_return_small');

-- 第15栏：financing_receipts_capital
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第15栏', 'financing_receipts_capital', 3, 'vw_cf_return_small'),
('15栏', 'financing_receipts_capital', 3, 'vw_cf_return_small'),
('栏次15', 'financing_receipts_capital', 3, 'vw_cf_return_small'),
('吸收投资者投资收到的现金', 'financing_receipts_capital', 2, 'vw_cf_return_small'),
('吸收投资收到的现金', 'financing_receipts_capital', 1, 'vw_cf_return_small'),
('接受投资现金', 'financing_receipts_capital', 1, 'vw_cf_return_small'),
('增资现金', 'financing_receipts_capital', 1, 'vw_cf_return_small');

-- 第16栏：financing_payments_debt_principal
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第16栏', 'financing_payments_debt_principal', 3, 'vw_cf_return_small'),
('16栏', 'financing_payments_debt_principal', 3, 'vw_cf_return_small'),
('栏次16', 'financing_payments_debt_principal', 3, 'vw_cf_return_small'),
('偿还借款本金支付的现金', 'financing_payments_debt_principal', 2, 'vw_cf_return_small'),
('偿还借款本金', 'financing_payments_debt_principal', 1, 'vw_cf_return_small'),
('还本付现', 'financing_payments_debt_principal', 1, 'vw_cf_return_small');

-- 第17栏：financing_payments_debt_interest
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第17栏', 'financing_payments_debt_interest', 3, 'vw_cf_return_small'),
('17栏', 'financing_payments_debt_interest', 3, 'vw_cf_return_small'),
('栏次17', 'financing_payments_debt_interest', 3, 'vw_cf_return_small'),
('偿还借款利息支付的现金', 'financing_payments_debt_interest', 2, 'vw_cf_return_small'),
('偿还借款利息', 'financing_payments_debt_interest', 1, 'vw_cf_return_small'),
('付息现金', 'financing_payments_debt_interest', 1, 'vw_cf_return_small');

-- 第18栏：financing_payments_dividend
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第18栏', 'financing_payments_dividend', 3, 'vw_cf_return_small'),
('18栏', 'financing_payments_dividend', 3, 'vw_cf_return_small'),
('栏次18', 'financing_payments_dividend', 3, 'vw_cf_return_small'),
('分配利润支付的现金', 'financing_payments_dividend', 2, 'vw_cf_return_small'),
('分配利润现金', 'financing_payments_dividend', 1, 'vw_cf_return_small'),
('支付股利', 'financing_payments_dividend', 1, 'vw_cf_return_small'),
('分红付现', 'financing_payments_dividend', 1, 'vw_cf_return_small');

-- 第19栏：financing_net_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第19栏', 'financing_net_cash', 3, 'vw_cf_return_small'),
('19栏', 'financing_net_cash', 3, 'vw_cf_return_small'),
('栏次19', 'financing_net_cash', 3, 'vw_cf_return_small'),
('筹资活动产生的现金流量净额', 'financing_net_cash', 2, 'vw_cf_return_small'),
('筹资活动现金流量净额', 'financing_net_cash', 1, 'vw_cf_return_small'),
('筹资净现金流', 'financing_net_cash', 1, 'vw_cf_return_small'),
('CFF', 'financing_net_cash', 1, 'vw_cf_return_small');

-- 第20栏：net_increase_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第20栏', 'net_increase_cash', 3, 'vw_cf_return_small'),
('20栏', 'net_increase_cash', 3, 'vw_cf_return_small'),
('栏次20', 'net_increase_cash', 3, 'vw_cf_return_small'),
('现金净增加额', 'net_increase_cash', 2, 'vw_cf_return_small'),
('现金增加额', 'net_increase_cash', 1, 'vw_cf_return_small');

-- 第21栏：beginning_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第21栏', 'beginning_cash', 3, 'vw_cf_return_small'),
('21栏', 'beginning_cash', 3, 'vw_cf_return_small'),
('栏次21', 'beginning_cash', 3, 'vw_cf_return_small'),
('期初现金余额', 'beginning_cash', 2, 'vw_cf_return_small'),
('期初现金', 'beginning_cash', 1, 'vw_cf_return_small'),
('年初现金', 'beginning_cash', 1, 'vw_cf_return_small');

-- 第22栏：ending_cash
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('第22栏', 'ending_cash', 3, 'vw_cf_return_small'),
('22栏', 'ending_cash', 3, 'vw_cf_return_small'),
('栏次22', 'ending_cash', 3, 'vw_cf_return_small'),
('期末现金余额', 'ending_cash', 2, 'vw_cf_return_small'),
('期末现金', 'ending_cash', 1, 'vw_cf_return_small'),
('年末现金', 'ending_cash', 1, 'vw_cf_return_small');


-- ============================================
-- 通用同义词（适用于两个视图，字段名相同）
-- ============================================
-- 注意：以下字段在两个视图中字段名一致，可设置 scope_view=NULL 使其通用
-- 但为确保万无一失，也可分别插入两个视图记录；这里提供通用方式。

-- 经营活动现金流量净额（operating_net_cash）已分别在两个视图插入，这里不再重复

-- 现金净增加额（net_increase_cash）企业会计准则字段名相同，但小企业会计准则也是 net_increase_cash，但含义略有差别，可通用。
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('现金净增加额', 'net_increase_cash', 2, NULL),
('现金增加额', 'net_increase_cash', 1, NULL);

-- 期初现金余额（beginning_cash）企业会计准则字段为 beginning_cash，小企业会计准则也是 beginning_cash，但企业会计准则带“等价物”，可通用。
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('期初现金余额', 'beginning_cash', 2, NULL),
('期初现金', 'beginning_cash', 1, NULL);

-- 期末现金余额（ending_cash）
INSERT OR IGNORE INTO fs_cf_synonyms (phrase, column_name, priority, scope_view) VALUES
('期末现金余额', 'ending_cash', 2, NULL),
('期末现金', 'ending_cash', 1, NULL);
```

---

## 4.6 分准则视图（NL2SQL 入口）  

### 4.6.1 企业会计准则视图（`vw_cf_return_general`）  

```sql
CREATE VIEW vw_cf_return_general AS
SELECT
    g.taxpayer_id,
    t.taxpayer_name,
    g.period_year,
    g.period_month,
    g.time_range,
    t.taxpayer_type,
    t.accounting_standard,
    g.revision_no,
    g.submitted_at,
    g.etl_batch_id,
    g.source_doc_id,
    g.source_unit,
    g.etl_confidence,
    -- 35个指标
    g.operating_inflow_sales,
    g.operating_inflow_tax_refund,
    g.operating_inflow_other,
    g.operating_inflow_subtotal,
    g.operating_outflow_purchase,
    g.operating_outflow_labor,
    g.operating_outflow_tax,
    g.operating_outflow_other,
    g.operating_outflow_subtotal,
    g.operating_net_cash,
    g.investing_inflow_sale_investment,
    g.investing_inflow_returns,
    g.investing_inflow_disposal_assets,
    g.investing_inflow_disposal_subsidiary,
    g.investing_inflow_other,
    g.investing_inflow_subtotal,
    g.investing_outflow_purchase_assets,
    g.investing_outflow_purchase_investment,
    g.investing_outflow_acquire_subsidiary,
    g.investing_outflow_other,
    g.investing_outflow_subtotal,
    g.investing_net_cash,
    g.financing_inflow_capital,
    g.financing_inflow_borrowing,
    g.financing_inflow_other,
    g.financing_inflow_subtotal,
    g.financing_outflow_debt_repayment,
    g.financing_outflow_dividend_interest,
    g.financing_outflow_other,
    g.financing_outflow_subtotal,
    g.financing_net_cash,
    g.fx_impact,
    g.net_increase_cash,
    g.beginning_cash,
    g.ending_cash
FROM cf_return_general g
JOIN taxpayer_info t ON g.taxpayer_id = t.taxpayer_id
WHERE t.accounting_standard = '企业会计准则';
```

### 4.6.2 小企业会计准则视图（`vw_cf_return_small`）  

```sql
CREATE VIEW vw_cf_return_small AS
SELECT
    s.taxpayer_id,
    t.taxpayer_name,
    s.period_year,
    s.period_month,
    s.time_range,
    t.taxpayer_type,
    t.accounting_standard,
    s.revision_no,
    s.submitted_at,
    s.etl_batch_id,
    s.source_doc_id,
    s.source_unit,
    s.etl_confidence,
    -- 22个指标
    s.operating_receipts_sales,
    s.operating_receipts_other,
    s.operating_payments_purchase,
    s.operating_payments_staff,
    s.operating_payments_tax,
    s.operating_payments_other,
    s.operating_net_cash,
    s.investing_receipts_disposal_investment,
    s.investing_receipts_returns,
    s.investing_receipts_disposal_assets,
    s.investing_payments_purchase_investment,
    s.investing_payments_purchase_assets,
    s.investing_net_cash,
    s.financing_receipts_borrowing,
    s.financing_receipts_capital,
    s.financing_payments_debt_principal,
    s.financing_payments_debt_interest,
    s.financing_payments_dividend,
    s.financing_net_cash,
    s.net_increase_cash,
    s.beginning_cash,
    s.ending_cash
FROM cf_return_small s
JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id
WHERE t.accounting_standard = '小企业会计准则';
```

> **跨准则对比**：可通过 UNION ALL 分别从两个视图查询后按指标语义对齐（例如“经营活动现金流量净额”在两个视图中字段名相同，可直接 UNION）。  

---

## 4.7 用户查询日志表 & 未匹配短语表  

完全复用增值税方案中的 `user_query_log` 和 `unmatched_phrases` 表结构，仅需将表名前缀改为 `cf_` 或统一使用一套日志表（建议统一使用一套，通过 `domain` 字段区分）。  

```sql
-- 统一查询日志表（增加 domain 字段）
CREATE TABLE user_query_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT,
    domain            TEXT,                          -- 'vat', 'cf', 'eit', ...
    user_query        TEXT NOT NULL,
    normalized_query  TEXT,
    taxpayer_id       TEXT,
    taxpayer_name     TEXT,
    period_year       INTEGER,
    period_month      INTEGER,
    success           INTEGER DEFAULT 0,
    error_message     TEXT,
    generated_sql     TEXT,
    execution_time_ms INTEGER,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_ip           TEXT,
    user_agent        TEXT
);

-- 未匹配短语表（复用）
CREATE TABLE unmatched_phrases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase          TEXT NOT NULL,
    context_query   TEXT,
    frequency       INTEGER DEFAULT 1,
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'pending',
    suggested_column TEXT,
    suggested_priority INTEGER DEFAULT 2,
    remarks         TEXT,
    processed_by    TEXT,
    processed_at    TIMESTAMP
);
```

---

## 5. ETL 流程设计  

### 5.1 输入解析  
- 识别报表类型（企业会计准则/小企业会计准则）、纳税人识别号、所属期（年、月）。  
- 提取二维表格：行 = 行次，列 = “本年累计金额”和“本期金额”。  

### 5.2 行列转换  
```python
# 伪代码
for 行次号, 本年累计值, 本期值 in 每行数据:
    field_name = mapping[行次号]['column_name']   # 从映射表获取
    key = (taxpayer_id, period_year, period_month, '本年累计')
    rows_dict[key][field_name] = 本年累计值
    key = (taxpayer_id, period_year, period_month, '本期')
    rows_dict[key][field_name] = 本期值
```

### 5.3 写入明细表  
使用 `INSERT OR REPLACE` 按主键批量 upsert，索引预先建立。  

### 5.4 质量校验与错误日志  
可参照增值税方案增加 `etl_error_log` 表记录解析异常。  

---

## 6. NL2SQL 应用流程（两阶段受控生成）  

完全沿用增值税方案的两阶段设计，仅将域（domain）定义为 `cf`，并针对现金流量表设计意图解析 JSON 和 Prompt。  

### 6.1 实体识别与同义词标准化  
- 优先识别纳税人、期次、会计准则类型（可通过 `accounting_standard` 确定路由视图）。  
- 同义词替换采用“最长匹配优先 + 不重叠替换”，并根据识别出的 `scope_view` 过滤同义词。  

### 6.2 阶段1：意图解析（输出 JSON）  

```json
{
  "domain": "cf",
  "cf_scope": {
    "accounting_standard_hint": "企业会计准则|小企业会计准则|unknown",
    "views": ["vw_cf_return_general"],
    "cross_standard_union": false
  },
  "select": {
    "metrics": ["operating_net_cash"],
    "dimensions": ["period_year", "period_month"]
  },
  "filters": {
    "taxpayer_id": ":taxpayer_id",
    "period_mode": "month|year|range_month",
    "period": {
      "year": ":year",
      "month": ":month",
      "start_yyyymm": ":start_yyyymm",
      "end_yyyymm": ":end_yyyymm"
    },
    "time_range": "本期|本年累计|null",
    "revision_strategy": "latest|specific",
    "revision_no": ":revision_no"
  },
  "aggregation": {
    "group_by": ["period_year", "period_month"],
    "order_by": [{"column": "period_year", "dir": "ASC"}, {"column": "period_month", "dir": "ASC"}],
    "limit": 1000
  },
  "need_clarification": false,
  "clarifying_questions": []
}
```

### 6.3 阶段2：SQL 生成（动态 Schema 注入）  

- 根据阶段1 JSON 确定允许的视图和字段集合。  
- 强制包含 `taxpayer_id = :taxpayer_id` 和期间过滤。  
- 默认取最新版本（`revision_strategy=latest`），需在 SQL 中实现窗口函数取最大 revision_no。  

**示例 SQL（企业会计准则，查询某月经营活动现金流量净额）**  

```sql
WITH ranked AS (
  SELECT
    period_year, period_month, time_range, operating_net_cash,
    ROW_NUMBER() OVER (
      PARTITION BY taxpayer_id, period_year, period_month, time_range
      ORDER BY revision_no DESC
    ) AS rn
  FROM vw_cf_return_general
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year
    AND period_month = :month
    AND time_range = '本期'
)
SELECT period_year, period_month, operating_net_cash
FROM ranked
WHERE rn = 1
LIMIT 1;
```

### 6.4 SQL 审核器规则  

参照增值税方案，增加对现金流量表视图的白名单检查、必含 taxpayer_id 和期间过滤、禁止 `SELECT *`、禁止危险语句等。  

---

## 7. 方案对比分析  

| 对比维度 | **本方案（分准则视图 + 明细表 + 两阶段生成）** | **宽表（70列）** | **全纵表（一行一次）** |
|----------|-----------------------------------------------|------------------|------------------------|
| **存储效率** | ⭐⭐⭐⭐⭐（每期2行，35/22列，无空值） | ⭐⭐（70列，稀疏度低但列多） | ⭐⭐⭐⭐⭐（每期最多44行，但指标仅一列） |
| **NL2SQL 字段选择** | ⭐⭐⭐⭐⭐（视图降噪，字段语义明确） | ⭐⭐（列过多易选错） | ⭐⭐（需动态透视） |
| **跨准则对比** | ⭐⭐⭐⭐（UNION ALL 对齐口径） | ⭐⭐（需两表分别查询） | ⭐⭐（需分别聚合再 UNION） |
| **ETL 维护** | ⭐⭐⭐⭐（行列转换清晰） | ⭐⭐⭐（直接映射） | ⭐⭐（需 UNPIVOT） |
| **大模型准确率** | **≥95%** | 80~85% | ≤70% |

---

## 8. 总结与扩展建议  

本方案提供：  
- ✅ 两张明细表（企业会计准则/小企业会计准则）DDL  
- ✅ 纳税人信息表（含会计准则标识）  
- ✅ 两张栏次映射表及数据  
- ✅ 同义词表（支持分视图过滤）  
- ✅ 两个查询视图：`vw_cf_return_general`、`vw_cf_return_small`  
- ✅ 两阶段受控生成流程（意图解析 + 动态 Schema 注入）  
- ✅ SQL 审核器规则  

**扩展建议**：  
1. **现金流量表附注**：可复用相同模式，将附注项目作为独立明细表，建立映射表和视图。  
2. **快照表**：按月度对企业属性（行业、信用等级等）做快照，便于历史归因分析。  
3. **跨域对账**：当用户同时问及现金流量表与资产负债表（如“期末现金余额”与“货币资金”差异）时，启用跨域编排（cross_domain）。  
4. **审核器升级**：从正则匹配逐步迁移至 `sqlglot` AST 校验，增强安全性与灵活性。  

---

**附录**：略（ETL 错误日志表等可参照资产负债表、利润表方案）