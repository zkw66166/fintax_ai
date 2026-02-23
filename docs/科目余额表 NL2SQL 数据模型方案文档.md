# 科目余额表 NL2SQL 数据模型方案文档  
**版本**：**v1.0** | **最后更新**：2026-02-14  

## 1. 项目背景与目标  

科目余额表是企业财务核心数据之一，反映各会计科目在特定期间内的期初余额、本期借方发生、本期贷方发生及期末余额。  
我国企业分别适用**企业会计准则**或**小企业会计准则**，两套准则的科目体系存在大量重叠，但也有各自特有科目。  

目标：构建一套**面向 NL2SQL 的事后分析数据模型**，支持：  

- 用户通过自然语言查询任意纳税人、任意期次的科目余额数据；  
- 兼容企业会计准则与小企业会计准则，并支持未来扩展其他准则；  
- ETL 能够从 Excel/财务软件等异构来源稳定导入；  
- 存储紧凑、查询高效，大模型 SQL 生成准确率 ≥95%。  

---

## 2. 核心挑战  

| 挑战 | 描述 |  
|------|------|  
| **科目体系异构** | 两套准则科目有同有异，需统一存储并标识适用准则 |  
| **科目名称歧义** | 用户口语化表达（如“现金”“应收”“折旧”）需精准匹配到标准科目 |  
| **级次与方向** | 科目有级次（1‑4级）和默认余额方向，查询时可能需按级次汇总或过滤 |  
| **数据稀疏性** | 并非所有企业每月都有所有科目的发生额，但科目字典固定，明细表仍可能稀疏 |  
| **ETL 复杂度** | Excel 源为二维表，需按科目编码解析并写入关系模型 |  

---

## 3. 设计原则  

1. **存储与查询解耦**：明细表按科目编码+期间存储，通过视图提供 NL2SQL 入口，屏蔽物理表复杂性。  
2. **科目字典统一**：将两套准则科目合并为一张字典表，用标记字段区分适用准则，消除冗余。  
3. **字段名即业务术语**：物理字段采用完整英文名（如 `opening_balance`），大模型零学习成本。  
4. **同义词专门管理**：为科目名称及常用口语建立独立的同义词表，支持前置替换。  
5. **维度行拍平**：每个企业每月每个科目仅一行，包含期初、借方、贷方、期末四指标。  
6. **一次设计，无限扩展**：新增会计准则只需追加科目字典，不破坏已有查询。  

---

## 4. 数据模型详细设计  

### 4.1 纳税人信息表增强（`taxpayer_info`）  

> 为支持按会计准则过滤，在现有 `taxpayer_info` 表基础上增加 `accounting_standard` 字段。  

```sql
ALTER TABLE taxpayer_info ADD COLUMN accounting_standard TEXT;  -- '企业会计准则' / '小企业会计准则' / NULL
```

### 4.2 科目字典表（`account_master`）  

统一存储所有可能用到的会计科目，并用标记字段表示适用于哪种准则。  

```sql
CREATE TABLE account_master (
    account_code        TEXT PRIMARY KEY,      -- 科目编码，如 '1001'
    account_name        TEXT NOT NULL,         -- 科目名称
    level               INTEGER,               -- 级次（1,2,3,4）
    category            TEXT NOT NULL,         -- 类别：资产/负债/权益/成本/损益
    balance_direction   TEXT NOT NULL,         -- 余额方向：借/贷
    is_gaap             INTEGER DEFAULT 0,     -- 是否适用于企业会计准则
    is_small            INTEGER DEFAULT 0,     -- 是否适用于小企业会计准则
    is_active           INTEGER DEFAULT 1,     -- 是否在用
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (balance_direction IN ('借', '贷')),
    CHECK (category IN ('资产','负债','权益','成本','损益'))
);

CREATE INDEX idx_account_name ON account_master(account_name);
CREATE INDEX idx_account_category ON account_master(category);
```

