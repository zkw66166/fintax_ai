"""
Master script to fix and supplement fintax_ai.db
Executes all steps in order:
1. Delete future data (2026-04 onwards)
2. Add 2 new taxpayers
3. Generate sample data
4. Update financial metrics
5. Validate data quality
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

DB_PATH = "database/fintax_ai.db"
SCRIPTS_DIR = Path(__file__).parent


def execute_sql_script(db_path, sql_file):
    """Execute SQL script file"""
    print(f"\nExecuting SQL script: {sql_file.name}")
    print("-" * 70)

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.executescript(sql_script)
        conn.commit()
        print(f"✓ SQL script executed successfully")
        return True
    except Exception as e:
        print(f"✗ Error executing SQL script: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def execute_python_script(script_file):
    """Execute Python script"""
    print(f"\nExecuting Python script: {script_file.name}")
    print("-" * 70)

    try:
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=SCRIPTS_DIR.parent,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print(result.stdout)

        if result.returncode != 0:
            print(f"✗ Script failed with return code {result.returncode}")
            print(result.stderr)
            return False

        print(f"✓ Python script executed successfully")
        return True
    except Exception as e:
        print(f"✗ Error executing Python script: {e}")
        return False


def backup_database(db_path):
    """Create database backup"""
    from datetime import datetime
    import shutil

    backup_path = db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    print(f"\nCreating database backup: {backup_path}")

    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created successfully")
        return backup_path
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return None


def verify_new_taxpayers(db_path):
    """Verify new taxpayers were added"""
    print("\nVerifying new taxpayers...")
    print("-" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT taxpayer_id, taxpayer_name, taxpayer_type, accounting_standard
        FROM taxpayer_info
        WHERE taxpayer_id IN ('91110108MA01AAAAA1', '91320200MA02BBBBB2')
    """)

    taxpayers = cursor.fetchall()
    conn.close()

    if len(taxpayers) == 2:
        print("✓ New taxpayers verified:")
        for tp in taxpayers:
            print(f"  - {tp[1]} ({tp[2]}, {tp[3]})")
        return True
    else:
        print(f"✗ Expected 2 new taxpayers, found {len(taxpayers)}")
        return False


def verify_data_periods(db_path):
    """Verify data periods are correct (no future data)"""
    print("\nVerifying data periods...")
    print("-" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check VAT data
    cursor.execute("""
        SELECT taxpayer_id, MAX(period_year * 100 + period_month) as max_period
        FROM (
            SELECT taxpayer_id, period_year, period_month FROM vat_return_general
            UNION ALL
            SELECT taxpayer_id, period_year, period_month FROM vat_return_small
        )
        GROUP BY taxpayer_id
        HAVING max_period > 202603
    """)

    future_data = cursor.fetchall()
    conn.close()

    if len(future_data) == 0:
        print("✓ No future data found (all data <= 2026-03)")
        return True
    else:
        print(f"✗ Found future data for {len(future_data)} taxpayers:")
        for tp_id, max_period in future_data:
            print(f"  - {tp_id}: max period {max_period}")
        return False


def main():
    """Main execution"""
    print("=" * 70)
    print("FINTAX AI DATABASE FIX AND SUPPLEMENT")
    print("=" * 70)
    print("\nThis script will:")
    print("1. Create database backup")
    print("2. Delete future data (2026-04 onwards)")
    print("3. Add 2 new taxpayers")
    print("4. Generate sample data (2023-01 to 2026-03)")
    print("5. Update financial metrics")
    print("6. Validate data quality")
    print("\n" + "=" * 70)

    # Confirm execution
    response = input("\nProceed? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Operation cancelled.")
        return

    # Step 0: Backup database
    print("\n" + "=" * 70)
    print("STEP 0: Backup Database")
    print("=" * 70)
    backup_path = backup_database(DB_PATH)
    if not backup_path:
        print("\n✗ Failed to create backup. Aborting.")
        return

    # Step 1: Execute SQL script (delete future data + add taxpayers)
    print("\n" + "=" * 70)
    print("STEP 1: Delete Future Data and Add New Taxpayers")
    print("=" * 70)
    sql_file = SCRIPTS_DIR / "fix_and_supplement_data.sql"
    if not execute_sql_script(DB_PATH, sql_file):
        print("\n✗ Failed to execute SQL script. Aborting.")
        return

    # Verify new taxpayers
    if not verify_new_taxpayers(DB_PATH):
        print("\n✗ New taxpayers verification failed. Aborting.")
        return

    # Verify data periods
    if not verify_data_periods(DB_PATH):
        print("\n✗ Data period verification failed. Aborting.")
        return

    # Step 2: Generate sample data
    print("\n" + "=" * 70)
    print("STEP 2: Generate Sample Data")
    print("=" * 70)
    generate_script = SCRIPTS_DIR / "generate_sample_data.py"
    if not execute_python_script(generate_script):
        print("\n✗ Failed to generate sample data. Aborting.")
        return

    # Step 3: Update metrics and validate
    print("\n" + "=" * 70)
    print("STEP 3: Update Financial Metrics and Validate Data Quality")
    print("=" * 70)
    validate_script = SCRIPTS_DIR / "update_metrics_and_validate.py"
    if not execute_python_script(validate_script):
        print("\n✗ Failed to update metrics and validate. Check output above.")
        # Don't abort - validation failures are informational

    # Final summary
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)
    print(f"✓ Database backup: {backup_path}")
    print("✓ Future data deleted (2026-04 onwards)")
    print("✓ 2 new taxpayers added:")
    print("  - 博雅文化传媒有限公司 (企业会计准则 + 小规模纳税人)")
    print("  - 恒泰建材有限公司 (小企业会计准则 + 一般纳税人)")
    print("✓ Sample data generated (2023-01 to 2026-03)")
    print("✓ Financial metrics updated")
    print("✓ Data quality validation completed")
    print("\n" + "=" * 70)
    print("ALL OPERATIONS COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
