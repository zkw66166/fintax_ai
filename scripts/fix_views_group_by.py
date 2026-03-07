#!/usr/bin/env python3
"""Fix GROUP BY bug in cash_flow and profit views.

Removes metadata fields (submitted_at, etl_batch_id, source_doc_id, source_unit,
etl_confidence) and joined table columns (taxpayer_name, taxpayer_type,
accounting_standard) from GROUP BY clause.

Correct GROUP BY pattern (same as fixed balance_sheet views):
  GROUP BY i.taxpayer_id, i.period_year, i.period_month, tr.time_range, i.revision_no

Note: tr.time_range stays because it comes from CROSS JOIN and creates
legitimate separate groups (本期 vs 本年累计).
"""
import sqlite3
import sys

DB_PATH = "database/fintax_ai.db"

def get_view_sql(conn, view_name):
    """Get current view definition."""
    cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name=?", (view_name,))
    row = cur.fetchone()
    return row[0] if row else None

def fix_view(conn, view_name):
    """Fix GROUP BY clause in a view by dropping and recreating it."""
    sql = get_view_sql(conn, view_name)
    if not sql:
        print(f"  [SKIP] View {view_name} not found")
        return False

    # Find and fix the GROUP BY clause
    # Replace the broken GROUP BY with the correct one
    lines = sql.split('\n')
    new_lines = []
    in_group_by = False
    group_by_fixed = False

    for line in lines:
        if 'GROUP BY' in line and not group_by_fixed:
            # Replace entire GROUP BY clause
            new_lines.append("GROUP BY i.taxpayer_id, i.period_year, i.period_month, tr.time_range, i.revision_no")
            in_group_by = True
            group_by_fixed = True
            continue

        if in_group_by:
            # Skip continuation lines of old GROUP BY (they start with spaces and contain field names)
            stripped = line.strip()
            if stripped and not stripped.startswith('--') and ',' in stripped and any(
                kw in stripped for kw in ['submitted_at', 'etl_batch_id', 'source_doc_id',
                                          'taxpayer_name', 'taxpayer_type', 'accounting_standard',
                                          'source_unit', 'etl_confidence', 'tr.time_range',
                                          't.taxpayer', 't.accounting']
            ):
                continue  # Skip old GROUP BY continuation line
            else:
                in_group_by = False
                if stripped:  # Don't skip non-empty lines after GROUP BY
                    new_lines.append(line)
        else:
            new_lines.append(line)

    new_sql = '\n'.join(new_lines)

    # Remove the "CREATE VIEW xxx AS" prefix for recreation
    create_prefix = f"CREATE VIEW {view_name} AS"
    if new_sql.startswith(create_prefix):
        select_sql = new_sql[len(create_prefix):].strip()
    else:
        print(f"  [ERROR] Unexpected SQL prefix for {view_name}")
        return False

    # Drop and recreate
    conn.execute(f"DROP VIEW IF EXISTS {view_name}")
    conn.execute(f"CREATE VIEW {view_name} AS {select_sql}")
    print(f"  [OK] {view_name} fixed")
    return True

def verify_view(conn, view_name):
    """Verify the fixed view returns data."""
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cur.fetchone()[0]
        print(f"  [VERIFY] {view_name}: {count} rows")

        # Check GROUP BY is correct
        sql = get_view_sql(conn, view_name)
        if sql:
            # Extract GROUP BY line
            for line in sql.split('\n'):
                if 'GROUP BY' in line:
                    print(f"  [GROUP BY] {line.strip()}")
                    # Verify no metadata fields
                    bad_fields = ['submitted_at', 'etl_batch_id', 'source_doc_id',
                                  'source_unit', 'etl_confidence', 'taxpayer_name',
                                  'taxpayer_type', 'accounting_standard']
                    for f in bad_fields:
                        if f in line:
                            print(f"  [WARNING] GROUP BY still contains '{f}'!")
                            return False
                    break
        return count > 0
    except Exception as e:
        print(f"  [ERROR] {view_name}: {e}")
        return False

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    views_to_fix = ['vw_cash_flow_eas', 'vw_cash_flow_sas', 'vw_profit_eas', 'vw_profit_sas']

    print("=== Phase 1: Fix GROUP BY in financial statement views ===\n")

    # Show current state
    print("--- Before fix ---")
    for view_name in views_to_fix:
        sql = get_view_sql(conn, view_name)
        if sql:
            for line in sql.split('\n'):
                if 'GROUP BY' in line:
                    print(f"  {view_name}: {line.strip()}")
                    break

    print("\n--- Fixing views ---")
    for view_name in views_to_fix:
        fix_view(conn, view_name)

    conn.commit()

    print("\n--- Verifying ---")
    all_ok = True
    for view_name in views_to_fix:
        if not verify_view(conn, view_name):
            all_ok = False

    conn.close()

    if all_ok:
        print("\n=== All views fixed and verified ===")
    else:
        print("\n=== WARNING: Some views may have issues ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
