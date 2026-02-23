# 税收优惠政策查询系统 - 技术文档

> 文档版本: 1.0  
> 更新日期: 2026-02-18  
> 适用人员: 开发人员、系统架构师、技术维护人员

---

## 一、系统概述

税收优惠政策查询系统是一个智能问答系统的核心模块，负责从本地 SQLite 数据库中检索税收优惠政策信息。系统支持多种查询策略，包括结构化查询、跨税种实体搜索、关键词搜索和全文搜索，能够根据用户问题的语义自动选择最优查询方案。

### 1.1 核心组件

| 组件 | 文件路径 | 功能 |
|------|----------|------|
| TaxIncentiveQuery | `modules/db_query.py` | 核心查询类，提供多种查询方法 |
| 配置文件 | `config/tax_query_config.json` | 关键词、同义词等配置（支持热更新） |
| 数据库 | `database/tax_incentives.db` | SQLite 数据库，存储优惠政策数据 |

---

## 二、数据库结构

### 2.1 数据库文件

| 属性 | 值 |
|------|-----|
| 文件路径 | `database/tax_incentives.db` |
| 数据库类型 | SQLite 3 |
| 主表 | `tax_incentives` |
| 全文索引表 | `tax_incentives_fts` (FTS5) |
| 总记录数 | 1522条 |

### 2.2 表结构 (tax_incentives)

```sql
CREATE TABLE tax_incentives (
    id                      INTEGER PRIMARY KEY,
    serial_number           INTEGER,
    tax_type                TEXT NOT NULL,           -- 税种
    incentive_items         TEXT,                    -- 优惠项目名称
    qualification           TEXT,                    -- 认定条件/资格要求
    incentive_method        TEXT,                    -- 优惠方式
    detailed_rules          TEXT,                    -- 具体规定
    legal_basis             TEXT,                    -- 法律依据
    special_notes           TEXT,                    -- 特别说明
    explanation             TEXT,                    -- 解释说明
    effective_date          TEXT,                    -- 生效日期
    expiry_date             TEXT,                    -- 失效日期
    applicable_region       TEXT,                    -- 适用地区
    policy_status           TEXT,                    -- 政策状态
    industry_scope          TEXT,                    -- 行业范围
    enterprise_type         TEXT,                    -- 企业类型
    discount_rate           TEXT,                    -- 优惠比例
    application_process     TEXT,                    -- 申请流程
    required_documents      TEXT,                    -- 所需资料
    data_source             TEXT,                    -- 数据来源
    data_quality            INTEGER,                 -- 数据质量
    last_verified_date      TEXT,                    -- 最后验证日期
    created_at              TIMESTAMP,               -- 创建时间
    updated_at              TIMESTAMP,               -- 更新时间
    keywords                TEXT,                    -- 关键词（用于搜索）
    tags                    TEXT                     -- 标签
);
```

### 2.3 字段说明

| 字段名 | 类型 | 说明 | 搜索优先级 |
|--------|------|------|------------|
| `tax_type` | TEXT | 税种名称，如"增值税"、"企业所得税" | 高 |
| `incentive_items` | TEXT | 优惠项目名称 | 高 |
| `qualification` | TEXT | 认定条件/资格要求 | 高 |
| `incentive_method` | TEXT | 优惠方式（免征、减征、即征即退等） | 高 |
| `detailed_rules` | TEXT | 具体规定/政策内容 | 高 |
| `keywords` | TEXT | 预定义的搜索关键词 | 高 |
| `explanation` | TEXT | 解释说明 | 中 |
| `legal_basis` | TEXT | 法律依据 | 低 |
| `enterprise_type` | TEXT | 企业类型 | 中 |
| `industry_scope` | TEXT | 行业范围 | 中 |
| `applicable_region` | TEXT | 适用地区 | 低 |

### 2.4 税种分布统计

| 税种 | 记录数 | 占比 |
|------|--------|------|
| 增值税 | 247条 | 37.6% |
| 个人所得税 | 180条 | 27.4% |
| 企业所得税 | 119条 | 18.1% |
| 印花税 | 29条 | 4.4% |
| 房产税 | 28条 | 4.3% |
| 城镇土地使用税 | 21条 | 3.2% |
| 消费税 | 15条 | 2.3% |
| 土地增值税 | 10条 | 1.5% |
| 资源税 | 8条 | 1.2% |

### 2.5 优惠方式分布

