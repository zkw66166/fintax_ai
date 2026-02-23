# 企业税务与财务 NL2SQL 数据模型与受控生成方案文档  
**版本**：**v1.2** | **最后更新**：2026-02-13  

## fintax_ai is a is an intelligent tax and financial consulting platform (税务智能咨询系统) with:

Phase one: Chinese VAT (增值税) tax data modeling project for building an NL2SQL system. It enables natural language queries against structured tax return data for both General Taxpayers (一般纳税人) and Small-Scale Taxpayers (小规模纳税人).
Phase two: analysis for EIT returen, financial statements, accounting_balance, invoice, company profile, etc.

## 本文档仅是phase one 增值税相关的设计

---

## 1. 项目背景与目标

增值税申报表包含**一般纳税人**与**小规模纳税人**两套独立主表，每张主表均为“行次（栏次）+ 四列复合数据列”（一般纳税人：一般项目本月/累计、即征即退本月/累计；小规模：货物及劳务、服务不动产无形资产的本期/累计）。  
目标：构建一套**面向 NL2SQL 的事后分析数据模型**，支持：

- 用户通过自然语言查询任意纳税人、任意期次的申报明细数据；
- 支持跨纳税人类型（一般/小规模）的指标对比；
- ETL 能够从 PDF/Excel 等异构来源稳定导入；
- 存储紧凑、查询高效，大模型 SQL 生成准确率 ≥95%。

---

## 2. 核心挑战

| 挑战 | 描述 |
|------|------|
| **稀疏性** | 主表 41/25 栏次，四列数据 → 164/100 物理列，绝大多数企业无即征即退业务，空值极高 |
| **异构性** | 两套表结构、字段语义完全不同，无法直接合并 |
| **NL2SQL 歧义** | 用户口语化表达（如“销项税”“第11栏”“应补退税”）需精准映射到物理字段 |
| **表路由复杂度** | 若分表存储，NL2SQL 必须先判断纳税人类型再选表，易出错 |
| **ETL 复杂度** | PDF/Excel 源为二维表，需转换为关系模型 |

---

## 3. 设计原则

1. **存储与查询解耦**：明细表严格按纳税人类型分存，保障 ETL 清晰；查询侧通过分类型视图提供入口，NL2SQL 永不直接接触明细表。  
2. **字段名即业务术语**：物理字段采用完整业务中文名英译（如 `output_tax`），大模型零学习成本。  
3. **同义词集中管理**：用单独映射表存储用户口语→标准字段的映射，支持前置替换。  
4. **维度行拍平**：将“四列”拆分为 `item_type` + `time_range` 两维度，每纳税人每期仅 4 行数据，消除稀疏性。  
5. **一次设计，无限扩展**：新增税种报表只需追加明细表并增加对应视图与元数据，不破坏已有查询。  

---

## 4. 数据模型详细设计

### 4.1 一般纳税人申报表明细表（`vat_return_general`）


```sql
-- 增值税一般纳税人申报表主表
CREATE TABLE vat_return_general (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    item_type           TEXT NOT NULL,   -- '一般项目', '即征即退项目'
    time_range          TEXT NOT NULL,   -- '本月', '累计'

    -- ===== 追溯/版本（v1.1新增）=====
    revision_no         INTEGER NOT NULL DEFAULT 0,   -- 0=原始申报，1..n=更正版本
    submitted_at        TIMESTAMP,                    -- 申报提交时间（若可获取）
    etl_batch_id        TEXT,                         -- ETL批次ID
    source_doc_id       TEXT,                         -- 来源文件ID/路径hash/归档号（可选）
    source_unit         TEXT DEFAULT '元',            -- 金额单位：'元'/'万元'（可选）
    etl_confidence      REAL,                         -- OCR/解析置信度（0~1，可选）

    -- 41个指标列（栏次1～41）
    sales_taxable_rate            NUMERIC,  -- 第1栏：按适用税率计税销售额
    sales_goods                  NUMERIC,  -- 第2栏：应税货物销售额
    sales_services               NUMERIC,  -- 第3栏：应税劳务销售额
    sales_adjustment_check       NUMERIC,  -- 第4栏：纳税检查调整的销售额
    sales_simple_method          NUMERIC,  -- 第5栏：按简易办法计税销售额
    sales_simple_adjust_check    NUMERIC,  -- 第6栏：简易办法纳税检查调整
    sales_export_credit_refund   NUMERIC,  -- 第7栏：免、抵、退办法出口销售额
    sales_tax_free               NUMERIC,  -- 第8栏：免税销售额
    sales_tax_free_goods         NUMERIC,  -- 第9栏：免税货物销售额
    sales_tax_free_services      NUMERIC,  -- 第10栏：免税劳务销售额
    output_tax                   NUMERIC,  -- 第11栏：销项税额
    input_tax                    NUMERIC,  -- 第12栏：进项税额
    last_period_credit           NUMERIC,  -- 第13栏：上期留抵税额
    transfer_out                 NUMERIC,  -- 第14栏：进项税额转出
    export_refund                NUMERIC,  -- 第15栏：免、抵、退应退税额
    tax_check_supplement         NUMERIC,  -- 第16栏：按适用税率计算的纳税检查应补缴税额
    deductible_total             NUMERIC,  -- 第17栏：应抵扣税额合计
    actual_deduct                NUMERIC,  -- 第18栏：实际抵扣税额
    tax_payable                  NUMERIC,  -- 第19栏：应纳税额
    end_credit                   NUMERIC,  -- 第20栏：期末留抵税额
    simple_tax                   NUMERIC,  -- 第21栏：简易计税办法计算的应纳税额
    simple_tax_check_supplement  NUMERIC,  -- 第22栏：按简易计税办法计算的纳税检查应补缴税额
    tax_reduction                NUMERIC,  -- 第23栏：应纳税额减征额
    total_tax_payable            NUMERIC,  -- 第24栏：应纳税额合计
    unpaid_begin                 NUMERIC,  -- 第25栏：期初未缴税额（多缴为负数）
    export_receipt_tax           NUMERIC,  -- 第26栏：实收出口开具专用缴款书退税额
    paid_current                 NUMERIC,  -- 第27栏：本期已缴税额
    prepaid_installment          NUMERIC,  -- 第28栏：分次预缴税额
    prepaid_export_receipt       NUMERIC,  -- 第29栏：出口开具专用缴款书预缴税额
    paid_last_period             NUMERIC,  -- 第30栏：本期缴纳上期应纳税额
    paid_arrears                 NUMERIC,  -- 第31栏：本期缴纳欠缴税额
    unpaid_end                   NUMERIC,  -- 第32栏：期末未缴税额
    arrears                      NUMERIC,  -- 第33栏：欠缴税额
    supplement_refund            NUMERIC,  -- 第34栏：本期应补退税额
    immediate_refund             NUMERIC,  -- 第35栏：即征即退实际退税额
    unpaid_check_begin           NUMERIC,  -- 第36栏：期初未缴查补税额
    paid_check_current           NUMERIC,  -- 第37栏：本期入库查补税额
    unpaid_check_end             NUMERIC,  -- 第38栏：期末未缴查补税额
    city_maintenance_tax         NUMERIC,  -- 第39栏：城市维护建设税本期应补（退）税额
    education_surcharge          NUMERIC,  -- 第40栏：教育费附加本期应补（退）费额
    local_education_surcharge    NUMERIC,  -- 第41栏：地方教育附加本期应补（退）费额

    -- v1.1：主键加入 revision_no，支持更正申报并存
    PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no),

    -- v1.1：枚举约束，避免ETL写入脏维度值
    CHECK (item_type IN ('一般项目', '即征即退项目')),
    CHECK (time_range IN ('本月', '累计')),
    CHECK (revision_no >= 0)
);

-- 常用索引（SQLite 无分区，用索引加速）
CREATE INDEX idx_vat_period ON vat_return_general (period_year, period_month);
CREATE INDEX idx_vat_taxpayer ON vat_return_general (taxpayer_id);

-- v1.1：复合索引，覆盖最常见查询（按企业+期次）
CREATE INDEX idx_general_taxpayer_period 
ON vat_return_general (taxpayer_id, period_year, period_month);
```

### 4.2 小规模纳税人申报表明细表（`vat_return_small`）



```sql
-- 小规模纳税人申报表主表
CREATE TABLE vat_return_small (
    -- 维度
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    item_type           TEXT NOT NULL,   -- '货物及劳务', '服务不动产无形资产'
    time_range          TEXT NOT NULL,   -- '本期', '累计'

    -- ===== 追溯/版本（v1.1新增）=====
    revision_no         INTEGER NOT NULL DEFAULT 0,   -- 0=原始申报，1..n=更正版本
    submitted_at        TIMESTAMP,                    -- 申报提交时间（若可获取）
    etl_batch_id        TEXT,                         -- ETL批次ID
    source_doc_id       TEXT,                         -- 来源文件ID/路径hash/归档号（可选）
    source_unit         TEXT DEFAULT '元',            -- 金额单位：'元'/'万元'（可选）
    etl_confidence      REAL,                         -- OCR/解析置信度（0~1，可选）

    -- 25个指标列（对应栏次1～25，字段名直接使用业务术语）
    -- 计税依据部分
    sales_3percent              NUMERIC,  -- 第1栏：应征增值税不含税销售额（3%征收率）
    sales_3percent_invoice_spec NUMERIC,  -- 第2栏：增值税专用发票不含税销售额
    sales_3percent_invoice_other NUMERIC, -- 第3栏：其他增值税发票不含税销售额
    sales_5percent              NUMERIC,  -- 第4栏：应征增值税不含税销售额（5%征收率）
    sales_5percent_invoice_spec NUMERIC,  -- 第5栏：增值税专用发票不含税销售额（注：图中缺第5栏，实际应为5%专用发票销售额，此处补齐）
    sales_5percent_invoice_other NUMERIC, -- 第6栏：其他增值税发票不含税销售额
    sales_used_assets           NUMERIC,  -- 第7栏：销售使用过的固定资产不含税销售额
    sales_used_assets_invoice_other NUMERIC, -- 第8栏：其中其他增值税发票不含税销售额
    sales_tax_free             NUMERIC,  -- 第9栏：免税销售额
    sales_tax_free_micro       NUMERIC,  -- 第10栏：小微企业免税销售额
    sales_tax_free_threshold   NUMERIC,  -- 第11栏：未达起征点销售额
    sales_tax_free_other       NUMERIC,  -- 第12栏：其他免税销售额
    sales_export_tax_free      NUMERIC,  -- 第13栏：出口免税销售额
    sales_export_tax_free_invoice_other NUMERIC, -- 第14栏：其中其他增值税发票不含税销售额

    -- 税款计算
    tax_due_current            NUMERIC,  -- 第15栏：本期应纳税额
    tax_due_reduction          NUMERIC,  -- 第16栏：本期应纳税额减征额
    tax_free_amount            NUMERIC,  -- 第17栏：本期免税额
    tax_free_micro             NUMERIC,  -- 第18栏：其中小微企业免税额
    tax_free_threshold         NUMERIC,  -- 第19栏：未达起征点免税额（图中标为19栏，需确认）
    tax_due_total              NUMERIC,  -- 第20栏：应纳税额合计（=15-16）
    tax_prepaid                NUMERIC,  -- 第21栏：本期预缴税额
    tax_supplement_refund      NUMERIC,  -- 第22栏：本期应补（退）税额（=20-21）

    -- 附加税费
    city_maintenance_tax       NUMERIC,  -- 第23栏：城市维护建设税本期应补（退）税额
    education_surcharge        NUMERIC,  -- 第24栏：教育费附加本期应补（退）费额
    local_education_surcharge  NUMERIC,  -- 第25栏：地方教育附加本期应补（退）费额

    -- v1.1：主键加入 revision_no，支持更正申报并存
    PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no),

    -- v1.1：枚举约束，避免ETL写入脏维度值
    CHECK (item_type IN ('货物及劳务', '服务不动产无形资产')),
    CHECK (time_range IN ('本期', '累计')),
    CHECK (revision_no >= 0)
);

CREATE INDEX idx_small_period ON vat_return_small (period_year, period_month);
CREATE INDEX idx_small_taxpayer ON vat_return_small (taxpayer_id);

-- v1.1：复合索引，覆盖最常见查询（按企业+期次）
CREATE INDEX idx_small_taxpayer_period 
ON vat_return_small (taxpayer_id, period_year, period_month);
```

