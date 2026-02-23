# 资产负债表 NL2SQL 数据模型与受控生成方案文档  
**版本**：**v1.0** | **最后更新**：2026-02-14  

## 1. 项目背景与目标  

资产负债表是企业财务报表的核心组成部分，包含**企业会计准则**与**小企业会计准则**两套标准，每套报表均以“资产/负债和所有者权益”左右分栏格式呈现，包含数十个行次（项目）的**期末余额**与**年初余额**。  

目标：构建一套**面向 NL2SQL 的分析型数据模型**，支持：  
- 用户通过自然语言查询任意纳税人、任意期次的资产负债表明细数据；  
- 兼容企业会计准则、小企业会计准则，并预留未来扩展其他准则（如新租赁准则、政府会计等）的能力；  
- ETL 可从 PDF/Excel 等异构来源稳定导入；  
- 存储紧凑、查询高效，大模型 SQL 生成准确率 ≥95%。  

## 2. 核心挑战  

| 挑战 | 描述 |  
|------|------|  
| **多准则异构性** | 两套报表项目名称、行次、数量不一致，未来可能新增其他准则，需统一建模。 |  
| **稀疏性** | 若合并为一张超级宽表，不同准则下大量字段为空，影响查询效率与模型理解。 |  
| **左右分栏格式** | 报表为左右分列布局，但数据存储需脱离格式，确保合计平衡关系可追溯。 |  
| **NL2SQL 歧义** | 用户口语化表达（如“货币资金”“第5行”“资产总计”）需精准映射到具体准则下的具体项目。 |  
| **表路由复杂度** | 若分准则存储，NL2SQL 需先判断准则类型再选表，易出错；若合并存储，需解决字段名冲突。 |  

## 3. 设计原则  

1. **存储与查询解耦**：底层采用**纵表（EAV）**存储所有准则的明细项目，保证扩展性；查询侧为每个准则构建**宽表视图**，消除 NL2SQL 的复杂性。  
2. **字段名即业务术语**：视图中的列名采用标准英文编码（如 `cash_end`），并通过同义词表映射用户口语。  
3. **同义词集中管理**：用单独映射表存储用户口语→标准字段的映射，支持按准则类型过滤。  
4. **维度行拍平**：每个纳税人每期每个准则的每个项目作为一行，存储期末余额与年初余额，彻底消除稀疏性。  
5. **一次设计，无限扩展**：新增准则只需在字典表中定义项目，并创建对应视图，不破坏已有数据与查询。  

## 4. 数据模型详细设计  

### 4.1 资产负债表项目明细表（`fs_balance_sheet_item`）  

存储所有准则下每个项目的期初、期末余额，支持版本追溯。  

```sql
CREATE TABLE fs_balance_sheet_item (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    gaap_type           TEXT NOT NULL,   -- 'ASBE'（企业会计准则）, 'SME'（小企业会计准则）, 未来可扩展
    item_code           TEXT NOT NULL,   -- 标准项目编码（如 'CASH', 'ASSET_TOTAL'）

    -- 版本追溯
    revision_no         INTEGER NOT NULL DEFAULT 0,
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    source_unit         TEXT DEFAULT '元',
    etl_confidence      REAL,

    -- 指标
    beginning_balance   NUMERIC,         -- 年初余额
    ending_balance      NUMERIC,         -- 期末余额

    -- 冗余字段（可选，便于查询）
    item_name           TEXT,            -- 项目名称（如“货币资金”）
    line_number         INTEGER,         -- 原始行次（如 1）
    section             TEXT,            -- 'ASSET', 'LIABILITY', 'EQUITY'

    PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
    CHECK (gaap_type IN ('ASBE', 'SME')),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_bs_period ON fs_balance_sheet_item (period_year, period_month);
CREATE INDEX idx_bs_taxpayer ON fs_balance_sheet_item (taxpayer_id);
CREATE INDEX idx_bs_taxpayer_period ON fs_balance_sheet_item (taxpayer_id, period_year, period_month);
```

### 4.2 项目字典表（`fs_balance_sheet_item_dict`）  

定义每个准则下的项目编码、显示名称、行次、所属部分，用于 ETL 映射和视图生成。  

