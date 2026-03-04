import sqlite3
import json
import re

conn = sqlite3.connect('d:/fintax_ai/database/fintax_ai.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'vw_%' ORDER BY name")
views = [r[0] for r in cursor.fetchall()]

all_views = {}

for view_name in views:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='view' AND name=?", (view_name,))
    result = cursor.fetchone()
    sql_def = result[0] if result else ""

    cursor.execute(f"PRAGMA table_info({view_name})")
    columns = cursor.fetchall()

    col_info = []
    for col in columns:
        col_info.append({
            "name": col[1],
            "type": col[2],
            "not_null": bool(col[3]),
            "default": col[4],
            "pk": bool(col[5])
        })

    all_views[view_name] = {
        "sql": sql_def,
        "columns": col_info,
        "column_count": len(col_info)
    }

conn.close()

with open('d:/fintax_ai/views_output.json', 'w', encoding='utf-8') as f:
    json.dump(all_views, f, ensure_ascii=False, indent=2)

print("Done! Output saved to views_output.json")
