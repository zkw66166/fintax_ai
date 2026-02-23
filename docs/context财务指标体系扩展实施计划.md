# 财务指标体系扩展实施计划

## Context

当前 `financial_metrics` 表数据为空，且缺少 `financial_metrics_item`、`financial_metrics_item_dict` 等结构化表。需根据 v4 文档扩展为完整的财务指标体系。财务指标域之前未完成设计，无需考虑向后兼容，`vw_financial_metrics` 视图将完全重建。

## 关键设计决策

### 1. period_type 维度

新建 `financial_metrics_item` 表，PK 中加入 `period_type`（monthly/quarterly/annual）。`vw_financial_metrics` 视图完全重建，包含 `period_type` 列。

### 2. 旧表处理

保留旧 `financial_metrics` 表不删除（DDL 保留），视图切换到新表 `financial_metrics_item`。

### 3. 指标总数：25个

v4 文档 24 个（去掉"净利润"直接取值指标）+ 现有 `现金债务保障比率` = 25 个指标，10 个类别。

### 4. 发票开具异常率定义

"顶额开具"采用发票限额档位判定法：金额落在 [档位×90%, 档位) 区间视为顶额。档位：1万、10万、100万、1000万。查询 `inv_spec_sales` 表，按 `invoice_pk` 聚合后判定。

---

## 实施步骤

### Phase 1: DDL — 修改 `database/init_db.py`

**1a. 新增 `financial_metrics_item_dict` 表**（在现有 financial_metrics_synonyms DDL 之后，约 line 1090）

```sql
CREATE TABLE IF NOT EXISTS financial_metrics_item_dict (
    metric_code     TEXT PRIMARY KEY,
    metric_name     TEXT NOT NULL,
    metric_category TEXT NOT NULL,
    metric_unit     TEXT DEFAULT '',
    formula_desc    TEXT,
    source_domains  TEXT,           -- 逗号分隔: 'profit,balance_sheet'
    period_types    TEXT NOT NULL,  -- 逗号分隔: 'monthly,quarterly,annual'
    eval_rules      TEXT,           -- JSON: [[30,"优"],[15,"良"],[5,"中"],[null,"差"]]
    eval_ascending  INTEGER DEFAULT 0,
    display_order   INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1
);
```

**1b. 新增 `financial_metrics_item` 表**

```sql
CREATE TABLE IF NOT EXISTS financial_metrics_item (
    taxpayer_id      TEXT NOT NULL,
    period_year      INTEGER NOT NULL,
    period_month     INTEGER NOT NULL,  -- 季度用末月(3,6,9,12)，年度用12
    period_type      TEXT NOT NULL,     -- 'monthly'/'quarterly'/'annual'
    metric_code      TEXT NOT NULL,
    metric_name      TEXT NOT NULL,
    metric_category  TEXT NOT NULL,
    metric_value     NUMERIC,
    metric_unit      TEXT,
    evaluation_level TEXT,
    calculated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (taxpayer_id, period_year, period_month, period_type, metric_code),
    FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id),
    FOREIGN KEY (metric_code) REFERENCES financial_metrics_item_dict(metric_code)
);
-- 索引: idx_fmi_taxpayer, idx_fmi_period, idx_fmi_taxpayer_period, idx_fmi_category, idx_fmi_code, idx_fmi_period_type
```

**1c. 重建 `vw_financial_metrics` 视图**（修改 `_get_financial_metrics_view_ddl()`）

```sql
DROP VIEW IF EXISTS vw_financial_metrics;
CREATE VIEW IF NOT EXISTS vw_financial_metrics AS
SELECT
    fm.taxpayer_id, t.taxpayer_name, t.taxpayer_type, t.accounting_standard,
    fm.period_year, fm.period_month, fm.period_type,
    fm.metric_category, fm.metric_code, fm.metric_name,
    fm.metric_value, fm.metric_unit, fm.evaluation_level, fm.calculated_at
FROM financial_metrics_item fm
JOIN taxpayer_info t ON fm.taxpayer_id = t.taxpayer_id;
```

### Phase 2: 种子数据 — 修改 `database/seed_data.py`

**2a. 新增 `_seed_financial_metrics_item_dict(cur)` 函数**