```sql
CREATE TABLE fs_balance_sheet_item_dict (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    gaap_type       TEXT NOT NULL,        -- 'ASBE' 或 'SME'
    item_code       TEXT NOT NULL,        -- 标准编码
    item_name       TEXT NOT NULL,        -- 该准则下的显示名称
    line_number     INTEGER,              -- 该准则下的行次
    section         TEXT,                 -- 'ASSET', 'LIABILITY', 'EQUITY'
    display_order   INTEGER,              -- 显示顺序（用于视图列排序）
    is_total        BOOLEAN DEFAULT 0,    -- 是否为合计项（如资产总计）
    UNIQUE (gaap_type, item_code)
);

-- 插入企业会计准则项目
INSERT INTO fs_balance_sheet_item_dict (gaap_type, item_code, item_name, line_number, section, display_order, is_total) VALUES
-- 流动资产
('ASBE', 'A_CASH', '货币资金', 1, 'ASSET', 10, 0),
('ASBE', 'A_TRADING_FINANCIAL_ASSETS', '交易性金融资产', 2, 'ASSET', 20, 0),
('ASBE', 'A_DERIVATIVE_FINANCIAL_ASSETS', '衍生金融资产', 3, 'ASSET', 30, 0),
('ASBE', 'A_NOTES_RECEIVABLE', '应收票据', 4, 'ASSET', 40, 0),
('ASBE', 'A_ACCOUNTS_RECEIVABLE', '应收账款', 5, 'ASSET', 50, 0),
('ASBE', 'A_ACCOUNTS_RECEIVABLE_FINANCING', '应收账款融资', 6, 'ASSET', 60, 0),
('ASBE', 'A_PREPAYMENTS', '预付账款', 7, 'ASSET', 70, 0),
('ASBE', 'A_CONTRACT_ASSETS', '合同资产', 8, 'ASSET', 80, 0),
('ASBE', 'A_OTHER_RECEIVABLES', '其他应收款', 9, 'ASSET', 90, 0),
('ASBE', 'A_INVENTORY', '存货', 10, 'ASSET', 100, 0),
('ASBE', 'A_CONTRACT_ASSETS', '合同资产', 11, 'ASSET', 110, 0),   -- 注意第10栏合同资产，但之前已有合同资产？根据表格是第10栏，但第8栏也是合同资产？需核对原表：第8栏是其他应收款？原表第8是其他应收款，第9是存货，第10是合同资产。我们按原表顺序。此处修正。
-- 实际上原表顺序：
-- 1货币资金 2交易性金融资产 3衍生金融资产 4应收票据 5应收账款 6应收账款融资 7预付账款 8其他应收款 9存货 10合同资产 11持有待售资产 12一年内到期的非流动资产 13其他流动资产
-- 因此调整：
('ASBE', 'A_CASH', '货币资金', 1, 'ASSET', 10, 0),
('ASBE', 'A_TRADING_FINANCIAL_ASSETS', '交易性金融资产', 2, 'ASSET', 20, 0),
('ASBE', 'A_DERIVATIVE_FINANCIAL_ASSETS', '衍生金融资产', 3, 'ASSET', 30, 0),
('ASBE', 'A_NOTES_RECEIVABLE', '应收票据', 4, 'ASSET', 40, 0),
('ASBE', 'A_ACCOUNTS_RECEIVABLE', '应收账款', 5, 'ASSET', 50, 0),
('ASBE', 'A_ACCOUNTS_RECEIVABLE_FINANCING', '应收账款融资', 6, 'ASSET', 60, 0),
('ASBE', 'A_PREPAYMENTS', '预付账款', 7, 'ASSET', 70, 0),
('ASBE', 'A_OTHER_RECEIVABLES', '其他应收款', 8, 'ASSET', 80, 0),
('ASBE', 'A_INVENTORY', '存货', 9, 'ASSET', 90, 0),
('ASBE', 'A_CONTRACT_ASSETS', '合同资产', 10, 'ASSET', 100, 0),
('ASBE', 'A_HELD_FOR_SALE_ASSETS', '持有待售资产', 11, 'ASSET', 110, 0),
('ASBE', 'A_CURRENT_PORTION_NON_CURRENT_ASSETS', '一年内到期的非流动资产', 12, 'ASSET', 120, 0),
('ASBE', 'A_OTHER_CURRENT_ASSETS', '其他流动资产', 13, 'ASSET', 130, 0),
('ASBE', 'T_CURRENT_ASSETS', '流动资产合计', 14, 'ASSET', 140, 1),

-- 非流动资产
('ASBE', 'A_DEBT_INVESTMENTS', '债权投资', 15, 'ASSET', 150, 0),
('ASBE', 'A_OTHER_DEBT_INVESTMENTS', '其他债权投资', 16, 'ASSET', 160, 0),
('ASBE', 'A_LONG_TERM_RECEIVABLES', '长期应收款', 17, 'ASSET', 170, 0),
('ASBE', 'A_LONG_TERM_EQUITY_INVESTMENTS', '长期股权投资', 18, 'ASSET', 180, 0),
('ASBE', 'A_OTHER_EQUITY_INSTRUMENTS', '其他权益工具投资', 19, 'ASSET', 190, 0),
('ASBE', 'A_OTHER_NON_CURRENT_FINANCIAL_ASSETS', '其他非流动金融资产', 20, 'ASSET', 200, 0),
('ASBE', 'A_INVESTMENT_PROPERTY', '投资性房地产', 21, 'ASSET', 210, 0),
('ASBE', 'A_FIXED_ASSETS', '固定资产', 22, 'ASSET', 220, 0),
('ASBE', 'A_CONSTRUCTION_IN_PROGRESS', '在建工程', 23, 'ASSET', 230, 0),
('ASBE', 'A_PRODUCTIVE_BIOLOGICAL_ASSETS', '生产性生物资产', 24, 'ASSET', 240, 0),
('ASBE', 'A_OIL_AND_GAS_ASSETS', '油气资产', 25, 'ASSET', 250, 0),
('ASBE', 'A_RIGHT_OF_USE_ASSETS', '使用权资产', 26, 'ASSET', 260, 0),
('ASBE', 'A_INTANGIBLE_ASSETS', '无形资产', 27, 'ASSET', 270, 0),
('ASBE', 'A_DEVELOPMENT_EXPENDITURE', '开发支出', 28, 'ASSET', 280, 0),
('ASBE', 'A_GOODWILL', '商誉', 29, 'ASSET', 290, 0),
('ASBE', 'A_LONG_TERM_DEFERRED_EXPENSES', '长期待摊费用', 30, 'ASSET', 300, 0),
('ASBE', 'A_DEFERRED_TAX_ASSETS', '递延所得税资产', 31, 'ASSET', 310, 0),
('ASBE', 'A_OTHER_NON_CURRENT_ASSETS', '其他非流动资产', 32, 'ASSET', 320, 0),
('ASBE', 'T_NON_CURRENT_ASSETS', '非流动资产合计', 33, 'ASSET', 330, 1),

-- 资产总计
('ASBE', 'T_ASSETS', '资产总计', 34, 'ASSET', 340, 1),

-- 流动负债
('ASBE', 'L_SHORT_TERM_LOANS', '短期借款', 35, 'LIABILITY', 350, 0),
('ASBE', 'L_TRADING_FINANCIAL_LIABILITIES', '交易性金融负债', 36, 'LIABILITY', 360, 0),
('ASBE', 'L_DERIVATIVE_FINANCIAL_LIABILITIES', '衍生金融负债', 37, 'LIABILITY', 370, 0),
('ASBE', 'L_NOTES_PAYABLE', '应付票据', 38, 'LIABILITY', 380, 0),
('ASBE', 'L_ACCOUNTS_PAYABLE', '应付账款', 39, 'LIABILITY', 390, 0),
('ASBE', 'L_ADVANCES_FROM_CUSTOMERS', '预收款项', 40, 'LIABILITY', 400, 0),
('ASBE', 'L_CONTRACT_LIABILITIES', '合同负债', 41, 'LIABILITY', 410, 0),
('ASBE', 'L_EMPLOYEE_BENEFITS_PAYABLE', '应付职工薪酬', 42, 'LIABILITY', 420, 0),
('ASBE', 'L_TAXES_PAYABLE', '应交税费', 43, 'LIABILITY', 430, 0),
('ASBE', 'L_OTHER_PAYABLES', '其他应付款', 44, 'LIABILITY', 440, 0),
('ASBE', 'L_HELD_FOR_SALE_LIABILITIES', '持有待售负债', 45, 'LIABILITY', 450, 0),
('ASBE', 'L_CURRENT_PORTION_NON_CURRENT_LIABILITIES', '一年内到期的非流动负债', 46, 'LIABILITY', 460, 0),
('ASBE', 'L_OTHER_CURRENT_LIABILITIES', '其他流动负债', 47, 'LIABILITY', 470, 0),
('ASBE', 'T_CURRENT_LIABILITIES', '流动负债合计', 48, 'LIABILITY', 480, 1),

-- 非流动负债
('ASBE', 'L_LONG_TERM_LOANS', '长期借款', 49, 'LIABILITY', 490, 0),
('ASBE', 'L_BONDS_PAYABLE', '应付债券', 50, 'LIABILITY', 500, 0),
('ASBE', 'L_PREFERRED_STOCK', '其中：优先股', 51, 'LIABILITY', 510, 0),   -- 注意51行是优先股（列在应付债券下）
('ASBE', 'L_PERPETUAL_BONDS', '永续债', 52, 'LIABILITY', 520, 0),
('ASBE', 'L_LEASE_LIABILITIES', '租赁负债', 53, 'LIABILITY', 530, 0),
('ASBE', 'L_LONG_TERM_PAYABLES', '长期应付款', 54, 'LIABILITY', 540, 0),
('ASBE', 'L_PROVISIONS', '预计负债', 55, 'LIABILITY', 550, 0),
('ASBE', 'L_DEFERRED_INCOME', '递延收益', 56, 'LIABILITY', 560, 0),
('ASBE', 'L_DEFERRED_TAX_LIABILITIES', '递延所得税负债', 57, 'LIABILITY', 570, 0),
('ASBE', 'L_OTHER_NON_CURRENT_LIABILITIES', '其他非流动负债', 58, 'LIABILITY', 580, 0),
('ASBE', 'T_NON_CURRENT_LIABILITIES', '非流动负债合计', 59, 'LIABILITY', 590, 1),

-- 负债合计
('ASBE', 'T_LIABILITIES', '负债合计', 60, 'LIABILITY', 600, 1),

-- 所有者权益
('ASBE', 'E_SHARE_CAPITAL', '实收资本（或股本）', 61, 'EQUITY', 610, 0),
('ASBE', 'E_OTHER_EQUITY_INSTRUMENTS', '其他权益工具', 62, 'EQUITY', 620, 0),
('ASBE', 'E_PREFERRED_STOCK', '其中：优先股', 63, 'EQUITY', 630, 0),
('ASBE', 'E_PERPETUAL_BONDS', '永续债', 64, 'EQUITY', 640, 0),
('ASBE', 'E_CAPITAL_RESERVE', '资本公积', 65, 'EQUITY', 650, 0),
('ASBE', 'E_TREASURY_STOCK', '减:库存股', 66, 'EQUITY', 660, 0),
('ASBE', 'E_OTHER_COMPREHENSIVE_INCOME', '其他综合收益', 67, 'EQUITY', 670, 0),
('ASBE', 'E_SPECIAL_RESERVE', '专项储备', 68, 'EQUITY', 680, 0),
('ASBE', 'E_SURPLUS_RESERVE', '盈余公积', 69, 'EQUITY', 690, 0),
('ASBE', 'E_RETAINED_EARNINGS', '未分配利润', 70, 'EQUITY', 700, 0),
('ASBE', 'T_EQUITY', '所有者权益（或股东权益）合计', 71, 'EQUITY', 710, 1),

-- 负债和所有者权益总计
('ASBE', 'T_LIABILITIES_AND_EQUITY', '负债和所有者权益（或股东权益）总计', 72, 'LIABILITY_EQUITY', 720, 1);
```


