-- ============================================================================
-- Fintax AI Database Fix and Supplement Script
-- Purpose:
--   1. Delete future data (2026-04 onwards) for existing taxpayers
--   2. Add 2 new taxpayers to cover missing type combinations
--   3. Generate sample data for new taxpayers (2023-01 to 2026-03)
-- Date: 2026-03-08
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Delete future data (2026-04 onwards) for all existing taxpayers
-- ============================================================================

-- Delete from VAT tables
DELETE FROM vat_return_general
WHERE period_year = 2026 AND period_month >= 4;

DELETE FROM vat_return_small
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from EIT tables (keep 2023-2025 full years, 2026 Q1 only)
-- All EIT tables use filing_id as primary key, linked to filing tables
-- Delete child tables first, then parent filing tables

-- Annual EIT: delete all 2026+ data
DELETE FROM eit_annual_basic_info
WHERE filing_id IN (
    SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025
);

DELETE FROM eit_annual_shareholder
WHERE filing_id IN (
    SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025
);

DELETE FROM eit_annual_main
WHERE filing_id IN (
    SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025
);

DELETE FROM eit_annual_incentive_items
WHERE filing_id IN (
    SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025
);

DELETE FROM eit_annual_filing
WHERE period_year > 2025;

-- Quarterly EIT: delete 2026 Q2+ data
DELETE FROM eit_quarter_main
WHERE filing_id IN (
    SELECT filing_id FROM eit_quarter_filing
    WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1)
);

DELETE FROM eit_quarter_incentive_items
WHERE filing_id IN (
    SELECT filing_id FROM eit_quarter_filing
    WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1)
);

DELETE FROM eit_quarter_filing
WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1);

-- Delete from account balance
DELETE FROM account_balance
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from invoice tables
DELETE FROM inv_spec_purchase
WHERE period_year = 2026 AND period_month >= 4;

DELETE FROM inv_spec_sales
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from financial statement tables
DELETE FROM fs_balance_sheet_item
WHERE period_year = 2026 AND period_month >= 4;

DELETE FROM fs_income_statement_item
WHERE period_year = 2026 AND period_month >= 4;

DELETE FROM fs_cash_flow_item
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from financial metrics
DELETE FROM financial_metrics_item
WHERE period_year = 2026 AND period_month >= 4;

DELETE FROM financial_metrics
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from profile snapshots
DELETE FROM taxpayer_profile_snapshot_month
WHERE period_year = 2026 AND period_month >= 4;

-- Delete from credit grades
DELETE FROM taxpayer_credit_grade_year
WHERE year > 2025;

-- Delete from HR tables
DELETE FROM hr_employee_salary
WHERE salary_month >= '2026-04';


-- ============================================================================
-- STEP 2: Add 2 new taxpayers
-- ============================================================================

-- Taxpayer 1: 企业会计准则 + 小规模纳税人
-- 博雅文化传媒有限公司 (文化传媒行业，小规模纳税人，使用企业会计准则)
INSERT INTO taxpayer_info (
  taxpayer_id, taxpayer_name, taxpayer_type, accounting_standard,
  legal_representative, registered_capital,
  registered_address, business_scope, operating_status, collection_method,
  industry_code, tax_authority_code, region_code, establish_date
) VALUES (
  '91110108MA01AAAAA1',
  '博雅文化传媒有限公司',
  '小规模纳税人',
  '企业会计准则',
  '李明',
  5000000.00,
  '北京市海淀区中关村大街1号',
  '文化艺术交流活动策划；广告设计、制作、代理、发布；影视策划；企业形象策划；会议服务；展览展示服务',
  '在营',
  '查账征收',
  'R87',
  '11010800000',
  '110108',
  '2020-03-15'
);

-- Taxpayer 2: 小企业会计准则 + 一般纳税人
-- 恒泰建材有限公司 (建材批发行业，一般纳税人，使用小企业会计准则)
INSERT INTO taxpayer_info (
  taxpayer_id, taxpayer_name, taxpayer_type, accounting_standard,
  legal_representative, registered_capital,
  registered_address, business_scope, operating_status, collection_method,
  industry_code, tax_authority_code, region_code, establish_date
) VALUES (
  '91320200MA02BBBBB2',
  '恒泰建材有限公司',
  '一般纳税人',
  '小企业会计准则',
  '张伟',
  10000000.00,
  '江苏省无锡市滨湖区太湖大道100号',
  '建筑材料、装饰材料、五金交电、机电设备批发零售；建筑工程施工；室内外装饰装修工程设计施工',
  '在营',
  '查账征收',
  'F51',
  '32020000000',
  '320200',
  '2018-06-20'
);

-- Note: User access grants can be added manually via the admin UI
-- or by running: INSERT INTO user_company_access (user_id, taxpayer_id)
-- SELECT id, '91110108MA01AAAAA1' FROM users WHERE role IN ('sys', 'admin');

COMMIT;
