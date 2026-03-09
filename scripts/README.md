# Database Fix and Supplement Scripts

## Overview

This directory contains scripts to fix and supplement the fintax_ai.db database:

1. **Delete future data** (2026-04 onwards) - current month is 2026-03
2. **Add 2 new taxpayers** to cover missing type combinations
3. **Generate sample data** for new taxpayers (2023-01 to 2026-03)
4. **Update financial metrics** for new taxpayers
5. **Validate data quality** using existing data quality checker

## New Taxpayers

### 1. 博雅文化传媒有限公司
- **Taxpayer ID**: 91110108MA01AAAAA1
- **Type**: 小规模纳税人 (Small-scale taxpayer)
- **Accounting Standard**: 企业会计准则 (ASBE)
- **Industry**: 文化传媒 (Culture & Media)
- **Combination**: 企业会计准则 + 小规模纳税人 ✓ (Previously missing)

### 2. 恒泰建材有限公司
- **Taxpayer ID**: 91320200MA02BBBBB2
- **Type**: 一般纳税人 (General taxpayer)
- **Accounting Standard**: 小企业会计准则 (ASSE)
- **Industry**: 建材批发 (Building materials wholesale)
- **Combination**: 小企业会计准则 + 一般纳税人 ✓ (Previously missing)

## Complete Coverage Matrix

After adding these 2 taxpayers, all 4 combinations are covered:

| Accounting Standard | Taxpayer Type | Companies |
|---------------------|---------------|-----------|
| 企业会计准则 (ASBE) | 一般纳税人 | 华兴科技, TSE科技, 创智软件 |
| 企业会计准则 (ASBE) | 小规模纳税人 | **博雅文化传媒** ✓ NEW |
| 小企业会计准则 (ASSE) | 一般纳税人 | **恒泰建材** ✓ NEW |
| 小企业会计准则 (ASSE) | 小规模纳税人 | 鑫源贸易, 环球机械, 大华智能制造 |

## Scripts

### 1. `master_fix_database.py` (MAIN SCRIPT)

**Purpose**: Master orchestration script that executes all steps in order.

**Usage**:
```bash
cd D:\fintax_ai
python scripts/master_fix_database.py
```

**What it does**:
1. Creates database backup (timestamped)
2. Executes SQL script to delete future data and add taxpayers
3. Verifies new taxpayers were added
4. Verifies no future data remains
5. Generates sample data for new taxpayers
6. Updates financial metrics
7. Validates data quality
8. Prints execution summary

**Safety**: Creates automatic backup before any modifications.

### 2. `fix_and_supplement_data.sql`

**Purpose**: SQL script to delete future data and add new taxpayers.

**What it does**:
- Deletes all data with period >= 2026-04 from all tables
- Inserts 2 new taxpayer records into `taxpayer_info`
- Grants access to admin users via `user_company_access`

**Tables affected**:
- vat_return_general, vat_return_small
- eit_annual_*, eit_quarter_*
- account_balance
- inv_spec_purchase, inv_spec_sales
- fs_balance_sheet_item, fs_income_statement_item, fs_cash_flow_item
- financial_metrics, financial_metrics_item
- taxpayer_profile_snapshot_month
- taxpayer_credit_grade_year
- hr_employee_salary

### 3. `generate_sample_data.py`

**Purpose**: Generate realistic sample data for new taxpayers.

**Data generated**:
- **VAT returns** (39 months: 2023-01 to 2026-03)
- **Balance sheets** (39 months, ASBE/ASSE format)
- **Income statements** (39 months, CAS/SAS format)
- **Cash flow statements** (39 months, CAS/SAS format)
- **EIT annual** (3 years: 2023, 2024, 2025)
- **EIT quarterly** (13 quarters: 2023Q1-2025Q4, 2026Q1)
- **Invoices** (purchase + sales, 5-10 per month)
- **Account balances** (10 key accounts, 39 months)

**Data characteristics**:
- Realistic revenue patterns with seasonal variation
- Consistent growth rates (15% for media, 12% for building materials)
- Industry-appropriate margins (45% for media, 18% for building materials)
- Proper VAT rates (1% for small-scale, 13% for general)
- Internally consistent (BS equation, P&L formulas, cash flow reconciliation)

### 4. `update_metrics_and_validate.py`

**Purpose**: Calculate financial metrics and validate data quality.