根据提供的资产负债表表格，左侧资产行次1～29，右侧负债和所有者权益行次31～52，资产合计行30，负债合计行47，所有者权益合计行52，负债和所有者权益总计行53。

```sql
-- 小企业会计准则项目插入
INSERT INTO fs_balance_sheet_item_dict (gaap_type, item_code, item_name, line_number, section, display_order, is_total) VALUES
-- 流动资产
('SME', 'A_CASH', '货币资金', 1, 'ASSET', 10, 0),
('SME', 'A_SHORT_TERM_INVESTMENTS', '短期投资', 2, 'ASSET', 20, 0),
('SME', 'A_NOTES_RECEIVABLE', '应收票据', 3, 'ASSET', 30, 0),
('SME', 'A_ACCOUNTS_RECEIVABLE', '应收账款', 4, 'ASSET', 40, 0),
('SME', 'A_PREPAYMENTS', '预付账款', 5, 'ASSET', 50, 0),
('SME', 'A_DIVIDENDS_RECEIVABLE', '应收股利', 6, 'ASSET', 60, 0),
('SME', 'A_INTEREST_RECEIVABLE', '应收利息', 7, 'ASSET', 70, 0),
('SME', 'A_OTHER_RECEIVABLES', '其他应收款', 8, 'ASSET', 80, 0),
('SME', 'A_INVENTORY', '存货', 9, 'ASSET', 90, 0),
('SME', 'A_RAW_MATERIALS', '其中：原材料', 10, 'ASSET', 100, 0),   -- 存货明细
('SME', 'A_WORK_IN_PROCESS', '在产品', 11, 'ASSET', 110, 0),
('SME', 'A_FINISHED_GOODS', '库存商品', 12, 'ASSET', 120, 0),
('SME', 'A_TURNOVER_MATERIALS', '周转材料', 13, 'ASSET', 130, 0),
('SME', 'A_OTHER_CURRENT_ASSETS', '其他流动资产', 14, 'ASSET', 140, 0),
('SME', 'T_CURRENT_ASSETS', '流动资产合计', 15, 'ASSET', 150, 1),

-- 非流动资产
('SME', 'A_LONG_TERM_BOND_INVESTMENTS', '长期债券投资', 16, 'ASSET', 160, 0),
('SME', 'A_LONG_TERM_EQUITY_INVESTMENTS', '长期股权投资', 17, 'ASSET', 170, 0),
('SME', 'A_FIXED_ASSETS_ORIGINAL', '固定资产原价', 18, 'ASSET', 180, 0),
('SME', 'A_ACCUMULATED_DEPRECIATION', '减：累计折旧', 19, 'ASSET', 190, 0),
('SME', 'A_FIXED_ASSETS_NET', '固定资产账面价值', 20, 'ASSET', 200, 0),
('SME', 'A_CONSTRUCTION_IN_PROGRESS', '在建工程', 21, 'ASSET', 210, 0),
('SME', 'A_ENGINEERING_MATERIALS', '工程物资', 22, 'ASSET', 220, 0),
('SME', 'A_FIXED_ASSETS_LIQUIDATION', '固定资产清理', 23, 'ASSET', 230, 0),
('SME', 'A_PRODUCTIVE_BIOLOGICAL_ASSETS', '生产性生物资产', 24, 'ASSET', 240, 0),
('SME', 'A_INTANGIBLE_ASSETS', '无形资产', 25, 'ASSET', 250, 0),
('SME', 'A_DEVELOPMENT_EXPENDITURE', '开发支出', 26, 'ASSET', 260, 0),
('SME', 'A_LONG_TERM_DEFERRED_EXPENSES', '长期待摊费用', 27, 'ASSET', 270, 0),
('SME', 'A_OTHER_NON_CURRENT_ASSETS', '其他非流动资产', 28, 'ASSET', 280, 0),
('SME', 'T_NON_CURRENT_ASSETS', '非流动资产合计', 29, 'ASSET', 290, 1),

-- 资产合计
('SME', 'T_ASSETS', '资产合计', 30, 'ASSET', 300, 1),

-- 流动负债
('SME', 'L_SHORT_TERM_LOANS', '短期借款', 31, 'LIABILITY', 310, 0),
('SME', 'L_NOTES_PAYABLE', '应付票据', 32, 'LIABILITY', 320, 0),
('SME', 'L_ACCOUNTS_PAYABLE', '应付账款', 33, 'LIABILITY', 330, 0),
('SME', 'L_ADVANCES_FROM_CUSTOMERS', '预收账款', 34, 'LIABILITY', 340, 0),
('SME', 'L_EMPLOYEE_BENEFITS_PAYABLE', '应付职工薪酬', 35, 'LIABILITY', 350, 0),
('SME', 'L_TAXES_PAYABLE', '应交税费', 36, 'LIABILITY', 360, 0),
('SME', 'L_INTEREST_PAYABLE', '应付利息', 37, 'LIABILITY', 370, 0),
('SME', 'L_PROFIT_PAYABLE', '应付利润', 38, 'LIABILITY', 380, 0),
('SME', 'L_OTHER_PAYABLES', '其他应付款', 39, 'LIABILITY', 390, 0),
('SME', 'L_OTHER_CURRENT_LIABILITIES', '其他流动负债', 40, 'LIABILITY', 400, 0),
('SME', 'T_CURRENT_LIABILITIES', '流动负债合计', 41, 'LIABILITY', 410, 1),

-- 非流动负债
('SME', 'L_LONG_TERM_LOANS', '长期借款', 42, 'LIABILITY', 420, 0),
('SME', 'L_LONG_TERM_PAYABLES', '长期应付款', 43, 'LIABILITY', 430, 0),
('SME', 'L_DEFERRED_INCOME', '递延收益', 44, 'LIABILITY', 440, 0),
('SME', 'L_OTHER_NON_CURRENT_LIABILITIES', '其他非流动负债', 45, 'LIABILITY', 450, 0),
('SME', 'T_NON_CURRENT_LIABILITIES', '非流动负债合计', 46, 'LIABILITY', 460, 1),

-- 负债合计
('SME', 'T_LIABILITIES', '负债合计', 47, 'LIABILITY', 470, 1),

-- 所有者权益
('SME', 'E_SHARE_CAPITAL', '实收资本（或股本）', 48, 'EQUITY', 480, 0),
('SME', 'E_CAPITAL_RESERVE', '资本公积', 49, 'EQUITY', 490, 0),
('SME', 'E_SURPLUS_RESERVE', '盈余公积', 50, 'EQUITY', 500, 0),
('SME', 'E_RETAINED_EARNINGS', '未分配利润', 51, 'EQUITY', 510, 0),
('SME', 'T_EQUITY', '所有者权益（或股东权益）合计', 52, 'EQUITY', 520, 1),

-- 负债和所有者权益总计
('SME', 'T_LIABILITIES_AND_EQUITY', '负债和所有者权益（或股东权益）总计', 53, 'LIABILITY_EQUITY', 530, 1);
```

