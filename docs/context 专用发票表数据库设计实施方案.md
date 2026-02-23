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

**1.1 `database/init_db.py`**
- 添加 `inv_spec_purchase` 表 DDL（含 invoice_format, invoice_pk, line_no + 所有字段 + PK + 索引）
- 添加 `inv_spec_sales` 表 DDL（同上结构，无进项独有字段）
- 添加 `inv_column_mapping` 表 DDL（source_column, target_field, table_name, description）
- 添加 `inv_synonyms` 表 DDL（phrase, column_name, priority, scope_view）
- 替换空桩 `vw_invoice` 为两个实际视图
- 添加性能索引（taxpayer_id+period, invoice_pk, invoice_date 等）

**1.2 `database/seed_data.py`**
- `_seed_inv_column_mappings(cur)` — 两表完整字段映射（中文原始列名→英文字段名）
- `_seed_inv_synonyms(cur)` — 发票相关同义词（~80条），覆盖：
  - 金额类：金额→amount, 税额→tax_amount, 价税合计→total_amount
  - 方向类：进项发票→purchase, 销项发票→sales
  - 状态类：正常发票→invoice_status='正常', 红冲→is_positive='否'
  - 票种类：专用发票→invoice_type, 普通发票→invoice_type
  - 对方信息：购买方→buyer_name, 销售方→seller_name
  - 明细类（进项）：商品名称→goods_name, 规格型号→specification, 数量→quantity, 单价→unit_price, 税率→tax_rate

**1.3 `database/sample_data.py`**
- `_insert_invoice_purchase(cur)` — 10条进项发票（使用华兴科技 91310000MA1FL8XQ30，2025年12月，含数电和非数电）
- `_insert_invoice_sales(cur)` — 10条销项发票（同上纳税人，含正数和红冲）

### Phase 2: Schema + 配置层

**2.1 `config/settings.py`**
- 更新 `DOMAIN_VIEWS["invoice"]` → `["vw_inv_spec_purchase", "vw_inv_spec_sales"]`
- 添加 `VIEW_COLUMNS["vw_inv_spec_purchase"]` — 完整列清单
- 添加 `VIEW_COLUMNS["vw_inv_spec_sales"]` — 完整列清单
- 添加 `INVOICE_DIM_COLS` — 维度列集合
- 更新 `DOMAIN_CN_MAP` — 添加 '进项发票', '销项发票', '采购发票', '销售发票', '专用发票' 等映射

### Phase 3: 管线模块层

**3.1 `modules/entity_preprocessor.py`**
- 添加 `_INVOICE_KEYWORDS_HIGH` 列表（'发票', '进项发票', '销项发票', '采购发票', '销售发票', '专用发票', '普通发票', '数电票', '红冲发票', '红字发票', '蓝字发票', '开票人', '发票号码', '发票代码', '价税合计'）
- 在域检测链中，在 VAT 检测之前插入发票域检测（关键：含"发票"字样优先走 invoice）
- 添加发票方向检测到 entities dict（`invoice_direction`: purchase/sales/both）
- 在 `normalize_query()` 中添加 `domain == 'invoice'` 分支，查询 `inv_synonyms` 表
- 在 `get_scope_view()` 中添加 `domain == 'invoice'` 分支，根据 direction 返回对应视图

**3.2 `modules/constraint_injector.py`**
- 添加 `elif domain == 'invoice' and intent_json.get('invoice_scope'):` 分支
- 导入 `INVOICE_DIM_COLS`
- 在跨域视图名推断中添加 `elif 'inv' in view:` → `view_domain = 'invoice'`

**3.3 `modules/sql_auditor.py`**
- 添加 `if domain == 'invoice':` 的 period_month 过滤检查

**3.4 `modules/sql_writer.py`**
- 添加 `'invoice': 'stage2_invoice.txt'` 到 `_DOMAIN_PROMPT_MAP`

### Phase 4: LLM Prompt 层

**4.1 `prompts/stage1_system.txt`**
- 更新 invoice 域描述：`- invoice: 发票（视图: vw_inv_spec_purchase, vw_inv_spec_sales）`
- 添加发票域判断规则（在 VAT 规则之前）
- 添加 `invoice_scope` 到 JSON Schema：
  ```json
  "invoice_scope": {
    "direction": "purchase|sales|both",
    "views": ["vw_inv_spec_purchase"]
  }
  ```
- 添加规则：domain=invoice 时必须填写 invoice_scope

**4.2 `prompts/stage2_invoice.txt`（新建）**
- 发票域专用 SQL 生成 prompt，包含：
  - 两个视图的完整列说明
  - 必备过滤：taxpayer_id, period_year, period_month
  - 发票状态/方向过滤指导
  - 聚合查询指导（SUM(amount), COUNT(*) 等）
  - LIMIT 要求

### Phase 5: Pipeline 集成

**5.1 `mvp_pipeline.py`**
- 在 Step 2 scope_view 选择中添加 `elif domain_hint == 'invoice':` 分支
- 根据 entities 中的 invoice_direction 选择视图

### Phase 6: 测试验证

- 删除旧数据库 `database/fintax_ai.db`
- 重新初始化：`python -c "from database.init_db import init_database; init_database()"`
- 种子数据：`python -c "from database.seed_data import seed_reference_data; seed_reference_data()"`
- 示例数据：`python -c "from database.sample_data import insert_sample_data; insert_sample_data()"`
- 运行原有测试：`python run_tests.py` + `python test_real_scenarios.py`
- 手动测试发票查询（通过 pipeline）

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