| 优惠方式 | 说明 |
|----------|------|
| 免征 | 完全免除税款 |
| 减征 | 按一定比例减征 |
| 减半 | 减按50%征收 |
| 即征即退 | 当即征收当即将还 |
| 先征后退 | 先征收后返还 |
| 免税 | 免予征税 |
| 减税 | 减少应纳税额 |
| 抵扣 | 从应纳税额中抵扣 |
| 补贴 | 政府补贴 |
| 扶持 | 扶持性政策 |
| 暂免 | 暂时免征 |
| 不征 | 不予征税 |

---

## 三、配置文件详解

### 3.1 tax_query_config.json

配置文件路径: `config/tax_query_config.json`

该文件包含税收优惠查询系统的所有可配置参数，支持热更新（修改后自动生效）。

```json
{
    "_comment": "税收优惠查询系统配置文件 - 修改后自动生效(热更新)",
    "_last_updated": "2026-01-17",
    
    // 支持的税种列表
    "tax_types": [
        "城镇土地使用税",
        "企业所得税",
        "个人所得税",
        "土地增值税",
        "增值税",
        "印花税",
        "房产税",
        "消费税",
        "资源税",
        "车船税",
        "契税",
        "关税"
    ],
    
    // 税种模糊匹配映射（解决用户输入不完整的问题）
    "tax_fuzzy_map": {
        "企业所得": "企业所得税",
        "个人所得": "个人所得税",
        "土地增值": "土地增值税",
        "城镇土地使用": "城镇土地使用税"
    },
    
    // 优惠关键词（用于识别用户是否在询问优惠相关问题）
    "incentive_keywords": [
        "优惠", "减免", "免征", "减征", "抵扣", "退税",
        "不征税", "两免三减半", "补贴", "扶持", "即征即退",
        "先征后退", "加速折旧", "免税", "减税"
    ],
    
    // 核心实体关键词（高频、重要实体，用于快速匹配）
    "core_entity_keywords": [
        "集成电路", "软件", "高新技术", "小微企业", "小型微利",
        "残疾人", "创业投资", "天使投资"
    ],
    
    // 条件意图关键词（判断用户是否关注优惠条件/资格）
    "condition_intent_keywords": [
        "条件", "要求", "认定条件", "优惠条件", "减免条件",
        "资格", "标准", "手续", "资料", "备案", "申请", "流程"
    ],
    
    // 实体同义词映射（解决同一实体多种表述的问题）
    "entity_synonyms": {
        "小微企业": ["小微企业", "小型微利", "小微"],
        "小型微利": ["小型微利", "小微企业", "小微"],
        "高新技术": ["高新技术", "高新企业"]
    }
}
```

### 3.2 配置项详细说明

#### 3.2.1 tax_types - 税种列表

系统支持的税种名称，用于精确匹配用户问题中的税种。匹配时按列表顺序进行，用户问题中包含任一税种即认为用户指定了该税种。

**匹配规则**: 
- 精确匹配：用户问题完整包含税种名称
- 模糊匹配：通过 `tax_fuzzy_map` 映射表匹配不完整的税种表述

#### 3.2.2 tax_fuzzy_map - 税种模糊映射

用于处理用户输入不完整税种名称的情况。例如用户输入"企业所得"时，系统自动识别为"企业所得税"。

| 用户输入 | 映射结果 |
|----------|----------|
| 企业所得 | 企业所得税 |
| 个人所得 | 个人所得税 |
| 土地增值 | 土地增值税 |
| 城镇土地使用 | 城镇土地使用税 |

#### 3.2.3 incentive_keywords - 优惠关键词

用于判断用户问题是否与税收优惠相关。当用户问题中包含这些关键词时，系统会优先搜索包含优惠内容的政策。

#### 3.2.4 core_entity_keywords - 核心实体关键词

这些是高频出现的优惠主体/行业关键词，用于快速匹配。系统首先尝试从用户问题中提取这些关键词，如果未匹配到则调用 LLM 进行智能提取。

#### 3.2.5 condition_intent_keywords - 条件意图关键词

用于判断用户的查询意图是"了解优惠条件"还是"一般性了解"。如果用户问题中包含这些关键词，系统会将 `query_intent` 设置为 `"condition"`，否则为 `"general"`。

#### 3.2.6 entity_synonyms - 实体同义词

解决同一实体多种表述的问题。例如"小微企业"和"小型微利企业"在税务领域指代同一类主体，系统在搜索时会自动扩展这些同义词。

---

## 四、查询流程详解

### 4.1 整体架构