**What it does**:
1. Calculates 7 key financial metrics for all periods:
   - Asset-liability ratio
   - Current ratio
   - Quick ratio
   - Gross margin
   - Net margin
   - ROE (Return on Equity)
   - ROA (Return on Assets)
2. Inserts metrics into `financial_metrics` and `financial_metrics_item` tables
3. Runs comprehensive data quality checks using `DataQualityChecker`
4. Reports pass rates and failed checks

**Validation categories**:
- Internal consistency (BS equation, P&L formulas, etc.)
- Reasonableness (threshold checks)
- Cross-table consistency
- Period continuity
- Completeness

## Execution Steps

### Quick Start (Recommended)

```bash
cd D:\fintax_ai
python scripts/master_fix_database.py
```

This will execute all steps automatically with safety checks.

### Manual Execution (Advanced)

If you need to run steps individually:

```bash
# Step 1: Delete future data and add taxpayers
sqlite3 database/fintax_ai.db < scripts/fix_and_supplement_data.sql

# Step 2: Generate sample data
python scripts/generate_sample_data.py

# Step 3: Update metrics and validate
python scripts/update_metrics_and_validate.py
```

## Verification

After execution, verify the changes:

```sql
-- Check taxpayer count (should be 8)
SELECT COUNT(*) FROM taxpayer_info;

-- Check new taxpayers
SELECT taxpayer_id, taxpayer_name, taxpayer_type, accounting_standard
FROM taxpayer_info
WHERE taxpayer_id IN ('91110108MA01AAAAA1', '91320200MA02BBBBB2');

-- Check data periods (max should be 202603)
SELECT taxpayer_id, MAX(period_year * 100 + period_month) as max_period
FROM vat_return_general
GROUP BY taxpayer_id;

-- Check sample data count for new taxpayers
SELECT
  taxpayer_id,
  COUNT(*) as record_count
FROM fs_balance_sheet_item
WHERE taxpayer_id IN ('91110108MA01AAAAA1', '91320200MA02BBBBB2')
GROUP BY taxpayer_id;
```

## Rollback

If you need to rollback changes, restore from the automatic backup:

```bash
# Backup is created with timestamp: fintax_ai_backup_YYYYMMDD_HHMMSS.db
cp database/fintax_ai_backup_20260308_143000.db database/fintax_ai.db
```

## Data Quality Rules

The generated data follows these rules:

### Internal Consistency
- Balance sheet: Assets = Liabilities + Equity
- Income statement: Operating profit = Gross profit - Expenses
- Cash flow: Net increase = Operating + Investing + Financing
- VAT: Payable tax = Output tax - Input tax (general taxpayer)
- EIT: Tax = Taxable income × Tax rate

### Reasonableness
- All amounts are positive (except losses)
- Ratios are within reasonable ranges
- Growth rates are consistent
- Seasonal patterns are realistic

### Cross-Table Consistency
- Revenue matches across income statement and VAT return
- Net profit matches across income statement and balance sheet (retained earnings)
- Cash flow reconciles with balance sheet cash changes

### Period Continuity
- No gaps in monthly data (2023-01 to 2026-03)
- Ending balance of month N = Beginning balance of month N+1

### Completeness
- All required fields are populated
- No NULL values in critical fields
- All key financial statement items are present

## Notes

1. **Current month**: The system assumes current month is 2026-03, so all data after 2026-03 is considered "future data" and is deleted.

2. **Revision numbers**: All generated data uses `revision_no = 1` (original submission).

3. **Timestamps**: Generated data uses realistic submission timestamps (e.g., VAT on 15th, financial statements on 20th).

4. **Random variation**: Revenue and other amounts include random seasonal variation (±15%) to simulate real-world patterns.

5. **Industry characteristics**: Each taxpayer has industry-appropriate financial characteristics (margins, growth rates, etc.).

## Troubleshooting

### Error: "database is locked"
- Close any SQLite browser or other connections to the database
- Wait a few seconds and retry

### Error: "no such table"
- Ensure you're running from the project root directory (`D:\fintax_ai`)
- Check that `database/fintax_ai.db` exists

### Error: "module not found"
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're using the correct Python environment

### Validation failures
- Review the failed checks in the output
- Most failures are informational and don't prevent system operation
- Critical failures (e.g., BS equation violations) should be investigated

## Contact

For questions or issues, refer to the main project documentation in `CLAUDE.md`.
