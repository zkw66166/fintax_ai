-- ============================================================================
-- 为新增的2家公司复制示例数据
-- 策略：从相似类型的现有公司复制数据结构，修改taxpayer_id和金额
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- 公司1: 博雅文化传媒有限公司 (91110108MA01AAAAA1)
-- 类型: 企业会计准则 + 小规模纳税人
-- 复制来源: 鑫源贸易商行 (92440300MA5EQXL17P) - 同为小规模纳税人
-- 数据调整: 金额 × 0.8 (模拟不同规模)
-- ============================================================================

-- 1. VAT数据 (小规模纳税人)
INSERT INTO vat_return_small (
    taxpayer_id, period_year, period_month, item_type, time_range, revision_no,
    submitted_at, sales_3percent, sales_3percent_invoice_spec, sales_3percent_invoice_other,
    tax_due_current, tax_due_total, tax_prepaid, tax_supplement_refund
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month, item_type, time_range, revision_no,
    submitted_at,
    ROUND(sales_3percent * 0.8, 2),
    ROUND(sales_3percent_invoice_spec * 0.8, 2),
    ROUND(sales_3percent_invoice_other * 0.8, 2),
    ROUND(tax_due_current * 0.8, 2),
    ROUND(tax_due_total * 0.8, 2),
    ROUND(tax_prepaid * 0.8, 2),
    ROUND(tax_supplement_refund * 0.8, 2)
FROM vat_return_small
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 2. 资产负债表 (企业会计准则 ASBE)
INSERT INTO fs_balance_sheet_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    ending_balance, beginning_balance, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month,
    'ASBE' as gaap_type,  -- 改为企业会计准则
    item_code, item_name,
    ROUND(ending_balance * 0.8, 2),
    ROUND(beginning_balance * 0.8, 2),
    revision_no, submitted_at
FROM fs_balance_sheet_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 3. 利润表 (企业会计准则 CAS)
INSERT INTO fs_income_statement_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    current_amount, cumulative_amount, time_range, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month,
    'CAS' as gaap_type,  -- 改为企业会计准则
    item_code, item_name,
    ROUND(current_amount * 0.8, 2),
    ROUND(cumulative_amount * 0.8, 2),
    time_range, revision_no, submitted_at
FROM fs_income_statement_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 4. 现金流量表 (企业会计准则 CAS)
INSERT INTO fs_cash_flow_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    amount, time_range, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month,
    'CAS' as gaap_type,  -- 改为企业会计准则
    item_code, item_name,
    ROUND(amount * 0.8, 2),
    time_range, revision_no, submitted_at
FROM fs_cash_flow_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 5. 科目余额
INSERT INTO account_balance (
    taxpayer_id, period_year, period_month, account_code, account_name, account_category,
    beginning_debit, beginning_credit, period_debit, period_credit,
    ending_debit, ending_credit, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month, account_code, account_name, account_category,
    ROUND(beginning_debit * 0.8, 2),
    ROUND(beginning_credit * 0.8, 2),
    ROUND(period_debit * 0.8, 2),
    ROUND(period_credit * 0.8, 2),
    ROUND(ending_debit * 0.8, 2),
    ROUND(ending_credit * 0.8, 2),
    revision_no, submitted_at
FROM account_balance
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 6. 发票数据 (进项)
INSERT INTO inv_spec_purchase (
    taxpayer_id, period_year, period_month, invoice_code, invoice_number, invoice_date,
    seller_name, seller_tax_id, invoice_amount, tax_amount, total_amount,
    invoice_type, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month,
    invoice_code || '_BY',  -- 修改发票号避免重复
    invoice_number || '01',
    invoice_date,
    seller_name, seller_tax_id,
    ROUND(invoice_amount * 0.8, 2),
    ROUND(tax_amount * 0.8, 2),
    ROUND(total_amount * 0.8, 2),
    invoice_type, revision_no, submitted_at
FROM inv_spec_purchase
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603
LIMIT 100;  -- 限制发票数量

-- 7. 发票数据 (销项)
INSERT INTO inv_spec_sales (
    taxpayer_id, period_year, period_month, invoice_code, invoice_number, invoice_date,
    buyer_name, buyer_tax_id, invoice_amount, tax_amount, total_amount,
    invoice_type, revision_no, submitted_at
)
SELECT
    '91110108MA01AAAAA1' as taxpayer_id,
    period_year, period_month,
    invoice_code || '_BY',
    invoice_number || '01',
    invoice_date,
    buyer_name, buyer_tax_id,
    ROUND(invoice_amount * 0.8, 2),
    ROUND(tax_amount * 0.8, 2),
    ROUND(total_amount * 0.8, 2),
    invoice_type, revision_no, submitted_at
FROM inv_spec_sales
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603
LIMIT 100;


-- ============================================================================
-- 公司2: 恒泰建材有限公司 (91320200MA02BBBBB2)
-- 类型: 小企业会计准则 + 一般纳税人
-- 复制来源: TSE科技 (91310115MA2KZZZZZZ) 的VAT数据 + 环球机械的财务报表
-- 数据调整: 金额 × 1.2 (模拟中等规模)
-- ============================================================================

-- 1. VAT数据 (一般纳税人) - 从TSE科技复制
INSERT INTO vat_return_general
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month, item_type, time_range, revision_no,
    submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
    ROUND(COALESCE(sales_goods_13, 0) * 1.2, 2),
    ROUND(COALESCE(sales_goods_9, 0) * 1.2, 2),
    ROUND(COALESCE(sales_goods_6, 0) * 1.2, 2),
    ROUND(COALESCE(sales_goods_0, 0) * 1.2, 2),
    ROUND(COALESCE(sales_services_13, 0) * 1.2, 2),
    ROUND(COALESCE(sales_services_9, 0) * 1.2, 2),
    ROUND(COALESCE(sales_services_6, 0) * 1.2, 2),
    ROUND(COALESCE(sales_services_0, 0) * 1.2, 2),
    ROUND(COALESCE(sales_tax_free, 0) * 1.2, 2),
    ROUND(COALESCE(sales_export, 0) * 1.2, 2),
    ROUND(COALESCE(output_tax_13, 0) * 1.2, 2),
    ROUND(COALESCE(output_tax_9, 0) * 1.2, 2),
    ROUND(COALESCE(output_tax_6, 0) * 1.2, 2),
    ROUND(COALESCE(output_tax_total, 0) * 1.2, 2),
    ROUND(COALESCE(input_tax_total, 0) * 1.2, 2),
    ROUND(COALESCE(input_tax_domestic, 0) * 1.2, 2),
    ROUND(COALESCE(input_tax_import, 0) * 1.2, 2),
    ROUND(COALESCE(tax_payable, 0) * 1.2, 2),
    ROUND(COALESCE(tax_paid, 0) * 1.2, 2),
    ROUND(COALESCE(tax_refund, 0) * 1.2, 2)
FROM vat_return_general
WHERE taxpayer_id = '91310115MA2KZZZZZZ'
  AND period_year * 100 + period_month <= 202603;

-- 2. 资产负债表 (小企业会计准则 ASSE) - 从环球机械复制
INSERT INTO fs_balance_sheet_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    ending_balance, beginning_balance, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month, gaap_type, item_code, item_name,
    ROUND(ending_balance * 1.2, 2),
    ROUND(beginning_balance * 1.2, 2),
    revision_no, submitted_at
FROM fs_balance_sheet_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

-- 3. 利润表 (小企业会计准则 SAS) - 从环球机械复制
INSERT INTO fs_income_statement_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    current_amount, cumulative_amount, time_range, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month, gaap_type, item_code, item_name,
    ROUND(current_amount * 1.2, 2),
    ROUND(cumulative_amount * 1.2, 2),
    time_range, revision_no, submitted_at
FROM fs_income_statement_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

-- 4. 现金流量表 (小企业会计准则 SAS) - 从环球机械复制
INSERT INTO fs_cash_flow_item (
    taxpayer_id, period_year, period_month, gaap_type, item_code, item_name,
    amount, time_range, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month, gaap_type, item_code, item_name,
    ROUND(amount * 1.2, 2),
    time_range, revision_no, submitted_at
FROM fs_cash_flow_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

-- 5. 科目余额 - 从环球机械复制
INSERT INTO account_balance (
    taxpayer_id, period_year, period_month, account_code, account_name, account_category,
    beginning_debit, beginning_credit, period_debit, period_credit,
    ending_debit, ending_credit, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month, account_code, account_name, account_category,
    ROUND(beginning_debit * 1.2, 2),
    ROUND(beginning_credit * 1.2, 2),
    ROUND(period_debit * 1.2, 2),
    ROUND(period_credit * 1.2, 2),
    ROUND(ending_debit * 1.2, 2),
    ROUND(ending_credit * 1.2, 2),
    revision_no, submitted_at
FROM account_balance
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

-- 6. 发票数据 (进项) - 从TSE科技复制
INSERT INTO inv_spec_purchase (
    taxpayer_id, period_year, period_month, invoice_code, invoice_number, invoice_date,
    seller_name, seller_tax_id, invoice_amount, tax_amount, total_amount,
    invoice_type, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month,
    invoice_code || '_HT',
    invoice_number || '02',
    invoice_date,
    seller_name, seller_tax_id,
    ROUND(invoice_amount * 1.2, 2),
    ROUND(tax_amount * 1.2, 2),
    ROUND(total_amount * 1.2, 2),
    invoice_type, revision_no, submitted_at
FROM inv_spec_purchase
WHERE taxpayer_id = '91310115MA2KZZZZZZ'
  AND period_year * 100 + period_month <= 202603
LIMIT 100;

-- 7. 发票数据 (销项) - 从TSE科技复制
INSERT INTO inv_spec_sales (
    taxpayer_id, period_year, period_month, invoice_code, invoice_number, invoice_date,
    buyer_name, buyer_tax_id, invoice_amount, tax_amount, total_amount,
    invoice_type, revision_no, submitted_at
)
SELECT
    '91320200MA02BBBBB2' as taxpayer_id,
    period_year, period_month,
    invoice_code || '_HT',
    invoice_number || '02',
    invoice_date,
    buyer_name, buyer_tax_id,
    ROUND(invoice_amount * 1.2, 2),
    ROUND(tax_amount * 1.2, 2),
    ROUND(total_amount * 1.2, 2),
    invoice_type, revision_no, submitted_at
FROM inv_spec_sales
WHERE taxpayer_id = '91310115MA2KZZZZZZ'
  AND period_year * 100 + period_month <= 202603
LIMIT 100;

COMMIT;

-- ============================================================================
-- 验证数据
-- ============================================================================
SELECT '博雅文化传媒 - VAT数据' as check_item, COUNT(*) as count
FROM vat_return_small WHERE taxpayer_id = '91110108MA01AAAAA1'
UNION ALL
SELECT '博雅文化传媒 - 资产负债表', COUNT(*)
FROM fs_balance_sheet_item WHERE taxpayer_id = '91110108MA01AAAAA1'
UNION ALL
SELECT '恒泰建材 - VAT数据', COUNT(*)
FROM vat_return_general WHERE taxpayer_id = '91320200MA02BBBBB2'
UNION ALL
SELECT '恒泰建材 - 资产负债表', COUNT(*)
FROM fs_balance_sheet_item WHERE taxpayer_id = '91320200MA02BBBBB2';
