-- 简化版数据复制脚本
BEGIN TRANSACTION;

-- 公司1: 博雅文化传媒 (从鑫源贸易复制，金额×0.8)
INSERT INTO vat_return_small
SELECT '91110108MA01AAAAA1', period_year, period_month, item_type, time_range, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(sales_3percent, 0) * 0.8, 2),
       ROUND(COALESCE(sales_3percent_invoice_spec, 0) * 0.8, 2),
       ROUND(COALESCE(sales_3percent_invoice_other, 0) * 0.8, 2),
       ROUND(COALESCE(sales_5percent, 0) * 0.8, 2),
       ROUND(COALESCE(sales_5percent_invoice_spec, 0) * 0.8, 2),
       ROUND(COALESCE(sales_5percent_invoice_other, 0) * 0.8, 2),
       ROUND(COALESCE(sales_used_assets, 0) * 0.8, 2),
       ROUND(COALESCE(sales_used_assets_invoice_other, 0) * 0.8, 2),
       ROUND(COALESCE(sales_tax_free, 0) * 0.8, 2),
       ROUND(COALESCE(sales_tax_free_micro, 0) * 0.8, 2),
       ROUND(COALESCE(sales_tax_free_threshold, 0) * 0.8, 2),
       ROUND(COALESCE(sales_tax_free_other, 0) * 0.8, 2),
       ROUND(COALESCE(sales_export_tax_free, 0) * 0.8, 2),
       ROUND(COALESCE(sales_export_tax_free_invoice_other, 0) * 0.8, 2),
       ROUND(COALESCE(tax_due_current, 0) * 0.8, 2),
       ROUND(COALESCE(tax_due_reduction, 0) * 0.8, 2),
       ROUND(COALESCE(tax_free_amount, 0) * 0.8, 2),
       ROUND(COALESCE(tax_free_micro, 0) * 0.8, 2),
       ROUND(COALESCE(tax_free_threshold, 0) * 0.8, 2),
       ROUND(COALESCE(tax_due_total, 0) * 0.8, 2),
       ROUND(COALESCE(tax_prepaid, 0) * 0.8, 2),
       ROUND(COALESCE(tax_supplement_refund, 0) * 0.8, 2),
       ROUND(COALESCE(city_maintenance_tax, 0) * 0.8, 2),
       ROUND(COALESCE(education_surcharge, 0) * 0.8, 2),
       ROUND(COALESCE(local_education_surcharge, 0) * 0.8, 2)
FROM vat_return_small
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO fs_balance_sheet_item
SELECT '91110108MA01AAAAA1', period_year, period_month, 'ASBE', item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(ending_balance, 0) * 0.8, 2),
       ROUND(COALESCE(beginning_balance, 0) * 0.8, 2),
       item_name, line_number
FROM fs_balance_sheet_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO fs_income_statement_item
SELECT '91110108MA01AAAAA1', period_year, period_month, 'CAS', item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(current_amount, 0) * 0.8, 2),
       ROUND(COALESCE(cumulative_amount, 0) * 0.8, 2),
       item_name, line_number
FROM fs_income_statement_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO fs_cash_flow_item
SELECT '91110108MA01AAAAA1', period_year, period_month, 'CAS', item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(amount, 0) * 0.8, 2),
       item_name, line_number
FROM fs_cash_flow_item
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO account_balance
SELECT '91110108MA01AAAAA1', period_year, period_month, account_code, account_name, account_category,
       ROUND(COALESCE(beginning_debit, 0) * 0.8, 2),
       ROUND(COALESCE(beginning_credit, 0) * 0.8, 2),
       ROUND(COALESCE(period_debit, 0) * 0.8, 2),
       ROUND(COALESCE(period_credit, 0) * 0.8, 2),
       ROUND(COALESCE(ending_debit, 0) * 0.8, 2),
       ROUND(COALESCE(ending_credit, 0) * 0.8, 2),
       revision_no, submitted_at
FROM account_balance
WHERE taxpayer_id = '92440300MA5EQXL17P'
  AND period_year * 100 + period_month <= 202603;

-- 公司2: 恒泰建材 (VAT从TSE科技，财务报表从环球机械，金额×1.2)
INSERT INTO vat_return_general
SELECT '91320200MA02BBBBB2', period_year, period_month, item_type, time_range, revision_no,
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

INSERT INTO fs_balance_sheet_item
SELECT '91320200MA02BBBBB2', period_year, period_month, gaap_type, item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(ending_balance, 0) * 1.2, 2),
       ROUND(COALESCE(beginning_balance, 0) * 1.2, 2),
       item_name, line_number
FROM fs_balance_sheet_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO fs_income_statement_item
SELECT '91320200MA02BBBBB2', period_year, period_month, gaap_type, item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(current_amount, 0) * 1.2, 2),
       ROUND(COALESCE(cumulative_amount, 0) * 1.2, 2),
       item_name, line_number
FROM fs_income_statement_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO fs_cash_flow_item
SELECT '91320200MA02BBBBB2', period_year, period_month, gaap_type, item_code, revision_no,
       submitted_at, etl_batch_id, source_doc_id, source_unit, etl_confidence,
       ROUND(COALESCE(amount, 0) * 1.2, 2),
       item_name, line_number
FROM fs_cash_flow_item
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

INSERT INTO account_balance
SELECT '91320200MA02BBBBB2', period_year, period_month, account_code, account_name, account_category,
       ROUND(COALESCE(beginning_debit, 0) * 1.2, 2),
       ROUND(COALESCE(beginning_credit, 0) * 1.2, 2),
       ROUND(COALESCE(period_debit, 0) * 1.2, 2),
       ROUND(COALESCE(period_credit, 0) * 1.2, 2),
       ROUND(COALESCE(ending_debit, 0) * 1.2, 2),
       ROUND(COALESCE(ending_credit, 0) * 1.2, 2),
       revision_no, submitted_at
FROM account_balance
WHERE taxpayer_id = '91330100MA2KWWWWWW'
  AND period_year * 100 + period_month <= 202603;

COMMIT;
