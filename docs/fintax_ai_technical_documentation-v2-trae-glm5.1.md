# FinTax AI — 项目详细技术文档

> 基于源代码脚本分析生成，更新日期：2026-04-21

---

## 一、技术栈概览

| 层级 | 技术 | 版本/说明 |
|------|------|-----------|
| 后端框架 | FastAPI | ≥0.115.0 |
| ASGI 服务器 | Uvicorn | ≥0.30.0 |
| 数据库 | SQLite | 内置，WAL 模式 |
| ORM | 无 | 原生 sqlite3 + SQL |
| LLM | DeepSeek API | deepseek-chat (DeepSeek-V3)，OpenAI 兼容接口 |
| 外部知识库 | Coze RAG API | 法规知识库 |
| 认证 | JWT (PyJWT) + bcrypt | HS256，24h 有效期 |
| 前端框架 | React | Vite 构建 |
| 前端通信 | SSE (Server-Sent Events) | 流式输出 |
| 数据验证 | Pydantic | ≥2.0.0 |
| HTTP 客户端 | requests / openai | ≥2.28.0 / ≥1.0.0 |

---

## 二、项目目录结构

```
fintax_ai/
├── api/                          # 后端 API 层
│   ├── main.py                   # FastAPI 入口，路由注册，SPA 服务
│   ├── auth.py                   # JWT 认证工具，角色权限，企业数据隔离
│   ├── schemas.py                # Pydantic 请求/响应模型
│   ├── routes/                   # API 路由
│   │   ├── auth.py               # 认证路由（登录/登出/验证码）
│   │   ├── chat.py               # SSE 流式对话路由（核心）
│   │   ├── history.py            # 历史记录路由
│   │   ├── company.py            # 企业列表路由
│   │   ├── profile.py            # 企业画像路由
│   │   ├── profile_report.py     # 画像报告路由
│   │   ├── data_management.py    # 数据管理路由
│   │   ├── data_browser.py       # 数据浏览路由
│   │   ├── interpret.py          # 数据解读路由
│   │   ├── dashboard.py          # 仪表盘路由
│   │   ├── cache_stats.py        # 缓存统计路由
│   │   └── users.py              # 用户管理路由
│   └── services/                 # 业务服务层
│       ├── query_cache.py        # L1 精确缓存（文件持久化）
│       ├── template_cache.py     # L2 模板缓存（域感知）
│       ├── query_path_logger.py  # 查询路径日志
│       ├── dashboard_service.py  # 仪表盘服务
│       ├── data_quality.py       # 数据质量检查引擎
│       ├── data_update_service.py# 数据更新服务
│       └── view_adapter.py       # 视图适配器（已废弃）
├── modules/                      # 核心业务模块
│   ├── intent_parser.py          # 阶段1：LLM 意图解析
│   ├── intent_router.py          # 意图路由器（三路由分流）
│   ├── sql_writer.py             # 阶段2：LLM SQL 生成
│   ├── sql_auditor.py            # SQL 安全审核器
│   ├── entity_preprocessor.py    # 实体预处理器
│   ├── concept_registry.py       # 概念注册表（确定性 SQL）
│   ├── constraint_injector.py    # 约束注入器
│   ├── schema_catalog.py         # 静态白名单目录
│   ├── display_formatter.py      # 展示格式化器
│   ├── interpretation_service.py # LLM 数据解读服务
│   ├── cache_manager.py          # 内存缓存（已弃用）
│   ├── conversation_manager.py   # 对话上下文管理器
│   ├── cross_domain_calculator.py# 跨域计算引擎
│   ├── metric_calculator.py      # 计算指标引擎
│   ├── mixed_analysis_detector.py# 混合分析检测器
│   ├── mixed_analysis_executor.py# 混合分析执行器
│   ├── profile_service.py        # 企业画像数据聚合
│   ├── profile_report_service.py # 画像报告生成服务
│   ├── regulation_api.py         # 外部法规查询（Coze RAG）
│   ├── tax_incentive_query.py    # 税收优惠查询
│   └── db_utils.py               # 统一数据库连接工厂
├── config/                       # 配置文件
│   ├── settings.py               # 全局配置常量
│   ├── config_loader.py          # 统一配置加载工具
│   ├── pipeline/                 # 管线配置
│   │   ├── domain_prompt_map.json# 域→提示词模板映射
│   │   └── time_patterns.json    # 时间粒度正则模式
│   ├── domain_detection/         # 域检测关键词配置（8个域）
│   ├── concepts/                 # 概念映射配置（7个域）
│   ├── schema/                   # Schema 白名单配置
│   │   ├── domain_views.json     # 域→允许视图映射
│   │   ├── view_columns.json     # 视图→允许列映射
│   │   ├── security_blacklists.json # SQL 危险关键字/函数
│   │   └── dimension_columns.json# 各域维度列定义
│   ├── metrics/                  # 指标公式配置
│   │   └── metric_formulas.json  # 指标公式+同义词+已知率型指标
│   ├── profile/                  # 画像评价规则
│   │   └── evaluation_rules.json # 9大指标评价阈值
│   ├── auth/                     # 认证配置
│   │   ├── roles.json            # 角色定义+权限矩阵
│   │   └── seed_users.json       # 种子用户
│   ├── data_management/          # 数据管理配置
│   │   └── domain_config.json    # 域→物理表映射+质量检查项
│   ├── display/                  # 展示常量
│   │   └── display_constants.json# 隐藏列+中文映射+百分比列
│   ├── analysis/                 # 分析配置
│   │   └── mixed_analysis_keywords.json # 混合分析关键词
│   ├── cross_domain/             # 跨域配置
│   │   └── operation_keywords.json # 跨域操作关键词
│   ├── tax_query_config.json     # 税收优惠查询配置
│   └── tax_search_keywords.json  # 税收搜索关键词
├── prompts/                      # LLM 提示词模板
│   ├── stage1_system.txt         # 阶段1：意图解析提示词
│   ├── stage2_vat.txt            # 阶段2：增值税 SQL 生成
│   ├── stage2_eit.txt            # 阶段2：企业所得税 SQL 生成
│   ├── stage2_balance_sheet.txt  # 阶段2：资产负债表 SQL 生成
│   ├── stage2_profit.txt         # 阶段2：利润表 SQL 生成
│   ├── stage2_cash_flow.txt      # 阶段2：现金流量表 SQL 生成
│   ├── stage2_account_balance.txt# 阶段2：科目余额表 SQL 生成
│   ├── stage2_financial_metrics.txt # 阶段2：财务指标 SQL 生成
│   ├── stage2_invoice.txt        # 阶段2：发票 SQL 生成
│   ├── stage2_cross_domain.txt   # 阶段2：跨域 SQL 生成
│   ├── profile_report.txt        # 企业画像报告生成
│   └── mixed_analysis_tax_planning.txt # 混合分析税务筹划
├── database/                     # 数据库层
│   ├── init_db.py                # DDL 初始化（表+视图+索引）
│   ├── fintax_ai.db              # 主数据库
│   ├── tax_incentives.db         # 税收优惠知识库
│   ├── script/                   # 数据库脚本
│   │   ├── seed_data.py          # 种子数据
│   │   ├── sample_data.py        # 示例数据
│   │   ├── migrate_users.py      # 用户迁移
│   │   ├── migrate_permissions.py# 权限迁移
│   │   └── migrate_profile.py    # 画像迁移
│   ├── calculate_metrics.py      # 财务指标计算 v1
│   ├── calculate_metrics_v2.py   # 财务指标计算 v2
│   └── migrate_profile_reports.py# 报告表迁移
├── frontend/                     # 前端
│   ├── src/
│   │   ├── App.jsx               # 主应用（状态驱动路由）
│   │   ├── main.jsx              # 入口
│   │   ├── components/           # UI 组件
│   │   ├── hooks/                # 自定义 Hooks
│   │   ├── services/             # API 服务层
│   │   ├── config/               # 路由配置
│   │   ├── utils/                # 工具函数
│   │   └── styles/               # 全局样式
│   ├── index.html                # HTML 入口
│   └── vite.config.js            # Vite 配置
├── mvp_pipeline.py               # NL2SQL 管线编排（核心）
├── cache/                        # 缓存文件目录（运行时生成）
├── logs/                         # 日志目录
├── docs/                         # 文档目录
├── requirements.txt              # Python 依赖
└── start_servers.bat             # Windows 一键启动脚本
```