```
用户问题
    │
    ▼
┌─────────────────────────────────────┐
│  _extract_tax_and_incentive()       │
│  - 提取税种                         │
│  - 提取优惠关键词                   │
│  - 提取实体关键词                   │
│  - 判断查询意图                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  策略选择                           │
│  - explicit → structured_search    │
│  - inferred + entity → entity_search│
│  - 无匹配 → keyword_search          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  返回结果                           │
│  - results: 查询结果列表            │
│  - total_count: 总数                │
│  - query_intent: 查询意图           │
└─────────────────────────────────────┘
```

### 4.2 入口方法: search()

文件: `modules/db_query.py`，行号 110-167

```python
def search(self, question: str, limit: int = 50) -> tuple:
    """
    智能搜索：根据问题自动选择最佳查询策略
    
    Args:
        question: 用户问题
        limit: 返回结果数量限制(默认50)
    
    Returns:
        (查询结果列表, 总数, 查询意图)
    """
    # 第一步：提取关键信息
    tax_type, incentive_keywords, entity_keywords, query_intent, tax_type_source = \
        self._extract_tax_and_incentive(question)
    
    # 第二步：策略选择
    results = []
    total_count = 0
    
    # 策略1: 用户明确指定了税种 (explicit)
    if tax_type and tax_type_source == "explicit":
        total_count = self.count_structured_results(tax_type, entity_keywords)
        results = self.structured_search(tax_type, entity_keywords, limit=limit)
    
    # 策略2: 有实体关键词（无论是否有LLM推理的税种）
    elif entity_keywords:
        results = self.entity_search(entity_keywords, limit=limit)
        total_count = len(results)
    
    # 策略3: 使用提取的关键词搜索
    if not results:
        keywords = self._extract_keywords(question)
        if keywords:
            results = self.keyword_search(keywords, limit=limit)
            total_count = len(results)
    
    # 策略4: 使用原问题搜索
    if not results:
        results = self.keyword_search(question, limit=limit)
        total_count = len(results)
    
    return results[:limit], total_count, query_intent
```

### 4.3 关键信息提取: _extract_tax_and_incentive()

文件: `modules/db_query.py`，行号 169-247

该方法从用户问题中提取以下信息：

#### 返回值说明

| 返回值 | 类型 | 说明 |
|--------|------|------|
| tax_type | str | 识别出的税种 |
| incentive_keywords | List[str] | 匹配的优惠关键词列表 |
| entity_keywords | List[str] | 匹配的实体关键词列表 |
| query_intent | str | 查询意图 ("general" 或 "condition") |
| tax_type_source | str | 税种来源 ("explicit" 或 "inferred" 或 None) |

#### 税种提取流程

```
用户问题
    │
    ▼
┌──────────────────┐
│  精确匹配tax_types│ ──匹配成功──▶ tax_type_source = "explicit"
└──────────────────┘
    │
    │未匹配
    ▼
┌──────────────────┐
│ 模糊匹配tax_fuzzy_map│ ──匹配成功──▶ tax_type_source = "explicit"
└──────────────────┘
    │
    │未匹配
    ▼
┌──────────────────┐
│ LLM推理 _infer_tax_type_with_llm()│ ──推理成功──▶ tax_type_source = "inferred"
└──────────────────┘
    │
    │未匹配
    ▼
   None
```

#### 实体关键词提取流程

```
用户问题
    │
    ▼
┌──────────────────────────┐
│ 匹配 core_entity_keywords │ ──匹配成功──▶ entity_keywords
└──────────────────────────┘
    │
    │未匹配
    ▼
┌────────────────────────────────────────┐
│ LLM智能提取 _extract_project_keywords_with_llm() │ ──提取成功──▶ entity_keywords
└────────────────────────────────────────┘
    │
    │未提取
    ▼
   []
```

### 4.4 LLM 推理: _infer_tax_type_with_llm()

文件: `modules/db_query.py`，行号 249-308

当用户问题中没有明确提到税种时，系统调用 DeepSeek LLM 推理税种。

**Prompt 设计**:

```
请根据以下问题判断涉及的税种。

问题: {用户问题}

税种列表:
- 增值税
- 企业所得税
- 个人所得税
- 印花税
- 房产税
- 城镇土地使用税
- 消费税
- 土地增值税
- 资源税
- 车船税
- 契税
- 关税

判断规则:
1. 如果问题明确提到税种名称,返回该税种
2. 如果问题涉及"税前扣除"、"加计扣除"、"研发费用",通常是企业所得税
3. 如果问题涉及"专项附加扣除"、"工资薪金"、"劳务报酬",通常是个人所得税
4. 如果问题涉及"进项税"、"销项税"、"抵扣",通常是增值税
5. 如果无法判断,返回"无法判断"

请只返回税种名称或"无法判断",不要有其他内容。
```

