# 实施计划：意图路由 + 税收优惠查询 + 外部法规API

## Context

现有 fintax_ai 系统包含9个基于 `fintax_ai.db` 的财税数据查询域，通过两阶段 NL2SQL 管线处理用户查询。现需新增：
1. **意图路由层** — 在现有域检测之前，将查询分流到三条路径
2. **税收优惠查询** — 基于本地 `tax_incentives.db`（1522条政策，FTS5已建好）
3. **外部法规查询** — 对接 Coze RAG API

核心约束：现有9个域的查询逻辑**零改动**。

---

## 新增文件

| 文件 | 用途 |
|------|------|
| `modules/intent_router.py` | 三路意图路由器，多层关键词分类 + 热更新配置 |
| `modules/tax_incentive_query.py` | 税收优惠四级搜索（结构化→实体→关键词LIKE→FTS5）+ LLM摘要 |
| `modules/regulation_api.py` | Coze RAG API 客户端，SSE流式解析 |
| `prompts/tax_incentive_summary.txt` | DeepSeek 摘要提示词模板 |

## 修改文件

| 文件 | 改动 |
|------|------|
| `config/settings.py` | 末尾追加6行配置常量 |
| `config/tax_query_config.json` | 追加3组路由关键词列表 |
| `mvp_pipeline.py` | `run_pipeline()` 开头插入路由调用（~25行），早返回 |
| `app.py` | `query()` 函数适配文本类结果展示（~15行改动） |

---

## 一、意图路由模块 `modules/intent_router.py`

### 分类逻辑（按优先级执行，命中即返回）

| 层级 | 规则 | 路由目标 |
|------|------|----------|
| Layer -2 | 财务数据优先：查询含数据类关键词（`多少/金额/数据/查询/增长/趋势/情况`）**且**含税种/财务术语（`增值税/所得税/利润/资产/负债/发票`等） | `financial_data` |
| Layer -1 | 知识库优先：含流程/操作类关键词（`指南/指引/申报流程/怎么办/如何办/步骤/手续/享受`） | `regulation` |
| Layer 0 | 企业数据查询：含纳税人名称（从 `taxpayer_info` 缓存匹配）**或**含时间+金额模式（`\d{4}年.*多少`） | `financial_data` |
| Layer 1 | 税收优惠：含优惠关键词（`优惠/减免/免征/退税/补贴/加计扣除/即征即退`等，排除 `exclude_from_incentive` 列表中的词） | `tax_incentive` |
| Default | 以上均未命中 | `regulation` |

### 接口

```python
class IntentRouter:
    def __init__(self, config_path: str = None):
        """config_path 默认 config/tax_query_config.json"""

    def classify(self, question: str, db_conn=None) -> str:
        """返回 'financial_data' | 'tax_incentive' | 'regulation'
        db_conn 可选，用于 Layer 0 纳税人名称匹配"""

    def _load_config(self) -> dict:
        """热更新：检查文件 mtime，变化时重新加载"""
```

Layer 0 复用 `entity_preprocessor.py` 中的 `_load_taxpayer_cache(db_conn)` 获取纳税人名称列表，避免重复查询。需要传入 `fintax_ai.db` 的连接。

### 关键词配置（追加到 `config/tax_query_config.json`）

```json
{
    "financial_db_priority_keywords": [
        "多少", "是多少", "数据", "金额", "查询", "增长", "增减",
        "增加", "减少", "变动", "变化", "趋势", "情况", "对比"
    ],
    "financial_tax_type_keywords": [
        "增值税", "所得税", "企业所得税", "个人所得税",
        "销项税", "进项税", "应纳税", "税额", "税款",
        "利润", "收入", "成本", "费用", "资产", "负债",
        "现金流", "科目余额", "发票", "利润表", "资产负债表"
    ],
    "knowledge_base_priority_keywords": [
        "指南", "指引", "操作", "申报流程", "申请流程",
        "备案流程", "办理流程", "怎么办", "如何办", "怎样办",
        "程序", "步骤", "手续", "享受", "注销流程", "认定流程"
    ],
    "exclude_from_incentive": [
        "申报流程", "缴纳流程", "登记流程",
        "什么是", "定义", "概念", "计算公式"
    ]
}
```

