## 1）企业维度表增强（company / 组织 / 征管维度）

目标：把“企业是谁、在哪、归谁管、什么行业、什么纳税人属性、信用等级如何”结构化出来，让画像、分组统计、穿透筛选都能用 **JOIN 维表** 完成，而不是靠文本模糊匹配。

### 1.1 推荐建模：一张主维表 + 若干字典维表（可选）

#### 1.1.1 主维表（增强版 创建改为comanpy_info，迁移`taxpayer_info`数据到'comanpy_info',不再需要taxpayer_info）

> 保持稳定主键；把变化频繁/可能历史变更的字段拆到“快照表”（见 1.2）。

```sql
CREATE TABLE IF NOT EXISTS comanpy_info (
  company_id           TEXT PRIMARY KEY,            -- 统一社会信用代码/纳税人识别号
  company_name         TEXT NOT NULL,

  company_type         TEXT NOT NULL,               -- '一般纳税人'/'小规模纳税人'
  applicable_GAAP		TEXT,  						-- '企业会计准则'/'小企业会计准则'
  registration_type     TEXT,                        -- 企业登记类型（有限公司/个体等）
  legal_representative  TEXT,                        -- 法人（如合规不允许可移除）
  establish_date        DATE,

  -- 行业（建议用标准编码 + 名称，避免只存名称）
  industry_code         TEXT,                        -- 国标行业分类编码（如GB/T 4754）
  industry_name         TEXT,

  -- 征管信息（推荐编码化）
  tax_authority_code    TEXT,                        -- 税务机关代码
  tax_authority_name    TEXT,
  tax_bureau_level      TEXT,                        -- 省/市/区县/分局等（可选）

  -- 区划信息（可用于地区分析）
  region_code           TEXT,                        -- 行政区划代码
  region_name           TEXT,

  -- 纳税信用等级（注意：可能按年度变）
  credit_grade_current  TEXT,                        -- 'A'/'B'/'M'/'C'/'D'/NULL
  credit_grade_year     INTEGER,                     -- 当前等级对应年度（若有）

  -- 标签/状态
  status                TEXT DEFAULT 'active',        -- active/inactive/cancelled
  updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_company_name ON company_info(company_name);
CREATE INDEX IF NOT EXISTS idx_company_industry ON company_info(industry_code);
CREATE INDEX IF NOT EXISTS idx_company_region ON company_info(region_code);
CREATE INDEX IF NOT EXISTS idx_company_authority ON company_info(tax_authority_code);
```

**关键点**
- 行业/税务机关/区划都尽量“编码 + 名称”双存，方便标准化、避免同名歧义。
- `credit_grade_current` 只能表示“当前口径”，如果要做历史趋势或按年对比，必须用快照表（下一节）。

---

### 1.2 强烈建议：属性快照表（SCD2 / 按月按年快照）

典型会变的字段：`tax_authority`、`credit_grade`、甚至 `industry`（企业变更经营范围后可能调整）。  
为保证“查询某个期间时，企业属性与当期一致”，建议引入快照表：

#### 1.2.1 按月快照（适合与 VAT/月度财务对齐）
```sql
CREATE TABLE IF NOT EXISTS company_profile_snapshot_month (
  company_id        TEXT NOT NULL,
  period_year        INTEGER NOT NULL,
  period_month       INTEGER NOT NULL,

  industry_code      TEXT,
  tax_authority_code TEXT,
  region_code        TEXT,
  credit_grade       TEXT,          -- 当月有效的信用等级（如有）
  employee_scale     TEXT,          -- 人员规模段（可选）
  revenue_scale      TEXT,          -- 收入规模段（可选）

  source_doc_id      TEXT,
  etl_batch_id       TEXT,
  updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (company_id, period_year, period_month),
  FOREIGN KEY (company_id) REFERENCES company_info(company_id)
);

CREATE INDEX IF NOT EXISTS idx_snap_month_industry
ON company_profile_snapshot_month(period_year, period_month, industry_code);

CREATE INDEX IF NOT EXISTS idx_snap_month_credit
ON company_profile_snapshot_month(period_year, period_month, credit_grade);
```

#### 1.2.2 按年快照（适合纳税信用等级“年度发布”的现实）
```sql
CREATE TABLE IF NOT EXISTS company_credit_grade_year (
  company_id    TEXT NOT NULL,
  year           INTEGER NOT NULL,
  credit_grade   TEXT NOT NULL,     -- A/B/M/C/D
  published_at   DATE,
  source_doc_id  TEXT,
  etl_batch_id   TEXT,
  PRIMARY KEY (company_id, year),
  FOREIGN KEY (company_id) REFERENCES company_info(company_id)
);

CREATE INDEX IF NOT EXISTS idx_credit_year_grade
ON company_credit_grade_year(year, credit_grade);
```

