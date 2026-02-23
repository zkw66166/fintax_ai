# 专用发票表数据库设计实施方案

## Context

fintax_ai 的发票域(invoice)目前仅有一个空桩视图 `vw_invoice`。需要完成专用发票（进项/销项）的完整数据库设计和 NL2SQL 管线集成，使用户可以通过自然语言查询发票数据。

## 设计概要

### 两张宽表

| 表名 | 用途 | taxpayer_id 来源 |
|------|------|-----------------|
| `inv_spec_purchase` | 进项发票（采购发票） | buyer_tax_id（购方识别号，即"我方"） |
| `inv_spec_sales` | 销项发票（销售发票） | seller_tax_id（销方识别号，即"我方"） |

### 主键设计（用户确认）

两表统一增加两个字段：
- `invoice_format` TEXT NOT NULL — '数电' 或 '非数电'（ETL 判断：digital_invoice_no 有效值→数电，否则→非数电）
- `invoice_pk` TEXT NOT NULL — 数电发票取 digital_invoice_no，非数电发票取 invoice_number

**主键：**
- `inv_spec_purchase`: PK = `(taxpayer_id, invoice_pk, line_no)` — line_no 为发票内行号（同一张发票多行商品明细）
- `inv_spec_sales`: PK = `(taxpayer_id, invoice_pk, line_no)` — line_no 默认为 1（销项发票通常单行）

### 字段设计

**共有字段（两表均有）：**
- `taxpayer_id` TEXT NOT NULL — 我方纳税人识别号
- `period_year` INTEGER NOT NULL — 从 invoice_date 提取
- `period_month` INTEGER NOT NULL — 从 invoice_date 提取
- `invoice_format` TEXT NOT NULL — '数电' / '非数电'
- `invoice_pk` TEXT NOT NULL — 主键标识（数电票号码或发票号码）
- `line_no` INTEGER NOT NULL DEFAULT 1 — 发票内行号
- `invoice_code` TEXT — 发票代码
- `invoice_number` TEXT — 发票号码
- `digital_invoice_no` TEXT — 数电票号码
- `seller_tax_id` TEXT — 销方识别号
- `seller_name` TEXT — 销方名称
- `buyer_tax_id` TEXT — 购方识别号
- `buyer_name` TEXT — 购买方名称
- `invoice_date` TEXT — 开票日期
- `amount` REAL — 金额
- `tax_amount` REAL — 税额
- `total_amount` REAL — 价税合计
- `invoice_source` TEXT — 发票来源
- `invoice_type` TEXT — 发票票种
- `invoice_status` TEXT — 发票状态
- `is_positive` TEXT — 是否正数发票（是/否）
- `risk_level` TEXT — 发票风险等级
- `issuer` TEXT — 开票人
- `remark` TEXT — 备注
- `submitted_at` TIMESTAMP — 元数据
- `etl_batch_id` TEXT — 元数据

**进项发票独有字段：**
- `tax_category_code` TEXT — 税收分类编码
- `special_business_type` TEXT — 特定业务类型
- `goods_name` TEXT — 货物或应税劳务名称
- `specification` TEXT — 规格型号
- `unit` TEXT — 单位
- `quantity` REAL — 数量
- `unit_price` REAL — 单价
- `tax_rate` TEXT — 税率

### 域冲突处理（用户确认）

采用"发票后缀优先"策略：
- 含"发票"字样时优先走 invoice 域（如"进项发票"→invoice，"进项税"→VAT）
- 发票域关键词在域检测链中排在 VAT 之前

### 两个视图

- `vw_inv_spec_purchase` — JOIN taxpayer_info，暴露所有查询列
- `vw_inv_spec_sales` — JOIN taxpayer_info，暴露所有查询列
- 删除原有空桩 `vw_invoice`

### 域路由

- `DOMAIN_VIEWS["invoice"]` → `["vw_inv_spec_purchase", "vw_inv_spec_sales"]`
- intent JSON 新增 `invoice_scope.direction`: `"purchase"` | `"sales"` | `"both"`
- 关键词路由：含"进项发票"/"采购发票" → purchase；含"销项发票"/"销售发票" → sales；仅"发票" → both

---

## 实施步骤（按依赖顺序）

### Phase 1: DDL + 数据层

**1.1 `database/init_db.py`** — 在 `get_ddl_statements()` 的 section 9b 之前插入

新增表 DDL：
- `inv_spec_purchase` — 30列宽表（含 invoice_format, invoice_pk, line_no + 共有字段 + 进项独有字段）
  - PK: `(taxpayer_id, invoice_pk, line_no)`
  - CHECK: `invoice_format IN ('数电', '非数电')`
- `inv_spec_sales` — 22列宽表（共有字段，无进项独有字段）
  - PK: `(taxpayer_id, invoice_pk, line_no)`
  - CHECK: `invoice_format IN ('数电', '非数电')`
