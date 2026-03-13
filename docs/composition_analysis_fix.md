# 构成/占比分析功能修复总结

## 问题描述

用户查询"2025年末的总资产构成分析"只返回总资产汇总数字，没有返回组成总资产的子项（流动资产、非流动资产）及其占比。

## 根本原因

1. **概念管线拦截**：查询被概念管线（concept pipeline）拦截，直接返回单一概念的值，没有走到 Stage 2 SQL 生成
2. **Stage 1 缺失识别规则**：`prompts/stage1_system.txt` 没有构成/结构查询的识别规则和示例
3. **Stage 2 缺失生成指导**：`prompts/stage2_balance_sheet.txt` 虽有 UNION ALL 模板，但缺少明确的触发条件

## 修复方案

### 1. 添加构成查询检测函数（`mvp_pipeline.py`）

```python
def is_composition_query(query: str) -> bool:
    """检测是否为构成/结构分析查询"""
    composition_keywords = ['构成', '组成', '结构', '分布', '占比', '比例', '明细']
    return any(keyword in query for keyword in composition_keywords)
```

### 2. 修改概念管线触发条件（`mvp_pipeline.py` line 563）

```python
# 添加 is_composition 检测
is_composition = is_composition_query(user_query)

# 修改触发条件，跳过构成查询
if len(concepts) >= 1 and time_gran and not is_multi_period and not is_composition:
    # 概念管线逻辑...
```

### 3. 增强 Stage 1 提示词（`prompts/stage1_system.txt`）

添加内容：
- **构成查询识别规则**（line 37-68）：关键词、层级映射、特殊处理说明
- **JSON 字段**：`query_type="composition"`, `composition_target`
- **示例**（示例4-6）：单目标、多层级、多目标构成查询

### 4. 增强 Stage 2 提示词（`prompts/stage2_balance_sheet.txt`）

添加内容：
- **构成查询特殊处理说明**（line 4-22）：UNION ALL 模式、占比计算公式
- **示例 SQL**（line 207-227）：单期间总资产构成分析的完整 SQL

## 修复效果

### 修复前
```
查询：2025年末的总资产构成分析
返回：1 行（只有总资产汇总）
{
  "period_year": 2025,
  "总资产": 639.40万
}
```

### 修复后
```
查询：TSE科技2025年末的总资产构成分析
返回：2 行（拆分为子项 + 占比）
{
  "项目名称": "流动资产",
  "金额": 3603992,
  "占比(%)": 56.37
}
{
  "项目名称": "非流动资产",
  "金额": 2790000,
  "占比(%)": 43.63
}
```

## 支持的查询类型

1. **单目标单期间**：
   - "2025年末的总资产构成分析"
   - "2025年末的总资产结构"
   - "2025年末的总资产占比分析"

2. **不同目标**：
   - "2025年末的总负债构成分析"
   - "2025年末的流动资产构成分析"（多层级）

3. **多目标**：
   - "2025年末的总资产和总负债构成分析"

4. **多期间**（已有模板支持）：
   - "2024和2025年末的总资产构成分析"

## 关键词支持

所有以下关键词都会触发构成分析：
- 构成
- 组成
- 结构
- 分布
- 占比
- 比例
- 明细

## 测试验证

运行测试脚本：
```bash
python test_composition_debug.py
```

预期输出：
- ✅ 检测到构成/结构查询，跳过概念管线
- ✅ Stage 1 输出 `query_type="composition"`
- ✅ Stage 2 生成 UNION ALL SQL
- ✅ 返回多行数据（每个子项一行）

## 文件修改清单

1. `mvp_pipeline.py` — 添加 `is_composition_query()` 函数，修改概念管线触发条件
2. `prompts/stage1_system.txt` — 添加构成查询识别规则和示例
3. `prompts/stage2_balance_sheet.txt` — 添加构成查询处理说明和示例 SQL
4. `test_composition_debug.py` — 调试测试脚本（新增）
5. `tests/test_composition_analysis.py` — 综合测试套件（新增）

## 注意事项

1. **不破坏现有逻辑**：所有修改都是增量式的，不影响非构成查询
2. **向后兼容**：旧查询不受影响，新字段 `query_type` 和 `composition_target` 是可选的
3. **多域支持**：虽然当前只实现了资产负债表域，但框架支持扩展到利润表、现金流量表等其他域