---

## 三、核心管线技术详解

### 3.1 NL2SQL 管线架构

NL2SQL 管线是系统最核心的技术模块，由 `mvp_pipeline.py` 编排，采用**多阶段+多快捷分支**架构：

```
用户查询
  │
  ├─ [分支0] 多轮对话混合分析检测
  │    └─ 触发 → execute_mixed_analysis_stream() → 返回
  │
  ├─ [路由分流] IntentRouter.classify()
  │    ├─ tax_incentive → TaxIncentiveQuery → 返回
  │    ├─ regulation → query_regulation() → 返回
  │    └─ financial_data → 继续以下流程
  │
  ├─ [Step 1] 实体预处理 (entity_preprocessor)
  │    ├─ detect_entities() / detect_entities_with_context()
  │    ├─ 域检测 + 跨域检测
  │    ├─ 纳税人识别 + 会计准则推断
  │    └─ 相对日期解析
  │
  ├─ [Step 1b] 提前检测计算指标
  │    ├─ extract_all_rate_metrics() → 纯率型 → 域锁定 financial_metrics
  │    └─ detect_computed_metrics() → 非率型计算指标
  │
  ├─ [Step 2] 同义词标准化 (entity_preprocessor.normalize_query)
  │
  ├─ [Step 3] 阶段1：意图解析
  │    ├─ 域锁定时 → 直接构造 intent（跳过 LLM）
  │    └─ 正常流程 → parse_intent() (LLM)
  │
  ├─ [Step 3b] 计算指标快捷分支
  │    └─ _run_metric_pipeline() → 确定性计算 → 返回
  │
  ├─ [Step 3b2] 概念快捷分支
  │    ├─ resolve_concepts() + detect_time_granularity()
  │    ├─ _run_concept_pipeline() → 确定性 SQL → 返回
  │    └─ 完整性校验失败 → 回退标准管线
  │
  ├─ [Step 3c] 跨域分支
  │    └─ _run_cross_domain_pipeline() → 并行 LLM → 返回
  │
  ├─ [Step 4] 约束注入 (constraint_injector)
  │
  ├─ [Step 5] 阶段2：SQL 生成 (sql_writer, LLM)
  │
  ├─ [Step 6] SQL 审核 (sql_auditor)
  │    └─ 审核失败 → 重试一次（反馈违规信息给 LLM）
  │
  └─ [Step 7] SQL 执行
       ├─ _build_params() 构建参数绑定
       ├─ 执行 SQL
       └─ 执行失败 → 重试一次（反馈错误信息给 LLM）
```