- `inv_column_mapping` — 字段映射表
  - 列: `id`, `source_column`(中文), `target_field`(英文), `table_name`, `description`
- `inv_synonyms` — 同义词表
  - 列: `id`, `phrase`, `column_name`, `priority`, `scope_view`
  - UNIQUE: `(phrase, column_name, scope_view)`

索引：
- `idx_inv_purchase_taxpayer_period` ON inv_spec_purchase(taxpayer_id, period_year, period_month)
- `idx_inv_purchase_pk` ON inv_spec_purchase(invoice_pk)
- `idx_inv_purchase_date` ON inv_spec_purchase(invoice_date)
- `idx_inv_sales_taxpayer_period` ON inv_spec_sales(taxpayer_id, period_year, period_month)
- `idx_inv_sales_pk` ON inv_spec_sales(invoice_pk)
- `idx_inv_sales_date` ON inv_spec_sales(invoice_date)
- `idx_inv_synonyms_phrase` ON inv_synonyms(phrase)

视图（替换原空桩 `vw_invoice`）：
- 删除 `vw_invoice` 空桩 DDL
- `vw_inv_spec_purchase` — `SELECT p.*, t.taxpayer_name, t.taxpayer_type FROM inv_spec_purchase p JOIN taxpayer_info t ON p.taxpayer_id = t.taxpayer_id`
- `vw_inv_spec_sales` — `SELECT s.*, t.taxpayer_name, t.taxpayer_type FROM inv_spec_sales s JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id`

**1.2 `database/seed_data.py`** — 在 `seed_reference_data()` 末尾添加调用

新增函数：
- `_seed_inv_column_mappings(cur)` — 两表完整字段映射
  - 进项: 序号→seq_no, 发票代码→invoice_code, 发票号码→invoice_number, 数电票号码→digital_invoice_no, 销方识别号→seller_tax_id, 销方名称→seller_name, 购方识别号→buyer_tax_id, 购买方名称→buyer_name, 开票日期→invoice_date, 税收分类编码→tax_category_code, 特定业务类型→special_business_type, 货物或应税劳务名称→goods_name, 规格型号→specification, 单位→unit, 数量→quantity, 单价→unit_price, 金额→amount, 税率→tax_rate, 税额→tax_amount, 价税合计→total_amount, 发票来源→invoice_source, 发票票种→invoice_type, 发票状态→invoice_status, 是否正数发票→is_positive, 发票风险等级→risk_level, 开票人→issuer, 备注→remark
  - 销项: 同上但无 tax_category_code ~ tax_rate 8个字段
- `_seed_inv_synonyms(cur)` — ~80条同义词，按类别：
  - 金额: 金额→amount, 不含税金额→amount, 税额→tax_amount, 增值税额→tax_amount, 价税合计→total_amount, 含税金额→total_amount, 发票金额→amount
  - 票面: 发票代码→invoice_code, 发票号码→invoice_number, 数电票号码→digital_invoice_no, 票号→invoice_pk, 发票编号→invoice_pk
  - 对方: 购买方→buyer_name, 购方→buyer_name, 购方名称→buyer_name, 销售方→seller_name, 销方→seller_name, 销方名称→seller_name, 购方识别号→buyer_tax_id, 销方识别号→seller_tax_id, 供应商→seller_name(scope=purchase), 客户→buyer_name(scope=sales)
  - 状态: 发票状态→invoice_status, 正常发票→invoice_status, 作废→invoice_status, 红冲→is_positive, 红字→is_positive, 蓝字→is_positive, 正数发票→is_positive, 负数发票→is_positive
  - 票种: 专用发票→invoice_type, 普通发票→invoice_type, 数电票→invoice_format, 纸质发票→invoice_format
  - 风险: 风险等级→risk_level, 发票风险→risk_level
  - 明细(进项scope): 商品名称→goods_name, 货物名称→goods_name, 劳务名称→goods_name, 规格型号→specification, 规格→specification, 型号→specification, 单位→unit, 数量→quantity, 单价→unit_price, 税率→tax_rate, 税收分类编码→tax_category_code
  - 其他: 开票日期→invoice_date, 开票时间→invoice_date, 开票人→issuer, 备注→remark, 发票来源→invoice_source

**1.3 `database/sample_data.py`** — 在 `insert_sample_data()` 末尾添加调用

新增函数（使用华兴科技 91310000MA1FL8XQ30，2025年12月数据）：
- `_insert_invoice_purchase(cur)` — 10条进项发票
  - 含数电（invoice_format='数电', invoice_pk=digital_invoice_no）和非数电（invoice_format='非数电', invoice_pk=invoice_number）
  - 含多行明细（同一 invoice_pk 不同 line_no）
  - 含正数和红冲（is_positive='是'/'否'）
  - 含专用发票和普通发票
  - 供应商使用虚构名称
