## 多路、多层智能路由财税咨询系统完整方案

---

### 一、整体路由架构图（文字描述）

系统采用三层路由架构，逐层细化意图并定向分发至对应数据源或处理模块：

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    第一层：数据源级路由                      │
│ 意图分类：企业私有数据 / 税收优惠 / 通用法规 / 其他           │
│ 决策方式：向量相似度匹配（预设意图模板）                     │
└─────────────────────────────────────────────────────────────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌───────────┐ ┌───────────────┐ ┌───────────┐ ┌───────────┐
│企业私有数据│ │ 本地优惠库    │ │外部法规API│ │ 拒绝回答 │
│ SQLite    │ │ SQLite        │ │           │ │          │
└───────────┘ └───────────────┘ └───────────┘ └───────────┘
    │               │               │
    ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                    第二层：表/域级路由                       │
│ 针对企业私有数据，识别数据域、指标、期间、复杂度              │
│ 决策方式：向量检索匹配数据域 + NER提取指标/时间               │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    第三层：跨域融合路由                      │
│ 若问题同时涉及私有数据+优惠/法规，执行：                     │
│   ① 第二层路由 + NL2SQL 查询私有数据                         │
│   ② 优惠库/法规库检索获取政策条件                            │
│   ③ LLM综合推理输出结论                                      │
└─────────────────────────────────────────────────────────────┘
```

---

### 二、每一层路由的意图识别规则/向量匹配策略/阈值

#### 2.1 第一层路由：数据源级意图分类

**策略**：基于向量相似度的零样本分类，使用 `all-MiniLM-L6-v2` 模型将用户问题与预设的意图模板向量进行余弦相似度比较。

**预设意图模板**（每个类别包含 5~10 条代表性问法，此处仅示例）：

| 意图类别 | 模板例句（用于生成向量） |
|----------|--------------------------|
| 企业私有数据 | “查询去年12月31日未分配利润”<br>“今年一季度管理费用”<br>“上月净利润与经营现金流差异”<br>“增值税申报表销项税额”<br>“企业研发费用发生额” |
| 税收优惠 | “最新研发费用加计扣除政策”<br>“小微企业增值税优惠”<br>“高新技术企业税率优惠”<br>“出口退税率是多少” |
| 通用法规 | “增值税申报期限”<br>“一般纳税人认定条件”<br>“企业所得税汇算清缴时间”<br>“发票丢失如何处理” |

**匹配阈值**：
- 取最高相似度分数 `max_sim`，若 `max_sim < 0.65`，则判定为“意图模糊”，转异常处理。
- 若 `max_sim >= 0.65`，则路由至对应数据源。
- 若最高类别为“企业私有数据”且相似度低于其他类别但高于阈值，仍路由至企业私有数据。

**实现方式**：
- 离线为每个模板例句生成向量，存入 `intent_templates` 表。
- 在线对用户问题生成向量，计算与所有模板向量的余弦相似度，按类别取平均或最高分。

#### 2.2 第二层路由：表/域级意图识别（仅企业私有数据）

**目标**：识别用户问题涉及的数据域、指标、期间、聚合条件，并确定查询复杂度。

**策略**：
- **数据域识别**：使用向量相似度匹配预定义的“数据域描述向量”。
- **指标识别**：利用同义词表 `domain_synonyms` 将口语化指标映射为标准字段名，同时确定所属域。
- **时间识别**：基于规则的正则表达式提取年份、月份、季度、期间范围。
- **复杂度判断**：根据提取到的指标个数、时间点个数、域个数自动归类。

**数据域预定义**（每个域需生成描述向量）：

| 域名 | 描述文本（用于向量化） |
|------|------------------------|
| 资产负债表域 | 资产负债表相关，包括资产、负债、所有者权益科目，如货币资金、应收账款、存货、固定资产、短期借款、应付账款、实收资本、未分配利润等。 |
| 利润表域 | 利润表相关，包括收入、成本、费用、利润科目，如营业收入、营业成本、销售费用、管理费用、财务费用、营业利润、净利润等。 |
| 现金流量表域 | 现金流量表相关，包括经营活动、投资活动、筹资活动现金流量，如销售商品收到的现金、购买商品支付的现金、投资支付的现金等。 |
| 科目余额域 | 科目余额表相关，包括各科目的期初余额、本期发生额、期末余额，以及辅助核算（部门、项目、客户等）。 |
| 增值税申报域 | 增值税申报表主表及附表数据，包括销项税额、进项税额、应纳税额、即征即退等。 |
| 企业所得税申报域 | 企业所得税申报表数据，包括应纳税所得额、应纳所得税额、减免税额等。 |
| 发票域 | 发票数据，包括进项发票、销项发票、发票金额、税额、状态等。 |
| 人事工资域 | 人员工资、社保、个税等数据。 |
| 工商信息域 | 企业工商登记信息，如注册资本、成立日期、经营范围、股东等。 |
| 企业基本画像域 | 综合财务比率、税收比率、经营指标等衍生数据。 |

**指标识别规则**：
- 同义词表 `domain_synonyms` 结构：`(phrase, domain, standard_field)`，例如 `("未分配利润", "资产负债表域", "retained_earnings")`。
- 将用户问题分词后匹配同义词，得到候选指标列表及其所属域。

**时间识别规则**（正则示例）：
- “去年12月31日” → 年份=当前年-1，月份=12，日=31（精确日期）
- “今年一季度” → 年份=当前年，季度=1，转换为月份范围 1-3
- “1月” → 年份=当前年（若未指定），月份=1
- “前三月” → 最近三个月（需根据当前日期推算）
- “2025年” → 年份=2025

**复杂度判断**：
- 单源单指标单期间：1个域，1个指标，1个时间点
- 单源单指标多期间：1个域，1个指标，多个时间点（如“每月”）
- 单源多指标多期间：1个域，多个指标，多个时间点
- 多源单指标单期间：多个域，1个指标，1个时间点
- 多源多指标多期间：多个域，多个指标，多个时间点

**输出**：路由结果对象包含：
- domains: 列表 [域1, 域2, ...]
- indicators: 列表 [ (standard_field, domain), ... ]
- time_conditions: 列表 [ {year, month, day?} ] 或范围表达式
- complexity_type: 上述复杂度类型

#### 2.3 第三层路由：跨域融合触发条件

当第一层路由为“企业私有数据”，且第二层路由完成后，**额外判断**用户问题是否隐含对税收优惠或法规的查询。判断方式：
- 在第二层指标识别后，若问题中包含优惠/法规相关关键词（如“符合条件”、“适用政策”、“是否可以享受”、“加计扣除”等），则标记为“跨域问题”。
- 也可通过向量检索匹配“跨域意图模板”，例如“企业是否符合研发费用加计扣除条件”的相似度。

若触发跨域，则进入第三层处理流程。

---

### 三、企业私有数据：NL2SQL生成规范 + 多表关联逻辑

#### 3.1 数据模型基础

系统已有多个统一视图（如 `vw_vat_declaration_full`、`vw_balance_sheet`、`vw_income_statement`、`vw_cash_flow`、`vw_subject_balance`、`vw_invoice`、`vw_employee`、`vw_business_info` 等）。每个视图均包含 `taxpayer_id`、`period_year`、`period_month` 等公共维度字段。

#### 3.2 NL2SQL 生成规范

**输入**：第二层路由输出对象 R = {domains, indicators, time_conditions, complexity_type}

**步骤**：
1. **确定主视图**：若 domains 长度为1，则直接使用对应视图；若长度>1，则需要多表关联。
2. **构建 SELECT 子句**：
   - 对于每个 indicator，使用其标准字段名，必要时添加表别名。
   - 若 indicators 为空（如查询整张表），则 SELECT *。
3. **构建 FROM 子句**：
   - 单域：`FROM 对应视图 AS t1`
   - 多域：根据预定义的关联关系，使用 JOIN 连接多个视图，关联条件为 `t1.taxpayer_id = t2.taxpayer_id AND t1.period_year = t2.period_year AND t1.period_month = t2.period_month`（若指标粒度一致）。
4. **构建 WHERE 子句**：
   - 添加纳税人条件：若用户指定了企业名称，需先通过 `taxpayer_info` 表获取 `taxpayer_id`；否则默认为当前登录企业（由会话上下文提供）。
   - 添加时间条件：将 time_conditions 转换为 SQL 条件，例如：
     - 单月：`period_year = ? AND period_month = ?`
     - 范围：`(period_year * 12 + period_month) BETWEEN start_month_num AND end_month_num`
     - 跨年处理：使用 `date` 拼接字段（若视图有日期字段）。
5. **聚合处理**：
   - 若时间条件为多期间且需要按期间返回，则添加 `GROUP BY period_year, period_month`。
   - 若要求汇总值，则使用 SUM、AVG 等聚合函数。

#### 3.3 多表关联逻辑

- **默认关联键**：所有业务视图均包含 `taxpayer_id`、`period_year`、`period_month`，可直接等值连接。
- **特殊关联**：若某视图无月份粒度（如工商信息），则只关联 `taxpayer_id`。
- **关联类型**：一般使用 INNER JOIN，但若某域可能无数据（如现金流量表月报缺失），则根据业务需求使用 LEFT JOIN。

**关联关系预定义表** `table_relationships`：
| domain1 | domain2 | join_condition |
|---------|---------|----------------|
| 利润表域 | 现金流量表域 | `i.taxpayer_id = c.taxpayer_id AND i.period_year = c.period_year AND i.period_month = c.period_month` |
| 资产负债表域 | 利润表域 | 同上（但资产负债表通常为期末时点数，需注意） |

#### 3.4 示例

- 查询“去年12月31日未分配利润”：
  - domain=资产负债表域，indicator=retained_earnings，time=单点（去年12月31日）
  - SQL: `SELECT retained_earnings FROM vw_balance_sheet WHERE taxpayer_id = ? AND period_year = 2025 AND period_month = 12 LIMIT 1`

- 查询“今年一季度每月管理费用-办公费发生额”：
  - domain=科目余额域，indicator=manage_expense_office，time=范围（2026年1-3月）
  - SQL: `SELECT period_month, SUM(manage_expense_office) as amount FROM vw_subject_balance WHERE taxpayer_id = ? AND period_year = 2026 AND period_month IN (1,2,3) GROUP BY period_month ORDER BY period_month`

- 查询“上月净利润与经营现金流差异”：
  - domains=[利润表域, 现金流量表域]，indicators=[net_profit, operating_cash_flow]，time=单月（上个月）
  - SQL: `SELECT i.net_profit, c.operating_cash_flow, (i.net_profit - c.operating_cash_flow) AS difference FROM vw_income_statement i JOIN vw_cash_flow c ON i.taxpayer_id = c.taxpayer_id AND i.period_year = c.period_year AND i.period_month = c.period_month WHERE i.taxpayer_id = ? AND i.period_year = ? AND i.period_month = ?`

---

### 四、本地优惠库：FTS + 向量混合检索策略

#### 4.1 数据结构

优惠库表 `tax_preference` 包含字段：
- id
- title（优惠名称）
- content（优惠详细描述、条件、计算公式、适用范围等）
- industry（适用行业）
- region（适用地区）
- effective_start, effective_end（有效期）
- 其他结构化字段（如优惠类型、税率、减免方式等）

建立 FTS5 虚拟表：
```sql
CREATE VIRTUAL TABLE tax_preference_fts USING fts5(title, content, industry, region, tokenize = 'chinese');
```

同时为每条记录生成语义向量（使用 `all-MiniLM-L6-v2` 对 `title + content` 编码），存入向量表 `tax_preference_vec`。

#### 4.2 混合检索策略

输入：用户问题 Q（经过第一层路由确定为“税收优惠”）

**步骤**：
1. **FTS全文检索**：
   ```sql
   SELECT id, title, content, bm25(tax_preference_fts) as score
   FROM tax_preference_fts
   WHERE tax_preference_fts MATCH ?
   ORDER BY score LIMIT 20;
   ```
   返回 BM25 排序的前 20 条。

2. **向量语义检索**：
   - 生成 Q 的向量 q_vec。
   - 从向量表检索最相似的 10 条（余弦距离）。
   ```sql
   SELECT p.id, p.title, p.content, vec_distance_cosine(v.embedding, ?) as distance
   FROM tax_preference_vec v
   JOIN tax_preference p ON v.id = p.id
   ORDER BY distance ASC LIMIT 10;
   ```

3. **结果融合**：
   - 取 FTS 前 5 条与向量检索前 5 条的并集（去重）。
   - 若需要精确排序，可计算每条的综合得分 = 0.5 * (1 - 归一化距离) + 0.5 * (1 - 归一化 BM25 倒数排名)，但简单取并集通常足够。

4. **返回**：将合并后的结果（标题 + 内容片段）作为上下文，构造 Prompt 给 LLM 生成最终答案。

#### 4.3 特殊处理

- 若用户问题包含具体行业、地区，可在 FTS 中增加过滤条件（如 `industry MATCH '制造业'`），或在向量检索后过滤。
- 对于需要精确条件匹配的优惠（如研发费用加计扣除），需在最终 LLM 回答中结合私有数据（跨域情况）进行判断。

---

### 五、跨域问题（数据+政策/法规）的决策流程与 Prompt 模板

#### 5.1 决策流程

1. **触发条件**：第一层路由为企业私有数据，且第二层完成后检测到“跨域关键词”或向量匹配跨域意图模板。
2. **并行执行**：
   - 分支 A：执行第二层 NL2SQL，获取企业私有数据结果（如研发费用金额、研发人员数量等）。
   - 分支 B：调用优惠库检索，获取相关政策条件（如加计扣除政策要求）。
3. **结果汇聚**：将私有数据结果和优惠政策文本送入 LLM 进行综合推理。
4. **生成答案**：LLM 依据数据是否符合政策条件，给出结论并附依据。

#### 5.2 Prompt 模板

```text
你是一位专业的财税顾问。请根据以下信息，判断企业是否符合税收优惠政策条件，并给出详细解释。