### 3.2 查询类型路由决策树

```
查询进入 financial_data 路由
  │
  ├─ 纯率型指标？ ─── 是 ──→ 域锁定 financial_metrics → 标准 NL2SQL（跳过 Stage1 LLM）
  │
  ├─ 混合指标（率型+非率型）？ ─── 是 ──→ 保持跨域 → _run_cross_domain_pipeline
  │
  ├─ 非率型计算指标？ ─── 是 ──→ _run_metric_pipeline（确定性，无 LLM）
  │
  ├─ 概念匹配 + 时间粒度 + 非多期间 + 非构成查询？ ─── 是 ──→ _run_concept_pipeline
  │    └─ 完整性校验失败 → 回退标准 NL2SQL
  │
  ├─ domain == cross_domain？ ─── 是 ──→ _run_cross_domain_pipeline（并行 LLM）
  │
  └─ 单域标准查询 ──→ 约束注入 → LLM SQL 生成 → 审核 → 执行
```

### 3.3 跨域管线详解

跨域管线 `_run_cross_domain_pipeline` 采用三阶段架构：

**Phase 1 — 串行构建子域任务**：
- 遍历 `cross_domain_list` 中的每个子域
- 为每个子域构建 `sub_intent`（domain、filters、scope、metrics）
- `financial_metrics` 域的 metrics 过滤逻辑不同（接受含"率"的中文名）
- 跨年多期间比较时注入 `cross_year_compare` 信息
- 为每个子域调用 `inject_constraints()` 生成约束

**Phase 2 — 并行执行 LLM SQL 生成+审核**：
- 使用 `ThreadPoolExecutor` 并行调用 `_generate_subdomain_sql()`
- 每个子域独立生成 SQL + 审核，审核失败重试一次

**Phase 3 — 串行执行 SQL 查询**：
- 主线程串行执行（避免 SQLite 多线程问题）
- 执行失败时重试一次
- 调用 `merge_cross_domain_results()` 合并各子域结果

### 3.4 概念管线详解

概念管线 `_run_concept_pipeline` 是**确定性 SQL 生成路径**，不依赖 LLM：

1. `resolve_concepts()` 从查询中提取匹配的概念
2. `detect_time_granularity()` 检测时间粒度（季度/月度/年度）
3. 对每个概念：
   - `computed` 类型 → `execute_computed_concept()`（Python 公式计算）
   - 普通类型 → `build_concept_sql()`（确定性 SQL 拼接）
4. `merge_concept_results()` 按期间对齐合并
5. 完整性校验：用 `_fuzzy_match_metric()` 模糊匹配用户请求的指标与返回的指标，缺失则回退

**概念类型**：

| 类型 | 说明 | SQL 生成方式 |
|------|------|-------------|
| 直接取值 | 报表类概念，直接映射到视图列 | `SELECT col FROM view WHERE ...` |
| 聚合取值 | 明细类概念，需 GROUP BY | `SELECT SUM(col) FROM view WHERE ... GROUP BY ...` |
| 计算型 | 多数据点 + Python 公式 | 分别查询各源数据，Python eval 计算 |

**季度策略**：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `sum_months` | 汇总季度内 3 个月数据 | 发生额类（如采购金额） |
| `quarter_end` | 取季末月数据 | 余额类（如货币资金） |

### 3.5 计算指标管线详解

计算指标管线 `_run_metric_pipeline` 完全确定性，不依赖 LLM：

1. `detect_computed_metrics()` 检测查询中的计算指标
2. 对每个 `metric_name`，从 `METRIC_FORMULAS` 获取定义
3. 对每个 source 变量，根据 `sources` 定义构建确定性 SQL
4. 执行 SQL 获取源数据
5. `compute_metric()` 用公式计算最终指标值（Python eval）

**公式示例**：

```python
# 资产负债率
"formula": "total_liabilities / total_assets * 100 if total_assets else None"
"sources": {
    "total_liabilities": {"domain": "balance_sheet", "column": "liabilities_end"},
    "total_assets": {"domain": "balance_sheet", "column": "assets_end"}
}

# 净资产收益率（跨域）
"formula": "net_profit / avg_equity * 100 if avg_equity else None"
"sources": {
    "net_profit": {"domain": "profit", "column": "net_profit"},
    "avg_equity": {"domain": "balance_sheet", "column": "(equity_begin + equity_end) / 2.0"}
}
```

---

## 四、LLM 提示词工程

### 4.1 两阶段提示词架构

系统采用两阶段提示词架构，Stage1 负责意图解析，Stage2 负责 SQL 生成：