- `_insert_invoice_sales(cur)` — 10条销项发票
  - 全部数电（与CSV数据一致）
  - 含正数和红冲
  - 含专用发票和普通发票
  - 客户使用虚构名称

### Phase 2: Schema + 配置层

**2.1 `modules/schema_catalog.py`** — 这是 `config/settings.py` 之外的白名单文件

修改：
- `DOMAIN_VIEWS["invoice"]` → `["vw_inv_spec_purchase", "vw_inv_spec_sales"]`（替换原 `["vw_invoice"]`）
- 添加 `VIEW_COLUMNS["vw_inv_spec_purchase"]` — 完整列清单（taxpayer_id, taxpayer_name, taxpayer_type, period_year, period_month, invoice_format, invoice_pk, line_no, invoice_code, invoice_number, digital_invoice_no, seller_tax_id, seller_name, buyer_tax_id, buyer_name, invoice_date, tax_category_code, special_business_type, goods_name, specification, unit, quantity, unit_price, amount, tax_rate, tax_amount, total_amount, invoice_source, invoice_type, invoice_status, is_positive, risk_level, issuer, remark）
- 添加 `VIEW_COLUMNS["vw_inv_spec_sales"]` — 同上但无进项独有8列
- 添加 `INVOICE_DIM_COLS` — 维度列集合：`['taxpayer_id', 'taxpayer_name', 'taxpayer_type', 'period_year', 'period_month', 'invoice_format', 'invoice_pk', 'line_no', 'invoice_code', 'invoice_number', 'digital_invoice_no', 'seller_tax_id', 'seller_name', 'buyer_tax_id', 'buyer_name', 'invoice_date', 'invoice_source', 'invoice_type', 'invoice_status', 'is_positive', 'risk_level', 'issuer', 'remark']`
- 更新 `DOMAIN_CN_MAP` — 添加：'进项发票'→'invoice', '销项发票'→'invoice', '采购发票'→'invoice', '销售发票'→'invoice', '专用发票'→'invoice', '普通发票'→'invoice', '数电票'→'invoice'

### Phase 3: 管线模块层

**3.1 `modules/entity_preprocessor.py`**

在域检测函数 `detect_entities()` 中：
- 添加 `_INVOICE_KEYWORDS` 列表：'发票', '进项发票', '销项发票', '采购发票', '销售发票', '专用发票', '普通发票', '数电票', '红冲发票', '红字发票', '蓝字发票', '开票人', '发票号码', '发票代码', '价税合计', '发票金额', '票面金额'
- 在域检测链中，在 VAT 检测之前插入发票域检测（关键：含"发票"字样优先走 invoice）
- 检测逻辑：`if any(kw in query for kw in _INVOICE_KEYWORDS):`
- 添加发票方向检测：
  - '进项发票' or '采购发票' in query → `entities['invoice_direction'] = 'purchase'`
  - '销项发票' or '销售发票' in query → `entities['invoice_direction'] = 'sales'`
  - else → `entities['invoice_direction'] = 'both'`

在 `normalize_query()` 中：
- 添加 `domain == 'invoice'` 分支，查询 `inv_synonyms` 表
- SQL: `SELECT phrase, column_name, priority FROM inv_synonyms WHERE ? LIKE '%' || phrase || '%' ORDER BY LENGTH(phrase) DESC, priority DESC`

在 `get_scope_view()` 中：
- 添加 `domain == 'invoice'` 分支
- direction='purchase' → `['vw_inv_spec_purchase']`
- direction='sales' → `['vw_inv_spec_sales']`
- direction='both' → `['vw_inv_spec_purchase', 'vw_inv_spec_sales']`

**3.2 `modules/constraint_injector.py`**

在 `inject_constraints()` 中：
- 添加 `elif domain == 'invoice' and intent_json.get('invoice_scope'):` 分支
  - `allowed_views = intent_json['invoice_scope'].get('views', DOMAIN_VIEWS.get('invoice', []))`
- 添加 `elif domain == 'invoice':` 默认分支
  - `allowed_views = DOMAIN_VIEWS.get('invoice', ['vw_inv_spec_purchase', 'vw_inv_spec_sales'])`
- 在 import 中添加 `INVOICE_DIM_COLS`
- 在维度列选择中添加 `elif view_domain == 'invoice': dim_set = set(INVOICE_DIM_COLS)`
- 在跨域视图名推断中添加 `elif 'inv' in view: view_domain = 'invoice'`

**3.3 `modules/sql_auditor.py`**

