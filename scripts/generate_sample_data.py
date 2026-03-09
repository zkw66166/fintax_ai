"""
Generate sample data for new taxpayers in fintax_ai.db
- 博雅文化传媒有限公司 (企业会计准则 + 小规模纳税人)
- 恒泰建材有限公司 (小企业会计准则 + 一般纳税人)

Data period: 2023-01 to 2026-03 (39 months)
"""

import sqlite3
import random
from datetime import datetime, timedelta
from decimal import Decimal

DB_PATH = "database/fintax_ai.db"

# Taxpayer configurations
TAXPAYERS = {
    "91110108MA01AAAAA1": {
        "name": "博雅文化传媒有限公司",
        "type": "小规模纳税人",
        "standard": "企业会计准则",
        "industry": "文化传媒",
        "base_revenue": 800000,  # 月均收入80万
        "growth_rate": 0.15,  # 年增长15%
        "gross_margin": 0.45,  # 毛利率45%
        "vat_rate": 0.01,  # 小规模1%
    },
    "91320200MA02BBBBB2": {
        "name": "恒泰建材有限公司",
        "type": "一般纳税人",
        "standard": "小企业会计准则",
        "industry": "建材批发",
        "base_revenue": 5000000,  # 月均收入500万
        "growth_rate": 0.12,  # 年增长12%
        "gross_margin": 0.18,  # 毛利率18%
        "vat_rate": 0.13,  # 一般纳税人13%
    }
}


def generate_periods():
    """Generate all periods from 2023-01 to 2026-03"""
    periods = []
    for year in range(2023, 2027):
        max_month = 3 if year == 2026 else 12
        for month in range(1, max_month + 1):
            periods.append((year, month))
    return periods


def calculate_revenue(base, year, month, growth_rate):
    """Calculate revenue with seasonal variation and growth"""
    # Years since 2023
    years_elapsed = year - 2023 + (month - 1) / 12

    # Apply growth
    revenue = base * (1 + growth_rate) ** years_elapsed

    # Seasonal variation (±15%)
    seasonal_factor = 1 + 0.15 * random.uniform(-1, 1)

    # Month-specific patterns
    if month in [1, 2]:  # Spring Festival impact
        seasonal_factor *= 0.85
    elif month in [6, 12]:  # Mid-year and year-end peaks
        seasonal_factor *= 1.15

    return round(revenue * seasonal_factor, 2)


def generate_vat_data(conn, taxpayer_id, config, periods):
    """Generate VAT return data"""
    cursor = conn.cursor()

    for year, month in periods:
        revenue = calculate_revenue(
            config["base_revenue"], year, month, config["growth_rate"]
        )

        if config["type"] == "小规模纳税人":
            # Small-scale taxpayer
            output_tax = round(revenue * config["vat_rate"], 2)

            cursor.execute("""
                INSERT INTO vat_return_small (
                    taxpayer_id, period_year, period_month, item_type,
                    sales_amount, tax_amount, revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month, "应税销售额",
                revenue, output_tax, 1,
                f"{year}-{month:02d}-15 10:00:00"
            ))
        else:
            # General taxpayer
            output_tax = round(revenue * config["vat_rate"], 2)
            input_tax = round(output_tax * 0.75, 2)  # 75% input credit
            payable_tax = output_tax - input_tax

            cursor.execute("""
                INSERT INTO vat_return_general (
                    taxpayer_id, period_year, period_month, item_type,
                    sales_amount, output_tax, input_tax, payable_tax,
                    revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month, "销项税额",
                revenue, output_tax, input_tax, payable_tax, 1,
                f"{year}-{month:02d}-15 10:00:00"
            ))

    conn.commit()
    print(f"✓ Generated VAT data for {config['name']}")