**说明**：  
- 科目编码全局唯一，如果同一编码在两套准则中名称不同（极少见），则以企业会计准则为准，或视为两个不同编码（需拆分）。此处假设名称一致。  
- `is_gaap` / `is_small` 同时为 1 表示该科目两套准则通用。  

### 4.3 科目余额明细表（`account_balance`）  

存储每个企业每月每个科目的余额数据。  

```sql
CREATE TABLE account_balance (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    account_code        TEXT NOT NULL,         -- 关联 account_master

    -- 追溯/版本（v1.0 预留）
    revision_no         INTEGER NOT NULL DEFAULT 0,
    submitted_at        TIMESTAMP,
    etl_batch_id        TEXT,
    source_doc_id       TEXT,
    source_unit         TEXT DEFAULT '元',
    etl_confidence      REAL,

    -- 指标
    opening_balance     NUMERIC,               -- 本币期初余额
    debit_amount        NUMERIC,               -- 本币借方发生
    credit_amount       NUMERIC,               -- 本币贷方发生
    closing_balance     NUMERIC,               -- 本币期末余额

    PRIMARY KEY (taxpayer_id, period_year, period_month, account_code, revision_no),
    FOREIGN KEY (account_code) REFERENCES account_master(account_code),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_balance_period ON account_balance (period_year, period_month);
CREATE INDEX idx_balance_taxpayer ON account_balance (taxpayer_id);
CREATE INDEX idx_balance_taxpayer_period ON account_balance (taxpayer_id, period_year, period_month);
CREATE INDEX idx_balance_account ON account_balance (account_code);
```

### 4.4 ETL 列映射表（可选，`account_balance_column_mapping`）  

用于将 Excel 源中的列标题映射到目标字段，提升 ETL 鲁棒性。  

```sql
CREATE TABLE account_balance_column_mapping (
    source_column   TEXT PRIMARY KEY,
    target_field    TEXT NOT NULL,
    description     TEXT
);

INSERT INTO account_balance_column_mapping (source_column, target_field) VALUES
    ('本币期初余额', 'opening_balance'),
    ('本币借方发生', 'debit_amount'),
    ('本币贷方发生', 'credit_amount'),
    ('本币期末余额', 'closing_balance');
```

### 4.5 科目同义词表（`account_synonyms`）  

将用户口语化的科目名称（如“现金”“应收”）映射到标准科目名称或编码，用于 NL2SQL 前置处理。  

```sql
CREATE TABLE account_synonyms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase          TEXT NOT NULL,               -- 用户口语，如“现金”
    account_code    TEXT,                         -- 若能确定唯一科目，可填编码
    account_name    TEXT,                         -- 或直接映射到标准科目名称
    priority        INTEGER DEFAULT 1,
    applicable_standards TEXT,                    -- 可选，限制适用准则
    UNIQUE(phrase, account_code, account_name)
);

CREATE INDEX idx_synonyms_phrase ON account_synonyms(phrase);

-- 示例数据（需根据实际科目填充）
INSERT INTO account_synonyms (phrase, account_name, priority) VALUES
    ('现金', '库存现金', 2),
    ('银行存款', '银行存款', 2),
    ('银行', '银行存款', 1),
    ('应收', '应收账款', 1),
    ('应付', '应付账款', 1),
    ('固定资产', '固定资产', 2),
    ('折旧', '累计折旧', 1),
    ('主营业务收入', '主营业务收入', 2),
    ('收入', '主营业务收入', 1);
```

**处理逻辑**：NL2SQL 前置模块对用户问题分词，优先匹配 `account_synonyms`，将识别出的短语替换为 `account_name`（或 `account_code`），然后在生成 SQL 时作为 `account_name` 的过滤条件。  

### 4.6 科目余额视图（`vw_account_balance`）  

为 NL2SQL 提供统一入口，自动关联科目字典和纳税人信息，并根据纳税人适用的会计准则过滤科目。  

