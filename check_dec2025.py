import sqlite3

conn = sqlite3.connect('database/fintax_ai.db')
cursor = conn.cursor()

# Check Dec 2025 specific metrics
cursor.execute("""
    SELECT metric_name, metric_value, period_type
    FROM financial_metrics_item
    WHERE taxpayer_id='91310115MA2KZZZZZZ'
    AND period_year=2025
    AND period_month=12
    AND metric_name IN ('净利率', '增值税税负率', '企业所得税税负率')
""")
print('Dec 2025 specific metrics:')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} ({row[2]})')

conn.close()
