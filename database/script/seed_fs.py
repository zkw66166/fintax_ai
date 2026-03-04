import sqlite3
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH
from database.init_db import get_ddl_statements

def seed_fs_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Executing DDLs...")
    ddls = get_ddl_statements()
    for ddl in ddls:
        try:
            cursor.execute(ddl)
        except Exception as e:
            print(f"Error executing DDL: {e}")
    
    print("Seeding Balance Sheet Dictionary...")
    # 1. Dictionary (ASBE)
    asbe_items = [
        ('ASBE', 'CASH', '货币资金', 1, 'ASSET', 10),
        ('ASBE', 'ACCOUNTS_RECEIVABLE', '应收账款', 5, 'ASSET', 50),
        ('ASBE', 'INVENTORY', '存货', 10, 'ASSET', 100),
        ('ASBE', 'FIXED_ASSETS', '固定资产', 22, 'ASSET', 220),
        ('ASBE', 'ASSETS', '资产总计', 34, 'ASSET', 340), # is_total=1
        ('ASBE', 'SHORT_TERM_LOANS', '短期借款', 35, 'LIABILITY', 350),
        ('ASBE', 'ACCOUNTS_PAYABLE', '应付账款', 39, 'LIABILITY', 390),
        ('ASBE', 'LIABILITIES', '负债合计', 60, 'LIABILITY', 600), # is_total=1
        ('ASBE', 'SHARE_CAPITAL', '实收资本（或股本）', 61, 'EQUITY', 610),
        ('ASBE', 'RETAINED_EARNINGS', '未分配利润', 70, 'EQUITY', 700),
        ('ASBE', 'EQUITY', '所有者权益（或股东权益）合计', 71, 'EQUITY', 710), # is_total=1
        ('ASBE', 'LIABILITIES_AND_EQUITY', '负债和所有者权益（或股东权益）总计', 72, 'LIABILITY_EQUITY', 720), # is_total=1
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO fs_balance_sheet_item_dict 
        (gaap_type, item_code, item_name, line_number, section, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, asbe_items)
    
    # 2. Dictionary (ASSE) - Small Business
    asse_items = [
        ('ASSE', 'CASH', '货币资金', 1, 'ASSET', 10),
        ('ASSE', 'ACCOUNTS_RECEIVABLE', '应收账款', 4, 'ASSET', 40),
        ('ASSE', 'INVENTORY', '存货', 9, 'ASSET', 90),
        ('ASSE', 'FIXED_ASSETS_NET', '固定资产账面价值', 20, 'ASSET', 200),
        ('ASSE', 'ASSETS', '资产合计', 30, 'ASSET', 300),
        ('ASSE', 'SHORT_TERM_LOANS', '短期借款', 31, 'LIABILITY', 310),
        ('ASSE', 'ACCOUNTS_PAYABLE', '应付账款', 33, 'LIABILITY', 330),
        ('ASSE', 'LIABILITIES', '负债合计', 47, 'LIABILITY', 470),
        ('ASSE', 'SHARE_CAPITAL', '实收资本（或股本）', 48, 'EQUITY', 480),
        ('ASSE', 'RETAINED_EARNINGS', '未分配利润', 51, 'EQUITY', 510),
        ('ASSE', 'EQUITY', '所有者权益（或股东权益）合计', 52, 'EQUITY', 520),
        ('ASSE', 'LIABILITIES_AND_EQUITY', '负债和所有者权益（或股东权益）总计', 53, 'LIABILITY_EQUITY', 530),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO fs_balance_sheet_item_dict 
        (gaap_type, item_code, item_name, line_number, section, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, asse_items)

    print("Seeding Synonyms...")
    # 3. Synonyms
    synonyms = [
        ('货币资金', 'cash_end', 'ASBE', 1),
        ('货币资金年初', 'cash_begin', 'ASBE', 2),
        ('应收账款', 'accounts_receivable_end', 'ASBE', 1),
        ('应收账款余额', 'accounts_receivable_end', 'ASBE', 1),
        ('应收账款年初', 'accounts_receivable_begin', 'ASBE', 2),
        ('存货', 'inventory_end', 'ASBE', 1),
        ('存货年初', 'inventory_begin', 'ASBE', 2),
        ('资产总计', 'assets_end', 'ASBE', 1),
        ('负债合计', 'liabilities_end', 'ASBE', 1),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO fs_balance_sheet_synonyms
        (phrase, column_name, gaap_type, priority)
        VALUES (?, ?, ?, ?)
    """, synonyms)

    print("Seeding Mock Data (FS Item)...")
    # 4. Mock Data
    taxpayer_id = "91310000TESTBS001"
    period_year = 2023
    period_month = 12
    
    # ASBE Data
    # Assets: Cash 100 + AR 200 + Inv 300 + Fixed 400 = 1000
    # Liab: Loan 200 + AP 300 = 500
    # Equity: Cap 400 + Retained 100 = 500
    # Total = 1000
    mock_data = [
        (taxpayer_id, period_year, period_month, 'ASBE', 'CASH', 100, 150), # Begin, End
        (taxpayer_id, period_year, period_month, 'ASBE', 'ACCOUNTS_RECEIVABLE', 200, 250),
        (taxpayer_id, period_year, period_month, 'ASBE', 'INVENTORY', 300, 350),
        (taxpayer_id, period_year, period_month, 'ASBE', 'FIXED_ASSETS', 400, 450),
        (taxpayer_id, period_year, period_month, 'ASBE', 'ASSETS', 1000, 1200),
        
        (taxpayer_id, period_year, period_month, 'ASBE', 'SHORT_TERM_LOANS', 200, 250),
        (taxpayer_id, period_year, period_month, 'ASBE', 'ACCOUNTS_PAYABLE', 300, 350),
        (taxpayer_id, period_year, period_month, 'ASBE', 'LIABILITIES', 500, 600),
        
        (taxpayer_id, period_year, period_month, 'ASBE', 'SHARE_CAPITAL', 400, 400),
        (taxpayer_id, period_year, period_month, 'ASBE', 'RETAINED_EARNINGS', 100, 200),
        (taxpayer_id, period_year, period_month, 'ASBE', 'EQUITY', 500, 600),
        (taxpayer_id, period_year, period_month, 'ASBE', 'LIABILITIES_AND_EQUITY', 1000, 1200),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO fs_balance_sheet_item
        (taxpayer_id, period_year, period_month, gaap_type, item_code, beginning_balance, ending_balance)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, mock_data)
    
    # Ensure Taxpayer Exists
    cursor.execute("""
        INSERT OR IGNORE INTO taxpayer_info (taxpayer_id, taxpayer_name, taxpayer_type)
        VALUES (?, ?, ?)
    """, (taxpayer_id, "测试资产负债企业001", "一般纳税人"))

    conn.commit()
    conn.close()
    print("Seed Complete.")

if __name__ == "__main__":
    seed_fs_data()
