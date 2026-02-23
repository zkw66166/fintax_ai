# 现金流量表数据模型重构：宽表 → EAV 纵表

## Context

当前现金流量表使用两张宽表 `fs_cash_flow_eas`（35数据列）和 `fs_cash_flow_sas`（22数据列）分别存储企业会计准则和小企业会计准则的数据。这与利润表重构前的问题相同：
- 新增准则需要新建整张表
- 项目变动需要 DDL 变更（加列/改列）
- 两张表结构完全不同，维护成本高

目标：参照利润表 `fs_income_statement_item` 的 EAV 模式，合并为单张纵表 `fs_cash_flow_item`，同时保持 `vw_cash_flow_eas` 和 `vw_cash_flow_sas` 视图结构完全不变，下游代码零修改。

## 决策：向后兼容（同利润表方案 A）

- 视图保持原结构（含 `time_range`、`taxpayer_type`、`accounting_standard` 列）
- `item_code` 使用现有列名（如 `operating_inflow_sales`）
- 同义词 `column_name` 映射到原列名
- `gaap_type` 使用 'CAS'/'SAS'

---

## 实施计划

### Phase 1: 替换表 DDL（init_db.py lines 900-1021）

**删除：**
- `fs_cash_flow_eas` 表 + 4个索引（lines 900-953）
- `fs_cash_flow_sas` 表 + 4个索引（lines 955-996）
- `fs_cf_eas_column_mapping` 和 `fs_cf_sas_column_mapping`（lines 998-1008）
- `fs_cf_synonyms` 表 + 2个索引（lines 1010-1021）

**新建：**

1. `fs_cash_flow_item` 纵表
   ```sql
   CREATE TABLE IF NOT EXISTS fs_cash_flow_item (
       taxpayer_id TEXT NOT NULL, period_year INTEGER NOT NULL,
       period_month INTEGER NOT NULL, gaap_type TEXT NOT NULL,
       item_code TEXT NOT NULL, revision_no INTEGER NOT NULL DEFAULT 0,
       submitted_at TIMESTAMP, etl_batch_id TEXT, source_doc_id TEXT,
       source_unit TEXT DEFAULT '元', etl_confidence REAL,
       current_amount NUMERIC, cumulative_amount NUMERIC,
       item_name TEXT, line_number INTEGER, category TEXT,
       PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
       CHECK (gaap_type IN ('CAS', 'SAS')), CHECK (revision_no >= 0)
   )
   ```

2. `fs_cash_flow_item_dict` 字典表
   - CAS 35项 + SAS 22项（数据来自现有 `seed_cf.py` 的 column_mapping）

3. `fs_cash_flow_synonyms` 同义词表
   - 字段: `phrase`, `column_name`, `gaap_type`, `priority`
   - `UNIQUE(phrase, column_name, gaap_type)`
   - 替代 `fs_cf_synonyms`（`scope_view` → `gaap_type`）

4. 新索引
   - `idx_cf_period` on `(period_year, period_month)`
   - `idx_cf_taxpayer` on `(taxpayer_id)`
   - `idx_cf_taxpayer_period` on `(taxpayer_id, period_year, period_month)`

### Phase 2: 重建视图（init_db.py `_get_cash_flow_view_ddl()`）

使用 `MAX(CASE WHEN) + CROSS JOIN` 透视模式（同利润表）：

```python
def _get_cash_flow_view_ddl():
    CAS_ITEMS = [
        'operating_inflow_sales', 'operating_inflow_tax_refund', 'operating_inflow_other',
        'operating_inflow_subtotal', 'operating_outflow_purchase', 'operating_outflow_labor',
        'operating_outflow_tax', 'operating_outflow_other', 'operating_outflow_subtotal',
        'operating_net_cash', 'investing_inflow_sale_investment', 'investing_inflow_returns',
        'investing_inflow_disposal_assets', 'investing_inflow_disposal_subsidiary',
        'investing_inflow_other', 'investing_inflow_subtotal',
        'investing_outflow_purchase_assets', 'investing_outflow_purchase_investment',
        'investing_outflow_acquire_subsidiary', 'investing_outflow_other',
        'investing_outflow_subtotal', 'investing_net_cash',
        'financing_inflow_capital', 'financing_inflow_borrowing', 'financing_inflow_other',
        'financing_inflow_subtotal', 'financing_outflow_debt_repayment',
        'financing_outflow_dividend_interest', 'financing_outflow_other',
        'financing_outflow_subtotal', 'financing_net_cash',
        'fx_impact', 'net_increase_cash', 'beginning_cash', 'ending_cash',
    ]
    SAS_ITEMS = [
        'operating_receipts_sales', 'operating_receipts_other',
        'operating_payments_purchase', 'operating_payments_staff',
        'operating_payments_tax', 'operating_payments_other', 'operating_net_cash',
        'investing_receipts_disposal_investment', 'investing_receipts_returns',
        'investing_receipts_disposal_assets',
        'investing_payments_purchase_investment', 'investing_payments_purchase_assets',
        'investing_net_cash',
        'financing_receipts_borrowing', 'financing_receipts_capital',
        'financing_payments_debt_principal', 'financing_payments_debt_interest',
        'financing_payments_dividend', 'financing_net_cash',
        'net_increase_cash', 'beginning_cash', 'ending_cash',
    ]
    # 生成 vw_cash_flow_eas (CAS) 和 vw_cash_flow_sas (SAS)
    # 关键：视图元数据列包含 taxpayer_type 和 accounting_standard（非 accounting_standard_name）
    # 关键：WHERE 同时过滤 i.gaap_type 和 t.accounting_standard
```