### 4.5 LLM 实体提取: _extract_project_keywords_with_llm()

文件: `modules/db_query.py`，行号 310-372

当用户问题中没有匹配到核心实体关键词时，系统调用 LLM 智能提取优惠项目关键词。

**Prompt 设计**:

```
请从以下问题中提取税收优惠相关的项目关键词。

问题: {用户问题}

项目类型包括:
- 产品: 如粮食、油页岩、软件产品、集成电路等
- 服务: 如会议展览、婚姻介绍、文化服务、工程监理等
- 行业: 如出版、科研、农业、医疗等
- 企业类型: 如高新技术企业、小微企业、残疾人企业等
- 事项: 如资产损失、补贴收入、保险赔款、残疾人就业等
- 地区: 如海南、前海、西藏等

要求:
1. 只提取与税收优惠直接相关的项目关键词
2. 每个关键词2-6个字,尽量简洁
3. 最多返回3个关键词
4. 如果问题中没有明确的项目,返回"无"
5. 只返回关键词,用逗号分隔,不要其他内容
```

---

## 五、查询方法详解

### 5.1 结构化查询: structured_search()

文件: `modules/db_query.py`，行号 443-527

**适用场景**: 用户明确指定了税种（如"增值税优惠"）

**查询逻辑**:

```python
def structured_search(self, tax_type: str, entity_keywords: List[str] = None, limit: int = 50):
    """
    结构化查询：税种精确匹配 + 优惠方式包含特定关键词 + 实体关键词过滤
    """
    # 优惠方式关键词列表
    incentive_methods = [
        "减征", "免征", "不征", "暂免", "减半", "退税",
        "即征即退", "先征后退", "先征后返", "免税", "减税",
        "减免", "抵扣", "补贴", "扶持", "优惠"
    ]
    
    # 构建优惠方式OR条件
    method_conditions = " OR ".join(["incentive_method LIKE ?" for _ in incentive_methods])
    method_params = [f"%{method}%" for method in incentive_methods]
    
    # 如果有实体关键词，扩展并搜索多个字段
    if entity_keywords:
        # 扩展同义词
        expanded_keywords = expand_synonyms(entity_keywords)
        
        # 构建实体条件（在多个字段中搜索）
        entity_conditions = []
        for entity in expanded_keywords:
            entity_conditions.append("""(
                incentive_items LIKE ? 
                OR detailed_rules LIKE ? 
                OR qualification LIKE ?
                OR incentive_method LIKE ?
            )""")
        
        entity_clause = " OR ".join(entity_conditions)
        
        # SQL: tax_type = ? AND (实体条件)
        query = """
            SELECT * FROM tax_incentives
            WHERE tax_type = ?
            AND ({entity_clause})
            LIMIT ?
        """
    else:
        # SQL: tax_type = ? AND (优惠方式条件)
        query = """
            SELECT * FROM tax_incentives
            WHERE tax_type = ?
            AND ({method_conditions})
            LIMIT ?
        """
```

**SQL 构建逻辑**:

```sql
-- 有实体关键词时
SELECT * FROM tax_incentives
WHERE tax_type = '增值税'
AND (
    (incentive_items LIKE '%小微企业%' OR detailed_rules LIKE '%小微企业%' OR ...)
    OR (incentive_items LIKE '%高新技术%' OR detailed_rules LIKE '%高新技术%' OR ...)
)
LIMIT 50

-- 无实体关键词时
SELECT * FROM tax_incentives
WHERE tax_type = '增值税'
AND (incentive_method LIKE '%减征%' OR incentive_method LIKE '%免征%' OR ...)
LIMIT 50
```

### 5.2 跨税种实体查询: entity_search()

文件: `modules/db_query.py`，行号 374-441

**适用场景**: 用户未指定税种但提到了特定主体（如"小微企业优惠有哪些"）

**查询逻辑**:

```python
def entity_search(self, entity_keywords: List[str], limit: int = 50):
    """
    跨税种实体搜索：根据实体关键词搜索所有税种的相关政策
    """
    # 扩展实体关键词（同义词处理）
    entity_synonyms = config.get("entity_synonyms", {})
    expanded_keywords = []
    for entity in entity_keywords:
        if entity in entity_synonyms:
            expanded_keywords.extend(entity_synonyms[entity])
        else:
            expanded_keywords.append(entity)
    expanded_keywords = list(set(expanded_keywords))
    
    # 构建在多个字段中搜索的条件
    entity_conditions = []
    params = []
    for entity in expanded_keywords:
        entity_conditions.append("""(
            incentive_items LIKE ? 
            OR detailed_rules LIKE ? 
            OR qualification LIKE ?
            OR incentive_method LIKE ?
            OR keywords LIKE ?
            OR explanation LIKE ?
        )""")
        params.extend([f"%{entity}%"] * 6)
    
    entity_clause = " OR ".join(entity_conditions)
    
    # SQL: (实体条件) ORDER BY tax_type优先级
    query = """
        SELECT * FROM tax_incentives
        WHERE {entity_clause}
        ORDER BY 
            CASE tax_type 
                WHEN '企业所得税' THEN 1 
                WHEN '增值税' THEN 2 
                ELSE 3 
            END,
            id
        LIMIT ?
    """
```

**搜索字段**:

| 字段 | 说明 |
|------|------|
| incentive_items | 优惠项目名称 |
| detailed_rules | 具体规定 |
| qualification | 认定条件 |
| incentive_method | 优惠方式 |
| keywords | 关键词 |
| explanation | 解释说明 |

**排序优先级**: 企业所得税 > 增值税 > 其他税种

### 5.3 关键词查询: keyword_search()

文件: `modules/db_query.py`，行号 689-744

**适用场景**: 无法识别税种和实体时的兜底策略

**查询逻辑**:

```python
def keyword_search(self, keywords: str, limit: int = 50):
    """
    关键词搜索（使用LIKE）
    """
    # 将关键词分割成列表
    keyword_list = keywords.split()
    
    # 构建OR查询条件
    conditions = []
    params = []
    
    for keyword in keyword_list:
        like_pattern = f"%{keyword}%"
        # 每个关键词在多个字段中搜索
        conditions.append("""(
            tax_type LIKE ? OR
            incentive_items LIKE ? OR
            qualification LIKE ? OR
            detailed_rules LIKE ? OR
            keywords LIKE ? OR
            explanation LIKE ? OR
            incentive_method LIKE ? OR
            legal_basis LIKE ?
        )""")
        params.extend([like_pattern] * 8)
    
    # 组合所有条件(OR连接)
    where_clause = " OR ".join(conditions)
    
    query = f"""
        SELECT * FROM tax_incentives
        WHERE {where_clause}
        LIMIT ?
    """
    params.append(limit)
```

**搜索字段**:

| 字段 | 说明 |
|------|------|
| tax_type | 税种 |
| incentive_items | 优惠项目名称 |
| qualification | 认定条件 |
| detailed_rules | 具体规定 |
| keywords | 关键词 |
| explanation | 解释说明 |
| incentive_method | 优惠方式 |
| legal_basis | 法律依据 |

### 5.4 全文搜索: fulltext_search()

文件: `modules/db_query.py`，行号 653-687

**适用场景**: 需要更高性能的专业搜索（使用 SQLite FTS5）

**查询逻辑**:

```python
def fulltext_search(self, query: str, limit: int = 10):
    """
    全文搜索（使用FTS5）
    """
    # 使用FTS5全文搜索
    cursor.execute("""
        SELECT t.* 
        FROM tax_incentives t
        JOIN tax_incentives_fts fts ON t.id = fts.rowid
        WHERE tax_incentives_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    # 如果FTS搜索失败，降级到LIKE搜索
    except sqlite3.OperationalError:
        return self.keyword_search(query, limit)
```

### 5.5 其他查询方法

#### 5.5.1 按税种查询: search_by_tax_type()

文件: `modules/db_query.py`，行号 746-769

```python
def search_by_tax_type(self, tax_type: str, limit: int = 10):
    """按税种搜索"""
    cursor.execute("""
        SELECT * FROM tax_incentives
        WHERE tax_type = ?
        LIMIT ?
    """, (tax_type, limit))
```

#### 5.5.2 按优惠方式查询: search_by_incentive_method()

文件: `modules/db_query.py`，行号 771-794

```python
def search_by_incentive_method(self, method: str, limit: int = 10):
    """按优惠方式搜索"""
    cursor.execute("""
        SELECT * FROM tax_incentives
        WHERE incentive_method LIKE ?
        LIMIT ?
    """, (f"%{method}%", limit))
```

#### 5.5.3 按ID查询: get_by_id()

文件: `modules/db_query.py`，行号 796-813

```python
def get_by_id(self, policy_id: int):
    """根据ID获取政策详情"""
    cursor.execute("SELECT * FROM tax_incentives WHERE id = ?", (policy_id,))
```

