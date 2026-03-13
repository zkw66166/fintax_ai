import sqlite3

conn = sqlite3.connect('database/fintax_ai.db')
cursor = conn.cursor()

# Check Dec 2025
cursor.execute("""
    SELECT DISTINCT metric_name
    FROM financial_metrics_item
    WHERE taxpayer_id='91310115MA2KZZZZZZ'
    AND period_year=2025
    AND period_month=12
    ORDER BY metric_name
""")
print('Available metrics in Dec 2025:')
for row in cursor.fetchall():
    print(f' - {row[0]}')

print('\n' + '='*60 + '\n')

# Check Mar 2026
cursor.execute("""
    SELECT metric_name, metric_value, period_type
    FROM financial_metrics_item
    WHERE taxpayer_id='91310115MA2KZZZZZZ'
    AND period_year=2026
    AND period_month=3
    ORDER BY metric_name
""")
print('Available metrics in Mar 2026:')
for row in cursor.fetchall():
    print(f' - {row[0]}: {row[1]} ({row[2]})')

conn.close()