```sql
CREATE VIEW vw_account_balance AS
SELECT
    b.taxpayer_id,
    t.taxpayer_name,
    t.accounting_standard,               -- 企业使用的会计准则
    b.period_year,
    b.period_month,
    b.account_code,
    a.account_name,
    a.level,
    a.category,
    a.balance_direction,
    a.is_gaap,
    a.is_small,
    b.revision_no,
    b.opening_balance,
    b.debit_amount,
    b.credit_amount,
    b.closing_balance,
    b.source_unit
FROM account_balance b
JOIN taxpayer_info t ON b.taxpayer_id = t.taxpayer_id
JOIN account_master a ON b.account_code = a.account_code
WHERE (
    (t.accounting_standard = '企业会计准则' AND a.is_gaap = 1)
    OR (t.accounting_standard = '小企业会计准则' AND a.is_small = 1)
    OR (a.is_gaap = 1 AND a.is_small = 1)          -- 通用科目
    OR t.accounting_standard IS NULL                -- 未指定准则时不过滤
);
```

**说明**：若企业未指定会计准则，视图仍返回所有科目（此时由用户自行澄清或由上层默认）。  

---

## 5. ETL 流程设计（Excel → 明细表）  

### 5.1 输入解析  
- 识别报表类型（企业会计准则/小企业会计准则）、纳税人识别号、所属期（年/月）；  
- 读取二维表格：行 = 科目编码，列 = 期初余额、借方发生、贷方发生、期末余额。  

### 5.2 科目字典更新  
- 遍历所有科目行，对于每个科目：  
  - 若 `account_code` 在 `account_master` 中不存在，则插入新记录，并根据当前报表的准则设置 `is_gaap` 或 `is_small` 为 1；  
  - 若已存在，则将对应准则标记更新为 1（如原本只有企业准则，现发现小企业也有，则置 `is_small=1`）。  

### 5.3 余额数据写入  
```python
for 科目编码, 期初, 借方, 贷方, 期末 in 行数据:
    key = (taxpayer_id, period_year, period_month, 科目编码, revision_no=0)
    upsert account_balance set
        opening_balance = 期初,
        debit_amount = 借方,
        credit_amount = 贷方,
        closing_balance = 期末
    where key matches;
```

### 5.4 错误日志（复用 `etl_error_log`）  
记录解析异常、单位不一致（如万元需转换）、校验失败（如 `期初+借方-贷方≠期末` 超出容忍范围）等。  

---

## 6. NL2SQL 应用流程  

### 6.1 实体识别与同义词标准化  

1. **实体识别**：提取纳税人 ID/名称、期间（年/月）、可能的科目短语。  
2. **科目同义词替换**：  
   - 对用户问题分词，查找 `account_synonyms`，将匹配的短语替换为标准科目名称（或编码）；  
   - 例如“2024年12月现金余额” → “2024年12月 库存现金 余额”。  
3. **路由确定**：  
   - 根据纳税人 ID 从 `taxpayer_info` 获取其 `accounting_standard`，用于后续视图过滤。  
   - 若无法获取，则暂不限制准则（视图条件中 `t.accounting_standard IS NULL`）。  

### 6.2 两阶段受控生成（方案A）  

**阶段1：意图解析（LLM → JSON）**  

输出 JSON 示例：  
```json
{
  "domain": "account_balance",
  "select": {
    "metrics": ["closing_balance"],
    "dimensions": ["account_name"]
  },
  "filters": {
    "taxpayer_id": ":taxpayer_id",
    "period_year": ":year",
    "period_month": ":month",
    "account_name": "库存现金"
  },
  "aggregation": {
    "group_by": ["account_name"],
    "order_by": [{"column": "account_name", "dir": "ASC"}],
    "limit": 100
  },
  "need_clarification": false
}
```

**阶段2：动态 Schema 注入 + SQL 生成**  
- 系统根据 JSON 从 `schema_catalog` 提取允许的视图（仅 `vw_account_balance`）及允许的列（如 `closing_balance`, `account_name` 等）。  
- 注入阶段2 prompt，要求生成只读 SQL，必须包含 `taxpayer_id` 和期间过滤。  
- 示例生成 SQL：  
```sql
SELECT account_name, closing_balance
FROM vw_account_balance
WHERE taxpayer_id = :taxpayer_id
  AND period_year = :year AND period_month = :month
  AND account_name = '库存现金'
ORDER BY account_name
LIMIT 100;
```