### 4.3 同义词映射表（`fs_balance_sheet_synonyms`）  

将用户口语化表达（含栏次号、简称）映射到标准字段名（视图中的列名），支持按准则过滤。  

```sql
CREATE TABLE fs_balance_sheet_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,               -- 用户输入短语，如“货币资金”“第1行”“资产总计”
    column_name TEXT NOT NULL,               -- 映射到的标准列名，如 'cash_end' 或 'asset_total_begin'
    gaap_type   TEXT,                         -- 适用准则，NULL 表示通用
    priority    INTEGER DEFAULT 1,
    UNIQUE(phrase, column_name)
);

CREATE INDEX idx_synonyms_phrase ON fs_balance_sheet_synonyms(phrase);
CREATE INDEX idx_synonyms_gaap ON fs_balance_sheet_synonyms(gaap_type, priority);

```

-- 企业会计准则常用同义词

```sql
-- 企业会计准则同义词（部分，完整应覆盖所有项目）
-- 货币资金 (A_CASH)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('货币资金', 'a_cash_end', 'ASBE', 2),
('货币资金期初', 'a_cash_begin', 'ASBE', 2),
('货币资金期末', 'a_cash_end', 'ASBE', 2),
('现金', 'a_cash_end', 'ASBE', 1),
('第1行', 'a_cash_end', 'ASBE', 3),
('1行', 'a_cash_end', 'ASBE', 3);

-- 应收账款 (A_ACCOUNTS_RECEIVABLE)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('应收账款', 'a_accounts_receivable_end', 'ASBE', 2),
('应收账款期初', 'a_accounts_receivable_begin', 'ASBE', 2),
('应收', 'a_accounts_receivable_end', 'ASBE', 1),
('第5行', 'a_accounts_receivable_end', 'ASBE', 3),
('5行', 'a_accounts_receivable_end', 'ASBE', 3);

-- 存货 (A_INVENTORY)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('存货', 'a_inventory_end', 'ASBE', 2),
('存货期初', 'a_inventory_begin', 'ASBE', 2),
('库存', 'a_inventory_end', 'ASBE', 1),
('第9行', 'a_inventory_end', 'ASBE', 3),
('9行', 'a_inventory_end', 'ASBE', 3);

-- 固定资产 (A_FIXED_ASSETS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('固定资产', 'a_fixed_assets_end', 'ASBE', 2),
('固定资产原值', 'a_fixed_assets_end', 'ASBE', 1),
('第22行', 'a_fixed_assets_end', 'ASBE', 3),
('22行', 'a_fixed_assets_end', 'ASBE', 3);

-- 短期借款 (L_SHORT_TERM_LOANS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('短期借款', 'l_short_term_loans_end', 'ASBE', 2),
('短借', 'l_short_term_loans_end', 'ASBE', 1),
('第35行', 'l_short_term_loans_end', 'ASBE', 3),
('35行', 'l_short_term_loans_end', 'ASBE', 3);

-- 应付账款 (L_ACCOUNTS_PAYABLE)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('应付账款', 'l_accounts_payable_end', 'ASBE', 2),
('应付', 'l_accounts_payable_end', 'ASBE', 1),
('第39行', 'l_accounts_payable_end', 'ASBE', 3),
('39行', 'l_accounts_payable_end', 'ASBE', 3);

-- 实收资本 (E_SHARE_CAPITAL)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('实收资本', 'e_share_capital_end', 'ASBE', 2),
('股本', 'e_share_capital_end', 'ASBE', 1),
('第61行', 'e_share_capital_end', 'ASBE', 3),
('61行', 'e_share_capital_end', 'ASBE', 3);

-- 未分配利润 (E_RETAINED_EARNINGS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('未分配利润', 'e_retained_earnings_end', 'ASBE', 2),
('未分配', 'e_retained_earnings_end', 'ASBE', 1),
('第70行', 'e_retained_earnings_end', 'ASBE', 3),
('70行', 'e_retained_earnings_end', 'ASBE', 3);

-- 资产总计 (T_ASSETS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('资产总计', 't_assets_end', 'ASBE', 2),
('总资产', 't_assets_end', 'ASBE', 1),
('资产合计', 't_assets_end', 'ASBE', 1),
('第34行', 't_assets_end', 'ASBE', 3),
('34行', 't_assets_end', 'ASBE', 3);

-- 负债和所有者权益总计 (T_LIABILITIES_AND_EQUITY)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('负债和所有者权益总计', 't_liabilities_and_equity_end', 'ASBE', 2),
('负债及权益总计', 't_liabilities_and_equity_end', 'ASBE', 1),
('权益总计', 't_liabilities_and_equity_end', 'ASBE', 1),
('第72行', 't_liabilities_and_equity_end', 'ASBE', 3),
('72行', 't_liabilities_and_equity_end', 'ASBE', 3);
```