### 4.3 纳税人信息表（`taxpayer_info`）

目标：把“企业是谁、在哪、归谁管、什么行业、什么纳税人属性、信用等级如何”结构化出来，让画像、分组统计、穿透筛选都能用 **JOIN 维表** 完成，而不是靠文本模糊匹配。

**推荐建模：一张主维表 + 若干快照**

#### 4.3.1 主维表（增强版 `taxpayer_info`）

> 保持 `taxpayer_id` 稳定主键；把变化频繁/可能历史变更的字段拆到“快照表”（见 1.2）。

```sql
CREATE TABLE IF NOT EXISTS taxpayer_info (
  taxpayer_id           TEXT PRIMARY KEY,            -- 统一社会信用代码/纳税人识别号
  taxpayer_name         TEXT NOT NULL,

  taxpayer_type         TEXT NOT NULL,               -- '一般纳税人'/'小规模纳税人'
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

CREATE INDEX IF NOT EXISTS idx_taxpayer_name ON taxpayer_info(taxpayer_name);
CREATE INDEX IF NOT EXISTS idx_taxpayer_industry ON taxpayer_info(industry_code);
CREATE INDEX IF NOT EXISTS idx_taxpayer_region ON taxpayer_info(region_code);
CREATE INDEX IF NOT EXISTS idx_taxpayer_authority ON taxpayer_info(tax_authority_code);
```

**关键点**
- 行业/税务机关/区划都尽量“编码 + 名称”双存，方便标准化、避免同名歧义。
- `credit_grade_current` 只能表示“当前口径”，如果要做历史趋势或按年对比，必须用快照表（下一节）。

---

### 4.3.2 强烈建议：属性快照表（SCD2 / 按月按年快照）

典型会变的字段：`tax_authority`、`credit_grade`、甚至 `industry`（企业变更经营范围后可能调整）。  
为保证“查询某个期间时，企业属性与当期一致”，建议引入快照表：

#### 4.3.2.1 按月快照（适合与 VAT/月度财务对齐）
```sql
CREATE TABLE IF NOT EXISTS taxpayer_profile_snapshot_month (
  taxpayer_id        TEXT NOT NULL,
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

  PRIMARY KEY (taxpayer_id, period_year, period_month),
  FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
);

CREATE INDEX IF NOT EXISTS idx_snap_month_industry
ON taxpayer_profile_snapshot_month(period_year, period_month, industry_code);

CREATE INDEX IF NOT EXISTS idx_snap_month_credit
ON taxpayer_profile_snapshot_month(period_year, period_month, credit_grade);
```

#### 4.3.2.2 按年快照（适合纳税信用等级“年度发布”的现实）
```sql
CREATE TABLE IF NOT EXISTS taxpayer_credit_grade_year (
  taxpayer_id    TEXT NOT NULL,
  year           INTEGER NOT NULL,
  credit_grade   TEXT NOT NULL,     -- A/B/M/C/D
  published_at   DATE,
  source_doc_id  TEXT,
  etl_batch_id   TEXT,
  PRIMARY KEY (taxpayer_id, year),
  FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
);

CREATE INDEX IF NOT EXISTS idx_credit_year_grade
ON taxpayer_credit_grade_year(year, credit_grade);
```

> 选择建议：  
> - 若你们的下游分析绝大多数按“申报期（月）”跑，优先“按月快照”。  
> - 若只关心信用等级且它按年发布，单独做按年表最干净。


---


### 最佳实践：**三层次容错体系**



| 层级 | 存储形式 | 作用 | NL2SQL 阶段 |
|------|--------|------|------------|
| **精准对照** | SQLite 表 `vat_column_mapping` | 字段 ↔ 栏次号（1:1） | 用于**栏次号查询**的精确转换 |
| **同义词库** | SQLite 表 `vat_synonyms` + JSON | 自然语言短语 → 标准字段名（n:1） | 用于**用户问题实体识别**，标准化字段 |
| **Prompt 语义** | 系统提示词 | 大模型直接理解业务含义 | 兜底，利用大模型泛化能力 |

**三者协同**：同义词库做第一道标准化 → 精准对照转栏次 → 大模型语义兜底。

### 4.4 栏次-字段映射表（ETL 专用）

#### 一般纳税人映射表（`vat_general_column_mapping`）
```sql
-- 创建一般纳税人栏次映射表
CREATE TABLE IF NOT EXISTS vat_general_column_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

-- 插入41条映射记录
INSERT OR REPLACE INTO vat_general_column_mapping (line_number, column_name, business_name) VALUES
(1,  'sales_taxable_rate', '按适用税率计税销售额'),
(2,  'sales_goods', '应税货物销售额'),
(3,  'sales_services', '应税劳务销售额'),
(4,  'sales_adjustment_check', '纳税检查调整的销售额'),
(5,  'sales_simple_method', '按简易办法计税销售额'),
(6,  'sales_simple_adjust_check', '简易办法纳税检查调整'),
(7,  'sales_export_credit_refund', '免、抵、退办法出口销售额'),
(8,  'sales_tax_free', '免税销售额'),
(9,  'sales_tax_free_goods', '免税货物销售额'),
(10, 'sales_tax_free_services', '免税劳务销售额'),
(11, 'output_tax', '销项税额'),
(12, 'input_tax', '进项税额'),
(13, 'last_period_credit', '上期留抵税额'),
(14, 'transfer_out', '进项税额转出'),
(15, 'export_refund', '免、抵、退应退税额'),
(16, 'tax_check_supplement', '按适用税率计算的纳税检查应补缴税额'),
(17, 'deductible_total', '应抵扣税额合计'),
(18, 'actual_deduct', '实际抵扣税额'),
(19, 'tax_payable', '应纳税额'),
(20, 'end_credit', '期末留抵税额'),
(21, 'simple_tax', '简易计税办法计算的应纳税额'),
(22, 'simple_tax_check_supplement', '按简易计税办法计算的纳税检查应补缴税额'),
(23, 'tax_reduction', '应纳税额减征额'),
(24, 'total_tax_payable', '应纳税额合计'),
(25, 'unpaid_begin', '期初未缴税额'),
(26, 'export_receipt_tax', '实收出口开具专用缴款书退税额'),
(27, 'paid_current', '本期已缴税额'),
(28, 'prepaid_installment', '分次预缴税额'),
(29, 'prepaid_export_receipt', '出口开具专用缴款书预缴税额'),
(30, 'paid_last_period', '本期缴纳上期应纳税额'),
(31, 'paid_arrears', '本期缴纳欠缴税额'),
(32, 'unpaid_end', '期末未缴税额'),
(33, 'arrears', '欠缴税额'),
(34, 'supplement_refund', '本期应补退税额'),
(35, 'immediate_refund', '即征即退实际退税额'),
(36, 'unpaid_check_begin', '期初未缴查补税额'),
(37, 'paid_check_current', '本期入库查补税额'),
(38, 'unpaid_check_end', '期末未缴查补税额'),
(39, 'city_maintenance_tax', '城市维护建设税本期应补（退）税额'),
(40, 'education_surcharge', '教育费附加本期应补（退）费额'),
(41, 'local_education_surcharge', '地方教育附加本期应补（退）费额');
```

#### 小规模纳税人映射表（`vat_small_column_mapping`）
```sql
-- 创建小规模纳税人栏次映射表
CREATE TABLE IF NOT EXISTS vat_small_column_mapping (
    line_number INTEGER PRIMARY KEY,
    column_name TEXT NOT NULL,
    business_name TEXT
);

-- 插入25条映射记录
INSERT OR REPLACE INTO vat_small_column_mapping (line_number, column_name, business_name) VALUES
(1,  'sales_3percent', '应征增值税不含税销售额（3%征收率）'),
(2,  'sales_3percent_invoice_spec', '增值税专用发票不含税销售额'),
(3,  'sales_3percent_invoice_other', '其他增值税发票不含税销售额'),
(4,  'sales_5percent', '应征增值税不含税销售额（5%征收率）'),
(5,  'sales_5percent_invoice_spec', '增值税专用发票不含税销售额（5%征收率）'),
(6,  'sales_5percent_invoice_other', '其他增值税发票不含税销售额（5%征收率）'),
(7,  'sales_used_assets', '销售使用过的固定资产不含税销售额'),
(8,  'sales_used_assets_invoice_other', '其中其他增值税发票不含税销售额'),
(9,  'sales_tax_free', '免税销售额'),
(10, 'sales_tax_free_micro', '小微企业免税销售额'),
(11, 'sales_tax_free_threshold', '未达起征点销售额'),
(12, 'sales_tax_free_other', '其他免税销售额'),
(13, 'sales_export_tax_free', '出口免税销售额'),
(14, 'sales_export_tax_free_invoice_other', '其中其他增值税发票不含税销售额'),
(15, 'tax_due_current', '本期应纳税额'),
(16, 'tax_due_reduction', '本期应纳税额减征额'),
(17, 'tax_free_amount', '本期免税额'),
(18, 'tax_free_micro', '其中小微企业免税额'),
(19, 'tax_free_threshold', '未达起征点免税额'),
(20, 'tax_due_total', '应纳税额合计'),
(21, 'tax_prepaid', '本期预缴税额'),
(22, 'tax_supplement_refund', '本期应补（退）税额'),
(23, 'city_maintenance_tax', '城市维护建设税本期应补（退）税额'),
(24, 'education_surcharge', '教育费附加本期应补（退）费额'),
(25, 'local_education_surcharge', '地方教育附加本期应补（退）费额');
```

**作用**：ETL 解析 PDF/Excel 时，根据栏次号直接获取目标字段名，完成行列转换。

### 4.5 同义词映射表（NL2SQL 专用）

#### 4.5.1 表结构增强（v1.1新增，兼容原数据）

```sql
-- ============================================
-- 1. 创建同义词映射表（若不存在）
-- ============================================
CREATE TABLE IF NOT EXISTS vat_synonyms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase      TEXT NOT NULL,
    column_name TEXT NOT NULL,
    priority    INTEGER DEFAULT 1,

    -- v1.1新增：用于解决“同词不同字段”与跨类型歧义
    taxpayer_type TEXT,     -- '一般纳税人'/'小规模纳税人'/NULL(通用)
    scope_view    TEXT,     -- 'vw_vat_return_general'/'vw_vat_return_small'/NULL(通用)

    UNIQUE(phrase, column_name)
);
CREATE INDEX IF NOT EXISTS idx_synonyms_phrase ON vat_synonyms(phrase);
CREATE INDEX IF NOT EXISTS idx_synonyms_scope ON vat_synonyms(scope_view, taxpayer_type, priority);
```

#### 4.5.2（保留原文）原同义词 INSERT 脚本

-- 2. 一般纳税人 41 个字段同义词
-- ============================================

-- 第1栏：sales_taxable_rate
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第1栏', 'sales_taxable_rate', 3),
    ('1栏', 'sales_taxable_rate', 3),
    ('栏次1', 'sales_taxable_rate', 3),
    ('按适用税率计税销售额', 'sales_taxable_rate', 2),
    ('适用税率计税销售额', 'sales_taxable_rate', 2),
    ('计税销售额', 'sales_taxable_rate', 1),
    ('适用税率销售额', 'sales_taxable_rate', 1),
    ('一般计税销售额', 'sales_taxable_rate', 1);

