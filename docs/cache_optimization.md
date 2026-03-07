# 缓存优化 - L1/L2 持久化缓存

## 功能概述

L1/L2 持久化缓存是一个智能查询加速系统，通过两级缓存策略实现快速响应。L1 缓存完整查询结果，L2 缓存 SQL 模板实现跨纳税人查询复用。系统是公司感知的，避免了跨公司数据泄漏问题。

## 架构变更说明

**2026-03-06 更新**：移除了内存缓存（Stage 1 意图、Stage 2 SQL、结果、跨域缓存），原因是内存缓存使用 `query + taxpayer_type` 作为键，不包含 `company_id`，导致不同公司的相同类型查询可能返回错误的缓存数据（跨公司缓存污染）。

系统现在完全依赖 L1/L2 持久化缓存，它们是公司感知的，提供更好的跨会话持久化，且不会造成数据泄漏。

## 性能提升

| 场景 | 优化前 | 优化后 | 提速 |
|------|--------|--------|------|
| L1 缓存命中（完全相同查询） | 5.1s | 0.01s | 99.8% |
| L2 缓存命中（跨纳税人查询） | 5.1s | 1.6s | 68.6% |
| L2 智能适配（跨类型查询） | 5.1s | 1.7s | 66.7% |
| 完整 Pipeline（首次查询） | 5.1s | 5.1s | 0% |

## 工作原理

### 两级缓存架构

系统采用两级持久化缓存架构，按优先级依次检查：

1. **L1 缓存（完整结果缓存）**
   - 缓存完整的查询结果（包括 SQL、数据、解读）
   - 适用场景：完全相同的查询（公司 + 查询内容 + 响应模式）
   - 响应时间：~0.01s
   - 最大文件数：1500
   - 缓存键：MD5(`company_id|normalized_query|response_mode`)

2. **L2 缓存（SQL 模板缓存）**
   - 缓存 SQL 模板（将 `taxpayer_id = 'xxx'` 替换为 `{{TAXPAYER_ID}}`）
   - 适用场景：相同查询内容，不同纳税人
   - 响应时间：~1.6s（SQL 执行 + LLM 解读）
   - 最大文件数：500
   - **域感知缓存键**（2026-03-06 更新）：
     - 财务报表域（balance_sheet, profit, cash_flow, account_balance）：`MD5(query|mode|fs|accounting_standard)` —— 按会计准则区分，与纳税人类型无关
     - VAT域：`MD5(query|mode|vat|taxpayer_type)` —— 按纳税人类型区分
     - EIT域：`MD5(query|mode|eit)` —— 无需区分
     - 其他：`MD5(query|mode|taxpayer_type|accounting_standard)` —— 向后兼容

3. **完整 Pipeline**
   - 完整的 NL2SQL 流程（意图解析 + SQL 生成 + 执行 + 解读）
   - 适用场景：首次查询或缓存未命中
   - 响应时间：~5.1s

**注意**：内存缓存（Stage 1 意图、Stage 2 SQL、结果、跨域）已移除，因为它们不是公司感知的，会导致跨公司数据泄漏。

### SQL 模板化

SQL 模板化是 L2 缓存的核心技术，通过正则表达式将 SQL 中的纳税人 ID 替换为占位符。

### 智能适配

当会计准则或纳税人类型不匹配时，系统会自动尝试适配视图名称：

- **财务报表域**：按会计准则适配（企业会计准则 ↔ 小企业会计准则），视图名 `_eas` ↔ `_sas`
- **VAT域**：不支持适配（一般纳税人和小规模纳税人列结构差异过大）
- **EIT域**：无需适配（不区分纳税人类型或会计准则）

## 使用指南

### 配置参数

所有配置参数位于 `config/settings.py`：

- `CACHE_ENABLED = False` — **已弃用**，内存缓存已移除
- `QUERY_CACHE_ENABLED = True` — L1 缓存开关
- `QUERY_CACHE_MAX_FILES_L1 = 1500` — L1 最大文件数
- `QUERY_CACHE_ENABLED_L2 = True` — L2 缓存开关
- `QUERY_CACHE_MAX_FILES_L2 = 500` — L2 最大文件数
- `TAXPAYER_TYPE_SMART_ADAPT = True` — L2 智能适配开关

### 缓存统计

访问 \`GET /api/cache/stats\` 查看缓存统计信息。

### 查询路径日志

系统会记录每个查询所走的路径，日志文件位于 \`logs/query_path.log\`（JSON Lines 格式）。

路径类型：
- \`l1\` - L1 缓存命中（完全相同查询）
- \`l2\` - L2 缓存命中（跨纳税人查询）
- \`l2_adapted\` - L2 智能适配（跨类型查询）
- \`pipeline\` - 完整 Pipeline（首次查询）

## 技术支持

如需更多技术细节，请参考：
- [L2 缓存技术设计文档](technical/l2_cache_design.md)
- [CLAUDE.md](../CLAUDE.md) - 项目整体架构
