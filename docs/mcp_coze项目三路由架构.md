
          
根据我对项目代码的详细分析，我来为你详解这个系统如何实现基于用户提问的智能路由机制。

---

## 📋 项目三向路由架构概览

```
用户提问
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    IntentClassifier                         │
│                  (意图分类模块)                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  多层判断优先级:                                     │   │
│  │  1. 财务数据库优先关键词 (最高优先级)                │   │
│  │  2. 知识库优先关键词                                  │   │
│  │  3. 企业财务数据查询                                  │   │
│  │  4. 税收优惠关键词过滤                               │   │
│  │  5. DeepSeek LLM 二次确认                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
    ├── "financial_data" ──→ FinancialQuery ──→ financial.db
    │
    ├── "tax_incentive" ──→ TaxIncentiveQuery ──→ tax_incentives.db
    │
    └── "other" ──→ DeepSeekClient/CozeAPI ──→ 外部知识库
```

---

## 🔧 核心实现细节

### 1️⃣ 意图分类器 (IntentClassifier)

文件位置: [modules/intent_classifier.py](file:///d:/MyProjects/MCP_coze/modules/intent_classifier.py)

#### 多层判断逻辑

```python
# 第-2层（最高优先级）: 财务数据库优先路由
if self._should_priority_route_to_financial_db(question):
    return "financial_data"

# 第-1层: 知识库优先关键词
if self._should_route_to_knowledge_base(question):
    return "other"

# 第0层: 检查企业财务数据查询
if self._is_financial_data_query(question):
    return "financial_data"

# 第一层: 税收优惠关键词过滤
keyword_result = self._keyword_filter(question)
if keyword_result == "tax_incentive":
    return "tax_incentive"

# LLM 二次确认（不确定时）
if self.use_llm:
    return self._llm_classify(question)
```

---

### 2️⃣ 关键词配置详解

#### 📌 税收优惠关键词 (tax_incentive.db)

```python
self.incentive_keywords = [
    "优惠", "减免", "免征", "减征", "抵扣", "退税", 
    "补贴", "扶持", "即征即退", "先征后退", "先征后返",
    "免税", "减税", "税收优惠", "优惠政策", "优惠条件",
    "优惠比例", "优惠税率", "税收减免", "税收扶持",
    "减半征收", "减半", "两免三减半", "三免三减半",
    "免", "减", "返还", "返税", "加计扣除", "加计",
    "税收政策", "税收支持", "税惠"
]
```

#### 📌 财务数据库优先关键词 (financial.db)

```python
# 当问题包含 税种关键词 + 以下任一关键词时，最优先路由到财务数据库
self.financial_db_priority_keywords = [
    "多少", "是多少", "数据", "金额", "查询", 
    "增长", "增减", "增加", "减少", 
    "变动", "改变", "变化", "趋势", "情况"
]

# 税种关键词
self.tax_type_keywords = [
    "增值税", "企业所得税", "个人所得税", "印花税", 
    "房产税", "城镇土地使用税", "消费税", "土地增值税", 
    "资源税", "车船税", "契税", "关税"
]
```

#### 📌 知识库优先关键词 (Coze API)

```python
# 即使包含优惠关键词，也优先路由到知识库
self.knowledge_base_priority_keywords = [
    "指南", "指引", "操作", "申报", "申请", "备案", "管理", 
    "办理", "注销", "注册", "登记注册", "注册登记", 
    "认定", "扣缴", "目录", "汇编", "流程", "怎么办",
    "如何办", "怎样办", "程序", "步骤", "手续", "享受"
]
```

#### 📌 时间范围检测 (路由到财务数据库)

```python
# 支持检测时间区间表述，自动识别财务数据查询
pattern_4_4 = r'\d{4}[—\-~至到]\d{4}'      # 2022-2023
pattern_2_2 = r'(?<!\d)\d{2}[—\-~至到]\d{2}(?!\d)'  # 21-23
pattern_4_2 = r'\d{4}[—\-~至到]\d{2}(?!\d)'  # 2021-24
pattern_2_year = r'(?<!\d)\d{2}年'  # 23年
```

---

### 3️⃣ 路由决策流程图

```
                        用户问题
                           │
                           ▼
              ┌────────────────────────┐
              │ 包含时间范围表述?       │
              │ (2022-2023, 23年等)    │
              └──────────┬─────────────┘
                         │
           ┌─────Yes─────┴─────No─────┐
           ▼                           ▼
    ┌──────────────┐          ┌──────────────────┐
    │ → financial  │          │ 包含知识库优先词? │
    │     _db      │          │ (申报/指南/流程)  │
    └──────────────┘          └────────┬─────────┘
                                       │
                            ┌────Yes───┴────No────┐
                            ▼                     ▼
                     ┌────────────┐    ┌────────────────────┐
                     │ → Coze API │    │ 包含企业名称+财务词?│
                     │ (知识库)   │    └────────┬───────────┘
                     └────────────┘             │
                                   ┌────Yes────┴────No─────┐
                                   ▼                      ▼
                            ┌──────────────┐    ┌─────────────────┐
                            │ → financial  │    │ 包含优惠关键词?  │
                            │     _db      │    └────────┬────────┘
                            └──────────────┐             │
                                          ├────Yes───────┴────No───┐
                                          ▼                       ▼
                                   ┌──────────────┐       ┌──────────────┐
                                   │ → tax_       │       │ → Coze API   │
                                   │ incentive_db │       │ (知识库)     │
                                   └──────────────┘       └──────────────┘
```

---

### 4️⃣ 三大数据源模块

#### A. 财务数据库查询 (financial.db)

文件: [modules/financial_query.py](file:///d:/MyProjects/MCP_coze/modules/financial_query.py)

```python
class FinancialQuery:
    def search(self, question: str):
        # 1. 识别企业名称 (支持别名匹配、模糊匹配、LLM智能识别)
        company = self.match_company(question)
        
        # 2. 提取时间范围 (支持多年、多季度、月份范围)
        time_range = self.extract_time_range(question)
        
        # 3. 识别财务指标
        metrics = self.extract_metrics(question)
        
        # 4. 执行查询 (三层策略: 预计算指标 → 公式计算 → Text-to-SQL)
        results = self.execute_query(company['id'], time_range, metrics, question)
```

**支持的时间格式**:
- 单年: `2023`, `23年`
- 多年: `2023-2024`, `2023、2024`
- 季度: `Q1`, `一季度`, `Q1、Q2`
- 月份: `1月`, `1-3月`

#### B. 税收优惠数据库查询 (tax_incentives.db)

文件: [modules/db_query.py](file:///d:/MyProjects/MCP_coze/modules/db_query.py)

```python
class TaxIncentiveQuery:
    def search(self, question: str):
        # 智能搜索策略选择:
        # 1. 用户明确指定税种 → 结构化查询
        # 2. 有实体关键词 → 跨税种实体搜索  
        # 3. 无提取信息 → 关键词搜索
        # 4. 仍无结果 → 原问题搜索
```

#### C. 外部API (Coze)

文件: [server/routers/chat.py](file:///d:/MyProjects/MCP_coze/server/routers/chat.py#L855-L911)

```python
# Coze API 配置
PAT_TOKEN = "pat_vfbLQz46C21deblJhKhahPLcjYb5xcdB1KKVyEQliGzdhsBZgCi01DzUD0GQ7aYb"
BOT_ID = "7592905400907989034"

async def stream_coze_response(question: str):
    # 调用 Coze API 获取回答
    payload = {
        "bot_id": BOT_ID,
        "user_id": USER_ID,
        "stream": True,
        "additional_messages": [{"role": "user", "content": question}]
    }
```

---

### 5️⃣ 配置文件 (热更新)

文件: [config/tax_query_config.json](file:///d:/MyProjects/MCP_coze/config/tax_query_config.json)

```json
{
    "tax_types": ["增值税", "企业所得税", "个人所得税", ...],
    "tax_fuzzy_map": {
        "企业所得": "企业所得税",
        "个人所得": "个人所得税"
    },
    "incentive_keywords": ["优惠", "减免", "免征", ...],
    "core_entity_keywords": ["集成电路", "软件", "高新技术", ...],
    "condition_intent_keywords": ["条件", "要求", "认定条件", ...],
    "entity_synonyms": {
        "小微企业": ["小微企业", "小型微利", "小微"]
    }
}
```

---

### 6️⃣ API 接口调用

文件: [server/routers/chat.py](file:///d:/MyProjects/MCP_coze/server/routers/chat.py#L914-L939)

```python
class ChatRequest(BaseModel):
    question: str
    company_id: Optional[int] = None
    enable_routing: bool = True  # 是否启用智能路由
    show_chart: bool = True     # 是否显示图表
    response_mode: str = "detailed"  # 回答模式

@router.post("/chat")
async def chat_stream(request: ChatRequest):
    # 自动识别意图并路由到对应模块
    intent = classifier.classify(request.question)
    
    if intent == "financial_data":
        # → financial.db
        async for chunk in stream_financial_response(...):
            yield chunk
    elif intent == "tax_incentive":
        # → tax_incentives.db
        async for chunk in stream_tax_response(...):
            yield chunk
    else:
        # → Coze API
        async for chunk in stream_coze_response(...):
            yield chunk
```

---

## 📊 路由示例

| 用户问题 | 路由方向 | 判断依据 |
|---------|---------|---------|
| `ABC公司2023年销售额` | financial.db | 包含企业名+财务关键词+时间 |
| `高新技术企业增值税优惠` | tax_incentives.db | 包含"优惠"关键词 |
| `小微企业所得税减免条件` | tax_incentives.db | 包含"优惠"关键词 |
| `如何申报高新技术企业` | Coze API | 包含"申报"知识库优先词 |
| `增值税专用发票是什么` | Coze API | 包含排除词"什么是" |
| `23年公司收入多少` | financial.db | 包含时间范围+财务优先词 |

---

## 🎯 总结

这个项目通过 **IntentClassifier** 模块实现了一个智能的三向路由系统：

1. **financial.db** - 通过检测时间范围、财务关键词、企业名称等组合条件判断
2. **tax_incentives.db** - 通过税收优惠关键词（如"优惠"、"减免"等）识别
3. **Coze API** - 作为兜底方案，处理知识库类问题和无法识别的问题

所有关键词都支持 **热更新** 配置，可以在 `config/tax_query_config.json` 中修改而无需重启服务。