---

## 二、税收优惠查询模块 `modules/tax_incentive_query.py`

### 数据库现状（已确认）

- 路径：`database/tax_incentives.db`，1522条政策记录
- 主表 `tax_incentives`：30列，含 `tax_type`, `incentive_items`, `qualification`, `incentive_method`, `detailed_rules`, `legal_basis`, `keywords`, `explanation` 等
- FTS5表 `tax_incentives_fts`：索引7列（tax_type, incentive_items, qualification, detailed_rules, legal_basis, explanation, keywords）
- **注意**：列名 `"incentive _category"` 和 `"incentive _subcategory"` 有空格（历史遗留），SQL中需用双引号引用
- **FTS5 tokenizer 限制**：默认 unicode61 分词器，中文按空格/标点分词。精确短语匹配（`"高新技术企业"`→5条）有效，但子串匹配（`"高新技术"`→0条）无效。因此 **LIKE 搜索是中文查询的主力**，FTS5 作为兜底

### 四级搜索策略

| 优先级 | 策略 | 触发条件 | 实现方式 |
|--------|------|----------|----------|
| 1 | 结构化搜索 | 明确指定税种 | `WHERE tax_type = ? AND (incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ?)` |
| 2 | 实体搜索 | 有实体关键词（高新技术/小微企业等），无明确税种 | 跨税种搜索 `WHERE incentive_items LIKE ? OR keywords LIKE ? OR qualification LIKE ? OR enterprise_type LIKE ?` |
| 3 | 关键词搜索 | 上述策略结果为空 | 多字段 LIKE 搜索（incentive_items, qualification, detailed_rules, keywords, explanation, incentive_method） |
| 4 | FTS5 兜底 | 上述均无结果 | `SELECT ... FROM tax_incentives_fts WHERE tax_incentives_fts MATCH ?`，用空格拼接关键词 |

每级搜索 limit=20，命中即停止下探。

### LLM 摘要

搜索结果送入 DeepSeek 生成用户友好的回答。复用现有 `intent_parser.py` 中的 OpenAI 客户端模式（`_get_client()` 单例 + DeepSeek API）。

提示词模板 `prompts/tax_incentive_summary.txt` 要求 LLM：
- 根据用户问题和检索到的政策数据，生成结构化回答
- 包含：适用条件、优惠方式、法律依据
- 如果数据不足以回答，明确说明

### 接口

```python
class TaxIncentiveQuery:
    def __init__(self, db_path: str = None, config_path: str = None):
        """db_path 默认 config/settings.py 中的 TAX_INCENTIVES_DB_PATH"""

    def search(self, question: str, limit: int = 20) -> dict:
        """返回:
        {
            'success': bool,
            'route': 'tax_incentive',
            'answer': str,              # LLM 摘要文本
            'raw_results': list[dict],  # 原始 DB 行
            'result_count': int,
            'query_strategy': str,      # 'structured'|'entity'|'keyword'|'fts5'|'empty'
            'tax_type': str | None,
            'error': str | None,
        }
        """

    def _parse_query_intent(self, question: str) -> dict:
        """从问题中提取 tax_type、entity_keywords、search_keywords（纯正则，无LLM）"""

    def _structured_search(self, conn, tax_type, entity_kws, limit) -> list
    def _entity_search(self, conn, entity_kws, limit) -> list
    def _keyword_search(self, conn, keywords, limit) -> list
    def _fts5_search(self, conn, question, limit) -> list
    def _summarize_with_llm(self, question, results, query_intent) -> str
```

---

## 三、外部法规查询模块 `modules/regulation_api.py`

### Coze API 对接

