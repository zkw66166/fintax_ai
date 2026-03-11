# 多年年末查询修复总结

## 修复日期
2026-03-11

## 问题描述

用户报告了三个多年年末查询的错误：

1. **错误1**: "2024-2025每年末的总资产和总负债分析" → 只返回2025年12月数据（缺失2024年）
2. **错误2**: "2024-2025年末的总资产和总负债分析" → 返回2024年12月到2025年12月共13个月的数据
3. **错误3**: "2024、2025年末的总资产和总负债分析" → LLM要求澄清"请确认2024年的具体月份"

## 根本原因

1. **实体识别不完整**: 正则表达式未包含顿号"、"，导致"2024、2025年末"无法识别为多年查询
2. **执行顺序错误**: YYYY-MM模式匹配（line 1046）在多年范围检测（line 1079）之前执行，导致"2024-2025"被误识别为"2024年20月"
3. **"年末"处理逻辑缺陷**: 未针对多年年末场景设置`period_months=[12]`标志位
4. **Stage 2 Prompt不完整**: 缺少明确的多年年末SQL生成指令

## 解决方案（中策）

### 修改1: 扩展多年范围正则（`entity_preprocessor.py` line 1079）

**修改前**:
```python
m_year_range = re.search(r'(\d{4})\s*年?\s*[到至与和跟及\-]\s*(\d{4})\s*年?', resolved_query)
```

**修改后**:
```python
m_year_range = re.search(r'(\d{4})\s*年?\s*[到至与和跟及、\-]\s*(\d{4})\s*年?', resolved_query)
```

**说明**: 新增顿号"、"支持，解决错误3。

### 修改2: 调整检测顺序（`entity_preprocessor.py` line 1038-1055）

**修改前**: YYYY-MM模式检测 → 多年范围检测
**修改后**: 多年范围检测 → YYYY-MM模式检测

**新增代码** (line 1038-1055):
```python
# 3a. 多年范围检测（优先级高，必须在单年月份提取之前）
m_year_range = re.search(r'(\d{4})\s*年?\s*[到至与和跟及、\-]\s*(\d{4})\s*年?', resolved_query)
if m_year_range:
    start_y = int(m_year_range.group(1))
    end_y = int(m_year_range.group(2))
    # 只有在不是跨年月份范围的情况下才设置多年范围
    m_cross_year_check = re.search(
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*[到至与和跟及\-]\s*(\d{4})\s*年\s*(\d{1,2})\s*月',
        resolved_query
    )
    if not m_cross_year_check:
        result['period_year'] = start_y
        result['period_years'] = list(range(start_y, end_y + 1))
```

**说明**: 将多年范围检测提前到YYYY-MM模式之前，避免"2024-2025"被误识别为"2024年20月"。

### 修改3: 多年年末特殊处理（`entity_preprocessor.py` line 1088-1097）

**修改前**:
```python
if not result.get('period_month'):
    if '年末' in resolved_query:
        result['period_month'] = 12
    elif '年初' in resolved_query and result.get('domain_hint') != 'account_balance':
        result['period_month'] = 1
```

**修改后**:
```python
if not result.get('period_month'):
    if '年末' in resolved_query or '年底' in resolved_query:
        result['period_month'] = 12
        # 多年年末特殊处理：设置枚举月份列表，标记为每年12月
        if result.get('period_years') and len(result['period_years']) > 1:
            result['period_months'] = [12]  # 标记为枚举月份（每年12月）
    elif '年初' in resolved_query and result.get('domain_hint') != 'account_balance':
        result['period_month'] = 1
        # 多年年初特殊处理：设置枚举月份列表，标记为每年1月
        if result.get('period_years') and len(result['period_years']) > 1:
            result['period_months'] = [1]  # 标记为枚举月份（每年1月）
```

**说明**: 当检测到多年年末时，设置`period_months=[12]`标志位，明确告知LLM这是枚举月份查询。

### 修改4: 增强Stage 2 Prompt（`prompts/stage2_balance_sheet.txt` line 19-31）

**修改前**:
```
  - **多年年末查询**（如"2024和2025年末"、"2024-2025每年末"）：
    ⚠️ "年末"特指12月，必须使用：
    WHERE taxpayer_id = :taxpayer_id
      AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
    或简化为：period_year IN (2024, 2025) AND period_month = 12
```

