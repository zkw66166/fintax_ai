
## 缓存策略（L1 + L2）

### 两级持久化缓存架构

fintax_ai 采用两级持久化缓存系统，L1和L2均为文件存储，服务器重启后数据保留，且具备公司感知能力。

### 缓存流程图

```
请求到达
    ↓
thinking_mode == "quick" or "think"?
    ↓ 是
L1缓存检查 (Line 49-76)
    ↓ 命中
返回完整缓存结果（跳过所有pipeline）
    ↓ 未命中
L2缓存检查 (Line 79-144)
    ↓ 命中
实例化SQL → 执行 → 返回（跳过Stage 1+2）
    ↓ 未命中
L2智能适配 (Line 148-223)
    ↓ 命中
适配SQL → 执行 → 保存新L2 → 返回
    ↓ 未命中
执行完整pipeline (Line 233-325)
    ├─→ Stage 1: Intent Parser (LLM)
    ├─→ Stage 2: SQL Writer (LLM)
    ├─→ SQL Audit
    ├─→ SQL Execution
    └─→ Display Formatting
    ↓
保存到L1 (Line 286-294)
保存到L2 (Line 297-314)
    ↓
返回结果
```

---

### L1缓存：完整结果缓存

#### 作用

存储完整的查询结果，包括：
- SQL执行结果（results）
- 显示数据（display_data）
- 数据解读（interpretation）
- 路由信息（route）
- 所有元数据

#### 缓存键

```
MD5(company_id | normalized_query | response_mode)
```

示例：
- 查询: "华兴科技2025年1月增值税"
- company_id: "91110000MA01234567"
- response_mode: "detailed"
- 缓存键: MD5("91110000MA01234567|华兴科技2025年1月增值税|detailed")

#### 存储结构

文件路径: cache/{cache_key}.json

文件内容包含：
- cache_key: 缓存键
- company_id: 公司ID
- query: 查询文本
- response_mode: 响应模式
- route: 路由类型
- result: 完整结果对象
- interpretation: 数据解读文本
- created_at: 创建时间
- accessed_at: 最后访问时间
- access_count: 访问次数

#### 介入时机

检查时机（最早介入，Line 49-76）：
- Quick模式: 返回缓存结果 + 缓存解读（0次LLM调用）
- Think模式: 返回缓存结果 + 设置need_reinterpret=True（前端触发新解读）

保存时机（pipeline执行完成后，Line 286-294）：
- 剥离瞬态键后保存完整结果

#### LRU淘汰策略

- 最大文件数: 1500
- 淘汰逻辑: 按访问时间排序，删除最旧文件
- 内存索引: 服务器启动时从磁盘重建，快速查找

#### 三种模式交互

| 模式 | L1缓存行为 | LLM调用 | 前端行为 |
|------|-----------|---------|---------|
| Quick | 返回缓存结果 + 缓存解读 | 0次 | 直接显示 |
| Think | 返回缓存结果 + 设置need_reinterpret | 0次（pipeline），1次（解读） | 触发/api/interpret |
| Deep | 完全绕过L1缓存 | 2次（Stage 1+2） | 显示新结果 |

---

### L2缓存：SQL模板缓存

#### 作用

存储SQL模板（将taxpayer_id替换为占位符），实现：
- 跨公司复用: 同类型查询可用于不同公司
- 智能适配: 财务报表可在会计准则间自动适配（_eas ↔ _sas）

#### 缓存键（域感知，2026-03-06重构）

财务报表（balance_sheet, profit, cash_flow, account_balance）：
```
MD5(query | mode | "fs" | accounting_standard)
```

增值税：
```
MD5(query | mode | "vat" | taxpayer_type)
```

企业所得税：
```
MD5(query | mode | "eit")
```

未知域（向后兼容）：
```
MD5(query | mode | taxpayer_type | accounting_standard)
```

#### 存储结构

文件路径: cache/template_{cache_key}.json

文件内容包含：
- cache_key: 缓存键
- query: 查询文本
- response_mode: 响应模式
- taxpayer_type: 纳税人类型
- accounting_standard: 会计准则
- domain: 领域
- sql_template: SQL模板（带占位符）
- intent: Stage 1意图JSON
- created_at: 创建时间

#### 模板化与实例化

模板化：
- 将SQL中的taxpayer_id替换为占位符:taxpayer_id
- 示例: WHERE taxpayer_id = '91110000MA01234567' → WHERE taxpayer_id = :taxpayer_id