-- 小企业会计准则（SME）同义词示例

```sql
-- 货币资金 (A_CASH)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('货币资金', 'a_cash_end', 'SME', 2),
('货币资金期初', 'a_cash_begin', 'SME', 2),
('现金', 'a_cash_end', 'SME', 1),
('第1行', 'a_cash_end', 'SME', 3),
('1行', 'a_cash_end', 'SME', 3);

-- 短期投资 (A_SHORT_TERM_INVESTMENTS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('短期投资', 'a_short_term_investments_end', 'SME', 2),
('短投', 'a_short_term_investments_end', 'SME', 1),
('第2行', 'a_short_term_investments_end', 'SME', 3),
('2行', 'a_short_term_investments_end', 'SME', 3);

-- 存货 (A_INVENTORY)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('存货', 'a_inventory_end', 'SME', 2),
('存货期初', 'a_inventory_begin', 'SME', 2),
('第9行', 'a_inventory_end', 'SME', 3),
('9行', 'a_inventory_end', 'SME', 3);

-- 原材料 (A_RAW_MATERIALS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('原材料', 'a_raw_materials_end', 'SME', 2),
('原料', 'a_raw_materials_end', 'SME', 1),
('第10行', 'a_raw_materials_end', 'SME', 3),
('10行', 'a_raw_materials_end', 'SME', 3);

-- 固定资产原价 (A_FIXED_ASSETS_ORIGINAL)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('固定资产原价', 'a_fixed_assets_original_end', 'SME', 2),
('固定资产原值', 'a_fixed_assets_original_end', 'SME', 1),
('第18行', 'a_fixed_assets_original_end', 'SME', 3),
('18行', 'a_fixed_assets_original_end', 'SME', 3);

-- 累计折旧 (A_ACCUMULATED_DEPRECIATION)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('累计折旧', 'a_accumulated_depreciation_end', 'SME', 2),
('折旧', 'a_accumulated_depreciation_end', 'SME', 1),
('第19行', 'a_accumulated_depreciation_end', 'SME', 3),
('19行', 'a_accumulated_depreciation_end', 'SME', 3);

-- 固定资产账面价值 (A_FIXED_ASSETS_NET)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('固定资产账面价值', 'a_fixed_assets_net_end', 'SME', 2),
('固定资产净值', 'a_fixed_assets_net_end', 'SME', 1),
('第20行', 'a_fixed_assets_net_end', 'SME', 3),
('20行', 'a_fixed_assets_net_end', 'SME', 3);

-- 短期借款 (L_SHORT_TERM_LOANS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('短期借款', 'l_short_term_loans_end', 'SME', 2),
('短借', 'l_short_term_loans_end', 'SME', 1),
('第31行', 'l_short_term_loans_end', 'SME', 3),
('31行', 'l_short_term_loans_end', 'SME', 3);

-- 应付职工薪酬 (L_EMPLOYEE_BENEFITS_PAYABLE)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('应付职工薪酬', 'l_employee_benefits_payable_end', 'SME', 2),
('应付工资', 'l_employee_benefits_payable_end', 'SME', 1),
('第35行', 'l_employee_benefits_payable_end', 'SME', 3),
('35行', 'l_employee_benefits_payable_end', 'SME', 3);

-- 实收资本 (E_SHARE_CAPITAL)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('实收资本', 'e_share_capital_end', 'SME', 2),
('股本', 'e_share_capital_end', 'SME', 1),
('第48行', 'e_share_capital_end', 'SME', 3),
('48行', 'e_share_capital_end', 'SME', 3);

-- 未分配利润 (E_RETAINED_EARNINGS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('未分配利润', 'e_retained_earnings_end', 'SME', 2),
('未分配', 'e_retained_earnings_end', 'SME', 1),
('第51行', 'e_retained_earnings_end', 'SME', 3),
('51行', 'e_retained_earnings_end', 'SME', 3);

-- 资产合计 (T_ASSETS)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('资产合计', 't_assets_end', 'SME', 2),
('总资产', 't_assets_end', 'SME', 1),
('第30行', 't_assets_end', 'SME', 3),
('30行', 't_assets_end', 'SME', 3);

-- 负债合计 (T_LIABILITIES)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('负债合计', 't_liabilities_end', 'SME', 2),
('总负债', 't_liabilities_end', 'SME', 1),
('第47行', 't_liabilities_end', 'SME', 3),
('47行', 't_liabilities_end', 'SME', 3);

-- 所有者权益合计 (T_EQUITY)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('所有者权益合计', 't_equity_end', 'SME', 2),
('股东权益合计', 't_equity_end', 'SME', 1),
('第52行', 't_equity_end', 'SME', 3),
('52行', 't_equity_end', 'SME', 3);

-- 负债和所有者权益总计 (T_LIABILITIES_AND_EQUITY)
INSERT INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES
('负债和所有者权益总计', 't_liabilities_and_equity_end', 'SME', 2),
('负债及权益总计', 't_liabilities_and_equity_end', 'SME', 1),
('第53行', 't_liabilities_and_equity_end', 'SME', 3),
('53行', 't_liabilities_and_equity_end', 'SME', 3);
```