#### Stage1 — 意图解析提示词 (`stage1_system.txt`)

- **定位**：税务数据查询意图解析器
- **输出**：严格 JSON
- **核心功能**：
  - 16 条优先级规则判断数据域
  - 构成/结构查询识别（`query_type="composition"`）
  - 跨域检测（`cross_domain_list`）
  - 指标提取（中文→物理列名）
  - 期间解析
  - 会计准则判断

**域判断优先级规则**（从高到低）：

| 规则 | 域 |
|------|------|
| 0 | 财务指标关键词 → financial_metrics |
| 1 | 科目余额关键词 → account_balance |
| 2 | 借贷/发生额修饰词 → account_balance |
| 3-4 | 利润表/现金流量表特有项目 → profit/cash_flow |
| 5-7 | 资产负债表关键词 → balance_sheet |
| 8 | 共有项目消歧（年初→BS，期初→AB） |
| 9 | 利润表与 EIT 消歧 |
| 9a | 发票域判断 |
| 10-14 | 增值税/企业所得税明确关键词 |
| 15 | 多域 → cross_domain |

#### Stage2 — SQL 生成提示词

每个域有独立的 Stage2 提示词，共同特征：
- 只输出纯 SQL，不解释
- 严格限制只能访问白名单视图和列
- 包含修订版本处理（ROW_NUMBER 窗口函数取最新版本）

**各域特有指令**：

| 域 | 特有指令 |
|------|----------|
| balance_sheet | 构成分析 UNION ALL、占比计算、恒等式校验、_begin/_end 列命名 |
| vat | item_type 选择策略、VAT 修订版本处理、季度累计数据 |
| profit | 双行数据结构（本期/本年累计）、time_range 过滤、期间费用构成分析 |
| cash_flow | 双行数据结构、会计准则过滤 |
| financial_metrics | 5 种查询模式、period_type 智能选择、CASE WHEN 透视 |
| cross_domain | UNION ALL 合并、禁止跨视图 JOIN、统一输出格式 |
| eit | 年度/季度视图选择、核心列映射 |
| invoice | 进项/销项视图选择 |
| account_balance | 会计准则科目过滤 |

### 4.2 画像报告提示词 (`profile_report.txt`)

- **定位**：20 年经验的财务数据分析师/税务筹划专家
- **输出**：14 个分析模块 + 企业全景综合结论
- **严格约束**：数据缺失模块直接跳过、符合中国财税政策、不提供违法方案

### 4.3 混合分析提示词 (`mixed_analysis_tax_planning.txt`)

- **定位**：多轮对话税务筹划分析器
- **5 大分析维度**：数据匹配分析、风险识别、税收筹划建议、财务优化建议、行动计划
- **输入**：按路由分组的历史对话数据

---

## 五、数据库技术设计

### 5.1 数据库架构

- **引擎**：SQLite，WAL 模式（支持并发读写）
- **PRAGMA 调优**：
  - `journal_mode=WAL`
  - `cache_size=-64000`（64MB 页缓存）
  - `mmap_size=268435456`（256MB 内存映射）
  - `temp_store=MEMORY`（临时表存内存）
  - `synchronous=NORMAL`

### 5.2 表设计模式

系统采用三种数据存储模式：

| 模式 | 适用域 | 说明 |
|------|--------|------|
| 宽表 | VAT、EIT、发票、HR | 每个字段一列，直接查询 |
| EAV 纵表 | 资产负债表、利润表、现金流量表 | 项目编码+值，通过视图透视 |
| 混合 | 科目余额、财务指标 | 主表+字典表+同义词表 |

### 5.3 视图设计

系统使用视图层实现数据访问控制，每个域区分会计准则/纳税人类型：

| 域 | 视图 | 过滤条件 |
|------|------|----------|
| VAT | vw_vat_return_general | taxpayer_type='一般纳税人' |
| VAT | vw_vat_return_small | taxpayer_type='小规模纳税人' |
| EIT 年度 | vw_eit_annual_main | 无过滤 |
| EIT 季度 | vw_eit_quarter_main | 无过滤 |
| 资产负债表 | vw_balance_sheet_eas | gaap_type='ASBE' |
| 资产负债表 | vw_balance_sheet_sas | gaap_type='ASSE' |
| 利润表 | vw_profit_eas | gaap_type='CAS' |
| 利润表 | vw_profit_sas | gaap_type='SAS' |
| 现金流量表 | vw_cash_flow_eas | gaap_type='CAS' + accounting_standard |
| 现金流量表 | vw_cash_flow_sas | gaap_type='SAS' + accounting_standard |
| 科目余额 | vw_account_balance | 会计准则科目过滤 |
| 发票 | vw_inv_spec_purchase/sales | 无过滤 |
| 财务指标 | vw_financial_metrics | 无过滤 |

**EAV 透视视图生成**：资产负债表/利润表/现金流量表的宽表视图通过动态 DDL 从 EAV 纵表透视生成，使用 `MAX(CASE WHEN item_code='...' THEN value END)` 模式。

### 5.4 核心数据表

