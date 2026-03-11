# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

fintax_ai is a Chinese tax and financial consulting platform (税务智能咨询系统) that uses a two-stage NL2SQL pipeline to answer natural language queries against structured tax return and financial data stored in SQLite.

**Current status**: MVP complete with VAT, EIT, balance sheet, account balance, profit statement (利润表), cash flow statement (现金流量表), invoice (发票, 进项/销项), cross-domain queries (跨域), computed financial metrics (财务指标), and enterprise profile (企业画像) domains. Additionally supports tax incentive policy queries (税收优惠政策, via local `tax_incentives.db`) and external regulation knowledge base queries (法规知识库, via Coze RAG API). Includes JWT-based user auth with 5-role hierarchy and company-scoped data access, data browser (general + raw format modes), and data quality check service. Frontend: FastAPI + React SPA with SSE streaming, 5-page layout (工作台, AI智问, 企业画像, 数据管理, 系统设置). Dashboard (工作台) is the default landing page with 6 role-adaptive widgets. LLM backend is DeepSeek (`deepseek-chat`) via OpenAI-compatible API.

**Sample data**: 6 taxpayers total — 2 original (华兴科技/一般纳税人, 鑫源贸易/小规模纳税人) + 4 additional (创智软件/一般纳税人, 大华智能制造/小规模纳税人, TSE科技/一般纳税人, 环球机械/小规模纳税人). Original 2 cover 2024.01–2026.02; additional 4 cover 2023.01–2025.12 across all domains.


## Architecture

### NL2SQL Pipeline (`mvp_pipeline.py`)

All stages orchestrated in `run_pipeline()`, with three execution paths preceded by an intent router:

**Intent Router** (`modules/intent_router.py`, enabled via `ROUTER_ENABLED` in settings):
- Runs before all domain detection; classifies queries into four routes:
  - `financial_data` → existing NL2SQL pipeline (9 domains)
  - `tax_incentive` → local tax incentive DB search + LLM summary
  - `regulation` → external Coze RAG API
  - `mixed_analysis` → cross-route multi-turn synthesis (NEW, see below)
- Multi-layer keyword classification (Layer -2 through Layer 1 + default), with fuzzy taxpayer name matching
- Hot-reloadable config from `config/tax_query_config.json`

**Multi-Turn Conversation System** (two-tier architecture):

**Tier 1: Financial Data Multi-Turn** (`modules/conversation_manager.py`, `modules/entity_preprocessor.py`):
- **Trigger**: User enables multi-turn conversation + history contains ONLY `financial_data` route
- **Behavior**: Passes conversation history to NL2SQL pipeline for entity inheritance
  - Inherits: `taxpayer_id`, `taxpayer_name`, `taxpayer_type`, `period_year`, `period_month`, `domain_hint`
  - Pronoun resolution: "它/那/这个" → previous taxpayer
  - Implicit inheritance: time/company/domain from previous turn
  - Special handling: "N月呢？" pattern (extract month, inherit year)
- **LLM integration**:
  - Stage 1 (Intent Parser): passes last 2 turns (4 messages) as context
  - Stage 2 (SQL Writer): passes previous SQL as context for pattern consistency
- **Example**:
  ```
  Turn 1: "华兴科技2025年1月增值税"
    → Route: financial_data
  Turn 2: "2月呢"
    → Route: financial_data (inherits taxpayer_id, period_year from Turn 1)
  Turn 3: "3月呢"
    → Route: financial_data (continues entity inheritance)
  ```

**Tier 2: Cross-Route Mixed Analysis** (`modules/mixed_analysis_detector.py`, `modules/mixed_analysis_executor.py`):
- **Trigger conditions** (highest priority, checked BEFORE Tier 1):
  1. User enables multi-turn conversation in frontend (conversation_depth ≥ 2)
  2. Conversation history contains ≥2 different route types (e.g., tax_incentive + financial_data)
  3. Current query requires synthesis (LLM auto-detection via keywords: "综合", "匹配", "建议", "筹划", "优化", etc.)
