import sqlite3
import sys
import unittest
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_PATH
from modules.entity_preprocessor import detect_entities


class TestBalanceSheetFeatures(unittest.TestCase):

    def test_01_db_schema(self):
        """Verify tables and views exist"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        tables = [
            'fs_balance_sheet_item',
            'fs_balance_sheet_item_dict',
            'fs_balance_sheet_synonyms'
        ]
        for t in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
            self.assertIsNotNone(cursor.fetchone(), f"Table {t} missing")

        views = [
            'vw_balance_sheet_eas',
            'vw_balance_sheet_sas'
        ]
        for v in views:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='view' AND name='{v}'")
            self.assertIsNotNone(cursor.fetchone(), f"View {v} missing")

        conn.close()

    def test_02_data_exists(self):
        """Verify seeded data exists for the test taxpayers"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check Item Table (华兴科技 ASBE)
        cursor.execute("SELECT COUNT(*) FROM fs_balance_sheet_item WHERE taxpayer_id='91310000MA1FL8XQ30'")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "No data in fs_balance_sheet_item for 华兴科技")

        # Check Dictionary
        cursor.execute("SELECT COUNT(*) FROM fs_balance_sheet_item_dict")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "No data in fs_balance_sheet_item_dict")

        # Check View (ASBE)
        cursor.execute("SELECT * FROM vw_balance_sheet_eas WHERE taxpayer_id='91310000MA1FL8XQ30' LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row, "View vw_balance_sheet_eas returned no rows")

        cols = [d[0] for d in cursor.description]
        self.assertIn('cash_end', cols)
        self.assertIn('cash_begin', cols)
        self.assertIn('assets_end', cols)

        # Check View (ASSE)
        cursor.execute("SELECT * FROM vw_balance_sheet_sas WHERE taxpayer_id='92440300MA5EQXL17P' LIMIT 1")
        row = cursor.fetchone()
        self.assertIsNotNone(row, "View vw_balance_sheet_sas returned no rows")

        # Verify accounting equation
        cursor.execute("""
            SELECT assets_end, liabilities_end, equity_end
            FROM vw_balance_sheet_eas
            WHERE taxpayer_id='91310000MA1FL8XQ30' AND period_year=2025 AND period_month=1
        """)
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        assets, liabilities, equity = row
        self.assertEqual(assets, liabilities + equity, "Accounting equation violated")

        conn.close()

    def test_03_domain_heuristics(self):
        """Verify domain routing heuristics in entity_preprocessor"""
        conn = sqlite3.connect(DB_PATH)

        cases = [
            ("货币资金年初余额是多少", 'balance_sheet'),
            ("应收账款期初余额", 'account_balance'),
            ("本月借方发生额", 'account_balance'),
            ("应收账款余额", 'balance_sheet'),
            ("资产负债表", 'balance_sheet'),
            ("资产总计", 'balance_sheet'),
            ("科目余额表", 'account_balance'),
            ("借方发生额", 'account_balance'),
            ("合同资产", 'balance_sheet'),
            ("存货年初余额", 'balance_sheet'),
            ("存货期初余额", 'account_balance'),
        ]

        for query, expected in cases:
            entities = detect_entities(query, conn)
            actual = entities.get('domain_hint')
            self.assertEqual(actual, expected,
                             f"Query '{query}': expected {expected}, got {actual}")

        conn.close()


if __name__ == '__main__':
    unittest.main()