def generate_balance_sheet_data(conn, taxpayer_id, config, periods):
    """Generate balance sheet data"""
    cursor = conn.cursor()

    # Get GAAP type
    gaap_type = "ASBE" if config["standard"] == "企业会计准则" else "ASSE"

    # Initial balance sheet values (as of 2022-12)
    initial_assets = config["base_revenue"] * 12 * 1.5  # 1.5x annual revenue
    initial_equity = initial_assets * 0.6
    initial_liabilities = initial_assets - initial_equity

    for year, month in periods:
        # Calculate growth
        years_elapsed = year - 2023 + (month - 1) / 12
        growth_factor = (1 + config["growth_rate"]) ** years_elapsed

        # Assets
        total_assets = round(initial_assets * growth_factor, 2)
        current_assets = round(total_assets * 0.65, 2)
        non_current_assets = total_assets - current_assets

        # Liabilities
        total_liabilities = round(initial_liabilities * growth_factor * 1.1, 2)
        current_liabilities = round(total_liabilities * 0.70, 2)
        non_current_liabilities = total_liabilities - current_liabilities

        # Equity
        total_equity = total_assets - total_liabilities

        # Insert asset items
        items = [
            ("1", "流动资产合计", current_assets),
            ("101", "货币资金", round(current_assets * 0.25, 2)),
            ("102", "应收账款", round(current_assets * 0.35, 2)),
            ("103", "存货", round(current_assets * 0.30, 2)),
            ("2", "非流动资产合计", non_current_assets),
            ("201", "固定资产", round(non_current_assets * 0.70, 2)),
            ("202", "无形资产", round(non_current_assets * 0.20, 2)),
            ("100", "资产总计", total_assets),
            ("3", "流动负债合计", current_liabilities),
            ("301", "短期借款", round(current_liabilities * 0.30, 2)),
            ("302", "应付账款", round(current_liabilities * 0.40, 2)),
            ("4", "非流动负债合计", non_current_liabilities),
            ("401", "长期借款", round(non_current_liabilities * 0.80, 2)),
            ("300", "负债合计", total_liabilities),
            ("5", "所有者权益合计", total_equity),
            ("501", "实收资本", round(total_equity * 0.60, 2)),
            ("502", "未分配利润", round(total_equity * 0.30, 2)),
        ]

        for item_code, item_name, amount in items:
            cursor.execute("""
                INSERT INTO fs_balance_sheet_item (
                    taxpayer_id, period_year, period_month, gaap_type,
                    item_code, item_name, ending_balance, beginning_balance,
                    revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month, gaap_type,
                item_code, item_name, amount, amount * 0.95, 1,
                f"{year}-{month:02d}-20 14:00:00"
            ))

    conn.commit()
    print(f"✓ Generated balance sheet data for {config['name']}")


def generate_income_statement_data(conn, taxpayer_id, config, periods):
    """Generate income statement data"""
    cursor = conn.cursor()

    # Get GAAP type
    gaap_type = "CAS" if config["standard"] == "企业会计准则" else "SAS"

    for year, month in periods:
        revenue = calculate_revenue(
            config["base_revenue"], year, month, config["growth_rate"]
        )

        # Calculate P&L items
        operating_revenue = revenue
        operating_cost = round(revenue * (1 - config["gross_margin"]), 2)
        gross_profit = operating_revenue - operating_cost

        # Operating expenses (20% of revenue)
        selling_expense = round(revenue * 0.08, 2)
        admin_expense = round(revenue * 0.07, 2)
        finance_expense = round(revenue * 0.02, 2)
        total_expense = selling_expense + admin_expense + finance_expense

        # Operating profit
        operating_profit = gross_profit - total_expense

        # Income tax (25% for general, 20% for small-scale)
        tax_rate = 0.20 if config["type"] == "小规模纳税人" else 0.25
        income_tax = round(max(operating_profit, 0) * tax_rate, 2)

        # Net profit
        net_profit = operating_profit - income_tax

        # Cumulative amounts (for current year)
        month_in_year = month
        ytd_factor = month_in_year

        items = [
            ("1", "营业收入", revenue, revenue * ytd_factor),
            ("2", "营业成本", operating_cost, operating_cost * ytd_factor),
            ("3", "营业利润", operating_profit, operating_profit * ytd_factor),
            ("301", "销售费用", selling_expense, selling_expense * ytd_factor),
            ("302", "管理费用", admin_expense, admin_expense * ytd_factor),
            ("303", "财务费用", finance_expense, finance_expense * ytd_factor),
            ("4", "利润总额", operating_profit, operating_profit * ytd_factor),
            ("5", "所得税费用", income_tax, income_tax * ytd_factor),
            ("6", "净利润", net_profit, net_profit * ytd_factor),
        ]

        for item_code, item_name, current_amount, ytd_amount in items:
            cursor.execute("""
                INSERT INTO fs_income_statement_item (
                    taxpayer_id, period_year, period_month, gaap_type,
                    item_code, item_name, current_period_amount, ytd_amount,
                    time_range, revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month, gaap_type,
                item_code, item_name, current_amount, ytd_amount,
                "monthly", 1, f"{year}-{month:02d}-20 14:00:00"
            ))

    conn.commit()
    print(f"✓ Generated income statement data for {config['name']}")


