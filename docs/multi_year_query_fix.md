# 多年全年查询修复文档

## 问题描述

用户报告两个查询只返回单年数据，缺少另一年的数据：

1. **查询1**: "2024年和2025年的全年营业收入比较分析" → 只返回2024年1-12月明细
2. **查询2**: "请对比2024年和2025年的全年营业收入" → 只返回2024年1月数据

## 根本原因

Stage 2 SQL生成prompt缺少多年全年查询的处理规则，导致LLM生成错误的SQL：

- **错误SQL**: `WHERE (period_year*100+period_month) BETWEEN 202401 AND 202412` （只查询2024年）
- **正确SQL**: `WHERE ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12)) AND time_range='本年累计'`

## 修复方案

### 1. Stage 1 Prompt 增强 (`prompts/stage1_system.txt`)

**修改位置**: Line 501, 537-548

**修改内容**:

1. 在 `filters.period` 示例中添加 `period_years` 字段：
```json
"period": {"year": 2025, "month": 1, "quarter": 1, "end_month": 12, "period_years": [2024, 2025]}
```

2. 添加规则 9c - 多年全年查询处理：
```
9c. 【重要】多年全年查询（如"2024年和2025年的全年营业收入"、"对比2024年和2025年的全年"）：
   - 当已识别实体中包含period_years字段时（如period_years=[2024, 2025]），必须在filters.period中包含period_years字段
   - "全年"/"年度"/"整年"表示查询每年12月的本年累计数据
   - 对于利润表/现金流量表域：设置period_years=[2024, 2025], month=12, profit_time_range="本年累计"或cash_flow_time_range="本年累计"
   - 对于资产负债表域：设置period_years=[2024, 2025], month=12
   - 对于财务指标域：设置period_years=[2024, 2025], month=12
   - 示例：用户问"2024年和2025年的全年营业收入比较" → filters.period = {"year": 2024, "period_years": [2024, 2025], "month": 12}, profit_time_range="本年累计"
```

### 2. Stage 2 Profit Prompt 增强 (`prompts/stage2_profit.txt`)

**修改位置**: Line 10-38

**修改内容**: 在【必备过滤】section中添加多年全年查询规则：

```
   - 枚举月份（如"12月和3月"）：period_month IN (12, 3) 或 ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=3))
   - 跨年枚举月份：必须使用 OR 连接，并用括号包裹整个条件，例如：
     WHERE taxpayer_id = :taxpayer_id
       AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=3))
       AND time_range = '本年累计'
   - **多年全年查询**（如"2024年和2025年的全年营业收入"、"对比2024年和2025年的全年"）：
     ⚠️ "全年"特指12月的本年累计数据，必须使用：
     WHERE taxpayer_id = :taxpayer_id
       AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
       AND time_range = '本年累计'
     或简化为：period_year IN (2024, 2025) AND period_month = 12 AND time_range = '本年累计'

     ⚠️ 关键判断依据：
     - 如果 filters.period.period_years 存在且长度>1 → 多年查询
     - 如果用户问"全年"/"年度"/"整年" → 查询12月的本年累计数据
     - 必须为每个年份生成独立的 (period_year=YYYY AND period_month=12) 条件
     - 禁止使用 BETWEEN（会返回中间月份的所有数据）
     - 禁止只查询最后一年（必须包含所有年份）
     - 必须添加 time_range = '本年累计' 过滤条件
   注意：当实体信息包含 period_months=[12, 3] 时，表示只查询这些特定月份，不是范围查询
   ⚠️ 重要：OR条件必须用括号包裹，避免与taxpayer_id条件混淆
```

### 3. Stage 2 Cash Flow Prompt 增强 (`prompts/stage2_cash_flow.txt`)

**修改位置**: Line 10-38

**修改内容**: 与 `stage2_profit.txt` 相同的多年全年查询规则

## 验证结果

所有3个测试用例通过 ✓

### 测试用例 1: "2024年和2025年的全年营业收入比较分析"

**生成SQL**:
```sql
WHERE taxpayer_id = '91330200MA2KXXXXXX'
  AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
  AND time_range = '本年累计'
```

**返回数据**:
- 2024年12月: 营业收入 18,749,947
- 2025年12月: 营业收入 24,345,057

### 测试用例 2: "请对比2024年和2025年的全年营业收入"

**生成SQL**: 同上

**返回数据**: 同上

### 测试用例 3: "2024年和2025年的全年经营活动现金流量净额对比"

**生成SQL**:
```sql
WHERE taxpayer_id = :taxpayer_id
  AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
  AND time_range = '本年累计'
```

**返回数据**:
- 2024年12月: 经营活动现金流量净额 10,904,782
- 2025年12月: 经营活动现金流量净额 14,158,841

## 影响范围

### 修改的文件
1. `prompts/stage1_system.txt` - Stage 1 意图解析prompt
2. `prompts/stage2_profit.txt` - 利润表SQL生成prompt
3. `prompts/stage2_cash_flow.txt` - 现金流量表SQL生成prompt

### 不需要修改的文件
- `prompts/stage2_balance_sheet.txt` - 已有多年查询规则（Line 36-47）
- `prompts/stage2_financial_metrics.txt` - 已有跨期比较规则（Line 56-126）
- `modules/entity_preprocessor.py` - 实体识别已正确（`period_years: [2024, 2025]`）
- `modules/intent_parser.py` - 已正确传递 `period_years` 到LLM（Line 56-57）

## 举一反三

此修复适用于所有类似的多年全年查询：

1. **利润表**: "2023年和2024年的全年净利润对比"
2. **现金流量表**: "2023年和2024年的全年现金净增加额比较"
3. **资产负债表**: "2024年和2025年年末总资产对比" （已支持）
4. **财务指标**: "2024年和2025年年末ROE对比" （已支持）

## 注意事项

1. **"全年"的定义**: 特指12月的本年累计数据，不是1-12月的所有月份
2. **time_range过滤**: 利润表和现金流量表必须添加 `time_range = '本年累计'`
3. **OR条件括号**: 必须用括号包裹，避免与taxpayer_id条件混淆
4. **禁止BETWEEN**: 会返回中间月份的所有数据，不符合"全年"语义

## 测试脚本

测试脚本位于: `test_multi_year_fix.py`

运行命令:
```bash
python test_multi_year_fix.py
```

## 修复日期

2026-03-13
