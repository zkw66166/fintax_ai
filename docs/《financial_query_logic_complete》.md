# Financial Data Query System - Complete Logic Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Query Entry Point](#query-entry-point)
4. [Intent Router](#intent-router)
5. [Domain Detection](#domain-detection)
6. [Execution Paths](#execution-paths)
7. [Standard Query Path](#standard-query-path)
8. [Cross-Domain Path](#cross-domain-path)
9. [Concept Registry Path](#concept-registry-path)
10. [Computed Metrics Path](#computed-metrics-path)
11. [Multi-Turn Conversation](#multi-turn-conversation)
12. [Mixed Analysis](#mixed-analysis)
13. [Caching Strategy](#caching-strategy)
14. [Configuration](#configuration)

---

## 1. Introduction

The fintax_ai system is a Chinese tax and financial consulting platform that converts natural language queries into SQL queries against structured financial data.

### Supported Domains

- VAT (增值税)
- EIT (企业所得税)
- Balance Sheet (资产负债表)
- Profit Statement (利润表)
- Cash Flow (现金流量表)
- Account Balance (科目余额)
- Financial Metrics (财务指标)
- Invoice (发票)
- Enterprise Profile (企业画像)

### Key Features

- Multi-turn conversation with entity inheritance
- Cross-route synthesis (financial + tax + regulation)
- Deterministic paths (concept registry + computed metrics)
- Two-level persistent caching (L1 + L2)
- Dual GAAP support (EAS vs SAS)
- Dual taxpayer types (一般纳税人 vs 小规模纳税人)


---

## 2. Architecture Overview

### System Flow

```
User Query (NL)
    ↓
API Entry (/api/chat)
    ↓
Company Name Resolution
    ↓
Intent Router (Layer 0)
    ├─→ financial_data → NL2SQL Pipeline (6 paths)
    ├─→ tax_incentive → Local DB + LLM Summary
    └─→ regulation → Coze RAG API
    ↓
SSE Streaming Response
    ↓
Display Formatting
    ↓
Frontend (React)
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| FastAPI Backend | REST API + SSE | Python 3.9+ |
| SQLite Database | Financial data storage | SQLite 3 |
| DeepSeek LLM | Intent + SQL generation | deepseek-chat (V3) |
| Intent Router | Route classification | Keyword + fuzzy match |
| NL2SQL Pipeline | Query → SQL → Results | Multi-stage LLM |
| Concept Registry | Deterministic cross-domain | 240+ concepts |
| Metric Calculator | Computed ratios | 15+ formulas |
| Conversation Manager | Multi-turn context | Entity inheritance |
| Cache System | L1 + L2 persistent | File-based, LRU |

---

## 3. Query Entry Point

### API Endpoint

**POST /api/chat** - SSE streaming endpoint

### Request Format

```json
{
  "query": "华兴科技2025年1月增值税",
  "company_id": "91110000MA01234567",
  "response_mode": "detailed",
  "thinking_mode": "quick",
  "conversation_history": [],
  "conversation_depth": 3,
  "conversation_enabled": true
}
```

### Response Format (SSE)

Three event types:

1. **stage** - Route indicator
```
event: stage
data: {"route": "financial_data", "text": "正在查询..."}
```

2. **chunk** - Text fragments
```
event: chunk
data: {"text": "根据查询结果..."}
```

3. **done** - Final result
```
event: done
data: {"success": true, "route": "financial_data", "results": [...]}
```

### Company Name Resolution

When `company_id` provided, system resolves company name and prepends to query:

```
Original: "2025年1月增值税"
Company ID: "91110000MA01234567"
Resolved: "华兴科技"
Final query: "华兴科技 2025年1月增值税"
```

### Original Query Preservation

For `tax_incentive` and `regulation` routes, system passes `original_query` (without company prefix) to avoid polluting keyword search.

---

## 4. Intent Router

### Three Primary Routes

1. **financial_data** - Structured financial database queries
2. **tax_incentive** - Tax policy searches (local DB)
3. **regulation** - Procedural knowledge (external RAG)

### Multi-Layer Classification

**Layer -2: Financial Data Priority**
- Trigger: Data keywords + Tax keywords both present
- Keywords: "数据", "查询", "多少" + "增值税", "所得税"

**Layer -1: Knowledge Base Priority**
- Trigger: Procedural keywords
- Keywords: "如何", "怎么", "流程", "步骤", "办理"

**Layer 0: Enterprise Data Query**
- Trigger: Taxpayer name match (exact/fuzzy) + time pattern
- Fuzzy prefix: "华兴" matches "华兴科技" (length ≥ 2)
- Time pattern: `\d{4}年.*多少`

**Layer 1: Tax Incentive**
- Trigger: Incentive keywords (excluding blacklist)
- Keywords: "优惠", "减免", "免税", "退税", "补贴"
- Exclude: "优惠政策申报", "优惠备案流程"

**Default: Regulation**

### Configuration

Hot-reloadable config: `config/tax_query_config.json`

```json
{
  "financial_db_priority_keywords": ["数据", "查询"],
  "incentive_keywords": ["优惠", "减免"],
  "exclude_from_incentive": ["申报", "备案"]
}
```

### Master Switch

```python
# config/settings.py
ROUTER_ENABLED = True  # Set False to bypass routing
```

---

## 5. Domain Detection

### Two-Stage Detection

1. **Heuristic** (entity_preprocessor.py) - Fast keyword-based
2. **LLM Confirmation** (intent_parser.py) - Stage 1 validates

### Priority Order

```
1. Financial Metrics (distinctive keywords)
2. Cash Flow (distinctive keywords)
3. Account Balance (temporal + directional)
4. Profit Statement (temporal or month-based)
5. Balance Sheet (temporal or item names)
6. EIT (temporal keywords)
7. Invoice (explicit "发票")
8. VAT (default for tax)
9. Cross-domain upgrade (multiple domains)
```

### Domain Rules

**Financial Metrics**
- Keywords: "财务指标", "毛利率", "ROE", "资产负债率"

**Cash Flow**
- Keywords: "现金流量表", "经营活动现金流"

**Account Balance**
- High priority: "科目余额", "借方发生额", "贷方发生额"
- Medium priority: "发生额", "借方", "贷方" (need context)
- Account names: "银行存款", "主营业务收入", "坏账准备"

**Profit Statement**
- Temporal: "本期金额", "本年累计"
- Items: "营业收入", "营业成本", "净利润"
- Disambiguation: "年度"/"季度" → EIT, "本期"/"本年" → Profit

**Balance Sheet**
- Temporal: "年初", "期初", "年末", "期末"
- Items: "资产", "负债", "所有者权益"
- Disambiguation: "借"/"贷" → Account Balance

**EIT**
- Temporal: "年度", "季度", "年报", "季报"
- Items: "应纳税所得额", "应纳所得税额"
- Views: annual (`vw_eit_annual_main`) vs quarterly (`vw_eit_quarter_main`)

**Invoice**
- Explicit: "发票" (must be present)
- Direction: "进项"→purchase, "销项"→sales
- Priority: Checked BEFORE VAT

**VAT**
- Keywords: "增值税", "VAT", "销项税", "进项税"
- Default for tax queries

**Cross-Domain Upgrade**
- If primary domain + keywords from other domains → upgrade

### Scope-Aware View Selection

Automatic view selection based on:
- Domain
- Taxpayer Type (一般纳税人 vs 小规模纳税人)
- Accounting Standard (企业会计准则 vs 小企业会计准则)

**Rules:**
- Financial statements: vary by `accounting_standard` only
- VAT: vary by `taxpayer_type` only
- EIT: no distinction, annual vs quarterly only


---

## 6. Execution Paths

### Decision Tree

```
Query arrives at financial_data route
    ↓
Multi-turn enabled? → NO → Continue
    ↓ YES
≥2 different routes in history? → NO → Continue
    ↓ YES
LLM detects synthesis need? → NO → Continue
    ↓ YES
PATH 6: Mixed Analysis (Tier 2)
    ↓
[If not Path 6...]
    ↓
Multi-turn enabled + history ONLY financial_data?
    ↓ YES
PATH 5: Multi-Turn (Tier 1)
    ↓ NO
Detected computed metric?
    ↓ YES
PATH 4: Computed Metrics
    ↓ NO
Detected ≥2 concepts + time granularity?
    ↓ YES
PATH 3: Concept Registry
    ↓ NO
Detected cross-domain operation?
    ↓ YES
PATH 2: Cross-Domain Query
    ↓ NO
PATH 1: Standard Query
```

### Path Priority

1. Path 6: Mixed Analysis (highest, checked first)
2. Path 5: Multi-Turn Conversation
3. Path 4: Computed Metrics (deterministic)
4. Path 3: Concept Registry (deterministic)
5. Path 2: Cross-Domain Query
6. Path 1: Standard Query (default)

### Trigger Conditions

| Path | Trigger | LLM? |
|------|---------|------|
| Path 6 | Multi-turn + ≥2 routes + synthesis | Yes (tax expert) |
| Path 5 | Multi-turn + ONLY financial_data | Yes (Stage 1+2) |
| Path 4 | Metric keyword match | No (deterministic) |
| Path 3 | ≥2 concepts + time + NOT multi-period | No (deterministic) |
| Path 2 | ≥2 domains | Yes (Stage 1+2 per subdomain) |
| Path 1 | Single domain | Yes (Stage 1+2) |

---

## 7. Standard Query Path

### Flow (7 Steps)

```
Step 1: Entity Preprocessing
Step 2: Stage 1 LLM (Intent Parser)
Step 3: Constraint Injection
Step 4: Stage 2 LLM (SQL Writer)
Step 5: SQL Audit
Step 6: SQL Execution
Step 7: Result Formatting
```

### Step 1: Entity Preprocessing

Extract entities and normalize query:
- Relative date resolution
- Taxpayer ID/name extraction
- Period extraction
- Domain detection
- Synonym normalization

### Step 2: Stage 1 LLM

Parse user intent into structured JSON (never writes SQL).

### Step 3: Constraint Injection

Derive security constraints from Stage 1 output.

### Step 4: Stage 2 LLM

Generate read-only SQL query using domain-specific prompts.

### Step 5: SQL Audit

Hard-block dangerous SQL patterns with retry logic.

### Step 6: SQL Execution

Execute query against SQLite with error handling.

### Step 7: Result Formatting

Build display-friendly data structure.

---

## 8. Cross-Domain Path

### Flow

```
Step 1: Concept Pipeline (deterministic)
    ↓ (if fails)
Step 2: LLM Cross-Domain Pipeline
    ├─→ Subdomain splitting
    ├─→ Parallel SQL generation
    ├─→ Result merging
    └─→ Display formatting
```

### Result Merging Strategies

1. **compare** - Side-by-side comparison
2. **ratio** - Division calculation
3. **reconcile** - Consistency check
4. **list** - Union all

### Smart Metric Filtering

When no metrics match subdomain columns, pass user_intent_metrics as hint to LLM.


---

## 9. Concept Registry Path

### Purpose

Deterministic cross-domain queries via pre-registered financial concept mappings. Bypasses LLM entirely for precision.

### 240+ Pre-Defined Concepts

**Concept types**:
- Direct values (agg=None) - Report items, direct SELECT
- Aggregated values (agg=SUM) - Detail items, GROUP BY aggregation
- Computed values (type=computed) - Multi-data-point + Python formula

**Examples**:
```python
'采购金额': {
  'domain': 'invoice',
  'view': 'vw_inv_spec_purchase',
  'column': 'amount',
  'agg': 'SUM',
  'quarterly_strategy': 'sum_months'
}

'存货增加额': {
  'domain': 'balance_sheet',
  'type': 'computed',
  'sources': {
    'end': {'column': 'inventory_end', 'period': 'current'},
    'begin': {'column': 'inventory_end', 'period': 'previous'}
  },
  'formula': 'end - begin',
  'quarterly_strategy': 'quarter_end'
}
```

### Quarterly Strategies

- **sum_months** - Aggregate 3 months (invoices, account balance)
- **quarter_end** - Take quarter-end month (balance sheet, cash flow, profit)

### Alias Resolution

Fuzzy matching of user queries to canonical concept names:
```python
"ROE" → "净资产收益率"
"采购额" → "采购金额"
"销售额" → "销售金额"
```

### Time Granularity Detection

Patterns: monthly, quarterly, yearly
```python
"2025年1月" → monthly
"2025年Q1" → quarterly
"2025年" → yearly
```

### Trigger Conditions

- ≥2 concepts detected
- Time granularity detected
- NOT multi-period query (single point or single range)

### Fallback

If concept pipeline fails (incomplete data, execution error), falls back to LLM-based cross-domain pipeline.

---

## 10. Computed Metrics Path

### Purpose

Deterministic calculation of financial ratios using pre-defined formulas. No LLM needed.

### 15+ Pre-Registered Metrics

Each metric defines:
- **sources**: Cross-domain data requirements
- **formula**: Python expression
- **label**: Display name
- **unit**: Display unit

**Examples**:
```python
'资产负债率': {
  'sources': {
    'total_liabilities': {
      'domain': 'balance_sheet',
      'column': 'liabilities_end'
    },
    'total_assets': {
      'domain': 'balance_sheet',
      'column': 'assets_end'
    }
  },
  'formula': 'total_liabilities / total_assets * 100',
  'label': '资产负债率',
  'unit': '%'
}

'ROE': {
  'sources': {
    'net_profit': {
      'domain': 'profit',
      'column': 'net_profit'
    },
    'equity': {
      'domain': 'balance_sheet',
      'column': 'equity_end'
    }
  },
  'formula': 'net_profit / equity * 100',
  'label': '净资产收益率',
  'unit': '%'
}
```

### Flow

```
Step 1: Early detection (Step 2b in pipeline)
Step 2: Extract source data (cross-domain SQL)
Step 3: Python formula evaluation
Step 4: Result formatting
```

### Accounting Standard-Aware

Automatically selects correct view based on accounting standard:
- EAS (企业会计准则) → `vw_balance_sheet_eas`, `vw_profit_eas`
- SAS (小企业会计准则) → `vw_balance_sheet_sas`, `vw_profit_sas`

### Synonym Mapping

Supports aliases:
```python
"ROE" → "净资产收益率"
"ROA" → "总资产收益率"
"毛利率" → "销售毛利率"
```

---

## 11. Multi-Turn Conversation (Tier 1)

### Purpose

Entity inheritance for seamless financial data queries across multiple turns.

### Trigger

- User enables multi-turn conversation (frontend checkbox)
- History contains ONLY financial_data route

### Behavior

**Entity inheritance**:
- taxpayer_id
- taxpayer_name
- taxpayer_type
- period_year
- period_month
- domain_hint

**Pronoun resolution**:
- "它/那/这个" → previous taxpayer

**Implicit inheritance**:
- Time/company/domain from previous turn

**Special patterns**:
- "N月呢？" → extract month, inherit year

### LLM Integration

- **Stage 1**: Passes last 2 turns (4 messages) as context
- **Stage 2**: Passes previous SQL for pattern consistency

### Example Conversation

```
Turn 1: "华兴科技2025年1月增值税"
  → Route: financial_data
  → Returns: VAT data for Jan 2025

Turn 2: "2月呢"
  → Route: financial_data
  → Inherits: taxpayer_id="华兴科技", period_year=2025
  → Returns: VAT data for Feb 2025

Turn 3: "利润是多少"
  → Route: financial_data
  → Inherits: taxpayer_id, period_year
  → Switches domain to profit
  → Returns: Profit data for Feb 2025
```

### Configuration

```python
# config/settings.py
CONVERSATION_ENABLED = True
CONVERSATION_MAX_TURNS = 3  # Default: 3 turns (6 messages)
CONVERSATION_MIN_TURNS = 2
CONVERSATION_MAX_TURNS_LIMIT = 5
CONVERSATION_TOKEN_BUDGET = 4000
CONVERSATION_BETA_USERS = ["admin", "user1", "sys"]
```

---

## 12. Mixed Analysis (Tier 2)

### Purpose

Comprehensive synthesis when mixing different route types (financial_data + tax_incentive + regulation).

### Trigger Conditions (ALL must be true)

1. User enables multi-turn conversation (frontend checkbox)
2. Conversation history contains ≥2 different route types
3. Current query requires synthesis (LLM auto-detection)

### Synthesis Detection Keywords

"综合", "匹配", "建议", "筹划", "优化", "对比", "结合", "根据上述", "根据前面"

### Behavior

- Extracts ALL historical Q&A from different routes (not just entities)
- Feeds complete context to tax planning expert LLM (NOT to NL2SQL pipeline)
- Generates comprehensive analysis report
- **Does NOT route to original 3 branches** (financial_data/tax_incentive/regulation)

### Output Format

6-section structured report:
1. 📊 Data Overview
2. ✅ Applicable Policies
3. ⚠️ Risk Alerts
4. 💡 Tax Planning Suggestions
5. 📈 Optimization Directions
6. 🎯 Action Plan

### Example Conversation

```
Turn 1: "资产税收优惠有哪些"
  → Route: tax_incentive
  → Returns: Accelerated depreciation, R&D expense deduction policies

Turn 2: "TSE科技2025年末流动资产结构"
  → Route: financial_data
  → Returns: Current asset details

Turn 3: "TSE可以享受哪些税收优惠，请结合上述数据分析"
  → Route: mixed_analysis (auto-triggered)
  → Returns: Comprehensive synthesis report
```

### Prompt Template

`prompts/mixed_analysis_tax_planning.txt` - 20-year tax consultant persona

### Configuration

```python
# config/settings.py
MIXED_ANALYSIS_ENABLED = True
MIXED_ANALYSIS_MIN_ROUTES = 2
MIXED_ANALYSIS_LLM_MODEL = "deepseek-chat"
MIXED_ANALYSIS_MAX_CONTEXT_TOKENS = 8000
MIXED_ANALYSIS_STREAM_CHUNK_SIZE = 50
```

### Safety

If user does NOT enable multi-turn conversation, this route is completely bypassed → original 3-route logic unchanged.


---

## 13. Caching Strategy

### Two-Level Persistent Cache

Both L1 and L2 are file-based, survive server restarts, and are company-aware.

### L1 Cache: Full Query Results

- Cache key: MD5(company_id|normalized_query|response_mode)
- Storage: File-based in cache/ directory
- Max files: 1500 (LRU eviction)
- In-memory index for fast lookups

### L2 Cache: SQL Templates

- Domain-aware cache key (refactored 2026-03-06)
- Financial statements: keyed by accounting_standard only
- VAT: keyed by taxpayer_type only
- EIT: no type/standard distinction
- Max files: 500
- Smart adaptation: swaps _eas ↔ _sas view suffixes

### Three-Mode Cache Interaction

- Quick mode: Returns cached result + cached interpretation
- Think mode: Returns cached result + sets need_reinterpret=True
- Deep mode: Bypasses cache, re-runs full pipeline

---

## 14. Special Query Handling

### Single Period Queries

Example: "华兴科技2025年1月增值税"

### Multi-Period Queries

- Month ranges: "2025年1-3月"
- Year-over-year: "2024年和2025年对比"

### Quarterly Queries

Example: "2025年Q1" → expands to months [1, 2, 3]

### Accounting Standard Selection

Automatic selection based on taxpayer_info:
- 一般纳税人 → 企业会计准则 (EAS)
- 小规模纳税人 → 小企业会计准则 (SAS)

### Relative Date Resolution

- "今年3月" → "2026年3月"
- "去年12月" → "2025年12月"
- "上个月" → previous month

---

## 15. SQL Generation & Audit

### Domain-Specific Stage 2 Prompts

9 prompts in prompts/ directory for each domain.

### SQL Audit Rules

Hard-blocks:
- Non-SELECT statements
- Multi-statement queries
- Disallowed views/columns
- Missing taxpayer_id filter
- Missing period filter
- No LIMIT clause
- SELECT *
- Dangerous functions

Domain-specific checks:
- EIT: period_quarter filter for quarter views
- Monthly domains: period_month filter required
- Profit/Cash Flow: time_range validation

### Retry Logic

- On audit failure: retry once with feedback
- On execution failure: retry once with error message

---

## 16. Display Formatting

### Column Name Mapping

300+ static mappings with fallback chain.

### Number Formatting

Intelligent scaling:
- ≥1亿 → "X.XX亿"
- ≥1万 → "X.XX万"

### Domain-Specific Display

- KV lists: Single-row results
- Markdown tables: Multi-row results
- Metric cards: Financial ratios
- Cross-domain grouping: Grouped by source domain

### Chart Data Generation

Chart.js-compatible data structures:
- Bar charts: Multi-period comparisons
- Line charts: Trend analysis
- Pie charts: Composition analysis


---

## 17. Configuration Reference

### LLM Settings

```python
LLM_API_KEY = "sk-..."
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 60
```

### Pipeline Settings

```python
MAX_ROWS = 1000
MAX_PERIOD_MONTHS = 36
```

### Cache Settings

```python
QUERY_CACHE_ENABLED = True
QUERY_CACHE_DIR = PROJECT_ROOT / "cache"
QUERY_CACHE_MAX_FILES_L1 = 1500
QUERY_CACHE_ENABLED_L2 = True
QUERY_CACHE_MAX_FILES_L2 = 500
TAXPAYER_TYPE_SMART_ADAPT = True
```

### Router Settings

```python
ROUTER_ENABLED = True
```

### Conversation Settings

```python
CONVERSATION_ENABLED = True
CONVERSATION_MAX_TURNS = 3
CONVERSATION_MIN_TURNS = 2
CONVERSATION_MAX_TURNS_LIMIT = 5
CONVERSATION_TOKEN_BUDGET = 4000
CONVERSATION_BETA_USERS = ["admin", "user1", "sys"]
```

### Mixed Analysis Settings

```python
MIXED_ANALYSIS_ENABLED = True
MIXED_ANALYSIS_MIN_ROUTES = 2
MIXED_ANALYSIS_LLM_MODEL = "deepseek-chat"
MIXED_ANALYSIS_MAX_CONTEXT_TOKENS = 8000
MIXED_ANALYSIS_STREAM_CHUNK_SIZE = 50
```

---

## 18. Key Files Reference

| Module | Purpose |
|--------|---------|
| api/routes/chat.py | API entry point, caching orchestration |
| mvp_pipeline.py | Main pipeline orchestration, path selection |
| modules/intent_router.py | Intent routing logic |
| modules/entity_preprocessor.py | Domain detection, entity extraction |
| modules/intent_parser.py | Stage 1 LLM intent parsing |
| modules/sql_writer.py | Stage 2 LLM SQL generation |
| modules/sql_auditor.py | SQL validation |
| modules/cross_domain_calculator.py | Cross-domain merging |
| modules/concept_registry.py | Concept-based queries |
| modules/metric_calculator.py | Computed metrics |
| modules/conversation_manager.py | Multi-turn conversation |
| modules/mixed_analysis_detector.py | Mixed analysis detection |
| modules/mixed_analysis_executor.py | Mixed analysis execution |
| api/services/query_cache.py | L1 persistent cache |
| api/services/template_cache.py | L2 template cache |
| modules/display_formatter.py | Result formatting |
| config/settings.py | All configuration |

---

## 19. Flow Diagrams

### Overall System Flow

```
User Query
    ↓
API Entry (/api/chat)
    ↓
Company Name Resolution
    ↓
Intent Router
    ├─→ financial_data
    │   ├─→ Path 6: Mixed Analysis
    │   ├─→ Path 5: Multi-Turn
    │   ├─→ Path 4: Computed Metrics
    │   ├─→ Path 3: Concept Registry
    │   ├─→ Path 2: Cross-Domain
    │   └─→ Path 1: Standard
    ├─→ tax_incentive
    │   └─→ Local DB + LLM Summary
    └─→ regulation
        └─→ Coze RAG API
    ↓
SSE Streaming Response
    ↓
Display Formatting
    ↓
Frontend
```

### Path Selection Decision Tree

```
Query at financial_data route
    ↓
Multi-turn + ≥2 routes + synthesis? → YES → Path 6
    ↓ NO
Multi-turn + ONLY financial_data? → YES → Path 5
    ↓ NO
Computed metric detected? → YES → Path 4
    ↓ NO
≥2 concepts + time? → YES → Path 3
    ↓ NO
Cross-domain detected? → YES → Path 2
    ↓ NO
Path 1 (Standard)
```

### Domain Detection Priority

```
1. Financial Metrics (distinctive keywords)
2. Cash Flow (distinctive keywords)
3. Account Balance (temporal + directional)
4. Profit Statement (temporal or month-based)
5. Balance Sheet (temporal or item names)
6. EIT (temporal keywords)
7. Invoice (explicit "发票")
8. VAT (default for tax)
9. Cross-domain upgrade (multiple domains)
```

---

## 20. Examples by Query Type

| Query | Domain(s) | Path | Key Characteristics |
|-------|-----------|------|---------------------|
| "华兴科技2025年1月增值税" | VAT | Path 1 | Single domain, single period |
| "华兴科技2025年1-3月增值税" | VAT | Path 1 | Single domain, multi-period |
| "华兴科技2025年Q1增值税" | VAT | Path 1 | Quarterly expansion |
| "华兴科技2025年资产负债率" | Financial Metrics | Path 4 | Computed metric (deterministic) |
| "华兴科技2025年1月采购金额和销售金额" | Invoice | Path 3 | Concept registry (deterministic) |
| "华兴科技2025年1月增值税和利润对比" | VAT + Profit | Path 2 | Cross-domain (LLM) |
| "华兴科技2025年1月增值税" → "2月呢" | VAT | Path 5 | Multi-turn (entity inheritance) |
| "资产税收优惠" → "TSE科技资产" → "综合分析" | Mixed | Path 6 | Cross-route synthesis |
| "资产税收优惠有哪些" | N/A | tax_incentive | Local DB search |
| "如何办理增值税申报" | N/A | regulation | External RAG API |

---

## Appendix: Glossary

- **EAS**: Enterprise Accounting Standards (企业会计准则)
- **SAS**: Small Enterprise Accounting Standards (小企业会计准则)
- **VAT**: Value-Added Tax (增值税)
- **EIT**: Enterprise Income Tax (企业所得税)
- **NL2SQL**: Natural Language to SQL
- **SSE**: Server-Sent Events
- **LRU**: Least Recently Used
- **RAG**: Retrieval-Augmented Generation
- **LLM**: Large Language Model

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-07  
**Author**: Claude Code (Opus 4.6)

