#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for composition/structure query analysis
Tests: "2025年末的总资产构成分析"
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mvp_pipeline import run_pipeline
from config.settings import DB_PATH


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_composition_query():
    """Test composition/structure query"""

    # Test query
    query = "TSE科技2025年末的总资产构成分析"

    print_section("TEST QUERY")
    print(f"Query: {query}")
    print(f"Database: {DB_PATH}")

    # Run pipeline with debug output
    print_section("RUNNING PIPELINE")

    try:
        result = run_pipeline(
            user_query=query,
            db_path=str(DB_PATH),
            conversation_history=[]
        )

        # Print Stage 1 output (Intent Parser)
        print_section("STAGE 1: INTENT PARSER OUTPUT")
        if "intent" in result:
            print(json.dumps(result["intent"], indent=2, ensure_ascii=False))
        else:
            print("⚠️  No 'intent' field in result")

        # Print entities
        print_section("ENTITIES EXTRACTED")
        if "entities" in result:
            print(json.dumps(result["entities"], indent=2, ensure_ascii=False))
        else:
            print("⚠️  No 'entities' field in result")

        # Print Stage 2 output (SQL Writer)
        print_section("STAGE 2: SQL GENERATED")
        if "sql" in result:
            print(result["sql"])
        else:
            print("⚠️  No 'sql' field in result")

        # Print execution result
        print_section("EXECUTION RESULT")
        if "results" in result:
            data = result["results"]
            print(f"Row count: {len(data)}")
            if data:
                print("\nFirst 5 rows:")
                for i, row in enumerate(data[:5], 1):
                    print(f"\nRow {i}:")
                    print(json.dumps(row, indent=2, ensure_ascii=False))
        elif "data" in result:
            data = result["data"]
            print(f"Row count: {len(data)}")
            if data:
                print("\nFirst 5 rows:")
                for i, row in enumerate(data[:5], 1):
                    print(f"\nRow {i}:")
                    print(json.dumps(row, indent=2, ensure_ascii=False))
        else:
            print("⚠️  No 'results' or 'data' field in result")

        # Print error if any
        if "error" in result:
            print_section("ERROR")
            print(result["error"])

        # Print route
        print_section("ROUTE INFORMATION")
        print(f"Route: {result.get('route', 'unknown')}")
        print(f"Success: {result.get('success', False)}")

        # Check for composition-specific patterns
        print_section("COMPOSITION QUERY ANALYSIS")

        # Check if Stage 1 detected composition intent
        intent = result.get("intent", {})
        metrics = intent.get("metrics", [])
        print(f"\n✓ Metrics extracted: {len(metrics)}")
        if metrics:
            print("  Metrics list:")
            for m in metrics:
                print(f"    - {m}")

        # Check if SQL uses UNION ALL (composition pattern)
        sql = result.get("sql", "")
        if sql:
            has_union = "UNION ALL" in sql.upper()
            print(f"\n✓ SQL uses UNION ALL: {has_union}")
        else:
            print(f"\n✓ SQL uses UNION ALL: N/A (no SQL generated)")

        # Check if result has multiple rows (one per component)
        data = result.get("results") or result.get("data", [])
        print(f"\n✓ Result rows: {len(data)}")

        if len(data) > 1:
            print("  ✓ Multiple components detected (expected for composition query)")
        elif len(data) == 1:
            print("  ⚠️  Only 1 row returned (may be aggregated, not composition)")
        else:
            print("  ❌ No data returned")

        # Check domain detection
        entities = result.get("entities", {})
        domain = entities.get("domain_hint", "unknown")
        print(f"\n✓ Domain detected: {domain}")

        return result

    except Exception as e:
        print_section("EXCEPTION")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return None


def check_recent_changes():
    """Check for recent changes in key modules"""
    print_section("CHECKING KEY MODULE FILES")

    key_files = [
        "modules/entity_preprocessor.py",
        "modules/intent_parser.py",
        "modules/sql_writer.py",
        "prompts/stage2_balance_sheet.txt"
    ]

    for file_path in key_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            stat = full_path.stat()
            print(f"\n{file_path}:")
            print(f"  Size: {stat.st_size} bytes")
            print(f"  Modified: {stat.st_mtime}")
        else:
            print(f"\n{file_path}: ❌ NOT FOUND")


if __name__ == "__main__":
    print("=" * 80)
    print("  COMPOSITION QUERY DEBUG TEST")
    print("=" * 80)

    # Run test
    result = test_composition_query()

    # Check recent changes
    check_recent_changes()

    # Summary
    print_section("TEST SUMMARY")
    if result:
        success = result.get("success", False)
        route = result.get("route", "unknown")
        data_count = len(result.get("results") or result.get("data", []))

        print(f"✓ Pipeline completed: {success}")
        print(f"✓ Route: {route}")
        print(f"✓ Data rows: {data_count}")

        if success and data_count > 1:
            print("\n✅ TEST PASSED: Composition query returned multiple components")
        elif success and data_count == 1:
            print("\n⚠️  TEST WARNING: Query succeeded but only 1 row (may not be composition)")
        else:
            print("\n❌ TEST FAILED: Query did not return expected composition data")
    else:
        print("❌ TEST FAILED: Pipeline raised exception")