> 选择建议：  
> - 若你们的下游分析绝大多数按“申报期（月）”跑，优先“按月快照”。  
> - 若只关心信用等级且它按年发布，单独做按年表最干净。

---

### 1.3 字典维表（可选但很有价值）

用于统一口径、避免自由文本污染。

```sql
CREATE TABLE IF NOT EXISTS dim_industry (
  industry_code TEXT PRIMARY KEY,
  industry_name TEXT NOT NULL,
  parent_code   TEXT
);

CREATE TABLE IF NOT EXISTS dim_tax_authority (
  tax_authority_code TEXT PRIMARY KEY,
  tax_authority_name TEXT NOT NULL,
  region_code        TEXT,
  level              TEXT
);

CREATE TABLE IF NOT EXISTS dim_region (
  region_code TEXT PRIMARY KEY,
  region_name TEXT NOT NULL,
  parent_code TEXT
);
```

---

### 1.4 面向 NL2SQL 的“企业画像入口视图”（建议）

把常用维度（行业/税务机关/区划/信用等级）做成一个统一视图，减少 NL2SQL JOIN 出错。

```sql
CREATE VIEW IF NOT EXISTS vw_company_dimension AS
SELECT
  t.company_id,
  t.company_name,
  t.company_type,
  t.industry_code,
  t.industry_name,
  t.tax_authority_code,
  t.tax_authority_name,
  t.region_code,
  t.region_name,
  t.credit_grade_current,
  t.credit_grade_year
FROM company_info t;
```

如果你采用快照表，再提供按月版本：

```sql
CREATE VIEW IF NOT EXISTS vw_company_dimension_month AS
SELECT
  s.company_id,
  t.company_name,
  t.company_type,
  s.period_year,
  s.period_month,
  s.industry_code,
  di.industry_name,
  s.tax_authority_code,
  ta.tax_authority_name,
  s.region_code,
  r.region_name,
  s.credit_grade
FROM company_profile_snapshot_month s
JOIN company_info t ON t.company_id = s.company_id
LEFT JOIN dim_industry di ON di.industry_code = s.industry_code
LEFT JOIN dim_tax_authority ta ON ta.tax_authority_code = s.tax_authority_code
LEFT JOIN dim_region r ON r.region_code = s.region_code;
```

---

### 1.5 典型分析 SQL 示例（增强维度后能做什么）

**例：按行业统计 2025-12 一般纳税人销项税额（一般项目、本月、latest）Top 10**
```sql
WITH g AS (
  SELECT
    company_id,
    period_year,
    period_month,
    item_type,
    time_range,
    output_tax,
    ROW_NUMBER() OVER (
      PARTITION BY company_id, period_year, period_month, item_type, time_range
      ORDER BY revision_no DESC
    ) AS rn
  FROM vw_vat_return_general
  WHERE period_year = 2025 AND period_month = 12
    AND item_type = '一般项目' AND time_range = '本月'
)
SELECT
  d.industry_name,
  SUM(COALESCE(g.output_tax, 0)) AS output_tax_sum
FROM g
JOIN vw_company_dimension d ON d.company_id = g.company_id
WHERE g.rn = 1
GROUP BY d.industry_name
ORDER BY output_tax_sum DESC
LIMIT 10;
```

---

## 2）对齐口径字典（Metric Registry）：显式化跨域/跨类型指标映射

目标：当用户问“税负率”“应纳税额对比（申报 vs 发票）”“销项税（一般 vs 小规模）”时，不让 LLM 临时猜字段，而是**先查字典**得到“应该用哪些视图/字段/过滤维度/聚合方式/对齐口径说明”，然后再生成 SQL。

### 2.1 你需要解决的三类“对齐”

1. **跨类型对齐**（一般 vs 小规模）：同名指标未必同口径；字段也不对称。  
2. **跨域对齐**（申报 vs 发票 vs 财务）：口径不同、时间维度不同（invoice_date vs period_month）。  
3. **衍生指标**（比率/差异/同比环比）：需要表达式 + 依赖多个基础指标。

> 结论：字典不只是“字段映射”，而是“指标的可执行规范（spec）”。

---

### 2.2 建表方案（SQLite 友好，先 MVP 后增强）

