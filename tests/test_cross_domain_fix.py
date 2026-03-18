"""测试跨域查询修复：小规模纳税人 + 企业会计准则"""
import sqlite3
from mvp_pipeline import run_pipeline

def test_cross_domain_query():
    """测试博雅文化传媒（小规模纳税人 + 企业会计准则）的跨域查询"""

    # 测试公司信息
    company_id = "91110108MA01AAAAA1"
    company_name = "博雅文化传媒有限公司"

    # 验证数据库中的公司信息
    conn = sqlite3.connect('database/fintax_ai.db')
    cur = conn.cursor()
    info = cur.execute(
        "SELECT taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
        (company_id,)
    ).fetchone()
    print(f"\n{'='*60}")
    print(f"公司信息验证")
    print(f"{'='*60}")
    print(f"公司名称: {company_name}")
    print(f"纳税人类型: {info[0]}")
    print(f"会计准则: {info[1]}")

    # 验证数据存在（使用视图）
    balance_count = cur.execute(
        "SELECT COUNT(*) FROM vw_balance_sheet_eas WHERE taxpayer_id = ?",
        (company_id,)
    ).fetchone()[0]
    profit_count = cur.execute(
        "SELECT COUNT(*) FROM vw_profit_eas WHERE taxpayer_id = ?",
        (company_id,)
    ).fetchone()[0]
    print(f"\n数据验证:")
    print(f"  资产负债表记录数 (vw_balance_sheet_eas): {balance_count}")
    print(f"  利润表记录数 (vw_profit_eas): {profit_count}")
    conn.close()

    # 测试跨域查询（公司名称已包含在查询中）
    query = f"{company_name}今年各季度总资产、总负债和净利润情况"
    print(f"\n{'='*60}")
    print(f"测试查询")
    print(f"{'='*60}")
    print(f"查询: {query}")
    print(f"\n执行中...")

    result = run_pipeline(query)

    print(f"\n{'='*60}")
    print(f"查询结果")
    print(f"{'='*60}")
    print(f"路由: {result.get('route')}")
    print(f"域: {result.get('domain')}")
    print(f"成功: {result.get('success')}")

    if result.get('entities'):
        entities = result['entities']
        print(f"\n实体信息:")
        print(f"  纳税人ID: {entities.get('taxpayer_id')}")
        print(f"  纳税人类型: {entities.get('taxpayer_type')}")
        print(f"  会计准则: {entities.get('accounting_standard')}")  # ✅ 应该显示"企业会计准则"

    if result.get('data'):
        data = result['data']
        print(f"\n数据行数: {len(data)}")
        if len(data) > 0:
            print(f"✅ 成功返回数据！")
            print(f"\n前3行数据:")
            for i, row in enumerate(data[:3]):
                print(f"  {i+1}. {row}")
        else:
            print(f"❌ 返回0行数据（Bug未修复）")

    if result.get('error'):
        print(f"\n错误: {result['error']}")

    return result

if __name__ == '__main__':
    test_cross_domain_query()
