#!/usr/bin/env python3
"""Get view definitions from SQLite database."""
import sqlite3

db_path = "database/fintax_ai.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

views = ['vw_cash_flow_eas', 'vw_cash_flow_sas', 'vw_profit_eas', 'vw_profit_sas']

for view_name in views:
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name=?", (view_name,))
    row = cursor.fetchone()
    if row:
        print(f"\n{'='*80}")
        print(f"View: {view_name}")
        print(f"{'='*80}")
        print(row[0])
    else:
        print(f"\nView {view_name} not found")

conn.close()
