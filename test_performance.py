"""综合性能测试 - 验证所有优化效果"""
import time
from mvp_pipeline import run_pipeline, print_cache_stats

print("="*80)
print("fintax_ai 性能优化综合测试")
print("="*80)

# 测试查询集
test_queries = [
    "查询纳税人001在2025年1月的销项税额",
    "查询纳税人001在2025年1月的销项税额",  # 重复查询（测试缓存）
    "查询纳税人001在2025年1月的进项税额",  # 相似查询
]

results = []

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*80}")
    print(f"测试 {i}/{len(test_queries)}: {query}")
    print(f"{'='*80}")

    start = time.time()
    result = run_pipeline(query)
    elapsed = time.time() - start

    status = "✓ 成功" if result['success'] else "✗ 失败"
    print(f"\n{status} - 总耗时: {elapsed:.2f}秒")

    results.append({
        'query': query,
        'elapsed': elapsed,
        'success': result['success']
    })

# 打印缓存统计
print("\n")
print_cache_stats()

# 性能汇总
print("\n" + "="*80)
print("性能汇总")
print("="*80)

for i, r in enumerate(results, 1):
    query_short = r['query'][:40] + "..." if len(r['query']) > 40 else r['query']
    status = "✓" if r['success'] else "✗"
    print(f"{i}. {status} {query_short:<45} {r['elapsed']:>6.2f}秒")

# 性能对比
if len(results) >= 2:
    first_time = results[0]['elapsed']
    second_time = results[1]['elapsed']
    improvement = (1 - second_time / first_time) * 100 if first_time > 0 else 0

    print(f"\n缓存效果:")
    print(f"  首次查询: {first_time:.2f}秒")
    print(f"  重复查询: {second_time:.2f}秒")
    print(f"  性能提升: {improvement:.1f}%")

    if improvement > 90:
        print(f"  ✓ 优秀 - 缓存工作正常")
    elif improvement > 50:
        print(f"  ⚠ 良好 - 缓存部分生效")
    else:
        print(f"  ✗ 需检查 - 缓存可能未生效")

print("\n" + "="*80)
print("测试完成")
print("="*80)