---

## 六、同义词处理机制

### 6.1 同义词配置

在 `tax_query_config.json` 中配置 `entity_synonyms`：

```json
"entity_synonyms": {
    "小微企业": ["小微企业", "小型微利", "小微"],
    "小型微利": ["小型微利", "小微企业", "小微"],
    "高新技术": ["高新技术", "高新企业"]
}
```

### 6.2 同义词扩展逻辑

```python
def expand_synonyms(keywords: List[str], entity_synonyms: dict) -> List[str]:
    """
    扩展关键词，添加同义词
    
    Args:
        keywords: 原始关键词列表
        entity_synonyms: 同义词映射表
    
    Returns:
        扩展后的关键词列表
    """
    expanded = []
    for keyword in keywords:
        if keyword in entity_synonyms:
            expanded.extend(entity_synonyms[keyword])
        else:
            expanded.append(keyword)
    return list(set(expanded))  # 去重
```

### 6.3 同义词使用场景

| 场景 | 方法 | 说明 |
|------|------|------|
| 跨税种实体搜索 | `entity_search()` | 扩展后在多个字段中搜索 |
| 结构化查询 | `structured_search()` | 扩展后限定税种搜索 |
| 统计总数 | `count_structured_results()` | 扩展后统计数量 |

### 6.4 示例

**用户输入**: "小微企业优惠有哪些"

**处理流程**:

1. 提取实体关键词: `["小微企业"]`
2. 同义词扩展: `["小微企业", "小型微利", "小微"]`
3. 搜索字段: `incentive_items`, `detailed_rules`, `qualification`, `incentive_method`, `keywords`, `explanation`
4. SQL 构建:
   ```sql
   WHERE (
       incentive_items LIKE '%小微企业%' OR detailed_rules LIKE '%小微企业%' OR ...
       OR incentive_items LIKE '%小型微利%' OR detailed_rules LIKE '%小型微利%' OR ...
       OR incentive_items LIKE '%小微%' OR detailed_rules LIKE '%小微%' OR ...
   )
   ```

---

## 七、配置热更新机制

### 7.1 热更新原理

配置文件 (`tax_query_config.json`) 支持热更新，修改后无需重启服务即可生效。

```python
def _load_config(self):
    """
    加载配置文件(支持热更新)
    每次调用时检查文件修改时间,只有文件变化时才重新加载
    """
    current_mtime = os.path.getmtime(self.config_path)
    
    # 如果文件未修改,直接返回缓存的配置
    if current_mtime == self._config_mtime and self._config:
        return self._config
    
    # 文件已修改,重新加载
    with open(self.config_path, 'r', encoding='utf-8') as f:
        self._config = json.load(f)
    
    self._config_mtime = current_mtime
    return self._config
```

### 7.2 热更新触发时机

每次调用以下方法时会检查配置文件是否已更新：

- `search()` → 调用 `_extract_tax_and_incentive()` → 调用 `_load_config()`
- `entity_search()` → 调用 `_load_config()`
- `structured_search()` → 调用 `_load_config()`
- `count_structured_results()` → 调用 `_load_config()`

---

## 八、查询策略选择算法

### 8.1 策略优先级

| 优先级 | 条件 | 方法 | 说明 |
|--------|------|------|------|
| 1 | 用户明确指定税种 (tax_type_source == "explicit") | `structured_search()` | 限定税种 + 实体关键词 |
| 2 | 有实体关键词 (entity_keywords) | `entity_search()` | 跨所有税种搜索 |
| 3 | 提取到关键词 (keywords) | `keyword_search()` | OR连接多字段搜索 |
| 4 | 无任何匹配 | `keyword_search(原问题)` | 兜底策略 |

### 8.2 税种来源标记

| 标记 | 说明 | 处理方式 |
|------|------|----------|
| "explicit" | 用户明确指定 | 使用 `structured_search()` 限定该税种 |
| "inferred" | LLM推理得到 | 仅当有实体关键词时使用 `entity_search()`，忽略推理的税种 |
| None | 未识别 | 进入关键词搜索策略 |

### 8.3 查询意图判断

通过 `condition_intent_keywords` 判断用户是否关注优惠条件：

```python
condition_intent_keywords = ["条件", "要求", "认定条件", "优惠条件", "减免条件", "资格", "标准", "手续", "资料", "备案", "申请", "流程"]

is_condition_focused = any(kw in question for kw in condition_intent_keywords)
query_intent = "condition" if is_condition_focused else "general"
```