-- 第2栏：sales_goods
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第2栏', 'sales_goods', 3),
    ('2栏', 'sales_goods', 3),
    ('栏次2', 'sales_goods', 3),
    ('应税货物销售额', 'sales_goods', 2),
    ('货物销售额', 'sales_goods', 1),
    ('应税货物', 'sales_goods', 1);

-- 第3栏：sales_services
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第3栏', 'sales_services', 3),
    ('3栏', 'sales_services', 3),
    ('栏次3', 'sales_services', 3),
    ('应税劳务销售额', 'sales_services', 2),
    ('应税服务销售额', 'sales_services', 2),
    ('劳务销售额', 'sales_services', 1),
    ('服务销售额', 'sales_services', 1),
    ('应税劳务', 'sales_services', 1),
    ('应税服务', 'sales_services', 1);

-- 第4栏：sales_adjustment_check
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第4栏', 'sales_adjustment_check', 3),
    ('4栏', 'sales_adjustment_check', 3),
    ('栏次4', 'sales_adjustment_check', 3),
    ('纳税检查调整的销售额', 'sales_adjustment_check', 2),
    ('查补销售额', 'sales_adjustment_check', 1),
    ('纳税检查销售额', 'sales_adjustment_check', 1),
    ('税务检查调整销售额', 'sales_adjustment_check', 1);

-- 第5栏：sales_simple_method
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第5栏', 'sales_simple_method', 3),
    ('5栏', 'sales_simple_method', 3),
    ('栏次5', 'sales_simple_method', 3),
    ('按简易办法计税销售额', 'sales_simple_method', 2),
    ('简易计税销售额', 'sales_simple_method', 1),
    ('简易办法销售额', 'sales_simple_method', 1);

-- 第6栏：sales_simple_adjust_check
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第6栏', 'sales_simple_adjust_check', 3),
    ('6栏', 'sales_simple_adjust_check', 3),
    ('栏次6', 'sales_simple_adjust_check', 3),
    ('简易办法纳税检查调整', 'sales_simple_adjust_check', 2),
    ('简易计税查补销售额', 'sales_simple_adjust_check', 1),
    ('简易查补销售额', 'sales_simple_adjust_check', 1),
    ('简易纳税检查调整', 'sales_simple_adjust_check', 1);

-- 第7栏：sales_export_credit_refund
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第7栏', 'sales_export_credit_refund', 3),
    ('7栏', 'sales_export_credit_refund', 3),
    ('栏次7', 'sales_export_credit_refund', 3),
    ('免、抵、退办法出口销售额', 'sales_export_credit_refund', 2),
    ('免抵退出口销售额', 'sales_export_credit_refund', 1),
    ('出口免抵退销售额', 'sales_export_credit_refund', 1);

-- 第8栏：sales_tax_free
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第8栏', 'sales_tax_free', 3),
    ('8栏', 'sales_tax_free', 3),
    ('栏次8', 'sales_tax_free', 3),
    ('免税销售额', 'sales_tax_free', 2),
    ('免税销售', 'sales_tax_free', 1);

-- 第9栏：sales_tax_free_goods
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第9栏', 'sales_tax_free_goods', 3),
    ('9栏', 'sales_tax_free_goods', 3),
    ('栏次9', 'sales_tax_free_goods', 3),
    ('免税货物销售额', 'sales_tax_free_goods', 2),
    ('免税货物', 'sales_tax_free_goods', 1);

-- 第10栏：sales_tax_free_services
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第10栏', 'sales_tax_free_services', 3),
    ('10栏', 'sales_tax_free_services', 3),
    ('栏次10', 'sales_tax_free_services', 3),
    ('免税劳务销售额', 'sales_tax_free_services', 2),
    ('免税服务销售额', 'sales_tax_free_services', 2),
    ('免税劳务', 'sales_tax_free_services', 1),
    ('免税服务', 'sales_tax_free_services', 1);

-- 第11栏：output_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第11栏', 'output_tax', 3),
    ('11栏', 'output_tax', 3),
    ('栏次11', 'output_tax', 3),
    ('销项税额', 'output_tax', 2),
    ('销项税', 'output_tax', 1),
    ('销项', 'output_tax', 1);

-- 第12栏：input_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第12栏', 'input_tax', 3),
    ('12栏', 'input_tax', 3),
    ('栏次12', 'input_tax', 3),
    ('进项税额', 'input_tax', 2),
    ('进项税', 'input_tax', 1),
    ('进项', 'input_tax', 1);

-- 第13栏：last_period_credit
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第13栏', 'last_period_credit', 3),
    ('13栏', 'last_period_credit', 3),
    ('栏次13', 'last_period_credit', 3),
    ('上期留抵税额', 'last_period_credit', 2),
    ('上期留抵', 'last_period_credit', 1),
    ('期初留抵税额', 'last_period_credit', 1);

-- 第14栏：transfer_out
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第14栏', 'transfer_out', 3),
    ('14栏', 'transfer_out', 3),
    ('栏次14', 'transfer_out', 3),
    ('进项税额转出', 'transfer_out', 2),
    ('进项转出', 'transfer_out', 1),
    ('进项税额转出额', 'transfer_out', 1);

-- 第15栏：export_refund
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第15栏', 'export_refund', 3),
    ('15栏', 'export_refund', 3),
    ('栏次15', 'export_refund', 3),
    ('免、抵、退应退税额', 'export_refund', 2),
    ('免抵退应退税额', 'export_refund', 1),
    ('出口退税应退额', 'export_refund', 1),
    ('应退税额', 'export_refund', 1);

-- 第16栏：tax_check_supplement
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第16栏', 'tax_check_supplement', 3),
    ('16栏', 'tax_check_supplement', 3),
    ('栏次16', 'tax_check_supplement', 3),
    ('按适用税率计算的纳税检查应补缴税额', 'tax_check_supplement', 2),
    ('查补税额', 'tax_check_supplement', 1),
    ('纳税检查补税', 'tax_check_supplement', 1),
    ('适用税率查补税额', 'tax_check_supplement', 1);

-- 第17栏：deductible_total
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第17栏', 'deductible_total', 3),
    ('17栏', 'deductible_total', 3),
    ('栏次17', 'deductible_total', 3),
    ('应抵扣税额合计', 'deductible_total', 2),
    ('应抵扣税额', 'deductible_total', 1),
    ('应抵扣合计', 'deductible_total', 1);

-- 第18栏：actual_deduct
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第18栏', 'actual_deduct', 3),
    ('18栏', 'actual_deduct', 3),
    ('栏次18', 'actual_deduct', 3),
    ('实际抵扣税额', 'actual_deduct', 2),
    ('实际抵扣', 'actual_deduct', 1),
    ('实抵扣税额', 'actual_deduct', 1);

-- 第19栏：tax_payable
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第19栏', 'tax_payable', 3),
    ('19栏', 'tax_payable', 3),
    ('栏次19', 'tax_payable', 3),
    ('应纳税额', 'tax_payable', 2),
    ('应纳增值税', 'tax_payable', 1),
    ('应纳额', 'tax_payable', 1),
    ('增值税应纳税额', 'tax_payable', 1);

-- 第20栏：end_credit
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第20栏', 'end_credit', 3),
    ('20栏', 'end_credit', 3),
    ('栏次20', 'end_credit', 3),
    ('期末留抵税额', 'end_credit', 2),
    ('期末留抵', 'end_credit', 1),
    ('留抵税额', 'end_credit', 1);

-- 第21栏：simple_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第21栏', 'simple_tax', 3),
    ('21栏', 'simple_tax', 3),
    ('栏次21', 'simple_tax', 3),
    ('简易计税办法计算的应纳税额', 'simple_tax', 2),
    ('简易计税应纳税额', 'simple_tax', 1),
    ('简易办法应纳税额', 'simple_tax', 1),
    ('简易应纳', 'simple_tax', 1);

-- 第22栏：simple_tax_check_supplement
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第22栏', 'simple_tax_check_supplement', 3),
    ('22栏', 'simple_tax_check_supplement', 3),
    ('栏次22', 'simple_tax_check_supplement', 3),
    ('按简易计税办法计算的纳税检查应补缴税额', 'simple_tax_check_supplement', 2),
    ('简易计税查补税额', 'simple_tax_check_supplement', 1),
    ('简易查补', 'simple_tax_check_supplement', 1),
    ('简易办法查补税额', 'simple_tax_check_supplement', 1);

-- 第23栏：tax_reduction
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第23栏', 'tax_reduction', 3),
    ('23栏', 'tax_reduction', 3),
    ('栏次23', 'tax_reduction', 3),
    ('应纳税额减征额', 'tax_reduction', 2),
    ('减征额', 'tax_reduction', 1),
    ('应纳税额减征', 'tax_reduction', 1),
    ('税额减征', 'tax_reduction', 1);

-- 第24栏：total_tax_payable
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第24栏', 'total_tax_payable', 3),
    ('24栏', 'total_tax_payable', 3),
    ('栏次24', 'total_tax_payable', 3),
    ('应纳税额合计', 'total_tax_payable', 2),
    ('应纳税合计', 'total_tax_payable', 1),
    ('应纳总额', 'total_tax_payable', 1),
    ('本期应纳合计', 'total_tax_payable', 1);

-- 第25栏：unpaid_begin
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第25栏', 'unpaid_begin', 3),
    ('25栏', 'unpaid_begin', 3),
    ('栏次25', 'unpaid_begin', 3),
    ('期初未缴税额', 'unpaid_begin', 2),
    ('期初未缴', 'unpaid_begin', 1),
    ('期初欠税', 'unpaid_begin', 1),
    ('期初应缴未缴', 'unpaid_begin', 1);

-- 第26栏：export_receipt_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第26栏', 'export_receipt_tax', 3),
    ('26栏', 'export_receipt_tax', 3),
    ('栏次26', 'export_receipt_tax', 3),
    ('实收出口开具专用缴款书退税额', 'export_receipt_tax', 2),
    ('出口专用缴款书退税额', 'export_receipt_tax', 1),
    ('实收出口退税额', 'export_receipt_tax', 1);

-- 第27栏：paid_current
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第27栏', 'paid_current', 3),
    ('27栏', 'paid_current', 3),
    ('栏次27', 'paid_current', 3),
    ('本期已缴税额', 'paid_current', 2),
    ('本期已缴', 'paid_current', 1),
    ('本期实缴', 'paid_current', 1);

-- 第28栏：prepaid_installment
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第28栏', 'prepaid_installment', 3),
    ('28栏', 'prepaid_installment', 3),
    ('栏次28', 'prepaid_installment', 3),
    ('分次预缴税额', 'prepaid_installment', 2),
    ('分次预缴', 'prepaid_installment', 1),
    ('预缴税额', 'prepaid_installment', 1),
    ('预缴税款', 'prepaid_installment', 1);

-- 第29栏：prepaid_export_receipt
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第29栏', 'prepaid_export_receipt', 3),
    ('29栏', 'prepaid_export_receipt', 3),
    ('栏次29', 'prepaid_export_receipt', 3),
    ('出口开具专用缴款书预缴税额', 'prepaid_export_receipt', 2),
    ('出口预缴税额', 'prepaid_export_receipt', 1),
    ('专用缴款书预缴', 'prepaid_export_receipt', 1);

-- 第30栏：paid_last_period
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第30栏', 'paid_last_period', 3),
    ('30栏', 'paid_last_period', 3),
    ('栏次30', 'paid_last_period', 3),
    ('本期缴纳上期应纳税额', 'paid_last_period', 2),
    ('缴纳上期税额', 'paid_last_period', 1),
    ('上期税款本期缴纳', 'paid_last_period', 1);