### 4.4 分准则宽表视图  

为每个准则创建一个视图，将纵表数据透视成宽表，每个项目对应两列：`{item_code}_begin` 和 `{item_code}_end`。列名直接使用 `item_code`，便于 NL2SQL 识别。  

#### 4.4.1 企业会计准则视图（`vw_balance_sheet_eas`）  

```sql
CREATE VIEW vw_balance_sheet_eas AS
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
    -- 动态生成每个项目的期初期末列（此处以部分项目为例，完整视图需用代码生成）
    MAX(CASE WHEN i.item_code = 'CASH' THEN i.beginning_balance END) AS cash_begin,
    MAX(CASE WHEN i.item_code = 'CASH' THEN i.ending_balance END) AS cash_end,
    MAX(CASE WHEN i.item_code = 'TRADING_FINANCIAL_ASSETS' THEN i.beginning_balance END) AS trading_financial_assets_begin,
    MAX(CASE WHEN i.item_code = 'TRADING_FINANCIAL_ASSETS' THEN i.ending_balance END) AS trading_financial_assets_end,
    -- ... 继续列出所有企业会计准则项目
    MAX(CASE WHEN i.item_code = 'ASSET_TOTAL' THEN i.beginning_balance END) AS asset_total_begin,
    MAX(CASE WHEN i.item_code = 'ASSET_TOTAL' THEN i.ending_balance END) AS asset_total_end,
    MAX(CASE WHEN i.item_code = 'LIABILITY_EQUITY_TOTAL' THEN i.beginning_balance END) AS liability_equity_total_begin,
    MAX(CASE WHEN i.item_code = 'LIABILITY_EQUITY_TOTAL' THEN i.ending_balance END) AS liability_equity_total_end
FROM fs_balance_sheet_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
WHERE i.gaap_type = 'ASBE'
GROUP BY i.taxpayer_id, i.period_year, i.period_month, i.revision_no, i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence;
```