实例化：
- 将占位符替换为实际taxpayer_id
- 示例: WHERE taxpayer_id = :taxpayer_id → WHERE taxpayer_id = '91110000MA01234567'

#### 介入时机

检查时机（L1未命中后，Line 79-144）：
1. 获取纳税人类型和会计准则
2. 检测查询的域类别
3. 查找L2缓存
4. 如果命中，实例化SQL并执行
5. 返回结果（跳过Stage 1+2）

保存时机（pipeline执行完成后，Line 297-314）：
1. 模板化SQL
2. 获取纳税人类型和会计准则
3. 保存模板到L2缓存

#### 智能适配（财务报表专用）

目的: 当L2缓存未命中但存在对立会计准则的缓存时，自动适配SQL

适配逻辑（Line 148-223）：
1. 检测cache_domain为"financial_statement"
2. 查找对立会计准则的缓存
3. 适配SQL（交换_eas ↔ _sas视图后缀）
4. 实例化并执行适配后的SQL
5. 保存新的L2缓存

适配规则：
- 企业会计准则 → 小企业会计准则: _eas → _sas
- 小企业会计准则 → 企业会计准则: _sas → _eas

限制: 增值税查询不适配，因为列结构差异显著：
- 一般纳税人: output_tax, input_tax, tax_payable
- 小规模纳税人: tax_due_total

#### LRU淘汰策略

- 最大文件数: 500
- 淘汰逻辑: 与L1相同，按文件访问时间排序删除最旧文件

---

### 缓存效果对比

| 特性 | L1缓存 | L2缓存 |
|------|--------|--------|
| 存储内容 | 完整结果（SQL+数据+解读+显示） | SQL模板（仅SQL，taxpayer_id占位符） |
| 缓存键 | company_id + query + mode | query + mode + type/standard（域感知） |
| 跨公司复用 | 否（公司特定） | 是（模板化） |
| 智能适配 | 否 | 是（财务报表可适配会计准则） |
| 介入时机 | 最早（Line 49） | L1未命中后（Line 79） |
| 跳过环节 | 跳过所有pipeline | 跳过Stage 1+2（仍需执行SQL） |
| LLM调用 | 0次 | 0次 |
| SQL执行 | 0次 | 1次 |
| 最大文件数 | 1500 | 500 |
| LRU淘汰 | 是 | 是 |

---

### 实际案例

案例1：完全命中L1
- 查询: "华兴科技2025年1月增值税"
- 模式: Quick
- 流程: L1命中 → 返回缓存结果
- 性能: LLM调用0次，SQL执行0次，响应时间<50ms

案例2：L1未命中，L2命中
- 查询: "鑫源贸易2025年2月增值税"（相同查询，不同公司）
- 模式: Quick
- 流程: L1未命中 → L2命中 → 实例化SQL → 执行 → 返回
- 性能: LLM调用0次，SQL执行1次，响应时间~200ms
- 节省: 2次LLM调用（约3-5秒）

案例3：L2智能适配
- 查询: "鑫源贸易2025年资产负债表"（小规模纳税人+小企业会计准则）
- 前提: 华兴科技的缓存存在（一般纳税人+企业会计准则）
- 流程: L1未命中 → L2未命中 → L2智能适配命中 → 适配SQL → 执行 → 保存新L2 → 返回
- 性能: LLM调用0次，SQL执行1次，响应时间~250ms
- 节省: 2次LLM调用（约3-5秒）

案例4：Deep模式绕过缓存
- 查询: "华兴科技2025年1月增值税"
- 模式: Deep
- 流程: 跳过L1+L2 → 执行完整pipeline → 保存L1+L2 → 返回
- 性能: LLM调用2次，SQL执行1次，响应时间~3-5秒

---

### 缓存配置

```python
# config/settings.py

# L1缓存配置
QUERY_CACHE_ENABLED = True
QUERY_CACHE_DIR = PROJECT_ROOT / "cache"
QUERY_CACHE_MAX_FILES_L1 = 1500

# L2缓存配置
QUERY_CACHE_ENABLED_L2 = True
QUERY_CACHE_MAX_FILES_L2 = 500
QUERY_CACHE_L2_PREFIX = "template_"

# 智能适配开关
TAXPAYER_TYPE_SMART_ADAPT = True

# 缓存失效策略
CACHE_INVALIDATE_L2_ON_DATA_UPDATE = False
```