def generate_cash_flow_data(conn, taxpayer_id, config, periods):
    """Generate cash flow statement data"""
    cursor = conn.cursor()

    # Get GAAP type
    gaap_type = "CAS" if config["standard"] == "企业会计准则" else "SAS"

    for year, month in periods:
        revenue = calculate_revenue(
            config["base_revenue"], year, month, config["growth_rate"]
        )

        # Operating cash flow (90% of revenue)
        operating_inflow = round(revenue * 0.90, 2)
        operating_outflow = round(revenue * 0.75, 2)
        operating_net = operating_inflow - operating_outflow

        # Investing cash flow (negative, capex)
        investing_outflow = round(revenue * 0.05, 2)
        investing_net = -investing_outflow

        # Financing cash flow
        financing_inflow = round(revenue * 0.02, 2) if month % 6 == 0 else 0
        financing_outflow = round(revenue * 0.01, 2)
        financing_net = financing_inflow - financing_outflow

        # Net increase
        net_increase = operating_net + investing_net + financing_net

        items = [
            ("1", "经营活动现金流入小计", operating_inflow),
            ("101", "销售商品、提供劳务收到的现金", operating_inflow),
            ("2", "经营活动现金流出小计", operating_outflow),
            ("201", "购买商品、接受劳务支付的现金", round(operating_outflow * 0.70, 2)),
            ("202", "支付给职工以及为职工支付的现金", round(operating_outflow * 0.20, 2)),
            ("100", "经营活动产生的现金流量净额", operating_net),
            ("3", "投资活动现金流出小计", investing_outflow),
            ("301", "购建固定资产、无形资产支付的现金", investing_outflow),
            ("200", "投资活动产生的现金流量净额", investing_net),
            ("4", "筹资活动现金流入小计", financing_inflow),
            ("5", "筹资活动现金流出小计", financing_outflow),
            ("300", "筹资活动产生的现金流量净额", financing_net),
            ("400", "现金及现金等价物净增加额", net_increase),
        ]

        for item_code, item_name, amount in items:
            cursor.execute("""
                INSERT INTO fs_cash_flow_item (
                    taxpayer_id, period_year, period_month, gaap_type,
                    item_code, item_name, amount, time_range,
                    revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month, gaap_type,
                item_code, item_name, amount, "monthly", 1,
                f"{year}-{month:02d}-20 14:00:00"
            ))

    conn.commit()
    print(f"✓ Generated cash flow data for {config['name']}")


def generate_eit_data(conn, taxpayer_id, config, periods):
    """Generate EIT (Enterprise Income Tax) data"""
    cursor = conn.cursor()

    # Annual EIT (for years 2023, 2024, 2025)
    for year in [2023, 2024, 2025]:
        # Calculate annual revenue
        annual_revenue = sum(
            calculate_revenue(config["base_revenue"], year, m, config["growth_rate"])
            for m in range(1, 13)
        )

        # Calculate taxable income (simplified)
        gross_profit = annual_revenue * config["gross_margin"]
        expenses = annual_revenue * 0.20
        taxable_income = round(gross_profit - expenses, 2)

        # Tax rate
        tax_rate = 0.20 if config["type"] == "小规模纳税人" else 0.25
        tax_payable = round(max(taxable_income, 0) * tax_rate, 2)

        # Insert filing record
        filing_id = f"{taxpayer_id}_{year}_0"
        cursor.execute("""
            INSERT INTO eit_annual_filing (
                filing_id, taxpayer_id, period_year, revision_no, submitted_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            filing_id, taxpayer_id, year, 1, f"{year+1}-05-31 16:00:00"
        ))

        # Insert main table
        cursor.execute("""
            INSERT INTO eit_annual_main (
                filing_id, revenue, cost, total_profit,
                taxable_income, tax_payable
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            filing_id,
            annual_revenue,
            round(annual_revenue * (1 - config["gross_margin"]), 2),
            taxable_income,
            taxable_income,
            tax_payable
        ))

    # Quarterly EIT (for 2023-2025 Q1-Q4, 2026 Q1)
    for year in [2023, 2024, 2025, 2026]:
        max_quarter = 1 if year == 2026 else 4
        for quarter in range(1, max_quarter + 1):
            # Calculate quarterly revenue
            quarter_months = range((quarter-1)*3 + 1, quarter*3 + 1)
            if year == 2026 and quarter == 1:
                quarter_months = range(1, 4)  # Jan-Mar

            quarterly_revenue = sum(
                calculate_revenue(config["base_revenue"], year, m, config["growth_rate"])
                for m in quarter_months
            )

            # Calculate taxable income
            gross_profit = quarterly_revenue * config["gross_margin"]
            expenses = quarterly_revenue * 0.20
            taxable_income = round(gross_profit - expenses, 2)

            # Tax
            tax_rate = 0.20 if config["type"] == "小规模纳税人" else 0.25
            tax_payable = round(max(taxable_income, 0) * tax_rate, 2)

            # Insert filing
            filing_month = quarter * 3 + 1 if quarter < 4 else 1
            filing_year = year if quarter < 4 else year + 1
            filing_id = f"{taxpayer_id}_{year}_Q{quarter}_0"

            cursor.execute("""
                INSERT INTO eit_quarter_filing (
                    filing_id, taxpayer_id, period_year, period_quarter,
                    revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                filing_id, taxpayer_id, year, quarter, 1,
                f"{filing_year}-{filing_month:02d}-15 10:00:00"
            ))

            # Insert main table
            cursor.execute("""
                INSERT INTO eit_quarter_main (
                    filing_id, revenue, cost, total_profit,
                    actual_profit, tax_rate, tax_payable
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                filing_id,
                quarterly_revenue,
                round(quarterly_revenue * (1 - config["gross_margin"]), 2),
                taxable_income,
                taxable_income,
                tax_rate,
                tax_payable
            ))

    conn.commit()
    print(f"✓ Generated EIT data for {config['name']}")


def generate_invoice_data(conn, taxpayer_id, config, periods):
    """Generate invoice data"""
    cursor = conn.cursor()

    for year, month in periods:
        revenue = calculate_revenue(
            config["base_revenue"], year, month, config["growth_rate"]
        )

        # Sales invoices (5-10 invoices per month)
        num_sales = random.randint(5, 10)
        for i in range(num_sales):
            invoice_amount = round(revenue / num_sales, 2)
            tax_amount = round(invoice_amount * config["vat_rate"], 2)

            cursor.execute("""
                INSERT INTO inv_spec_sales (
                    taxpayer_id, period_year, period_month,
                    invoice_code, invoice_number, invoice_date,
                    buyer_name, buyer_tax_id,
                    invoice_amount, tax_amount, total_amount,
                    invoice_type, revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month,
                f"0{random.randint(1000000, 9999999)}", f"{random.randint(10000000, 99999999)}",
                f"{year}-{month:02d}-{random.randint(1, 28):02d}",
                f"客户{i+1}", f"91{random.randint(100000000000000, 999999999999999)}",
                invoice_amount, tax_amount, invoice_amount + tax_amount,
                "增值税专用发票" if config["type"] == "一般纳税人" else "增值税普通发票",
                1, f"{year}-{month:02d}-{random.randint(1, 28):02d} 10:00:00"
            ))

        # Purchase invoices (4-8 invoices per month)
        num_purchase = random.randint(4, 8)
        cost = revenue * (1 - config["gross_margin"])
        for i in range(num_purchase):
            invoice_amount = round(cost / num_purchase, 2)
            tax_amount = round(invoice_amount * 0.13, 2)  # Assume 13% input VAT

            cursor.execute("""
                INSERT INTO inv_spec_purchase (
                    taxpayer_id, period_year, period_month,
                    invoice_code, invoice_number, invoice_date,
                    seller_name, seller_tax_id,
                    invoice_amount, tax_amount, total_amount,
                    invoice_type, revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month,
                f"0{random.randint(1000000, 9999999)}", f"{random.randint(10000000, 99999999)}",
                f"{year}-{month:02d}-{random.randint(1, 28):02d}",
                f"供应商{i+1}", f"91{random.randint(100000000000000, 999999999999999)}",
                invoice_amount, tax_amount, invoice_amount + tax_amount,
                "增值税专用发票",
                1, f"{year}-{month:02d}-{random.randint(1, 28):02d} 10:00:00"
            ))

    conn.commit()
    print(f"✓ Generated invoice data for {config['name']}")


def generate_account_balance_data(conn, taxpayer_id, config, periods):
    """Generate account balance data"""
    cursor = conn.cursor()

    # Define key accounts
    accounts = [
        ("1001", "库存现金", "资产类"),
        ("1002", "银行存款", "资产类"),
        ("1122", "应收账款", "资产类"),
        ("1405", "原材料", "资产类"),
        ("1601", "固定资产", "资产类"),
        ("2001", "短期借款", "负债类"),
        ("2202", "应付账款", "负债类"),
        ("4001", "实收资本", "所有者权益类"),
        ("6001", "主营业务收入", "损益类"),
        ("6401", "主营业务成本", "损益类"),
    ]

    for year, month in periods:
        revenue = calculate_revenue(
            config["base_revenue"], year, month, config["growth_rate"]
        )

        for account_code, account_name, account_category in accounts:
            # Calculate balances based on account type
            if account_code == "1002":  # Bank deposit
                debit_balance = round(revenue * 0.3, 2)
                credit_balance = 0
            elif account_code == "1122":  # Accounts receivable
                debit_balance = round(revenue * 0.4, 2)
                credit_balance = 0
            elif account_code == "2202":  # Accounts payable
                debit_balance = 0
                credit_balance = round(revenue * 0.3, 2)
            elif account_code == "6001":  # Revenue
                debit_balance = 0
                credit_balance = revenue
            elif account_code == "6401":  # Cost
                debit_balance = round(revenue * (1 - config["gross_margin"]), 2)
                credit_balance = 0
            else:
                # Other accounts with random balances
                debit_balance = round(revenue * random.uniform(0.1, 0.5), 2)
                credit_balance = 0

            # Calculate period amounts (10% of balance)
            debit_amount = round(debit_balance * 0.1, 2)
            credit_amount = round(credit_balance * 0.1, 2)

            cursor.execute("""
                INSERT INTO account_balance (
                    taxpayer_id, period_year, period_month,
                    account_code, account_name, account_category,
                    beginning_debit, beginning_credit,
                    period_debit, period_credit,
                    ending_debit, ending_credit,
                    revision_no, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                taxpayer_id, year, month,
                account_code, account_name, account_category,
                round(debit_balance * 0.9, 2), round(credit_balance * 0.9, 2),
                debit_amount, credit_amount,
                debit_balance, credit_balance,
                1, f"{year}-{month:02d}-25 16:00:00"
            ))

    conn.commit()
    print(f"✓ Generated account balance data for {config['name']}")


def main():
    """Main execution"""
    print("=" * 70)
    print("Generating sample data for new taxpayers")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    periods = generate_periods()

    print(f"\nGenerating data for {len(periods)} periods (2023-01 to 2026-03)")
    print()

    for taxpayer_id, config in TAXPAYERS.items():
        print(f"\n{'='*70}")
        print(f"Processing: {config['name']}")
        print(f"Type: {config['type']} | Standard: {config['standard']}")
        print(f"{'='*70}")

        generate_vat_data(conn, taxpayer_id, config, periods)
        generate_balance_sheet_data(conn, taxpayer_id, config, periods)
        generate_income_statement_data(conn, taxpayer_id, config, periods)
        generate_cash_flow_data(conn, taxpayer_id, config, periods)
        generate_eit_data(conn, taxpayer_id, config, periods)
        generate_invoice_data(conn, taxpayer_id, config, periods)
        generate_account_balance_data(conn, taxpayer_id, config, periods)

    conn.close()

    print("\n" + "=" * 70)
    print("✓ All sample data generated successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