插入 25 条指标定义（已去掉"净利润"直接取值指标），完整映射如下：

| # | metric_code | metric_name | category | unit | period_types | eval_rules |
|---|-------------|-------------|----------|------|-------------|------------|
| 1 | gross_margin | 毛利率 | 盈利能力 | % | monthly,quarterly,annual | [[30,"优"],[15,"良"],[5,"中"],[null,"差"]] |
| 2 | net_margin | 净利率 | 盈利能力 | % | monthly,quarterly,annual | [[15,"优"],[8,"良"],[3,"中"],[null,"差"]] |
| 3 | roe | 净资产收益率(ROE) | 盈利能力 | % | monthly,quarterly,annual | [[15,"优"],[8,"良"],[3,"中"],[null,"差"]] |
| 4 | net_profit_growth | 净利润增长率 | 盈利能力 | % | monthly,quarterly,annual | [[20,"优"],[10,"良"],[0,"中"],[null,"差"]] |
| 5 | admin_expense_ratio | 管理费用率 | 费用控制 | % | monthly,quarterly,annual | [[5,"优"],[10,"良"],[15,"中"],[null,"差"]] (ascending) |
| 6 | sales_expense_ratio | 销售费用率 | 费用控制 | % | monthly,quarterly,annual | [[8,"优"],[15,"良"],[20,"中"],[null,"差"]] (ascending) |
| 7 | debt_ratio | 资产负债率 | 偿债能力 | % | monthly,quarterly,annual | [[40,"优"],[60,"良"],[70,"中"],[null,"差"]] (ascending) |
| 8 | current_ratio | 流动比率 | 偿债能力 | | monthly,quarterly,annual | [[2.0,"优"],[1.5,"良"],[1.0,"中"],[null,"差"]] |
| 9 | quick_ratio | 速动比率 | 偿债能力 | | monthly,quarterly,annual | [[1.5,"优"],[1.0,"良"],[0.5,"中"],[null,"差"]] |
| 10 | cash_debt_coverage | 现金债务保障比率 | 偿债能力 | % | monthly,quarterly,annual | None |
| 11 | ar_turnover | 应收账款周转率 | 营运能力 | 次 | monthly,quarterly,annual | [[12,"优"],[6,"良"],[3,"中"],[null,"差"]] |
| 12 | ar_days | 应收款周转天数 | 营运能力 | 天 | monthly,quarterly,annual | [[30,"优"],[60,"良"],[90,"中"],[null,"差"]] (ascending) |
| 13 | inventory_turnover | 存货周转率 | 营运能力 | 次 | monthly,quarterly,annual | [[8,"优"],[4,"良"],[2,"中"],[null,"差"]] |
| 14 | asset_turnover | 总资产周转率 | 营运能力 | 次 | monthly,quarterly,annual | [[1.2,"优"],[0.8,"良"],[0.5,"中"],[null,"差"]] |
| 15 | revenue_growth | 营业收入增长率 | 成长能力 | % | monthly,quarterly,annual | [[20,"优"],[10,"良"],[0,"中"],[null,"差"]] |
| 16 | asset_growth | 资产增长率 | 成长能力 | % | monthly,quarterly,annual | [[20,"优"],[10,"良"],[0,"中"],[null,"差"]] |
| 17 | cash_to_revenue | 销售收现比 | 现金流 | | monthly,quarterly,annual | [[1.0,"优"],[0.8,"良"],[0.5,"中"],[null,"差"]] |
| 18 | vat_burden | 增值税税负率 | 税负率类 | % | monthly,quarterly,annual | None（行业差异大） |
| 19 | eit_burden | 企业所得税税负率 | 税负率类 | % | quarterly,annual | None |
| 20 | total_tax_burden | 综合税负率 | 税负率类 | % | monthly,quarterly,annual | None |
| 21 | output_input_ratio | 销项进项配比率 | 增值税重点指标 | | monthly,quarterly,annual | None |
| 22 | transfer_out_ratio | 进项税额转出占比 | 增值税重点指标 | % | monthly,quarterly,annual | None |
| 23 | taxable_income_ratio | 应税所得率 | 所得税重点指标 | % | quarterly,annual | None |
| 24 | zero_filing_ratio | 零申报率 | 风险预警类 | % | quarterly,annual | None |
| 25 | invoice_anomaly_ratio | 发票开具异常率 | 风险预警类 | % | monthly,quarterly,annual | None |

