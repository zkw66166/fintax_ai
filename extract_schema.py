import sqlite3

conn = sqlite3.connect('d:/fintax_ai/database/fintax_ai.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== Tables ===")
for table in tables:
    print(f"\n--- {table[0]} ---")
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
        if col[5] == 1:
            print(f"    -> PRIMARY KEY")
    cursor.execute(f"PRAGMA foreign_key_list({table[0]})")
    fks = cursor.fetchall()
    if fks:
        print("  Foreign Keys:")
        for fk in fks:
            print(f"    {fk[3]} -> {fk[2]}({fk[4]})")

conn.close()