---

## 九、典型查询场景示例

### 场景1: 用户明确指定税种

**用户输入**: "企业所得税小微企业优惠"

**处理流程**:

1. `_extract_tax_and_incentive()` 提取:
   - tax_type: "企业所得税" (explicit)
   - entity_keywords: ["小微企业"]
   - query_intent: "general"

2. 策略选择: tax_type_source == "explicit" → `structured_search("企业所得税", ["小微企业"])`

3. SQL:
   ```sql
   SELECT * FROM tax_incentives
   WHERE tax_type = '企业所得税'
   AND (
       incentive_items LIKE '%小微企业%' OR detailed_rules LIKE '%小微企业%' OR ...
       OR incentive_items LIKE '%小型微利%' OR detailed_rules LIKE '%小型微利%' OR ...
   )
   LIMIT 50
   ```

### 场景2: 用户未指定税种但提到实体

**用户输入**: "小微企业优惠有哪些"

**处理流程**:

1. `_extract_tax_and_incentive()` 提取:
   - tax_type: None → LLM推理可能返回"企业所得税"但 tax_type_source="inferred"
   - entity_keywords: ["小微企业"]
   - query_intent: "general"

2. 策略选择: 有 entity_keywords → `entity_search(["小微企业"])`

3. SQL:
   ```sql
   SELECT * FROM tax_incentives
   WHERE (
       incentive_items LIKE '%小微企业%' OR ... OR
       incentive_items LIKE '%小型微利%' OR ... OR
       incentive_items LIKE '%小微%' OR ...
   )
   ORDER BY CASE tax_type WHEN '企业所得税' THEN 1 WHEN '增值税' THEN 2 ELSE 3 END
   LIMIT 50
   ```

### 场景3: 用户关注优惠条件

**用户输入**: "高新技术企业认定条件有哪些？"

**处理流程**:

1. `_extract_tax_and_incentive()` 提取:
   - tax_type: None → LLM推理可能返回相关税种
   - entity_keywords: ["高新技术"]
   - query_intent: "condition" (因为包含"条件")

2. 策略选择: 有 entity_keywords → `entity_search(["高新技术"])`

3. 结果中会优先返回包含认定条件的高新技术企业相关政策

### 场景4: 无法识别任何信息

**用户输入**: "最近有什么新政策？"

**处理流程**:

1. `_extract_tax_and_incentive()` 提取:
   - tax_type: None
   - entity_keywords: []
   - incentive_keywords: ["优惠"] (可能匹配)

2. 策略1: 无 tax_type_source == "explicit"，跳过
3. 策略2: 无 entity_keywords，跳过
4. 策略3: `_extract_keywords()` 可能提取到 ["优惠"]，调用 `keyword_search("优惠")`
5. 策略4: 如果仍无结果，调用 `keyword_search("最近有什么新政策？")`

---

## 十、数据库索引优化

### 10.1 现有索引

建议为以下字段创建索引以提升查询性能：

```sql
-- 税种索引
CREATE INDEX idx_tax_type ON tax_incentives(tax_type);

-- 优惠方式索引
CREATE INDEX idx_incentive_method ON tax_incentives(incentive_method);

-- 企业类型索引
CREATE INDEX idx_enterprise_type ON tax_incentives(enterprise_type);

-- 行业范围索引
CREATE INDEX idx_industry_scope ON tax_incentives(industry_scope);

-- 关键词索引
CREATE INDEX idx_keywords ON tax_incentives(keywords);

-- 复合索引（用于结构化查询）
CREATE INDEX idx_tax_method ON tax_incentives(tax_type, incentive_method);
```

### 10.2 FTS5 全文索引

数据库包含 FTS5 全文索引表 `tax_incentives_fts`，用于高性能全文搜索：

```sql
-- 重建FTS索引
INSERT INTO tax_incentives_fts(tax_incentives_fts) VALUES('rebuild');

-- 优化FTS索引
INSERT INTO tax_incentives_fts(tax_incentives_fts) VALUES('optimize');
```

---

## 十一、错误处理与降级策略

### 11.1 LLM 调用失败

当 DeepSeek API 调用失败时，系统会打印警告并返回 None，不影响其他查询逻辑：

```python
except Exception as e:
    print(f"⚠️  DeepSeek推理失败: {str(e)}")
    return None
```

### 11.2 FTS 搜索失败

当 FTS5 全文搜索失败时，降级到 LIKE 搜索：

```python
except sqlite3.OperationalError as e:
    print(f"⚠️  全文搜索失败: {e}, 使用关键词搜索")
    return self.keyword_search(query, limit)
```

