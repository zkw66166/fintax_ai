"""测试方案A - 验证prompt修改后是否避免SELECT *"""
import time
from mvp_pipeline import run_pipeline

print("="*80)
print("方案A测试 - 验证prompt修改效果")
print("="*80)

# 使用新的查询（避免缓存）
test_queries = [
    "查询纳税人001在2025年2月的销项税额",  # 新查询
    "查询纳税人001在2025年3月的进项税额",  # 新查询
    "查询纳税人001在2025年4月的应纳税额",  # 新查询
]

success_count = 0
retry_count = 0
total_time = 0

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*80}")
    print(f"测试 {i}/{len(test_queries)}: {query}")
    print(f"{'='*80}")

    start = time.time()
    result = run_pipeline(query)
    elapsed = time.time() - start
    total_time += elapsed

    # 检查是否有重试
    if result.get('audit_violations'):
        if 'SELECT *' in str(result['audit_violations']):
            print(f"\n⚠️ 仍然出现SELECT *问题")
            retry_count += 1
        else:
            print(f"\n⚠️ 其他审核问题: {result['audit_violations']}")
    else:
        print(f"\n✓ 首次生成即通过审核")

    if result['success']:
        success_count += 1
        print(f"✓ 查询成功 - 耗时: {elapsed:.2f}秒")
    else:
        print(f"✗ 查询失败 - 耗时: {elapsed:.2f}秒")
        print(f"  错误: {result.get('error', 'Unknown')}")

print(f"\n{'='*80}")
print("测试结果汇总")
print(f"{'='*80}")
print(f"总查询数: {len(test_queries)}")
print(f"成功数: {success_count}")
print(f"需要重试数: {retry_count}")
print(f"平均耗时: {total_time/len(test_queries):.2f}秒")

if retry_count == 0:
    print(f"\n✓ 优秀！所有查询首次生成即通过审核")
    print(f"  方案A成功解决了SELECT *问题")
elif retry_count < len(test_queries):
    print(f"\n⚠️ 部分改善：{len(test_queries)-retry_count}/{len(test_queries)}查询首次通过")
    print(f"  改善率: {(1-retry_count/len(test_queries))*100:.1f}%")
else:
    print(f"\n✗ 方案A未生效，仍需重试")
