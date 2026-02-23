"""为现有数据库添加性能优化索引"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def add_performance_indexes():
    """添加性能优化索引"""
    print(f"连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    # 定义要添加的索引
    indexes = [
        # P0: 关键索引
        ("idx_general_taxpayer_period_revision",
         "vat_return_general(taxpayer_id, period_year, period_month, revision_no DESC)",
         "优化修订版本追踪（窗口函数）"),

        ("idx_small_taxpayer_period_revision",
         "vat_return_small(taxpayer_id, period_year, period_month, revision_no DESC)",
         "优化修订版本追踪（窗口函数）"),

        ("idx_taxpayer_type",
         "taxpayer_info(taxpayer_type)",
         "优化视图类型过滤"),

        ("idx_general_dimensions",
         "vat_return_general(taxpayer_id, period_year, period_month, item_type, time_range)",
         "覆盖常见过滤条件组合"),

        ("idx_small_dimensions",
         "vat_return_small(taxpayer_id, period_year, period_month, item_type, time_range)",
         "覆盖常见过滤条件组合"),

        # P1: 次要索引
        ("idx_taxpayer_type_industry",
         "taxpayer_info(taxpayer_type, industry_code)",
         "优化类型+行业组合查询"),

        ("idx_query_log_taxpayer_period",
         "user_query_log(taxpayer_id, created_at DESC)",
         "优化查询日志分析"),
    ]

    print(f"\n准备添加 {len(indexes)} 个索引...\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for idx_name, idx_def, description in indexes:
        try:
            # 检查索引是否已存在
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                (idx_name,)
            )
            if cursor.fetchone():
                print(f"⊙ {idx_name}: 已存在，跳过")
                skip_count += 1
                continue

            # 创建索引
            print(f"→ {idx_name}: 创建中...")
            print(f"  定义: {idx_def}")
            print(f"  说明: {description}")

            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            conn.commit()

            print(f"✓ {idx_name}: 创建成功\n")
            success_count += 1

        except Exception as e:
            print(f"✗ {idx_name}: 创建失败 - {e}\n")
            error_count += 1

    conn.close()

    # 打印汇总
    print("="*60)
    print("索引创建汇总")
    print("="*60)
    print(f"成功: {success_count}")
    print(f"跳过: {skip_count}")
    print(f"失败: {error_count}")
    print(f"总计: {len(indexes)}")
    print("="*60)

    if error_count > 0:
        print("\n⚠ 部分索引创建失败，请检查错误信息")
        return False
    else:
        print("\n✓ 所有索引创建完成")
        return True


def verify_indexes():
    """验证索引是否创建成功"""
    print("\n验证索引...")
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.execute("""
        SELECT name, tbl_name
        FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
        ORDER BY tbl_name, name
    """)

    indexes = cursor.fetchall()
    conn.close()

    print(f"\n当前数据库共有 {len(indexes)} 个索引:\n")

    current_table = None
    for idx_name, tbl_name in indexes:
        if tbl_name != current_table:
            print(f"\n{tbl_name}:")
            current_table = tbl_name
        print(f"  - {idx_name}")


if __name__ == "__main__":
    print("="*60)
    print("fintax_ai 性能优化索引迁移")
    print("="*60)

    # 添加索引
    success = add_performance_indexes()

    # 验证索引
    if success:
        verify_indexes()

    print("\n完成！")