**修改后**:
```
  - **多年年末查询**（如"2024和2025年末"、"2024-2025每年末"、"2024、2025年末"）：
    ⚠️ "年末"特指12月，必须使用：
    WHERE taxpayer_id = :taxpayer_id
      AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
    或简化为：period_year IN (2024, 2025) AND period_month = 12

    ⚠️ 关键判断依据：
    - 如果 filters.period.period_years 存在且长度>1 → 多年查询
    - 如果 filters.period.period_months=[12] → 每年12月（年末）
    - 必须为每个年份生成独立的 (period_year=YYYY AND period_month=12) 条件
    - 禁止使用 BETWEEN（会返回中间月份）
    - 禁止只查询最后一年（必须包含所有年份）
```

**说明**: 增加明确的判断依据和禁止事项，减少LLM误解。

## 测试结果

### 单元测试（`tests/test_year_end_queries.py`）

✅ 所有6个测试通过：
1. "2024-2025每年末" → `period_years=[2024, 2025]`, `period_month=12`, `period_months=[12]`
2. "2024-2025年末" → `period_years=[2024, 2025]`, `period_month=12`, `period_months=[12]`
3. "2024、2025年末" → `period_years=[2024, 2025]`, `period_month=12`, `period_months=[12]`
4. "2024年到2025年" → `period_years=[2024, 2025]`, `period_month=None`, `period_months=None`（范围查询，不受影响）
5. "2025年末" → `period_year=2025`, `period_month=12`, `period_months=None`（单年年末，不受影响）
6. "2024-2025年初" → `period_years=[2024, 2025]`, `period_month=1`, `period_months=[1]`

### 端到端测试（`tests/test_year_end_e2e.py`）

✅ 所有3个测试通过：
1. "TSE科技2024-2025每年末的总资产和总负债" → 返回2行数据（2024.12, 2025.12）
2. "TSE科技2024、2025年末的总资产和总负债" → 返回2行数据（2024.12, 2025.12）
3. "TSE科技2025年末的总资产和总负债" → 返回1行数据（2025.12）

**生成的SQL示例**:
```sql
WITH latest AS (
  SELECT taxpayer_id, taxpayer_name, period_year, period_month, revision_no,
         assets_end, liabilities_end,
         ROW_NUMBER() OVER (PARTITION BY taxpayer_id, period_year, period_month ORDER BY revision_no DESC) AS rn
  FROM vw_balance_sheet_eas
  WHERE taxpayer_id = '91310115MA2KZZZZZZ'
    AND ((period_year=2024 AND period_month=12) OR (period_year=2025 AND period_month=12))
)
SELECT taxpayer_name, period_year, period_month,
       assets_end AS "资产总计",
       liabilities_end AS "负债合计"
FROM latest
WHERE rn = 1
ORDER BY period_year, period_month
LIMIT 1000;
```

## 影响范围

### 修改的文件
1. `modules/entity_preprocessor.py` - 实体识别逻辑（约30行修改）
2. `prompts/stage2_balance_sheet.txt` - Stage 2 prompt增强（约7行新增）

### 新增的文件
1. `tests/test_year_end_queries.py` - 单元测试（约150行）
2. `tests/test_year_end_e2e.py` - 端到端测试（约130行）

### 不受影响的功能
- ✅ 单年年末查询（"2025年末"）
- ✅ 范围查询（"2024年到2025年"）
- ✅ 单年单月查询（"2025年1月"）
- ✅ L1/L2缓存系统
- ✅ 概念管线
- ✅ 跨域查询

## 成功标准

✅ 错误1修复：返回2024.12和2025.12两个月
✅ 错误2修复：返回2024.12和2025.12两个月
✅ 错误3修复：返回2024.12和2025.12两个月
✅ 单年年末不受影响：返回单个月
✅ 范围查询不受影响：返回所有中间月份
✅ L1/L2缓存正常工作
✅ 现有测试用例全部通过

## 后续建议

1. **监控LLM稳定性**: 虽然prompt已增强，但LLM仍可能偶尔误解，建议监控生产环境查询日志
2. **扩展测试覆盖**: 可增加更多年末表达方式的测试（如"年底"、"年终"等）
3. **文档更新**: 更新用户文档，说明支持的多年年末查询格式