- 端点：`https://api.coze.cn/v3/chat`
- 认证：Bearer Token（PAT_TOKEN）
- 请求方式：POST + SSE 流式响应
- 同步实现（`requests.post(stream=True)`），与现有管线同步模式一致

### SSE 解析

```
event: conversation.message.delta
data: {"role": "assistant", "type": "answer", "content": "..."}
```

累积所有 `type=answer` 的 `content` 片段，拼接为完整回答。

### 接口

```python
def query_regulation(question: str, progress_callback=None) -> dict:
    """返回:
    {
        'success': bool,
        'route': 'regulation',
        'answer': str,       # 完整回答文本
        'error': str | None,
    }
    """

def _parse_sse_line(line: str) -> tuple[str | None, dict | None]:
    """解析单行 SSE 数据"""
```

### 错误处理

- HTTP 非200 → `{success: False, error: "外部知识库API错误: {status_code}"}`
- 超时（180s）→ `{success: False, error: "外部知识库请求超时"}`
- 连接失败 → `{success: False, error: "无法连接外部知识库"}`
- SSE 解析异常 → 返回已累积的部分内容

---

## 四、管线集成 `mvp_pipeline.py`

在 `run_pipeline()` 函数开头（`conn = sqlite3.connect(db_path)` 之后、`entities = detect_entities()` 之前）插入：

```python
# Step 0: 意图路由（在所有域检测之前）
from config.settings import ROUTER_ENABLED
if ROUTER_ENABLED:
    from modules.intent_router import IntentRouter
    _router = IntentRouter()
    route = _router.classify(user_query, db_conn=conn)
    print(f"\n[0] 意图路由: {route}")

    if route == 'tax_incentive':
        if progress_callback:
            progress_callback(0.10, "📚 正在查询税收优惠政策...")
        from modules.tax_incentive_query import TaxIncentiveQuery
        tiq = TaxIncentiveQuery()
        tax_result = tiq.search(user_query)
        tax_result['user_query'] = user_query
        tax_result['entities'] = {}
        tax_result['intent'] = {'domain': 'tax_incentive'}
        conn.close()
        if progress_callback:
            progress_callback(1.0, "✅ 税收优惠查询完成")
        return tax_result

    if route == 'regulation':
        if progress_callback:
            progress_callback(0.10, "🌐 正在查询法规知识库...")
        from modules.regulation_api import query_regulation
        reg_result = query_regulation(user_query, progress_callback)
        reg_result['user_query'] = user_query
        reg_result['entities'] = {}
        reg_result['intent'] = {'domain': 'regulation'}
        conn.close()
        if progress_callback:
            progress_callback(1.0, "✅ 法规查询完成")
        return reg_result

    # route == 'financial_data' → 继续现有管线，零改动
```

**关键设计**：`ROUTER_ENABLED = True` 为主开关。设为 `False` 时完全跳过路由，回退到原有行为。

---

## 五、Gradio UI 适配 `app.py`

### `query()` 函数改动

在结果格式化逻辑中增加对 `route` 字段的判断：

```python
route = result.get('route')

if result.get('clarification'):
    # 原有澄清逻辑不变
    ...
elif route in ('tax_incentive', 'regulation'):
    # 文本类回答（无表格）
    if result.get('success'):
        label = '📚 税收优惠政策' if route == 'tax_incentive' else '🌐 法规知识库'
        main_output = f"{label}\n\n{result.get('answer', '')}"
        status = 'success'
    else:
        main_output = f"❌ 查询失败\n\n{result.get('error', '未知错误')}"
        status = 'error'
elif result.get('success'):
    # 原有表格逻辑不变
    ...
```

### 新增示例问题

```python
"高新技术企业有哪些企业所得税优惠",
"小微企业增值税减免政策",
"研发费用加计扣除的条件是什么",
"如何申报增值税",
```

---

## 六、配置变更 `config/settings.py`

末尾追加：

