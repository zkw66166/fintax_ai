"""Test SQL statements one by one to find the problematic one"""
import sqlite3

DB_PATH = "database/fintax_ai.db"

sql_statements = [
    ("VAT general", "DELETE FROM vat_return_general WHERE period_year = 2026 AND period_month >= 4"),
    ("VAT small", "DELETE FROM vat_return_small WHERE period_year = 2026 AND period_month >= 4"),
    ("EIT annual basic info", "DELETE FROM eit_annual_basic_info WHERE filing_id IN (SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025)"),
    ("EIT annual shareholder", "DELETE FROM eit_annual_shareholder WHERE filing_id IN (SELECT filing_id FROM eit_annual_filing WHERE period_year > 2025)"),
    ("EIT annual main", "DELETE FROM eit_annual_main WHERE period_year > 2025"),
    ("EIT annual incentive", "DELETE FROM eit_annual_incentive_items WHERE period_year > 2025"),
    ("EIT annual filing", "DELETE FROM eit_annual_filing WHERE period_year > 2025"),
    ("EIT quarter filing", "DELETE FROM eit_quarter_filing WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1)"),
    ("EIT quarter main", "DELETE FROM eit_quarter_main WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1)"),
    ("EIT quarter incentive", "DELETE FROM eit_quarter_incentive_items WHERE period_year > 2026 OR (period_year = 2026 AND period_quarter > 1)"),
    ("Account balance", "DELETE FROM account_balance WHERE period_year = 2026 AND period_month >= 4"),
    ("Invoice purchase", "DELETE FROM inv_spec_purchase WHERE period_year = 2026 AND period_month >= 4"),
    ("Invoice sales", "DELETE FROM inv_spec_sales WHERE period_year = 2026 AND period_month >= 4"),
    ("Balance sheet", "DELETE FROM fs_balance_sheet_item WHERE period_year = 2026 AND period_month >= 4"),
    ("Income statement", "DELETE FROM fs_income_statement_item WHERE period_year = 2026 AND period_month >= 4"),
    ("Cash flow", "DELETE FROM fs_cash_flow_item WHERE period_year = 2026 AND period_month >= 4"),
    ("Financial metrics item", "DELETE FROM financial_metrics_item WHERE period_year = 2026 AND period_month >= 4"),
    ("Financial metrics", "DELETE FROM financial_metrics WHERE period_year = 2026 AND period_month >= 4"),
    ("Profile snapshot", "DELETE FROM taxpayer_profile_snapshot_month WHERE period_year = 2026 AND period_month >= 4"),
    ("Credit grade", "DELETE FROM taxpayer_credit_grade_year WHERE period_year > 2025"),
    ("HR salary", "DELETE FROM hr_employee_salary WHERE salary_month >= '2026-04'"),
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for name, sql in sql_statements:
    try:
        print(f"Testing: {name}... ", end="")
        cursor.execute(sql)
        print(f"✓ OK")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        break

conn.close()
