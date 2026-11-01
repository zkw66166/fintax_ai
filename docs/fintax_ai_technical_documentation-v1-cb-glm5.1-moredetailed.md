# fintax_ai 技术文档

## 版本信息

- **版本**：v1.0.0
- **更新日期**：2026-04-01
- **文档类型**：技术文档（面向开发人员）

---

## 目录

1. [系统架构总览](#1-系统架构总览)
2. [后端架构](#2-后端架构)
3. [NL2SQL 流水线](#3-nl2sql-流水线)
4. [数据库设计](#4-数据库设计)
5. [API 接口定义](#5-api-接口定义)
6. [前端架构](#6-前端架构)
7. [缓存体系](#7-缓存体系)
8. [安全设计](#8-安全设计)
9. [配置体系](#9-配置体系)

---

## 1. 系统架构总览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端展示层                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │  工作台      │ │  AI智问     │ │  企业画像   │ │  数据管理/系统设置      │ │
│  │  Dashboard  │ │   Chat      │ │   Profile   │ │  Data/Settings          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘ │
│                              React 19 + Vite 7                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↑↓
                              HTTP / SSE (EventSource)
                                       ↑↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 网关层                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         FastAPI Application                            │  │
│  │  - CORS 中间件                                                          │  │
│  │  - JWT 认证依赖 (get_current_user)                                      │  │
│  │  - 静态文件托管 (React SPA)                                             │  │
│  │  - 异常处理                                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↑↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              路由层 (12 Routers)                              │
│  ┌────────┬────────┬────────┬────────┬────────┬────────┬──────────────────┐ │
│  │  auth  │ users  │  chat  │ history│ company│ profile│ profile_report   │ │
│  │ 认证   │ 用户   │ 聊天   │ 历史   │ 企业   │ 画像   │ 画像报告         │ │
│  ├────────┼────────┼────────┼────────┼────────┼────────┼──────────────────┤ │
│  │ data_  │ data_  │interpret│dashboard│cache_ │        │                  │ │
│  │browser │manage  │ 解读   │工作台  │stats   │        │                  │ │
│  │ 浏览器 │ 管理   │        │        │ 缓存   │        │                  │ │
│  └────────┴────────┴────────┴────────┴────────┴────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↑↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              服务层 (7 Services)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │ dashboard_  │ data_quality│ data_update │ query_cache               │ │
│  │ service     │ 数据质量    │ _service    │ 查询缓存(L1)              │ │
│  ├─────────────┼─────────────┼─────────────┼───────────────────────────┤ │
│  │ query_path_ │ template_   │ view_       │                           │ │
│  │ logger      │ cache       │ adapter     │                           │ │
│  │ 路径日志    │ 模板缓存(L2)│ 视图适配    │                           │ │
│  └─────────────┴─────────────┴─────────────┴───────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↑↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层 (23 Modules)                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ 核心流水线模块                                                        │   │
│  │  - intent_router: 意图路由（4路由分类）                                │   │
│  │  - entity_preprocessor: 实体预处理（日期、域检测、同义词）              │   │
│  │  - intent_parser: Stage 1 意图解析（LLM）                              │   │
│  │  - constraint_injector: 约束注入                                       │   │
│  │  - sql_writer: Stage 2 SQL生成（LLM）                                  │   │
│  │  - sql_auditor: SQL审计（硬阻断+软阻断+重试）                           │   │
│  │  - cross_domain_calculator: 跨域计算                                   │   │
│  │  - metric_calculator: 22个指标确定性计算                               │   │
│  │  - concept_registry: 326个概念注册表                                   │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ 对话与混合分析                                                        │   │
│  │  - conversation_manager: 多轮对话管理（Tier 1）                         │   │
│  │  - mixed_analysis_detector: 混合分析检测                               │   │
│  │  - mixed_analysis_executor: 混合分析执行                               │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ 企业画像与解读                                                        │   │
│  │  - profile_service: 企业画像聚合服务                                   │   │
│  │  - profile_report_service: 画像报告生成（LLM）                          │   │
│  │  - interpretation_service: 数据解读服务（7场景）                         │   │
│  │  - display_formatter: 显示格式化                                       │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ 外部服务集成                                                          │   │
│  │  - tax_incentive_query: 税收优惠查询（FTS5）                            │   │
│  │  - regulation_api: 法规知识库（Coze RAG）                               │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ 基础设施                                                              │   │
│  │  - schema_catalog: Schema目录（白名单）                                 │   │
│  │  - cache_manager: 缓存管理                                             │   │
│  │  - db_utils: 数据库工具                                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↑↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据访问层                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         SQLite Database                                │  │
│  │  - 30+ 数据表                                                           │  │
│  │  - 18 个核心视图（NL2SQL唯一入口）                                       │  │
│  │  - 9 个同义词表（300+映射）                                              │  │
│  │  - FTS5 全文索引（税收优惠）                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | React | 19.x |
| 前端 | Vite | 7.x |
| 前端 | Chart.js | 4.x |
| 后端 | Python | 3.9+ |
| 后端 | FastAPI | 最新 |
| 后端 | Pydantic | 2.x |
| 数据库 | SQLite | 3.35+ |
| AI | DeepSeek | deepseek-chat |
| 部署 | Uvicorn | 标准 |

### 1.3 核心文件结构

```
fintax_ai/
├── api/                          # FastAPI 后端
│   ├── main.py                   # 入口：FastAPI app，12路由注册
│   ├── auth.py                   # JWT工具：create_access_token, get_current_user
│   ├── schemas.py                # Pydantic模型：9个请求/响应模型
│   ├── routes/                   # 12个路由模块
│   │   ├── auth.py               # 认证：login/logout/me/captcha
│   │   ├── users.py              # 用户：CRUD + company access
│   │   ├── chat.py               # 聊天：SSE streaming，三模式缓存
│   │   ├── history.py            # 历史：CRUD + reinvocation
│   │   ├── company.py            # 企业：列表查询
│   │   ├── profile.py            # 画像：企业画像聚合
│   │   ├── profile_report.py     # 画像报告：生成/列表/详情/删除
│   │   ├── data_browser.py       # 数据浏览器：10域浏览
│   │   ├── data_management.py    # 数据管理：统计+质量检查
│   │   ├── interpret.py          # 解读：LLM数据解读
│   │   ├── dashboard.py          # 工作台：聚合数据
│   │   └── cache_stats.py        # 缓存统计
│   └── services/                 # 7个服务模块
│       ├── dashboard_service.py
│       ├── data_quality.py
│       ├── data_update_service.py
│       ├── query_cache.py        # L1缓存
│       ├── query_path_logger.py
│       ├── template_cache.py     # L2缓存
│       └── view_adapter.py
├── modules/                      # 23个核心业务模块
│   ├── intent_router.py          # 意图路由
│   ├── entity_preprocessor.py    # 实体预处理
│   ├── intent_parser.py          # Stage 1意图解析
│   ├── constraint_injector.py    # 约束注入
│   ├── sql_writer.py             # Stage 2 SQL生成
│   ├── sql_auditor.py            # SQL审计
│   ├── cross_domain_calculator.py # 跨域计算
│   ├── metric_calculator.py      # 指标计算
│   ├── concept_registry.py       # 概念注册表
│   ├── conversation_manager.py   # 多轮对话
│   ├── mixed_analysis_detector.py # 混合分析检测
│   ├── mixed_analysis_executor.py # 混合分析执行
│   ├── profile_service.py        # 企业画像服务
│   ├── profile_report_service.py # 画像报告服务
│   ├── interpretation_service.py # 数据解读服务
│   ├── display_formatter.py      # 显示格式化
│   ├── tax_incentive_query.py    # 税收优惠查询
│   ├── regulation_api.py         # 法规API
│   ├── schema_catalog.py         # Schema目录
│   ├── cache_manager.py          # 缓存管理
│   └── db_utils.py               # 数据库工具
├── mvp_pipeline.py               # NL2SQL流水线编排
├── database/                     # 数据库
│   ├── init_db.py                # DDL：30+表+18视图
│   ├── migrate_profile_reports.py # 报告表迁移
│   └── seed_data.py              # 种子数据
├── config/                       # 配置
│   ├── settings.py               # 主配置（50+参数）
│   ├── tax_query_config.json     # 意图路由配置
│   ├── tax_search_keywords.json  # 搜索关键词
│   └── [15个子目录]              # 各类配置
├── prompts/                      # AI提示词（13个文件）
│   ├── stage1_system.txt         # Stage 1系统提示
│   ├── stage2_*.txt              # Stage 2域特定提示（9个）
│   ├── mixed_analysis_tax_planning.txt
│   ├── profile_report.txt
│   └── tax_incentive_summary.txt
├── frontend/                     # React前端
│   └── src/
│       ├── App.jsx               # 入口：7页面路由
│       ├── components/           # 20+组件目录
│       ├── hooks/                # 自定义Hooks
│       ├── services/             # API服务
│       └── utils/                # 工具函数
└── docs/                         # 文档
    ├── fintax_ai_functional_specification.md
    └── fintax_ai_technical_documentation.md
```

---

## 2. 后端架构

### 2.1 FastAPI 入口 (api/main.py)

```python
app = FastAPI(title="fintax_ai API", version="1.0.0")

# CORS 配置
app.add_middleware(CORSMiddleware, ...)

# 12 个路由注册（注意顺序）
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(profile_report.router, prefix="/api")  # 必须在 profile 之前
app.include_router(profile.router, prefix="/api")
app.include_router(data_management.router, prefix="/api")
app.include_router(data_browser.router, prefix="/api")
app.include_router(interpret.router, prefix="/api")
app.include_router(dashboard.router)
app.include_router(cache_stats.router, prefix="/api")

# 生产环境静态文件托管
if dist_dir.exists():
    app.mount("/assets", StaticFiles(...))
    # SPA catch-all
    @app.get("/{full_path:path}")
    async def serve_spa(...)
```

### 2.2 JWT 认证 (api/auth.py)

```python
# JWT 配置
JWT_SECRET_KEY = "[REMOVED_JWT_SECRET]"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 1440  # 24小时

# 核心函数
def create_access_token(data: dict) -> str
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def require_company_access(user: User, company_id: str) -> None
```

### 2.3 Pydantic 模型 (api/schemas.py)

| 模型 | 用途 | 字段 |
|------|------|------|
| `ChatRequest` | 聊天请求 | query, response_mode, company_id, thinking_mode, conversation_history, conversation_depth |
| `LoginRequest` | 登录请求 | username, password |
| `UserCreate` | 创建用户 | username, password, role, display_name, is_active, company_ids |
| `UserUpdate` | 更新用户 | password, role, display_name, is_active, company_ids |
| `CompanyItem` | 企业项 | taxpayer_id, taxpayer_name, taxpayer_type |
| `InterpretRequest` | 解读请求 | query, result, response_mode, company_id, cache_key, conversation_history |
| `HistoryDeleteRequest` | 删除历史 | ids |
| `CaptchaVerifyRequest` | 验证码 | code |

### 2.4 路由模块详解

#### 2.4.1 Chat 路由 (api/routes/chat.py)

**端点**：`POST /api/chat`

**功能**：核心查询入口，SSE 流式返回

**流程**：
```python
@router.post("/chat")
async def chat_endpoint(request: ChatRequest, user: User = Depends(get_current_user)):
    # 1. 验证企业访问权限
    require_company_access(user, request.company_id)
    
    # 2. 三模式缓存交互
    if request.thinking_mode == "quick":
        # 直接返回缓存结果
    elif request.thinking_mode == "think":
        # 返回缓存结果 + need_reinterpret=True
    elif request.thinking_mode == "deep":
        # 跳过缓存，执行完整流水线
    
    # 3. 调用 mvp_pipeline.run_pipeline_stream()
    # 4. SSE 流式返回
```

**SSE 事件类型**：
- `stage`: 阶段指示（route, stage）
- `chunk`: 文本片段（用于 tax_incentive/regulation 路由）
- `done`: 最终结果（含 display_data）

#### 2.4.2 Auth 路由 (api/routes/auth.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/auth/login` | POST | 登录，返回 JWT + 用户信息 + company_ids |
| `/api/auth/logout` | POST | 登出（客户端清除 token） |
| `/api/auth/me` | GET | 获取当前用户信息 |
| `/api/auth/captcha/verify` | POST | 验证码验证 |

#### 2.4.3 Users 路由 (api/routes/users.py)

| 端点 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/api/users` | GET | 用户列表 | sys/admin |
| `/api/users` | POST | 创建用户 | 按角色规则 |
| `/api/users/{id}` | PUT | 更新用户 | sys/admin |
| `/api/users/{id}` | DELETE | 删除用户 | sys/admin |
| `/api/users/{id}/companies` | GET | 获取用户企业权限 | sys/admin |
| `/api/users/{id}/companies` | PUT | 设置用户企业权限 | sys/admin |

**角色创建规则**（CREATABLE_ROLES）：
- `sys`: 可创建所有角色
- `admin`: 可创建 admin/firm/group/enterprise
- `firm`: 可创建 firm/enterprise
- `group`: 可创建 group/enterprise
- `enterprise`: 不可创建用户

#### 2.4.4 Profile Report 路由 (api/routes/profile_report.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/profile/{taxpayer_id}/report` | POST | 生成报告（SSE 流式） |
| `/api/profile/reports` | GET | 报告列表（分页） |
| `/api/profile/reports/{id}` | GET | 报告详情 |
| `/api/profile/reports/{id}` | DELETE | 删除报告 |

**权限**：
- `sys`/`admin`: 可查看所有报告
- 其他角色: 仅可查看自己的报告
- 删除: `sys`/`admin` 或报告所有者

### 2.5 服务层详解

#### 2.5.1 Query Cache (api/services/query_cache.py) - L1 缓存

```python
class QueryCache:
    """L1 缓存：完整查询结果"""
    
    # 缓存键：MD5(company_id|normalized_query|response_mode)
    # 存储：cache/{hash}.json
    # 内容：{result, route, interpretation, display_data, ...}
    
    def get_cached_query(company_id, query, response_mode) -> dict
    def save_query_cache(key, data)
    def update_cache_interpretation(key, interpretation)
    def invalidate_by_company(company_id, period_year=None, period_month=None)
```

**LRU 淘汰**：max 1200 文件，超出时删除最旧文件

#### 2.5.2 Template Cache (api/services/template_cache.py) - L2 缓存

```python
class TemplateCache:
    """L2 缓存：SQL 模板"""
    
    # 域感知缓存键策略：
    # - 财务报表：MD5(query|mode|fs|accounting_standard)
    # - VAT：MD5(query|mode|vat|taxpayer_type)
    # - EIT：MD5(query|mode|eit)
    # - 跨域：同上策略
    
    # 单域模板结构：
    # {sql_template, domain, views, ...}
    
    # 跨域模板结构：
    # {cache_domain: "cross_domain", sub_templates: [...], 
    #  subdomains: [...], cross_domain_operation: "compare|ratio|..."}
    
    def get_template(query, mode, domain, taxpayer_type, accounting_standard)
    def save_template(key, template_data)
```

**LRU 淘汰**：max 600 文件

#### 2.5.3 Data Quality (api/services/data_quality.py)

```python
class DataQualityChecker:
    """数据质量检查器"""
    
    # 5 类检查
    CHECK_CATEGORIES = [
        "internal_consistency",  # 内部一致性
        "reasonableness",        # 合理性
        "cross_table",          # 跨表一致性
        "period_continuity",    # 期间连续性
        "completeness"          # 完整性
    ]
    
    # 检查规则 ID 前缀映射
    # SB=account_balance, BS=balance_sheet, IS=income_statement
    # CF=cash_flow, VAT=vat_return, EIT=eit_return, INV=invoice
    
    def check_company(taxpayer_id, year, month) -> DomainCheckResult
```

---

## 3. NL2SQL 流水线

### 3.1 流水线入口 (mvp_pipeline.py)

```python
def run_pipeline_stream(
    user_query: str,
    db_path: str = None,
    response_mode: str = "detailed",
    conversation_history: list = None,
    conversation_depth: int = 3,
    original_query: str = None  # 用于 tax_incentive/regulation 路由
) -> Generator[dict, None, None]
```

**返回值**：SSE 事件生成器
- `{"type": "stage", "route": str, "text": str}`
- `{"type": "chunk", "text": str}`
- `{"type": "done", "result": dict}`

### 3.2 执行路径选择

```
用户查询
    ↓
意图路由 (IntentRouter.classify)
    ↓
┌─────────────┬─────────────┬─────────────┐
│ financial   │  tax_       │ regulation  │
│ _data       │  incentive  │             │
└──────┬──────┴──────┬──────┴──────┬──────┘
       ↓             ↓             ↓
多轮对话检测        FTS5搜索      Coze API
(ConversationManager) ↓             ↓
       ↓         LLM摘要       SSE返回
┌──────┴──────┐    ↓
│ Tier 2混合  │   返回
│ 分析检测    │
└──────┬──────┘
       ↓
┌──────┴──────┐
│ 是 → 混合分析│
│ 执行器      │
└──────┬──────┘
       ↓
   LLM税务筹划
   专家生成报告
       ↓
    返回
       
否 → Tier 1多轮
    实体继承
       ↓
实体预处理
(EntityPreprocessor)
       ↓
┌──────┬──────┬──────┬──────┐
│指标  │概念  │跨域  │标准  │
│路径  │路径  │路径  │路径  │
└──┬───┴──┬───┴──┬───┴──┬───┘
   ↓      ↓      ↓      ↓
确定   确定   拆分   Stage 1
性计算 性SQL  子查询  意图解析
   ↓      ↓      ↓      ↓
返回   返回   合并   Stage 2
结果   结果   结果   SQL生成
                      ↓
                   SQL审计
                      ↓
                   SQL执行
                      ↓
                   结果格式化
                      ↓
                    返回
```

### 3.3 意图路由 (modules/intent_router.py)

```python
class IntentRouter:
    def classify(self, question: str, db_conn=None) -> str:
        """
        返回: 'financial_data' | 'tax_incentive' | 'regulation'
        """
        # Layer -2: 财务数据优先
        # 数据类关键词 + 税种/财务术语同时出现 → financial_data
        
        # Layer -1: 知识库优先
        # 流程/操作类关键词 → regulation
        
        # Layer 0: 企业数据查询
        # 纳税人名称匹配（含模糊前缀）→ financial_data
        
        # Layer 1: 优惠/政策/法规关键词分类
        # 优惠关键词 → tax_incentive
        # 法规关键词 → regulation
        # 默认 → financial_data
```

**配置来源**：`config/tax_query_config.json`（热重载）

### 3.4 实体预处理 (modules/entity_preprocessor.py)

```python
def detect_entities(query: str, db_conn=None, conversation_history=None) -> dict:
    """
    返回实体字典:
    {
        "taxpayer_id": str,      # 纳税人识别号
        "taxpayer_name": str,    # 纳税人名称
        "taxpayer_type": str,    # 纳税人类型（一般纳税人/小规模纳税人）
        "period_year": int,      # 期间年份
        "period_month": int,     # 期间月份
        "period_quarter": int,   # 期间季度
        "domain": str,           # 检测域
        "domain_hint": str,      # 域提示
        "accounting_standard": str,  # 会计准则
        ...
    }
    """
```

**处理步骤**：

1. **相对日期解析**
   - "今年3月" → "2026年3月"
   - "去年12月" → "2025年12月"
   - "上个月" → 上个月
   - "上个季度" → 上季度范围

2. **实体提取**（正则表达式）
   - 纳税人名称匹配（模糊前缀）
   - 期间提取（年、月、季度）
   - 纳税人类型推断

3. **域检测**（优先级顺序）
   - 财务指标（"财务指标"、"毛利率"、"ROE"等）
   - 现金流量（无重叠关键词）
   - 科目余额（"期初"、"借"/"贷"、"发生额"）
   - 利润表（"本期金额"/"本年累计"）
   - 资产负债表（"年初"/"期初"）
   - 企业所得税（"年度"/"季度"）
   - 发票（"发票"、"进项"/"销项"）
   - 增值税（默认）
   - 跨域升级（检测到多域关键词）

4. **同义词规范化**（最长匹配优先）
   - 9 个同义词表，300+ 映射
   - 域感知：不同域/会计准则/纳税人类型使用不同映射

5. **视图选择**
   ```python
   def get_scope_view(domain, taxpayer_type, accounting_standard) -> str:
       # 财务报表：按会计准则分流
       #   一般纳税人/企业会计准则 → vw_profit_eas
       #   小规模纳税人/小企业会计准则 → vw_profit_sas
       # VAT：按纳税人类型分流
       #   一般纳税人 → vw_vat_return_general
       #   小规模纳税人 → vw_vat_return_small
   ```

### 3.5 指标路径 (modules/metric_calculator.py)

```python
# 22 个预定义指标
METRIC_FORMULAS = {
    "资产负债率": {
        "label": "资产负债率",
        "unit": "%",
        "formula": "总负债 / 总资产 * 100",
        "sources": {
            "总负债": {"domain": "balance_sheet", "column": "负债合计_end"},
            "总资产": {"domain": "balance_sheet", "column": "资产合计_end"}
        }
    },
    # ... 其他 21 个指标
}

def detect_computed_metrics(query: str) -> list:
    """检测查询中的指标名称（支持同义词）"""

def compute_metric(metric_name: str, taxpayer_id: str, 
                   year: int, month: int = None) -> dict:
    """确定性计算指标值，无 LLM 调用"""
```

**特点**：
- 确定性计算，无 LLM 调用
- 响应时间：100-300ms
- 支持同义词（如 "ROE" → "净资产收益率"）

### 3.6 概念路径 (modules/concept_registry.py)

```python
# 326 个预注册财务概念
CONCEPTS = {
    "货币资金": {
        "domain": "balance_sheet",
        "type": "direct",  # direct|computed|aggregated
        "columns": {
            "ASBE": ["货币资金_end"],
            "ASSE": ["货币资金_SAS_end"]
        }
    },
    "存货增加额": {
        "domain": "balance_sheet",
        "type": "computed",
        "formula": "存货_end - 存货_begin"
    },
    # ... 其他概念
}

def resolve_concepts(query: str, domain: str, 
                     accounting_standard: str) -> list:
    """解析查询中的概念（支持模糊匹配）"""

def build_concept_sql(concepts: list, entities: dict) -> str:
    """构建确定性 SQL（无 LLM）"""
```

**概念类型**：
- `direct`: 直接取值
- `computed`: 计算值（如 期末-期初）
- `aggregated`: 聚合值（如 季度求和）

**季度策略**：
- `sum_months`: 聚合 3 个月
- `quarter_end`: 取季度末月份

### 3.7 跨域路径 (modules/cross_domain_calculator.py)

```python
def detect_cross_domain_operation(query: str, entities: dict) -> dict:
    """
    检测跨域操作类型:
    - compare: 对比（并排显示）
    - ratio: 比率（除法计算）
    - reconcile: 核对（差异检查）
    - list: 列表（并集）
    """

def execute_cross_domain(query: str, operation: str, 
                         subdomains: list, entities: dict) -> dict:
    """
    执行跨域查询:
    1. 拆分为子域查询
    2. 每个子域执行标准路径
    3. 使用 UNION ALL 合并结果
    4. 对齐输出 Schema
    """
```

### 3.8 标准路径 - Stage 1 (modules/intent_parser.py)

```python
def parse_intent(query: str, entities: dict, 
                 conversation_history: list = None) -> dict:
    """
    Stage 1: 意图解析（LLM 调用）
    
    返回:
    {
        "domain": str,           # 确认域
        "views": [str],          # 涉及的视图
        "metrics": [str],        # 指标列表
        "filters": {             # 过滤条件
            "taxpayer_id": str,
            "period_year": int,
            "period_month": int,
            ...
        },
        "need_clarification": bool,  # 是否需要澄清
        "clarification_question": str  # 澄清问题
    }
    """
```

**Prompt 模板**：`prompts/stage1_system.txt`

**多轮对话支持**：传递最近 2 轮对话（4 条消息）作为上下文

### 3.9 约束注入 (modules/constraint_injector.py)

```python
def inject_constraints(intent_result: dict, entities: dict) -> dict:
    """
    根据 Stage 1 输出生成约束:
    {
        "allowed_views": [str],      # 允许查询的视图白名单
        "allowed_columns": [str],    # 允许查询的列白名单
        "max_rows": int,             # 最大返回行数
        "required_filters": [str]    # 必需的过滤条件
    }
    """
```

### 3.10 标准路径 - Stage 2 (modules/sql_writer.py)

```python
def generate_sql(intent: dict, constraints: dict, 
                 query: str, domain: str) -> str:
    """
    Stage 2: SQL 生成（LLM 调用）
    
    输入: Stage 1 意图 + 约束条件
    输出: 可执行的 SELECT SQL
    
    Prompt 选择: prompts/stage2_{domain}.txt
    """
```

**域特定 Prompt**（9 个）：
- `stage2_vat.txt`
- `stage2_eit.txt`
- `stage2_balance_sheet.txt`
- `stage2_profit.txt`
- `stage2_cash_flow.txt`
- `stage2_account_balance.txt`
- `stage2_financial_metrics.txt`
- `stage2_invoice.txt`
- `stage2_cross_domain.txt`

### 3.11 SQL 审计 (modules/sql_auditor.py)

```python
def audit_sql(sql: str, domain: str, constraints: dict) -> dict:
    """
    SQL 审计：硬阻断 + 软阻断 + 重试
    
    返回:
    {
        "passed": bool,
        "error_type": str,       # hard_block|soft_block|domain_specific
        "error_message": str,
        "retryable": bool        # 是否可重试
    }
    """
```

**硬阻断规则**（10 条）：
1. 非 SELECT 语句
2. 多语句（分号分隔）
3. 非允许视图
4. 非允许列
5. 缺少 taxpayer_id 过滤
6. 缺少 period 过滤
7. 无 LIMIT
8. SELECT *
9. 危险函数（sleep, load_file, ...）
10. 表别名前缀的 period_year*100+period_month 模式（误拦截保护）

**软阻断规则**（域特定）：
- EIT 季度视图需 `period_quarter` 过滤
- 月度域需 `period_month` 过滤
- 利润/现金流量表需 `time_range` 验证

**重试机制**：
- 审计失败 → 将错误信息反馈给 LLM → 重新生成 SQL（最多 1 次）
- SQL 执行失败 → 将错误信息（含 SQLite JOIN 限制提示）反馈给 LLM → 重试（最多 1 次）

### 3.12 多轮对话系统

#### 3.12.1 Tier 1: 财务数据多轮 (modules/conversation_manager.py)

```python
class ConversationManager:
    def prepare_context(self, history: list, current_query: str) -> dict:
        """
        准备多轮对话上下文:
        1. 检测依赖关系（实体继承）
        2. 代词解析（"它/那/这个" → 上一纳税人）
        3. 隐式继承（时间/公司/域）
        4. 特殊模式（"N月呢？" → 提取月份，继承年份）
        
        继承实体:
        - taxpayer_id, taxpayer_name, taxpayer_type
        - period_year, period_month
        - domain_hint
        """
```

#### 3.12.2 Tier 2: 跨路由混合分析

```python
# modules/mixed_analysis_detector.py
def detect_mixed_analysis(
    current_query: str,
    conversation_history: list,
    conversation_depth: int
) -> bool:
    """
    检测是否触发混合分析:
    1. 多轮对话已启用
    2. 历史包含 >=2 种不同路由
    3. 当前查询包含综合分析关键词
    """

# modules/mixed_analysis_executor.py
def execute_mixed_analysis(
    current_query: str,
    conversation_history: list
) -> Generator[str, None, None]:
    """
    执行混合分析:
    1. 提取所有历史 Q&A（不同路由）
    2. 构建完整上下文
    3. 调用 LLM 税务筹划专家（prompts/mixed_analysis_tax_planning.txt）
    4. 流式生成 6 节报告
    """
```

---

## 4. 数据库设计

### 4.1 ER 图概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              核心实体关系                                     │
│                                                                              │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐│
│  │  taxpayer_info  │◄────────┤  vat_return_    │         │  eit_annual_    ││
│  │  纳税人主表      │         │  general/small  │         │  filing/main/...││
│  │                 │◄────────┤  增值税申报     │         │  企业所得税年度 ││
│  │ - taxpayer_id   │         │                 │         │                 ││
│  │ - taxpayer_name │◄────────┤  eit_quarter_   │         │  fs_balance_    ││
│  │ - taxpayer_type │         │  filing/main    │         │  sheet_item     ││
│  │ - accounting_   │◄────────┤  企业所得税季度 │         │  资产负债表项目 ││
│  │   standard      │         │                 │         │                 ││
│  └────────┬────────┘         └─────────────────┘         └─────────────────┘│
│           │                                                                  │
│           │◄───────────────────────────────────────────────────────────────┤
│           │          ┌─────────────────┐         ┌─────────────────┐        │
│           │          │  fs_income_     │         │  fs_cash_flow_  │        │
│           │          │  statement_item │         │  item           │        │
│           │          │  利润表项目      │         │  现金流量表项目  │        │
│           │          └─────────────────┘         └─────────────────┘        │
│           │                                                                  │
│           │◄───────────────────────────────────────────────────────────────┤
│           │          ┌─────────────────┐         ┌─────────────────┐        │
│           │          │  account_       │         │  financial_     │        │
│           │          │  balance        │         │  metrics_item   │        │
│           │          │  科目余额        │         │  财务指标项目    │        │
│           │          └─────────────────┘         └─────────────────┘        │
│           │                                                                  │
│           │◄───────────────────────────────────────────────────────────────┤
│           │          ┌─────────────────┐         ┌─────────────────┐        │
│           └─────────►│  inv_spec_      │         │  profile_       │        │
│                      │  purchase/sales │         │  reports        │        │
│                      │  进销项发票      │         │  画像报告        │        │
│                      └─────────────────┘         └─────────────────┘        │
│                                                                              │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐│
│  │  users          │◄───────►│  user_company_  │         │  user_query_    ││
│  │  用户表          │         │  access         │         │  log            ││
│  │                 │         │  用户企业权限    │         │  查询日志        ││
│  └─────────────────┘         └─────────────────┘         └─────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 核心表结构

#### 4.2.1 纳税人主表 (taxpayer_info)

```sql
CREATE TABLE taxpayer_info (
    taxpayer_id           TEXT PRIMARY KEY,      -- 纳税人识别号
    taxpayer_name         TEXT NOT NULL,         -- 纳税人名称
    taxpayer_type         TEXT NOT NULL,         -- 纳税人类型（一般纳税人/小规模纳税人）
    registration_type     TEXT,                  -- 登记类型
    legal_representative  TEXT,                  -- 法定代表人
    establish_date        DATE,                  -- 成立日期
    industry_code         TEXT,                  -- 行业代码
    industry_name         TEXT,                  -- 行业名称
    tax_authority_code    TEXT,                  -- 税务机关代码
    tax_authority_name    TEXT,                  -- 税务机关名称
    region_code           TEXT,                  -- 地区代码
    region_name           TEXT,                  -- 地区名称
    credit_grade_current  TEXT,                  -- 当前信用等级
    credit_grade_year     INTEGER,               -- 信用等级年度
    accounting_standard   TEXT,                  -- 会计准则
    status                TEXT DEFAULT 'active', -- 状态
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_taxpayer_name ON taxpayer_info(taxpayer_name);
CREATE INDEX idx_taxpayer_type ON taxpayer_info(taxpayer_type);
```

#### 4.2.2 增值税申报表

**一般纳税人** (vat_return_general)：
```sql
CREATE TABLE vat_return_general (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    item_type           TEXT NOT NULL,  -- '一般项目'|'即征即退项目'
    time_range          TEXT NOT NULL,  -- '本月'|'累计'
    revision_no         INTEGER NOT NULL DEFAULT 0,
    -- 50+ 个申报字段（销售额、税额、抵扣、预缴等）
    sales_taxable_rate            NUMERIC,
    sales_goods                   NUMERIC,
    sales_services                NUMERIC,
    output_tax                    NUMERIC,
    input_tax                     NUMERIC,
    tax_payable                   NUMERIC,
    ...
    PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no)
);
```

**小规模纳税人** (vat_return_small)：
```sql
CREATE TABLE vat_return_small (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    item_type           TEXT NOT NULL,  -- '货物及劳务'|'服务不动产无形资产'
    time_range          TEXT NOT NULL,  -- '本期'|'累计'
    revision_no         INTEGER NOT NULL DEFAULT 0,
    -- 30+ 个申报字段（不同税率销售额、减免等）
    sales_3percent      NUMERIC,
    sales_5percent      NUMERIC,
    tax_due_total       NUMERIC,
    ...
    PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no)
);
```

#### 4.2.3 企业所得税申报表

**年度申报**（6 张表）：
- `eit_annual_filing`：主记录表（封面信息）
- `eit_annual_main`：主表（A100000）
- `eit_annual_basic_info`：基础信息表（A000000）
- `eit_annual_shareholder`：股东分红明细表
- `eit_annual_incentive_items`：优惠事项明细表（动态子行）

**季度申报**（3 张表）：
- `eit_quarter_filing`：主记录表
- `eit_quarter_main`：主表（A200000）
- `eit_quarter_incentive_items`：优惠事项明细表

#### 4.2.4 财务报表（EAV 纵表）

**资产负债表** (fs_balance_sheet_item)：
```sql
CREATE TABLE fs_balance_sheet_item (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    gaap_type           TEXT NOT NULL,  -- 'ASBE'|'ASSE'
    item_code           TEXT NOT NULL,  -- 项目编码
    revision_no         INTEGER NOT NULL DEFAULT 0,
    beginning_balance   NUMERIC,         -- 年初余额
    ending_balance      NUMERIC,         -- 期末余额
    item_name           TEXT,
    line_number         INTEGER,
    section             TEXT,
    PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)
);
```

**利润表** (fs_income_statement_item)：
```sql
CREATE TABLE fs_income_statement_item (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    gaap_type           TEXT NOT NULL,  -- 'CAS'|'SAS'
    item_code           TEXT NOT NULL,
    revision_no         INTEGER NOT NULL DEFAULT 0,
    current_amount      NUMERIC,         -- 本期金额
    cumulative_amount   NUMERIC,         -- 本年累计
    ...
);
```

**现金流量表** (fs_cash_flow_item)：
```sql
CREATE TABLE fs_cash_flow_item (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    gaap_type           TEXT NOT NULL,  -- 'CAS'|'SAS'
    item_code           TEXT NOT NULL,
    revision_no         INTEGER NOT NULL DEFAULT 0,
    current_amount      NUMERIC,         -- 本期金额
    cumulative_amount   NUMERIC,         -- 本年累计
    ...
);
```

#### 4.2.5 发票表

**进项发票** (inv_spec_purchase)：
```sql
CREATE TABLE inv_spec_purchase (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    invoice_format      TEXT NOT NULL,  -- '数电'|'非数电'
    invoice_pk          TEXT NOT NULL,  -- 发票主键
    line_no             INTEGER NOT NULL DEFAULT 1,
    invoice_code        TEXT,
    invoice_number      TEXT,
    seller_tax_id       TEXT,
    seller_name         TEXT,
    amount              REAL,
    tax_amount          REAL,
    total_amount        REAL,
    tax_category_code   TEXT,
    goods_name          TEXT,
    ...
    PRIMARY KEY (taxpayer_id, invoice_pk, line_no)
);
```

**销项发票** (inv_spec_sales)：
```sql
CREATE TABLE inv_spec_sales (
    taxpayer_id         TEXT NOT NULL,
    period_year         INTEGER NOT NULL,
    period_month        INTEGER NOT NULL,
    invoice_format      TEXT NOT NULL,
    invoice_pk          TEXT NOT NULL,
    line_no             INTEGER NOT NULL DEFAULT 1,
    buyer_tax_id        TEXT,
    buyer_name          TEXT,
    amount              REAL,
    tax_amount          REAL,
    ...
    PRIMARY KEY (taxpayer_id, invoice_pk, line_no)
);
```

#### 4.2.6 用户权限表

```sql
-- 用户表
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- bcrypt 哈希
    role          TEXT NOT NULL DEFAULT 'enterprise',
    display_name  TEXT,
    is_active     INTEGER DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login    TIMESTAMP,
    created_by    INTEGER REFERENCES users(id)
);

-- 用户-企业权限关联表
CREATE TABLE user_company_access (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    taxpayer_id TEXT NOT NULL REFERENCES taxpayer_info(taxpayer_id),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, taxpayer_id)
);
```

#### 4.2.7 日志表

```sql
-- 查询日志
CREATE TABLE user_query_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT,
    user_query        TEXT NOT NULL,
    normalized_query  TEXT,
    taxpayer_id       TEXT,
    taxpayer_name     TEXT,
    period_year       INTEGER,
    period_month      INTEGER,
    domain            TEXT,
    success           INTEGER DEFAULT 0,
    error_message     TEXT,
    generated_sql     TEXT,
    execution_time_ms INTEGER,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_ip           TEXT,
    user_agent        TEXT
);

-- 未匹配短语（用于优化同义词）
CREATE TABLE unmatched_phrases (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase           TEXT NOT NULL,
    context_query    TEXT,
    frequency        INTEGER DEFAULT 1,
    first_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status           TEXT DEFAULT 'pending',
    suggested_column TEXT,
    ...
);
```

#### 4.2.8 报告表

```sql
CREATE TABLE profile_reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    taxpayer_id   TEXT    NOT NULL,
    taxpayer_name TEXT    NOT NULL,
    year          INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    username      TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'generating',  -- generating|completed|failed
    content       TEXT,                                    -- Markdown 内容
    error_msg     TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at  TIMESTAMP
);

CREATE INDEX idx_profile_reports_taxpayer ON profile_reports(taxpayer_id, year);
CREATE INDEX idx_profile_reports_user ON profile_reports(user_id);
```

### 4.3 核心视图（18 个）

NL2SQL 流水线**只允许查询这些视图**，不允许直接查询明细表。

| 视图 | 说明 | 分流条件 |
|------|------|----------|
| `vw_vat_return_general` | 一般纳税人增值税 | taxpayer_type='一般纳税人' |
| `vw_vat_return_small` | 小规模纳税人增值税 | taxpayer_type='小规模纳税人' |
| `vw_eit_annual_main` | 企业所得税年度 | - |
| `vw_eit_quarter_main` | 企业所得税季度 | - |
| `vw_balance_sheet_eas` | 资产负债表（EAS） | gaap_type='ASBE' |
| `vw_balance_sheet_sas` | 资产负债表（SAS） | gaap_type='ASSE' |
| `vw_profit_eas` | 利润表（EAS） | gaap_type='CAS' |
| `vw_profit_sas` | 利润表（SAS） | gaap_type='SAS' |
| `vw_cash_flow_eas` | 现金流量表（EAS） | gaap_type='CAS' |
| `vw_cash_flow_sas` | 现金流量表（SAS） | gaap_type='SAS' |
| `vw_account_balance` | 科目余额 | - |
| `vw_inv_spec_purchase` | 进项发票 | - |
| `vw_inv_spec_sales` | 销项发票 | - |
| `vw_financial_metrics` | 财务指标 | - |
| `vw_enterprise_profile` | 企业画像（桩视图） | - |

**视图特点**：
- 自动 JOIN `taxpayer_info` 获取企业信息
- 使用 `ROW_NUMBER()` 窗口函数自动选择最新 `revision_no`
- 财务报表视图按会计准则分流
- VAT 视图按纳税人类型分流

### 4.4 同义词表（9 个）

| 表名 | 用途 | 映射数 |
|------|------|--------|
| `vat_synonyms` | 增值税 | 150+ |
| `eit_synonyms` | 企业所得税 | 80+ |
| `fs_balance_sheet_synonyms` | 资产负债表 | 200+ |
| `fs_income_statement_synonyms` | 利润表 | 180+ |
| `fs_cash_flow_synonyms` | 现金流量表 | 120+ |
| `account_synonyms` | 科目余额 | 100+ |
| `inv_synonyms` | 发票 | 50+ |
| `financial_metrics_synonyms` | 财务指标 | 60+ |
| `hr_employee_synonyms` | 人事（未集成） | - |

**表结构**：
```sql
CREATE TABLE vat_synonyms (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase        TEXT NOT NULL,        -- 自然语言短语
    column_name   TEXT NOT NULL,        -- 标准列名
    priority      INTEGER DEFAULT 1,    -- 优先级
    taxpayer_type TEXT,                 -- 适用纳税人类型
    scope_view    TEXT,                 -- 适用视图
    UNIQUE(phrase, column_name)
);
```

### 4.5 索引设计

**核心索引**：
```sql
-- 纳税人查询
CREATE INDEX idx_taxpayer_name ON taxpayer_info(taxpayer_name);
CREATE INDEX idx_taxpayer_type ON taxpayer_info(taxpayer_type);

-- 期间查询（所有申报表通用）
CREATE INDEX idx_vat_period ON vat_return_general(period_year, period_month);
CREATE INDEX idx_vat_taxpayer_period ON vat_return_general(taxpayer_id, period_year, period_month);
CREATE INDEX idx_vat_taxpayer_period_revision ON vat_return_general(taxpayer_id, period_year, period_month, revision_no DESC);

-- 财务报表
CREATE INDEX idx_bs_taxpayer_period_gaap ON fs_balance_sheet_item(taxpayer_id, period_year, period_month, gaap_type, revision_no DESC);

-- 发票
CREATE INDEX idx_inv_purchase_taxpayer_period ON inv_spec_purchase(taxpayer_id, period_year, period_month);
CREATE INDEX idx_inv_purchase_date ON inv_spec_purchase(invoice_date);

-- 日志
CREATE INDEX idx_query_log_taxpayer_period ON user_query_log(taxpayer_id, created_at DESC);
```

---

## 5. API 接口定义

### 5.1 认证接口

#### POST /api/auth/login

**请求**：
```json
{
  "username": "string",
  "password": "string"
}
```

**响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "display_name": "管理员",
    "company_ids": ["taxpayer1", "taxpayer2"]
  }
}
```

#### POST /api/auth/logout

**请求**：无

**响应**：`{"message": "Logged out"}`

#### GET /api/auth/me

**响应**：当前用户信息（同 login 的 user 字段）

### 5.2 聊天接口

#### POST /api/chat

**Content-Type**：`text/event-stream`

**请求体** (ChatRequest)：
```json
{
  "query": "华兴科技2025年1月增值税",
  "response_mode": "detailed",  // "concise" | "detailed"
  "company_id": "taxpayer_id",
  "thinking_mode": "think",     // "quick" | "think" | "deep"
  "conversation_history": [],
  "conversation_depth": 3
}
```

**SSE 响应**：
```
event: stage
data: {"route": "financial_data", "text": "正在分析财务数据..."}

event: done
data: {
  "type": "financial_data",
  "data": [...],
  "display_data": {
    "summary": {...},
    "table": {...},
    "chart": {...},
    "metadata": {...}
  },
  "interpretation": "数据解读文本...",
  "sql": "SELECT ...",
  "execution_time_ms": 1234
}
```

### 5.3 用户管理接口

#### GET /api/users

**权限**：sys/admin

**响应**：用户列表

#### POST /api/users

**权限**：按角色规则

**请求** (UserCreate)：
```json
{
  "username": "newuser",
  "password": "password123",
  "role": "enterprise",
  "display_name": "新用户",
  "company_ids": ["taxpayer1"]
}
```

#### PUT /api/users/{id}

**请求** (UserUpdate)：
```json
{
  "password": "newpassword",
  "role": "firm",
  "display_name": "新名称",
  "is_active": 1,
  "company_ids": ["taxpayer1", "taxpayer2"]
}
```

#### DELETE /api/users/{id}

**权限**：sys/admin

#### GET /api/users/{id}/companies

**响应**：用户可访问的企业列表

#### PUT /api/users/{id}/companies

**请求**：`{"company_ids": ["taxpayer1", "taxpayer2"]}`

### 5.4 企业接口

#### GET /api/companies

**响应**：
```json
{
  "companies": [
    {
      "taxpayer_id": "taxpayer1",
      "taxpayer_name": "华兴科技",
      "taxpayer_type": "一般纳税人"
    }
  ]
}
```

### 5.5 企业画像接口

#### GET /api/profile/{taxpayer_id}

**Query**：`?year=2025`

**响应**：
```json
{
  "basic_info": {...},
  "asset_structure": {...},
  "profit_data": {...},
  "cash_flow": {...},
  "growth_metrics": {...},
  "financial_metrics": {...},
  "tax_summary": {...},
  "invoice_summary": {...},
  "rd_innovation": {...},
  "cross_border": {...},
  "compliance_risk": {...}
}
```

### 5.6 画像报告接口

#### POST /api/profile/{taxpayer_id}/report

**Content-Type**：`text/event-stream`

**Query**：`?year=2025`

**SSE 响应**：
```
event: meta
data: {"report_id": 123}

event: stage
data: {"text": "正在收集企业数据..."}

event: chunk
data: {"text": "报告内容片段..."}

event: done
data: {"content": "完整报告Markdown", "status": "completed"}
```

#### GET /api/profile/reports

**Query**：`?taxpayer_id=&page=1&size=10`

**权限**：sys/admin 可查看所有，其他仅自己的

**响应**：分页报告列表

#### GET /api/profile/reports/{id}

**响应**：单报告详情（含 content）

#### DELETE /api/profile/reports/{id}

**权限**：sys/admin 或报告所有者

### 5.7 数据浏览器接口

#### GET /api/data-browser/tables

**Query**：`?domain=profit`

**响应**：可浏览的表列表

#### GET /api/data-browser/periods

**Query**：`?table=vw_profit_eas&taxpayer_id=xxx`

**响应**：可用期间列表

#### GET /api/data-browser/data

**Query**：`?table=vw_profit_eas&taxpayer_id=xxx&year=2025&month=1&mode=general`

**mode**：`general` | `raw`

**响应**：
```json
{
  "columns": [{"key": "...", "label": "...", "align": "...", "col_type": "..."}],
  "rows": [...],
  "total": 100
}
```

### 5.8 数据管理接口

#### GET /api/data-management/stats

**响应**：数据统计概览

#### GET /api/data-management/companies-overview

**响应**：企业数据概览

#### POST /api/data-management/quality-check

**请求**：
```json
{
  "taxpayer_id": "taxpayer1",
  "year": 2025,
  "month": 1
}
```

**响应**：
```json
{
  "overall_pass_rate": 0.95,
  "categories": {
    "internal_consistency": {...},
    "reasonableness": {...},
    "cross_table": {...},
    "period_continuity": {...},
    "completeness": {...}
  },
  "issues": [...]
}
```

### 5.9 解读接口

#### POST /api/interpret

**Content-Type**：`text/event-stream`

**请求** (InterpretRequest)：
```json
{
  "query": "华兴科技2025年1月增值税",
  "result": {...},  // 查询结果
  "response_mode": "detailed",
  "company_id": "taxpayer1",
  "cache_key": "...",
  "conversation_history": []
}
```

**SSE 响应**：流式解读文本

### 5.10 工作台接口

#### GET /api/dashboard/summary

**Query**：`?company_id=taxpayer1`

**响应**：
```json
{
  "health_score": 85,
  "top_metrics": [...],
  "tax_summary": {...},
  "data_quality": {...},
  "recent_activity": [...]
}
```

### 5.11 缓存统计接口

#### GET /api/cache/stats

**响应**：
```json
{
  "l1": {
    "file_count": 100,
    "hit_count": 1000,
    "hit_rate": 0.65
  },
  "l2": {
    "file_count": 50,
    "hit_count": 500,
    "hit_rate": 0.45
  }
}
```

---

## 6. 前端架构

### 6.1 技术栈

- **框架**：React 19.x
- **构建工具**：Vite 7.x
- **样式**：CSS Modules
- **图表**：Chart.js + react-chartjs-2
- **Markdown**：react-markdown
- **图标**：lucide-react
- **HTTP**：原生 fetch + EventSource (SSE)

### 6.2 项目结构

```
frontend/src/
├── App.jsx                     # 入口：7页面路由
├── App.module.css              # 全局样式
├── main.jsx                    # React 渲染入口
├── components/                 # 组件目录
│   ├── Badge/                  # 徽章组件
│   ├── CaptchaModal/           # 验证码弹窗
│   ├── ChartRenderer/          # 图表渲染
│   ├── ChatArea/               # 聊天区域
│   │   ├── ChatArea.jsx
│   │   └── ChatArea.module.css
│   ├── ChatInput/              # 聊天输入
│   ├── ChatMessage/            # 聊天消息
│   ├── CompanyProfile/         # 企业画像（18文件）
│   │   ├── CompanyProfile.jsx
│   │   ├── ProfileHeader.jsx
│   │   ├── ProfileSection.jsx
│   │   └── ...
│   ├── Dashboard/              # 工作台（10文件）
│   │   ├── Dashboard.jsx
│   │   ├── widgets/            # 6个Widget
│   │   │   ├── HealthScoreWidget.jsx
│   │   │   ├── TaxSummaryWidget.jsx
│   │   │   ├── DataQualityWidget.jsx
│   │   │   ├── RecentQueriesWidget.jsx
│   │   │   ├── QuickShortcutsWidget.jsx
│   │   │   └── ClientPortfolioWidget.jsx
│   │   └── ...
│   ├── DataManagement/         # 数据管理（13文件）
│   ├── Footer/                 # 底部
│   ├── GrowthTable/            # 增长表格
│   ├── Header/                 # 顶部导航
│   ├── HistoryPanel/           # 历史面板
│   ├── Login/                  # 登录页
│   ├── PipelineDetail/         # 流水线详情
│   ├── ProfileReport/          # 画像报告
│   ├── ReportList/             # 报告列表
│   ├── ResultTable/            # 结果表格
│   ├── Sidebar/                # 侧边栏
│   └── SystemSettings/         # 系统设置（5文件）
├── hooks/                      # 自定义 Hooks
│   └── useAuth.js              # 认证 Hook
├── services/                   # API 服务
│   ├── api.js                  # API 基础配置
│   └── chatService.js          # 聊天服务
├── utils/                      # 工具函数
└── config/                     # 前端配置
```

### 6.3 页面路由

```javascript
// App.jsx
const [currentPage, setCurrentPage] = useState('dashboard');

switch (currentPage) {
  case 'dashboard':        // 工作台
  case 'chat':             // AI智问
  case 'profile':          // 企业画像
  case 'profile-report':   // 画像报告
  case 'profile-report-list': // 报告列表
  case 'data-management':  // 数据管理
  case 'settings':         // 系统设置
}
```

### 6.4 核心组件

#### 6.4.1 ChatArea

**职责**：聊天交互核心

**状态**：
```javascript
const [messages, setMessages] = useState([]);        // 消息列表
const [isLoading, setIsLoading] = useState(false);   // 加载状态
const [inputText, setInputText] = useState('');      // 输入文本
```

**核心方法**：
```javascript
// 发送消息
const handleSend = async () => {
  // 1. 添加用户消息
  // 2. 创建 SSE 连接
  // 3. 处理 SSE 事件（stage/chunk/done）
  // 4. 更新消息列表
};

// 重新执行历史查询
const handleReinvoke = async (historyIndex, thinkingMode) => {
  // POST /api/chat/history/reinvoke
};
```

**SSE 处理**：
```javascript
const eventSource = new EventSource('/api/chat', {
  headers: { 'Authorization': `Bearer ${token}` }
});

eventSource.addEventListener('stage', (e) => {
  const data = JSON.parse(e.data);
  // 显示阶段信息
});

eventSource.addEventListener('done', (e) => {
  const result = JSON.parse(e.data);
  // 显示最终结果（表格、图表、解读）
  eventSource.close();
});
```

#### 6.4.2 Dashboard

**职责**：工作台数据展示

**数据获取**：
```javascript
useEffect(() => {
  fetch(`/api/dashboard/summary?company_id=${selectedCompanyId}`)
    .then(res => res.json())
    .then(data => setDashboardData(data));
}, [selectedCompanyId]);
```

**Widget 组件**：
- `HealthScoreWidget`：健康评分卡片
- `TaxSummaryWidget`：税负汇总
- `DataQualityWidget`：数据质量预警
- `RecentQueriesWidget`：最近查询
- `QuickShortcutsWidget`：快捷查询
- `ClientPortfolioWidget`：客户组合（firm/group/admin）

#### 6.4.3 CompanyProfile

**职责**：企业画像展示

**数据获取**：
```javascript
fetch(`/api/profile/${taxpayerId}?year=${year}`)
  .then(res => res.json())
  .then(data => setProfileData(data));
```

**组件结构**：
```jsx
<ProfileHeader data={profileData.basic_info} />
<ProfileSection title="资产结构" data={profileData.asset_structure} />
<ProfileSection title="利润数据" data={profileData.profit_data} />
// ... 其他 9 个维度
```

#### 6.4.4 ProfileReport

**职责**：报告展示与打印

**SSE 报告生成**：
```javascript
const eventSource = new EventSource(
  `/api/profile/${taxpayerId}/report?year=${year}`
);

eventSource.addEventListener('chunk', (e) => {
  const { text } = JSON.parse(e.data);
  setContent(prev => prev + text);  // 流式追加
});
```

**打印功能**：
```javascript
const handlePrint = () => {
  window.print();  // 使用 @media print CSS 隐藏非内容元素
};
```

### 6.5 状态管理

系统使用 React 原生状态管理（无 Redux）：

```javascript
// App.jsx - 全局状态
const [messages, setMessages] = useState([]);
const [historyItems, setHistoryItems] = useState([]);
const [responseMode, setResponseMode] = useState('detailed');
const [thinkingMode, setThinkingMode] = useState('think');
const [selectedCompanyId, setSelectedCompanyId] = useState('');
const [currentPage, setCurrentPage] = useState('dashboard');

// useAuth Hook - 认证状态
const { user, loading, handleLogin, handleLogout, isAdmin } = useAuth();
```

### 6.6 认证流程

```javascript
// hooks/useAuth.js
const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // 初始化：从 localStorage 读取 token
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUserInfo(token);
    }
    setLoading(false);
  }, []);
  
  // 登录
  const handleLogin = async (username, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    const { access_token, user } = await res.json();
    localStorage.setItem('token', access_token);
    setUser(user);
  };
  
  // 登出
  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };
  
  return { user, loading, handleLogin, handleLogout };
};
```

---

## 7. 缓存体系

### 7.1 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        查询请求                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │  思考模式判断    │
                    │  quick/think/deep│
                    └────────┬────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   ┌─────────┐        ┌─────────┐          ┌─────────┐
   │  Quick  │        │  Think  │          │  Deep   │
   │  快速   │        │  思考   │          │  深度   │
   └────┬────┘        └────┬────┘          └────┬────┘
        ↓                  ↓                    ↓
   L1 缓存查找         L1 缓存查找            跳过缓存
   (query_cache)      (query_cache)          ↓
        ↓                  ↓              执行流水线
   ┌────┴────┐        ┌────┴────┐          ↓
   │ 命中    │        │ 命中    │      L1 缓存写入
   ↓         ↓        ↓         ↓          ↓
 返回      执行    返回      执行      返回结果
 缓存      流水线  缓存      流水线
 结果      ↓       结果      ↓
        L1写入        ┌────┴────┐
        ↓            重新解读   执行
   返回结果           (LLM)     流水线
                      ↓        ↓
                 更新缓存解读  L1写入
                      ↓        ↓
                 返回结果    返回结果
```

### 7.2 L1 缓存 - 完整结果缓存

**实现**：`api/services/query_cache.py`

**缓存键**：
```python
cache_key = MD5(f"{company_id}|{normalized_query}|{response_mode}")
```

**存储位置**：`cache/{cache_key}.json`

**内容结构**：
```json
{
  "result": {...},           // 查询结果
  "route": "financial_data", // 路由类型
  "interpretation": "...",   // 数据解读
  "display_data": {...},     // 显示数据
  "created_at": "...",
  "accessed_at": "...",
  "access_count": 10
}
```

**LRU 淘汰**：
- Max 1200 文件（`QUERY_CACHE_MAX_FILES_L1`）
- 超出时删除最旧文件（按 `accessed_at`）

**API**：
```python
class QueryCache:
    def get_cached_query(self, company_id, query, response_mode) -> dict
    def save_query_cache(self, key, data)
    def update_cache_interpretation(self, key, interpretation)
    def invalidate_by_company(self, company_id, year=None, month=None)
```

### 7.3 L2 缓存 - SQL 模板缓存

**实现**：`api/services/template_cache.py`

**目的**：跨公司复用相同类型的 SQL 模板

**域感知缓存键策略**：

| 域类型 | 缓存键组成 | 模板数/查询 |
|--------|-----------|------------|
| 财务报表 | `MD5(query\|mode\|fs\|accounting_standard)` | 2（EAS/SAS）|
| VAT | `MD5(query\|mode\|vat\|taxpayer_type)` | 2（一般/小规模）|
| EIT | `MD5(query\|mode\|eit)` | 1 |
| 跨域 | 同上策略 | 最多 4（2×2）|

**单域模板结构**：
```json
{
  "sql_template": "SELECT ... WHERE taxpayer_id = ? AND period_year = ?",
  "domain": "vat",
  "views": ["vw_vat_return_general"],
  "created_at": "..."
}
```

**跨域模板结构**：
```json
{
  "cache_domain": "cross_domain",
  "sub_templates": [
    {"domain": "vat", "sql_template": "..."},
    {"domain": "profit", "sql_template": "..."}
  ],
  "subdomains": ["vat", "profit"],
  "cross_domain_operation": "compare",
  "created_at": "..."
}
```

**使用流程**：
```python
# 1. 查找模板
template = template_cache.get_template(
    query, mode, domain, taxpayer_type, accounting_standard
)

if template:
    # 2. 实例化 SQL（替换参数）
    if template["cache_domain"] == "cross_domain":
        for sub in template["sub_templates"]:
            sql = sub["sql_template"].replace("?", actual_value)
            # 执行子查询
        # 合并结果
    else:
        sql = template["sql_template"].replace("?", actual_value)
        # 执行查询
else:
    # 3. 未命中，执行完整流水线
    # 4. 保存模板
    template_cache.save_template(key, template_data)
```

**LRU 淘汰**：Max 600 文件

### 7.4 三模式缓存交互

| 模式 | 缓存行为 | LLM 调用 | 响应时间 |
|------|----------|----------|----------|
| **Quick** | 直接返回 L1 缓存 | 无 | < 50ms |
| **Think** | 返回 L1 缓存 + need_reinterpret=True | 重新解读 | 1-2s |
| **Deep** | 跳过所有缓存 | 完整流水线 | 2-5s |

**Think 模式流程**：
```python
# 1. 返回缓存结果（不含解读）
yield {"type": "done", "result": cached_result, "need_reinterpret": True}

# 2. 前端检测到 need_reinterpret=True
# 3. 自动调用 POST /api/interpret
# 4. 后端调用 interpretation_service.interpret_stream()
# 5. 流式返回新解读
# 6. 前端更新显示
# 7. 后端更新 L1 缓存中的 interpretation
```

---

## 8. 安全设计

### 8.1 SQL 注入防护

**多层防护**：

1. **参数化查询**
   ```python
   cursor.execute("SELECT * FROM view WHERE id = ?", (taxpayer_id,))
   ```

2. **SQL 审计白名单**
   - 只允许查询 18 个核心视图
   - 只允许查询白名单列
   - 禁止 `SELECT *`

3. **硬阻断规则**
   - 非 SELECT 语句
   - 多语句（分号）
   - 危险函数（sleep, load_file, ...）

### 8.2 XSS 防护

1. **React 自动转义**
   - JSX 自动转义输出
   - `dangerouslySetInnerHTML` 谨慎使用

2. **CSP 头**
   ```python
   # FastAPI 中间件添加 CSP
   response.headers["Content-Security-Policy"] = "default-src 'self'..."
   ```

### 8.3 认证安全

1. **JWT 配置**
   - 算法：HS256
   - 过期：24 小时
   - 密钥：强随机字符串

2. **密码安全**
   - 哈希算法：bcrypt
   - Cost factor：12

3. **验证码**
   - 登录前需通过验证码
   - 最多 3 次尝试

### 8.4 数据访问控制

1. **企业级隔离**
   ```python
   async def require_company_access(user, company_id):
       if user.role in ['sys', 'admin']:
           return
       if company_id not in user.company_ids:
           raise HTTPException(403, "无权访问该企业")
   ```

2. **角色权限检查**
   ```python
   if current_user.role not in ['sys', 'admin']:
       raise HTTPException(403, "权限不足")
   ```

### 8.5 审计日志

**user_query_log 表**：
- 记录所有查询请求
- 包含：user_id, query, SQL, 执行时间, 是否成功
- 用于：审计、分析、优化

---

## 9. 配置体系

### 9.1 主配置 (config/settings.py)

```python
# 数据库
DB_PATH = PROJECT_ROOT / "database" / "fintax_ai.db"

# DeepSeek API
LLM_API_KEY = "sk-..."
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 60

# 流水线限制
MAX_ROWS = 1000
MAX_PERIOD_MONTHS = 36

# L1 缓存
QUERY_CACHE_ENABLED = True
QUERY_CACHE_DIR = PROJECT_ROOT / "cache"
QUERY_CACHE_MAX_FILES_L1 = 1200

# L2 缓存
QUERY_CACHE_ENABLED_L2 = True
QUERY_CACHE_MAX_FILES_L2 = 600
QUERY_CACHE_L2_PREFIX = "template_"

# JWT
JWT_SECRET_KEY = "[REMOVED_JWT_SECRET]"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 1440

# 解读
INTERPRETATION_ENABLED = True
INTERPRETATION_MAX_TOKENS = 2000
INTERPRETATION_TEMPERATURE = 0.3

# 多轮对话
CONVERSATION_ENABLED = True
CONVERSATION_MAX_TURNS = 3
CONVERSATION_TOKEN_BUDGET = 4000

# 混合分析
MIXED_ANALYSIS_ENABLED = True
MIXED_ANALYSIS_MIN_ROUTES = 2
MIXED_ANALYSIS_MAX_CONTEXT_TOKENS = 8000

# 画像报告
PROFILE_REPORT_ENABLED = True
PROFILE_REPORT_MAX_TOKENS = 8000
PROFILE_REPORT_TEMPERATURE = 0.3
```

### 9.2 外部化配置目录

```
config/
├── concepts/              # 326 个财务概念（JSON）
│   ├── balance_sheet/
│   ├── profit/
│   ├── cash_flow/
│   ├── vat/
│   ├── eit/
│   └── cross_domain/
├── domain_detection/      # 域检测关键词
│   └── keywords.json
├── metrics/               # 22 个财务指标公式
│   └── metric_formulas.json
├── schema/                # Schema 目录
│   └── catalog.json
├── cross_domain/          # 跨域操作配置
├── display/               # 显示格式化配置
├── pipeline/              # 流水线阶段配置
├── profile/               # 企业画像配置
├── auth/                  # 认证和角色配置
├── data_browser/          # 数据浏览器配置
└── data_management/       # 数据管理配置
```

### 9.3 热重载配置

```python
# config/config_loader.py
class ConfigLoader:
    def __init__(self, config_path):
        self._config_path = config_path
        self._config = None
        self._mtime = 0
    
    def get_config(self):
        # 检查文件修改时间
        current_mtime = os.path.getmtime(self._config_path)
        if current_mtime > self._mtime:
            # 重新加载
            with open(self._config_path) as f:
                self._config = json.load(f)
            self._mtime = current_mtime
        return self._config
```

### 9.4 扩展指南

#### 添加新财务指标

编辑 `config/metrics/metric_formulas.json`：
```json
{
  "新指标名称": {
    "label": "新指标",
    "unit": "%",
    "formula": "变量A / 变量B * 100",
    "sources": {
      "变量A": {"domain": "profit", "column": "营业收入"},
      "变量B": {"domain": "profit", "column": "营业成本"}
    }
  }
}
```

#### 添加新数据域

1. **数据库**：
   ```sql
   CREATE TABLE new_domain (...);
   CREATE VIEW vw_new_domain AS ...;
   ```

2. **Schema 目录**：
   ```python
   # modules/schema_catalog.py
   SCHEMA_CATALOG = {
       "new_domain": {
           "views": ["vw_new_domain"],
           "columns": ["col1", "col2", ...]
       }
   }
   ```

3. **Prompt**：
   ```
   # prompts/stage2_new_domain.txt
   ```

4. **域检测**：
   ```python
   # modules/entity_preprocessor.py
   def detect_domain(query):
       if "新域关键词" in query:
           return "new_domain"
   ```

5. **同义词**：
   ```sql
   CREATE TABLE new_domain_synonyms (...);
   ```

#### 切换 LLM 提供商

```python
# config/settings.py
LLM_API_BASE = "https://your-provider.com/v1"
LLM_API_KEY = "your-key"
LLM_MODEL = "your-model"
```

---

## 附录

### A. 核心文件索引

| 文件路径 | 说明 | 行数 |
|----------|------|------|
| `api/main.py` | FastAPI 入口 | ~85 |
| `mvp_pipeline.py` | NL2SQL 流水线 | ~900 |
| `config/settings.py` | 主配置 | ~104 |
| `database/init_db.py` | 数据库 DDL | ~1631 |
| `modules/entity_preprocessor.py` | 实体预处理 | ~800 |
| `modules/sql_auditor.py` | SQL 审计 | ~400 |
| `frontend/src/App.jsx` | 前端入口 | ~163 |

### B. 性能指标

| 层级 | 命中率 | 响应时间 | 适用场景 |
|------|--------|----------|----------|
| L1 缓存 | 60-70% | <50ms | 重复查询 |
| L2 缓存 | 40-50% | 200-500ms | 同类型跨公司查询 |
| 确定性计算 | N/A | 100-300ms | 指标/概念查询 |
| 完整流水线 | N/A | 2-5s | 首次复杂查询 |

### C. 术语表

| 术语 | 英文 | 说明 |
|------|------|------|
| NL2SQL | Natural Language to SQL | 自然语言转 SQL |
| EAV | Entity-Attribute-Value | 实体-属性-值（纵表）|
| SSE | Server-Sent Events | 服务器发送事件 |
| FTS5 | Full-Text Search 5 | SQLite 全文检索 |
| GAAP | Generally Accepted Accounting Principles | 会计准则 |
| EAS | Enterprise Accounting Standards | 企业会计准则 |
| SAS | Small Accounting Standards | 小企业会计准则 |
| VAT | Value Added Tax | 增值税 |
| EIT | Enterprise Income Tax | 企业所得税 |

---

*文档结束*
