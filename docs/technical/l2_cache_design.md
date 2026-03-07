# L2 缓存技术设计文档

## 架构概览

L2 模板缓存是一个基于 SQL 模板化的查询加速系统，通过缓存 SQL 模板并在运行时实例化，实现跨纳税人查询的快速响应。

## 核心模块

### 1. Template Cache (api/services/template_cache.py)

#### 功能
- SQL 模板化和实例化
- L2 缓存的保存和读取
- 独立 LRU 淘汰

#### 关键函数

**templatize_sql(sql, company_id)** - 将 SQL 中的 taxpayer_id 替换为模板占位符

**instantiate_sql(template, company_id)** - 将模板实例化为可执行的 SQL

**save_template_cache(...)** - 保存 L2 缓存到文件

**get_template_cache(...)** - 从文件读取 L2 缓存

### 2. View Adapter (api/services/view_adapter.py)

#### 功能
- 视图映射表管理
- SQL 视图名称适配

#### 视图映射

- general + ASBE: vw_vat_return_general, vw_balance_sheet_eas, vw_profit_eas, vw_cash_flow_eas
- small + ASSE: vw_vat_return_small, vw_balance_sheet_sas, vw_profit_sas, vw_cash_flow_sas

### 3. Query Path Logger (api/services/query_path_logger.py)

#### 功能
- 记录每个查询所走的路径
- JSON Lines 格式日志

### 4. Cache Stats API (api/routes/cache_stats.py)

#### 功能
- 提供缓存统计信息
- 计算命中率和性能指标

## 缓存策略

### L1 vs L2 缓存

| 特性 | L1 缓存 | L2 缓存 |
|------|---------|---------|
| 缓存内容 | 完整结果 | SQL 模板 |
| 适用场景 | 完全相同的查询 | 跨纳税人查询 |
| 响应时间 | ~0.01s | ~1.6s |
| 最大文件数 | 1500 | 500 |

### LRU 淘汰策略

L1 和 L2 缓存采用独立的 LRU 淘汰策略，互不影响。

## 执行流程

1. L1 缓存检查 → Hit: 返回（0.01s）
2. L2 缓存检查 → Hit: 实例化 SQL → 执行 → 返回（1.6s）
3. 智能适配检查 → Hit: 适配视图 → 执行 → 返回（1.7s）
4. 完整 Pipeline → 意图解析 → SQL 生成 → 执行 → 返回（5.1s）

## 性能优化

1. 正则表达式优化 - 预编译模式，单次替换
2. 缓存键设计 - 包含 taxpayer_type 和 accounting_standard
3. 文件系统优化 - JSON 文件 + 内存索引

## 扩展指南

### 添加新的视图映射

编辑 api/services/view_adapter.py 中的 VIEW_MAPPING 字典。

### 调整缓存大小

编辑 config/settings.py 中的 QUERY_CACHE_MAX_FILES_L1 和 QUERY_CACHE_MAX_FILES_L2。

### 禁用 L2 缓存

设置 QUERY_CACHE_ENABLED_L2 = False

## 监控和调试

- 查看缓存统计: GET /api/cache/stats
- 查看查询路径日志: tail -f logs/query_path.log
- 清理缓存: rm -rf cache/*.json

## 已知限制

1. SQL 模板化仅支持 taxpayer_id = 'xxx' 模式
2. 智能适配仅支持预定义的视图映射
3. L2 缓存仍需执行 SQL（~1.6s）

## 未来优化方向

1. L2 缓存预热
2. 按域设置不同 TTL
3. 分布式缓存（Redis）
4. 缓存预测