【企业私有数据】
{ 将 NL2SQL 查询结果以 JSON 或自然语言描述 }

【税收优惠政策】
{ 从优惠库检索到的相关政策原文或摘要 }

【用户问题】
{ 原始用户问题 }

请按以下步骤回答：
1. 列出政策的核心条件。
2. 逐条对照企业数据，说明是否满足。
3. 给出最终结论（符合/不符合/部分符合）及建议。

回答应专业、清晰，并引用数据支持结论。
```

#### 5.3 示例

用户问题：“我公司是否符合研发费用加计扣除政策条件？”

私有数据（NL2SQL 结果）：
```json
{
  "company_name": "XX科技有限公司",
  "year": 2025,
  "rd_expense": 1200000,
  "rd_staff_count": 15,
  "total_staff": 80,
  "rd_ratio": 0.1875
}
```

优惠政策：
```
政策名称：研发费用加计扣除政策
核心条件：
- 企业为居民企业；
- 研发费用真实发生，且费用范围符合规定；
- 研发人员占比不低于10%；
- 会计核算健全，能准确归集研发费用。
```

LLM 综合判断输出结论。

---

### 六、异常处理

#### 6.1 意图模糊（第一层路由相似度低于阈值）
- 返回提示：“抱歉，我没能完全理解您的问题，请尝试更明确的描述，例如：'查询去年净利润'、'小微企业增值税优惠'、'增值税申报期限'。”
- 记录模糊查询到日志，供后续优化。

#### 6.2 查询无结果（NL2SQL 返回空集）
- 若时间范围无数据：提示“未查询到该期间的对应数据，请确认期间是否正确或数据是否已录入。”
- 若指标不存在：提示“系统中未找到您提到的指标，请检查表达是否准确。”

#### 6.3 数据权限（当前企业无权限查看其他企业）
- 系统默认只能查询当前登录企业数据。若用户问题中指定了其他企业名称，需先校验权限，若无权限则提示“您无权查看其他企业的数据。”

#### 6.4 跨域冲突（政策条件与数据矛盾）
- 如数据不满足政策条件，LLM 会明确指出不符合项，并给出改进建议。
- 若政策条件模糊或需人工判断，提示“根据现有信息无法完全确定，建议咨询主管税务机关。”

#### 6.5 外部法规 API 调用失败
- 返回：“外部法规库服务暂时不可用，请稍后重试。”

#### 6.6 其他异常
- 记录错误日志，返回通用提示：“系统处理出现异常，请联系管理员。”

---

### 七、可直接落地的路由决策树/伪代码逻辑

#### 7.1 伪代码

```python
def route(user_query, context):
    # 1. 第一层路由
    intent = classify_intent(user_query)  # 返回 'private', 'preference', 'law', 'unknown'
    if intent == 'unknown':
        return reply_intent_unknown()
    
    if intent == 'preference':
        results = search_preference_db(user_query)  # 混合检索
        return format_preference_answer(results)
    
    if intent == 'law':
        results = call_law_api(user_query)
        return format_law_answer(results)
    
    # 2. 企业私有数据：第二层路由
    domain_result = analyze_private_query(user_query)  # 返回 domains, indicators, times, complexity
    if domain_result.error:
        return reply_analysis_error()
    
    # 检查是否跨域
    if is_cross_domain(user_query):
        # 并行执行
        private_data = execute_nl2sql(domain_result)
        policy_data = search_preference_db(user_query)  # 可能结合领域信息优化检索
        answer = cross_domain_reasoning(user_query, private_data, policy_data)
        return answer
    else:
        sql = generate_sql(domain_result, context.taxpayer_id)
        result = execute_sql(sql)
        return format_data_result(result, domain_result.complexity)