-- 第31栏：paid_arrears
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第31栏', 'paid_arrears', 3),
    ('31栏', 'paid_arrears', 3),
    ('栏次31', 'paid_arrears', 3),
    ('本期缴纳欠缴税额', 'paid_arrears', 2),
    ('缴纳欠税', 'paid_arrears', 1),
    ('欠税缴纳', 'paid_arrears', 1),
    ('本期缴欠税', 'paid_arrears', 1);

-- 第32栏：unpaid_end
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第32栏', 'unpaid_end', 3),
    ('32栏', 'unpaid_end', 3),
    ('栏次32', 'unpaid_end', 3),
    ('期末未缴税额', 'unpaid_end', 2),
    ('期末未缴', 'unpaid_end', 1),
    ('期末欠税', 'unpaid_end', 1);

-- 第33栏：arrears
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第33栏', 'arrears', 3),
    ('33栏', 'arrears', 3),
    ('栏次33', 'arrears', 3),
    ('欠缴税额', 'arrears', 2),
    ('欠税', 'arrears', 1),
    ('欠缴税款', 'arrears', 1),
    ('期末欠缴', 'arrears', 1);

-- 第34栏：supplement_refund
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第34栏', 'supplement_refund', 3),
    ('34栏', 'supplement_refund', 3),
    ('栏次34', 'supplement_refund', 3),
    ('本期应补退税额', 'supplement_refund', 2),
    ('应补退税额', 'supplement_refund', 1),
    ('应补退税', 'supplement_refund', 1),
    ('补退税', 'supplement_refund', 1);

-- 第35栏：immediate_refund
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第35栏', 'immediate_refund', 3),
    ('35栏', 'immediate_refund', 3),
    ('栏次35', 'immediate_refund', 3),
    ('即征即退实际退税额', 'immediate_refund', 2),
    ('即征即退税额', 'immediate_refund', 1),
    ('即征即退退税额', 'immediate_refund', 1);

-- 第36栏：unpaid_check_begin
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第36栏', 'unpaid_check_begin', 3),
    ('36栏', 'unpaid_check_begin', 3),
    ('栏次36', 'unpaid_check_begin', 3),
    ('期初未缴查补税额', 'unpaid_check_begin', 2),
    ('期初查补税额', 'unpaid_check_begin', 1),
    ('查补期初未缴', 'unpaid_check_begin', 1);

-- 第37栏：paid_check_current
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第37栏', 'paid_check_current', 3),
    ('37栏', 'paid_check_current', 3),
    ('栏次37', 'paid_check_current', 3),
    ('本期入库查补税额', 'paid_check_current', 2),
    ('查补入库税额', 'paid_check_current', 1),
    ('本期查补入库', 'paid_check_current', 1);

-- 第38栏：unpaid_check_end
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第38栏', 'unpaid_check_end', 3),
    ('38栏', 'unpaid_check_end', 3),
    ('栏次38', 'unpaid_check_end', 3),
    ('期末未缴查补税额', 'unpaid_check_end', 2),
    ('期末查补税额', 'unpaid_check_end', 1),
    ('查补期末未缴', 'unpaid_check_end', 1);

-- 第39栏：city_maintenance_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第39栏', 'city_maintenance_tax', 3),
    ('39栏', 'city_maintenance_tax', 3),
    ('栏次39', 'city_maintenance_tax', 3),
    ('城市维护建设税本期应补退税额', 'city_maintenance_tax', 2),
    ('城市维护建设税应补退税额', 'city_maintenance_tax', 2),
    ('城建税', 'city_maintenance_tax', 1),
    ('城市维护建设税', 'city_maintenance_tax', 1),
    ('城建税应补退', 'city_maintenance_tax', 1);

-- 第40栏：education_surcharge
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第40栏', 'education_surcharge', 3),
    ('40栏', 'education_surcharge', 3),
    ('栏次40', 'education_surcharge', 3),
    ('教育费附加本期应补退费额', 'education_surcharge', 2),
    ('教育费附加应补退费额', 'education_surcharge', 2),
    ('教育费附加', 'education_surcharge', 1),
    ('教育附加', 'education_surcharge', 1),
    ('教育费附加应补退', 'education_surcharge', 1);

-- 第41栏：local_education_surcharge
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第41栏', 'local_education_surcharge', 3),
    ('41栏', 'local_education_surcharge', 3),
    ('栏次41', 'local_education_surcharge', 3),
    ('地方教育附加本期应补退费额', 'local_education_surcharge', 2),
    ('地方教育附加应补退费额', 'local_education_surcharge', 2),
    ('地方教育附加', 'local_education_surcharge', 1),
    ('地方教育费附加', 'local_education_surcharge', 1),
    ('地方附加应补退', 'local_education_surcharge', 1);

-- ============================================
-- 3. 小规模纳税人 25 个字段同义词
-- ============================================

-- 第1栏：sales_3percent
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第1栏', 'sales_3percent', 3),
    ('1栏', 'sales_3percent', 3),
    ('栏次1', 'sales_3percent', 3),
    ('应征增值税不含税销售额（3%征收率）', 'sales_3percent', 2),
    ('3%销售额', 'sales_3percent', 1),
    ('3%不含税销售额', 'sales_3percent', 1),
    ('3%征收率销售额', 'sales_3percent', 1),
    ('应征增值税销售额3%', 'sales_3percent', 1);

-- 第2栏：sales_3percent_invoice_spec
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第2栏', 'sales_3percent_invoice_spec', 3),
    ('2栏', 'sales_3percent_invoice_spec', 3),
    ('栏次2', 'sales_3percent_invoice_spec', 3),
    ('增值税专用发票不含税销售额', 'sales_3percent_invoice_spec', 2),
    ('3%专票销售额', 'sales_3percent_invoice_spec', 1),
    ('专用发票销售额', 'sales_3percent_invoice_spec', 1);

-- 第3栏：sales_3percent_invoice_other
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第3栏', 'sales_3percent_invoice_other', 3),
    ('3栏', 'sales_3percent_invoice_other', 3),
    ('栏次3', 'sales_3percent_invoice_other', 3),
    ('其他增值税发票不含税销售额', 'sales_3percent_invoice_other', 2),
    ('3%其他发票销售额', 'sales_3percent_invoice_other', 1),
    ('其他发票销售额', 'sales_3percent_invoice_other', 1),
    ('普票销售额', 'sales_3percent_invoice_other', 1);

-- 第4栏：sales_5percent
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第4栏', 'sales_5percent', 3),
    ('4栏', 'sales_5percent', 3),
    ('栏次4', 'sales_5percent', 3),
    ('应征增值税不含税销售额（5%征收率）', 'sales_5percent', 2),
    ('5%销售额', 'sales_5percent', 1),
    ('5%不含税销售额', 'sales_5percent', 1),
    ('5%征收率销售额', 'sales_5percent', 1);

-- 第5栏：sales_5percent_invoice_spec
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第5栏', 'sales_5percent_invoice_spec', 3),
    ('5栏', 'sales_5percent_invoice_spec', 3),
    ('栏次5', 'sales_5percent_invoice_spec', 3),
    ('增值税专用发票不含税销售额（5%征收率）', 'sales_5percent_invoice_spec', 2),
    ('5%专票销售额', 'sales_5percent_invoice_spec', 1),
    ('5%专用发票销售额', 'sales_5percent_invoice_spec', 1);

-- 第6栏：sales_5percent_invoice_other
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第6栏', 'sales_5percent_invoice_other', 3),
    ('6栏', 'sales_5percent_invoice_other', 3),
    ('栏次6', 'sales_5percent_invoice_other', 3),
    ('其他增值税发票不含税销售额（5%征收率）', 'sales_5percent_invoice_other', 2),
    ('5%其他发票销售额', 'sales_5percent_invoice_other', 1),
    ('5%普票销售额', 'sales_5percent_invoice_other', 1);

-- 第7栏：sales_used_assets
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第7栏', 'sales_used_assets', 3),
    ('7栏', 'sales_used_assets', 3),
    ('栏次7', 'sales_used_assets', 3),
    ('销售使用过的固定资产不含税销售额', 'sales_used_assets', 2),
    ('销售旧固定资产销售额', 'sales_used_assets', 1),
    ('使用过的固定资产销售额', 'sales_used_assets', 1);

-- 第8栏：sales_used_assets_invoice_other
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第8栏', 'sales_used_assets_invoice_other', 3),
    ('8栏', 'sales_used_assets_invoice_other', 3),
    ('栏次8', 'sales_used_assets_invoice_other', 3),
    ('其中其他增值税发票不含税销售额', 'sales_used_assets_invoice_other', 2),
    ('旧固定资产其他发票销售额', 'sales_used_assets_invoice_other', 1),
    ('旧货普票销售额', 'sales_used_assets_invoice_other', 1);

-- 第9栏：sales_tax_free
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第9栏', 'sales_tax_free', 3),
    ('9栏', 'sales_tax_free', 3),
    ('栏次9', 'sales_tax_free', 3),
    ('免税销售额', 'sales_tax_free', 2),   -- 注意：与一般纳税人字段名相同，但同义词表允许重复phrase不同column
    ('免税销售', 'sales_tax_free', 1);

-- 第10栏：sales_tax_free_micro
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第10栏', 'sales_tax_free_micro', 3),
    ('10栏', 'sales_tax_free_micro', 3),
    ('栏次10', 'sales_tax_free_micro', 3),
    ('小微企业免税销售额', 'sales_tax_free_micro', 2),
    ('小微企业免税', 'sales_tax_free_micro', 1),
    ('小微免税销售额', 'sales_tax_free_micro', 1);

-- 第11栏：sales_tax_free_threshold
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第11栏', 'sales_tax_free_threshold', 3),
    ('11栏', 'sales_tax_free_threshold', 3),
    ('栏次11', 'sales_tax_free_threshold', 3),
    ('未达起征点销售额', 'sales_tax_free_threshold', 2),
    ('未达起征点', 'sales_tax_free_threshold', 1),
    ('起征点以下销售额', 'sales_tax_free_threshold', 1);

-- 第12栏：sales_tax_free_other
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第12栏', 'sales_tax_free_other', 3),
    ('12栏', 'sales_tax_free_other', 3),
    ('栏次12', 'sales_tax_free_other', 3),
    ('其他免税销售额', 'sales_tax_free_other', 2),
    ('其他免税', 'sales_tax_free_other', 1);

-- 第13栏：sales_export_tax_free
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第13栏', 'sales_export_tax_free', 3),
    ('13栏', 'sales_export_tax_free', 3),
    ('栏次13', 'sales_export_tax_free', 3),
    ('出口免税销售额', 'sales_export_tax_free', 2),
    ('出口免税', 'sales_export_tax_free', 1),
    ('免税出口销售额', 'sales_export_tax_free', 1);

-- 第14栏：sales_export_tax_free_invoice_other
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第14栏', 'sales_export_tax_free_invoice_other', 3),
    ('14栏', 'sales_export_tax_free_invoice_other', 3),
    ('栏次14', 'sales_export_tax_free_invoice_other', 3),
    ('其中其他增值税发票不含税销售额', 'sales_export_tax_free_invoice_other', 2),
    ('出口免税其他发票销售额', 'sales_export_tax_free_invoice_other', 1),
    ('出口普票免税销售额', 'sales_export_tax_free_invoice_other', 1);

-- 第15栏：tax_due_current
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第15栏', 'tax_due_current', 3),
    ('15栏', 'tax_due_current', 3),
    ('栏次15', 'tax_due_current', 3),
    ('本期应纳税额', 'tax_due_current', 2),
    ('本期应纳', 'tax_due_current', 1),
    ('应纳税额（本期）', 'tax_due_current', 1);

