"""Comprehensive analysis of mapping tables vs view columns for data browser header translation."""
import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect("database/fintax_ai.db")
conn.row_factory = sqlite3.Row

# 1. Get all column mapping tables
mapping_tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%column_mapping%' ORDER BY name"
).fetchall()]

all_mappings = {}
mapping_info = {}
for t in mapping_tables:
    cols_info = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
    if "column_name" not in cols_info or "business_name" not in cols_info:
        mapping_info[t] = f"SKIPPED - columns: {cols_info}"
        continue
    rows = conn.execute(f"SELECT column_name, business_name FROM {t} ORDER BY line_number").fetchall()
    mappings = {r["column_name"]: r["business_name"] for r in rows}
    mapping_info[t] = mappings
    all_mappings.update(mappings)

# 2. Check nl2sql_semantic_mapping
sem_mappings = {}
try:
    cols = [c[1] for c in conn.execute("PRAGMA table_info(nl2sql_semantic_mapping)").fetchall()]
    if "source_column" in cols and "business_term" in cols:
        sem_rows = conn.execute(
            "SELECT DISTINCT source_column, business_term FROM nl2sql_semantic_mapping WHERE is_primary = 1"
        ).fetchall()
        sem_mappings = {r["source_column"]: r["business_term"] for r in sem_rows}
except Exception as e:
    print(f"Semantic mapping error: {e}")

# 3. Get all view columns
views_config = {
    "vw_profit_eas": "profit",
    "vw_balance_sheet_eas": "balance_sheet", 
    "vw_cash_flow_eas": "cash_flow",
    "vw_vat_return_general": "vat",
    "vw_vat_return_small": "vat_small",
    "vw_eit_annual_main": "eit_annual",
    "vw_eit_quarter_main": "eit_quarter",
    "vw_account_balance": "account_balance",
    "vw_inv_spec_purchase": "invoice",
    "vw_financial_metrics": "financial_metrics",
}

skip_cols = {"revision_no", "submitted_at", "etl_batch_id", "source_doc_id", "source_unit", 
             "etl_confidence", "time_range", "accounting_standard_name", "accounting_standard"}

result = {}
for view_name, domain in views_config.items():
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({view_name})").fetchall()]
        display_cols = [c for c in cols if c not in skip_cols]
        
        uncovered = []
        for c in display_cols:
            is_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in c)
            if not is_chinese and c not in all_mappings and c not in sem_mappings:
                uncovered.append(c)
        
        result[view_name] = {
            "domain": domain,
            "all_display_cols": display_cols,
            "uncovered_english": uncovered,
        }
    except Exception as e:
        result[view_name] = {"error": str(e)}

conn.close()

# Print concise summary
print("=== MAPPING TABLES ===")
for t, info in mapping_info.items():
    if isinstance(info, dict):
        print(f"{t}: {len(info)} entries")
    else:
        print(f"{t}: {info}")

print(f"\nSemantic mappings: {len(sem_mappings)} entries")
print(f"Combined mappings: {len(all_mappings)} entries")

print("\n=== UNCOVERED COLUMNS PER VIEW ===")
for v, info in result.items():
    if "error" in info:
        print(f"{v}: ERROR - {info['error']}")
        continue
    uc = info["uncovered_english"]
    print(f"\n{v} ({info['domain']}): {len(info['all_display_cols'])} display cols, {len(uc)} uncovered")
    if uc:
        print(f"  Uncovered: {uc}")

# Write full results to JSON
full = {"mapping_tables": {k: v if isinstance(v, str) else v for k, v in mapping_info.items()},
        "semantic_mappings": sem_mappings,
        "views": result}
with open("mapping_analysis.json", "w", encoding="utf-8") as f:
    json.dump(full, f, ensure_ascii=False, indent=2)
print("\nFull results in mapping_analysis.json")
