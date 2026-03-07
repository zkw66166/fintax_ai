# Test Query Execution Summary

**Date**: 2026-03-07
**Purpose**: Generate comprehensive query_history.json and cache files for TSE科技有限公司 and 大华智能制造厂

## Results

### Cache Files Generated
- **Total**: 114 cache files
  - **L1 Cache** (Full Results): 79 files
  - **L2 Cache** (SQL Templates): 37 files

### Query History
- **Total Entries**: 100 (max limit reached)
- History file: `query_history.json` (2.4 MB)

### Test Coverage

#### Companies Tested
1. **TSE科技有限公司** (91310115MA2KZZZZZZ)
   - 企业会计准则 (ASBE)
   - 一般纳税人 (General VAT Taxpayer)

2. **大华智能制造厂** (91330200MA2KYYYYYY)
   - 小企业会计准则 (ASSE)
   - 小规模纳税人 (Small-scale VAT Taxpayer)

#### Domains Covered
All 9 data domains were tested:
1. 科目余额表 (Account Balance)
2. 资产负债表 (Balance Sheet)
3. 利润表 (Profit Statement)
4. 现金流量表 (Cash Flow Statement)
5. 增值税申报表 (VAT Return)
6. 企业所得税申报表 (EIT Return)
7. 进项发票 (Purchase Invoices)
8. 销项发票 (Sales Invoices)
9. 关键财务指标 (Key Financial Metrics)

#### Query Types
- **Single-domain queries**: 27 per company (3 per domain)
  - Single indicator, single period
  - Single indicator, multiple periods
  - Multiple indicators, multiple periods

- **Cross-domain queries**: 15+ per company
  - Cross-domain single indicator, single period
  - Cross-domain single indicator, multiple periods
  - Cross-domain multiple indicators, multiple periods

### Cache Benefits

#### L1 Cache (Full Results)
- Stores complete pipeline results including:
  - SQL query and execution results
  - Display data (formatted tables, charts)
  - Interpretation text
  - Route information
- Enables instant response for repeated queries
- Company-aware (different cache per company)

#### L2 Cache (SQL Templates)
- Stores SQL templates with taxpayer_id placeholders
- Enables cross-company reuse:
  - Same query for different companies reuses template
  - Only instantiates taxpayer_id parameter
- Domain-aware cache keys:
  - Financial statements: keyed by accounting_standard
  - VAT: keyed by taxpayer_type
  - EIT: no type/standard distinction
- Smart adaptation for financial statements (ASBE ↔ ASSE)

### Files Generated

```
D:\fintax_ai\
├── cache/                          # 114 cache files
│   ├── *.json                      # 79 L1 cache files
│   └── template_*.json             # 37 L2 cache files
├── query_history.json              # 100 history entries (2.4 MB)
└── scripts/
    ├── quick_test.py               # 8-query quick test
    ├── batch_test.py               # 84-query batch test
    └── run_comprehensive_test.py   # 114-query full test
```

### Authentication Fix

Fixed user1 password hash issue:
- Regenerated bcrypt hash for password "123456"
- Granted user1 access to all 6 companies in database

### Test Scripts Created

1. **quick_test.py**: Fast 8-query test for verification
2. **batch_test.py**: 84-query test covering both companies
3. **run_comprehensive_test.py**: Full 114-query test suite

## Usage

To re-run tests:
```bash
# Quick test (8 queries)
python scripts/quick_test.py

# Batch test (84 queries)
python scripts/batch_test.py

# Comprehensive test (114 queries)
python scripts/run_comprehensive_test.py
```

## Notes

- Query history has a max limit of 100 entries
- Cache files persist across server restarts
- L2 cache enables significant performance improvements for cross-company queries
- Both companies tested with different accounting standards and taxpayer types to ensure comprehensive coverage