#### 2.2.1 指标主表：`metric_registry`

存“指标是什么、输出单位、适用域、是否允许跨类型”。

```sql
CREATE TABLE IF NOT EXISTS metric_registry (
  metric_key        TEXT PRIMARY KEY,     -- 稳定标识：vat.output_tax / vat.tax_payable / reconcile.vat_vs_invoice_output
  metric_name       TEXT NOT NULL,        -- 展示名：销项税额、应纳税额、申报-开票差异（销项）
  description       TEXT,                 -- 口径说明（人读）
  unit              TEXT DEFAULT '元',    -- 元/份/%等
  value_type        TEXT DEFAULT 'amount',-- amount/count/ratio
  domain            TEXT NOT NULL,        -- vat/invoice/fs/cross_domain/profile...
  allow_cross_type  INTEGER DEFAULT 0,    -- 0/1
  allow_cross_domain INTEGER DEFAULT 0,   -- 0/1
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.2.2 指标实现表：`metric_definition`

存“这个指标怎么从哪个视图算出来”，一条指标可有多条 definition（按 company_type、按 source_domain、按版本）。

```sql
CREATE TABLE IF NOT EXISTS metric_definition (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  metric_key       TEXT NOT NULL,

  -- 适用范围（可用于选择最匹配的definition）
  company_type    TEXT,                  -- NULL=通用；或 '一般纳税人'/'小规模纳税人'
  source_domain    TEXT NOT NULL,         -- vat/invoice/fs/profile
  source_view      TEXT NOT NULL,         -- vw_vat_return_general / vw_vat_return_small / vw_invoice ...

  -- 维度约束（VAT的 item_type/time_range 等）
  dim_item_type    TEXT,                  -- 固定值或NULL
  dim_time_range   TEXT,                  -- 固定值或NULL

  -- 计算表达式（SQL片段，列名必须属于 source_view）
  value_expr       TEXT NOT NULL,         -- 例如 "COALESCE(output_tax,0)" 或 "SUM(COALESCE(total_tax_payable,0))"
  agg_func         TEXT DEFAULT 'SUM',    -- SUM/AVG/MAX/NA（也可直接写在 value_expr 里，二选一但要统一规范）
  revision_strategy TEXT DEFAULT 'latest',-- latest/specific/na（发票通常na）

  -- 输出标准化
  normalized_metric_name TEXT,            -- 例如 '销项税额(申报)'，便于 UNION ALL 展示
  priority         INTEGER DEFAULT 1,     -- 多条匹配时的选择
  is_active        INTEGER DEFAULT 1,

  FOREIGN KEY(metric_key) REFERENCES metric_registry(metric_key)
);

CREATE INDEX IF NOT EXISTS idx_metric_def_lookup
ON metric_definition(metric_key, source_domain, company_type, is_active, priority);
```

#### 2.2.3 指标同义词（可复用你现有 `vat_synonyms` 思路）

用户会说“销项”“销项税”“输出税”等，建议单独维护指标级 synonym，先映射到 `metric_key`，再由 metric_definition 指向字段。

```sql
CREATE TABLE IF NOT EXISTS metric_synonyms (
  phrase      TEXT PRIMARY KEY,
  metric_key  TEXT NOT NULL,
  priority    INTEGER DEFAULT 1,
  FOREIGN KEY(metric_key) REFERENCES metric_registry(metric_key)
);

CREATE INDEX IF NOT EXISTS idx_metric_syn_phrase ON metric_synonyms(phrase);
```

---

### 2.3 如何被 NL2SQL 使用（推荐流程）

**阶段1（意图 JSON）**不要直接选字段，而是：
1. 先把用户问题解析为 `metric_key`（通过 `metric_synonyms` / 规则 / LLM）。  
2. 再由程序查询 `metric_definition`，把“候选实现（views + expr + dim 约束）”作为白名单注入阶段2。  
3. 阶段2 只负责把这些实现拼成 SQL（含 period filter、latest revision、UNION ALL 对齐等）。

这样 LLM 的“自由度”被压缩到拼装层，错误率会明显下降。

---

### 2.4 示例：录入两类纳税人的“应纳税额（对齐口径）”

#### 2.4.1 registry
```sql
INSERT OR REPLACE INTO metric_registry
(metric_key, metric_name, description, unit, value_type, domain, allow_cross_type, allow_cross_domain)
VALUES
('vat.tax_payable_aligned', '应纳税额（对齐口径）',
 '一般纳税人使用申报表第24栏应纳税额合计；小规模使用第20栏应纳税额合计。仅用于跨类型对比展示。',
 '元', 'amount', 'vat', 1, 0);
