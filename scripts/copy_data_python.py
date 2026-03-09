"""
直接使用Python复制数据，避免SQL列数匹配问题
"""
import sqlite3

DB_PATH = "database/fintax_ai.db"

def copy_table_data(conn, table_name, source_id, target_id, multiplier, period_filter="period_year * 100 + period_month <= 202603"):
    """通用表数据复制函数"""
    cursor = conn.cursor()

    # 获取表的所有列
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    # 获取源数据
    cursor.execute(f"SELECT * FROM {table_name} WHERE taxpayer_id = ? AND {period_filter}", (source_id,))
    rows = cursor.fetchall()

    if not rows:
        print(f"  ⚠ {table_name}: 源数据为空")
        return 0

    # 准备INSERT语句
    placeholders = ','.join(['?'] * len(columns))
    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

    # 复制数据
    count = 0
    for row in rows:
        new_row = list(row)
        # 替换taxpayer_id
        new_row[0] = target_id

        # 对数值列应用倍数
        for i, (col_name, value) in enumerate(zip(columns, new_row)):
            if value is not None and isinstance(value, (int, float)) and col_name not in [
                'taxpayer_id', 'period_year', 'period_month', 'revision_no',
                'line_number', 'etl_confidence'
            ]:
                new_row[i] = round(value * multiplier, 2)

        try:
            cursor.execute(insert_sql, new_row)
            count += 1
        except sqlite3.IntegrityError:
            # 跳过重复数据
            pass

    return count

def main():
    print("=" * 70)
    print("为新增公司复制示例数据")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)

    try:
        # 公司1: 博雅文化传媒 (从鑫源贸易复制，×0.8)
        print("\n博雅文化传媒有限公司 (91110108MA01AAAAA1):")
        print("-" * 70)

        tables_1 = [
            ('vat_return_small', '92440300MA5EQXL17P'),
            ('fs_balance_sheet_item', '92440300MA5EQXL17P'),
            ('fs_income_statement_item', '92440300MA5EQXL17P'),
            ('fs_cash_flow_item', '92440300MA5EQXL17P'),
            ('account_balance', '92440300MA5EQXL17P'),
        ]

        for table, source in tables_1:
            count = copy_table_data(conn, table, source, '91110108MA01AAAAA1', 0.8)
            print(f"  ✓ {table}: {count} 条记录")

        # 修改GAAP类型为企业会计准则
        conn.execute("""
            UPDATE fs_balance_sheet_item
            SET gaap_type = 'ASBE'
            WHERE taxpayer_id = '91110108MA01AAAAA1'
        """)
        conn.execute("""
            UPDATE fs_income_statement_item
            SET gaap_type = 'CAS'
            WHERE taxpayer_id = '91110108MA01AAAAA1'
        """)
        conn.execute("""
            UPDATE fs_cash_flow_item
            SET gaap_type = 'CAS'
            WHERE taxpayer_id = '91110108MA01AAAAA1'
        """)
        print("  ✓ 已更新GAAP类型为企业会计准则")

        # 公司2: 恒泰建材 (VAT从TSE科技，财务报表从环球机械，×1.2)
        print("\n恒泰建材有限公司 (91320200MA02BBBBB2):")
        print("-" * 70)

        # VAT从TSE科技
        count = copy_table_data(conn, 'vat_return_general', '91310115MA2KZZZZZZ', '91320200MA02BBBBB2', 1.2)
        print(f"  ✓ vat_return_general: {count} 条记录")

        # 财务报表从环球机械
        tables_2 = [
            ('fs_balance_sheet_item', '91330100MA2KWWWWWW'),
            ('fs_income_statement_item', '91330100MA2KWWWWWW'),
            ('fs_cash_flow_item', '91330100MA2KWWWWWW'),
            ('account_balance', '91330100MA2KWWWWWW'),
        ]

        for table, source in tables_2:
            count = copy_table_data(conn, table, source, '91320200MA02BBBBB2', 1.2)
            print(f"  ✓ {table}: {count} 条记录")

        conn.commit()
        print("\n" + "=" * 70)
        print("✓ 数据复制完成")
        print("=" * 70)

        # 验证
        print("\n数据验证:")
        print("-" * 70)

        for taxpayer_id, name in [
            ('91110108MA01AAAAA1', '博雅文化传媒'),
            ('91320200MA02BBBBB2', '恒泰建材')
        ]:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    (SELECT COUNT(DISTINCT period_year*100+period_month) FROM vat_return_small WHERE taxpayer_id = ?) +
                    (SELECT COUNT(DISTINCT period_year*100+period_month) FROM vat_return_general WHERE taxpayer_id = ?) as vat_periods,
                    (SELECT COUNT(DISTINCT period_year*100+period_month) FROM fs_balance_sheet_item WHERE taxpayer_id = ?) as bs_periods,
                    (SELECT COUNT(DISTINCT period_year*100+period_month) FROM fs_income_statement_item WHERE taxpayer_id = ?) as is_periods
            """, (taxpayer_id, taxpayer_id, taxpayer_id, taxpayer_id))

            vat, bs, is_count = cursor.fetchone()
            status = "✓" if (vat > 0 and bs > 0 and is_count > 0) else "✗"
            print(f"{status} {name}: VAT={vat}期, 资产负债表={bs}期, 利润表={is_count}期")

        return 0

    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return 1
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    sys.exit(main())