| 表名 | 行数级别 | 主键 | 说明 |
|------|----------|------|------|
| taxpayer_info | ~10 | taxpayer_id | 纳税人主维表 |
| vat_return_general | ~100 | taxpayer_id+year+month+item_type+time_range+revision | 增值税一般纳税人 |
| vat_return_small | ~100 | 同上 | 增值税小规模纳税人 |
| eit_annual_filing | ~10 | filing_id | EIT 年度申报封面 |
| eit_annual_main | ~10 | filing_id | EIT 年度主表 |
| eit_quarter_filing | ~40 | filing_id | EIT 季度申报封面 |
| eit_quarter_main | ~40 | filing_id | EIT 季度主表 |
| fs_balance_sheet_item | ~1000 | taxpayer_id+year+month+gaap_type+item_code+revision | 资产负债表 EAV |
| fs_income_statement_item | ~1000 | 同上 | 利润表 EAV |
| fs_cash_flow_item | ~1000 | 同上 | 现金流量表 EAV |
| account_balance | ~5000 | taxpayer_id+year+month+account_code+revision | 科目余额 |
| inv_spec_purchase | ~500 | taxpayer_id+invoice_pk+line_no | 进项发票 |
| inv_spec_sales | ~500 | 同上 | 销项发票 |
| financial_metrics_item | ~500 | taxpayer_id+year+month+period_type+metric_code | 财务指标 |
| hr_employee_info | ~100 | employee_id | 员工信息 |
| hr_employee_salary | ~1000 | employee_id+salary_month | 员工薪资 |
| users | ~10 | id | 用户表 |
| user_company_access | ~20 | user_id+taxpayer_id | 用户企业权限 |

### 5.5 同义词体系

系统在每个域维护同义词表，用于将用户自然语言映射到标准列名：

| 同义词表 | 说明 |
|----------|------|
| vat_synonyms | 增值税列同义词 |
| eit_synonyms | 企业所得税列同义词 |
| fs_balance_sheet_synonyms | 资产负债表项目同义词 |
| fs_income_statement_synonyms | 利润表项目同义词 |
| fs_cash_flow_synonyms | 现金流量表项目同义词 |
| account_synonyms | 科目余额同义词 |
| inv_synonyms | 发票列同义词 |
| financial_metrics_synonyms | 财务指标同义词 |
| metric_synonyms | 计算指标同义词 |

同义词匹配策略：**最长匹配优先 + 不重叠替换**，从数据库加载域感知的同义词表。

---

## 六、缓存技术设计

### 6.1 L1 精确缓存

**实现**：`api/services/query_cache.py`

| 项目 | 说明 |
|------|------|
| 存储介质 | 文件系统（`cache/{md5}.json`） |
| 缓存键 | `MD5(company_id + normalized_query + response_mode)` |
| 存储内容 | 完整管线结果（route、result、interpretation） |
| 淘汰策略 | LRU（按 `last_accessed_at` 排序删除） |
| 上限 | 1200 个文件 |
| 线程安全 | `threading.Lock` |
| 附加操作 | 命中时更新访问时间和命中计数、解读回写、按企业/期间失效 |

**缓存文件结构**：

```json
{
  "cache_key": "md5hash",
  "company_id": "91310000MA1FL8XQ30",
  "query": "华兴科技2025年增值税",
  "response_mode": "detailed",
  "route": "financial_data",
  "result": { ... },
  "interpretation": "解读文本...",
  "created_at": "2026-04-21T10:00:00",
  "last_accessed_at": "2026-04-21T10:05:00",
  "hit_count": 3
}
```

### 6.2 L2 模板缓存

**实现**：`api/services/template_cache.py`

| 项目 | 说明 |
|------|------|
| 存储介质 | 文件系统（`cache/template_{md5}.json`） |
| 缓存键 | 域感知键（见下表） |
| 存储内容 | SQL 模板 + 意图 JSON + 跨域子模板 |
| 淘汰策略 | LRU |
| 上限 | 600 个文件 |

**域感知缓存键策略**：

| 域类别 | 缓存键维度 | 说明 |
|--------|-----------|------|
| financial_statement | query + response_mode + fs + accounting_standard | 财务三表，按会计准则区分 |
| vat | query + response_mode + vat + taxpayer_type | 增值税，按纳税人类型区分 |
| eit | query + response_mode + eit | 所得税，最简键 |
| unknown | query + response_mode + taxpayer_type + accounting_standard | 兜底，全维度 |

**SQL 模板化/实例化**：

```python
# 模板化：将 SQL 中的纳税人 ID 替换为占位符
templatize_sql(sql, company_id)
# "WHERE taxpayer_id = '91310000MA1FL8XQ30'" → "WHERE taxpayer_id = '{{TAXPAYER_ID}}'"

# 实例化：将占位符替换回参数化占位符
instantiate_sql(template, company_id)
# "WHERE taxpayer_id = '{{TAXPAYER_ID}}'" → "WHERE taxpayer_id = :taxpayer_id"
```

**跨域模板**：保存 `sub_templates` 列表（每个子域的 SQL 模板 + 参数键 + 静态参数），支持概念管线和 LLM 跨域管线两种模式。

### 6.3 缓存与思考模式交互

