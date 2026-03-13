import sqlite3
import json

conn = sqlite3.connect('d:/fintax_ai/database/fintax_ai.db')
cursor = conn.cursor()

result = {}

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]
    if table_name == 'sqlite_sequence':
        continue
    
    result[table_name] = {
        'columns': [],
        'indexes': [],
        'foreign_keys': []
    }
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        col_info = {
            'name': col[1],
            'type': col[2],
            'not_null': bool(col[3]),
            'default': col[4],
            'pk': bool(col[5])
        }
        result[table_name]['columns'].append(col_info)
    
    cursor.execute(f"PRAGMA index_list({table_name})")
    indexes = cursor.fetchall()
    for idx in indexes:
        result[table_name]['indexes'].append({
            'name': idx[1],
            'unique': bool(idx[2])
        })
    
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = cursor.fetchall()
    for fk in fks:
        result[table_name]['foreign_keys'].append({
            'from': fk[3],
            'to_table': fk[2],
            'to_column': fk[4]
        })

cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
views = cursor.fetchall()
result['__views__'] = [v[0] for v in views]

cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
indexes = cursor.fetchall()
result['__global_indexes__'] = [i[0] for i in indexes]

with open('d:/fintax_ai/schema.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Schema exported to schema.json")
conn.close()
