# Concept Pipeline Routing Simplification (2026-03-09)

## Summary

Simplified the concept pipeline routing strategy by removing the cross-domain concept pipeline branch. All multi-domain queries now route to the LLM cross-domain pipeline, while the concept pipeline only handles single-domain queries.

## Changes Made

### Phase 1: Remove Cross-Domain Concept Pipeline Branch

**File**: `D:\fintax_ai\mvp_pipeline.py` (lines 557-576)

**Before**: Lines 558-617 contained a cross-domain concept pipeline branch that attempted deterministic SQL generation for multi-domain queries.

**After**: Removed 60 lines of cross-domain concept pipeline logic. Now `if domain == 'cross_domain':` goes directly to LLM cross-domain pipeline.

**Impact**:
- All multi-domain queries → LLM cross-domain pipeline (more comprehensive results)
- Single-domain concept queries still benefit from deterministic SQL (lines 502-556 unchanged)
- Eliminates incomplete results from cross-domain concept pipeline

---

### Phase 2: Fix Single-Domain L2 Cache Retrieval Params

**File**: `D:\fintax_ai\api\routes\chat.py` (lines 244-278)

**Problem**: Single-domain L2 cache retrieval only passed `{'taxpayer_id': company_id}`, but concept pipeline may need additional params like `year`, `quarter`, `time_range`, `vat_item_type`, `vat_time_range`, `filter_*`.

**Solution**: Added concept pipeline param reconstruction logic with static params support:
1. Check if `pipeline_type == 'concept'`
2. Load static params from template (constant values like `vat_item_type`, `time_range`)
3. Extract param keys from SQL using regex `r':(\w+)'`
4. Rebuild dynamic params from `entities_for_cache`:
   - `year` → `period_year`
   - `quarter` → `period_quarter`
   - `month` → `period_month`
   - `year_N` → `period_years[N-1]`
   - `month_N` → `period_months[N-1]`

**Impact**: Single-domain concept queries can now hit L2 cache correctly with all required params.

---

### Phase 3: Update L2 Cache Save Logic for Single-Domain Concept Queries

**File**: `D:\fintax_ai\api\routes\chat.py` (lines 409-461)

**Problem**: Single-domain concept queries (`domain != 'cross_domain'`) didn't save to L2 cache because the save logic was inside the `if domain == "cross_domain"` block.

**Solution**: Moved concept pipeline L2 cache save logic OUTSIDE the `if domain == "cross_domain"` block to a new `if result.get("concept_results"):` block that runs first.

**New L2 Cache Save Priority**:
1. `if result.get("concept_results"):` — concept pipeline (single-domain or any domain)
2. `elif domain == "cross_domain":` — LLM cross-domain pipeline
3. `elif sql:` — single-domain standard pipeline

**Impact**: Single-domain concept queries now save to L2 cache with `pipeline_type='concept'`.

---

### Phase 4: Code Quality Improvements

**File**: `D:\fintax_ai\api\routes\chat.py` (line 3)

**Change**: Moved `import re` to module level (was inline inside function).

**Rationale**: Module-level imports are more efficient and follow Python best practices.

---

### Phase 5: Static Params Support for Concept Pipeline

**Files**:
- `D:\fintax_ai\api\services\template_cache.py` (lines 201-218)
- `D:\fintax_ai\api\routes\chat.py` (lines 122-146, 247-280)

**Problem**: Constant params from concept definitions (like `vat_item_type`, `vat_time_range`, `filter_*`, `time_range`) were being lost during template save and incorrectly reconstructed as `None` during retrieval.

**Solution**:
1. Modified `templatize_cross_domain_sql()` to save `static_params` dict containing constant values (excluding dynamic params like `taxpayer_id`, `year`, `quarter`, `month`)
2. Updated both single-domain and cross-domain L2 cache retrieval to load `static_params` first, then rebuild dynamic params from entities

**Impact**: VAT concepts and financial_metrics concepts with filters now work correctly with L2 cache.

---

### Phase 6: Single-Domain Concept Cache Key Fix

**Files**:
- `D:\fintax_ai\api\routes\chat.py` (lines 468-478)
- `D:\fintax_ai\api\services\template_cache.py` (lines 301-310)

**Problem**: Single-domain concept queries were using `cache_domain = "cross_domain"` which defeated the domain-aware cache key strategy.

**Solution**:
1. In `chat.py`: Detect if all sub_templates have the same domain, use that domain as `effective_domain`
2. In `template_cache.py`: Check if `len(unique_domains) == 1` and `domain != 'cross_domain'`, preserve the actual domain for cache key

**Impact**: Single-domain concept queries now use domain-aware cache keys (e.g., financial_statement by accounting_standard, VAT by taxpayer_type).

---

## L2 Cache Template Accumulation Strategy