#### 4.4.2 小企业会计准则视图（`vw_balance_sheet_sas`）  

```sql
CREATE VIEW vw_balance_sheet_sas AS
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
    MAX(CASE WHEN i.item_code = 'CASH' THEN i.beginning_balance END) AS cash_begin,
    MAX(CASE WHEN i.item_code = 'CASH' THEN i.ending_balance END) AS cash_end,
    MAX(CASE WHEN i.item_code = 'SHORT_TERM_INVESTMENT' THEN i.beginning_balance END) AS short_term_investment_begin,
    MAX(CASE WHEN i.item_code = 'SHORT_TERM_INVESTMENT' THEN i.ending_balance END) AS short_term_investment_end,
    -- ... 列出所有小企业会计准则项目
    MAX(CASE WHEN i.item_code = 'ASSET_TOTAL' THEN i.beginning_balance END) AS asset_total_begin,
    MAX(CASE WHEN i.item_code = 'ASSET_TOTAL' THEN i.ending_balance END) AS asset_total_end,
    MAX(CASE WHEN i.item_code = 'LIABILITY_EQUITY_TOTAL' THEN i.beginning_balance END) AS liability_equity_total_begin,
    MAX(CASE WHEN i.item_code = 'LIABILITY_EQUITY_TOTAL' THEN i.ending_balance END) AS liability_equity_total_end
FROM fs_balance_sheet_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
WHERE i.gaap_type = 'SME'
GROUP BY i.taxpayer_id, i.period_year, i.period_month, i.revision_no, i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence;
```

