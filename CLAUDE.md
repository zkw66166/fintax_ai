# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fintax_ai is a Chinese tax and financial consulting platform (税务智能咨询系统) that uses a two-stage NL2SQL pipeline to answer natural language queries against structured tax return and financial data stored in SQLite.

**Current status**: MVP complete with VAT, EIT, balance sheet, account balance, profit statement (利润表), cash flow statement (现金流量表), invoice (发票, 进项/销项), cross-domain queries (跨域), computed financial metrics (财务指标), and enterprise profile (企业画像) domains. Additionally supports tax incentive policy queries (税收优惠政策, via local `tax_incentives.db`) and external regulation knowledge base queries (法规知识库, via Coze RAG API). Frontend: FastAPI + React SPA with SSE streaming. LLM backend is DeepSeek (`deepseek-chat`) via OpenAI-compatible API.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the NL2SQL pipeline test suite (5 test cases, rebuilds DB from scratch)
python run_tests.py

# Run real-world scenario tests (46 test cases covering all domains)
python test_real_scenarios.py

# Run comprehensive test (57 questions, 9 domains, single+cross-domain, ~96% pass rate)
python test_comprehensive.py

# Run balance sheet unit tests
python -m unittest tests.test_bs

# Run cache validation tests
python test_cache.py

# Run performance benchmarks
python test_performance.py

# Initialize database manually (app.py does this automatically if DB missing)
python -c "from database.init_db import init_database; init_database()"
python -c "from database.seed_data import seed_reference_data; seed_reference_data()"
python -c "from database.sample_data import insert_sample_data; insert_sample_data()"

# Add performance indexes
python database/add_performance_indexes.py

# Calculate financial metrics v1 (17 indicators, run after data changes)
python database/calculate_metrics.py

# Calculate financial metrics v2 (25 indicators, monthly/quarterly/yearly granularity)
python database/calculate_metrics_v2.py

# Migrate enterprise profile fields to taxpayer_info
python database/migrate_profile.py

# Run FastAPI backend (launches on http://0.0.0.0:8000, serves React SPA)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Run display formatter tests
python -m pytest tests/test_display_formatter.py -v