### 6.3 SQL 审核器规则  

复用增值税方案中的审核器规则，并针对科目余额增加：  
- 禁止访问除 `vw_account_balance` 以外的表/视图；  
- 若涉及 `account_name` 过滤，建议使用等值或 `LIKE`，避免全表扫描；  
- 明细查询必须 `LIMIT ≤ 1000`。  

### 6.4 日志与未匹配短语  

- `user_query_log` 记录每次查询（同增值税表结构）。  
- `unmatched_phrases` 记录未能通过科目同义词匹配的短语，用于持续优化同义词库。  

---

## 7. 方案对比分析  

| 对比维度 | **本方案（科目字典 + 明细表 + 视图 + 两阶段）** | **两表独立（分准则存储）** | **全纵表（一行一科目一指标）** |  
|----------|-----------------------------------------------|--------------------------|-------------------------------|  
| **NL2SQL 表选择复杂度** | ⭐⭐⭐⭐（仅一个视图） | ⭐⭐（需判断准则路由） | ⭐⭐（需复杂聚合） |  
| **字段语义明确性** | ⭐⭐⭐⭐⭐（视图降噪） | ⭐⭐⭐⭐ | ⭐⭐ |  
| **存储效率** | ⭐⭐⭐⭐⭐（一行/科目/期） | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |  
| **科目体系扩展性** | ⭐⭐⭐⭐⭐（字典统一） | ⭐⭐（需同步修改两表） | ⭐⭐⭐ |  
| **跨准则对比** | ⭐⭐⭐（需用准则字段区分） | ❌ 难以统一 | ⭐⭐ |  
| **大模型准确率** | **≥95%（目标）**：同义词前置 + 两阶段 + 硬校验 | 80~90% | ≤70% |  

---

## 8. 总结与扩展建议  

本方案提供：  
- ✅ 科目字典表 `account_master`（统一两套准则，支持扩展）  
- ✅ 余额明细表 `account_balance`（按企业、期间、科目存储）  
- ✅ 科目同义词表 `account_synonyms`（口语→标准科目）  
- ✅ 查询视图 `vw_account_balance`（自动适配企业会计准则）  
- ✅ 两阶段受控生成 + SQL 审核器规则（复用增值税方案）  

**下一步扩展建议**：  
1. **外币支持**：若需外币余额，可增加 `currency_code` 字段及对应原币金额列。  
2. **辅助核算**：可扩展维度（如部门、项目），通过额外字段或关联表实现。  
3. **期初余额历史**：若需追溯期初余额的调整，可引入 `adjustment_type` 等版本控制。  
4. **科目级别汇总**：在视图中提供 `level` 字段，支持按级次汇总查询。  

---

## 附录：科目字典示例数据（部分）  

| account_code | account_name       | level | category | balance_direction | is_gaap | is_small |  
|--------------|--------------------|-------|----------|-------------------|---------|----------|  
| 1001         | 库存现金           | 1     | 资产     | 借                | 1       | 1        |  
| 1002         | 银行存款           | 1     | 资产     | 借                | 1       | 1        |  
| 1122         | 应收账款           | 1     | 资产     | 借                | 1       | 1        |  
| 1403         | 原材料             | 1     | 资产     | 借                | 1       | 1        |  
| 1501         | 持有至到期投资     | 1     | 资产     | 借                | 1       | 0        |  
| 222101       | 应交增值税         | 2     | 负债     | 贷                | 1       | 1        |  
| 4001         | 实收资本           | 1     | 权益     | 贷                | 1       | 1        |  
| 5001         | 主营业务收入       | 1     | 损益     | 贷                | 1       | 1        |  
| 5602         | 管理费用           | 1     | 损益     | 借                | 0       | 1        |  

（注：实际数据需从 "D:\fintax_ai\docs\合并后的科目余额表（企业准则 vs 小企业准则）_整合版tmp.xlsx" 导入生成。）