```
quick 模式:
  L1 命中 → 返回缓存结果 + 缓存解读
  L2 命中 → 实例化 SQL → 执行 → 返回
  未命中 → 完整管线 → 写入 L1 + L2

think 模式:
  L1 命中 → 返回缓存结果 + 重新请求 LLM 解读
  L2 命中 → 实例化 SQL → 执行 → 返回
  未命中 → 完整管线 → 写入 L1 + L2

deep 模式:
  不使用缓存 → 完整管线 → 写入 L1 + L2
```

### 6.4 已弃用缓存

`modules/cache_manager.py` 中的内存 LRU 缓存已弃用。原因：内存缓存使用 `query + taxpayer_type` 作为键，不包含 `company_id`，导致不同公司的相同类型查询可能返回错误的缓存数据。

---

## 七、API 接口技术规范

### 7.1 API 路由注册

所有路由在 `api/main.py` 中注册，前缀 `/api`：

```python
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(profile_report.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(data_management.router, prefix="/api")
app.include_router(data_browser.router, prefix="/api")
app.include_router(interpret.router, prefix="/api")
app.include_router(dashboard.router)
app.include_router(cache_stats.router, prefix="/api")
```

### 7.2 SSE 流式接口

系统有三个 SSE 流式接口：

| 端点 | 说明 | 事件类型 |
|------|------|----------|
| POST /api/chat | 对话主端点 | stage, chunk, done |
| POST /api/chat/history/reinvoke | 历史重执行 | stage, chunk, done |
| POST /api/profile/{id}/report | 报告生成 | section_start, chunk, section_end, done |

**SSE 事件格式**：

```
event: stage
data: {"route": "financial_data", "text": "正在解析查询意图..."}

event: chunk
data: {"text": "分析文本片段..."}

event: done
data: {"result": {...完整结果...}}
```

### 7.3 认证中间件

所有需要认证的端点使用 `get_current_user` 依赖注入：

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict
```

管理员权限使用 `require_admin` 依赖：

```python
async def require_admin(user: dict = Depends(get_current_user)) -> dict
```

企业数据权限使用 `require_company_access` 函数校验。

### 7.4 CORS 配置

```python
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://127.0.0.1:8000"
).split(",")
```

---

## 八、前端技术设计

### 8.1 架构模式

- **无路由库**：通过 `currentPage` 状态 + switch/case 实现页面切换
- **状态提升**：核心状态（messages、historyItems、selectedCompanyId 等）均在 App.jsx 管理
- **SSE 流式通信**：通过 `parseSSE` 异步生成器统一解析
- **三层认证门控**：验证码 → 登录 → Token 鉴权

### 8.2 组件结构

```
App.jsx
├── CaptchaModal          # 验证码弹窗
├── Login                 # 登录页
├── Header                # 顶部导航
├── Sidebar               # 侧边栏
├── ChatArea              # 对话区域
│   ├── ChatInput         # 输入框
│   └── ChatMessage       # 消息气泡
│       ├── ResultTable   # 结果表格
│       ├── ChartRenderer # 图表渲染
│       ├── GrowthTable   # 增长率表格
│       └── PipelineDetail# 管线详情
├── HistoryPanel          # 历史记录面板
│   └── Pagination        # 分页
├── Dashboard             # 仪表盘
│   └── widgets/          # 仪表盘组件
├── CompanyProfile        # 企业画像
│   └── modules/          # 画像子模块
├── ProfileReport         # 画像报告
├── ReportList            # 报告列表
├── DataManagementPage    # 数据管理
│   ├── DataBrowser       # 数据浏览
│   └── raw/              # 原表格式组件
├── SystemSettingsPage    # 系统设置
│   ├── UserManagement    # 用户管理
│   ├── BasicSettings     # 基本设置
│   └── ServiceSettings   # 服务设置
└── Footer                # 底部
```

### 8.3 SSE 解析器

```javascript
// sseParser.js
export async function* parseSSE(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';
  let currentData = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // 按行解析 SSE 协议
    for (const line of buffer.split('\n')) {
      if (line.startsWith('event:')) currentEvent = line.slice(6).trim();
      else if (line.startsWith('data:')) currentData = line.slice(5).trim();
      else if (line === '' && currentData) {
        yield { event: currentEvent, data: JSON.parse(currentData) };
        currentEvent = '';
        currentData = '';
      }
    }
  }
}
```

### 8.4 路由标签配置

```javascript
// routeConfig.js
const ROUTE_BADGES = {
  financial_data: { label: '财税数据查询', color: '#3b82f6' },
  tax_incentive:  { label: '本地知识库查询结果', color: '#10b981' },
  regulation:     { label: '法规知识库', color: '#f59e0b' },
  mixed_analysis: { label: '综合分析', color: '#8b5cf6' },
};