- **Behavior**:
  - Extracts ALL historical Q&A from different routes (not just entities)
  - Feeds complete context to tax planning expert LLM (NOT to NL2SQL pipeline)
  - Generates comprehensive analysis report with risk assessment, tax planning, financial optimization
  - **Does NOT route to original 3 branches** (financial_data/tax_incentive/regulation)
- **Output format**: 6-section structured report (📊 Data Overview, ✅ Applicable Policies, ⚠️ Risk Alerts, 💡 Tax Planning Suggestions, 📈 Optimization Directions, 🎯 Action Plan)
- **Safety**: If user does NOT enable multi-turn conversation, this route is completely bypassed → original 3-route logic unchanged
- **Prompt template**: `prompts/mixed_analysis_tax_planning.txt` (20-year tax consultant persona)
- **Example**:
  ```
  Turn 1: "资产税收优惠有哪些"
    → Route: tax_incentive
  Turn 2: "TSE科技2025年末流动资产结构"
    → Route: financial_data
  Turn 3: "TSE可以享受哪些税收优惠，请结合上述数据分析"
    → Route: mixed_analysis (auto-triggered, bypasses all 3 original routes)
    → LLM receives: Turn 1 policies + Turn 2 data → generates synthesis report
  ```

**Routing Decision Flow**:
```
User query arrives
  ↓
Is multi-turn enabled? → NO → Route to original 3 branches (financial_data/tax_incentive/regulation)
  ↓ YES
Check conversation history routes
  ↓
≥2 different routes? → NO → Tier 1: Financial Data Multi-Turn (entity inheritance)
  ↓ YES
LLM detects synthesis need? → NO → Tier 1: Financial Data Multi-Turn
  ↓ YES
Tier 2: Cross-Route Mixed Analysis (comprehensive synthesis, bypasses original 3 routes)
```

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
- Each metric defines `sources` (cross-domain data requirements), `formula` (Python expression), `label`, `unit`
- Deterministic SQL construction → Python formula evaluation → no LLM needed
- Synonym mapping supports aliases (e.g. "ROE" → "净资产收益率")

### Concept Registry (`modules/concept_registry.py`)

Deterministic cross-domain query engine via pre-registered financial concept mappings:
- **326 concepts** loaded from JSON config files (`config/concepts/*.json`), with hardcoded fallback
- **Concept externalization** (2026-03-10): migrated from code to JSON for hot-reload and non-technical editing
- **Concept segmentation strategy** (mixed approach):
  - **Financial statements** (balance_sheet, profit, cash_flow): split by accounting standard (EAS/SAS) — 20% column structure difference
  - **VAT**: split by taxpayer type (一般纳税人/小规模纳税人) — completely different structures
  - **EIT**: NOT split (annual/quarterly is time dimension, handled by `period_quarter` in entities)
  - **Invoice**: NOT split (purchase/sales distinguished by concept name, same column structure)
  - **Financial metrics**: NOT split (unified calculation logic)
- **Segmentation principle**: split by **structure dimension** (different columns), NOT by **time dimension** (different periods)
- Concept types: direct values, aggregated values, computed values (e.g. 存货增加额 = end - begin)
- Quarterly strategies: `sum_months` (aggregate 3 months) vs `quarter_end` (take quarter-end month)
- Alias resolution with fuzzy matching; multi-variant mapping (e.g. "货币资金" → ["货币资金", "货币资金_SAS"])
- Filtering by `accounting_standard` and `taxpayer_type` from entities during concept matching
- Time granularity detection: monthly/quarterly/yearly patterns from query text
- When ≥2 concepts detected + time granularity → deterministic SQL construction, bypasses LLM entirely
- Falls back to LLM-based cross-domain pipeline on failure
- Hot-reload function: `reload_concepts()` reloads from JSON without server restart

### Dashboard (工作台) (`frontend/src/components/Dashboard/`)

