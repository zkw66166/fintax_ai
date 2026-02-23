# fintax_ai 税务智能咨询系统 — 完整技术文档

> 版本：v2.0 | 更新日期：2026-02-20 | 状态：MVP 完成

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [核心管线 (NL2SQL Pipeline)](#4-核心管线-nl2sql-pipeline)
5. [意图路由层](#5-意图路由层)
6. [实体预处理模块](#6-实体预处理模块)
7. [Stage 1：意图解析 (LLM)](#7-stage-1意图解析-llm)
8. [约束注入模块](#8-约束注入模块)
9. [Stage 2：SQL 生成 (LLM)](#9-stage-2sql-生成-llm)
10. [SQL 审计模块](#10-sql-审计模块)
11. [跨域查询系统](#11-跨域查询系统)
12. [财务指标计算](#12-财务指标计算)
13. [概念注册表](#13-概念注册表)
14. [缓存系统](#14-缓存系统)
15. [Schema 白名单](#15-schema-白名单)
16. [数据库层](#16-数据库层)
17. [API 层 (FastAPI)](#17-api-层-fastapi)
18. [前端 (React SPA)](#18-前端-react-spa)
19. [展示格式化模块](#19-展示格式化模块)
20. [税收优惠查询模块](#20-税收优惠查询模块)
21. [外部法规知识库](#21-外部法规知识库)
22. [LLM Prompt 体系](#22-llm-prompt-体系)
23. [配置系统](#23-配置系统)
24. [测试体系](#24-测试体系)
25. [部署与运维](#25-部署与运维)

---

## 1. 项目概述

### 1.1 产品定位

fintax_ai 是一个面向中国税务和财务咨询场景的智能问答平台。用户以自然语言提问，系统自动将问题转化为 SQL 查询，从结构化的税务申报和财务报表数据中获取答案。

### 1.2 核心能力

| 能力 | 说明 |
|------|------|
| NL2SQL 查询 | 9 大领域的自然语言→SQL 转换 |
| 三路意图路由 | 财务数据查询 / 税收优惠政策 / 法规知识库 |
| 确定性计算 | 8 项财务指标 + 40+ 财务概念的无 LLM 计算 |
| 跨域分析 | 跨报表对比、比率、勾稽、列举 |
| 流式输出 | SSE 实时推送查询进度和结果 |
| 可视化展示 | Chart.js 图表 + 智能数字格式化 |

### 1.3 技术栈

| 层级 | 技术 |
|------|------|
| LLM | DeepSeek (`deepseek-chat`) via OpenAI-compatible API |
| 后端 | Python 3.10+ / FastAPI / Uvicorn |
| 数据库 | SQLite (本地文件) |
| 前端 | React 18 + Vite + CSS Modules |
| 图表 | Chart.js |
| 遗留前端 | Gradio 4.44.1 (app.py) |
| 外部 API | Coze RAG API (法规知识库) |

### 1.4 支持的 9 大查询领域

| # | 领域 | 中文名 | 视图 |
|---|------|--------|------|
| 1 | VAT | 增值税申报 | `vw_vat_return_general`, `vw_vat_return_small` |
| 2 | EIT | 企业所得税 | `vw_eit_annual_main`, `vw_eit_quarter_main` |
| 3 | balance_sheet | 资产负债表 | `vw_balance_sheet_eas`, `vw_balance_sheet_sas` |
| 4 | account_balance | 科目余额 | `vw_account_balance` |
| 5 | profit | 利润表 | `vw_profit_eas`, `vw_profit_sas` |
| 6 | cash_flow | 现金流量表 | `vw_cash_flow_eas`, `vw_cash_flow_sas` |
| 7 | financial_metrics | 财务指标 | `vw_financial_metrics` |
| 8 | invoice | 发票 | `vw_inv_spec_purchase`, `vw_inv_spec_sales` |
| 9 | cross_domain | 跨域查询 | 多视图组合 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        React SPA (前端)                          │
│  Header │ Sidebar │ ChatArea │ ChatMessage │ ChartRenderer │ ... │
└────────────────────────────┬────────────────────────────────────┘
                             │ SSE (POST /api/chat)
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend (api/)                        │
│  /api/chat  │  /api/companies  │  /api/chat/history              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   Pipeline Orchestrator                           │
│                    (mvp_pipeline.py)                              │
│                                                                   │
│  ┌──────────────┐                                                │
│  │ Intent Router │──→ tax_incentive ──→ TaxIncentiveQuery        │
│  │              │──→ regulation ──→ Coze RAG API                 │
│  │              │──→ financial_data ↓                             │
│  └──────────────┘                                                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────┐        │
│  │ Entity Preprocessor (日期解析/实体提取/领域检测/同义词)  │        │
│  └──────────────────────────┬───────────────────────────┘        │
│                              │                                    │
│  ┌───────────┐  ┌───────────▼──┐  ┌──────────────┐              │
│  │ Metric    │  │ Concept      │  │ Standard/    │              │
│  │ Calculator│  │ Registry     │  │ Cross-Domain │              │
│  │ (无LLM)   │  │ (无LLM)      │  │ (两阶段LLM)  │              │
│  └─────┬─────┘  └──────┬──────┘  └──────┬───────┘              │
│        │               │                 │                        │
│        │               │    ┌────────────▼──────────┐            │
│        │               │    │ Stage 1: Intent Parser │            │
│        │               │    │ Stage 2: SQL Writer    │            │
│        │               │    │ SQL Auditor (审计)      │            │
│        │               │    └────────────┬──────────┘            │
│        └───────────────┴────────────────▼                        │
│                              SQLite 执行                          │
│                              Display Formatter                    │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 五条执行路径

| 路径 | 触发条件 | 是否需要 LLM | 说明 |
|------|----------|-------------|------|
| 税收优惠 | 意图路由→tax_incentive | 仅摘要 | 本地 FTS5 搜索 + LLM 摘要 |
| 法规知识库 | 意图路由→regulation | 外部 API | Coze RAG API |
| 指标路径 | 匹配已注册指标 | 否 | 确定性 SQL + Python 公式 |
| 概念路径 | ≥2 概念 + 时间粒度 | 否 | 确定性 SQL 构建 |
| 标准/跨域 | 默认 | 是 (两阶段) | Intent Parser → SQL Writer |

---

## 3. 目录结构

```
D:\fintax_ai/
├── api/                          # FastAPI 后端
│   ├── main.py                   # 应用入口 (CORS, 路由注册, 静态文件)
│   ├── schemas.py                # Pydantic 请求/响应模型
│   └── routes/
│       ├── chat.py               # POST /api/chat (SSE 流式)
│       ├── company.py            # GET /api/companies
│       └── history.py            # 聊天历史 CRUD
├── config/
│   ├── settings.py               # 全局配置 (DB/LLM/缓存/外部API)
│   └── tax_query_config.json     # 意图路由关键词配置 (热加载)
├── database/
│   ├── init_db.py                # DDL (表/视图/索引)
│   ├── seed_data.py              # 参考数据 (字典/同义词/指标注册)
│   ├── sample_data.py            # 基础样本数据 (2025.01-03)
│   ├── sample_data_extended.py   # 扩展样本 (2024.01-2026.02)
│   ├── seed_fs.py                # 财务报表种子数据
│   ├── seed_cf.py                # 现金流量表种子数据
│   ├── calculate_metrics.py      # 财务指标计算 (18项)
│   ├── add_performance_indexes.py # 性能索引
│   ├── extract_schema.py         # Schema 提取工具
│   └── migrate_invoice.py        # 发票数据迁移
├── modules/                      # 核心管线模块
│   ├── intent_router.py          # 三路意图路由
│   ├── entity_preprocessor.py    # 实体预处理 (日期/实体/领域/同义词)
│   ├── intent_parser.py          # Stage 1: LLM 意图解析
│   ├── constraint_injector.py    # 约束注入
│   ├── sql_writer.py             # Stage 2: LLM SQL 生成
│   ├── sql_auditor.py            # SQL 安全审计
│   ├── schema_catalog.py         # 领域/视图/列 白名单
│   ├── cross_domain_calculator.py # 跨域查询编排
│   ├── metric_calculator.py      # 财务指标计算 (8项实时)
│   ├── concept_registry.py       # 概念注册表 (40+概念)
│   ├── cache_manager.py          # 四级 LRU 缓存
│   ├── tax_incentive_query.py    # 税收优惠查询
│   ├── regulation_api.py         # Coze RAG API 集成
│   └── display_formatter.py      # 展示格式化
├── prompts/                      # LLM 系统提示词
│   ├── stage1_system.txt         # Stage 1 意图解析提示词
│   ├── stage2_vat.txt            # VAT SQL 生成
│   ├── stage2_eit.txt            # EIT SQL 生成
│   ├── stage2_balance_sheet.txt  # 资产负债表 SQL
│   ├── stage2_profit.txt         # 利润表 SQL
│   ├── stage2_cash_flow.txt      # 现金流量表 SQL
│   ├── stage2_account_balance.txt # 科目余额 SQL
│   ├── stage2_financial_metrics.txt # 财务指标 SQL
│   ├── stage2_invoice.txt        # 发票 SQL
│   ├── stage2_cross_domain.txt   # 跨域 SQL
│   └── tax_incentive_summary.txt # 税收优惠摘要
├── frontend/                     # React SPA
│   ├── src/
│   │   ├── App.jsx               # 根组件
│   │   ├── main.jsx              # 入口
│   │   └── components/           # 13 个子组件
│   ├── dist/                     # 构建产物
│   ├── package.json
│   └── vite.config.js
├── tests/                        # 单元测试
│   ├── test_bs.py                # 资产负债表测试
│   ├── test_display_formatter.py # 展示格式化测试
│   └── test_concept_registry.py  # 概念注册表测试
├── mvp_pipeline.py               # 管线编排主入口
├── app.py                        # Gradio 界面 (遗留)
├── run_tests.py                  # 基础管线测试 (5例)
├── test_real_scenarios.py        # 真实场景测试 (46例)
├── test_comprehensive.py         # 综合测试 (57例, ~96% 通过率)
├── test_cache.py                 # 缓存验证测试
├── test_performance.py           # 性能基准测试
├── requirements.txt              # Python 依赖
└── CLAUDE.md                     # 项目说明
```

---

## 4. 核心管线 (NL2SQL Pipeline)

### 4.1 入口文件：`mvp_pipeline.py`

两个核心函数：

- `run_pipeline(user_query, db_path, progress_callback)` — 同步执行，返回完整结果字典
- `run_pipeline_stream(user_query, db_path, progress_callback, original_query)` — 生成器，yield 事件字典

#### 同步执行流程

```python
def run_pipeline(user_query, db_path, progress_callback):
    # 1. 意图路由 (如果 ROUTER_ENABLED)
    route = IntentRouter.classify(user_query, db_conn)
    if route == 'tax_incentive': return TaxIncentiveQuery.search(...)
    if route == 'regulation': return query_regulation(...)

    # 2. 实体预处理
    entities = detect_entities(user_query, db_conn)

    # 3. 同义词归一化
    normalized_query = normalize_query(user_query, scope_view, ...)

    # 4. 早期指标检测
    if detect_computed_metrics(normalized_query):
        return _run_metric_pipeline(...)  # 无 LLM

    # 5. Stage 1: 意图解析 (LLM)
    intent = parse_intent(normalized_query, entities, synonym_hits)

    # 6. 概念路径检测
    concepts = resolve_concepts(normalized_query, entities)
    if len(concepts) >= 2 and time_granularity:
        return _run_concept_pipeline(...)  # 无 LLM

    # 7. 跨域路径
    if intent['domain'] == 'cross_domain':
        return _run_cross_domain_pipeline(...)

    # 8. 约束注入
    constraints = inject_constraints(intent)

    # 9. Stage 2: SQL 生成 (LLM)
    sql = generate_sql(constraints, domain=intent['domain'])

    # 10. SQL 审计 (失败重试一次)
    passed, violations = audit_sql(sql, allowed_views, max_rows, domain)

    # 11. 执行 (失败重试一次)
    results = execute_sql(sql, params)

    # 12. 日志记录
    _log_query(...)
    return result_dict
```

#### 流式执行事件格式

```python
# 事件类型
{'type': 'stage', 'route': 'financial_data|tax_incentive|regulation', 'text': str}
{'type': 'chunk', 'text': str}       # 文本片段 (tax_incentive/regulation)
{'type': 'done', 'result': dict}     # 最终结果
```

### 4.2 路径选择优先级

```
意图路由 → tax_incentive / regulation (直接返回)
         → financial_data ↓
              指标检测 → 匹配 → 指标路径 (无LLM)
              Stage 1 意图解析 (LLM)
              概念检测 → ≥2概念+时间粒度 → 概念路径 (无LLM)
              领域判断 → cross_domain → 跨域路径 (并行LLM)
                       → 单领域 → 标准路径 (两阶段LLM)
```

### 4.3 重试机制

| 阶段 | 重试策略 |
|------|----------|
| SQL 审计失败 | 将违规信息反馈给 LLM，重新生成 SQL (1次) |
| SQL 执行失败 | 将 SQLite 错误信息 + JOIN 限制提示反馈给 LLM (1次) |
| LLM 调用失败 | OpenAI SDK 内置重试 (max_retries=3) |
| 概念路径失败 | 降级到 LLM 跨域路径 |

---

## 5. 意图路由层

### 5.1 模块：`modules/intent_router.py`

`IntentRouter.classify(question, db_conn)` 在所有领域检测之前运行，将查询分为三条路线：

| 路线 | 说明 | 后续处理 |
|------|------|----------|
| `financial_data` | 财务数据查询 | 进入 NL2SQL 管线 (9 领域) |
| `tax_incentive` | 税收优惠政策 | 本地 tax_incentives.db 搜索 |
| `regulation` | 法规/操作指南 | Coze RAG API |

### 5.2 多层关键词分类

```
Layer -2: 财务数据优先 (数据关键词 + 税种关键词 → financial_data)
Layer -1: 知识库优先 (操作/流程关键词 → regulation)
Layer  0: 企业数据查询 (纳税人名称匹配 或 时间+金额模式 → financial_data)
Layer  1: 税收优惠 (优惠关键词, 排除排除词 → tax_incentive)
Default:  regulation
```

### 5.3 配置热加载

配置文件 `config/tax_query_config.json` 支持基于文件修改时间的热加载，无需重启服务。

包含 12 个税种、优惠关键词、实体关键词、条件意图关键词、财务数据优先关键词、知识库优先关键词等。

---

## 6. 实体预处理模块

### 6.1 模块：`modules/entity_preprocessor.py`

四大功能：相对日期解析、实体提取、领域检测、同义词归一化。

### 6.2 相对日期解析

`_resolve_relative_dates(query, today)` 支持 20+ 种时间表达模式：

| 输入 | 输出 (假设今天 2026-02-20) |
|------|---------------------------|
| 今年3月 | 2026年3月 |
| 去年12月 | 2025年12月 |
| 上个月 | 2026年1月 |
| 上个季度 | 2025年10月到12月 |
| 最近3个月 | 2025年12月到2026年2月 |
| 去年全年 | 2025年全年 |
| 本月 (VAT 上下文) | 保持不变 |

### 6.3 实体提取

`detect_entities(user_query, db_conn)` 返回：

```python
{
    'taxpayer_id': str,           # 纳税人识别号
    'taxpayer_name': str,         # 纳税人名称
    'taxpayer_type': str,         # 一般纳税人/小规模纳税人
    'accounting_standard': str,   # 企业会计准则/小企业会计准则
    'period_year': int,
    'period_month': int,
    'period_quarter': int,
    'domain_hint': str,           # 领域提示
    'time_granularity': str,      # monthly/quarterly/yearly
    'cross_domain_list': list,    # 跨域领域列表
    'synonym_hits': list,         # 同义词命中
}
```

### 6.4 领域检测优先级

```
1. financial_metrics  (最高优先级: "财务指标", "毛利率", "ROE" 等)
2. cash_flow          (独特关键词: "现金流量", "经营活动现金" 等)
3. account_balance    (时间标记: "期初"/"期末"; 方向标记: "借"/"贷"/"发生额")
4. profit             (时间标记: "本期金额"/"本年累计"; 或月度默认)
5. balance_sheet      (时间标记: "年初"/"年末"; 或项目名称)
6. eit                (时间标记: "年度"/"季度"; 或关键词)
7. invoice            (含"发票"关键词; "进项发票"→purchase, "销项发票"→sales)
8. vat                (默认)
9. cross_domain 升级   (检测到多领域关键词时)
```

### 6.5 领域消歧规则

| 歧义场景 | 消歧规则 |
|----------|----------|
| 资产负债表 vs 科目余额 | "年初"→BS, "期初"→AB, "借"/"贷"→AB, 默认→BS |
| 利润表 vs 企业所得税 | "年度"/"季度"→EIT, "本期金额"/"本年累计"→profit, 默认→profit |
| 发票 vs 增值税 | "发票"→invoice, "进项税"→VAT |

### 6.6 同义词归一化

`normalize_query()` 使用最长匹配优先、非重叠替换策略：

1. 从数据库加载领域特定同义词表 (vat_synonyms, eit_synonyms, account_synonyms, fs_*_synonyms, inv_synonyms)
2. 按短语长度降序排列
3. 逐一替换，确保不重叠
4. 支持 scope_view 范围限定

### 6.7 视图路由

`get_scope_view(taxpayer_type, domain, report_type, accounting_standard)`:

| 领域 | 一般纳税人/企业会计准则 | 小规模纳税人/小企业会计准则 |
|------|----------------------|--------------------------|
| VAT | vw_vat_return_general | vw_vat_return_small |
| balance_sheet | vw_balance_sheet_eas | vw_balance_sheet_sas |
| profit | vw_profit_eas | vw_profit_sas |
| cash_flow | vw_cash_flow_eas | vw_cash_flow_sas |
| account_balance | vw_account_balance | vw_account_balance |
| invoice | vw_inv_spec_purchase / vw_inv_spec_sales | 同左 |

---

## 7. Stage 1：意图解析 (LLM)

### 7.1 模块：`modules/intent_parser.py`

`parse_intent(user_query, entities, synonym_hits)` 调用 LLM 将自然语言解析为结构化 JSON。

### 7.2 LLM 配置

- 模型：DeepSeek (`deepseek-chat`)
- Temperature：0.1 (接近确定性)
- Max tokens：2000
- 响应格式：JSON object

### 7.3 输出 Schema

```json
{
  "domain": "vat|eit|balance_sheet|profit|cash_flow|account_balance|financial_metrics|invoice|cross_domain",
  "need_clarification": false,
  "clarifying_questions": [],
  "select": {
    "metrics": ["output_tax", "input_tax"],
    "dimensions": ["period_year", "period_month"]
  },
  "filters": {
    "taxpayer_id": "91310000MA1FL8XQ30",
    "period_mode": "range",
    "period": {"start_year": 2025, "start_month": 1, "end_year": 2025, "end_month": 3}
  },
  "aggregation": {
    "group_by": ["period_month"],
    "order_by": ["period_month ASC"],
    "limit": 100
  },
  "vat_scope": {
    "views": ["vw_vat_return_general"],
    "item_type": "一般项目",
    "time_range": "累计"
  }
}
```

### 7.4 澄清触发条件

- 缺少纳税人类型 (无法确定视图)
- 缺少期间信息 (无法构建过滤条件)
- 注意：量词 ("各"/"每个"/"所有") 不触发澄清

---

## 8. 约束注入模块

### 8.1 模块：`modules/constraint_injector.py`

`inject_constraints(intent_json)` 从 Stage 1 输出派生 Stage 2 的约束条件。

### 8.2 输出

```python
{
    'allowed_views': ['vw_vat_return_general'],
    'allowed_columns': {'vw_vat_return_general': ['taxpayer_id', 'output_tax', ...]},
    'max_rows': 100,
    'allowed_views_text': "vw_vat_return_general",
    'allowed_columns_text': "vw_vat_return_general:\n  维度: ...\n  指标: ...",
    'intent_json_text': "<Stage 1 JSON>"
}
```

### 8.3 约束逻辑

- 跨域：合并所有子领域的视图
- 单领域：使用 `DOMAIN_VIEWS[domain]` 或 scope 指定的视图
- 列过滤：按领域维度集合过滤
- 行数限制：`min(intent.limit, MAX_ROWS)`

---

## 9. Stage 2：SQL 生成 (LLM)

### 9.1 模块：`modules/sql_writer.py`

`generate_sql(constraints, retry_feedback, domain)` 使用领域特定提示词模板调用 LLM 生成 SQL。

### 9.2 领域提示词映射

| 领域 | 提示词文件 |
|------|-----------|
| vat | stage2_vat.txt |
| eit | stage2_eit.txt |
| balance_sheet | stage2_balance_sheet.txt |
| profit | stage2_profit.txt |
| cash_flow | stage2_cash_flow.txt |
| account_balance | stage2_account_balance.txt |
| financial_metrics | stage2_financial_metrics.txt |
| invoice | stage2_invoice.txt |
| cross_domain | stage2_cross_domain.txt |

### 9.3 提示词通用结构

每个 Stage 2 提示词包含：

1. 角色定义：企业数据查询助手
2. 输出要求：只生成可执行的只读 SQLite SQL
3. 允许的视图白名单 (动态注入)
4. 允许的列白名单 (动态注入)
5. 强制过滤条件：taxpayer_id, 期间
6. 修订版本处理：`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY revision_no DESC)`
7. 输出规范：禁止 SELECT *，必须显式列名，必须 LIMIT

### 9.4 领域特殊规则

| 领域 | 特殊规则 |
|------|----------|
| VAT | item_type + time_range 维度过滤 |
| EIT | 年度 vs 季度分别处理，多季度用 WHERE IN |
| balance_sheet | `{item_code}_begin` / `{item_code}_end` 列命名 |
| profit / cash_flow | time_range 过滤 (本期 vs 本年累计) |
| account_balance | account_name LIKE 模式匹配子科目 |
| financial_metrics | period_type + metric_category + metric_code 过滤 |
| invoice | 方向过滤 (进项/销项)，聚合模式 |
| cross_domain | UNION ALL 策略，禁止跨视图 JOIN |

---

## 10. SQL 审计模块

### 10.1 模块：`modules/sql_auditor.py`

`audit_sql(sql, allowed_views, max_rows, domain)` 返回 `(passed: bool, violations: list)`。

### 10.2 审计规则 (10 条)

| # | 规则 | 说明 |
|---|------|------|
| 1 | 单语句 | 禁止中间分号 |
| 2 | 只读 | 仅允许 SELECT/WITH |
| 3 | 无危险关键词 | 禁止 INSERT/UPDATE/DELETE/DROP 等 |
| 4 | 视图白名单 | 只允许访问白名单视图 (CTE 例外) |
| 5 | 禁止 SELECT * | CTE 内部例外 |
| 6 | taxpayer_id 过滤 | 必须包含 |
| 7 | 期间过滤 | 领域感知 (EIT: period_quarter; 月度领域: period_month) |
| 8 | LIMIT 限制 | 必须有且 ≤ max_rows |
| 9 | 无危险函数 | 禁止 exec/system 等 |
| 10 | 领域特定检查 | EIT 季度视图需 period_quarter; 月度领域需 period_month |

### 10.3 重试流程

```
SQL 生成 → 审计 → 通过 → 执行
                → 失败 → 将违规信息反馈给 LLM → 重新生成 → 再次审计 → 通过/最终失败
```

---

## 11. 跨域查询系统

### 11.1 模块：`modules/cross_domain_calculator.py`

支持跨报表的数据对比、比率计算、勾稽校验和列举。

### 11.2 操作类型

| 操作 | 关键词 | 说明 |
|------|--------|------|
| compare | 对比/比较/差异 | 并排展示 + 差异/差异率 |
| ratio | 比重/占比/比率 | A/B 比率计算 |
| reconcile | 勾稽/一致/核对 | 一致性检查 (差异列) |
| list | 列举/汇总 | 简单合并 + _source_domain 标记 |

### 11.3 执行流程

```
跨域查询 → 拆分为子领域查询 → 并行 LLM SQL 生成 (ThreadPoolExecutor)
         → 串行执行各子查询 → 按操作类型合并结果
```

### 11.4 结果合并

- compare：按期间对齐，计算差异和差异率
- ratio：A/B 除法
- reconcile：差异列标记
- list：UNION ALL + _source_domain

---

## 12. 财务指标计算

### 12.1 模块：`modules/metric_calculator.py`

确定性计算 8 项财务比率，完全绕过 LLM。

### 12.2 支持的指标

| # | 指标 | 公式 | 单位 |
|---|------|------|------|
| 1 | 资产负债率 | total_liabilities / total_assets × 100 | % |
| 2 | 净资产收益率 (ROE) | net_profit / avg_equity × 100 | % |
| 3 | 毛利率 | (revenue - cost) / revenue × 100 | % |
| 4 | 总资产周转率 | revenue / avg_assets | 次 |
| 5 | 净利润率 | net_profit / revenue × 100 | % |
| 6 | 流动比率 | current_assets / current_liabilities | 倍 |
| 7 | 现金债务保障比率 | operating_cash / total_liabilities × 100 | % |
| 8 | 管理/销售费用率 | expense / revenue × 100 | % |

### 12.3 同义词映射

支持别名识别：`ROE` → `净资产收益率`，`负债率` → `资产负债率`

### 12.4 执行流程

```
查询 → detect_computed_metrics() → 匹配指标
     → 确定所需数据源领域 → 构建确定性 SQL → 执行
     → Python 公式求值 (安全 eval) → 返回结果
```

---

## 13. 概念注册表

### 13.1 模块：`modules/concept_registry.py`

40+ 预注册财务概念 → 确定性 SQL 构建，当检测到 ≥2 个概念 + 时间粒度时绕过 LLM。

### 13.2 概念分类

| 领域 | 概念示例 |
|------|----------|
| 发票 | 采购金额, 销售金额, 采购税额, 销售税额 |
| 增值税 | 销项税额, 进项税额, 增值税应纳税额, 留抵税额 |
| 资产负债表 | 货币资金, 应收账款, 存货, 固定资产, 总资产, 总负债, 所有者权益 |
| 利润表 | 营业收入, 营业成本, 营业利润, 利润总额, 净利润 |
| 现金流量表 | 经营活动现金流量净额, 投资活动现金流量净额, 筹资活动现金流量净额 |
| 企业所得税 | 应纳税所得额, 应纳所得税额, 实际利润额 |
| 计算型 | 存货增加额 (期末-期初), 应收账款变动额 |

### 13.3 季度聚合策略

| 策略 | 适用场景 | 说明 |
|------|----------|------|
| sum_months | 发票, VAT 本月数据 | 聚合 3 个月 |
| quarter_end | 资产负债表, 现金流量表本期, 利润表本期 | 取季末月 |

### 13.4 时间粒度检测

正则模式匹配：`各季度` → quarterly, `各月` → monthly, `各年` → yearly

### 13.5 执行流程

```
查询 → resolve_concepts() → 最长匹配优先提取概念
     → detect_time_granularity() → 检测时间粒度
     → 概念数 ≥ 2 且有时间粒度 → build_concept_sql() → 执行
     → merge_concept_results() → 按期间对齐合并
     → 失败 → 降级到 LLM 跨域路径
```

---

## 14. 缓存系统

### 14.1 模块：`modules/cache_manager.py`

四级 LRU 缓存，线程安全 (threading.Lock)。

### 14.2 缓存层级

| 层级 | 缓存内容 | 容量 | TTL | Key 构成 |
|------|----------|------|-----|----------|
| L1 | Stage 1 意图 | 500 | 30min | MD5(normalized_query + taxpayer_type + synonym_hits) |
| L2 | Stage 2 SQL | 500 | 1hr | MD5(intent_json + allowed_views + allowed_columns) |
| L3 | SQL 执行结果 | 200 | 30min | MD5(sql + params) |
| L4 | 跨域结果 | 100 | 30min | MD5(query + taxpayer_id + cross_list + period_key) |

### 14.3 实现

基于 `OrderedDict` 的 LRU 淘汰策略，每次访问移至末尾，超容量时淘汰头部。TTL 过期检查在 get 时执行。

### 14.4 统计接口

`get_cache_stats()` 返回各层级的命中/未命中次数和命中率。

---

## 15. Schema 白名单

### 15.1 模块：`modules/schema_catalog.py`

系统的单一事实来源 (Single Source of Truth)，定义领域→视图→列的映射关系。

### 15.2 核心数据结构

- `DOMAIN_VIEWS` — 领域 → 允许的视图列表
- `VIEW_COLUMNS` — 视图 → 允许的列列表
- `DENIED_KEYWORDS` — 危险 SQL 关键词 (INSERT, UPDATE, DELETE, DROP 等)
- `DENIED_FUNCTIONS` — 危险函数 (exec, system 等)
- `SYSTEM_TABLES` — 系统表 (sqlite_master 等)

### 15.3 维度列集合 (按领域)

| 领域 | 维度列 |
|------|--------|
| VAT | taxpayer_id, period_year, period_month, item_type, time_range, revision_no |
| EIT (年度) | filing_id, taxpayer_id, period_year, revision_no |
| EIT (季度) | filing_id, taxpayer_id, period_year, period_quarter, revision_no |
| account_balance | taxpayer_id, period_year, period_month, account_code, account_name, level, category, balance_direction |
| balance_sheet | taxpayer_id, period_year, period_month, accounting_standard_name |
| profit | taxpayer_id, period_year, period_month, time_range, accounting_standard_name |
| cash_flow | taxpayer_id, period_year, period_month, time_range, accounting_standard |
| financial_metrics | taxpayer_id, period_year, period_month, metric_name, metric_code, metric_category |
| invoice | taxpayer_id, period_year, period_month, invoice_pk, line_no, invoice_format |

### 15.4 动态列生成

资产负债表视图列通过 `_bs_view_columns()` 从项目代码动态生成：ASBE 67 项 × 2 (begin/end) = 134 列，ASSE 53 项 × 2 = 106 列。

---

## 16. 数据库层

### 16.1 数据库文件

| 文件 | 说明 |
|------|------|
| `database/fintax_ai.db` | 主数据库 (SQLite) |
| `database/tax_incentives.db` | 税收优惠政策库 (1522 条, FTS5 索引) |

### 16.2 表结构总览

#### 主维度表

**taxpayer_info** (PK: taxpayer_id)

| 列 | 类型 | 说明 |
|----|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| taxpayer_name | TEXT | 纳税人名称 |
| taxpayer_type | TEXT | 一般纳税人/小规模纳税人 |
| accounting_standard | TEXT | 企业会计准则/小企业会计准则 |
| registration_type | TEXT | 登记注册类型 |
| legal_representative | TEXT | 法定代表人 |
| establish_date | TEXT | 成立日期 |
| industry_code / industry_name | TEXT | 行业代码/名称 |
| tax_authority_code / tax_authority_name | TEXT | 税务机关 |
| region_code / region_name | TEXT | 地区 |
| credit_grade_current / credit_grade_year | TEXT | 纳税信用等级 |
| status | TEXT | active/inactive |

#### 增值税表

**vat_return_general** (PK: taxpayer_id, period_year, period_month, item_type, time_range, revision_no)
- 41 个指标列：sales_taxable_rate, output_tax, input_tax, transfer_out, tax_payable 等
- item_type: 一般项目 / 即征即退项目
- time_range: 本月 / 累计

**vat_return_small** (PK: 同上)
- 25 个指标列：sales_3percent, sales_5percent, tax_due_total 等
- item_type: 货物及劳务 / 服务不动产无形资产
- time_range: 本期 / 累计

#### 企业所得税表

**eit_annual_filing** → **eit_annual_main** (1:1, FK: filing_id)
- 45 列：revenue, cost, taxes_surcharges, operating_profit, total_profit, taxable_income, tax_payable 等

**eit_quarter_filing** → **eit_quarter_main** (1:1, FK: filing_id)
- 28 列：revenue, cost, total_profit, actual_profit, tax_rate, tax_payable 等

#### 科目余额表

**account_master** (PK: account_code) — 科目字典
**account_balance** (PK: taxpayer_id, period_year, period_month, account_code, revision_no)
- opening_balance, debit_amount, credit_amount, closing_balance

#### 财务报表 (EAV 纵表存储)

三张报表采用统一的 EAV 存储模式：

| 表 | PK | 值列 |
|----|-----|------|
| fs_balance_sheet_item | (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no) | beginning_balance, ending_balance |
| fs_income_statement_item | 同上 | current_amount, cumulative_amount |
| fs_cash_flow_item | 同上 | current_amount, cumulative_amount |

每张表配套：
- `*_item_dict` — 项目字典 (gaap_type + item_code → item_name)
- `*_synonyms` — 同义词映射 (phrase → column_name)

#### 发票表 (宽表存储)

**inv_spec_purchase** (PK: taxpayer_id, invoice_pk, line_no)
- 34 列，含商品明细 (goods_name, specification, unit, quantity, unit_price, tax_rate)

**inv_spec_sales** (PK: 同上)
- 26 列，无商品明细

#### 财务指标表

**financial_metrics_item** (PK: taxpayer_id, period_year, period_month, period_type, metric_code)
- 18 项预计算指标 (盈利能力/偿债能力/营运能力/成长能力/现金流/税负率/风险预警)

#### 日志表

**user_query_log** — 查询日志
**unmatched_phrases** — 未匹配短语 (用于持续优化同义词表)
**etl_error_log** — ETL 错误日志

### 16.3 视图设计

#### EAV → 宽表透视

资产负债表、利润表、现金流量表均采用 EAV 纵表存储 + 视图透视为宽表的设计：

```sql
-- 资产负债表视图示例 (vw_balance_sheet_eas)
SELECT t.taxpayer_id, t.taxpayer_name, b.period_year, b.period_month,
       MAX(CASE WHEN b.item_code='A001' THEN b.ending_balance END) AS A001_end,
       MAX(CASE WHEN b.item_code='A001' THEN b.beginning_balance END) AS A001_begin,
       ...
FROM fs_balance_sheet_item b
JOIN taxpayer_info t ON b.taxpayer_id = t.taxpayer_id
WHERE b.gaap_type = 'ASBE'
GROUP BY b.taxpayer_id, b.period_year, b.period_month
```

利润表和现金流量表额外使用 `CROSS JOIN` 引入 `time_range` 维度 (本期/本年累计)。

#### 双准则路由

| 准则 | 资产负债表 | 利润表 | 现金流量表 |
|------|-----------|--------|-----------|
| 企业会计准则 (ASBE/CAS) | vw_balance_sheet_eas (67项) | vw_profit_eas (42项) | vw_cash_flow_eas (35项) |
| 小企业会计准则 (ASSE/SAS) | vw_balance_sheet_sas (53项) | vw_profit_sas (32项) | vw_cash_flow_sas (22项) |

#### 修订版本处理

所有视图使用 `ROW_NUMBER()` 窗口函数取最新修订版本：

```sql
ROW_NUMBER() OVER (
    PARTITION BY taxpayer_id, period_year, period_month
    ORDER BY revision_no DESC
) AS rn
-- WHERE rn = 1
```

### 16.4 索引策略

| 类别 | 索引数量 | 说明 |
|------|----------|------|
| 主键索引 | 自动 | SQLite 自动为 PK 创建 |
| 复合查询索引 | 7+ | taxpayer_period_revision 组合 |
| 维度过滤索引 | 5+ | taxpayer_type, industry_code 等 |
| 日志索引 | 3+ | created_at, success, taxpayer |

### 16.5 样本数据

| 纳税人 | 类型 | 会计准则 | 数据范围 |
|--------|------|----------|----------|
| 华兴科技有限公司 (91310000MA1FL8XQ30) | 一般纳税人 | 企业会计准则 | 2024.01-2026.02 |
| 鑫源贸易商行 (92440300MA5EQXL17P) | 小规模纳税人 | 小企业会计准则 | 2024.01-2026.02 |

扩展数据生成策略：基准月 2025-01，月增长率 2%，季节性振幅 5-8% (正弦波)。

### 16.6 预计算财务指标 (18 项)

| 类别 | 指标 |
|------|------|
| 盈利能力 | 毛利率, 净利率, ROE |
| 偿债能力 | 资产负债率, 流动比率, 速动比率 |
| 营运能力 | 应收账款周转率, 存货周转率 |
| 成长能力 | 营业收入增长率 |
| 现金流 | 销售收现比 |
| 税负率 | 增值税税负率, 企业所得税税负率, 综合税负率 |
| 增值税指标 | 销项进项配比率, 进项税额转出占比 |
| 所得税指标 | 应税所得率 |
| 风险预警 | 零申报率 |

---

## 17. API 层 (FastAPI)

### 17.1 入口：`api/main.py`

- 自动初始化数据库 (如果 DB 文件不存在)
- CORS 配置：允许 localhost:5173 (React 开发服务器)
- 静态文件服务：`frontend/dist/` (生产环境)
- 注册三个路由模块：chat, history, company

### 17.2 API 端点

#### POST /api/chat — SSE 流式聊天

请求体 (`ChatRequest`):
```json
{
  "query": "华兴科技2025年1月销项税额是多少",
  "response_mode": "detailed",    // concise | standard | detailed
  "company_id": "91310000MA1FL8XQ30"  // 可选
}
```

响应：`text/event-stream`，三种事件类型：

```
event: stage
data: {"route": "financial_data", "text": "正在查询财务数据..."}

event: chunk
data: {"text": "根据查询结果..."}

event: done
data: {"success": true, "result": {...}, "display_data": {...}}
```

处理流程：
1. 根据 company_id 查询纳税人名称
2. 将公司名称前缀拼接到查询 (用于 NL2SQL 纳税人识别)
3. 传递 `original_query` (原始用户输入) 给管线 (避免公司名称污染税收优惠/法规搜索)
4. 包装 `run_pipeline_stream()` 为 SSE
5. 对 financial_data 路线结果附加 `display_data` (通过 `build_display_data()`)

#### GET /api/companies — 纳税人列表

响应：
```json
[
  {"taxpayer_id": "91310000MA1FL8XQ30", "taxpayer_name": "华兴科技有限公司", "taxpayer_type": "一般纳税人"},
  {"taxpayer_id": "92440300MA5EQXL17P", "taxpayer_name": "鑫源贸易商行", "taxpayer_type": "小规模纳税人"}
]
```

#### GET /api/chat/history — 获取历史

查询参数：`limit` (默认 100)
存储：`query_history.json` (线程安全, 最多 100 条)

#### POST /api/chat/history — 保存历史

请求体：历史条目 (query, status, main_output, entity_text, intent_text, sql_text, route, result_count, timestamp)

#### DELETE /api/chat/history — 删除历史

请求体：`{"ids": [0, 2, 5]}` 或空 ids 清空全部

### 17.3 Pydantic 模型 (`api/schemas.py`)

```python
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    response_mode: str = "detailed"
    company_id: Optional[str] = None

class HistoryDeleteRequest(BaseModel):
    ids: List[int] = []

class CompanyItem(BaseModel):
    taxpayer_id: str
    taxpayer_name: str
    taxpayer_type: str
```

---

## 18. 前端 (React SPA)

### 18.1 技术栈

- React 18 + Vite
- CSS Modules
- Chart.js (图表)
- SSE 流式通信

### 18.2 组件架构

```
App.jsx
├── Header/           # 顶部导航 (公司下拉框, 实时时钟, 用户信息)
├── Sidebar/          # 侧边栏
├── ChatArea/         # 主聊天区域
│   ├── ChatMessage/  # 消息渲染 (路线徽章, 响应模式, 管线详情)
│   ├── ResultTable/  # 表格展示
│   ├── ChartRenderer/ # Chart.js 图表
│   ├── GrowthTable/  # 增长分析表
│   └── PipelineDetail/ # 管线详情 (实体/意图/SQL)
├── ChatInput/        # 输入框
├── HistoryPanel/     # 历史面板
└── Footer/           # 底部
```

### 18.3 SSE 通信

**useSSE Hook** (`hooks/useSSE.js`):
- `startStream()` — 发起 fetch + AbortController，解析 SSE 事件
- `cancel()` — 中止流
- 状态：`isStreaming` boolean

**SSE Parser** (`utils/sseParser.js`):
- 异步生成器解析 ReadableStream
- 处理不完整行、UTF-8 解码
- 产出 `{event, data}` 对象

### 18.4 消息渲染

**路线徽章**：
- financial_data: 📊
- tax_incentive: 📋
- regulation: 🤖

**响应模式**：
| 模式 | 展示内容 |
|------|----------|
| concise | 仅文本摘要 |
| standard | 表格 + 增长分析 |
| detailed | 表格 + 图表 + 增长分析 |

**展示类型**：
| 类型 | 触发条件 | 布局 |
|------|----------|------|
| kv | 单行, ≤8 列 | 键值对列表 |
| table | 多行 | Markdown 表格 + 可选图表 |
| metric | 财务指标 | 指标卡片 + 计算依据 |
| cross_domain | 跨域查询 | 子领域分组 + 独立图表 |

### 18.5 API 服务 (`services/api.js`)

```javascript
fetchCompanies()              // GET /api/companies
fetchHistory(limit)           // GET /api/chat/history
saveHistoryEntry(entry)       // POST /api/chat/history
deleteHistory(ids)            // DELETE /api/chat/history
chatStream(query, signal, options) // POST /api/chat (SSE)
```

### 18.6 数据流

```
用户输入 → chatStream() → POST /api/chat
         → SSE 事件流 → parseSSE() → ChatArea 状态更新
         → ChatMessage 渲染 (根据 route + response_mode + display_type)
         → 保存历史 saveHistoryEntry()
```

---

## 19. 展示格式化模块

### 19.1 模块：`modules/display_formatter.py`

将查询结果转换为 React 前端可消费的结构化 JSON。

### 19.2 ColumnMapper 单例

延迟加载列名→中文业务名称映射：
- 数据源：所有 `*_column_mapping` 表、项目字典表、发票映射表
- 5 级回退：精确视图 → 领域视图 → 通用 → 跨域前缀 → 原始名

### 19.3 数字格式化

```
≥ 1亿  → "X.XX亿"
≥ 1万  → "X.XX万"
< 1万  → "1,234.50" (千分位)
百分比 → "X.XX%" (通过列名后缀检测: _rate, _ratio)
整数列 → 原样显示 (period_year, quantity 等)
None   → "-"
0      → "0.00"
```

### 19.4 build_display_data() 输出

```json
{
  "display_type": "kv|table|metric|cross_domain",
  "table": {
    "headers": ["纳税人名称", "期间", "销项税额"],
    "rows": [["华兴科技", "2025-01", "12.34万"]],
    "columns": ["taxpayer_name", "period", "output_tax"]
  },
  "chart_data": {
    "type": "bar",
    "labels": ["2025-01", "2025-02", "2025-03"],
    "datasets": [{"label": "销项税额", "data": [123400, 125600, 128900]}]
  },
  "growth": [
    {"period": "2025-02", "output_tax": {"current": 125600, "previous": 123400, "change": 2200, "change_pct": 1.78, "trend": "up"}}
  ],
  "summary": "华兴科技2025年1-3月销项税额呈上升趋势"
}
```

### 19.5 图表生成

- Chart.js 兼容格式
- 多期间数据 → 柱状图 + 可选增长率折线 (组合图)
- 最多 6 个指标
- 支持双 Y 轴 (百分比指标)

---

## 20. 税收优惠查询模块

### 20.1 模块：`modules/tax_incentive_query.py`

搜索本地 `tax_incentives.db` (1522 条政策, FTS5 索引)。

### 20.2 四级渐进搜索

| 级别 | 策略 | 说明 |
|------|------|------|
| 1 | 结构化搜索 | tax_type + entity LIKE (AND) |
| 2 | 实体搜索 | 跨税种 entity LIKE (AND) |
| 3 | 关键词 LIKE | 多字段 AND 匹配 (主力策略) |
| 4 | FTS5 全文搜索 | 兜底 (unicode61 分词器对中文子串匹配有限) |

### 20.3 意图解析

纯正则 (无 LLM)：从配置驱动的词表中提取 tax_type, entity_keywords, search_keywords。

### 20.4 LLM 摘要

将 Top 10 结果发送给 DeepSeek 生成摘要。失败时降级为简单列表。

### 20.5 流式接口

- `search()` — 非流式，返回完整结果
- `search_stream()` — 流式，yield (chunk_text, is_done, result_dict)

---

## 21. 外部法规知识库

### 21.1 模块：`modules/regulation_api.py`

通过 Coze RAG API (SSE 流式) 查询法规/操作指南。

### 21.2 接口

- `query_regulation(question)` — 非流式
- `query_regulation_stream(question)` — 流式，yield (chunk_text, is_done, result_dict)

### 21.3 技术要点

- UTF-8 编码修复：`resp.encoding = 'utf-8'` (requests 对 text/event-stream 默认 ISO-8859-1)
- 卡片模板过滤：过滤 JSON 中的 `card_type` 字段
- HTTP 200 错误检测：检测非 SSE 格式的 JSON 错误体

### 21.4 Coze API 配置

```python
COZE_API_URL = "https://api.coze.cn/v3/chat"
COZE_PAT_TOKEN = "pat_..."
COZE_BOT_ID = "7592905400907989034"
COZE_TIMEOUT = 180  # 秒
```

---

## 22. LLM Prompt 体系

### 22.1 Stage 1 提示词 (`stage1_system.txt`)

角色：企业数据查询意图解析助手
输出：严格 JSON (无 markdown 包裹)

关键指令：
- 10 个领域识别 (含 48 级优先级)
- 双准则路由 (ASBE/ASSE, CAS/SAS)
- 共享项目消歧 (如 "应收账款" 默认→balance_sheet, 含 "期初"/"借"/"贷"→account_balance)
- VAT 上下文保护 ("本月" 不替换)
- 澄清触发规则
- 默认行为 (VAT→累计, EIT→annual, profit→本年累计)

### 22.2 Stage 2 提示词通用模板

```
角色：企业数据查询助手
输出：只生成可执行的只读 SQLite SQL

允许访问的视图：{allowed_views}
允许访问的列：{allowed_columns}

强制过滤：
- taxpayer_id = :taxpayer_id
- 期间过滤 (领域特定)

修订版本处理：
- ROW_NUMBER() OVER (PARTITION BY ... ORDER BY revision_no DESC)
- WHERE rn = 1

输出规范：
- 禁止 SELECT *
- 显式列名
- LIMIT {max_rows}
```

### 22.3 领域特定提示词要点

| 领域 | 特殊指令 |
|------|----------|
| VAT | item_type + time_range 维度；4 行/纳税人/月 |
| EIT | 年度 vs 季度分别处理；多季度 WHERE IN |
| balance_sheet | `{item_code}_begin/_end` 列命名；会计等式验证 |
| profit / cash_flow | time_range 过滤 (本期 vs 本年累计)；2 行/月 |
| account_balance | account_name LIKE 子科目匹配 |
| financial_metrics | period_type + metric_category + metric_code |
| invoice | 方向过滤 (进项/销项)；聚合模式 (SUM/COUNT) |
| cross_domain | UNION ALL 策略；禁止跨视图 JOIN |

---

## 23. 配置系统

### 23.1 主配置 (`config/settings.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| DB_PATH | database/fintax_ai.db | SQLite 数据库路径 |
| PROMPTS_DIR | prompts/ | 提示词目录 |
| LLM_API_KEY | sk-... | DeepSeek API Key |
| LLM_API_BASE | https://api.deepseek.com | API 基础 URL |
| LLM_MODEL | deepseek-chat | 模型名称 |
| LLM_MAX_RETRIES | 3 | LLM 调用重试次数 |
| LLM_TIMEOUT | 60 | LLM 调用超时 (秒) |
| MAX_ROWS | 1000 | 查询结果最大行数 |
| MAX_PERIOD_MONTHS | 36 | 最大查询期间 (月) |
| CACHE_ENABLED | True | 缓存总开关 |
| CACHE_MAX_SIZE_INTENT | 500 | 意图缓存容量 |
| CACHE_TTL_INTENT | 1800 | 意图缓存 TTL (秒) |
| CACHE_MAX_SIZE_SQL | 500 | SQL 缓存容量 |
| CACHE_TTL_SQL | 3600 | SQL 缓存 TTL (秒) |
| CACHE_MAX_SIZE_RESULT | 200 | 结果缓存容量 |
| CACHE_TTL_RESULT | 1800 | 结果缓存 TTL (秒) |
| CACHE_MAX_SIZE_CROSS | 100 | 跨域缓存容量 |
| CACHE_TTL_CROSS | 1800 | 跨域缓存 TTL (秒) |
| TAX_INCENTIVES_DB_PATH | database/tax_incentives.db | 税收优惠库路径 |
| COZE_API_URL | https://api.coze.cn/v3/chat | Coze API URL |
| COZE_PAT_TOKEN | pat_... | Coze 认证令牌 |
| COZE_BOT_ID | 7592905400907989034 | Coze Bot ID |
| COZE_TIMEOUT | 180 | Coze 超时 (秒) |
| ROUTER_ENABLED | True | 意图路由总开关 |

### 23.2 意图路由配置 (`config/tax_query_config.json`)

热加载配置，包含：
- 12 个税种名称
- 优惠关键词 (15 个)
- 核心实体关键词 (8 个)
- 条件意图关键词 (15 个)
- 财务数据优先关键词 (16 个)
- 知识库优先关键词 (25+ 个)

### 23.3 Python 依赖 (`requirements.txt`)

```
openai>=1.0.0          # LLM API 客户端
gradio==4.44.1         # 遗留前端
huggingface-hub<0.25   # Gradio 依赖
fastapi>=0.115.0       # REST API 框架
uvicorn[standard]>=0.30.0  # ASGI 服务器
```

---

## 24. 测试体系

### 24.1 测试套件总览

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| run_tests.py | 5 | 基础管线功能 |
| test_real_scenarios.py | 46 | 日期解析/领域检测/端到端 |
| test_comprehensive.py | 57 | 9 领域 × 单域/跨域 (~96% 通过率) |
| test_cache.py | - | 缓存有效性验证 |
| test_performance.py | - | 性能基准 |
| tests/test_bs.py | 11+ | 资产负债表特性 |
| tests/test_display_formatter.py | 20+ | 展示格式化 |
| tests/test_concept_registry.py | 15+ | 概念注册表 |
| **合计** | **111+** | **~96% 通过率** |

### 24.2 基础管线测试 (`run_tests.py`)

5 个核心用例：
1. T1: 单字段查询 (VAT, 一般纳税人)
2. T2: 趋势查询 (3 个月)
3. T3: 缺少期间 → 触发澄清
4. T4: 小规模纳税人查询
5. T5: 多字段查询 + 修订版本处理

测试前重建数据库 (init_database → seed_reference_data → insert_sample_data)。

### 24.3 真实场景测试 (`test_real_scenarios.py`)

46 个用例，6 大类：
1. 相对日期解析 (6 例)
2. 领域检测 (6 例)
3. 指标检测 (4 例)
4. 跨域操作 (4 例)
5. 端到端管线 (26 例: VAT 3 + EIT 2 + AB 3 + BS 4 + Profit 4 + CF 3)

### 24.4 综合测试 (`test_comprehensive.py`)

57 个用例：
- 单域测试 (27 例): 9 领域 × 3 例
- 跨域测试 (30 例): 单指标单期 10 + 单指标多期 10 + 多指标多期 10

### 24.5 验证模式

```python
# 管线成功
assert result.get('success') == True
assert result.get('error') is None
assert result.get('clarification') is None

# 领域检测 (允许实体预处理器或 LLM 意图匹配)
detected_domain = intent.get('domain') or entities.get('domain_hint')

# 行数验证
if tc['min_rows'] > 0:
    assert len(results_data) >= tc['min_rows']

# 缓存效果
assert improvement > 90%  # "excellent"
```

### 24.6 运行命令

```bash
# 基础测试
python run_tests.py

# 真实场景测试
python test_real_scenarios.py

# 综合测试
python test_comprehensive.py

# 缓存测试
python test_cache.py

# 性能测试
python test_performance.py

# 单元测试
python -m unittest tests.test_bs
python -m pytest tests/test_display_formatter.py -v
python -m pytest tests/test_concept_registry.py -v
```

---

## 25. 部署与运维

### 25.1 环境要求

- Python 3.10+
- Node.js 18+ (前端构建)
- SQLite 3.35+ (窗口函数支持)

### 25.2 安装步骤

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 初始化数据库 (可选, app 启动时自动执行)
python -c "from database.init_db import init_database; init_database()"
python -c "from database.seed_data import seed_reference_data; seed_reference_data()"
python -c "from database.sample_data import insert_sample_data; insert_sample_data()"

# 3. 添加性能索引
python database/add_performance_indexes.py

# 4. 计算财务指标
python database/calculate_metrics.py

# 5. 构建前端 (如需修改)
cd frontend && npm install && npm run build

# 6. 启动服务
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 25.3 环境变量

需要在 `config/settings.py` 中配置：
- `LLM_API_KEY` — DeepSeek API Key
- `COZE_PAT_TOKEN` — Coze RAG API 令牌

### 25.4 数据库维护

```bash
# 数据变更后重新计算指标
python database/calculate_metrics.py

# 查看未匹配短语 (用于优化同义词表)
sqlite3 database/fintax_ai.db "SELECT phrase, frequency FROM unmatched_phrases WHERE status='pending' ORDER BY frequency DESC"
```

### 25.5 监控要点

| 指标 | 来源 | 说明 |
|------|------|------|
| 查询成功率 | user_query_log.success | 目标 ≥ 95% |
| 平均响应时间 | user_query_log.execution_time_ms | 目标 < 5s |
| 缓存命中率 | cache_manager.get_cache_stats() | 目标 > 50% |
| 未匹配短语 | unmatched_phrases | 定期审查并补充同义词 |
| LLM 调用量 | 按日统计 | 成本控制 |

---

## 附录 A：数据流全景图

```
用户提问
    │
    ▼
┌─────────────────┐
│  React Frontend  │ ← SSE 事件流
│  POST /api/chat  │
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│  Intent Router   │────→│ Tax Incentive DB  │ (1522 政策)
│  (3路分类)       │────→│ Coze RAG API      │ (法规知识库)
│                  │────→│ NL2SQL Pipeline ↓ │
└────────┬────────┘     └──────────────────┘
         │
    ▼
┌─────────────────┐
│ Entity Preproc.  │ 日期解析 → 实体提取 → 领域检测 → 同义词归一化
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ Path Selection   │────→│ Metric Calculator │ (8 指标, 无LLM)
│                  │────→│ Concept Registry  │ (40+ 概念, 无LLM)
│                  │────→│ Cross-Domain      │ (并行LLM)
│                  │────→│ Standard Path ↓   │ (两阶段LLM)
└────────┬────────┘     └──────────────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ Stage 1 (LLM)   │────→│ 结构化意图 JSON    │
│ Intent Parser    │     └──────────────────┘
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ Constraint Inj.  │────→│ 视图/列/行数约束    │
└────────┬────────┘     └──────────────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ Stage 2 (LLM)   │────→│ SQLite SQL        │
│ SQL Writer       │     └──────────────────┘
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ SQL Auditor      │────→│ 10 条审计规则      │
│ (失败重试1次)    │     └──────────────────┘
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ SQL Execution    │────→│ SQLite 参数化查询   │
│ (失败重试1次)    │     └──────────────────┘
└────────┬────────┘
         │
    ▼
┌─────────────────┐     ┌──────────────────┐
│ Display Format   │────→│ 结构化 JSON        │
│ + Chart Data     │     │ (表格/图表/增长)    │
└────────┬────────┘     └──────────────────┘
         │
    ▼
  SSE → React 渲染
```

---

## 附录 B：关键设计决策汇总

| # | 决策 | 理由 |
|---|------|------|
| 1 | 两阶段 LLM 管线 | 分离意图理解和 SQL 生成，提高可控性和可审计性 |
| 2 | EAV 纵表 + 视图透视 | 灵活适应不同会计准则的项目差异 |
| 3 | 双准则路由 | 企业会计准则和小企业会计准则的项目集不同 |
| 4 | 确定性计算路径 | 指标和概念路径绕过 LLM，提高准确性和速度 |
| 5 | 四级缓存 | 减少 LLM 调用和 SQL 执行开销 |
| 6 | 最长匹配优先同义词 | 避免短词误匹配 |
| 7 | SQL 审计 + 重试 | 安全防护 + 容错 |
| 8 | UNION ALL 跨域 | 避免 SQLite JOIN 限制 |
| 9 | 三路意图路由 | 分流不同类型查询到最适合的处理引擎 |
| 10 | 路由感知查询隔离 | 避免公司名称污染关键词搜索 |
| 11 | 热加载配置 | 无需重启即可调整路由规则 |
| 12 | SSE 流式输出 | 提升用户体验，实时反馈 |
| 13 | 发票双表设计 | 进项含商品明细，销项不含 |
| 14 | 修订版本窗口函数 | 自动取最新版本，支持历史追溯 |

---

> 文档结束 | fintax_ai v2.0 | 2026-02-20
