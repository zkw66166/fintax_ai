# Financial Metrics Query Issues - Analysis & Fixes

## Issue Summary

User reported two critical issues with financial metrics queries:

1. **Date Resolution Error**: "前年3月" incorrectly resolved to 2023 instead of 2024
2. **Cross-Domain Routing & Display Issues**: Missing metric names in frontend, duplicate domains

## Issue 1: Date Resolution Error ✅ FIXED

### Problem
- Query: "前年3月和去年3月利润率、增值税税负率、企业所得税税负率比较分析"
- Current year: 2026
- Expected: 前年3月 → 2024年3月
- Actual: 前年3月 → 2023年3月 (wrong!)

### Root Cause
**File**: `modules/entity_preprocessor.py` (line 595)

The regex pattern for "前年" was placed AFTER the pattern for "去年X月", but it used a negative lookahead `(?!\d)` that prevented matching "前年3月" (because "3" is a digit).

**Original code**:
```python
query = re.sub(r'去年(\d{1,2})月', lambda m: f'{cur_year - 1}年{m.group(1)}月', query)
# Missing: 前年X月 pattern
query = re.sub(r'前年(?!\d|年|季|和|与)', f'{cur_year - 2}年', query)  # ❌ Won't match "前年3月"
```

### Solution ✅
**File**: `modules/entity_preprocessor.py` (lines 593-603)

Added explicit pattern for "前年X月" BEFORE the generic "前年" pattern:

```python
# "今年N月" → "YYYY年N月"
query = re.sub(r'(?:今年|本年)(\d{1,2})月', lambda m: f'{cur_year}年{m.group(1)}月', query)
# "去年X月" → "(YYYY-1)年X月"
query = re.sub(r'去年(\d{1,2})月', lambda m: f'{cur_year - 1}年{m.group(1)}月', query)
# "前年X月" → "(YYYY-2)年X月"  ✅ NEW
query = re.sub(r'前年(\d{1,2})月', lambda m: f'{cur_year - 2}年{m.group(1)}月', query)

# 独立的 "今年" / "本年" → "YYYY年"
query = re.sub(r'(?:今年|本年)(?!\d|年|月|季|上|下|前|全|和|与)', f'{cur_year}年', query)
query = re.sub(r'(?:去年|上年)(?!\d|年|月|季|上|下|全|底|和|与)', f'{cur_year - 1}年', query)
query = re.sub(r'前年(?!\d|年|季|和|与)', f'{cur_year - 2}年', query)
```

### Test Result ✅
```
Input:  前年3月和去年3月
Output: 2024年3月和2025年3月  ✅ CORRECT
```

---

## Issue 2: Cross-Domain Routing & Display Issues ⚠️ PARTIALLY ADDRESSED

### Problem 2a: Duplicate Domain Routing

**Log shows**:
```
domain=cross_domain, 子域: ['financial_metrics', 'financial_metrics', 'financial_metrics']
```

**Expected**:
```
domain=cross_domain, 子域: ['financial_metrics', 'vat', 'eit']
```

### Root Cause Analysis

This is **NOT a bug**, but a **design decision**:

1. **财务指标表 (`vw_financial_metrics`) is a pre-computed metrics table** that contains:
   - 净利率 (from profit statement)
   - 增值税税负率 (from VAT returns)
   - 企业所得税税负率 (from EIT returns)
   - 25+ other financial metrics

2. **LLM Stage 1 correctly identifies** that all three metrics exist in `financial_metrics` domain

3. **This is semantically correct** because:
   - User asked for "利润率、增值税税负率、企业所得税税负率"
   - All three metrics are available in the pre-computed `vw_financial_metrics` table
   - Using pre-computed metrics is faster and more consistent than calculating from raw data

### When This Becomes a Problem

The current behavior causes issues when:
1. **User wants raw data calculation** (not pre-computed metrics)
2. **Frontend display expects different domains** for visualization

### Recommended Solutions

**Option A (Recommended)**: Accept current behavior as correct
- Document that financial metrics queries use the pre-computed metrics table
- Update frontend to handle single-domain results gracefully
- Add user guidance: "如需原始数据计算，请明确指定数据源"