Role-adaptive landing page with 6 core widgets (Phase 1 MVP):
- **Widget 1: Health Scorecard** — comprehensive health score (0-100) based on 4 key metrics (资产负债率, ROE, 毛利率, 营收增长率); color-coded evaluation levels; click to navigate to profile page
- **Widget 3: Tax Burden Summary** — VAT, EIT, total tax, tax burden rate from profile API
- **Widget 4: Data Quality Alert** — overall pass rate, 5-category breakdown (internal_consistency, reasonableness, cross_table, period_continuity, completeness), top 3 issues, manual check trigger
- **Widget 7: Recent Queries** — last 5 AI queries with route badges, click to re-run
- **Widget 9: Quick Query Shortcuts** — 6 pre-configured query buttons (本月增值税, 本年净利润, 资产负债率, 现金流, 发票统计, 税收优惠); click navigates to AI智问 with pre-filled query
- **Widget 11: Client Portfolio** (firm/group/admin only) — table view of all accessible companies with health scores and quick actions


**Backend API**:
- `GET /api/dashboard/summary?company_id={id}` — aggregates health score, top 3 metrics, recent activity (from `user_query_log`)
- `DashboardService` in `api/services/dashboard_service.py` — business logic for health score calculation, metric selection, activity aggregation

### FastAPI Backend (`api/`)