**2b. 扩展 `financial_metrics_synonyms`**（在 `calculate_metrics.py` 的 `seed_metric_synonyms` 中追加）

新增同义词：
- 净利润增长率, 利润增长率 → metric_name
- 管理费用率, 管理费用占比 → metric_name
- 销售费用率, 销售费用占比 → metric_name
- 应收款周转天数, 应收账款周转天数, 回款天数 → metric_name
- 总资产周转率, 资产周转率 → metric_name
- 资产增长率, 总资产增长率 → metric_name
- 发票开具异常率, 发票异常率, 顶额开具率 → metric_name
- 现金债务保障比率, 现金比率 → metric_name
- 费用控制, 费用指标 → metric_category
- 月度, 按月 → period_type
- 季度, 按季 → period_type
- 年度, 按年 → period_type

### Phase 3: 计算脚本 — 新建 `database/calculate_metrics_v2.py`

保留旧 `calculate_metrics.py` 不修改，新建 v2 脚本。

**核心架构：**

```python
# 三个计算函数，分别处理不同粒度
def _compute_monthly(conn, tid, year, month) -> list:
    """月度指标：利润用'本期'，BS用当月快照，CF用'本期'，VAT用'本月'"""

def _compute_quarterly(conn, tid, year, quarter) -> list:
    """季度指标：利润/CF用YTD差值法，BS用季末快照，EIT用季度表"""

def _compute_annual(conn, tid, year) -> list:
    """年度指标：利润/CF用'本年累计'(month=12)，BS用12月快照，EIT用年度表"""
```

**各指标的数据源字段映射：**

| 指标 | 利润表字段 | 资产负债表字段 | 现金流量表字段 | VAT字段 | EIT字段 | 发票字段 |
|------|-----------|--------------|--------------|---------|---------|---------|
| gross_margin | operating_revenue, operating_cost | | | | | |
| net_margin | net_profit, operating_revenue | | | | | |
| roe | net_profit | equity_begin, equity_end | | | | |
| net_profit_growth | net_profit (当期+上期) | | | | | |
| admin_expense_ratio | administrative_expense, operating_revenue | | | | | |
| sales_expense_ratio | selling_expense, operating_revenue | | | | | |
| debt_ratio | | liabilities_end, assets_end | | | | |
| current_ratio | | current_assets_end, current_liabilities_end | | | | |
| quick_ratio | | current_assets_end, inventory_end, current_liabilities_end | | | | |
| cash_debt_coverage | | liabilities_end | operating_net_cash | | | |
| ar_turnover | operating_revenue | accounts_receivable_begin, accounts_receivable_end | | | | |
| ar_days | (derived from ar_turnover) | | | | | |
| inventory_turnover | operating_cost | inventory_begin, inventory_end | | | | |
| asset_turnover | operating_revenue | assets_begin, assets_end | | | | |
| revenue_growth | operating_revenue (当期+上期) | | | | | |
| asset_growth | | assets_end (当期+上期) | | | | |
| cash_to_revenue | operating_revenue | | operating_inflow_sales (CAS) / operating_receipts_sales (SAS) | | | |
| vat_burden | | | | total_tax_payable, sales_taxable_rate (一般) / tax_due_total, sales_3pct+5pct (小规模) | | |
| eit_burden | operating_revenue | | | | actual_tax_payable | |
| total_tax_burden | operating_revenue | | | total_tax_payable + city_maintenance_tax + education_surcharge + local_education_surcharge (一般) / tax_due_total (小规模) | actual_tax_payable | |
| output_input_ratio | | | | output_tax, input_tax | | |
| transfer_out_ratio | | | | transfer_out, input_tax | | |
| taxable_income_ratio | | | | | taxable_income, revenue | |
| zero_filing_ratio | | | | 统计零申报月份数 | | |
| invoice_anomaly_ratio | | | | | | inv_spec_sales: amount, invoice_pk |

