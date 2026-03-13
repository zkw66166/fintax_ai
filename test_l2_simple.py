"""简化的L2缓存测试 - 直接调用pipeline"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mvp_pipeline import run_pipeline
from modules.db_utils import get_connection
import time

def test_multi_period_query():
    """测试多期间查询的L2缓存"""
    print("\n" + "="*60)
    print("测试: 多期间利润表查询L2缓存")
    print("="*60)

    query = "去年第一季度各月管理费用和财务费用比较分析"
    companies = [
        ("91310115MA2KZZZZZZ", "TSE科技有限公司"),
        ("91330200MA2KXXXXXX", "创智软件股份有限公司"),
        ("91310000MA1FL8XQ30", "华兴科技有限公司")
    ]

    for i, (company_id, company_name) in enumerate(companies):
        print(f"\n第{i+1}次查询: {company_name}")
        print(f"公司ID: {company_id}")

        # 构造完整查询（带公司名）
        full_query = f"{company_name} {query}"

        start = time.time()
        result = run_pipeline(full_query)
        elapsed = time.time() - start

        print(f"耗时: {elapsed:.2f}s")
        print(f"成功: {result.get('success', False)}")
        print(f"域: {result.get('domain', 'N/A')}")
        print(f"结果行数: {len(result.get('results', []))}")

        # 检查是否有SQL（第一次应该有，后续L2命中也应该有）
        if result.get('sql'):
            print(f"SQL长度: {len(result['sql'])}")

        # 第一次查询后等待一下，确保缓存已保存
        if i == 0:
            time.sleep(1)

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print("\n请检查后端日志:")
    print("- 第1次查询应该显示: [L2 Cache] Saved")
    print("- 第2次查询应该显示: [L2 Cache] Hit: domain=profit")
    print("- 第3次查询应该显示: [L2 Cache] Hit: domain=profit")

if __name__ == "__main__":
    test_multi_period_query()