### 11.3 配置文件缺失

当配置文件不存在或格式错误时，使用默认配置：

```python
except FileNotFoundError:
    print(f"⚠️ 配置文件不存在,使用默认配置")
    self._config = self._get_default_config()
except json.JSONDecodeError as e:
    print(f"⚠️ 配置文件格式错误,使用默认配置: {e}")
    self._config = self._get_default_config()
```

---

## 十二、扩展指南

### 12.1 添加新税种

1. 在 `config/tax_query_config.json` 的 `tax_types` 数组中添加税种名称
2. 在数据库中录入该税种的优惠政策
3. 确保 `tax_fuzzy_map` 中有必要的模糊映射（如需要）

### 12.2 添加新实体同义词

在 `config/tax_query_config.json` 的 `entity_synonyms` 中添加映射：

```json
"entity_synonyms": {
    "新实体": ["新实体", "新实体简称", "新实体别名"]
}
```

### 12.3 添加新优惠关键词

在 `config/tax_query_config.json` 的 `incentive_keywords` 数组中添加：

```json
"incentive_keywords": [..., "新优惠关键词"]
```

### 12.4 添加新的查询意图

在 `config/tax_query_config.json` 的 `condition_intent_keywords` 中添加条件关键词，或创建新的意图类型：

```json
"new_intent_keywords": ["关键词1", "关键词2"]
```

---

## 十三、API 参考

### 13.1 TaxIncentiveQuery 类

```python
class TaxIncentiveQuery:
    def __init__(self, db_path: str = None, config_path: str = None)
    
    # 核心查询方法
    def search(self, question: str, limit: int = 50) -> tuple
    def structured_search(self, tax_type: str, entity_keywords: List[str] = None, limit: int = 50) -> List[Dict]
    def entity_search(self, entity_keywords: List[str], limit: int = 50) -> List[Dict]
    def keyword_search(self, keywords: str, limit: int = 50) -> List[Dict]
    def fulltext_search(self, query: str, limit: int = 10) -> List[Dict]
    
    # 辅助查询方法
    def search_by_tax_type(self, tax_type: str, limit: int = 10) -> List[Dict]
    def search_by_incentive_method(self, method: str, limit: int = 10) -> List[Dict]
    def get_by_id(self, policy_id: int) -> Optional[Dict]
    def get_statistics(self) -> Dict
    def count_structured_results(self, tax_type: str, entity_keywords: List[str] = None) -> int
```

### 13.2 使用示例

```python
from modules.db_query import TaxIncentiveQuery

# 初始化查询对象
query = TaxIncentiveQuery()

# 智能搜索
results, total, intent = query.search("小微企业有哪些税收优惠？", limit=10)

# 打印结果
for r in results:
    print(f"[{r['tax_type']}] {r['incentive_items']} - {r['incentive_method']}")

print(f"共找到 {total} 条政策")
```

---

## 附录 A: 文件清单

| 文件路径 | 说明 |
|----------|------|
| `modules/db_query.py` | 核心查询模块 |
| `config/tax_query_config.json` | 查询配置文件 |
| `database/tax_incentives.db` | SQLite 数据库 |
| `tests/test_tax_extract.py` | 单元测试 |
| `docs/税收优惠查询调试备忘录.md` | 调试记录 |
| `docs/税收优惠查询系统_业务维护手册v3.md` | 业务维护手册 |

---

## 附录 B: 数据库表DDL

```sql
CREATE TABLE IF NOT EXISTS tax_incentives (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number           INTEGER,
    tax_type                TEXT NOT NULL,
    incentive_items         TEXT,
    qualification           TEXT,
    incentive_method        TEXT,
    detailed_rules          TEXT,
    legal_basis             TEXT,
    special_notes           TEXT,
    explanation             TEXT,
    effective_date          TEXT,
    expiry_date             TEXT,
    applicable_region       TEXT,
    policy_status           TEXT,
    industry_scope          TEXT,
    enterprise_type         TEXT,
    discount_rate           TEXT,
    application_process     TEXT,
    required_documents      TEXT,
    data_source             TEXT,
    data_quality            INTEGER DEFAULT 0,
    last_verified_date      TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    keywords                TEXT,
    tags                    TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS tax_incentives_fts USING fts5(
    tax_type,
    incentive_items,
    qualification,
    incentive_method,
    detailed_rules,
    legal_basis,
    explanation,
    keywords,
    content='tax_incentives',
    content_rowid='id'
);
```