-- 第16栏：tax_due_reduction
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第16栏', 'tax_due_reduction', 3),
    ('16栏', 'tax_due_reduction', 3),
    ('栏次16', 'tax_due_reduction', 3),
    ('本期应纳税额减征额', 'tax_due_reduction', 2),
    ('应纳税额减征额', 'tax_due_reduction', 1),
    ('减征额', 'tax_due_reduction', 1);   -- 与一般纳税人减征额同义，指向不同字段

-- 第17栏：tax_free_amount
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第17栏', 'tax_free_amount', 3),
    ('17栏', 'tax_free_amount', 3),
    ('栏次17', 'tax_free_amount', 3),
    ('本期免税额', 'tax_free_amount', 2),
    ('免税额', 'tax_free_amount', 1);

-- 第18栏：tax_free_micro
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第18栏', 'tax_free_micro', 3),
    ('18栏', 'tax_free_micro', 3),
    ('栏次18', 'tax_free_micro', 3),
    ('其中小微企业免税额', 'tax_free_micro', 2),
    ('小微企业免税额', 'tax_free_micro', 1),
    ('小微免税额', 'tax_free_micro', 1);

-- 第19栏：tax_free_threshold
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第19栏', 'tax_free_threshold', 3),
    ('19栏', 'tax_free_threshold', 3),
    ('栏次19', 'tax_free_threshold', 3),
    ('未达起征点免税额', 'tax_free_threshold', 2),
    ('起征点以下免税额', 'tax_free_threshold', 1);

-- 第20栏：tax_due_total
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第20栏', 'tax_due_total', 3),
    ('20栏', 'tax_due_total', 3),
    ('栏次20', 'tax_due_total', 3),
    ('应纳税额合计', 'tax_due_total', 2),   -- 与一般纳税人第24栏同义，指向不同字段
    ('应纳税合计', 'tax_due_total', 1),
    ('应纳总额', 'tax_due_total', 1),
    ('本期应纳合计', 'tax_due_total', 1);

-- 第21栏：tax_prepaid
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第21栏', 'tax_prepaid', 3),
    ('21栏', 'tax_prepaid', 3),
    ('栏次21', 'tax_prepaid', 3),
    ('本期预缴税额', 'tax_prepaid', 2),
    ('预缴税额', 'tax_prepaid', 1),
    ('本期预缴', 'tax_prepaid', 1);

-- 第22栏：tax_supplement_refund
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第22栏', 'tax_supplement_refund', 3),
    ('22栏', 'tax_supplement_refund', 3),
    ('栏次22', 'tax_supplement_refund', 3),
    ('本期应补（退）税额', 'tax_supplement_refund', 2),
    ('应补退税额', 'tax_supplement_refund', 1),
    ('应补退税', 'tax_supplement_refund', 1),
    ('补退税', 'tax_supplement_refund', 1);

-- 第23栏：city_maintenance_tax
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第23栏', 'city_maintenance_tax', 3),
    ('23栏', 'city_maintenance_tax', 3),
    ('栏次23', 'city_maintenance_tax', 3),
    ('城市维护建设税本期应补（退）税额', 'city_maintenance_tax', 2),
    ('城市维护建设税应补退税额', 'city_maintenance_tax', 2),
    ('城建税', 'city_maintenance_tax', 1),
    ('城市维护建设税', 'city_maintenance_tax', 1),
    ('城建税应补退', 'city_maintenance_tax', 1);

-- 第24栏：education_surcharge
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第24栏', 'education_surcharge', 3),
    ('24栏', 'education_surcharge', 3),
    ('栏次24', 'education_surcharge', 3),
    ('教育费附加本期应补（退）费额', 'education_surcharge', 2),
    ('教育费附加应补退费额', 'education_surcharge', 2),
    ('教育费附加', 'education_surcharge', 1),
    ('教育附加', 'education_surcharge', 1),
    ('教育费附加应补退', 'education_surcharge', 1);

-- 第25栏：local_education_surcharge
INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority) VALUES
    ('第25栏', 'local_education_surcharge', 3),
    ('25栏', 'local_education_surcharge', 3),
    ('栏次25', 'local_education_surcharge', 3),
    ('地方教育附加本期应补（退）费额', 'local_education_surcharge', 2),
    ('地方教育附加应补退费额', 'local_education_surcharge', 2),
    ('地方教育附加', 'local_education_surcharge', 1),
    ('地方教育费附加', 'local_education_surcharge', 1),
    ('地方附加应补退', 'local_education_surcharge', 1);
```

**数据量**：约 400 条记录，涵盖一般纳税人 41 字段 + 小规模 25 字段的栏次号、标准名称、常见口语简称。  
**作用**：NL2SQL 前置处理时，将用户问题中的短语替换为标准字段名，大幅提升模型准确率。



---

## 4.6 分类型视图（NL2SQL 入口）

> v1.2 说明：统一入口视图 **不再存在**；改为两个独立视图，分别覆盖对应纳税人类型全部 item 与维度列。

### 4.6.1 一般纳税人视图（`vw_vat_return_general`）


```sql
CREATE VIEW vw_vat_return_general AS
SELECT
    -- 维度
    g.taxpayer_id,
    t.taxpayer_name,
    g.period_year,
    g.period_month,
    g.item_type,
    g.time_range,
    t.taxpayer_type,

    -- 版本/追溯（v1.1新增字段）
    g.revision_no,
    g.submitted_at,
    g.etl_batch_id,
    g.source_doc_id,
    g.source_unit,
    g.etl_confidence,

    -- 指标（41个）
    g.sales_taxable_rate,
    g.sales_goods,
    g.sales_services,
    g.sales_adjustment_check,
    g.sales_simple_method,
    g.sales_simple_adjust_check,
    g.sales_export_credit_refund,
    g.sales_tax_free,
    g.sales_tax_free_goods,
    g.sales_tax_free_services,
    g.output_tax,
    g.input_tax,
    g.last_period_credit,
    g.transfer_out,
    g.export_refund,
    g.tax_check_supplement,
    g.deductible_total,
    g.actual_deduct,
    g.tax_payable,
    g.end_credit,
    g.simple_tax,
    g.simple_tax_check_supplement,
    g.tax_reduction,
    g.total_tax_payable,
    g.unpaid_begin,
    g.export_receipt_tax,
    g.paid_current,
    g.prepaid_installment,
    g.prepaid_export_receipt,
    g.paid_last_period,
    g.paid_arrears,
    g.unpaid_end,
    g.arrears,
    g.supplement_refund,
    g.immediate_refund,
    g.unpaid_check_begin,
    g.paid_check_current,
    g.unpaid_check_end,
    g.city_maintenance_tax,
    g.education_surcharge,
    g.local_education_surcharge
FROM vat_return_general g
JOIN taxpayer_info t ON g.taxpayer_id = t.taxpayer_id
WHERE t.taxpayer_type = '一般纳税人';
```

### 4.6.2 小规模纳税人视图（`vw_vat_return_small`）



```sql
CREATE VIEW vw_vat_return_small AS
SELECT
    -- 维度
    s.taxpayer_id,
    t.taxpayer_name,
    s.period_year,
    s.period_month,
    s.item_type,
    s.time_range,
    t.taxpayer_type,

    -- 版本/追溯（v1.1新增字段）
    s.revision_no,
    s.submitted_at,
    s.etl_batch_id,
    s.source_doc_id,
    s.source_unit,
    s.etl_confidence,

    -- 指标（25个）
    s.sales_3percent,
    s.sales_3percent_invoice_spec,
    s.sales_3percent_invoice_other,
    s.sales_5percent,
    s.sales_5percent_invoice_spec,
    s.sales_5percent_invoice_other,
    s.sales_used_assets,
    s.sales_used_assets_invoice_other,
    s.sales_tax_free,
    s.sales_tax_free_micro,
    s.sales_tax_free_threshold,
    s.sales_tax_free_other,
    s.sales_export_tax_free,
    s.sales_export_tax_free_invoice_other,
    s.tax_due_current,
    s.tax_due_reduction,
    s.tax_free_amount,
    s.tax_free_micro,
    s.tax_free_threshold,
    s.tax_due_total,
    s.tax_prepaid,
    s.tax_supplement_refund,
    s.city_maintenance_tax,
    s.education_surcharge,
    s.local_education_surcharge
FROM vat_return_small s
JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id
WHERE t.taxpayer_type = '小规模纳税人';
```

---

## 4.7 跨两类纳税人总体对比（允许 UNION）

> v1.2：不再提供公共指标视图 `vw_vat_common_indicators`。  
> 跨类型对比在查询侧通过 **UNION ALL**（推荐）或必要时 JOIN 编排完成。

### 4.7.1 推荐：总体对比用 UNION ALL（按类型对齐输出）

**例：对比 2025-12 两类纳税人“本期应纳税额”（口径分别取一般 `total_tax_payable`、小规模 `tax_due_total`）**

```sql
WITH g AS (
  SELECT
    taxpayer_id,
    period_year,
    period_month,
    '一般纳税人' AS taxpayer_type,
    SUM(COALESCE(total_tax_payable, 0)) AS tax_payable_amount
  FROM vw_vat_return_general
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year AND period_month = :month
    AND item_type = '一般项目' AND time_range = '本月'
  GROUP BY taxpayer_id, period_year, period_month
),
s AS (
  SELECT
    taxpayer_id,
    period_year,
    period_month,
    '小规模纳税人' AS taxpayer_type,
    SUM(COALESCE(tax_due_total, 0)) AS tax_payable_amount
  FROM vw_vat_return_small
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year AND period_month = :month
    AND item_type = '货物及劳务' AND time_range = '本期'
  GROUP BY taxpayer_id, period_year, period_month
)
SELECT * FROM g
UNION ALL
SELECT * FROM s
ORDER BY taxpayer_type;
```

> 说明：两类纳税人字段不一致，**UNION 对比**比 JOIN 更自然；对比指标需在业务侧定义“对齐口径”。

---

## 4.8 用户查询日志表（`user_query_log`）


记录每次 NL2SQL 请求的完整上下文，用于分析成功率、错误模式及未匹配短语。

```sql
CREATE TABLE user_query_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT,                          -- 会话标识（可选）
    user_query        TEXT NOT NULL,                 -- 用户原始自然语言查询
    normalized_query  TEXT,                          -- 同义词替换后的标准化查询
    taxpayer_id       TEXT,                          -- 解析出的纳税人识别号（若可提取）
    taxpayer_name     TEXT,                          -- 解析出的纳税人名称
    period_year       INTEGER,                       -- 解析出的年份
    period_month      INTEGER,                       -- 解析出的月份
    success           INTEGER DEFAULT 0,             -- 0=失败, 1=成功
    error_message     TEXT,                          -- 失败时的错误信息
    generated_sql     TEXT,                          -- 大模型生成的SQL（若成功）
    execution_time_ms INTEGER,                       -- 执行耗时
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_ip           TEXT,                          -- 客户端IP（可选）
    user_agent        TEXT                           -- 客户端标识（可选）
);

CREATE INDEX idx_query_log_created ON user_query_log (created_at);
CREATE INDEX idx_query_log_success ON user_query_log (success);
CREATE INDEX idx_query_log_taxpayer ON user_query_log (taxpayer_id);
```

**用途**：
- 查询成功率监控。
- 提取 `success=0` 的查询，分析是实体识别失败、同义词缺失还是其他原因。
- 为未匹配短语表提供原始文本来源。

---

### 4.9 未匹配短语表（`unmatched_phrases`）

> 原文保留（未改动）。

从用户查询中**自动或人工**识别出无法通过现有同义词映射匹配的短语，并跟踪处理状态。

```sql
CREATE TABLE unmatched_phrases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase          TEXT NOT NULL,                 -- 未匹配的短语（如“本期销项”）
    context_query   TEXT,                          -- 该短语出现的原始查询（示例）
    frequency       INTEGER DEFAULT 1,             -- 出现次数
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          TEXT DEFAULT 'pending',        -- pending, approved, rejected, ignored
    suggested_column TEXT,                        -- 人工建议的目标字段名（待确认）
    suggested_priority INTEGER DEFAULT 2,          -- 建议的同义词优先级
    remarks         TEXT,                         -- 备注
    processed_by    TEXT,                         -- 处理人
    processed_at    TIMESTAMP                     -- 处理时间
);