# Run concept registry tests
python -m pytest tests/test_concept_registry.py -v
```

## Architecture

### NL2SQL Pipeline (`mvp_pipeline.py`)

All stages orchestrated in `run_pipeline()`, with three execution paths preceded by an intent router:

**Intent Router** (`modules/intent_router.py`, enabled via `ROUTER_ENABLED` in settings):
- Runs before all domain detection; classifies queries into three routes:
  - `financial_data` → existing NL2SQL pipeline (9 domains)
  - `tax_incentive` → local tax incentive DB search + LLM summary
  - `regulation` → external Coze RAG API
- Multi-layer keyword classification (Layer -2 through Layer 1 + default), with fuzzy taxpayer name matching
- Hot-reloadable config from `config/tax_query_config.json`

**Path Selection** (in order):
- **Metric path** → if query matches a computed metric (e.g. 资产负债率, ROE), bypasses LLM entirely
- **Concept path** → if cross-domain query matches ≥2 registered financial concepts with time granularity, uses deterministic SQL (no LLM); falls back to LLM cross-domain on failure
- **Cross-domain path** → if query spans multiple domains (e.g. compare profit vs VAT)
- **Standard path** → single-domain queries (default)

**Common preprocessing stages:**

1. **Relative Date Resolution** (`modules/entity_preprocessor.py`) — converts "今年3月"→"2026年3月", "去年12月"→"2025年12月", "上个月"→previous month, "上个季度"→previous quarter range; context-aware (VAT "本月" preserved)
2. **Entity Preprocessing** (`modules/entity_preprocessor.py`) — regex extraction of taxpayer_id, period, taxpayer_type; domain detection via keyword heuristics with multi-domain disambiguation (balance_sheet vs account_balance via "年初"/"期初"/"借"/"贷" markers; profit vs EIT via "年度"/"季度"→EIT, "本期金额"/"本年累计"→profit, shared items default→profit); cross-domain upgrade when query contains keywords from multiple domains
3. **Scope-Aware View Selection** (`modules/entity_preprocessor.py:get_scope_view()`) — routes to correct view based on domain + taxpayer_type + accounting_standard (e.g. 一般纳税人→`vw_profit_eas`, 小规模纳税人→`vw_profit_sas`)
4. **Synonym Normalization** (`modules/entity_preprocessor.py`) — longest-match-first, scope-aware mapping from NL phrases to standard column names using domain-specific synonym tables (`vat_synonyms`, `eit_synonyms`, `account_synonyms`, `fs_balance_sheet_synonyms`, `fs_income_statement_synonyms`, `fs_cash_flow_synonyms`)

**Standard path stages:**

5. **Stage 1: Intent Parser** (`modules/intent_parser.py`) — LLM call → strict JSON with `domain`, `views`, `metrics`, `filters`, `need_clarification`; never writes SQL
6. **Constraint Injection** (`modules/constraint_injector.py`) — derives `allowed_views`/`allowed_columns`/`max_rows` from Stage 1 output
7. **Stage 2: SQL Writer** (`modules/sql_writer.py`) — LLM call → read-only SQLite SQL; prompt selected by domain from `prompts/stage2_*.txt`
8. **SQL Audit** (`modules/sql_auditor.py`) — hard-blocks: non-SELECT, multi-statement, disallowed views/columns, missing taxpayer_id filter, missing period filter, no LIMIT, SELECT *, dangerous functions; domain-specific checks (EIT: `period_quarter` filter for quarter views; monthly domains: `period_month` filter; profit/cash_flow: `time_range` validation); supports table-alias-prefixed `period_year*100+period_month` patterns; one retry with feedback on audit failure
9. **Execution** — parameterized query against SQLite; on SQL execution failure, retries once with error feedback to LLM (including SQLite JOIN limitation hints); logs to `user_query_log`

**Cross-domain path** (`modules/cross_domain_calculator.py`):
- Splits query into sub-domain queries → executes each via standard path → merges results
- Operations: `compare` (side-by-side), `ratio` (division), `reconcile` (difference check), `list` (union)
- Uses `UNION ALL` with aligned output schema

**Metric path** (`modules/metric_calculator.py`):
- 8 built-in financial ratios: 资产负债率, 净资产收益率/ROE, 毛利率, 总资产周转率, 净利润率, 流动比率, 现金债务保障比率
- Each metric defines `sources` (cross-domain data requirements), `formula` (Python expression), `label`, `unit`
- Deterministic SQL construction → Python formula evaluation → no LLM needed
- Synonym mapping supports aliases (e.g. "ROE" → "净资产收益率")

### Concept Registry (`modules/concept_registry.py`)

Deterministic cross-domain query engine via pre-registered financial concept mappings:
- 40+ pre-defined financial concepts (采购金额, 销售金额, 存货增加额, 经营现金流出, etc.)
- Concept types: direct values, aggregated values, computed values (e.g. 存货增加额 = end - begin)
- Quarterly strategies: `sum_months` (aggregate 3 months) vs `quarter_end` (take quarter-end month)
- Alias resolution with fuzzy matching of user queries to canonical concept names
- Time granularity detection: monthly/quarterly/yearly patterns from query text
- When ≥2 concepts detected + time granularity → deterministic SQL construction, bypasses LLM entirely
- Falls back to LLM-based cross-domain pipeline on failure

### FastAPI Backend (`api/`)

REST API layer replacing Gradio as the primary frontend backend:
- `api/main.py` — FastAPI entry point with CORS, static file serving for React SPA
- `api/routes/chat.py` — `POST /api/chat` SSE streaming endpoint wrapping `run_pipeline_stream()`; passes `original_query` (without company name prefix) so tax_incentive/regulation routes search on the raw user input
- `api/routes/history.py` — `GET/POST/DELETE /api/chat/history` JSON file-based chat history (max 100 entries)
- `api/routes/company.py` — `GET /api/companies` taxpayer list for UI dropdown
- `api/routes/profile.py` — `GET /api/profile/{taxpayer_id}?year=2025` enterprise profile aggregation endpoint
- `api/schemas.py` — Pydantic request/response models (`ChatRequest`, `HistoryDeleteRequest`, `CompanyItem`)
- Attaches `display_data` (from `build_display_data()`) to financial_data route results before SSE emission

### Display Formatter (`modules/display_formatter.py`)

Presentation layer for query results consumed by the React frontend:
- `ColumnMapper` singleton: lazy-loads column name → Chinese business name mappings from all synonym tables in DB
- Number formatting: intelligent scaling (≥1亿 → "X.XX亿", ≥1万 → "X.XX万"), percentage detection, sign handling
- Domain-specific display: KV lists for single rows, Markdown tables for multi-row, metric cards, cross-domain grouping
- Chart data generation: builds Chart.js-compatible data structures (bar/line/pie) for React frontend
- Growth analysis: calculates period-over-period changes and trends
- `build_display_data(result)` → structured JSON dict for React consumption (summary, table, chart, metadata)

### Enterprise Profile Service (`modules/profile_service.py`)

Company profile aggregation service (企业画像) that queries across all financial domains:
- `get_company_profile(taxpayer_id, year)` → structured JSON with 11 sections:
  - `basic_info` — taxpayer_info fields (including new: registered_capital, registered_address, business_scope, operating_status, collection_method)
  - `asset_structure` — balance sheet asset/liability composition
  - `profit_data` — income statement key figures
  - `cash_flow` — cash flow statement summary
  - `growth_metrics` — year-over-year growth rates
  - `financial_metrics` — key ratios from `financial_metrics_item` table
  - `tax_summary` — VAT + EIT tax burden summary
  - `invoice_summary` — purchase/sales invoice statistics
  - `rd_innovation` — R&D and innovation indicators
  - `cross_border` — cross-border business indicators
  - `compliance_risk` — compliance risk assessment
- Evaluation rules for 8 metrics (debt_ratio, current_ratio, quick_ratio, gross_margin, net_margin, ROE, revenue_growth, total_tax_burden) with threshold-based level/type classification
- Exposed via `GET /api/profile/{taxpayer_id}?year=2025`

### Tax Incentive Query (`modules/tax_incentive_query.py`)

Searches local `database/tax_incentives.db` (1522 policies, FTS5 indexed) with four-tier progressive fallback:
1. Structured search (tax_type + entity LIKE)
2. Entity search (cross-type entity LIKE)
3. Keyword LIKE search (multi-field AND)
4. FTS5 full-text search (fallback)

Intent parsing is pure regex (no LLM): extracts tax_type, entity_keywords, search_keywords from config-driven word lists. Results summarized by DeepSeek LLM. Both streaming (`search_stream()`) and non-streaming (`search()`) interfaces available.

### External Regulation Query (`modules/regulation_api.py`)

Queries Coze RAG API (SSE streaming) for procedural/regulatory knowledge. Both streaming (`query_regulation_stream()`) and non-streaming (`query_regulation()`) interfaces. Handles: UTF-8 encoding fix for SSE, card template JSON filtering, error-in-200-body detection.

### Streaming Output (`run_pipeline_stream()` + SSE / Gradio)

`run_pipeline_stream()` in `mvp_pipeline.py` is a generator that yields event dicts:
- `{'type': 'stage', 'route': str, 'text': str}` — initial stage indicator
- `{'type': 'chunk', 'text': str}` — text fragment (for tax_incentive/regulation routes)
- `{'type': 'done', 'result': dict}` — final result
- Accepts `original_query` param; tax_incentive and regulation routes use it (`raw_query`) instead of the company-prefixed `user_query` to avoid polluting keyword search with company name fragments

**FastAPI SSE** (`api/routes/chat.py`): wraps generator as `text/event-stream` with `event: stage|chunk|done` + JSON `data:` lines. Attaches `display_data` to financial_data results via `build_display_data()`. Passes `original_query` to pipeline for route-aware query isolation.

### Caching (`modules/cache_manager.py`)

Four-level in-memory LRU cache (enabled via `CACHE_ENABLED` in `config/settings.py`):
- Stage 1 intent cache: 500 entries, 30min TTL
- Stage 2 SQL cache: 500 entries, 1hr TTL
- SQL result cache: 200 entries, 30min TTL
- Cross-domain result cache: 100 entries, 30min TTL

### Schema Catalog (`modules/schema_catalog.py`)

Static whitelist of domain→views and view→columns mappings. This is the single source of truth for what the SQL auditor allows. When adding a new domain or view, update this file first.

### Domain System

| Domain | View(s) | Stage 2 Prompt |
|--------|---------|----------------|
| VAT 申报 | `vw_vat_return_general`, `vw_vat_return_small` | `stage2_vat.txt` |
| 企业所得税 | `vw_eit_annual_main`, `vw_eit_quarter_main` | `stage2_eit.txt` |
| 资产负债表 | `vw_balance_sheet_eas` (企业会计准则), `vw_balance_sheet_sas` (小企业会计准则) | `stage2_balance_sheet.txt` |
| 科目余额 | `vw_account_balance` | `stage2_account_balance.txt` |
| 利润表 | `vw_profit_eas` (企业会计准则), `vw_profit_sas` (小企业会计准则) | `stage2_profit.txt` |
| 现金流量表 | `vw_cash_flow_eas` (企业会计准则), `vw_cash_flow_sas` (小企业会计准则) | `stage2_cash_flow.txt` |
| 财务指标 | `vw_financial_metrics` | `stage2_financial_metrics.txt` |
| 发票 | `vw_inv_spec_purchase`, `vw_inv_spec_sales` | `stage2_invoice.txt` |
| 企业画像 | `vw_enterprise_profile` | via `profile_service.py` REST API |
| 跨域 | Multiple views | `stage2_cross_domain.txt` |

### Domain Detection Order

Detection in `entity_preprocessor.py` follows this priority:
1. Financial metrics (distinctive keywords: "财务指标", "毛利率", "ROE", etc.)
2. Cash flow (distinctive keywords, no overlap with other domains)
3. Account balance (temporal: "期初", directional: "借"/"贷"/"发生额")
3. Profit statement (temporal: "本期金额"/"本年累计", or month-based default)
4. Balance sheet (temporal: "年初"/"期初", or item names)
5. EIT (temporal: "年度"/"季度", or keywords)
5a. Invoice (contains "发票" keyword, checked before VAT; "进项发票"→purchase, "销项发票"→sales)
6. VAT (default)
7. Cross-domain upgrade: if primary domain detected but query contains keywords from other domains

### Data Model (SQLite: `database/fintax_ai.db`)

NL2SQL never touches detail tables directly. Views join detail tables with `taxpayer_info` and serve as the only query entry points.

Key tables:
- `vat_return_general` / `vat_return_small` — VAT return data with dimension flattening (4 rows per taxpayer per period)
- `taxpayer_info` — master dimension table (includes `accounting_standard` field: '企业会计准则' or '小企业会计准则'; profile fields: `registered_capital`, `registered_address`, `business_scope`, `operating_status`, `collection_method`)
- `fs_balance_sheet_item` — balance sheet EAV table (纵表), PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`
- `fs_balance_sheet_item_dict` — balance sheet item dictionary (ASBE 67 items, ASSE 53 items)
- `fs_balance_sheet_synonyms` — balance sheet NL phrase → column mapping with gaap_type scope
- `fs_income_statement_item` — profit statement EAV table (纵表), PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`
- `fs_income_statement_item_dict` — profit statement item dictionary (CAS 42 items, SAS 32 items)
- `fs_income_statement_synonyms` — profit statement NL phrase → column mapping with gaap_type scope
- `fs_cash_flow_item` — cash flow statement EAV table (纵表), PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`; `gaap_type` ('CAS'/'SAS'), `current_amount` (本期), `cumulative_amount` (本年累计)
- `fs_cash_flow_item_dict` — cash flow item dictionary (CAS 35 items, SAS 22 items)
- `fs_cash_flow_synonyms` — cash flow NL phrase → column mapping with gaap_type scope
- `vat_synonyms` — NL phrase → column mapping with scope disambiguation
- `eit_synonyms` — EIT NL phrase → column mapping
- `account_synonyms` — account balance NL phrase → account name mapping
- `metric_registry` / `metric_definition` / `metric_synonyms` — cross-domain metric alignment
- `financial_metrics` — pre-computed financial/tax metrics (17 indicators), PK: `(taxpayer_id, period_year, period_month, metric_code)`
- `financial_metrics_item` — v2 pre-computed metrics (25 indicators) with monthly/quarterly/yearly granularity, PK: `(taxpayer_id, period_year, period_month, period_type, metric_code)`; includes `evaluation_level` from dict rules
- `financial_metrics_item_dict` — metric code registry with name, category, unit, evaluation rules (`eval_rules` JSON, `eval_ascending`)
- `financial_metrics_synonyms` — financial metrics NL phrase → column mapping
- `inv_spec_purchase` — 进项发票宽表, PK: `(taxpayer_id, invoice_pk, line_no)`; buyer_tax_id = 我方; 含商品明细字段
- `inv_spec_sales` — 销项发票宽表, PK: `(taxpayer_id, invoice_pk, line_no)`; seller_tax_id = 我方; 无商品明细字段
- `inv_column_mapping` — 发票字段映射（中文→英文）
- `inv_synonyms` — 发票 NL phrase → column mapping with scope_view scope
- `taxpayer_profile_snapshot_month` — monthly profile snapshots (industry, tax authority, region, credit grade, employee/revenue scale), PK: `(taxpayer_id, period_year, period_month)`
- `taxpayer_credit_grade_year` — annual credit grade records, PK: `(taxpayer_id, year)`