**季度利润/现金流取数逻辑（YTD差值法）：**
```python
# Q2 营业收入 = YTD(6月) - YTD(3月)
q_end_month = quarter * 3  # 3, 6, 9, 12
q_prev_month = q_end_month - 3  # 0, 3, 6, 9
ytd_current = fetch(time_range='本年累计', month=q_end_month)
ytd_prev = fetch(time_range='本年累计', month=q_prev_month) if q_prev_month > 0 else 0
quarterly_value = ytd_current - ytd_prev
```

**月度综合税负率特殊处理：**
月度无 EIT 数据，仅计算 VAT + 附加税费部分，不含 EIT。

**发票异常率计算逻辑：**
```python
# 档位判定法
TIERS = [10000, 100000, 1000000, 10000000]
# 查询 inv_spec_sales，按 invoice_pk 聚合 amount
# 判断 amount 是否落在 [tier*0.9, tier) 区间
```

**入口函数：**
```python
def calculate_and_save_v2(db_path=None, taxpayer_id=None, year=None, month=None):
    """主入口：遍历纳税人/期间，计算月度+季度+年度指标，写入 financial_metrics_item"""
```

### Phase 4: Pipeline 集成

**4a. `modules/schema_catalog.py`**（line 370-383）
- `VIEW_COLUMNS["vw_financial_metrics"]` 加入 `"period_type"`（在 `period_month` 之后）
- `FINANCIAL_METRICS_DIM_COLS` 加入 `"period_type"`

**4b. `modules/entity_preprocessor.py`**（line 151-158）
- `_FINANCIAL_METRICS_ITEMS_UNIQUE` 追加：`'净利润增长率'`, `'管理费用率'`, `'销售费用率'`, `'应收款周转天数'`, `'应收账款周转天数'`, `'资产增长率'`, `'发票开具异常率'`, `'发票异常率'`, `'顶额开具率'`

**4c. `prompts/stage2_financial_metrics.txt`**
- 数据结构说明中加入 `period_type` 字段说明
- metric_category 列表加入 `'费用控制'`
- metric_code/metric_name 列表加入 9 个新指标
- 常见查询模式加入 period_type 过滤示例

**4d. `modules/metric_calculator.py`**（G3 实时路径，可选）
- 追加 `admin_expense_ratio`、`sales_expense_ratio` 的实时计算公式

### Phase 5: 初始化流程

```bash
# 1. 重建数据库（或增量执行 DDL）
python -c "from database.init_db import init_database; init_database()"
# 2. 插入种子数据（含指标字典）
python -c "from database.seed_data import seed_reference_data; seed_reference_data()"
# 3. 插入样本数据
python -c "from database.sample_data import insert_sample_data; insert_sample_data()"
# 4. 计算全部指标
python database/calculate_metrics_v2.py
```

---

## 需修改的文件清单

| 文件 | 修改内容 |
|------|---------|
| `database/init_db.py` | 新增2个表DDL + 索引，重建视图DDL |
| `database/seed_data.py` | 新增 `_seed_financial_metrics_item_dict()` |
| `database/calculate_metrics_v2.py` | **新建**，25个指标的月/季/年计算脚本 |
| `database/calculate_metrics.py` | 扩展 `seed_metric_synonyms()` 追加新同义词 |
| `modules/schema_catalog.py` | VIEW_COLUMNS 和 DIM_COLS 加 period_type |
| `modules/entity_preprocessor.py` | 指标关键词列表追加新指标名 |
| `prompts/stage2_financial_metrics.txt` | 更新数据结构说明和指标列表 |
| `modules/metric_calculator.py` | 追加新指标的实时计算公式（可选） |

## 验证方案

1. `python database/calculate_metrics_v2.py` — 确认无报错，输出写入记录数
2. 验证数据：`SELECT COUNT(*) FROM financial_metrics_item` 非空，`SELECT DISTINCT period_type FROM financial_metrics_item` 有三种类型
3. `python run_tests.py` — 确认现有测试不受影响
4. `python test_real_scenarios.py` — 确认现有场景测试通过
5. 启动 `python app.py`，在 Gradio UI 中测试财务指标域查询：
   - "查看纳税人XXX的2025年毛利率" → 应返回年度毛利率
   - "查看纳税人XXX的2025年3月管理费用率" → 应返回月度管理费用率
   - "查看纳税人XXX的盈利能力指标" → 应返回4个盈利能力指标
   - "查看纳税人XXX的费用控制指标" → 应返回2个费用控制指标
