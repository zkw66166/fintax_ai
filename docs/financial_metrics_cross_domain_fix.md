# Financial Metrics Cross-Domain Query Fix

## Problem Summary

User query: "2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"

**Issue 2b: Missing metric names in frontend**
- Backend returns: `{'metric_name': '净利率', '2024年3月': 25.5, '2025年3月': 25.5, ...}`
- Frontend displays: Row index (0, 1, 2) instead of metric names

**Issue 2c: Extra empty rows**
- Query requests 2 periods (2024-03, 2025-03)
- Result shows 16 rows (3 with data + 13 empty rows)

## Root Cause Analysis

### Issue 2b: Cross-Domain Merge Loses Metric Identity

**File**: `modules/cross_domain_calculator.py` (lines 57-92)

The `_merge_compare()` function:
1. Extracts numeric columns from each domain's results
2. Prefixes them with domain names: `f'{a_domain}_{col}'`
3. **Problem**: For financial_metrics domain, this creates `financial_metrics_metric_value` instead of preserving the `metric_name` dimension

**Current behavior**:
```python
# Line 74-79
a_nums = _extract_numeric(a_row)
b_nums = _extract_numeric(b_row)
for col, val in a_nums.items():
    result_row[f'{a_domain}_{col}'] = val  # ❌ Loses metric identity
```

**Why this happens**:
- `vw_financial_metrics` uses EAV model: `metric_name` (dimension) + `metric_value` (measure)
- Other domains use wide-table model: each metric is a separate column
- The merge function treats all numeric columns uniformly, losing the EAV structure

### Issue 2c: UNION ALL Semantics for Comparison Queries

**File**: `modules/cross_domain_calculator.py` (line 67)

```python
all_periods = sorted(set(a_by_period.keys()) | set(b_by_period.keys()))
```

**Problem**: Uses set UNION (`|`) which includes all periods from all domains
- Domain A has 3 periods: 2024-03, 2025-03, 2025-12
- Domain B has 13 periods: 2024-03 through 2025-03
- Result: 16 periods (UNION of both)

**Expected**: For comparison queries, only include periods explicitly requested by user
- User query: "2024年3月和2025年3月"
- Expected periods: 2024-03, 2025-03 only

## Solution Design

### Principle: Additive-Only Modification

**DO NOT**:
- Remove existing cross-domain merge logic
- Break existing queries that work correctly
- Modify L1/L2 cache logic

**DO**:
- Add special handling for financial_metrics domain
- Add period filtering for comparison queries
- Preserve backward compatibility

### Solution 1: Special Handling for Financial Metrics Domain

**Approach**: Detect when merging financial_metrics domain and preserve metric_name dimension

**Implementation** (`modules/cross_domain_calculator.py`):

```python
def _merge_compare(sub_results: list, query: str) -> dict:
    """合并多个子域查询结果（比较操作）。

    特殊处理：
    - financial_metrics 域：保留 metric_name 维度，按指标名称分组
    - 其他域：按期间分组（原有逻辑）
    """
    if len(sub_results) < 2:
        return _merge_list(sub_results)

    # 检测是否所有子域都是 financial_metrics
    all_fm = all(sr.get('domain') == 'financial_metrics' for sr in sub_results)

    if all_fm:
        # 新增：financial_metrics 专用合并逻辑
        return _merge_compare_financial_metrics(sub_results, query)

    # 原有逻辑：按期间合并
    return _merge_compare_by_period(sub_results, query)
```

**New function**: `_merge_compare_financial_metrics()`

```python
def _merge_compare_financial_metrics(sub_results: list, query: str) -> dict:
    """financial_metrics 域专用比较合并：按 metric_name 分组。

    输入示例：
    sub_results[0] = {
        'domain': 'financial_metrics',
        'data': [
            {'metric_name': '净利率', 'period_year': 2024, 'period_month': 3, 'metric_value': 25.5},
            {'metric_name': '增值税税负率', 'period_year': 2024, 'period_month': 3, 'metric_value': 3.7},
        ]
    }

    输出示例：
    {
        'operation': 'compare',
        'merged_data': [
            {'metric_name': '净利率', '2024年3月': 25.5, '2025年3月': 25.5, '变动': 0.0},
            {'metric_name': '增值税税负率', '2024年3月': 3.7, '2025年3月': 3.7, '变动': 0.0},
        ],
        'summary': '财务指标比较，共2个指标'
    }
    """
    # 1. 收集所有期间
    all_periods = set()
    for sr in sub_results:
        for row in sr.get('data', []):
            year = row.get('period_year')
            month = row.get('period_month')
            if year and month:
                all_periods.add((year, month))

    # 2. 按 metric_name 分组
    metric_groups = {}
    for sr in sub_results:
        for row in sr.get('data', []):
            metric_name = row.get('metric_name')
            if not metric_name:
                continue
            if metric_name not in metric_groups:
                metric_groups[metric_name] = {}

            year = row.get('period_year')
            month = row.get('period_month')
            if year and month:
                period_key = (year, month)
                metric_groups[metric_name][period_key] = row.get('metric_value')

    # 3. 构建输出行
    merged = []
    sorted_periods = sorted(all_periods)

    for metric_name, period_values in metric_groups.items():
        result_row = {'metric_name': metric_name}

        # 添加各期间列
        for year, month in sorted_periods:
            period_label = f'{year}年{month}月'
            result_row[period_label] = period_values.get((year, month))

        # 计算变动（如果有2个期间）
        if len(sorted_periods) == 2:
            val1 = period_values.get(sorted_periods[0])
            val2 = period_values.get(sorted_periods[1])
            if val1 is not None and val2 is not None:
                result_row['变动'] = round(val2 - val1, 2)
                if val1 != 0:
                    result_row['变动率(%)'] = round((val2 - val1) / val1 * 100, 2)

        merged.append(result_row)

    return {
        'operation': 'compare',
        'merged_data': merged,
        'summary': f'财务指标比较，共{len(merged)}个指标',
    }
```