REST API layer with JWT auth, 9 route modules:
- `api/main.py` — FastAPI entry point with CORS, static file serving for React SPA; registers 9 routers (auth, users, chat, history, company, profile, data_management, data_browser, dashboard)
- `api/auth.py` — JWT utilities: `create_access_token()`, `get_current_user()` (dependency), `require_company_access(user, company_id)` (per-request company-level authorization)
- `api/routes/auth.py` — `POST /api/auth/login` (returns JWT + user info + company_ids), `POST /api/auth/logout`, `GET /api/auth/me`
- `api/routes/users.py` — user CRUD: `GET/POST /api/users`, `PUT/DELETE /api/users/{id}`, `GET/PUT /api/users/{id}/companies`; role-based creation rules via `CREATABLE_ROLES`
- `api/routes/chat.py` — `POST /api/chat` SSE streaming endpoint wrapping `run_pipeline_stream()`; passes `original_query` (without company name prefix) so tax_incentive/regulation routes search on the raw user input
- `api/routes/history.py` — `GET/POST/DELETE /api/chat/history` JSON file-based chat history (max 100 entries); `POST /api/chat/history/reinvoke` re-invocation endpoint with quick/think/deep mode support; enhanced schema with `conversation_history`, `result`, `thinking_mode`, `response_mode` fields for persistent re-invocation
- `api/routes/company.py` — `GET /api/companies` taxpayer list for UI dropdown (filtered by user's company access)
- `api/routes/profile.py` — `GET /api/profile/{taxpayer_id}?year=2025` enterprise profile aggregation endpoint
- `api/routes/data_browser.py` — `GET /api/data-browser/tables|periods|data` data browsing with `general` (flat view) and `raw` (domain-specific structured format) modes; 10 browsable domains; 300+ column→Chinese name mappings
- `api/routes/data_management.py` — `GET /api/data-management/stats|companies-overview`, `POST /api/data-management/quality-check` data management and quality check endpoints
- `api/routes/dashboard.py` — `GET /api/dashboard/summary?company_id={id}` dashboard aggregation endpoint (health score, top metrics, recent activity)
- `api/schemas.py` — Pydantic models (`ChatRequest`, `LoginRequest`, `UserCreate`, `UserUpdate`, `HistoryDeleteRequest`, `CompanyItem`)
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

### User Authentication & Permissions (`api/auth.py`, `api/routes/auth.py`, `api/routes/users.py`)

JWT-based auth with 5-role hierarchy and company-scoped data access:
- **Roles** (descending privilege): `sys` (超级管理员) > `admin` (系统管理员) > `firm` (事务所用户) / `group` (集团企业用户) > `enterprise` (普通企业用户)
- **JWT**: HS256, 24h expiry, stored in `localStorage`; `bcrypt` password hashing
- **Company-scoped access**: `user_company_access` table maps `user_id → taxpayer_id`; `sys`/`admin` bypass and see all companies
- **Role-based creation**: `CREATABLE_ROLES` dict enforces who can create which roles (e.g. `firm` can only create `firm`/`enterprise`)
- **Default company assignment**: `ROLE_DEFAULT_COMPANIES` maps roles to default taxpayer IDs; auto-assigned on user creation
- **Seed users** (auto-created on fresh DB init): `sys/sys123`, `admin/admin123`, `user1/123456` (firm), `user2/123456` (group), `user3/123456` (group), `user4/123456` (enterprise), `sws2/123456` (firm)
- **Captcha verification**: Login page has a captcha modal that validates against user1's password via `POST /api/auth/captcha/verify`; captcha automatically syncs when user1's password changes; backend uses bcrypt comparison without exposing password hash; max 3 attempts per session

### Data Browser (`api/routes/data_browser.py`)

Interactive data browsing API with dual view modes:
- **10 browsable domains**: profit, balance_sheet, cash_flow, vat, eit_annual, eit_quarter, account_balance, purchase_invoice, sales_invoice, financial_metrics
- **General mode**: flat wide-table rows via views (up to 500 rows), with column metadata (`key`, `label`, `align`, `col_type`)
- **Raw mode**: domain-specific structured format mimicking official tax return layout; handlers for 6 domains: EAV (profit/cash_flow), balance sheet (dual-column assets/liabilities), VAT (pivoted per-field rows), EIT annual/quarter
- **Column metadata**: 300+ static Chinese name mappings (`_COLUMN_CHINESE_NAMES`); fallback to `nl2sql_semantic_mapping` then domain-specific mapping tables
- **Auth enforcement**: all endpoints require `get_current_user` + `require_company_access`

### Data Quality Service (`api/services/data_quality.py`)

`DataQualityChecker` with 5 check categories:
1. **internal_consistency** — BS equation (assets = liabilities + equity), income statement operating profit formula, cash flow subtotals, VAT tax calculation, EIT formula checks, invoice amount checks
2. **reasonableness** — threshold-based sanity checks
3. **cross_table** — cross-domain consistency (e.g. profit net income vs BS retained earnings change)
4. **period_continuity** — checks for gaps in monthly data sequences
5. **completeness** — checks for missing required fields
- Supports dual GAAP (ASBE/ASSE for BS, CAS/SAS for income statement and cash flow) and dual taxpayer types
- Immutable `CheckResult` and `DomainCheckResult` dataclasses
- Rule ID prefix → domain mapping: `SB`=account_balance, `BS`=balance_sheet, `IS`=income_statement, `CF`=cash_flow, `VAT`=vat_return, `EIT`=eit_return, `INV`=invoice, `REAS`=reasonableness, `CROSS`=cross_table, `CONT`=period_continuity

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

### Caching (`api/services/query_cache.py`, `api/services/template_cache.py`)

Two-level persistent cache system (company-aware, survives server restarts):

**L1 Cache (Full Query Result)**:
- Stores complete pipeline results including `display_data` and `interpretation`
- Cache key: MD5 hash of `company_id|normalized_query|response_mode`
- File-based storage in `cache/` directory
- LRU eviction: max 1500 files, oldest deleted when exceeded
- In-memory index for fast lookups (rebuilt on startup)

**L2 Cache (SQL Template)**:
- Stores SQL templates with placeholders for `taxpayer_id`
- **Supports both single-domain and cross-domain queries** (2026-03-08):
  - Single-domain: stores one SQL template per cache entry
  - Cross-domain: stores multiple sub-domain SQL templates per cache entry
- **Domain-aware cache key** (2026-03-06 refactored, 2026-03-08 smart adaptation removed):
  - Financial statements (balance_sheet, profit, cash_flow, account_balance): `MD5(query|mode|fs|accounting_standard)` — keyed by accounting_standard only, taxpayer_type irrelevant
  - VAT: `MD5(query|mode|vat|taxpayer_type)` — keyed by taxpayer_type only
  - EIT: `MD5(query|mode|eit)` — no type/standard distinction
  - Cross-domain: uses same domain-aware strategy as single-domain
  - Unknown: `MD5(query|mode|taxpayer_type|accounting_standard)` — backward compatible fallback
- **Exact match strategy** (2026-03-08): Each query generates multiple templates based on domain:
  - Financial statements: 2 templates per query (企业会计准则, 小企业会计准则)
  - VAT: 2 templates per query (一般纳税人, 小规模纳税人)
  - EIT: 1 template per query (no type/standard distinction)
  - Cross-domain: up to 4 templates per query (2 types × 2 standards), each containing multiple sub-domain SQL templates
- **Cross-domain template structure** (2026-03-08):
  - `cache_domain`: "cross_domain"
  - `sub_templates`: array of `{'domain': str, 'sql_template': str}`
  - `subdomains`: array of domain names
  - `cross_domain_operation`: 'compare'|'ratio'|'reconcile'|'list'
  - On cache hit: instantiates all sub-domain SQLs, executes them, merges results using `merge_cross_domain_results()`
- **Smart adaptation removed** (2026-03-08): Previously attempted to adapt templates across accounting standards/taxpayer types, but removed due to 20% column structure differences between standards and complete structural differences in VAT views
- Enables cross-company reuse for same query type + accounting standard/taxpayer type combination
- Max 500 files

**Note**: In-memory pipeline cache (Stage 1 intent, Stage 2 SQL, result, cross-domain) has been removed due to cross-company cache pollution issues. The system now relies solely on L1/L2 persistent cache, which is company-aware and provides better cross-session benefits. All taxpayer_type values use Chinese ("一般纳税人", "小规模纳税人") for consistency with database and pipeline code.

**Three-mode cache interaction** (via `api/routes/chat.py`):
- **Quick mode** (`thinking_mode="quick"`): returns cached result + cached interpretation instantly (no LLM call)
- **Think mode** (`thinking_mode="think"`): returns cached result + sets `need_reinterpret=True` (frontend triggers fresh LLM interpretation via `/api/interpret`)
- **Deep mode** (`thinking_mode="deep"`): bypasses persistent cache, re-runs full pipeline

### Persistent Query Cache (`api/services/query_cache.py`)

File-based persistent cache that survives server restarts and page refreshes:
- Stores complete pipeline results (including `display_data` and `interpretation`) as JSON files in `cache/` directory (L1 cache)
- Cache key: MD5 hash of `company_id|normalized_query|response_mode`
- LRU eviction: max 1500 files (`QUERY_CACHE_MAX_FILES_L1`), oldest deleted when exceeded
- In-memory index for fast lookups (rebuilt on startup from disk)
- `get_cached_query()` — lookup by company_id + query + response_mode; updates access metadata on hit
- `save_query_cache()` — save pipeline result + route + interpretation text
- `update_cache_interpretation()` — write interpretation text back into existing cache entry
- `invalidate_by_company(company_id, period_year?, period_month?)` — delete cache entries by company with optional period filter
- `delete_query_caches(cache_keys)` — batch delete by cache key (used by history deletion cascade)

**Three-mode cache interaction** (via `api/routes/chat.py`):
- **Quick mode** (`thinking_mode="quick"`): returns cached result + cached interpretation instantly (no LLM call)
- **Think mode** (`thinking_mode="think"`): returns cached result + sets `need_reinterpret=True` (frontend triggers fresh LLM interpretation via `/api/interpret`)
- **Deep mode** (`thinking_mode="deep"`): bypasses persistent cache, re-runs full pipeline

### History Re-Invocation (`api/routes/history.py`)

Endpoint `POST /api/chat/history/reinvoke` enables re-running historical queries after page refresh or re-login:
- Request: `{ "history_index": int, "thinking_mode": "quick|think|deep" }`
- Enhanced history entries store: `result` (full pipeline output), `conversation_history` (multi-turn context), `company_id`, `response_mode`, `thinking_mode`, `conversation_enabled`, `conversation_depth`
- Quick mode: instant return from persistent cache (no LLM call)
- Think mode: cached result + fresh LLM interpretation
- Deep mode: full pipeline re-execution with restored conversation context
- Returns SSE stream in same format as `/api/chat`
- JWT auth + company access check enforced
- Frontend: HistoryPanel shows "↻" re-invoke button on hover; ChatArea handles SSE response via `handleReinvokeInternal`
- Backward compatible: old history entries without new fields receive defaults

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


Composite PK pattern: `(taxpayer_id, period_year, period_month, item_type, time_range, revision_no)` (VAT); `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)` (balance sheet, profit statement, cash flow)

Revision handling: default query strategy is "latest" via `ROW_NUMBER` window function on `revision_no`.

## Configuration

All config in `config/settings.py`:
- `DB_PATH` — SQLite database path
- `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` — DeepSeek API settings
- `LLM_MAX_RETRIES` / `LLM_TIMEOUT` — LLM call resilience (3 retries, 60s timeout)
- `CACHE_ENABLED` — **DEPRECATED** (set to `False`); in-memory cache removed due to cross-company pollution
- `QUERY_CACHE_ENABLED` / `QUERY_CACHE_DIR` / `QUERY_CACHE_MAX_FILES_L1` — L1 persistent cache (default: enabled, `cache/` dir, max 1500 files)
- `QUERY_CACHE_ENABLED_L2` / `QUERY_CACHE_MAX_FILES_L2` — L2 template cache (default: enabled, max 500 files)
- `TAXPAYER_TYPE_SMART_ADAPT` — L2 smart adaptation switch (default: `True`)
- `MAX_ROWS` / `MAX_PERIOD_MONTHS` — pipeline safety limits
- `TAX_INCENTIVES_DB_PATH` — tax incentive policy database path
- `COZE_API_URL` / `COZE_PAT_TOKEN` / `COZE_BOT_ID` / `COZE_USER_ID` / `COZE_TIMEOUT` — Coze RAG API settings
- `ROUTER_ENABLED` — intent router master switch (set `False` to bypass routing, revert to original behavior)
- `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` — JWT auth settings (HS256, 24h default)
- `CONVERSATION_ENABLED` — multi-turn conversation master switch (default: `True`)
- `CONVERSATION_MAX_TURNS` — default conversation depth (default: 3 turns = 6 messages)
- `CONVERSATION_MIN_TURNS` / `CONVERSATION_MAX_TURNS_LIMIT` — min/max turn limits (2-5)
- `CONVERSATION_TOKEN_BUDGET` — reserved tokens for conversation history (default: 4000)
- `CONVERSATION_BETA_USERS` — beta user whitelist for multi-turn feature (list of usernames)
- `MIXED_ANALYSIS_ENABLED` — mixed analysis route master switch (default: `True`)
- `MIXED_ANALYSIS_MIN_ROUTES` — minimum number of different routes to trigger (default: 2)
- `MIXED_ANALYSIS_LLM_MODEL` — LLM model for synthesis (default: `deepseek-chat`)
- `MIXED_ANALYSIS_MAX_CONTEXT_TOKENS` — max tokens for historical context (default: 8000)
- `MIXED_ANALYSIS_STREAM_CHUNK_SIZE` — streaming chunk size (default: 50)

## Documentation

Design docs in `docs/` (Chinese):

## Multi-Turn Conversation (多轮对话)

**Feature added**: 2024 (Tier 1: Financial Data), 2026-03-02 (Tier 2: Cross-Route Mixed Analysis)

The system supports a two-tier multi-turn conversation architecture:

### Tier 1: Financial Data Multi-Turn (财务数据多轮查询)

**Purpose**: Entity inheritance for seamless financial data queries across multiple turns.

**Trigger**: User enables multi-turn conversation + history contains ONLY `financial_data` route.

**Behavior**:
- Passes conversation history to NL2SQL pipeline for entity inheritance
- Inherits: `taxpayer_id`, `taxpayer_name`, `taxpayer_type`, `period_year`, `period_month`, `domain_hint`
- Pronoun resolution: "它/那/这个" → previous taxpayer
- Implicit inheritance: time/company/domain from previous turn
- Special handling: "N月呢？" pattern (extract month, inherit year)

**Example**:
```
Frontend: Enable "Multi-turn Conversation" - "3 turns"

Turn 1: "华兴科技2025年1月增值税"
  → Route: financial_data
  → Returns: VAT data for Jan 2025

Turn 2: "2月呢"
  → Route: financial_data (inherits taxpayer_id="华兴科技", period_year=2025)
  → Returns: VAT data for Feb 2025

Turn 3: "利润是多少"
  → Route: financial_data (inherits taxpayer_id, period_year, switches domain to profit)
  → Returns: Profit data for Feb 2025
```

**Key modules**:
- `modules/conversation_manager.py` — Context preparation, dependency detection
- `modules/entity_preprocessor.py` — Entity inheritance logic

### Tier 2: Cross-Route Mixed Analysis (跨路由混合多轮查询)

**Purpose**: Comprehensive synthesis when mixing different route types (financial_data + tax_incentive + regulation).

**Trigger**: User enables multi-turn conversation + history contains ≥2 different route types + current query requires synthesis.

**Behavior**:
- Extracts ALL historical Q&A from different routes (not just entities)
- Feeds complete context to tax planning expert LLM (NOT to NL2SQL pipeline)
- Generates comprehensive analysis report with risk assessment, tax planning, financial optimization
- **Does NOT route to original 3 branches** (financial_data/tax_incentive/regulation)

**Example**:
```
Frontend: Enable "Multi-turn Conversation" - "3 turns"

Turn 1: "What tax incentives are available for assets?"
  → Route: tax_incentive
  → Returns: Accelerated depreciation, R&D expense deduction policies...

Turn 2: "TSE Tech's current asset structure at end of 2025"
  → Route: financial_data
  → Returns: Current asset details...

Turn 3: "What tax incentives can TSE enjoy? Please analyze based on the above data."
  → Route: mixed_analysis (auto-triggered, bypasses all 3 original routes)
  → Returns: Comprehensive analysis report (matches Turn 1 policies + Turn 2 data)
```

**Output Format**: 6-section structured report:
- 📊 Data Overview
- ✅ Applicable Policies
- ⚠️ Risk Alerts
- 💡 Tax Planning Suggestions
- 📈 Optimization Directions
- 🎯 Action Plan

**Key modules**:
- `modules/mixed_analysis_detector.py` — Detection logic
- `modules/mixed_analysis_executor.py` — Execution engine
- `prompts/mixed_analysis_tax_planning.txt` — Tax planning expert prompt
- Tests: `test_mixed_analysis.py`, `test_mixed_analysis_e2e.py`

### Routing Decision Flow

```
User query arrives
  ↓
Is multi-turn enabled? → NO → Route to original 3 branches (financial_data/tax_incentive/regulation)
  ↓ YES
Check conversation history routes
  ↓
≥2 different routes? → NO → Tier 1: Financial Data Multi-Turn (entity inheritance)
  ↓ YES
LLM detects synthesis need? → NO → Tier 1: Financial Data Multi-Turn
  ↓ YES
Tier 2: Cross-Route Mixed Analysis (comprehensive synthesis, bypasses original 3 routes)
```

### Safety

- **Frontend-controlled**: Only triggers when user enables multi-turn conversation
- **Fully isolated**: Tier 2 is a new 4th route, zero impact on existing 3 routes and Tier 1
- **Auto-fallback**: If detection fails, falls back to original routing logic

