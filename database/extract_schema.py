
import sqlite3
import os

db_path = 'd:/fintax_ai/database/fintax_ai.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables and views
cursor.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name")
results = cursor.fetchall()


with open(os.path.join(os.path.dirname(db_path), 'schema_dump.sql'), 'w', encoding='utf-8') as f:
    f.write(f"-- Schema for {db_path}:\n\n")
    for type_, name, sql in results:
        if sql:
            f.write(f"-- {type_.upper()}: {name}\n")
            f.write(sql)
            f.write(";\n\n")

print(f"Schema written to {os.path.join(os.path.dirname(db_path), 'schema_dump.sql')}")

conn.close()