视图输出列与现有完全一致：
- `vw_cash_flow_eas`: 13 metadata + 35 data = 48 列
- `vw_cash_flow_sas`: 13 metadata + 22 data = 35 列

### Phase 3: 种子数据（seed_cf.py 全面重写）

**替换 `seed_cf_column_mappings()`** → `seed_cf_item_dict(cur)`
- 插入 CAS 35项 + SAS 22项到 `fs_cash_flow_item_dict`
- 数据来源：现有 `seed_cf.py` 的 general/small 列表（line_number, column_name, business_name）
- 增加 `category` 字段：
  - CAS lines 1-10 → '经营活动', 11-22 → '投资活动', 23-31 → '筹资活动', 32-35 → '汇总'
  - SAS lines 1-7 → '经营活动', 8-13 → '投资活动', 14-19 → '筹资活动', 20-22 → '汇总'

**替换 `seed_fs_cf_synonyms()`** → `seed_cf_synonyms(cur)`
- 插入到 `fs_cash_flow_synonyms`（`gaap_type` 替代 `scope_view`）
- CAS: `scope_view='vw_cash_flow_eas'` → `gaap_type='CAS'`
- SAS: `scope_view='vw_cash_flow_sas'` → `gaap_type='SAS'`
- 去掉 `taxpayer_type` 列（现有数据全为 NULL）

### Phase 4: 示例数据（sample_data.py `_insert_cash_flow()`）

重写为 EAV 格式：
- 华兴科技(CAS): 3月 × 35项 = 105 行
- 鑫源贸易(SAS): 3月 × 22项 = 66 行
- 总计: 171 行（原 12 行）
- 每行包含 `current_amount`（本期）和 `cumulative_amount`（本年累计）
- 数据值从现有宽表数据转换

### Phase 5: 更新下游引用

1. **`modules/entity_preprocessor.py`** (lines 842-849)
   ```python
   elif domain == 'cash_flow':
       gaap_filter = None
       if scope_view == 'vw_cash_flow_sas':
           gaap_filter = 'SAS'
       elif scope_view == 'vw_cash_flow_eas':
           gaap_filter = 'CAS'
       rows = cur.execute(
           """SELECT phrase, column_name, priority FROM fs_cash_flow_synonyms
           WHERE (gaap_type IS NULL OR gaap_type = ?)
           ORDER BY priority DESC, LENGTH(phrase) DESC""",
           (gaap_filter,)
       ).fetchall()
   ```

2. **`database/seed_data.py`** (lines 30-31, 38-45)
   - `_seed_cf_column_mappings` → `_seed_cf_item_dict`（调用 `seed_cf_item_dict`）
   - `_seed_cf_synonyms` → 调用新的 `seed_cf_synonyms`

3. **以下文件无需修改**（视图结构不变）：
   - `modules/schema_catalog.py`
   - `prompts/stage2_cash_flow.txt`
   - `modules/sql_auditor.py`
   - `modules/intent_parser.py`
   - `modules/constraint_injector.py`
   - `database/calculate_metrics.py`
   - `modules/metric_calculator.py`
   - `mvp_pipeline.py`

### Phase 6: 更新文档

- `CLAUDE.md`: 更新现金流量表相关描述（宽表→EAV、表名、gaap_type）

### Phase 7: 验证

```bash
python -c "from database.init_db import init_database; init_database()"
python -c "from database.seed_data import seed_reference_data; seed_reference_data()"
python -c "from database.sample_data import insert_sample_data; insert_sample_data()"
python database/calculate_metrics.py
python run_tests.py
python test_real_scenarios.py
```

## 关键文件清单

| 文件 | 修改内容 |
|------|----------|
| `database/init_db.py` | 替换2张宽表+2张映射表+1张同义词表 → 1张EAV表+1张字典表+1张同义词表；重写视图DDL |
| `database/seed_cf.py` | 全面重写：字典数据+同义词数据 |
| `database/seed_data.py` | 更新wrapper函数名和import |
| `database/sample_data.py` | 重写 `_insert_cash_flow()` 为EAV格式 |
| `modules/entity_preprocessor.py` | 同义词查询改用 `fs_cash_flow_synonyms` + `gaap_type` |
| `CLAUDE.md` | 文档更新 |