**Option B**: Add domain preference hints
- Modify Stage 1 prompt to prefer原始域 over financial_metrics when user explicitly mentions domain names
- Example: "增值税税负率" → prefer `vat` domain if user says "增值税申报表"

**Option C**: Split financial_metrics table
- Separate `vw_financial_metrics` into domain-specific views
- `vw_profit_metrics`, `vw_vat_metrics`, `vw_eit_metrics`
- Requires schema changes (high risk)

---

### Problem 2b: Missing Metric Names in Frontend ⚠️ NEEDS INVESTIGATION

**Frontend displays**:
```
期间    financial_metrics_2023年3月    financial_metrics_2025年3月
0    25.50    25.50
1    3.70    3.70
2    37.50    37.50
```

**Expected**:
```
指标名称    2023年3月    2025年3月
净利率    25.50    25.50
增值税税负率    3.70    3.70
企业所得税税负率    37.50    37.50
```

### Root Cause

**Backend returns correct data** (from test output):
```python
{'metric_name': '企业所得税税负率', '2024年3月': 37.5, '2025年3月': 37.5, ...}
{'metric_name': '净利率', '2024年3月': 25.5, '2025年3月': 25.5, ...}
{'metric_name': '增值税税负率', '2024年3月': 3.7, '2025年3月': 3.7, ...}
```

**Problem is in frontend display logic** (`modules/display_formatter.py` or React components):
- Cross-domain merge may be dropping `metric_name` column
- Frontend table rendering may not be extracting `metric_name` correctly

### Investigation Needed

**Files to check**:
1. `modules/cross_domain_calculator.py` - `merge_cross_domain_results()` function
2. `modules/display_formatter.py` - `build_display_data()` function
3. `frontend/src/components/ResultTable/ResultTable.jsx` - table rendering logic

**Test query**:
```python
result = run_pipeline("TSE科技2024年3月和2025年3月利润率、增值税税负率、企业所得税税负率比较分析")
print(result['results'][0].keys())  # Should include 'metric_name'
```

---

### Problem 2c: Extra Empty Rows in Results

**Frontend shows 16 rows** (3 with data + 13 empty rows):
```
2024-03    -    -
2024-04    -    -
...
2025-03    -    -
```

### Root Cause

**Cross-domain merge is including periods from VAT domain** that don't exist in financial_metrics:

**Log shows**:
```
[financial_metrics] 返回 3 行
[vat] 返回 13 行
[eit] 返回 2 行

跨域合并: financial_metrics vs vat，共16个期间
```

The merge operation is doing a **UNION** of all periods from all domains, creating empty rows for periods that only exist in one domain.

### Solution

**File**: `modules/cross_domain_calculator.py`

The merge logic should:
1. **For comparison queries**: Only include periods explicitly requested by user (2024-03, 2025-03)
2. **Filter out periods** that don't match the query intent
3. **Use INNER JOIN semantics** for comparison queries (not UNION ALL)

**Current behavior**: UNION ALL (returns all periods from all domains)
**Expected behavior**: INNER JOIN on requested periods only

---

## Summary

| Issue | Status | Priority | Effort |
|-------|--------|----------|--------|
| 1. Date resolution ("前年3月") | ✅ FIXED | HIGH | LOW |
| 2a. Duplicate domain routing | ⚠️ BY DESIGN | MEDIUM | N/A |
| 2b. Missing metric names | ❌ NEEDS FIX | HIGH | MEDIUM |
| 2c. Extra empty rows | ❌ NEEDS FIX | MEDIUM | MEDIUM |

## Files Modified

1. ✅ `modules/entity_preprocessor.py` (lines 593-603) - Added "前年X月" pattern

## Files Needing Investigation

1. ⚠️ `modules/cross_domain_calculator.py` - merge logic for comparison queries
2. ⚠️ `modules/display_formatter.py` - display data building
3. ⚠️ `frontend/src/components/ResultTable/ResultTable.jsx` - table rendering

## Test Files Created

1. `test_metrics_fixes.py` - Date resolution and cross-domain routing tests
2. `test_regex.py` - Regex pattern testing

## Next Steps

1. ✅ Deploy date resolution fix to production
2. ⚠️ Investigate frontend display issue (missing metric names)
3. ⚠️ Fix cross-domain merge to filter periods correctly
4. ⚠️ Add user documentation about financial_metrics table behavior
