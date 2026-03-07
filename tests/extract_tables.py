import sqlite3

conn = sqlite3.connect('d:/fintax_ai/database/fintax_ai.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("=== ALL TABLES ===")
for table in tables:
    print(table[0])
