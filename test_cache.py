"""测试缓存功能"""
import time
from mvp_pipeline import run_pipeline, print_cache_stats

# 测试查询
test_query = "查询纳税人001在2025年1月的销项税额"

print("="*80)
print("缓存功能测试")
print("="*80)

# 第一次查询（缓存未命中）
print("\n【第1次查询 - 预期缓存未命中】")
start = time.time()
result1 = run_pipeline(test_query)
elapsed1 = time.time() - start
print(f"\n总耗时: {elapsed1:.2f}秒")

# 第二次查询（缓存命中）
print("\n\n【第2次查询 - 预期缓存命中】")
start = time.time()
result2 = run_pipeline(test_query)
elapsed2 = time.time() - start
print(f"\n总耗时: {elapsed2:.2f}秒")

# 第三次查询（缓存命中）
print("\n\n【第3次查询 - 预期缓存命中】")
start = time.time()
result3 = run_pipeline(test_query)
elapsed3 = time.time() - start
print(f"\n总耗时: {elapsed3:.2f}秒")

# 打印缓存统计
print("\n")
print_cache_stats()

# 性能对比
print(f"\n性能对比:")
print(f"  第1次查询: {elapsed1:.2f}秒 (缓存未命中)")
print(f"  第2次查询: {elapsed2:.2f}秒 (缓存命中，提升 {(1-elapsed2/elapsed1)*100:.1f}%)")
print(f"  第3次查询: {elapsed3:.2f}秒 (缓存命中，提升 {(1-elapsed3/elapsed1)*100:.1f}%)")