```

#### 7.2 关键函数说明

- `classify_intent(user_query)`：向量匹配意图模板，返回最高分类别。
- `analyze_private_query(user_query)`：
   - 向量匹配数据域（计算与各域描述向量的相似度，取 top 1~2）
   - 同义词匹配指标
   - 正则提取时间
   - 返回结构化对象
- `is_cross_domain(user_query)`：检测是否有跨域关键词，或向量匹配跨域模板。
- `execute_nl2sql(domain_result)`：按 3.2 节生成 SQL 并执行，返回 JSON 格式数据。
- `search_preference_db(user_query)`：执行 FTS+向量混合检索，返回前 K 条政策文本。
- `cross_domain_reasoning(user_query, private_data, policy_data)`：构造 Prompt 调用 LLM，返回自然语言答案。
- `generate_sql(domain_result, taxpayer_id)`：按 3.2 节生成 SQL 字符串。
- `format_data_result(result, complexity)`：将查询结果转换为自然语言表格或摘要。

---

### 八、总结

本方案完整构建了一个三层智能路由系统，充分利用向量检索进行意图分类、数据域识别、语义检索，结合 NL2SQL 精确查询私有数据，并通过跨域融合满足复杂决策需求。所有组件均可基于 SQLite 向量扩展和轻量级模型在 Windows 环境私有部署，满足企业级财税咨询的准确性、安全性和可扩展性要求。