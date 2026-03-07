"""Check EIT table structure."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.db_utils import get_connection

conn = get_connection()

print("EIT Annual Basic Info sample:")
for r in conn.execute('SELECT * FROM eit_annual_basic_info LIMIT 1').fetchall():
    print(dict(r))

print("\nEIT Annual Main sample:")
for r in conn.execute('SELECT * FROM eit_annual_main LIMIT 1').fetchall():
    print(dict(r))

print("\nEIT Quarter Main sample:")
for r in conn.execute('SELECT * FROM eit_quarter_main LIMIT 1').fetchall():
    print(dict(r))

print("\nHR Employee Salary sample:")
for r in conn.execute('SELECT * FROM hr_employee_salary LIMIT 1').fetchall():
    print(dict(r))

conn.close()
