"""简单测试：2025年数据"""
from mvp_pipeline import run_pipeline

query = "博雅文化传媒有限公司2025年各季度总资产、总负债和净利润情况"
print(f"查询: {query}\n")

result = run_pipeline(query)

print(f"\n{'='*60}")
print(f"结果")
print(f"{'='*60}")
print(f"成功: {result.get('success')}")
print(f"域: {result.get('domain')}")

if result.get('entities'):
    entities = result['entities']
    print(f"\n实体:")
    print(f"  会计准则: {entities.get('accounting_standard')}")

if result.get('data'):
    data = result['data']
    print(f"\n数据行数: {len(data)}")
    if len(data) > 0:
        print(f"✅ 成功！")
        for i, row in enumerate(data[:5]):
            print(f"  {i+1}. {row}")
    else:
        print(f"❌ 0行")