CREATE INDEX idx_unmatched_phrase ON unmatched_phrases (phrase);
CREATE INDEX idx_unmatched_status ON unmatched_phrases (status);
```

**自动提取机制**（Python伪代码）：
```python
def extract_unmatched_phrases(user_query, normalized_query):
    # 场景1：同义词替换时，某些词汇未被任何phrase命中
    # 简单方法：分词后检查是否被替换
    words = tokenize(user_query)  # 按空格、标点分词
    for word in words:
        if len(word) > 1 and not is_matched(word, normalized_query):
            upsert_unmatched(word, user_query)
```

**人工处理流程**：
1. 定期查询 `status='pending'` 并按 `frequency DESC` 排序。
2. 分析短语对应的业务含义，确定应映射到的标准字段名。
3. 更新 `suggested_column` 和 `status='approved'`。
4. 将 `approved` 的记录批量插入 `vat_synonyms` 表。
5. 标记 `status='processed'` 并记录处理人/时间。

---

### 4.10 自动化扩展工作流示意图

> 原文保留（未改动）。

```
用户自然语言查询
        ↓
同义词标准化（基于vat_synonyms）
        ↓
  是否有未替换词？ ──是──→ 记录到unmatched_phrases（自动去重、频次+1）
        ↓
  生成SQL & 执行
        ↓
记录user_query_log（含success状态）
        ↓
[每日/每周] 审核unmatched_phrases
        ↓
人工确认映射关系
        ↓
插入vat_synonyms + 更新unmatched_phrases状态
```

---

## 5. ETL 流程设计（PDF/Excel → 明细表）

### 5.1 输入解析
- 识别报表类型（一般/小规模）、纳税人识别号、所属期；
- 提取二维表格：行 = 栏次号，列 = 四个数据列（如“一般项目本月数”等）。

### 5.2 行列转换
```python
rows_dict = {}  # key = (纳税人, 所属期, 项目类型, 时间范围)
for 栏次号, 数值 in 行数据.items():
    field_name = mapping[栏次号]['column_name']   # 从映射表获取字段名
    for 列标题 in 列标题列表:
        item, time_range = parse_column_title(列标题)
        key = (taxpayer_id, period, item, time_range)
        rows_dict[key][field_name] = 数值
```

### 5.3 写入明细表
- 使用 `INSERT OR REPLACE` 按主键批量 upsert。
- 索引在导入前已建立，不影响性能。

> **v1.1补充：ETL 质量校验与错误日志（新增建议实现）**  
> 为提高 OCR/PDF 解析稳定性，建议增加校验与错误落库（不影响现有表结构）。

**建议新增 ETL 错误日志表：**
```sql
CREATE TABLE IF NOT EXISTS etl_error_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    etl_batch_id  TEXT,
    source_doc_id TEXT,
    taxpayer_id   TEXT,
    period_year   INTEGER,
    period_month  INTEGER,
    table_name    TEXT,          -- 'vat_return_general'/'vat_return_small'
    error_type    TEXT,          -- 'parse'/'validate'/'unit'/'constraint'...
    error_message TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_etl_error_batch ON etl_error_log(etl_batch_id);
```

**建议校验示例：**
- 小规模：检查 `tax_supplement_refund ≈ tax_due_total - tax_prepaid`（允许少量误差/空值）
- 单位：检测“万元”并统一换算为“元”，写入 `source_unit`

---

## 6. NL2SQL 应用流程（v1.2 最终落地版）

### 6.1 实体识别与同义词标准化

> **变更（v1.1）：按评审意见从“直接 replace 文本”升级为“最长匹配优先 + 不重叠替换 + 分视图启用同义词”。**  
> 目标：降低误替换与跨类型歧义，提高 SQL 生成准确率。

#### 6.1.1 标准化策略要点
1. 先做实体识别：纳税人（ID/名称）、期次、是否一般/小规模、时间范围（本月/累计/本期）等。  
2. 根据识别出的 `taxpayer_type`（或路由结果）选择 `scope_view`：  
   - 一般纳税人：`vw_vat_return_general`  
   - 小规模纳税人：`vw_vat_return_small`  
3. 同义词替换采用“最长匹配优先 + 不重叠替换”，并且仅启用符合 `taxpayer_type/scope_view` 的同义词。

#### 6.1.2 伪代码

```python
def detect_scope(user_query, taxpayer_id=None, taxpayer_name=None):
    """
    输出：scope_view, taxpayer_type(可能为空), period_year, period_month, etc.
    - 若能从taxpayer_info确定纳税人类型，则直接路由到对应视图
    - 否则先根据关键词（一般/小规模/征收率3%/5%/专票等）进行初步路由
    """
    # 1) 如果有taxpayer_id，查taxpayer_info得到taxpayer_type
    # 2) 解析期次（2025年12月/2025-12/本月/上月）
    # 3) 若未识别类型，返回 None 并进入 6.2 方案A 的第一阶段让LLM判断
    return scope_view, taxpayer_type, period_year, period_month


def normalize_query(user_query, scope_view=None, taxpayer_type=None):
    """
    同义词替换：最长匹配优先 + 不重叠替换
    输出 normalized_query 与命中列表 hits
    """
    # 取可用同义词（按优先级降序，再按phrase长度降序）
    sql = """
    SELECT phrase, column_name, priority
    FROM vat_synonyms
    WHERE (scope_view IS NULL OR scope_view = ?)
      AND (taxpayer_type IS NULL OR taxpayer_type = ?)
    ORDER BY priority DESC, LENGTH(phrase) DESC
    """
    rows = cur.execute(sql, (scope_view, taxpayer_type)).fetchall()

    hits = []
    occupied = [False] * len(user_query)  # 简化：标记已替换区间

    for phrase, col, pr in rows:
        # 查找所有出现位置（可用更高效的Aho-Corasick）
        for start in find_all(user_query, phrase):
            end = start + len(phrase)
            if any(occupied[start:end]):
                continue
            # 记录替换，但不直接就地replace避免偏移；可构造token/片段列表
            hits.append((start, end, phrase, col, pr))
            for i in range(start, end):
                occupied[i] = True

    normalized_query = apply_replacements(user_query, hits)  # 按start倒序替换
    return normalized_query, hits