const DOMAIN_BADGES = {
  vat: { label: '增值税', color: '#3b82f6' },
  eit: { label: '企业所得税', color: '#8b5cf6' },
  balance_sheet: { label: '资产负债表', color: '#06b6d4' },
  profit: { label: '利润表', color: '#10b981' },
  cash_flow: { label: '现金流量表', color: '#f59e0b' },
  account_balance: { label: '科目余额', color: '#6366f1' },
  invoice: { label: '发票', color: '#ec4899' },
  financial_metrics: { label: '财务指标', color: '#14b8a6' },
  cross_domain: { label: '跨域查询', color: '#f97316' },
};
```

---

## 九、安全设计

### 9.1 SQL 安全

| 层级 | 机制 | 说明 |
|------|------|------|
| 视图白名单 | schema_catalog.DOMAIN_VIEWS | 只允许访问预定义视图 |
| 列白名单 | schema_catalog.VIEW_COLUMNS | 只允许访问预定义列 |
| SQL 审核 | sql_auditor.audit_sql() | 10 条正则规则硬拦截 |
| 参数绑定 | _build_params() | 防止 SQL 注入 |
| 危险关键字 | schema_catalog.DENIED_KEYWORDS | DROP/DELETE/INSERT/UPDATE/ALTER |
| 危险函数 | schema_catalog.DENIED_FUNCTIONS | LOAD_EXTENSION/WRITEFILE |

### 9.2 认证安全

| 机制 | 说明 |
|------|------|
| JWT Token | HS256 签名，24h 过期 |
| bcrypt 密码 | 自适应盐值哈希 |
| 验证码门控 | 首次访问需验证 |
| Token 自动注入 | 前端 authHeaders() 自动添加 |

### 9.3 数据隔离

| 机制 | 说明 |
|------|------|
| 企业级隔离 | user_company_access 表控制 |
| 角色权限 | 5 级 RBAC |
| API 鉴权 | get_current_user + require_company_access |
| 缓存隔离 | L1 缓存键包含 company_id |

---

## 十、配置体系

### 10.1 全局配置 (`config/settings.py`)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| LLM_API_KEY | sk-6ba4... | DeepSeek API Key |
| LLM_API_BASE | https://api.deepseek.com | LLM API 地址 |
| LLM_MODEL | deepseek-chat | LLM 模型名 |
| DB_PATH | database/fintax_ai.db | 主数据库路径 |
| TAX_INCENTIVES_DB_PATH | database/tax_incentives.db | 税收优惠库路径 |
| JWT_SECRET_KEY | fintax-ai-secret-... | JWT 签名密钥 |
| JWT_EXPIRE_MINUTES | 1440 | Token 有效期（分钟） |
| MAX_ROWS | 1000 | SQL 查询最大行数 |
| QUERY_CACHE_ENABLED | True | L1 缓存开关 |
| QUERY_CACHE_ENABLED_L2 | True | L2 缓存开关 |
| CONVERSATION_ENABLED | True | 多轮对话开关 |
| MIXED_ANALYSIS_ENABLED | True | 混合分析开关 |
| PROFILE_REPORT_ENABLED | True | 画像报告开关 |

### 10.2 JSON 配置热加载

系统通过 `config_loader.py` 实现配置热加载：

- `load_json(path, fallback)` — 加载单个 JSON 文件
- `load_json_dir(dir_path, fallback)` — 加载目录下所有 JSON 文件并合并

多个模块支持配置热重载：
- `IntentRouter.reload_config()` — 重载路由配置
- `concept_registry.reload_concepts()` — 重载概念配置
- `DataUpdateService.reload_router_config()` — 重载路由配置

---

## 十一、关键模块接口规范

### 11.1 mvp_pipeline.py

```python
def run_pipeline_stream(
    user_query: str,
    db_path: str = None,
    progress_callback=None,
    original_query: str = None,
    conversation_history: list = None,
    multi_turn_enabled: bool = False,
) -> Generator[Dict]