**No changes needed** - existing logic already supports accumulation:

**Financial Statements** (balance_sheet, profit, cash_flow, account_balance):
- Cache key: `MD5(query|mode|financial_statement|accounting_standard)`
- 2 templates per query: 企业会计准则, 小企业会计准则

**VAT**:
- Cache key: `MD5(query|mode|vat|taxpayer_type)`
- 2 templates per query: 一般纳税人, 小规模纳税人

**EIT**:
- Cache key: `MD5(query|mode|eit)`
- 1 template per query (no distinction)

**Cross-Domain** (LLM only after Phase 1):
- Cache key: domain-aware (same as above)
- Up to 4 templates per query: 2 types × 2 standards

**Concept Pipeline** (single-domain only after Phase 1):
- Saves as `cache_domain='cross_domain'` with `pipeline_type='concept'`
- Uses same accumulation strategy as above

---

## Test Cases

### Test Case 1: Single-Domain Concept Query (Baseline)
**Query**: "华兴科技2025年各季度采购金额"

**Expected**:
- Routes to single-domain concept pipeline (lines 502-556)
- Returns quarterly purchase amounts
- Saves to L2 cache with `pipeline_type='concept'`
- Second query hits L2 cache

### Test Case 2: Multi-Domain Query (Changed Behavior)
**Query**: "华兴科技2025年各季度总资产、总负债和净利润情况"

**Expected**:
- **Before**: Routes to cross-domain concept pipeline → may have incomplete results
- **After**: Routes to LLM cross-domain pipeline → comprehensive results
- Saves to L2 cache with `pipeline_type=None`

### Test Case 3: L2 Cache Accumulation (Financial Statements)
**Query**: "华兴科技2025年各季度营业收入"

**Expected**:
- First query (企业会计准则): creates 1 template
- Second query (小企业会计准则): creates 2nd template
- Both queries can hit L2 cache after accumulation

### Test Case 4: L2 Cache Accumulation (VAT)
**Query**: "华兴科技2025年1月增值税"

**Expected**:
- First query (一般纳税人): creates 1 template
- Second query (小规模纳税人): creates 2nd template

### Test Case 5: Single-Domain Concept L2 Cache Params
**Query**: "华兴科技2025年各季度存货增加额"

**Expected**:
- First query: executes concept pipeline, saves to L2 with params
- Second query: hits L2 cache, correctly reconstructs params (year, quarter, time_range)

---

## Risk Assessment

### Medium Risk
1. **Single-domain concept queries may not save to L2 cache correctly**
   - Mitigation: Phase 3 moves concept save logic outside `if domain == "cross_domain"` block
   - Validation: Test single-domain concept queries

2. **Single-domain L2 cache retrieval may fail due to missing params**
   - Mitigation: Phase 2 adds param reconstruction logic
   - Validation: Test L2 cache hit for single-domain concept queries

### Low Risk
1. **Existing cross-domain concept queries may behave differently**
   - Impact: They will now route to LLM cross-domain pipeline instead
   - Expected: More comprehensive results
   - Validation: Test queries like "华兴科技2025年各季度总资产、总负债和净利润情况"

---

## Files Modified

1. **`D:\fintax_ai\mvp_pipeline.py`** (lines 557-576) - Removed cross-domain concept pipeline branch
2. **`D:\fintax_ai\api\routes\chat.py`** (lines 3, 244-278, 409-461) - Fixed L2 cache retrieval params and save logic

---

## Verification

Run the following test queries to verify the changes:

```bash
# Test 1: Single-domain concept query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "华兴科技2025年各季度采购金额", "company_id": "91310115MA2KZZZZZZ", "thinking_mode": "quick", "response_mode": "detailed"}'

# Test 2: Multi-domain query (should use LLM cross-domain pipeline)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "华兴科技2025年各季度总资产、总负债和净利润情况", "company_id": "91310115MA2KZZZZZZ", "thinking_mode": "quick", "response_mode": "detailed"}'

# Test 3: Repeat Test 1 (should hit L2 cache)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "创智软件2025年各季度采购金额", "company_id": "91330200MA2KXXXXXX", "thinking_mode": "quick", "response_mode": "detailed"}'
```

Check logs for:
- `[3b2] 单概念时序管线` (single-domain concept pipeline)
- `[3c] 进入跨域查询管线` (LLM cross-domain pipeline)
- `[L2 Cache] Saved concept pipeline` (L2 cache save)
- `[L2 Cache] Hit` (L2 cache hit)
- `[L2 Cache] Concept pipeline single-domain params` (param reconstruction)

---

## Next Steps

1. Run regression tests on existing test suite
2. Monitor production logs for any unexpected behavior
3. Update CLAUDE.md and MEMORY.md with new routing strategy
4. Consider adding automated tests for the 5 test cases above
