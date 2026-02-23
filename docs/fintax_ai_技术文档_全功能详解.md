# fintax_ai 税务智能咨询系统 — 全功能技术文档

> 文档版本：v1.0 | 生成日期：2026-02-21 | 基于代码分析自动生成

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构总览](#2-系统架构总览)
3. [技术栈](#3-技术栈)
4. [后端架构](#4-后端架构)
   - 4.1 [FastAPI 服务层](#41-fastapi-服务层)
   - 4.2 [NL2SQL 主管线](#42-nl2sql-主管线)
   - 4.3 [意图路由器](#43-意图路由器)
   - 4.4 [实体预处理器](#44-实体预处理器)
   - 4.5 [意图解析器（Stage 1）](#45-意图解析器stage-1)
   - 4.6 [约束注入器](#46-约束注入器)
   - 4.7 [SQL 生成器（Stage 2）](#47-sql-生成器stage-2)
   - 4.8 [SQL 审计器](#48-sql-审计器)
   - 4.9 [跨域计算器](#49-跨域计算器)
   - 4.10 [指标计算器](#410-指标计算器)
   - 4.11 [概念注册表](#411-概念注册表)
   - 4.12 [缓存管理器](#412-缓存管理器)
   - 4.13 [展示格式化器](#413-展示格式化器)
   - 4.14 [企业画像服务](#414-企业画像服务)
   - 4.15 [税收优惠查询](#415-税收优惠查询)
   - 4.16 [法规知识库查询](#416-法规知识库查询)
5. [前端架构](#5-前端架构)
   - 5.1 [组件体系](#51-组件体系)
   - 5.2 [SSE 流式通信](#52-sse-流式通信)
   - 5.3 [聊天界面](#53-聊天界面)
   - 5.4 [企业画像页面](#54-企业画像页面)
   - 5.5 [图表渲染](#55-图表渲染)
   - 5.6 [状态管理](#56-状态管理)
6. [数据库设计](#6-数据库设计)
   - 6.1 [表结构总览](#61-表结构总览)
   - 6.2 [视图设计](#62-视图设计)
   - 6.3 [数据初始化流程](#63-数据初始化流程)
   - 6.4 [财务指标计算](#64-财务指标计算)
7. [域系统设计](#7-域系统设计)
8. [LLM 提示词工程](#8-llm-提示词工程)
9. [配置体系](#9-配置体系)
10. [测试体系](#10-测试体系)
11. [项目文件结构](#11-项目文件结构)

---

## 1. 项目概述

fintax_ai 是一个面向中国税务与财务咨询场景的智能问答平台，核心采用两阶段 NL2SQL 管线，将自然语言查询转换为 SQL 并在 SQLite 数据库上执行，返回结构化的税务申报和财务数据。

### 核心能力

| 能力 | 说明 |
|------|------|
| 9 域 NL2SQL 查询 | 增值税、企业所得税、资产负债表、科目余额、利润表、现金流量表、发票、财务指标、企业画像 |
| 跨域查询 | 支持 compare（对比）、ratio（比率）、reconcile（勾稽）、list（列举）四种操作 |
| 确定性指标计算 | 8 个内置财务比率（资产负债率、ROE 等），绕过 LLM 直接计算 |
| 概念驱动查询 | 40+ 预注册财务概念，≥2 概念 + 时间粒度时绕过 LLM |
| 税收优惠政策查询 | 本地 FTS5 索引库（1522 条政策），四级渐进搜索 |
| 法规知识库查询 | 对接 Coze RAG API，SSE 流式返回 |
| 企业画像 | 11 维度全域聚合，阈值评估 |
| 流式响应 | FastAPI SSE 实时推送 |
| 四级缓存 | 意图 / SQL / 结果 / 跨域，LRU + TTL |

### 系统用户

- 税务顾问、财务人员：通过自然语言查询企业税务和财务数据
- 企业管理者：通过企业画像了解公司全貌

---

## 2. 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        React SPA (Vite)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ ChatArea  │ │ChatInput │ │HistPanel │ │ CompanyProfile    │  │
│  │ ChatMsg   │ │ 3 modes  │ │ search   │ │ 11 sections       │  │
│  │ ResultTbl │ │          │ │ delete   │ │ MiniChart         │  │
│  │ ChartRdr  │ │          │ │          │ │ EvalLabel         │  │
│  │ GrowthTbl │ │          │ │          │ │                   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSE / REST
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend (api/)                       │
│  POST /api/chat (SSE)  GET /api/companies  GET /api/profile     │
│  GET/POST/DELETE /api/chat/history                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    NL2SQL Pipeline (mvp_pipeline.py)             │
│                                                                  │
│  ┌─────────────┐    ┌──────────────────────────────────────┐    │
│  │ IntentRouter │───▶│ financial_data │ tax_incentive │ reg │    │
│  └─────────────┘    └───────┬────────┴───────┬───────┴──┬──┘    │
│                             │                │          │        │
│  ┌──────────────────────────▼──────┐  ┌──────▼───┐ ┌───▼────┐  │
│  │ Entity Preprocessor             │  │ TaxIncent│ │CozeRAG │  │
│  │ → 日期解析 → 域检测 → 同义词    │  │ 4级搜索  │ │SSE流式 │  │
│  └──────────────┬─────────────────┘  └──────────┘ └────────┘  │
│                 │                                               │
│  ┌──────────────▼──────────────────────────────────────────┐    │
│  │ 路径选择                                                 │    │
│  │ ① 指标路径 → MetricCalculator (确定性)                   │    │
│  │ ② 概念路径 → ConceptRegistry (确定性)                    │    │
│  │ ③ 跨域路径 → CrossDomainCalculator (并行 LLM)           │    │
│  │ ④ 标准路径 → Stage1(LLM) → Stage2(LLM) → Audit → Exec  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 四级缓存: Intent(500/30m) SQL(500/1h) Result(200/30m)   │   │
│  │           CrossDomain(100/30m)                            │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    SQLite (fintax_ai.db)                         │
│  9 域 × 多视图 | EAV 纵表 + 宽表视图 | 双准则 GAAP 路由        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术栈

### 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | ≥0.115.0 |
| ASGI 服务器 | Uvicorn | ≥0.30.0 |
| 数据库 | SQLite 3 | 内置 |
| LLM | DeepSeek (deepseek-chat) | OpenAI 兼容 API |
| LLM SDK | openai (Python) | ≥1.0.0 |
| 备用前端 | Gradio | 4.44.1 |

### 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | React | 19.2.0 |
| 构建工具 | Vite | 7.3.1 |
| 图表 | Chart.js + react-chartjs-2 | 4.5.1 / 5.3.1 |
| Markdown 渲染 | react-markdown | 10.1.0 |
| 代码检查 | ESLint | 9.39.1 |

---

## 4. 后端架构

### 4.1 FastAPI 服务层

**入口文件**: `api/main.py`

FastAPI 应用作为主要的 Web 服务层，提供 REST API 和 SSE 流式接口，同时托管 React SPA 静态文件。

#### API 端点

| 方法 | 路径 | 功能 | 模块 |
|------|------|------|------|
| POST | `/api/chat` | SSE 流式聊天 | `api/routes/chat.py` |
| GET | `/api/chat/history` | 获取聊天历史 | `api/routes/history.py` |
| POST | `/api/chat/history` | 保存聊天记录 | `api/routes/history.py` |
| DELETE | `/api/chat/history` | 删除聊天记录 | `api/routes/history.py` |
| GET | `/api/companies` | 获取企业列表 | `api/routes/company.py` |
| GET | `/api/profile/{taxpayer_id}` | 获取企业画像 | `api/routes/profile.py` |

#### 请求/响应模型 (`api/schemas.py`)

```python
class ChatRequest(BaseModel):
    query: str          # 用户问题 (1-500字)
    response_mode: str  # "detailed" | "standard" | "concise"
    company_id: str     # 纳税人识别号

class HistoryDeleteRequest(BaseModel):
    ids: list[int]      # 要删除的记录 ID 列表

class CompanyItem(BaseModel):
    taxpayer_id: str
    taxpayer_name: str
    taxpayer_type: str
```

#### SSE 流式实现 (`api/routes/chat.py`)

聊天端点的核心流程：

1. 接收 `ChatRequest`，如有 `company_id` 则查询纳税人名称
2. 将企业名称拼接到查询前面（用于 NL2SQL 纳税人识别）
3. 同时保留 `original_query`（原始用户输入，供税收优惠/法规路由使用，避免企业名称污染关键词搜索）
4. 调用 `run_pipeline_stream()` 生成器
5. 将管线事件转换为 SSE 格式推送

SSE 事件类型：

| 事件 | 数据格式 | 说明 |
|------|----------|------|
| `stage` | `{"route": str, "text": str}` | 路由指示 + 初始文本 |
| `chunk` | `{"text": str}` | 流式文本片段（税收优惠/法规路由） |
| `done` | `{result + display_data}` | 最终结果（financial_data 路由附加 display_data） |

#### CORS 配置

```python
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

#### 静态文件托管

```python
# 如果 frontend/dist/ 存在，挂载 React SPA
app.mount("/", StaticFiles(directory="frontend/dist", html=True))
```

#### 数据库自动初始化

应用启动时检查数据库文件是否存在，不存在则自动执行三阶段初始化：DDL → 参考数据 → 样本数据。

#### 聊天历史持久化

基于 JSON 文件 (`query_history.json`)，线程安全（`threading.Lock`），最多保存 100 条记录。

### 4.2 NL2SQL 主管线

**文件**: `mvp_pipeline.py`

主管线是整个系统的核心编排器，协调所有模块完成从自然语言到 SQL 执行的全流程。

#### 入口函数

| 函数 | 类型 | 用途 |
|------|------|------|
| `run_pipeline(user_query, db_path, progress_callback)` | 同步 | 返回完整结果 dict |
| `run_pipeline_stream(user_query, db_path, progress_callback, original_query)` | 生成器 | yield 事件 dict（stage/chunk/done） |

#### 执行路径（按优先级）

```
用户查询
  │
  ├─ 意图路由器 (ROUTER_ENABLED=True)
  │   ├─ tax_incentive → TaxIncentiveQuery.search_stream()
  │   ├─ regulation → query_regulation_stream() (Coze API)
  │   └─ financial_data ↓
  │
  ├─ 实体预处理 (detect_entities + normalize_query)
  │
  ├─ 路径 ①: 指标路径 (MetricCalculator)
  │   条件: 查询匹配内置财务比率（资产负债率、ROE 等）
  │   特点: 确定性 SQL + Python 公式，完全绕过 LLM
  │
  ├─ 路径 ②: 概念路径 (ConceptRegistry)
  │   条件: ≥1 个注册概念 + 时间粒度
  │   特点: 确定性 SQL 构建，无 LLM 调用
  │   失败回退: LLM 跨域管线
  │
  ├─ 路径 ③: 跨域路径 (CrossDomainCalculator)
  │   条件: 查询涉及多个域
  │   特点: 拆分子查询 → 并行 LLM SQL 生成 → 串行执行 → 合并
  │
  └─ 路径 ④: 标准路径 (默认)
      Stage 1: 意图解析 (LLM → JSON)
      约束注入 (inject_constraints)
      Stage 2: SQL 生成 (LLM → SQL)
      SQL 审计 (audit_sql)
      SQL 执行 (参数化查询)
```

#### 标准路径详细流程

```
1. detect_entities()        → 提取纳税人、期间、域提示
2. normalize_query()        → 同义词标准化
3. detect_computed_metrics() → 检查是否匹配内置指标
4. resolve_concepts()       → 检查是否匹配注册概念
5. parse_intent()           → Stage 1 LLM 调用 → JSON
6. inject_constraints()     → 推导允许的视图/列/行数
7. generate_sql()           → Stage 2 LLM 调用 → SQL
8. audit_sql()              → 10 条安全规则审计
   └─ 失败 → 反馈错误信息给 SQL Writer 重试一次
9. execute SQL              → 参数化查询 SQLite
   └─ 失败 → 反馈错误信息给 LLM 重试一次
10. _log_query()            → 记录到 user_query_log
```

#### 跨域并行执行

```python
# Phase 1: 并行 LLM SQL 生成 (ThreadPoolExecutor)
with ThreadPoolExecutor(max_workers=len(sub_domains)) as executor:
    futures = {executor.submit(generate_sql, ...): domain for domain in sub_domains}

# Phase 2: 串行 SQL 执行 (SQLite 线程安全)
for domain, sql in sql_results:
    rows = cursor.execute(sql, params).fetchall()
```

#### 参数绑定 (`_build_params`)

支持多种期间模式：
- VAT 月份列表: `:period_months` → `(1, 2, 3)`
- EIT 年度/季度: `:period_year`, `:period_quarter`
- 多年对比: `:period_years` → `(2024, 2025)`
- 月份范围: `:period_month_start`, `:period_month_end`

### 4.3 意图路由器

**文件**: `modules/intent_router.py`

三路意图路由器，在域检测之前对用户查询进行分类，路由到三条处理路径之一。

#### 分类层级（按优先级）

| 层级 | 名称 | 条件 | 路由结果 |
|------|------|------|----------|
| Layer -2 | 财务数据优先 | 数据关键词 + 税种关键词同时命中 | `financial_data` |
| Layer -1 | 知识库优先 | 操作/流程类关键词 | `regulation` |
| Layer 0 | 企业数据查询 | 纳税人名称匹配（精确 + 模糊前缀） | `financial_data` |
| Layer 1 | 税收优惠 | 优惠关键词（排除排除列表） | `tax_incentive` |
| Default | 默认 | 以上均未命中 | `regulation` |

#### 关键词配置 (`config/tax_query_config.json`)

```json
{
  "financial_db_priority_keywords": ["多少", "数据", "金额", "查询", "增长", ...],
  "financial_tax_type_keywords": ["增值税", "所得税", "销项税", "进项税", "利润", ...],
  "knowledge_base_priority_keywords": ["指南", "指引", "操作", "申报流程", "怎么办", ...],
  "incentive_keywords": ["优惠", "减免", "免征", "减征", "抵扣", "退税", ...],
  "exclude_from_incentive": ["进项税额抵扣", "留抵退税", ...]
}
```

#### 热重载机制

配置文件通过 `mtime` 检测变更，无需重启即可生效。

#### 纳税人名称模糊匹配

从 `entity_preprocessor` 缓存纳税人名称列表，支持最长前缀匹配（≥2 字符）。

---

### 4.4 实体预处理器

**文件**: `modules/entity_preprocessor.py`（57KB，系统最大模块）

负责日期解析、实体提取、域检测、同义词标准化四大功能。

#### 4.4.1 相对日期解析 (`_resolve_relative_dates`)

| 输入 | 输出（假设当前 2026-02） |
|------|--------------------------|
| "今年3月" | "2026年3月" |
| "去年12月" | "2025年12月" |
| "上个月" | "2026年1月" |
| "上个季度" | "2025年10月到12月" |
| "最近3个月" | "2025年12月到2026年2月" |
| "去年全年" | "2025年1月到12月" |

上下文感知：VAT 域的"本月"保留不替换。

#### 4.4.2 域检测优先级

```
1. 财务指标 → "财务指标", "毛利率", "ROE" 等独特关键词
2. 现金流量表 → 独特关键词，与其他域无重叠
3. 科目余额 → 时间标记 "期初"，方向标记 "借"/"贷"/"发生额"
4. 利润表 → 时间标记 "本期金额"/"本年累计"，或含月份默认
5. 资产负债表 → 时间标记 "年初"/"期初"，或科目名称
6. 企业所得税 → 时间标记 "年度"/"季度"，或关键词
7. 发票 → 含 "发票" 关键词
8. 增值税 → 默认域
9. 跨域升级 → 主域已检测但查询含其他域关键词
```

#### 4.4.3 域消歧规则

| 冲突场景 | 消歧标记 | 结果 |
|----------|----------|------|
| 资产负债表 vs 科目余额 | "年初" → BS, "期初" → AB, "借"/"贷" → AB | 按标记路由 |
| 利润表 vs 企业所得税 | "年度"/"季度" → EIT, "本期金额" → Profit | 按标记路由 |
| 发票 vs 增值税 | "进项发票" → Invoice, "进项税" → VAT | 按关键词路由 |
| 共享科目（应收账款等） | 方向标记 "借"/"贷"/"发生额" → AB | 无标记默认 Profit |

#### 4.4.4 同义词标准化 (`normalize_query`)

- 最长匹配优先（避免短词截断长词）
- 非重叠替换（occupied 数组跟踪已替换位置）
- 域特定同义词表：`vat_synonyms`, `eit_synonyms`, `account_synonyms`, `fs_balance_sheet_synonyms`, `fs_income_statement_synonyms`, `fs_cash_flow_synonyms`, `inv_synonyms`, `financial_metrics_synonyms`
- 作用域感知：不同视图（eas/sas）使用不同同义词

#### 4.4.5 视图路由 (`get_scope_view`)

| 域 | 一般纳税人 / 企业会计准则 | 小规模纳税人 / 小企业会计准则 |
|----|--------------------------|-------------------------------|
| VAT | `vw_vat_return_general` | `vw_vat_return_small` |
| EIT | `vw_eit_annual_main` / `vw_eit_quarter_main` | 同左 |
| 资产负债表 | `vw_balance_sheet_eas` | `vw_balance_sheet_sas` |
| 利润表 | `vw_profit_eas` | `vw_profit_sas` |
| 现金流量表 | `vw_cash_flow_eas` | `vw_cash_flow_sas` |
| 科目余额 | `vw_account_balance` | 同左 |
| 发票 | `vw_inv_spec_purchase` / `vw_inv_spec_sales` | 同左 |
| 财务指标 | `vw_financial_metrics` | 同左 |

#### 4.4.6 输出结构

```python
{
    'taxpayer_id': str,
    'taxpayer_name': str,
    'taxpayer_type': '一般纳税人' | '小规模纳税人',
    'period_year': int,
    'period_month': int,
    'period_quarter': int,
    'period_years': [int],      # 多年对比
    'period_months': [int],     # 多月查询
    'domain_hint': str,         # 检测到的域
    'cross_domain_list': [str], # 跨域列表
    'resolved_query': str,      # 日期解析后的查询
    'invoice_direction': str,   # 发票方向
    'all_quarters': bool        # "各季度" 模式
}
```

### 4.5 意图解析器（Stage 1）

**文件**: `modules/intent_parser.py`

Stage 1 LLM 调用，将用户查询解析为结构化 JSON 意图。

#### 调用方式

```python
parse_intent(user_query, entities, synonym_hits)
```

- 系统提示词: `prompts/stage1_system.txt`（17KB，含 14 条域判断规则 + 48 条字段映射规则）
- LLM 参数: `response_format={"type": "json_object"}`
- 缓存: 意图缓存（500 条，30 分钟 TTL）

#### 输出 JSON 结构

```json
{
  "domain": "vat|eit|balance_sheet|profit|cash_flow|account_balance|invoice|financial_metrics|cross_domain",
  "select": {"metrics": ["output_tax", "input_tax"], "dimensions": ["period_month"]},
  "filters": {"taxpayer_id": "xxx", "period_mode": "single_month", "period": {"year": 2025, "month": 3}},
  "aggregation": {"group_by": [], "order_by": [], "limit": 1000},
  "vat_scope": {"views": ["vw_vat_return_general"], "item_type": "一般项目", "time_range": "本月数"},
  "need_clarification": false,
  "clarifying_questions": []
}
```

#### 错误处理

- JSON 解析失败 → 回退到 `domain_hint` + `need_clarification=True`
- LLM 超时 → 回退并附带错误信息
- 缺失字段 → 应用域特定默认值

---

### 4.6 约束注入器

**文件**: `modules/constraint_injector.py`

将 Stage 1 意图 JSON 转换为 SQL 审计约束。

#### 输入 → 输出

```
Stage 1 Intent JSON
  ↓
inject_constraints()
  ↓
{
  'allowed_views': ['vw_vat_return_general'],
  'allowed_columns': {'vw_vat_return_general': ['taxpayer_id', 'output_tax', ...]},
  'max_rows': 1000,
  'allowed_views_text': "vw_vat_return_general",
  'allowed_columns_text': "vw_vat_return_general:\n  维度: taxpayer_id, ...\n  指标: output_tax, ...",
  'intent_json_text': "{...}"
}
```

#### 维度列集合（域特定）

- VAT: `taxpayer_id, period_year, period_month, item_type, time_range, taxpayer_type, revision_no`
- EIT: `filing_id, taxpayer_id, period_year, [period_quarter], revision_no`
- 资产负债表: `taxpayer_id, period_year, period_month, revision_no`
- 科目余额: `taxpayer_id, period_year, period_month, account_code, account_name, ...`

#### Schema 目录 (`modules/schema_catalog.py`)

静态白名单，是 SQL 审计器允许访问的唯一真相来源：
- `DOMAIN_VIEWS`: 9 域 → 允许的视图列表
- `VIEW_COLUMNS`: 视图 → 列列表（全部视图共 1000+ 列）
- `DENIED_KEYWORDS`: INSERT, UPDATE, DELETE, DROP 等
- `DENIED_FUNCTIONS`: randomblob, load_extension 等
- `SYSTEM_TABLES`: sqlite_master, sqlite_sequence 等

---

### 4.7 SQL 生成器（Stage 2）

**文件**: `modules/sql_writer.py`

Stage 2 LLM 调用，在约束范围内生成只读 SQLite SQL。

#### 调用方式

```python
generate_sql(constraints, domain, retry_feedback=None)
```

- 域特定提示词: `prompts/stage2_{domain}.txt`
- LLM 参数: `temperature=0.1`（确定性输出）
- 缓存: SQL 缓存（500 条，1 小时 TTL）

#### 提示词模板结构

```
【允许访问的视图】仅：{allowed_views_text}
【允许的列】{allowed_columns_text}
【必备过滤】
  1. taxpayer_id = :taxpayer_id
  2. 期间过滤（按用户问题选择）
【修订版本处理】使用 ROW_NUMBER() OVER (PARTITION BY ... ORDER BY revision_no DESC)
【输出要求】
  - 只输出 SQL，不要解释
  - 严格禁止 SELECT *
  - CTE 中必须明确列出所有维度列 + 需要的指标列
【用户意图 JSON】{intent_json}
```

#### 重试逻辑

审计失败时，将错误信息追加到用户消息中，LLM 根据错误上下文重新生成 SQL，仅重试一次。

---

### 4.8 SQL 审计器

**文件**: `modules/sql_auditor.py`

基于正则的 SQL 安全审计，10 条核心规则硬阻断。

#### 审计规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | 单语句 | 禁止分号（多语句阻断） |
| 2 | 只读 | 必须以 SELECT 或 WITH 开头 |
| 3 | 危险关键词 | 禁止 INSERT, UPDATE, DELETE, CREATE, DROP 等 |
| 4 | 视图白名单 | 只允许 `allowed_views` + CTE 名称 |
| 5 | 禁止 SELECT * | CTE 内部除外 |
| 6 | taxpayer_id 过滤 | 必须包含（多租户隔离） |
| 7 | 期间过滤 | 必须包含 period_year（或 EIT 的 period_quarter） |
| 8 | EIT 季度视图 | 必须包含 period_quarter 过滤 |
| 9 | 月度域 | 必须包含 period_month 过滤 |
| 10 | LIMIT 子句 | 必须存在且 ≤ max_rows |

#### 域特定检查

- EIT: 季度视图必须有 `period_quarter` 过滤
- 月度域（科目余额、资产负债表、利润表、现金流量表、财务指标、发票）: 必须有 `period_month` 过滤
- 利润表/现金流量表: `time_range` 验证
- 支持表别名前缀: `t.period_year * 100 + t.period_month` 模式

#### 返回值

```python
(passed: bool, violations: list[str])
```

调用方决定重试或报错。

### 4.9 跨域计算器

**文件**: `modules/cross_domain_calculator.py`

将跨域查询拆分为子域查询，独立执行后合并结果。

#### 操作类型

| 操作 | 关键词 | 说明 |
|------|--------|------|
| `compare` | "对比", "比较", "对照" | 并排对比 + 差异/差异率 |
| `ratio` | "比率", "占比", "比值" | 除法比率 (A/B × 100%) |
| `reconcile` | "勾稽", "一致", "核对" | 一致性检查 |
| `list` | "列出", "汇总", "所有" | 联合展示 + `_source_domain` 标记 |

#### 合并算法

1. 按期间（年-月 或 年-季度）索引子结果
2. 提取数值列（跳过维度列）
3. 按操作类型计算派生指标（差异、比率、一致性）
4. 对齐输出 Schema

#### 并行执行策略

- LLM SQL 生成: `ThreadPoolExecutor` 并行（无 DB 访问）
- SQL 查询执行: 串行（SQLite 线程安全限制）

---

### 4.10 指标计算器

**文件**: `modules/metric_calculator.py`

确定性财务比率计算，完全绕过 LLM。

#### 8 个内置指标

| 指标 | 公式 | 单位 | 数据来源 |
|------|------|------|----------|
| 资产负债率 | 总负债 / 总资产 × 100 | % | 资产负债表 |
| 净资产收益率 (ROE) | 净利润 / 平均所有者权益 × 100 | % | 利润表 + 资产负债表 |
| 毛利率 | (营业收入 - 营业成本) / 营业收入 × 100 | % | 利润表 |
| 总资产周转率 | 营业收入 / 平均总资产 | 次 | 利润表 + 资产负债表 |
| 净利润率 | 净利润 / 营业收入 × 100 | % | 利润表 |
| 流动比率 | 流动资产 / 流动负债 | 倍 | 资产负债表 |
| 现金债务保障比率 | 经营活动现金流 / 总负债 × 100 | % | 现金流量表 + 资产负债表 |
| 管理费用率 | 管理费用 / 营业收入 × 100 | % | 利润表 |

#### 工作流程

```
用户查询 → detect_computed_metrics() → 同义词匹配
  ↓ (命中)
构建跨域 SQL → 获取源数据 → Python 公式计算 → 返回结果
```

#### 同义词映射

支持别名如 "ROE" → "净资产收益率"，"负债率" → "资产负债率"。

#### 错误处理

- 数据缺失 → 返回 None
- 除零 → 返回 None
- 类型错误 → 返回 None

---

### 4.11 概念注册表

**文件**: `modules/concept_registry.py`（34KB）

预注册财务概念映射，实现确定性跨域查询，绕过 LLM。

#### 40+ 预定义概念

| 类别 | 概念示例 |
|------|----------|
| 发票 | 采购金额, 销售金额, 采购税额, 销售税额, 采购价税合计, 销售价税合计 |
| 增值税 | 销项税额, 进项税额, 增值税应纳税额, 留抵税额 |
| 资产负债表 | 货币资金, 应收账款, 存货, 固定资产, 总资产, 总负债, 所有者权益, 流动资产, 流动负债 |
| 计算型 | 存货增加额 (期末-期初), 应收账款变动额 |
| 利润表 | 营业收入, 营业成本, 营业利润, 利润总额, 净利润, 所得税费用, 税金及附加 |
| 现金流量表 | 经营活动现金流量净额, 投资活动现金流量净额, 筹资活动现金流量净额 |
| 企业所得税 | 应纳税所得额, 应纳所得税额, 实际利润额 |
| 财务指标 | 企业所得税税负率, 增值税税负率, 综合税负率 |

#### 触发条件

≥1 个概念匹配 + 时间粒度检测 → 确定性 SQL 构建

#### 时间粒度检测

| 模式 | 粒度 |
|------|------|
| "各季度", "每季度", "Q1-Q4" | quarterly |
| "各月", "每个月", "1-12月" | monthly |
| "各年", "近三年" | yearly |

#### 季度聚合策略

| 策略 | 适用场景 | 说明 |
|------|----------|------|
| `sum_months` | 发票、VAT 本月数据 | 聚合 3 个月 (Q1 = 1月+2月+3月) |
| `quarter_end` | 资产负债表、现金流量表本期 | 取季末月 (Q1 = 3月) |

#### SQL 构建

- 月度: `GROUP BY period_month` + `SUM` (如 agg=True)
- 季度: `GROUP BY ((period_month-1)/3+1)` 或 `WHERE period_month IN (3,6,9,12)`
- 年度: `WHERE period_month=12`（报表类概念）

#### 失败回退

概念路径失败时自动回退到 LLM 跨域管线。

---

### 4.12 缓存管理器

**文件**: `modules/cache_manager.py`

四级内存 LRU 缓存，线程安全。

#### 缓存层级

| 层级 | 容量 | TTL | 缓存键 |
|------|------|-----|--------|
| 意图缓存 | 500 | 30 分钟 | (normalized_query, taxpayer_type, synonym_hits) |
| SQL 缓存 | 500 | 1 小时 | constraints dict |
| 结果缓存 | 200 | 30 分钟 | (sql, params) |
| 跨域缓存 | 100 | 30 分钟 | (query, taxpayer_id, cross_list, period_key) |

#### 实现细节

- 缓存键: MD5 哈希 JSON 序列化数据（稳定、确定性）
- 线程安全: `threading.Lock` + `OrderedDict` LRU 排序
- 统计: `get_cache_stats()` 返回各级命中率

---

### 4.13 展示格式化器

**文件**: `modules/display_formatter.py`（29KB）

查询结果的展示层，为 React 前端构建结构化 JSON。

#### 核心函数

```python
build_display_data(result) → {
    'summary': str,          # 文本摘要
    'table': str,            # Markdown 表格或 KV 列表
    'chart': dict,           # Chart.js 兼容数据
    'metadata': dict         # 查询元数据
}
```

#### ColumnMapper 单例

懒加载列名 → 中文业务名称映射，从所有同义词表加载。

映射优先级：
1. 精确视图映射 (view, column_name)
2. 域候选视图
3. 通用映射 (COMMON_COLUMN_CN)
4. 跨域前缀拆分 (profit_net_profit → 利润表-净利润)
5. 回退到原始列名

#### 数字格式化

| 条件 | 格式 |
|------|------|
| ≥ 1亿 | "X.XX亿" |
| ≥ 1万 | "X.XX万" |
| 百分比列 (_rate, _ratio) | "X.XX%" |
| 整数列 | 无小数 |
| None | "-" |

#### 展示类型

| 类型 | 条件 | 格式 |
|------|------|------|
| KV 列表 | 单行，≤8 列 | 键值对 |
| 表格 | 多行 | Markdown 表格 |
| 指标卡 | 计算指标 | 指标名 + 值 + 来源 |
| 跨域分组 | 跨域查询 | 按域分组或合并对比 |

#### 图表数据生成

- 多期间数据 → 柱状图
- 1 指标 + ≥3 期间 → 折线图（增长率）
- 柱状 + 折线 → 组合图
- 输出 Chart.js 兼容格式

#### 增长分析

- 环比变化计算
- 趋势分类: 上升/下降/平稳
- 增长率百分比

---

### 4.14 企业画像服务

**文件**: `modules/profile_service.py`（23KB）

全域聚合的企业画像服务。

#### 接口

```python
get_company_profile(taxpayer_id, year) → 11 节 JSON
```

#### 11 个画像维度

| 维度 | 数据来源 | 内容 |
|------|----------|------|
| basic_info | taxpayer_info | 基本信息（注册资本、地址、经营范围、状态、征收方式） |
| asset_structure | 资产负债表 | 资产/负债构成 + 资产负债率 |
| profit_data | 利润表 | 收入、成本、净利润、毛利率、净利率 |
| cash_flow | 现金流量表 | 经营/投资/筹资活动现金流 |
| growth_metrics | 多域对比 | 收入增长率、净利润增长率、资产增长率 |
| financial_metrics | financial_metrics_item | 预计算财务比率 |
| tax_summary | VAT + EIT | 增值税 + 所得税税负 |
| invoice_summary | 发票表 | 进项/销项发票统计 |
| rd_innovation | 利润表 | 研发费用 + 研发强度 |
| cross_border | EIT | 境外收入 + 税收抵免 |
| compliance_risk | 多域 | 风险指标 + 流动性评估 |

#### 评估规则（8 个指标）

| 指标 | 优秀 | 良好 | 偏高/一般 | 风险/偏低 |
|------|------|------|-----------|-----------|
| 资产负债率 | ≤30% | ≤50% | ≤70% | >70% |
| 流动比率 | ≥2.0 | ≥1.5 | ≥1.0 | <1.0 |
| 毛利率 | ≥40% | ≥20% | ≥10% | <10% |
| 净利率 | ≥15% | ≥8% | ≥3% | <3% |
| ROE | ≥20% | ≥10% | ≥5% | <5% |
| 收入增长率 | ≥20% | ≥10% | ≥0% | <0% |
| 综合税负率 | ≤2% | ≤5% | ≤10% | >10% |

### 4.15 税收优惠查询

**文件**: `modules/tax_incentive_query.py`（17KB）

本地税收优惠政策数据库搜索（1522 条政策，FTS5 索引）。

#### 四级渐进搜索

| 级别 | 策略 | 条件 |
|------|------|------|
| 1 | 结构化搜索 | tax_type + entity LIKE (AND) |
| 2 | 实体搜索 | entity keywords 跨字段 LIKE (AND) |
| 3 | 关键词 LIKE | search keywords 跨 6 字段 (AND) |
| 4 | FTS5 全文搜索 | 回退方案 |

#### 意图解析

纯正则（无 LLM），从配置驱动的词表中提取：
- `tax_type`: 税种（增值税、企业所得税等）
- `entity_keywords`: 核心实体（集成电路、软件、高新技术等）
- `search_keywords`: 搜索关键词（已知词 + CJK 片段，去停用词）

#### 结果摘要

Top 10 结果 → DeepSeek LLM 摘要。LLM 失败时回退到简单列表。

#### 接口

```python
search(question, limit=10)        → dict (answer + raw_results)
search_stream(question, limit=10) → generator (chunk, is_done, result)
```

---

### 4.16 法规知识库查询

**文件**: `modules/regulation_api.py`（9KB）

对接 Coze RAG API，SSE 流式返回法规/操作类知识。

#### 调用流程

1. POST 到 Coze API（bot_id, user_id, question）
2. 解析 SSE 流（event: data: 格式）
3. 累积 type=answer 内容（跳过 card template JSON）
4. 强制 UTF-8 编码（requests 默认 ISO-8859-1）
5. 检测 HTTP 200 body 中的错误（Coze 以 JSON 形式在 200 中返回错误）

#### 接口

```python
query_regulation(question)        → dict (answer)
query_regulation_stream(question) → generator (chunk, is_done, result)
```

#### 错误处理

- HTTP 状态码检查
- Content-Type 验证 (text/event-stream)
- 首行 JSON 错误检测
- 超时/连接错误处理
- Card template 过滤（跳过含 card_type 的 JSON）

---

## 5. 前端架构

### 5.1 组件体系

React 19 SPA，Vite 7 构建，CSS Modules 作用域样式。

#### 组件树

```
App (根状态管理)
├── Header (企业选择器, 时钟, 用户信息)
├── Sidebar (导航: 智能问答, 企业画像, 禁用项)
├── ChatArea (主聊天界面)
│   ├── ChatMessage (用户/助手消息)
│   │   ├── ResultTable (格式化数据表)
│   │   ├── ChartRenderer (Chart.js 可视化)
│   │   ├── GrowthTable (环比分析表)
│   │   └── PipelineDetail (可折叠调试信息)
│   └── ChatInput (输入框, 模式选择器, 控件)
├── HistoryPanel (侧边栏: 搜索 + 删除)
├── CompanyProfile (企业画像页面)
│   ├── ProfileHeader (企业名称, 年份选择器)
│   ├── ProfileSection (可折叠区块)
│   └── Modules:
│       ├── IdentityModule (基本信息)
│       ├── FinancialModule (资产, 利润, 现金流)
│       ├── BusinessModule (收入, 发票)
│       ├── RDModule (研发投入)
│       ├── TaxModule (税务摘要)
│       ├── CrossBorderModule (跨境业务)
│       ├── ComplianceModule (风险评估)
│       └── PlaceholderModule (未来功能)
└── Footer (版权, 版本)
```

#### 布局系统

CSS Grid 三栏布局：

```css
grid-template:
  "header  header  header"  56px
  "sidebar main    history" 1fr
  "footer  footer  footer"  36px
  / 220px 1fr 280px;
```

企业画像页面切换为无历史面板布局（`data-page="profile"`）。

#### 设计变量

```css
--color-primary: #2563eb;
--color-sidebar-bg: #1e293b;
--color-body-bg: #f1f5f9;
--header-height: 56px;
--sidebar-width: 220px;
--history-width: 280px;
--footer-height: 36px;
```

---

### 5.2 SSE 流式通信

#### API 客户端 (`services/api.js`)

```javascript
// 核心端点
GET  /api/companies              → fetchCompanies()
GET  /api/chat/history?limit=100 → fetchHistory()
POST /api/chat/history           → saveHistoryEntry(entry)
DELETE /api/chat/history         → deleteHistory(ids)
GET  /api/profile/{id}?year=Y   → fetchProfile()
POST /api/chat (SSE)             → chatStream(query, signal, options)
```

#### SSE 解析器 (`utils/sseParser.js`)

```javascript
async function* parseSSE(response) {
  // ReadableStream → UTF-8 解码 → 逐行解析
  // 解析 "event: " 和 "data: " 行
  // JSON 解析尝试，失败回退到原始字符串
  yield { event, data }
}
```

#### useSSE Hook (`hooks/useSSE.js`)

```javascript
const { startStream, cancel } = useSSE()

startStream(query, (event) => {
  // event.type: 'stage' | 'chunk' | 'done' | 'error'
}, { response_mode, company_id })
```

支持 `AbortController` 取消流式请求。

---

### 5.3 聊天界面

#### ChatArea

- 消息列表管理
- 智能自动滚动（仅在用户位于底部时滚动）
- 选择模式（批量删除消息）
- 导出 PDF（DOM 克隆 + Canvas 转图片 + 打印对话框）

#### ChatMessage

根据 `route` 和 `responseMode` 渲染不同布局：

| 路由 | 简报模式 | 纯数据模式 | 图文模式 |
|------|----------|------------|----------|
| financial_data | 仅摘要 | 表格 + 增长分析 | 表格 + 图表 + 增长分析 |
| tax_incentive | 流式文本 | 流式文本 | 流式文本 |
| regulation | 流式文本 | 流式文本 | 流式文本 |

展示类型：`metric`（指标卡）、`kv`（键值对）、`table`（表格）、`cross_domain`（跨域分组）

#### ChatInput

- 文本域（500 字限制）
- 三种响应模式: 图文 (detailed) / 纯数据 (standard) / 简报 (concise)
- Enter 发送，Shift+Enter 换行
- Escape 取消流式
- 字符计数器

#### 消息数据结构

```javascript
{
  id: 'u-{timestamp}' | 'a-{timestamp}',
  role: 'user' | 'assistant',
  content: 'text',
  status: 'loading' | 'streaming' | 'done' | 'error',
  route: 'financial_data' | 'tax_incentive' | 'regulation',
  result: { /* 后端响应 */ },
  chunks: ['chunk1', 'chunk2'],  // 流式文本
  pipelineDetail: { entities, intent, sql },
  responseMode: 'detailed' | 'standard' | 'concise'
}
```

---

### 5.4 企业画像页面

#### CompanyProfile 组件

- 从 `GET /api/profile/{taxpayer_id}?year=Y` 获取数据
- 年份选择器（2025, 2024, 2023）
- 12 个画像区块（7 个已实现，5 个占位）

#### 子模块

| 模块 | 内容 |
|------|------|
| IdentityModule | 企业名称、行业、纳税人类型、注册资本、经营状态 |
| FinancialModule | 资产结构、利润数据、现金流、财务指标（含 MiniChart） |
| BusinessModule | 营业收入、发票统计 |
| RDModule | 研发费用、研发强度 |
| TaxModule | 增值税 + 所得税税负 |
| CrossBorderModule | 境外收入、税收抵免 |
| ComplianceModule | 风险指标、流动性评估（含 EvalLabel） |

#### 辅助组件

- `ProfileHeader`: 企业名称 + 年份选择
- `ProfileSection`: 可折叠区块容器
- `CompactMetric`: 紧凑指标卡
- `EvalLabel`: 评估标签（优秀/良好/一般/偏低，颜色编码）
- `MiniChart`: 迷你图表（饼图/柱状图/折线图）
- `ProgressBar`: 进度条

---

### 5.5 图表渲染

#### ChartRenderer（查询结果图表）

- 使用 `react-chartjs-2` 的 Bar 组件
- 支持柱状/折线/组合图
- 双 Y 轴（百分比 + 绝对值）
- 智能数字格式化（亿/万缩放）
- Tooltip 回调格式化

#### MiniChart（画像卡片图表）

- 支持饼图/柱状图/折线图
- 自动分配颜色
- 紧凑图例
- 用于 FinancialModule、TaxModule 等

#### 数字格式化

```javascript
// 值 ≥ 1亿 → 缩放到亿
// 值 ≥ 1万 → 缩放到万
// 百分比 → X.XX%
// 千分位分隔符
```

---

### 5.6 状态管理

纯 React Hooks + 本地组件状态，无 Redux/Zustand。

| 组件 | 状态 |
|------|------|
| App | messages, historyItems, responseMode, selectedCompanyId, currentPage |
| ChatArea | isSelectionMode, selectedIndices, highlightIdx |
| CompanyProfile | year, data, loading, error |
| Header | time (时钟), companies (下拉列表) |
| HistoryPanel | selected (复选框), searchText |

Refs 使用：
- `chatAreaRef` → `useImperativeHandle` 暴露 `scrollToMessage()`
- `msgRefs` → 消息 DOM 元素数组（滚动定位）
- `containerRef` → 聊天消息容器（导出/打印）
- `controllerRef` → AbortController（SSE 取消）

## 6. 数据库设计

### 6.1 表结构总览

SQLite 数据库 (`database/fintax_ai.db`)，DDL 定义在 `database/init_db.py`（70KB）。

#### 维度表

| 表名 | 用途 |
|------|------|
| `dim_industry` | 行业分类 |
| `dim_tax_authority` | 税务机关 |
| `dim_region` | 地区 |

#### 主数据表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `taxpayer_info` | 纳税人主表 | taxpayer_id (PK), taxpayer_name, taxpayer_type, accounting_standard, registered_capital, registered_address, business_scope, operating_status, collection_method |
| `taxpayer_profile_snapshot_month` | 月度画像快照 | (taxpayer_id, period_year, period_month) PK |
| `taxpayer_credit_grade_year` | 年度信用等级 | (taxpayer_id, year) PK |

#### 增值税表

| 表名 | 指标数 | PK |
|------|--------|-----|
| `vat_return_general` | 41 | (taxpayer_id, period_year, period_month, item_type, time_range, revision_no) |
| `vat_return_small` | 25 | 同上 |

#### 企业所得税表

| 表名 | 用途 | PK |
|------|------|-----|
| `eit_annual_filing` | 年度申报主表 | (taxpayer_id, period_year, revision_no) |
| `eit_annual_main` | 年度主表 A100000 | (filing_id) FK |
| `eit_annual_shareholder` | 股东信息 | (filing_id, shareholder_seq) |
| `eit_quarter_filing` | 季度申报主表 | (taxpayer_id, period_year, period_quarter, revision_no) |
| `eit_quarter_main` | 季度主表 | (filing_id) FK |

#### 科目余额表

| 表名 | 用途 | PK |
|------|------|-----|
| `account_master` | 科目目录 | (account_code, gaap_scope) |
| `account_balance` | 月度余额 | (taxpayer_id, period_year, period_month, account_code) |

#### 财务报表（EAV 纵表）

| 表名 | GAAP | PK |
|------|------|-----|
| `fs_balance_sheet_item` | ASBE/ASSE | (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no) |
| `fs_income_statement_item` | CAS/SAS | 同上 |
| `fs_cash_flow_item` | CAS/SAS | 同上 |

每个报表配套字典表和同义词表：
- `fs_balance_sheet_item_dict` (ASBE 67 项, ASSE 53 项)
- `fs_balance_sheet_synonyms`
- `fs_income_statement_item_dict` (CAS 42 项, SAS 32 项)
- `fs_income_statement_synonyms`
- `fs_cash_flow_item_dict` (CAS 35 项, SAS 22 项)
- `fs_cash_flow_synonyms`

#### 发票表

| 表名 | 用途 | PK | 特殊字段 |
|------|------|-----|----------|
| `inv_spec_purchase` | 进项发票宽表 | (taxpayer_id, invoice_pk, line_no) | goods_name, specification, unit, quantity, unit_price, tax_rate, tax_category_code, special_business_type |
| `inv_spec_sales` | 销项发票宽表 | 同上 | 无商品明细字段 |

配套: `inv_column_mapping`, `inv_synonyms`

#### 财务指标表

| 表名 | 版本 | 用途 |
|------|------|------|
| `financial_metrics` | v1 | 17 指标，月度 |
| `financial_metrics_item` | v2 | 25 指标，月度/季度/年度粒度 |
| `financial_metrics_item_dict` | v2 | 指标定义 + 评估规则 (JSON) |
| `financial_metrics_synonyms` | - | 指标同义词 |

#### 日志表

| 表名 | 用途 |
|------|------|
| `user_query_log` | 查询审计日志 |
| `unmatched_phrases` | 未匹配短语反馈 |
| `etl_error_log` | ETL 错误跟踪 |

---

### 6.2 视图设计

NL2SQL 永远不直接查询明细表，视图是唯一的查询入口。

#### 视图列表

| 视图 | 源表 | 特点 |
|------|------|------|
| `vw_vat_return_general` | vat_return_general + taxpayer_info | 按纳税人类型过滤 |
| `vw_vat_return_small` | vat_return_small + taxpayer_info | 按纳税人类型过滤 |
| `vw_eit_annual_main` | eit_annual_filing + eit_annual_main | JOIN 申报 + 主表 |
| `vw_eit_quarter_main` | eit_quarter_filing + eit_quarter_main | JOIN 申报 + 主表 |
| `vw_account_balance` | account_balance + taxpayer_info | 作用域感知 |
| `vw_balance_sheet_eas` | fs_balance_sheet_item (ASBE) | EAV → 宽表 pivot |
| `vw_balance_sheet_sas` | fs_balance_sheet_item (ASSE) | EAV → 宽表 pivot |
| `vw_profit_eas` | fs_income_statement_item (CAS) | EAV → 宽表 + CROSS JOIN time_range |
| `vw_profit_sas` | fs_income_statement_item (SAS) | EAV → 宽表 + CROSS JOIN time_range |
| `vw_cash_flow_eas` | fs_cash_flow_item (CAS) | EAV → 宽表 + CROSS JOIN time_range |
| `vw_cash_flow_sas` | fs_cash_flow_item (SAS) | EAV → 宽表 + CROSS JOIN time_range |
| `vw_inv_spec_purchase` | inv_spec_purchase + taxpayer_info | JOIN 纳税人信息 |
| `vw_inv_spec_sales` | inv_spec_sales + taxpayer_info | JOIN 纳税人信息 |
| `vw_financial_metrics` | financial_metrics_item | v2 指标视图 |

#### EAV → 宽表 Pivot 模式

资产负债表、利润表、现金流量表均采用 EAV 纵表存储，视图通过 `MAX(CASE WHEN item_code = 'xxx' THEN value END)` 聚合转换为宽表。

```sql
-- 示例：资产负债表视图 pivot
SELECT taxpayer_id, period_year, period_month,
  MAX(CASE WHEN item_code = 'cash' THEN begin_balance END) AS cash_begin,
  MAX(CASE WHEN item_code = 'cash' THEN end_balance END) AS cash_end,
  ...
FROM fs_balance_sheet_item
WHERE gaap_type = 'ASBE'
GROUP BY taxpayer_id, period_year, period_month
```

利润表和现金流量表额外使用 `CROSS JOIN` 生成 `time_range` 维度（'本期'/'本年累计'）。

#### 修订版本处理

默认查询策略为"最新版本"，通过 `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY revision_no DESC)` 窗口函数实现。

---

### 6.3 数据初始化流程

```
database/init_db.py          → DDL (所有表、视图、索引)
  ↓
database/seed_data.py        → 参考数据 (字典、同义词、映射)
  ↓
database/sample_data.py      → 基础样本 (2025 Q1, 2 纳税人)
  ↓
database/sample_data_extended.py → 扩展样本 (2024.01–2026.02, 26 个月)
  ↓
database/calculate_metrics.py    → 财务指标 v1 (17 指标)
  ↓
database/calculate_metrics_v2.py → 财务指标 v2 (25 指标, 多粒度)
  ↓
database/migrate_profile.py      → 画像字段迁移 (5 列)
  ↓
database/add_performance_indexes.py → 性能索引 (7 个)
```

#### 样本数据生成算法

```python
# 月度因子 = 增长趋势 × 季节波动
monthly_factor(offset) = (1 + growth_rate)^offset × (1 + seasonal_amp × sin(2π × offset / 12))
```

- 华兴科技: 月增长 2%, 季节振幅 5-8%
- 鑫源贸易: 月增长 1.5%, 季节振幅 5-8%

#### 跨域数据一致性

- VAT 销售额 ≈ 利润表营业收入（含税调整）
- 利润表净利润 ≈ 科目余额未分配利润变动
- 现金流量表期末现金 ≈ 资产负债表货币资金
- EIT 收入 ≈ 利润表收入（季度）

---

### 6.4 财务指标计算

#### v1 (`calculate_metrics.py`) — 17 指标

| 类别 | 指标 |
|------|------|
| 盈利能力 | 毛利率, 净利率, ROE |
| 偿债能力 | 资产负债率, 流动比率, 速动比率 |
| 营运能力 | 应收账款周转率, 存货周转率 |
| 成长能力 | 收入增长率 |
| 现金流 | 销售收现比 |
| 税负率 | 增值税税负率, 所得税税负率, 综合税负率 |
| 增值税重点 | 销项/进项比, 转出比 |
| 所得税重点 | 应纳税所得额比 |
| 风险预警 | 零申报比例 |

#### v2 (`calculate_metrics_v2.py`) — 25 指标

增强特性：
- 期间类型: monthly / quarterly / annual
- 评估规则: JSON 阈值存储在 `financial_metrics_item_dict`
- 升序标志: 指示高/低哪个更好
- 评估等级: 优秀/良好/一般/偏低

---

## 7. 域系统设计

### 9 个业务域

| 域 | 视图 | Stage 2 提示词 | 检测优先级 |
|----|------|----------------|------------|
| 增值税 | `vw_vat_return_general`, `vw_vat_return_small` | `stage2_vat.txt` | 8 (默认) |
| 企业所得税 | `vw_eit_annual_main`, `vw_eit_quarter_main` | `stage2_eit.txt` | 6 |
| 资产负债表 | `vw_balance_sheet_eas`, `vw_balance_sheet_sas` | `stage2_balance_sheet.txt` | 5 |
| 科目余额 | `vw_account_balance` | `stage2_account_balance.txt` | 3 |
| 利润表 | `vw_profit_eas`, `vw_profit_sas` | `stage2_profit.txt` | 4 |
| 现金流量表 | `vw_cash_flow_eas`, `vw_cash_flow_sas` | `stage2_cash_flow.txt` | 2 |
| 发票 | `vw_inv_spec_purchase`, `vw_inv_spec_sales` | `stage2_invoice.txt` | 7 |
| 财务指标 | `vw_financial_metrics` | `stage2_financial_metrics.txt` | 1 |
| 企业画像 | `vw_enterprise_profile` | via `profile_service.py` REST API | N/A |
| 跨域 | 多视图 | `stage2_cross_domain.txt` | 9 (升级) |

### 双准则 GAAP 路由

```
taxpayer_type / accounting_standard
  ├─ 一般纳税人 / 企业会计准则 → ASBE/CAS 视图 (eas)
  └─ 小规模纳税人 / 小企业会计准则 → ASSE/SAS 视图 (sas)
```

### 发票双表设计

| 表 | 方向 | 特殊字段 |
|----|------|----------|
| `inv_spec_purchase` | 进项（采购） | goods_name, specification, unit, quantity, unit_price, tax_rate, tax_category_code, special_business_type |
| `inv_spec_sales` | 销项（销售） | 无商品明细 |

发票格式: `数电` (数字发票) / `非数电` (传统发票)

---

## 8. LLM 提示词工程

### Stage 1 系统提示词 (`prompts/stage1_system.txt`, 17KB)

核心内容：
- 14 条域判断规则（按优先级排序）
- 作用域确定规则（GAAP 类型、报表类型等）
- JSON Schema 规范
- 48 条字段映射和默认值规则
- 澄清触发条件（缺少期间、域歧义等）

### Stage 2 域特定提示词

每个域一个提示词文件，共同模板结构：

```
【允许访问的视图】仅：{allowed_views_text}
【允许的列】{allowed_columns_text}
【必备过滤】
  1. taxpayer_id = :taxpayer_id
  2. 期间过滤
【修订版本处理】ROW_NUMBER() OVER (... ORDER BY revision_no DESC)
【输出要求】只输出 SQL，禁止 SELECT *
【用户意图 JSON】{intent_json}
```

域特定变体：
- VAT: item_type 过滤 + time_range 过滤
- EIT: 年度 vs 季度报表类型
- 资产负债表: GAAP 路由 + EAV→宽表 pivot
- 利润表/现金流量表: time_range 过滤 + GAAP 路由
- 科目余额: opening/debit/credit/closing 列
- 财务指标: metric_name/metric_code 过滤
- 发票: 方向路由 (进项/销项)
- 跨域: UNION ALL + 对齐 Schema

### 税收优惠摘要提示词 (`prompts/tax_incentive_summary.txt`)

用于 LLM 摘要搜索结果。

---

## 9. 配置体系

### 主配置 (`config/settings.py`)

```python
# 数据库
DB_PATH = PROJECT_ROOT / "database" / "fintax_ai.db"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# LLM (DeepSeek)
LLM_API_KEY = "sk-..."
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 60

# 管线安全限制
MAX_ROWS = 1000
MAX_PERIOD_MONTHS = 36

# 四级缓存
CACHE_ENABLED = True
CACHE_MAX_SIZE_INTENT = 500      # Stage 1 意图
CACHE_MAX_SIZE_SQL = 500         # Stage 2 SQL
CACHE_MAX_SIZE_RESULT = 200      # SQL 结果
CACHE_MAX_SIZE_CROSS = 100       # 跨域结果
CACHE_TTL_INTENT = 1800          # 30 分钟
CACHE_TTL_SQL = 3600             # 1 小时
CACHE_TTL_RESULT = 1800          # 30 分钟
CACHE_TTL_CROSS = 1800           # 30 分钟

# 税收优惠数据库
TAX_INCENTIVES_DB_PATH = PROJECT_ROOT / "database" / "tax_incentives.db"

# Coze RAG API
COZE_API_URL = "https://api.coze.cn/v3/chat"
COZE_PAT_TOKEN = "pat_..."
COZE_BOT_ID = "7592905400907989034"
COZE_USER_ID = "123"
COZE_TIMEOUT = 180

# 意图路由器
ROUTER_ENABLED = True
```

### 意图路由配置 (`config/tax_query_config.json`)

热重载配置，包含：
- `tax_types`: 12 种税种
- `tax_fuzzy_map`: 模糊映射
- `incentive_keywords`: 15 个优惠关键词
- `core_entity_keywords`: 8 个核心实体
- `financial_db_priority_keywords`: 13 个数据优先关键词
- `financial_tax_type_keywords`: 19 个税种关键词
- `knowledge_base_priority_keywords`: 20 个知识库优先关键词
- `exclude_from_incentive`: 4 个排除关键词

### Vite 开发配置 (`frontend/vite.config.js`)

```javascript
{
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' }
  },
  build: { outDir: 'dist' }
}
```

## 10. 测试体系

### 测试套件总览

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| `run_tests.py` | 5 | 核心管线（重建 DB） |
| `test_real_scenarios.py` | 46 | 真实场景（9 域） |
| `test_comprehensive.py` | 57 | 全域综合（单域 + 跨域） |
| `test_cache.py` | 3 | 缓存有效性 |
| `test_performance.py` | 3 | 性能基准 |
| `tests/test_bs.py` | - | 资产负债表单元测试 |
| `tests/test_concept_registry.py` | - | 概念注册表单元测试 |
| `tests/test_display_formatter.py` | - | 展示格式化器单元测试 |

### 核心管线测试 (`run_tests.py`)

5 个测试用例：
1. T1: 单字段查询 (VAT)
2. T2: 趋势查询 (3 个月)
3. T3: 缺少期间 → 触发澄清
4. T4: 小规模纳税人查询
5. T5: 多字段查询 + 修订版本处理

测试前重建数据库（init → seed → sample）。

### 真实场景测试 (`test_real_scenarios.py`)

46 个用例，6 个类别：
- 单域单指标单期间 (6)
- 单域单指标多期间 (6)
- 单域多指标多期间 (6)
- 跨域单指标单期间 (10)
- 跨域单指标多期间 (10)
- 跨域多指标多期间 (10, 未测试)

验证项：相对日期解析、域检测、管线执行成功。

### 综合测试 (`test_comprehensive.py`)

57 个问题，9 域覆盖：
- 单域问题 (27): 每域 3 个
- 跨域问题 (30): 单指标/多指标 × 单期间/多期间

验证项：预期域检测、预期执行路径、最小行数。

### 缓存测试 (`test_cache.py`)

验证四级缓存有效性：首次查询（miss）→ 重复查询（hit）→ 再次查询（hit），对比执行时间。

### 性能基准 (`test_performance.py`)

测试查询：单字段、重复查询（缓存命中）、相似查询（部分缓存命中）。指标：执行时间、缓存命中率、性能提升百分比。

---

## 11. 项目文件结构

```
D:\fintax_ai/
├── api/                              # FastAPI 后端
│   ├── main.py                       # 应用入口 (CORS, 静态文件, DB 初始化)
│   ├── schemas.py                    # Pydantic 模型
│   └── routes/
│       ├── chat.py                   # SSE 流式聊天端点
│       ├── company.py                # 企业列表端点
│       ├── history.py                # 聊天历史管理
│       └── profile.py               # 企业画像端点
│
├── config/                           # 配置
│   ├── settings.py                   # 主配置
│   └── tax_query_config.json         # 意图路由关键词配置
│
├── database/                         # 数据库层
│   ├── init_db.py                    # DDL (表、视图、索引)
│   ├── seed_data.py                  # 参考数据 (字典、同义词)
│   ├── sample_data.py                # 基础样本数据
│   ├── sample_data_extended.py       # 扩展样本 (26 个月)
│   ├── seed_fs.py                    # 财务报表种子数据
│   ├── seed_cf.py                    # 现金流量表种子数据
│   ├── calculate_metrics.py          # 财务指标 v1 (17 指标)
│   ├── calculate_metrics_v2.py       # 财务指标 v2 (25 指标)
│   ├── migrate_profile.py            # 画像字段迁移
│   ├── migrate_invoice.py            # 发票表迁移
│   ├── add_performance_indexes.py    # 性能索引
│   └── fintax_ai.db                  # SQLite 数据库文件
│
├── modules/                          # 核心 NL2SQL 管线模块
│   ├── intent_router.py              # 三路意图路由器
│   ├── entity_preprocessor.py        # 实体预处理 (日期、域、同义词)
│   ├── intent_parser.py              # Stage 1: 意图解析 (LLM)
│   ├── constraint_injector.py        # 约束注入
│   ├── sql_writer.py                 # Stage 2: SQL 生成 (LLM)
│   ├── sql_auditor.py                # SQL 安全审计
│   ├── schema_catalog.py             # 域/视图/列白名单
│   ├── cross_domain_calculator.py    # 跨域查询计算
│   ├── metric_calculator.py          # 确定性指标计算
│   ├── concept_registry.py           # 概念注册表 (40+ 概念)
│   ├── cache_manager.py              # 四级 LRU 缓存
│   ├── display_formatter.py          # 展示格式化 (React JSON)
│   ├── profile_service.py            # 企业画像聚合服务
│   ├── tax_incentive_query.py        # 税收优惠政策搜索
│   └── regulation_api.py             # Coze RAG API 集成
│
├── prompts/                          # LLM 提示词
│   ├── stage1_system.txt             # Stage 1 系统提示词
│   ├── stage2_vat.txt                # VAT 域 SQL 生成
│   ├── stage2_eit.txt                # EIT 域 SQL 生成
│   ├── stage2_balance_sheet.txt      # 资产负债表域
│   ├── stage2_account_balance.txt    # 科目余额域
│   ├── stage2_profit.txt             # 利润表域
│   ├── stage2_cash_flow.txt          # 现金流量表域
│   ├── stage2_financial_metrics.txt  # 财务指标域
│   ├── stage2_invoice.txt            # 发票域
│   ├── stage2_cross_domain.txt       # 跨域
│   └── tax_incentive_summary.txt     # 税收优惠摘要
│
├── frontend/                         # React SPA
│   ├── package.json                  # 依赖 (React 19, Chart.js 4, Vite 7)
│   ├── vite.config.js                # Vite 配置 (代理 /api)
│   ├── index.html                    # HTML 入口
│   ├── dist/                         # 构建产物 (FastAPI 托管)
│   └── src/
│       ├── main.jsx                  # React 入口
│       ├── App.jsx                   # 根组件 (状态管理)
│       ├── styles/global.css         # 全局样式 + CSS 变量
│       ├── services/api.js           # API 客户端
│       ├── utils/sseParser.js        # SSE 流解析器
│       ├── hooks/
│       │   ├── useChatHistory.js     # 聊天历史 Hook
│       │   └── useSSE.js            # SSE 连接 Hook
│       └── components/
│           ├── Header/               # 顶部导航 + 企业选择器
│           ├── Sidebar/              # 侧边导航
│           ├── ChatArea/             # 主聊天区域
│           ├── ChatInput/            # 输入框 + 模式选择
│           ├── ChatMessage/          # 消息渲染 (多路由多模式)
│           ├── ResultTable/          # 数据表格
│           ├── ChartRenderer/        # Chart.js 图表
│           ├── GrowthTable/          # 增长分析表
│           ├── HistoryPanel/         # 历史记录面板
│           ├── PipelineDetail/       # 管线调试信息
│           ├── Footer/              # 页脚
│           └── CompanyProfile/       # 企业画像模块
│               ├── CompanyProfile.jsx
│               ├── ProfileHeader.jsx
│               ├── ProfileSection.jsx
│               ├── CompactMetric.jsx
│               ├── EvalLabel.jsx
│               ├── MiniChart.jsx
│               ├── ProgressBar.jsx
│               ├── utils.js
│               └── modules/          # 7 个画像子模块
│
├── tests/                            # 单元测试
│   ├── test_bs.py                    # 资产负债表测试
│   ├── test_concept_registry.py      # 概念注册表测试
│   └── test_display_formatter.py     # 展示格式化器测试
│
├── mvp_pipeline.py                   # 主管线编排器
├── app.py                            # Gradio 备用前端
├── run_tests.py                      # 核心测试 (5 用例)
├── test_real_scenarios.py            # 真实场景测试 (46 用例)
├── test_comprehensive.py             # 综合测试 (57 用例)
├── test_cache.py                     # 缓存测试
├── test_performance.py               # 性能基准
├── requirements.txt                  # Python 依赖
└── CLAUDE.md                         # 项目文档
```

---

## 附录：关键设计决策

| 决策 | 理由 |
|------|------|
| 两阶段 LLM 管线 | 分离意图理解与 SQL 生成，提高可控性和可审计性 |
| EAV 纵表 + 宽表视图 | 灵活存储 + 高效查询，支持双准则 GAAP |
| 白名单安全模型 | schema_catalog.py 作为唯一真相来源，防止 SQL 注入 |
| 确定性路径优先 | 指标/概念路径绕过 LLM，提高速度和准确性 |
| 四级缓存 | 减少 LLM 调用和 SQL 执行，提升响应速度 |
| 三路意图路由 | 分流不同类型查询到最适合的处理路径 |
| SSE 流式响应 | 实时推送，改善用户体验 |
| 热重载配置 | 无需重启即可调整路由关键词 |
| 最长匹配同义词 | 避免短词截断长词，提高替换准确性 |
| 跨域并行 LLM + 串行 SQL | 平衡性能与 SQLite 线程安全 |
| 路由感知查询隔离 | 避免企业名称污染税收优惠/法规搜索 |
| 季度聚合策略 | sum_months vs quarter_end 适配不同数据特征 |