def run_pipeline(
    user_query: str,
    db_path: str = None,
    progress_callback=None,
    conversation_history: list = None,
) -> dict
```

### 11.2 entity_preprocessor.py

```python
def detect_entities(user_query: str, db_conn) -> dict
def detect_entities_with_context(user_query: str, db_conn, conversation_history=None) -> dict
def normalize_query(user_query: str, scope_view: str, taxpayer_type: str, db_conn, domain=None) -> tuple
def get_scope_view(taxpayer_type: str, domain=None, report_type=None, accounting_standard=None) -> str
```

### 11.3 intent_parser.py

```python
def parse_intent(user_query: str, entities: dict, synonym_hits: list, conversation_history=None) -> dict
```

### 11.4 sql_writer.py

```python
def generate_sql(constraints: dict, retry_feedback=None, domain='vat', conversation_history=None) -> str
```

### 11.5 sql_auditor.py

```python
def audit_sql(sql: str, allowed_views: list, max_rows=1000, domain='vat') -> tuple[bool, list[str]]
```

### 11.6 concept_registry.py

```python
def resolve_concepts(query: str, entities=None) -> list
def resolve_concepts_with_remainder(query: str, entities: dict) -> tuple
def build_concept_sql(concept_def: dict, entities: dict, time_granularity: str) -> tuple
def detect_time_granularity(query: str, entities=None) -> str
def reload_concepts()
```

### 11.7 metric_calculator.py

```python
def detect_computed_metrics(query: str) -> list
def extract_all_rate_metrics(query: str) -> list
def compute_metric(metric_name: str, source_data: dict) -> dict
```

### 11.8 display_formatter.py

```python
def format_display(result: dict) -> str
def build_display_data(result: dict, query: str = '') -> dict
```

### 11.9 interpretation_service.py

```python
def interpret_stream(result: dict, query: str, response_mode="detailed") -> Generator[str]
```

### 11.10 profile_service.py

```python
def get_company_profile(taxpayer_id: str, year: int) -> dict
```

### 11.11 profile_report_service.py

```python
def generate_report_stream(profile_data: dict, taxpayer_name: str, year: int) -> Generator[Dict]
```

---

## 十二、重试与容错机制

### 12.1 SQL 生成重试

| 阶段 | 重试条件 | 重试策略 |
|------|----------|----------|
| SQL 审核 | 审核不通过 | 将违规信息反馈给 LLM 重新生成，最多重试 1 次 |
| SQL 执行 | 执行报错 | 将错误信息反馈给 LLM 重新生成，最多重试 1 次 |
| 跨域子域 | 子域审核/执行失败 | 同上，每个子域独立重试 |

### 12.2 LLM 调用容错

| 场景 | 容错策略 |
|------|----------|
| LLM 调用失败 | 返回安全的默认意图/空结果 |
| JSON 解析失败 | 正则提取兜底 |
| 意图解析异常 | 返回默认域(vat)的空意图 |
| 混合分析 LLM 判断失败 | 回退到关键词匹配 |

### 12.3 缓存容错

| 场景 | 容错策略 |
|------|----------|
| L1 缓存读取失败 | 走完整管线 |
| L2 缓存读取失败 | 走完整管线 |
| L2 SQL 实例化失败 | 走完整管线 |
| 概念管线完整性校验失败 | 回退到标准 NL2SQL 管线 |

---

## 十三、日志与监控

### 13.1 查询路径日志

通过 `query_path_logger.py` 记录每次查询的路径：

| 字段 | 说明 |
|------|------|
| query | 用户查询 |
| company_id | 企业 ID |
| path | 查询路径（l1/l2/l2_adapted/pipeline） |
| response_time | 响应时间(ms) |
| thinking_mode | 思考模式 |
| success | 是否成功 |

日志格式：JSON Lines，写入 `logs/query_path.log`

### 13.2 缓存统计

通过 `/api/cache/stats` 端点获取：

| 指标 | 说明 |
|------|------|
| L1 文件数 / 命中数 | L1 缓存规模和命中 |
| L2 文件数 / 命中数 | L2 缓存规模和命中 |
| L2 适配命中数 | L2 模板适配命中 |
| 管线完整执行数 | 未命中缓存的查询数 |
| 命中率 | L1+L2 综合命中率 |

---

## 十四、有效脚本与临时脚本分类

### 14.1 有效核心脚本

| 脚本 | 路径 | 说明 |
|------|------|------|
| mvp_pipeline.py | 项目根目录 | NL2SQL 管线编排 |
| api/main.py | api/ | FastAPI 入口 |
| api/auth.py | api/ | JWT 认证工具 |
| api/schemas.py | api/ | 请求/响应模型 |
| api/routes/*.py | api/routes/ | 12 个 API 路由 |
| api/services/*.py | api/services/ | 7 个业务服务 |
| modules/*.py | modules/ | 21 个核心模块 |
| config/settings.py | config/ | 全局配置 |
| config/config_loader.py | config/ | 配置加载工具 |
| database/init_db.py | database/ | 数据库初始化 |
| database/calculate_metrics.py | database/ | 指标计算 v1 |
| database/calculate_metrics_v2.py | database/ | 指标计算 v2 |
| database/migrate_profile_reports.py | database/ | 报告表迁移 |
| database/script/seed_data.py | database/script/ | 种子数据 |
| database/script/sample_data.py | database/script/ | 示例数据 |
| database/script/migrate_users.py | database/script/ | 用户迁移 |
| database/script/migrate_permissions.py | database/script/ | 权限迁移 |
| database/script/migrate_profile.py | database/script/ | 画像迁移 |
| frontend/src/** | frontend/src/ | 前端全部源码 |
| start_servers.bat | 项目根目录 | 启动脚本 |

### 14.2 临时/测试脚本（应忽略）

项目根目录和 tests/ 目录下存在大量 `test_*.py`、`check_*.py`、`verify_*.py`、`extract_*.py`、`split_output.py`、`quick_test_*.py` 等脚本，以及 `scripts/` 目录下的数据生成/修复脚本，这些均为临时调试或测试用途，不属于系统核心功能。

---

## 十五、技术债务与已废弃模块

| 模块/配置 | 状态 | 说明 |
|-----------|------|------|
| modules/cache_manager.py | 已弃用 | 内存 LRU 缓存，与 L1/L2 持久化缓存冲突 |
| api/services/view_adapter.py | 已弃用 | 视图适配器，会计准则差异导致列结构不同 |
| config/settings.py CACHE_* | 已弃用 | 内存缓存配置，保留向后兼容 |
| config/settings.py TAXPAYER_TYPE_SMART_ADAPT | 已弃用 | 智能适配开关，保留向后兼容 |
| modules/entity_preprocessor - 副本.py | 备份文件 | 应忽略 |
| database/fintax_ai_backup_*.db | 备份文件 | 应忽略 |
| database/users-bak.db | 备份文件 | 应忽略 |
