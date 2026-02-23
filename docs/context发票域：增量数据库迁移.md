# 发票域：增量数据库迁移

## Context

上一轮已完成发票域的全部代码修改（12个文件），但现有 `database/fintax_ai.db` 中尚未创建发票相关的数据库对象。DB 不能删除重建（包含其他域的生产数据），需要增量迁移。

### 当前 DB 状态
- 旧空桩 `vw_invoice` 视图仍存在
- 4 张新表不存在：`inv_spec_purchase`, `inv_spec_sales`, `inv_column_mapping`, `inv_synonyms`
- 7 个新索引不存在
- 2 个新视图不存在：`vw_inv_spec_purchase`, `vw_inv_spec_sales`
- 无种子数据（字段映射、同义词）
- 无示例发票数据

### 已完成的代码修改（无需再改）
- `database/init_db.py` — DDL 已添加
- `database/seed_data.py` — `_seed_inv_column_mappings()` + `_seed_inv_synonyms()` 已添加
- `database/sample_data.py` — `_insert_invoice_purchase()` + `_insert_invoice_sales()` 已添加
- `modules/schema_catalog.py` — DOMAIN_VIEWS, VIEW_COLUMNS, INVOICE_DIM_COLS, DOMAIN_CN_MAP 已更新
- `modules/entity_preprocessor.py` — 发票域检测 + 同义词 + 视图路由已添加
- `modules/constraint_injector.py` — invoice scope 处理已添加
- `modules/sql_auditor.py` — invoice period_month 审核已添加
- `modules/sql_writer.py` — prompt 映射已添加
- `prompts/stage1_system.txt` — 发票域规则已添加
- `prompts/stage2_invoice.txt` — 已创建
- `mvp_pipeline.py` — invoice 分支已添加
- `CLAUDE.md` — 已更新

## 实施步骤

### Step 1: 创建迁移脚本 `database/migrate_invoice.py`

一次性迁移脚本，对现有 DB 执行增量 DDL + 数据插入：

```python
# 1. DROP VIEW IF EXISTS vw_invoice  (移除旧空桩)
# 2. CREATE TABLE IF NOT EXISTS inv_spec_purchase (...)
# 3. CREATE TABLE IF NOT EXISTS inv_spec_sales (...)
# 4. CREATE TABLE IF NOT EXISTS inv_column_mapping (...)
# 5. CREATE TABLE IF NOT EXISTS inv_synonyms (...)
# 6. CREATE INDEX IF NOT EXISTS (7 indexes)
# 7. CREATE VIEW IF NOT EXISTS vw_inv_spec_purchase (...)
# 8. CREATE VIEW IF NOT EXISTS vw_inv_spec_sales (...)
# 9. 调用 seed_data._seed_inv_column_mappings(cur)
# 10. 调用 seed_data._seed_inv_synonyms(cur)
# 11. 调用 sample_data._insert_invoice_purchase(cur)
# 12. 调用 sample_data._insert_invoice_sales(cur)
```

DDL 全部使用 `IF NOT EXISTS`，数据插入使用 `INSERT OR IGNORE`/`INSERT OR REPLACE`，脚本可安全重复执行。

### Step 2: 执行迁移

```bash
python database/migrate_invoice.py
```

### Step 3: 验证

```bash
# 确认表/视图/数据
python -c "
import sqlite3
conn = sqlite3.connect('database/fintax_ai.db')
cur = conn.cursor()
for t in ['inv_spec_purchase','inv_spec_sales','inv_column_mapping','inv_synonyms']:
    cnt = cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {cnt} rows')
for v in ['vw_inv_spec_purchase','vw_inv_spec_sales']:
    cnt = cur.execute(f'SELECT COUNT(*) FROM {v}').fetchone()[0]
    print(f'{v}: {cnt} rows')
old = cur.execute(\"SELECT name FROM sqlite_master WHERE name='vw_invoice'\").fetchall()
print(f'vw_invoice removed: {not old}')
conn.close()
"

# 运行原有测试确保不破坏
python run_tests.py
python test_real_scenarios.py
```

## 关键文件

| 文件 | 操作 |
|------|------|
| `database/migrate_invoice.py` | 新建：一次性增量迁移脚本 |
