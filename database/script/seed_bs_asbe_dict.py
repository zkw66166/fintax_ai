"""Seed ASBE balance sheet item dict (67 items) - one-time migration.

The _seed_bs_item_dict() in seed_data.py defines 67 ASBE items but only
inserts the ASSE items due to a missing executemany call. This script
inserts the ASBE items directly.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


ASBE_ITEMS = [
    ('ASBE', 'CASH', '货币资金', 1, 'ASSET', 10, 0),
    ('ASBE', 'TRADING_FINANCIAL_ASSETS', '交易性金融资产', 2, 'ASSET', 20, 0),
    ('ASBE', 'DERIVATIVE_FINANCIAL_ASSETS', '衍生金融资产', 3, 'ASSET', 30, 0),
    ('ASBE', 'NOTES_RECEIVABLE', '应收票据', 4, 'ASSET', 40, 0),
    ('ASBE', 'ACCOUNTS_RECEIVABLE', '应收账款', 5, 'ASSET', 50, 0),
    ('ASBE', 'ACCOUNTS_RECEIVABLE_FINANCING', '应收账款融资', 6, 'ASSET', 60, 0),
    ('ASBE', 'PREPAYMENTS', '预付账款', 7, 'ASSET', 70, 0),
    ('ASBE', 'OTHER_RECEIVABLES', '其他应收款', 8, 'ASSET', 80, 0),
    ('ASBE', 'INVENTORY', '存货', 9, 'ASSET', 90, 0),
    ('ASBE', 'CONTRACT_ASSETS', '合同资产', 10, 'ASSET', 100, 0),
    ('ASBE', 'HELD_FOR_SALE_ASSETS', '持有待售资产', 11, 'ASSET', 110, 0),
    ('ASBE', 'CURRENT_PORTION_NON_CURRENT_ASSETS', '一年内到期的非流动资产', 12, 'ASSET', 120, 0),
    ('ASBE', 'OTHER_CURRENT_ASSETS', '其他流动资产', 13, 'ASSET', 130, 0),
    ('ASBE', 'CURRENT_ASSETS', '流动资产合计', 14, 'ASSET', 140, 1),
    ('ASBE', 'DEBT_INVESTMENTS', '债权投资', 15, 'ASSET', 150, 0),
    ('ASBE', 'OTHER_DEBT_INVESTMENTS', '其他债权投资', 16, 'ASSET', 160, 0),
    ('ASBE', 'LONG_TERM_RECEIVABLES', '长期应收款', 17, 'ASSET', 170, 0),
    ('ASBE', 'LONG_TERM_EQUITY_INVESTMENTS', '长期股权投资', 18, 'ASSET', 180, 0),
    ('ASBE', 'OTHER_EQUITY_INSTRUMENTS_INVEST', '其他权益工具投资', 19, 'ASSET', 190, 0),
    ('ASBE', 'OTHER_NON_CURRENT_FINANCIAL_ASSETS', '其他非流动金融资产', 20, 'ASSET', 200, 0),
    ('ASBE', 'INVESTMENT_PROPERTY', '投资性房地产', 21, 'ASSET', 210, 0),
    ('ASBE', 'FIXED_ASSETS', '固定资产', 22, 'ASSET', 220, 0),
    ('ASBE', 'CONSTRUCTION_IN_PROGRESS', '在建工程', 23, 'ASSET', 230, 0),
    ('ASBE', 'PRODUCTIVE_BIOLOGICAL_ASSETS', '生产性生物资产', 24, 'ASSET', 240, 0),
    ('ASBE', 'OIL_AND_GAS_ASSETS', '油气资产', 25, 'ASSET', 250, 0),
    ('ASBE', 'RIGHT_OF_USE_ASSETS', '使用权资产', 26, 'ASSET', 260, 0),
    ('ASBE', 'INTANGIBLE_ASSETS', '无形资产', 27, 'ASSET', 270, 0),
    ('ASBE', 'DEVELOPMENT_EXPENDITURE', '开发支出', 28, 'ASSET', 280, 0),
    ('ASBE', 'GOODWILL', '商誉', 29, 'ASSET', 290, 0),
    ('ASBE', 'LONG_TERM_DEFERRED_EXPENSES', '长期待摊费用', 30, 'ASSET', 300, 0),
    ('ASBE', 'DEFERRED_TAX_ASSETS', '递延所得税资产', 31, 'ASSET', 310, 0),
    ('ASBE', 'OTHER_NON_CURRENT_ASSETS', '其他非流动资产', 32, 'ASSET', 320, 0),
    ('ASBE', 'NON_CURRENT_ASSETS', '非流动资产合计', 33, 'ASSET', 330, 1),
    ('ASBE', 'ASSETS', '资产总计', 34, 'ASSET', 340, 1),
    ('ASBE', 'SHORT_TERM_LOANS', '短期借款', 35, 'LIABILITY', 350, 0),
    ('ASBE', 'TRADING_FINANCIAL_LIABILITIES', '交易性金融负债', 36, 'LIABILITY', 360, 0),
    ('ASBE', 'DERIVATIVE_FINANCIAL_LIABILITIES', '衍生金融负债', 37, 'LIABILITY', 370, 0),
    ('ASBE', 'NOTES_PAYABLE', '应付票据', 38, 'LIABILITY', 380, 0),
    ('ASBE', 'ACCOUNTS_PAYABLE', '应付账款', 39, 'LIABILITY', 390, 0),
    ('ASBE', 'ADVANCES_FROM_CUSTOMERS', '预收款项', 40, 'LIABILITY', 400, 0),
    ('ASBE', 'CONTRACT_LIABILITIES', '合同负债', 41, 'LIABILITY', 410, 0),
    ('ASBE', 'EMPLOYEE_BENEFITS_PAYABLE', '应付职工薪酬', 42, 'LIABILITY', 420, 0),
    ('ASBE', 'TAXES_PAYABLE', '应交税费', 43, 'LIABILITY', 430, 0),
    ('ASBE', 'OTHER_PAYABLES', '其他应付款', 44, 'LIABILITY', 440, 0),
    ('ASBE', 'HELD_FOR_SALE_LIABILITIES', '持有待售负债', 45, 'LIABILITY', 450, 0),
    ('ASBE', 'CURRENT_PORTION_NON_CURRENT_LIABILITIES', '一年内到期的非流动负债', 46, 'LIABILITY', 460, 0),
    ('ASBE', 'OTHER_CURRENT_LIABILITIES', '其他流动负债', 47, 'LIABILITY', 470, 0),
    ('ASBE', 'CURRENT_LIABILITIES', '流动负债合计', 48, 'LIABILITY', 480, 1),
    ('ASBE', 'LONG_TERM_LOANS', '长期借款', 49, 'LIABILITY', 490, 0),
    ('ASBE', 'BONDS_PAYABLE', '应付债券', 50, 'LIABILITY', 500, 0),
    ('ASBE', 'LEASE_LIABILITIES', '租赁负债', 51, 'LIABILITY', 510, 0),
    ('ASBE', 'LONG_TERM_PAYABLES', '长期应付款', 52, 'LIABILITY', 520, 0),
    ('ASBE', 'PROVISIONS', '预计负债', 53, 'LIABILITY', 530, 0),
    ('ASBE', 'DEFERRED_INCOME', '递延收益', 54, 'LIABILITY', 540, 0),
    ('ASBE', 'DEFERRED_TAX_LIABILITIES', '递延所得税负债', 55, 'LIABILITY', 550, 0),
    ('ASBE', 'OTHER_NON_CURRENT_LIABILITIES', '其他非流动负债', 56, 'LIABILITY', 560, 0),
    ('ASBE', 'NON_CURRENT_LIABILITIES', '非流动负债合计', 57, 'LIABILITY', 570, 1),
    ('ASBE', 'LIABILITIES', '负债合计', 58, 'LIABILITY', 580, 1),
    ('ASBE', 'SHARE_CAPITAL', '实收资本（或股本）', 59, 'EQUITY', 590, 0),
    ('ASBE', 'CAPITAL_RESERVE', '资本公积', 60, 'EQUITY', 600, 0),
    ('ASBE', 'TREASURY_STOCK', '减：库存股', 61, 'EQUITY', 610, 0),
    ('ASBE', 'OTHER_COMPREHENSIVE_INCOME', '其他综合收益', 62, 'EQUITY', 620, 0),
    ('ASBE', 'SPECIAL_RESERVE', '专项储备', 63, 'EQUITY', 630, 0),
    ('ASBE', 'SURPLUS_RESERVE', '盈余公积', 64, 'EQUITY', 640, 0),
    ('ASBE', 'RETAINED_EARNINGS', '未分配利润', 65, 'EQUITY', 650, 0),
    ('ASBE', 'EQUITY', '所有者权益合计', 66, 'EQUITY', 660, 1),
    ('ASBE', 'LIABILITIES_AND_EQUITY', '负债和所有者权益总计', 67, 'LIABILITY_EQUITY', 670, 1),
]


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Check current state
    count_before = cur.execute(
        "SELECT COUNT(*) FROM fs_balance_sheet_item_dict WHERE gaap_type='ASBE'"
    ).fetchone()[0]
    print(f"ASBE items before: {count_before}")

    cur.executemany(
        "INSERT OR REPLACE INTO fs_balance_sheet_item_dict "
        "(gaap_type, item_code, item_name, line_number, section, display_order, is_total) "
        "VALUES (?,?,?,?,?,?,?)",
        ASBE_ITEMS,
    )
    conn.commit()

    count_after = cur.execute(
        "SELECT COUNT(*) FROM fs_balance_sheet_item_dict WHERE gaap_type='ASBE'"
    ).fetchone()[0]
    print(f"ASBE items after: {count_after}")

    # Verify sections
    for section, cnt in cur.execute(
        "SELECT section, COUNT(*) FROM fs_balance_sheet_item_dict WHERE gaap_type='ASBE' GROUP BY section ORDER BY section"
    ).fetchall():
        print(f"  {section}: {cnt}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