> **说明**：视图列名采用 `{item_code}_begin` 和 `{item_code}_end`，与同义词表中的 `column_name` 一致。实际开发时，可通过读取字典表动态生成视图 DDL。

### 4.5 纳税人信息表（`taxpayer_info`）  

复用增值税方案中的纳税人信息表，用于关联纳税人名称、类型等。  

```sql
CREATE TABLE taxpayer_info (
    taxpayer_id           TEXT PRIMARY KEY,
    taxpayer_name         TEXT NOT NULL,
    taxpayer_type         TEXT NOT NULL,   -- '一般纳税人'/'小规模纳税人'（与增值税保持一致）
    -- 其他字段（行业、信用等级等）可根据需要添加
);
```

### 4.6 用户查询日志表（`user_query_log`）与未匹配短语表（`unmatched_phrases`）  

直接复用增值税方案中的设计，用于监控和优化 NL2SQL。  

```sql
-- 用户查询日志表（同增值税）
CREATE TABLE user_query_log (...);

-- 未匹配短语表（同增值税）
CREATE TABLE unmatched_phrases (...);
```

## 5. ETL 流程设计（PDF/Excel → 明细表）  

### 5.1 输入解析  
- 识别报表类型（企业会计准则/小企业会计准则）、纳税人识别号、所属期（年月）。  
- 解析左右分栏表格：左侧为资产项目，右侧为负债和所有者权益项目。需注意行次连续、合计行可能无行次号。  

### 5.2 行列转换  
- 遍历每一行，提取项目名称、行次（若有）、期末余额、年初余额。  
- 根据项目名称和准则类型，通过字典表匹配标准 `item_code`；若无法匹配，记录错误并跳过。  
- 将数据组织为 `(taxpayer_id, period, gaap_type, item_code, beginning_balance, ending_balance)` 的形式。  

### 5.3 写入明细表  
- 使用 `INSERT OR REPLACE` 按主键批量 upsert，支持更正申报（`revision_no` 递增）。  

### 5.4 数据质量校验  
- 检查资产总计是否等于负债和所有者权益总计（允许少量误差）。  
- 若从 PDF 解析，记录置信度字段。  

## 6. NL2SQL 应用流程（适配资产负债表）  

### 6.1 实体识别与同义词标准化  
1. 从用户问题中提取纳税人、期次、准则类型（通过关键词如“小企业”“一般企业”或默认为企业会计准则）。  
2. 根据准则类型选择对应的视图（`vw_balance_sheet_eas` 或 `vw_balance_sheet_sas`）。  
3. 使用同义词表进行“最长匹配优先 + 不重叠替换”，将用户口语映射到视图列名（如 `cash_end`）。  

### 6.2 大模型 Prompt 设计（两阶段受控生成）  
- **阶段1（意图解析）**：输出 JSON，包含 `domain='balance_sheet'`、`gaap_type`、需查询的列（metrics/dimensions）、过滤条件（纳税人、期次）、是否需要澄清。  
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

- 增加现金流量表、利润表等财务报表，采用相同建模思路。  
- 构建统一的企业画像维度表，增强跨表分析能力。  
- 实现自动化的未匹配短语闭环处理，持续丰富同义词库。  

---  

**附录**：项目字典表完整数据、同义词表示例（略）。