```python
# 税收优惠知识库
TAX_INCENTIVES_DB_PATH = PROJECT_ROOT / "database" / "tax_incentives.db"

# 外部法规知识库 (Coze API)
COZE_API_URL = "https://api.coze.cn/v3/chat"
COZE_PAT_TOKEN = "pat_vfbLQz46C21deblJhKhahPLcjYb5xcdB1KVyEQliGzdhsBZgCi01DzUD0GQ7aYb"
COZE_BOT_ID = "7592905400907989034"
COZE_USER_ID = "123"
COZE_TIMEOUT = 180

# 意图路由开关
ROUTER_ENABLED = True
```

---

## 七、调用示例

### 示例1：财务数据查询（现有管线，不受影响）

```
输入: "华兴科技2025年1月的销项税额"
路由: Layer -2 命中（"税额" + "增值税"上下文）→ financial_data
结果: 走现有 NL2SQL 管线，返回表格数据
```

### 示例2：税收优惠查询（结构化搜索）

```
输入: "高新技术企业有哪些企业所得税优惠"
路由: Layer 1 命中（"优惠"）→ tax_incentive
搜索: _parse_query_intent → tax_type="企业所得税", entity=["高新技术"]
      Tier 1 结构化搜索 → WHERE tax_type='企业所得税' AND (keywords LIKE '%高新技术%' OR ...)
      命中4条 → LLM 摘要生成回答
结果: 文本回答，列出高新技术企业所得税优惠政策
```

### 示例3：税收优惠查询（关键词搜索）

```
输入: "研发费用加计扣除比例"
路由: Layer 1 命中（"加计扣除"）→ tax_incentive
搜索: _parse_query_intent → tax_type=None, entity=[]
      Tier 1 跳过（无税种）→ Tier 2 跳过（无实体）
      → Tier 3 关键词搜索 LIKE '%研发费用%' AND LIKE '%加计扣除%'
结果: 文本回答
```

### 示例4：外部法规查询

```
输入: "如何申报增值税"
路由: Layer -1 命中（"申报" + "如何"）→ regulation
结果: 调用 Coze API，返回增值税申报流程说明
```

### 示例5：优先级冲突解决

```
输入: "华兴科技2025年增值税销项税额是多少"
路由: Layer -2 命中（"是多少" + "增值税"）→ financial_data（最高优先级）
结果: 走现有管线，即使"增值税"也是其他路由的关键词
```

### 示例6：知识库优先覆盖优惠

```
输入: "小微企业如何享受增值税优惠"
路由: Layer -1 命中（"享受" + "如何"）→ regulation（优先于 Layer 1 的"优惠"）
结果: Coze API 回答操作流程
```

---

## 八、实施顺序

1. **Phase 1 — 配置 + 路由器**：`settings.py` 追加配置 → `tax_query_config.json` 追加关键词 → 实现 `intent_router.py` → `mvp_pipeline.py` 插入路由调用
2. **Phase 2 — 税收优惠模块**：`prompts/tax_incentive_summary.txt` → 实现 `tax_incentive_query.py`
3. **Phase 3 — 外部法规模块**：实现 `regulation_api.py`
4. **Phase 4 — UI 集成**：修改 `app.py`
5. **Phase 5 — 验证**：运行 `test_comprehensive.py` 确认现有57题零回归 → 手动测试三条路由

## 九、验证方式

1. `python test_comprehensive.py` — 现有57题通过率不低于当前水平（~96%）
2. 手动测试税收优惠查询：`python -c "from modules.tax_incentive_query import TaxIncentiveQuery; print(TaxIncentiveQuery().search('高新技术企业所得税优惠'))"`
3. 手动测试法规查询：`python -c "from modules.regulation_api import query_regulation; print(query_regulation('如何申报增值税'))"`
4. 手动测试路由分类：`python -c "from modules.intent_router import IntentRouter; r=IntentRouter(); print(r.classify('华兴科技2025年销项税额')); print(r.classify('小微企业减免政策')); print(r.classify('如何申报增值税'))"`
5. Gradio UI 端到端测试：`python app.py` → 分别输入三类查询验证展示效果