Composite PK pattern: `(taxpayer_id, period_year, period_month, item_type, time_range, revision_no)` (VAT); `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)` (balance sheet, profit statement, cash flow)

Revision handling: default query strategy is "latest" via `ROW_NUMBER` window function on `revision_no`.

### Database Initialization

`database/init_db.py` — all DDL (tables, views, indexes)
`database/seed_data.py` — reference/dictionary data
`database/sample_data.py` — sample taxpayer data for testing (calls `sample_data_extended.py` at end)
`database/sample_data_extended.py` — extended sample data covering 2024.01–2026.02 for all domains (VAT, EIT, account balance, balance sheet, profit, cash flow, invoices); uses 2% monthly growth + seasonal sin() wave
`database/seed_fs.py` — financial statement seed data
`database/seed_cf.py` — cash flow statement seed data (item dict + synonyms)
`database/calculate_metrics.py` — financial metrics calculation script v1 (17 indicators from profit/BS/CF/VAT/EIT data)
`database/calculate_metrics_v2.py` — financial metrics calculation script v2 (25 indicators, monthly/quarterly/yearly granularity, writes to `financial_metrics_item` table with evaluation levels)
`database/migrate_profile.py` — migration script adding 5 profile columns to `taxpayer_info` + sample data

## Key Design Decisions