```

#### 2.4.2 definitions
```sql
INSERT INTO metric_definition
(metric_key, company_type, source_domain, source_view, dim_item_type, dim_time_range,
 value_expr, agg_func, revision_strategy, normalized_metric_name, priority)
VALUES
-- 一般纳税人：第24栏 total_tax_payable，建议限定一般项目+本月
('vat.tax_payable_aligned', '一般纳税人', 'vat', 'vw_vat_return_general',
 '一般项目', '本月',
 'COALESCE(total_tax_payable,0)', 'SUM', 'latest', '应纳税额(一般-申报)', 10),

-- 小规模：第20栏 tax_due_total，建议限定货物及劳务+本期
('vat.tax_payable_aligned', '小规模纳税人', 'vat', 'vw_vat_return_small',
 '货物及劳务', '本期',
 'COALESCE(tax_due_total,0)', 'SUM', 'latest', '应纳税额(小规模-申报)', 10);
```

---

### 2.5 示例：跨域对账指标（申报销项税 vs 发票销项税）

这里要先明确：发票域是否有可直接汇总“销项税额”的字段（如 `output_vat_amount` / `tax_amount` 且仅销项）。如果你们的 `vw_invoice` 区分销项/进项、红蓝字、作废等，那么 metric_definition 才能写得严谨。

**示例（假设 `vw_invoice` 有 `invoice_direction`='销项'，税额列 `vat_tax_amount`）**：

```sql
INSERT OR REPLACE INTO metric_registry
(metric_key, metric_name, description, unit, value_type, domain, allow_cross_type, allow_cross_domain)
VALUES
('reconcile.output_tax_vat_vs_invoice', '销项税额对账（申报 vs 发票）',
 '对比同期间：申报销项税额 vs 发票销项税额汇总。注意红冲/作废/开票日期口径差异需在规则中明确。',
 '元', 'amount', 'cross_domain', 0, 1);

-- 申报侧（一般纳税人）
INSERT INTO metric_definition
(metric_key, company_type, source_domain, source_view, dim_item_type, dim_time_range,
 value_expr, agg_func, revision_strategy, normalized_metric_name, priority)
VALUES
('reconcile.output_tax_vat_vs_invoice', '一般纳税人', 'vat', 'vw_vat_return_general',
 '一般项目', '本月',
 'COALESCE(output_tax,0)', 'SUM', 'latest', '销项税额(申报)', 10);

-- 发票侧（通用，不分一般/小规模也可）
INSERT INTO metric_definition
(metric_key, company_type, source_domain, source_view,
 value_expr, agg_func, revision_strategy, normalized_metric_name, priority)
VALUES
('reconcile.output_tax_vat_vs_invoice', NULL, 'invoice', 'vw_invoice',
 'CASE WHEN invoice_direction = ''销项'' THEN COALESCE(vat_tax_amount,0) ELSE 0 END',
 'SUM', 'na', '销项税额(发票)', 10);
```

然后阶段2 生成 SQL 时，按同一期间做两侧聚合再 `UNION ALL` 输出对比表；或计算差异列（取决于你是否允许单 SQL 内做两侧 join/子查询）。

---

### 2.6 关键治理点（不做这些，字典会“看似有用、实际难用”）

1. **口径说明必须落库**（`description`）：尤其是跨域对账，必须写清红冲/作废是否包含、按开票日期还是入账期等。  
2. **维度约束显式化**：VAT 的 `item_type/time_range` 建议写进 definition，别让 LLM 猜默认值。  
3. **优先级与停用机制**：同一指标可能有多个实现（例如老表、新表；或不同政策期间），需要 `priority` 与 `is_active` 管理。  
4. **指标输出 schema 统一**：跨域/跨类型推荐统一输出列：  
   - `source`（申报/发票/财务）  
   - `company_type`（可空）  
   - `metric_key/metric_name`  
   - `metric_value`  
   - `period_year/period_month` 或 `start_date/end_date`  
   这会让前端渲染与二次计算非常省事。

---

如果你确认你们现有 `vw_invoice` 的关键字段（例如：销项/进项区分字段名、税额列名、红冲/作废标识、以及 period 字段是否齐全），我可以把“跨域对账指标”的 metric_definition 模板按你真实字段补到可直接执行的程度，并给出阶段2 SQL 的标准拼装模板（含参数与审核规则要点）。