在 period_month 检查区域添加：
```python
if domain == 'invoice':
    has_month = (
        re.search(r'period_month\s*=', sql_stripped, re.I) or
        re.search(r'period_month\s*BETWEEN', sql_stripped, re.I) or
        re.search(r'period_month\s*>=', sql_stripped, re.I) or
        re.search(r'period_year\s*\*\s*100\s*\+\s*period_month', sql_stripped, re.I)
    )
    if not has_month:
        violations.append("缺少月份过滤(period_month)")
```

**3.4 `modules/sql_writer.py`**

在 `_DOMAIN_PROMPT_MAP` 中添加：
```python
'invoice': 'stage2_invoice.txt',
```

### Phase 4: LLM Prompt 层

**4.1 `prompts/stage1_system.txt`**

在域列表中更新 invoice 行：
```
- invoice: 发票（视图: vw_inv_spec_purchase 进项/采购发票, vw_inv_spec_sales 销项/销售发票）
```

添加发票域判断规则（在 VAT 规则之前）：
```
【发票域判断】
- 含"发票"字样（进项发票、销项发票、采购发票、销售发票、专用发票、普通发票、数电票、红冲发票等）→ domain=invoice
- 注意区分：进项发票→invoice，进项税→vat；销项发票→invoice，销项税→vat
- 方向判断：进项发票/采购发票→direction=purchase；销项发票/销售发票→direction=sales；仅"发票"→direction=both
```

添加 `invoice_scope` 到 JSON Schema：
```json
"invoice_scope": {
  "direction": "purchase|sales|both",
  "views": ["vw_inv_spec_purchase"]
}
```

**4.2 `prompts/stage2_invoice.txt`（新建）**

参照 `stage2_account_balance.txt` 格式，包含：
- 角色定义 + 只读SQL约束
- 允许视图/列占位符
- 必备过滤：taxpayer_id, period_year, period_month
- 发票特有过滤指导：
  - 按发票状态：`invoice_status = '正常'`
  - 按正负：`is_positive = '是'` / `is_positive = '否'`（红冲）
  - 按票种：`invoice_type LIKE '%专用%'` / `invoice_type LIKE '%普通%'`
  - 按发票格式：`invoice_format = '数电'` / `invoice_format = '非数电'`
  - 按对方：`seller_name LIKE '%xxx%'`（进项）/ `buyer_name LIKE '%xxx%'`（销项）
  - 按商品（进项）：`goods_name LIKE '%xxx%'`
- 聚合指导：SUM(amount), SUM(tax_amount), SUM(total_amount), COUNT(DISTINCT invoice_pk)
- LIMIT 要求
- 用户意图JSON占位符

### Phase 5: Pipeline 集成

**5.1 `mvp_pipeline.py`**
- 在 Step 2 scope_view 选择中添加 `elif domain_hint == 'invoice':` 分支
- 根据 entities 中的 invoice_direction 选择视图

### Phase 6: 测试验证

步骤：
1. 删除旧数据库：`rm database/fintax_ai.db`（如存在）
2. 重新初始化：`python -c "from database.init_db import init_database; init_database()"`
3. 种子数据：`python -c "from database.seed_data import seed_reference_data; seed_reference_data()"`
4. 示例数据：`python -c "from database.sample_data import insert_sample_data; insert_sample_data()"`
5. 运行原有测试确保不破坏：
   - `python run_tests.py` — 5个基础测试
   - `python test_real_scenarios.py` — 46个场景测试
6. 手动验证发票查询（通过 pipeline 或 app.py）：
   - "华兴科技2025年12月的销项发票有哪些" → 应返回 vw_inv_spec_sales 数据
   - "华兴科技2025年12月进项发票金额合计" → 应返回 SUM(amount)
   - "华兴科技2025年12月红冲发票" → 应过滤 is_positive='否'
   - "华兴科技2025年12月专用发票税额" → 应过滤 invoice_type LIKE '%专用%'

---

## 关键文件清单

| 文件 | 操作 |
|------|------|
| `database/init_db.py` | 修改：添加表/视图/索引 DDL |
| `database/seed_data.py` | 修改：添加字段映射 + 同义词种子 |
| `database/sample_data.py` | 修改：添加示例发票数据 |
| `config/settings.py` | 修改：添加视图列、维度列、域映射 |
| `modules/entity_preprocessor.py` | 修改：添加发票域检测 + 同义词 + 视图路由 |
| `modules/constraint_injector.py` | 修改：添加 invoice scope 处理 |
| `modules/sql_auditor.py` | 修改：添加 invoice 审核规则 |
| `modules/sql_writer.py` | 修改：添加 prompt 映射 |
| `prompts/stage1_system.txt` | 修改：添加发票域规则 |
| `prompts/stage2_invoice.txt` | 新建：发票 SQL 生成 prompt |
| `mvp_pipeline.py` | 修改：添加 invoice 分支 |
| `CLAUDE.md` | 修改：更新域表格和架构说明 |