- **Storage-query decoupling**: detail tables split by taxpayer type; views unify with `taxpayer_info`
- **Balance sheet EAV→wide pivot**: `fs_balance_sheet_item` stores data as EAV rows; `vw_balance_sheet_eas`/`vw_balance_sheet_sas` views pivot to wide tables with `{item_code}_begin`/`{item_code}_end` columns via `MAX(CASE WHEN)` aggregation
- **Balance sheet GAAP routing**: `gaap_type` field ('ASBE'/'ASSE') routes to the correct view; inferred from `taxpayer_info.accounting_standard` or `taxpayer_type`
- **Domain disambiguation**: balance_sheet vs account_balance resolved by temporal markers ("年初"→BS, "期初"→AB), directional markers ("借"/"贷"/"发生额"→AB), and default-to-BS for unmodified item names; profit vs EIT resolved by "年度"/"季度"→EIT, "本期金额"/"本年累计金额"→profit, "借"/"贷"→AB, default-to-profit for shared items with month
- **Profit statement EAV storage**: `fs_income_statement_item` stores data as EAV rows (纵表) with `gaap_type` ('CAS'/'SAS'), `item_code`, `current_amount` (本期), and `cumulative_amount` (本年累计); `vw_profit_eas`/`vw_profit_sas` views pivot to wide tables via `MAX(CASE WHEN)` + `CROSS JOIN` with `time_range` dimension ('本期'/'本年累计')
- **Profit statement GAAP routing**: `gaap_type` field ('CAS'/'SAS') routes to `vw_profit_eas` or `vw_profit_sas`; inferred from `taxpayer_info.accounting_standard` or `taxpayer_type` (一般纳税人→CAS, 小规模纳税人→SAS)
- **Cash flow statement EAV storage**: `fs_cash_flow_item` stores data as EAV rows (纵表) with `gaap_type` ('CAS'/'SAS'), `item_code`, `current_amount` (本期), and `cumulative_amount` (本年累计); `vw_cash_flow_eas`/`vw_cash_flow_sas` views pivot to wide tables via `MAX(CASE WHEN)` + `CROSS JOIN` with `time_range` dimension ('本期'/'本年累计')
- **Cash flow GAAP routing**: `gaap_type` field ('CAS'/'SAS') routes to `vw_cash_flow_eas` or `vw_cash_flow_sas`; `accounting_standard` from `taxpayer_info` also filtered in view WHERE clause; inferred from `taxpayer_type` (一般纳税人→CAS, 小规模纳税人→SAS)
- **Cash flow domain detection**: distinctive keywords ("现金流量", "经营活动现金", "投资活动现金", "筹资活动现金", etc.) have no overlap with other domains, making detection straightforward; checked first in the domain detection chain
- **Field names = business terms**: e.g. `output_tax` for 销项税额, `input_tax` for 进项税额, `cash_end` for 货币资金期末余额, `operating_revenue` for 营业收入, `net_profit` for 净利润
- **Three-tier error tolerance**: synonym table → column mapping → LLM semantic fallback
- **Two-stage LLM pipeline**: separates intent understanding from SQL generation for control and auditability
- **Cross-type comparison**: uses `UNION ALL` (not JOIN) with aligned output schema
- **Cross-domain query system**: `cross_domain_calculator.py` supports compare, ratio, reconcile, list operations across domains; splits into sub-queries, executes independently, merges results
- **Computed metrics system**: `metric_calculator.py` provides 8 financial ratios (资产负债率, ROE, 毛利率, etc.) via deterministic SQL + Python formula evaluation, bypassing LLM entirely; extensible via metric registry
- **Materialized financial metrics**: `financial_metrics` table stores 17 pre-computed indicators (盈利能力, 偿债能力, 营运能力, 成长能力, 现金流, 税负率类, 增值税重点指标, 所得税重点指标, 风险预警类) via `calculate_metrics.py`; queryable through `vw_financial_metrics` view as a standard NL2SQL domain; coexists with G3 metric path for real-time computation
- **Financial metrics v2**: `financial_metrics_item` table stores 25 indicators with monthly/quarterly/yearly granularity via `calculate_metrics_v2.py`; `financial_metrics_item_dict` provides metric definitions with evaluation rules; `vw_financial_metrics` view rebuilt to source from `financial_metrics_item`
- **Enterprise profile aggregation**: `profile_service.py` queries across all domains (BS, profit, CF, VAT, EIT, invoices, metrics) to build a comprehensive company profile JSON; threshold-based evaluation for 8 key metrics; exposed via REST API (`/api/profile/{taxpayer_id}`); `taxpayer_info` extended with 5 profile columns via `migrate_profile.py`
- **Relative date resolution**: converts NL temporal expressions ("今年", "去年", "上个月", "上个季度") to absolute dates before pipeline processing; context-aware for VAT "本月"
- **Scope-aware view selection**: `get_scope_view()` routes queries to the correct view based on domain + taxpayer_type + accounting_standard combination
- **Invoice dual-table design**: separate `inv_spec_purchase` (进项) and `inv_spec_sales` (销项) wide tables; purchase table has 8 extra detail columns (goods_name, specification, unit, quantity, unit_price, tax_rate, tax_category_code, special_business_type); `invoice_format` ('数电'/'非数电') + `invoice_pk` (数电票号码 or 发票号码) as logical key; `line_no` supports multi-line items per invoice
- **Invoice domain conflict resolution**: "发票" keyword triggers invoice domain before VAT; "进项发票"→invoice, "进项税"→VAT; direction routing: purchase/sales/both
- **SQL audit retry**: on first audit failure, feeds error message back to SQL Writer for one retry attempt
- **Three-way intent router**: `IntentRouter` classifies queries before domain detection; multi-layer keyword priority (financial data > knowledge base > taxpayer name > tax incentive > default regulation); fuzzy prefix matching for taxpayer names; `ROUTER_ENABLED` master switch for safe rollback
- **Tax incentive four-tier search**: structured → entity → keyword LIKE → FTS5 fallback; LIKE is the main workhorse (FTS5 unicode61 tokenizer has limited Chinese substring matching); config-driven keyword extraction with stopword removal
- **Coze SSE streaming**: `resp.encoding = 'utf-8'` forced before `iter_lines()` (requests defaults to ISO-8859-1 for text/event-stream); card template JSON (`card_type`) filtered from answer accumulation
- **Generator-based streaming**: `run_pipeline_stream()` yields event dicts; text routes stream chunk-by-chunk, financial data route uses existing non-streaming `run_pipeline()`
- **Route-aware query isolation**: `chat.py` prepends company name to query for NL2SQL taxpayer identification, but passes `original_query` (raw user input) via `run_pipeline_stream(original_query=...)` so tax_incentive/regulation routes search without company name pollution (company name fragments in AND-based keyword LIKE search cause zero results)
- **Concept-driven cross-domain**: `concept_registry.py` maps 40+ financial concepts to deterministic SQL; when ≥2 concepts + time granularity detected, bypasses LLM entirely; falls back to LLM cross-domain on failure; supports quarterly aggregation strategies (`sum_months` vs `quarter_end`)
- **FastAPI + React SPA**: `api/` directory provides REST API with SSE streaming (`POST /api/chat`), chat history persistence (`/api/chat/history`), company listing (`/api/companies`), and enterprise profile (`/api/profile/{taxpayer_id}`); serves React build from `frontend/dist/`; coexists with Gradio `app.py`
- **Structured display data**: `display_formatter.py` builds Chart.js-compatible JSON for React frontend; `ColumnMapper` singleton lazy-loads Chinese column names from all synonym tables; intelligent number formatting (亿/万 scaling); domain-specific layouts (KV, table, metric card, cross-domain grouping)
- **Four-tier caching**: intent + SQL + result + cross-domain caches; result cache (200 entries, 30min) and cross-domain cache (100 entries, 30min) added to reduce repeated SQL execution