```

---

## 6.2 大模型 Prompt 设计（方案A：两阶段“受控生成”+ 动态 Schema 注入）——细化终版

> 你给的“6 套分域 System Prompt（终版）”是**单阶段直接出 SQL**的“次优方案”。  
> v1.2 在保留你提供的“6 套分域 System Prompt（终版）”（用于单阶段直出 SQL 的次优落地）同时，给出 **方案A（最优）** 的完整可落地链路：  
> - **阶段1：意图解析（LLM 输出严格 JSON，包含 domain/views/字段/过滤/追问）**  
> - **约束注入器（程序）：根据阶段1 JSON 动态注入最小 schema 白名单**（allowed_views/allowed_columns/max_rows 等）  
> - **阶段2：SQL 生成（LLM 在白名单内生成 SQLite SQL）**  
> - **SQL 审核器（程序硬拦截）**  
> - **执行反馈回路**（错误回传→重试/澄清）

> 说明：方案A中**不再设置“阶段0 程序路由”来替代 LLM 路由**；系统侧可做实体预处理（税号/期次候选提取）帮助阶段1，但最终 domain/views 以阶段1 JSON 为准。

---

#### 6.2.0 角色与链路分工（强制）

- **实体预处理（程序，可选）**  
  - 输入：用户问题、会话上下文  
  - 输出（候选信息）：`taxpayer_id/taxpayer_name`、`period_year/period_month`、时间范围词（本月/累计/本期）、VAT 关键词命中等  
  - 说明：该步骤只提供“候选实体/提示”，**不做最终 domain/views 决策**。

- **阶段1 Intent Parser（LLM）**：**只产 JSON，不写 SQL**  
  - 输入：用户问题 + 上下文 +（可选）实体预处理候选 +（可选）同义词命中信息  
  - 输出：严格 JSON，必须包含 `domain` 与 `views`（以及字段、过滤、聚合、是否需要澄清）

- **约束注入器（程序，必须）**  
  - 输入：阶段1 JSON  
  - 输出：`guardrails.allowed_views`、`allowed_columns_by_view`、`max_rows/max_period_months` 等  
  - 逻辑：从 `schema_catalog`（或静态白名单）抽取“最小必要字段集合”，注入阶段2 prompt

- **阶段2 SQL Writer（LLM）**  
  - 输入：阶段1 JSON + 动态 schema 白名单（allowed views/columns）  
  - 输出：只读 SQLite SQL（SELECT 或 WITH…SELECT）

- **SQL 审核器（程序，必须）**：按规则清单硬拦截（只读、单语句、白名单、必备过滤、LIMIT 等）  
- **执行器（程序）**：绑定参数执行，记录日志与结果形态

> 注释建议：你提供的 system prompt 中“必须包含 taxpayer_id = :taxpayer_id”是很强的合规约束；若业务永远是单企业私域数据可保留；若需要集团/行业 TopN 等场景，应在上层显式开一个“允许全局统计”的受控开关，并同步更新审核器必备过滤规则。

---

### 6.2.1 域（Domain）定义：6 套单域 + 1 套跨域（新增）

- 单域（你给的 6 套）  
  1) VAT 申报域  
  2) 企业所得税申报域  
  3) 财务报表域  
  4) 科目余额域  
  5) 发票域  
  6) 企业画像域  
- ** 7) 跨域（新增）**：当用户问题明确要求“对账/差异/追溯来源/申报 vs 发票/财务 vs 发票”等，若用户问题明确要求“对账/差异/追溯来源/申报 vs 发票/财务 vs 发票”等跨域分析：  
> - 阶段1 JSON 的 `domain` 应输出为 `cross_domain`（或输出多域 views）；  
> - 系统侧据此启用跨域编排（多视图白名单 + 更严格审核），不应强行套用单域 system prompt 直接回答。

---

### 6.2.2 VAT 申报域的适配（重要更新）

你提供的 VAT 域 system prompt 仍引用 `vw_vat_return_full`，而 v1.2 的数据模型只有：  
- `vw_vat_return_general`（一般纳税人）  
- `vw_vat_return_small`（小规模纳税人）

因此 VAT 域应拆成两套单域 system prompt（或保留一套但允许访问两个视图）。

**建议做法**：VAT 域允许访问两个视图，但仍是“VAT 单域”。  
- 好处：用户不需要显式知道类型；SQL Writer 在 JSON 指示下选择 1 个或 UNION 两个。

> 注释建议：如果你坚持“单域只能访问一个视图”，那 VAT 域必须拆成 `VAT_GENERAL` 与 `VAT_SMALL` 两个域，会让 Router 更复杂。

---

### 6.2.3 方案A：阶段1（Intent → JSON）最细颗粒度设计

#### (1) 阶段1 输入（prompt 注入字段）

- 用户原问题 `user_query`
- 会话上下文 `conversation_context`（可选）
- Router 输出：`domain_candidates`、`allowed_views`（若已确定）、`taxpayer_id`（若已识别）
- 同义词命中列表（可选）：`synonym_hits=[{phrase,column_name,scope_view}]`

#### (2) 阶段1 输出（严格 JSON Schema）

```json
{
  "domain": "vat|eit|fs|account_balance|invoice|profile|cross_domain",
  "vat_scope": {
    "taxpayer_type_hint": "一般纳税人|小规模纳税人|unknown",
    "views": ["vw_vat_return_general"],
    "cross_type_union": false
  },
  "select": {
    "metrics": ["output_tax"],
    "dimensions": ["period_year", "period_month"]
  },
  "filters": {
    "taxpayer_id": ":taxpayer_id",
    "period_mode": "month|quarter|year|range_month|date_range",
    "period": {
      "year": ":year",
      "month": ":month",
      "quarter": ":quarter",
      "start_yyyymm": ":start_yyyymm",
      "end_yyyymm": ":end_yyyymm",
      "start_date": ":start_date",
      "end_date": ":end_date"
    },
    "vat_dims": {
      "item_type": "一般项目|即征即退项目|货物及劳务|服务不动产无形资产|null",
      "time_range": "本月|累计|本期|null"
    },
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

#### (3) 阶段1 判定规则（最细）

- **缺 taxpayer**：若 system 强约束“必须 taxpayer_id”，则 `need_clarification=true`，问题如“请提供 taxpayer_id”。  
- **缺期间**：必须澄清；除非上下文已提供默认期间。  
- **VAT 指标字段选择**：  
  - 若用户提“销项税额/进项税额/应纳税额/留抵”等，优先映射到一般 `output_tax/input_tax/total_tax_payable/end_credit`；  
  - 若 Router 判定小规模（或命中 3%/5%/征收率/小微免税等词），则映射到小规模字段；  
  - 若无法确定类型但用户要“总体对比/看看两类”，则 `cross_type_union=true`，views 两个都带上，并在阶段2做 UNION 对齐。  
- **VAT 维度 item_type/time_range 默认值**：  
  - 一般纳税人：用户未说明，默认 `item_type='一般项目'`；time_range 由“本月/累计/当月/本期”推断，否则澄清。  
  - 小规模：用户未说明，默认 `item_type='货物及劳务'`；time_range 默认 `本期`。  
- **revision 策略**：默认 `latest`（每个维度组合取最大 `revision_no`）。用户明确“更正前/第1次更正”才用 specific。

---

### 6.2.4 方案A：阶段2（JSON + 最小 Schema → SQL）最细颗粒度设计

#### (1) 阶段2 输入（动态 Schema 注入）

系统从 `schema_catalog`（或代码内字段白名单）注入：

- `allowed_views`（单域必须 1 组；VAT 可能是 2 个视图集合）
- 每个 view 的允许列清单：
  - 维度：`taxpayer_id, period_year, period_month, item_type, time_range, revision_no`
  - 以及 JSON 里 `metrics/dimensions` 需要的列
- 审核器限制参数（max_rows、是否强制 limit、最大期间跨度）

#### (2) 阶段2 SQL 生成规则（硬规则）

- 只生成 `SELECT` 或 `WITH ... SELECT`
- 禁止 `SELECT *`
- 必须带 `WHERE taxpayer_id = :taxpayer_id`
- 必须带期间过滤（按 period_mode）
- 若 `revision_strategy=latest`：必须在 SQL 中实现 “latest revision” 过滤（示例见下）
- 明细/列表必须 `LIMIT <= :max_rows`

#### (3) latest revision 的标准写法（SQLite 推荐）

**写法A（窗口函数）**：

```sql
WITH x AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY taxpayer_id, period_year, period_month, item_type, time_range
      ORDER BY revision_no DESC
    ) AS rn
  FROM vw_vat_return_general
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year AND period_month = :month
)
SELECT
  period_year, period_month, item_type, time_range, output_tax
FROM x
WHERE rn = 1
LIMIT 1000;
```

**写法B（相关子查询）**（更通用但可能慢）：

```sql
SELECT
  g.period_year, g.period_month, g.item_type, g.time_range, g.output_tax
FROM vw_vat_return_general g
WHERE g.taxpayer_id = :taxpayer_id
  AND g.period_year = :year AND g.period_month = :month
  AND g.revision_no = (
    SELECT MAX(revision_no)
    FROM vw_vat_return_general
    WHERE taxpayer_id = g.taxpayer_id
      AND period_year = g.period_year
      AND period_month = g.period_month
      AND item_type = g.item_type
      AND time_range = g.time_range
  )
LIMIT 1000;
```

#### (4) VAT 跨两类总体对比（UNION）标准模板（阶段2必须会）

当 `cross_type_union=true`：

- 先各自聚合到同一输出 schema（统一列名），再 `UNION ALL`
- 列名对齐：`taxpayer_type, metric_name, metric_value, period_year, period_month`

示例（对比本期应纳税额）：

```sql
WITH g AS (
  SELECT
    '一般纳税人' AS taxpayer_type,
    '应纳税额(对齐口径)' AS metric_name,
    SUM(COALESCE(total_tax_payable, 0)) AS metric_value,
    period_year,
    period_month
  FROM vw_vat_return_general
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year AND period_month = :month
    AND item_type = '一般项目' AND time_range = '本月'
  GROUP BY period_year, period_month
),
s AS (
  SELECT
    '小规模纳税人' AS taxpayer_type,
    '应纳税额(对齐口径)' AS metric_name,
    SUM(COALESCE(tax_due_total, 0)) AS metric_value,
    period_year,
    period_month
  FROM vw_vat_return_small
  WHERE taxpayer_id = :taxpayer_id
    AND period_year = :year AND period_month = :month
    AND item_type = '货物及劳务' AND time_range = '本期'
  GROUP BY period_year, period_month
)
SELECT * FROM g
UNION ALL
SELECT * FROM s
ORDER BY taxpayer_type
LIMIT 1000;
```

> 注释建议：跨类型“对齐口径”必须在产品侧沉淀字典（比如把一般的 `output_tax` 与小规模的“税额类字段”对齐时要谨慎），否则 LLM 容易做出不合理对齐。

---

### 6.2.5 你提供的「6 套分域 System Prompt（终版）」——v1.2 适配版（可直接粘贴）

> 说明：你给的文本要求“缺关键条件就停止生成 SQL，输出澄清问题”。  
> 在最优的方案A里，我们建议：  
> - system 仍可要求“缺条件则澄清”  
> - 但输出最好是结构化（如 JSON 的 `need_clarification=true`），由应用层渲染为中文追问。  
> 下面按你的“文本澄清也可”的要求，给出可直接粘贴版本；其中 VAT 域按 v1.2 改为两个视图。

#### 6.2.5.1 增值税申报域（`vw_vat_return_general` + `vw_vat_return_small`）

```text
你是企业数据查询助手。只生成可执行的只读 SQL（SELECT 或 WITH ... SELECT）。
【允许访问的视图】仅：
- vw_vat_return_general（一般纳税人）
- vw_vat_return_small（小规模纳税人）

【必备过滤】SQL 必须包含 taxpayer_id = :taxpayer_id
并且必须包含期间过滤，按用户问题选择：
- 月：period_year = :year AND period_month = :month
- 年：period_year = :year
- 范围（月）：(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm
（注：这两个视图不包含 quarter 字段；若用户问季度，必须先澄清为季度对应的起止月份，或由上层把 quarter 转换成 month 范围后再让你生成SQL。）

【口径提示】这是“增值税申报口径”，不同于发票明细口径。用户若问“开票/认证/红冲/发票明细”，应改走发票域(vw_invoice)。

【输出要求】
- 只输出 SQL，不要解释
- 禁止 SELECT *
- 汇总类问题优先 GROUP BY period_year, period_month
- 明细/列表默认 LIMIT 1000

【澄清规则】
- 若用户问的是“发票口径的销项/进项”，请询问：要申报口径(vw_vat_return_general/vw_vat_return_small)还是发票口径(vw_invoice)？
- 若缺少期间（例如只说“最近”），必须先问清 year/month 或范围后再生成 SQL。
- 若无法判断应使用一般还是小规模视图，且用户未要求对比两类，则必须澄清纳税人类型；若用户要求总体对比，则允许对两个视图分别汇总后 UNION ALL。
```

#### 6.2.5.2 企业所得税申报域（`vw_EIT_return`）

（按你原文保留，仅加注释建议：若视图字段不含 quarter，则同样需要澄清或上层映射）

```text
你是企业数据查询助手。只生成可执行的只读 SQL（SELECT 或 WITH ... SELECT）。
【允许访问的视图】仅：vw_EIT_return

【必备过滤】必须包含 taxpayer_id = :taxpayer_id
并且必须包含期间过滤（一般按年/季，若视图是月度也同样适用）：
- 年：period_year = :year
- 季：period_year = :year AND period_quarter = :quarter（若无 quarter 字段则必须澄清为季度对应月份范围）
- 范围：按 (period_year*100+period_month) 或 period_year BETWEEN ...（取决于视图字段）

【口径提示】这是“企业所得税申报口径”，不同于财务利润表的“所得税费用”。

【输出要求】
- 只输出 SQL，不要解释
- 默认 LIMIT 1000（纯聚合单行可不加 LIMIT）

【澄清规则】
- 若用户问“所得税费用”，必须问清：财务报表口径(vw_financial_statement)还是所得税申报口径(vw_EIT_return)？
- 若缺少期间必须澄清后再生成 SQL。
```

#### 6.2.5.3 财务报表域（`vw_financial_statement`）

（按你原文保留）

```text
你是企业数据查询助手。只生成可执行的只读 SQL（SELECT 或 WITH ... SELECT）。
【允许访问的视图】仅：vw_financial_statement

【必备过滤】必须包含 taxpayer_id = :taxpayer_id
并且必须包含期间过滤：
- 月：period_year = :year AND period_month = :month
- 季：period_year = :year AND period_quarter = :quarter（若无 quarter 字段则用 month 映射）
- 年：period_year = :year
- 范围（月）：(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm

【口径提示】财务三表口径，与申报口径不一定一致。用户问“申报表栏次/应纳税额/留抵”等应走税务申报域。

【输出要求】
- 只输出 SQL
- 若用户问“某指标趋势”，按 period_year, period_month 排序输出
- 默认 LIMIT 1000（纯聚合单行可不加 LIMIT）

【澄清规则】
- 若用户问“税负率/毛利率/ROE”等画像指标，应路由到 vw_enterprise_profile（或在本域计算需谨慎，默认走画像域）。
- 缺期间则先澄清。
```

#### 6.2.5.4 科目余额域（`vw_account_balance`）

（按你原文保留）

```text
你是企业数据查询助手。只生成可执行的只读 SQL（SELECT 或 WITH ... SELECT）。
【允许访问的视图】仅：vw_account_balance

【必备过滤】必须包含 taxpayer_id = :taxpayer_id
并且必须包含期间过滤：
- 月：period_year = :year AND period_month = :month
- 范围（月）：(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm

【输出要求】
- 只输出 SQL
- 若用户问某科目余额，优先按 account_code 精确匹配；否则按 account_name 模糊匹配（LIKE）
- 明细列表默认 ORDER BY account_code, LIMIT 1000

【澄清规则】
- 若用户未提供科目（代码/名称）且请求“列出异常科目”等，需澄清“异常定义/阈值”或改为给出可执行的 TopN 列表（例如发生额最大的前 N 个）但仍必须有期间。
```

#### 6.2.5.5 发票域（`vw_invoice`）

（按你原文保留）

```text
你是企业数据查询助手，只生成可执行的只读 SQL（SELECT）。
【允许访问的视图】仅：vw_invoice

【必备过滤】
1) SQL 必须包含 taxpayer_id = :taxpayer_id
2) SQL 必须包含期间过滤（两种方式二选一，按用户问题选择最合适）：
A) 明细/按天/逐张：使用 invoice_date 过滤
   invoice_date BETWEEN :start_date AND :end_date
B) 汇总（按月/季/年）：使用 period_year/period_month/period_quarter 过滤
   - 月：period_year = :year AND period_month = :month
   - 季：period_year = :year AND period_quarter = :quarter
   - 月范围：(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm
   - 年：period_year = :year

【默认口径】发票为“开票/认证明细口径”，与申报口径可能不一致。

【澄清规则（必须遵守）】
- 若用户问“应纳税额/留抵/申报表栏次/销项税额(申报)/进项税额(申报)”，停止生成SQL，改为提问：
  需要申报口径(vw_vat_return_general/vw_vat_return_small)还是发票口径(vw_invoice)？
- 若用户问“对账/差异（申报 vs 发票、收入 vs 发票）”，不要单域硬答，应要求走 cross-domain（由router选择多视图）。

【输出要求】
- 只输出SQL，不要解释
- 明细默认 ORDER BY invoice_date DESC
- 明细默认 LIMIT 1000；汇总类可 LIMIT 1000 或不加（建议加以稳妥）
【禁止】
- 禁止 INSERT/UPDATE/DELETE/DDL
- 禁止访问未授权视图/表
```

#### 6.2.5.6 企业画像域（`vw_enterprise_profile`）

（按你原文保留）

```text
你是企业数据查询助手。只生成可执行的只读 SQL（SELECT 或 WITH ... SELECT）。
【允许访问的视图】仅：vw_enterprise_profile

【必备过滤】必须包含 taxpayer_id = :taxpayer_id
并且必须包含期间过滤（画像通常为月/季/年）：
- 月：period_year = :year AND period_month = :month
- 季：period_year = :year AND period_quarter = :quarter（若无则用 month 映射）
- 年：period_year = :year
- 范围（月）：(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm

【口径提示】画像指标为衍生口径，可能来自财务/申报/发票的加工结果。若用户要求“追溯明细来源”，应提示需要 cross-domain 或明细域查询。

【输出要求】
- 只输出 SQL
- 趋势类按 period_year, period_month 排序
- 默认 LIMIT 1000（纯聚合单行可不加 LIMIT）

【澄清规则】
- 若用户只问“最近/今年表现如何”缺乏期间边界，必须澄清时间范围后再生成 SQL。
```

#### [缺新增的跨域部分]
---

### 6.2.6 SQL 审核器规则清单（终版，SQLite MVP 友好）

> 你提供的规则清单在 v1.2 **原样纳入**，并做 1 处同步修订：  
> - VAT 域的“视图白名单”要能包含 `vw_vat_return_general` / `vw_vat_return_small`（而非 `vw_vat_return_full`）。  

（以下为你原文规则清单，除必要视图名同步外，保持一致；交付时请以你提供原文为准逐字保留。）

> 审核器目标：对 LLM 生成 SQL 做“硬拦截”。  
> 本清单是**规则**；实现可先正则/轻解析，后续再换 AST（如 sqlglot）。

### 3.1 基础安全规则（所有域通用）

1. **只允许单语句**
   - 禁止出现多条语句（除末尾一个分号外，不允许中间再有 `;`）。

2. **只允许只读**
   - SQL 必须以 `SELECT` 或 `WITH` 开头（CTE 最终也必须 SELECT）。

3. **禁用危险关键字/语句（大小写不敏感）**
   - DML/DDL：`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `REPLACE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`
   - 权限/外部：`GRANT`, `REVOKE`
   - SQLite 特别禁用：`PRAGMA`, `ATTACH`, `DETACH`
   - 其它你认为敏感的：如 `VACUUM`、`LOAD_EXTENSION`（如启用扩展）

4. **视图白名单**
   - `FROM` / `JOIN` 的对象只能在 Router 给定的 `guardrails.allowed_views` 集合内。
   - 禁止访问 `sqlite_master` 等系统表。

5. **行数控制**
   - 对“明细型/列表型”要求必须 `LIMIT <= guardrails.max_rows`。
   - 对纯聚合（无明细列、无 group by 或 group by 期别）可放宽，但仍建议限制返回行数。

6. **禁止 `SELECT *`（建议强制）**
   - 防止敏感字段意外泄露与宽表扫出。
   - 若确需调试，走内部运维通道，不走对外。

7. **函数/表达式 denylist（可选）**
   - `randomblob`, `load_extension` 等 SQLite 特殊函数可禁用。
   - 过重/不确定函数可加入 denylist。

8. **列级 denylist（可选，按合规）**
   - 如地址电话、银行账号、校验码等：`buyer_bank_account`、`seller_bank_account`、`*_address_phone`、`verification_code` 等（以你真实字段为准）。
   - 审核器检查 SELECT 列与 WHERE/ORDER BY/GROUP BY 里是否引用 denylist 列（策略由你定：完全禁止或需授权）。

---

### 3.2 必备过滤规则（按域）

> 核心：必须在 WHERE（或等价约束）中**同时**锁定纳税人 + 期间边界。

#### 3.2.1 通用：必须包含 `taxpayer_id` 过滤
- 必须出现等值过滤：`taxpayer_id = :taxpayer_id`（或 `?` 占位等价形式）。
- 不接受仅用 `IN (subquery without taxpayer filter)` 的间接过滤（MVP 可先不做深度推理，但建议逐步强化）。

#### 3.2.2 申报/报表/科目/画像（非发票域）必须包含 period 过滤之一
- 月：`period_year = :year AND period_month = :month`
- 季：`period_year = :year AND period_quarter = :quarter`（若有该字段）
- 年：`period_year = :year`
- 跨月范围：`(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm`

并受 `max_period_months` 约束（审核器可计算跨度；MVP 可先做“存在性校验”，后续增强）。

#### 3.2.3 发票域（`vw_invoice`）必须包含期间过滤（二选一）——重点更新
必须满足：

- **固定必须**：`taxpayer_id = :taxpayer_id`
- **并且必须出现以下之一：**

A) `invoice_date` 过滤（明细/逐张/按天）
- 允许形式：
  - `invoice_date BETWEEN :start_date AND :end_date`
  - 或 `invoice_date >= :start_date AND invoice_date <= :end_date`
- 同时受 `max_day_span` 约束（例如 1100 天；可配置）

B) `period_*` 过滤（汇总/月季年）
- 月：`period_year` 与 `period_month` 同时出现
- 季：`period_year` 与 `period_quarter` 同时出现
- 或跨月范围：`(period_year*100+period_month) BETWEEN :start_yyyymm AND :end_yyyymm`
- 受 `max_period_months` 约束

---

### 3.3 结果形态规则（建议）

1. **明细默认排序**
   - 发票明细：`ORDER BY invoice_date DESC`
   - 期别趋势：`ORDER BY period_year, period_month`

2. **聚合规则**
   - 若 SELECT 中出现非聚合列，则必须在 `GROUP BY` 中出现（标准 SQL 规则；SQLite 宽松但你应强制，避免错误口径）。

3. **禁止笛卡尔积**
   - 多表 JOIN 必须带 ON 条件（即便当前单域通常不会 join；跨域时更重要）。


---

## 6.3 SQL 生成与执行（v1.2 同步修订）

v1.2 执行链路统一如下：

1.**实体预处理（可选）**：抽取纳税人/期次等候选信息；做同义词标准化（按 scope_view/taxpayer_type 条件启用）。  
2. **意图解析（阶段1，LLM）**：输出严格 JSON（包含 `domain`、`views`、字段、过滤、聚合、是否需要澄清）。  
3. **若需澄清**：直接返回澄清问题（不生成 SQL）。  
4. **约束注入器（程序）**：根据阶段1 JSON，从 `schema_catalog` 生成本次 `allowed_views/allowed_columns` 与执行约束（max_rows、max_period_months 等），注入阶段2。  
5. **SQL 生成（阶段2，LLM）**：在“动态 schema 白名单”约束下生成 SQL。  
6. **SQL 审核器（程序）**：硬拦截危险/越权/缺过滤/无 LIMIT 等问题；失败则返回结构化原因触发一次重试。  
7. **执行与返回**：绑定参数执行并返回结果；写入 `user_query_log`，未命中短语写入 `unmatched_phrases`。

> v1.2 明确：增值税申报查询不再从 `vw_vat_return_full` 获取，而是从：  
> - 一般：`vw_vat_return_general`  
> - 小规模：`vw_vat_return_small`  
> 跨两类总体对比：默认 `UNION ALL` 编排；仅在用户明确要求“并列列展示”时才使用 `JOIN`。

---

## 7. 方案对比分析（v1.2 同步修订，消除旧矛盾）

| 对比维度 | **本方案（分类型视图 + 明细表 + 受控两阶段）** | **超级宽表（164/100列）** | **全纵表（一行一指标）** | **传统表路由（两表独立 + 无 guardrails）** |
|----------|-----------------------------------------------|---------------------------|--------------------------|---------------------------------------------|
| **NL2SQL 表选择复杂度** | ⭐⭐⭐⭐（阶段1 JSON 决定 views；系统据此注入白名单；VAT 可能 1 或 2 视图并用 UNION ALL 对齐输出） | ⭐⭐（无路由但字段噪声大） | ⭐⭐（需复杂聚合/透视） | ⭐（模型需自行判断易错） |
| **字段语义明确性** | ⭐⭐⭐⭐⭐（视图降噪 + 白名单字段注入） | ⭐⭐（字段过多易选错） | ⭐⭐（语义分散在维度/字典） | ⭐⭐⭐⭐⭐ |
| **存储效率** | ⭐⭐⭐⭐⭐（4行/期） | ⭐（空值爆炸） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **ETL 维护成本** | ⭐⭐⭐⭐（行列转换清晰可控） | ⭐⭐⭐（直接映射） | ⭐⭐⭐（需 UNPIVOT） | ⭐⭐⭐⭐ |
| **跨类型比较** | ⭐⭐⭐⭐（推荐 UNION ALL 对齐口径） | ❌ 难以统一语义 | ⭐⭐ | ⭐⭐（应用层/手写 SQL） |
| **安全与合规可控** | ⭐⭐⭐⭐⭐（审核器 + 白名单 + 只读约束） | ⭐⭐ | ⭐⭐ | ⭐（风险最高） |
| **大模型准确率** | **≥95%（目标）**：字段注入+两阶段+硬校验 | 70~80% | ≤60% | 80~90%（取决于路由与约束） |

### 为什么本方案最优（v1.2 版本的解释）

1. **降噪而不是“强行统一视图”**：VAT 拆为两视图，字段集合更小，模型选错列的概率显著降低。  
2. **两阶段受控生成**：先定意图/字段/过滤，再生成 SQL；配合审核器，线上稳定性更高。  
3. **跨类型对比用 UNION**：避免 JOIN 的语义陷阱（两类字段不对称），对齐口径可运营沉淀。  
4. **可审计可运营**：日志 + 未匹配短语闭环，持续提升覆盖率与准确率。

---

## 8. 总结与扩展建议（v1.2 同步修订）

本方案（v1.2）提供：**一般纳税人 + 小规模纳税人** 的完整数据模型与 NL2SQL 受控生成链路，包含：

- ✅ 2 张明细表 DDL  
- ✅ 1 张纳税人信息表  
- ✅ 2 张 ETL 栏次映射表及数据  
- ✅ 1 张 NL2SQL 同义词表（支持分视图/分类型 scope）  
- ✅ **2 张 VAT 查询视图**：`vw_vat_return_general`、`vw_vat_return_small`  
- ✅ **方案A**：两阶段受控生成 + 动态 schema 注入 + SQL 审核器规则  
- ✅ 跨两类总体对比：**允许 UNION ALL** 编排（不依赖公共指标视图）

**下一步扩展建议**：

1. **附列资料（一）～（四）**：复用同样模式——明细表按栏次字段化，建立映射表，提供分域视图入口。  
2. **企业维度表增强**：增加行业、税务机关、纳税信用等级等属性，支持更丰富的分析。  
3. **对齐口径字典**：把“跨域/跨类型对比”的指标映射显式化（metric registry），减少 LLM 自行猜测。  
4. **从正则审核升级到 AST**：MVP 用规则清单，成熟后用 `sqlglot` 等做更强的结构校验与重写。  

---

## 附录：