### Solution 2: Period Filtering for Comparison Queries

**Approach**: Extract requested periods from query and filter merge results

**Implementation** (`modules/cross_domain_calculator.py`):

```python
def _extract_requested_periods(query: str, entities: dict) -> set:
    """从查询和实体中提取用户明确请求的期间。

    Returns:
        set of (year, month) tuples, or empty set if cannot determine
    """
    requested = set()

    # 从 entities 提取
    year = entities.get('period_year')
    month = entities.get('period_month')
    end_year = entities.get('period_end_year')
    end_month = entities.get('period_end_month')

    if year and month:
        requested.add((year, month))
    if end_year and end_month:
        requested.add((end_year, end_month))

    # 从查询文本提取（正则匹配 "YYYY年M月"）
    pattern = r'(\d{4})年(\d{1,2})月'
    for match in re.finditer(pattern, query):
        y = int(match.group(1))
        m = int(match.group(2))
        requested.add((y, m))

    return requested


def _merge_compare_by_period(sub_results: list, query: str) -> dict:
    """原有逻辑：按期间合并（非 financial_metrics 域）。

    新增：期间过滤（仅保留用户请求的期间）
    """
    if len(sub_results) < 2:
        return _merge_list(sub_results)

    a_data = sub_results[0].get('data', [])
    b_data = sub_results[1].get('data', [])
    a_domain = sub_results[0].get('domain', 'A')
    b_domain = sub_results[1].get('domain', 'B')

    a_by_period = _index_by_period(a_data)
    b_by_period = _index_by_period(b_data)

    # 原有逻辑：UNION ALL
    all_periods = sorted(set(a_by_period.keys()) | set(b_by_period.keys()))

    # 新增：期间过滤
    entities = sub_results[0].get('entities', {})  # 假设所有子结果共享 entities
    requested_periods = _extract_requested_periods(query, entities)

    if requested_periods:
        # 过滤：只保留请求的期间
        filtered_periods = []
        for period_str in all_periods:
            # 解析 period_str (e.g., "2024-03") 为 (year, month)
            match = re.match(r'(\d{4})-(\d{2})', period_str)
            if match:
                y = int(match.group(1))
                m = int(match.group(2))
                if (y, m) in requested_periods:
                    filtered_periods.append(period_str)

        if filtered_periods:
            all_periods = filtered_periods

    # 原有合并逻辑（不变）
    merged = []
    for period in all_periods:
        a_row = a_by_period.get(period, {})
        b_row = b_by_period.get(period, {})
        result_row = {'period': period}
        a_nums = _extract_numeric(a_row)
        b_nums = _extract_numeric(b_row)
        for col, val in a_nums.items():
            result_row[f'{a_domain}_{col}'] = val
        for col, val in b_nums.items():
            result_row[f'{b_domain}_{col}'] = val
        if len(a_nums) == 1 and len(b_nums) == 1:
            a_val = list(a_nums.values())[0]
            b_val = list(b_nums.values())[0]
            if a_val is not None and b_val is not None:
                result_row['差异'] = round(a_val - b_val, 2)
                result_row['差异率(%)'] = round((a_val - b_val) / b_val * 100, 2) if b_val != 0 else None
        merged.append(result_row)

    return {
        'operation': 'compare',
        'merged_data': merged,
        'summary': f'{a_domain} vs {b_domain}，共{len(merged)}个期间',
    }
```

## Implementation Plan

### Phase 1: Add Financial Metrics Special Handling

1. Add `_merge_compare_financial_metrics()` function
2. Modify `_merge_compare()` to detect and route to new function
3. Test with original failing query

### Phase 2: Add Period Filtering

1. Add `_extract_requested_periods()` helper
2. Modify `_merge_compare_by_period()` to filter periods
3. Test with queries that have extra empty rows

### Phase 3: Update Display Formatter

**File**: `modules/display_formatter.py`

Ensure `_format_table_rows()` correctly handles `metric_name` column:
- Already has `metric_name` in `COMMON_COLUMN_CN` mapping (line 47)
- Should work correctly once cross_domain_calculator preserves the column

### Phase 4: Testing

**Test cases**:
1. Original failing query: "2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析"
   - Expected: 3 rows with metric_name column
   - Expected: Only 2 period columns (2024年3月, 2025年3月)

2. Cross-domain query (non-financial_metrics): "2024年3月和2025年3月营业收入和增值税对比"
   - Expected: Original behavior preserved (period-based merge)

3. Single-domain query: "2024年3月增值税"
   - Expected: No impact (not cross-domain)

## Risk Assessment

**Low Risk**:
- ✅ Additive approach (new functions, not removing old logic)
- ✅ Backward compatible (original logic preserved for non-FM domains)
- ✅ No cache changes
- ✅ Easy rollback (revert new functions)

**Testing Required**:
- ⚠️ Test all cross-domain operation types (compare, ratio, reconcile, list)
- ⚠️ Test mixed domain queries (FM + non-FM)
- ⚠️ Verify display_formatter handles new structure

## Success Criteria

1. ✅ Frontend displays metric names (not row indices)
2. ✅ Only requested periods appear in results (no extra empty rows)
3. ✅ Backward compatibility maintained for non-FM queries
4. ✅ L1/L2 cache unaffected
5. ✅ All existing tests pass