## Configuration

All config in `config/settings.py`:
- `DB_PATH` — SQLite database path
- `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` — DeepSeek API settings
- `LLM_MAX_RETRIES` / `LLM_TIMEOUT` — LLM call resilience (3 retries, 60s timeout)
- `CACHE_ENABLED` / `CACHE_MAX_SIZE_*` / `CACHE_TTL_*` — four-tier cache tuning (intent, SQL, result, cross-domain)
- `MAX_ROWS` / `MAX_PERIOD_MONTHS` — pipeline safety limits
- `TAX_INCENTIVES_DB_PATH` — tax incentive policy database path
- `COZE_API_URL` / `COZE_PAT_TOKEN` / `COZE_BOT_ID` / `COZE_USER_ID` / `COZE_TIMEOUT` — Coze RAG API settings
- `ROUTER_ENABLED` — intent router master switch (set `False` to bypass routing, revert to original behavior)

## Documentation

Design docs in `docs/` (Chinese):

- `增值税申报表 NL2SQL 数据模型方案文档v1.3--.md` — main VAT design doc with DDL, views, synonyms, pipeline design, system prompts, auditor rules
- `企业所得税申报表数据库设计文档.md` — EIT domain design
- `科目余额表 NL2SQL 数据模型方案文档.md` — account balance domain
- `资产负债表 NL2SQL 数据模型方案文档z.md` — balance sheet domain (ASBE/ASSE dual-GAAP, EAV storage, wide-view pivot, domain disambiguation rules)
- `利润表 NL2SQL 数据模型修改方案文档v2.md` — profit statement domain (ASBE/SAS dual-standard, wide-table storage, time_range disambiguation, profit vs EIT vs account_balance domain routing)
- `现金流量表 NL2SQL 数据模型方案文档z.md` — cash flow statement domain
- `税收优惠政策查询系统 - 技术文档v2.md` — tax incentive query system
- `基于用户提问的智能路由技术文档.md` — intent router design
- `外部 API 知识库查询技术文档.md` — Coze RAG API integration
- `财务数据库查询结果处理与前端展示_技术文档参考v2.2final.md` — display formatter and frontend rendering
- `AI智能咨询前端交互技术文档.md` — React frontend interaction design

