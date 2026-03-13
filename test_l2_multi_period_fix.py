"""测试L2缓存多期间单域查询修复

测试场景：
1. 多期间利润表查询（当前问题）
2. 单期间利润表查询（回归测试）
3. 跨域查询（回归测试）
4. VAT查询（回归测试）
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# 测试用户登录
def login():
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "user1",
        "password": "123456"
    })
    if response.status_code == 200:
        data = response.json()
        return data["access_token"]
    else:
        raise Exception(f"Login failed: {response.text}")

# 执行查询并检查缓存命中
def test_query(token, company_id, query, test_name):
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"公司: {company_id}")
    print(f"查询: {query}")
    print(f"{'='*60}")

    headers = {"Authorization": f"Bearer {token}"}

    # 第一次查询（应该走pipeline）
    print("\n第一次查询（应该走pipeline）...")
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/chat",
        headers=headers,
        json={
            "query": query,
            "company_id": company_id,
            "thinking_mode": "quick",
            "response_mode": "detailed",
            "multi_turn_enabled": False,
            "conversation_depth": 3
        },
        stream=True
    )

    first_result = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('event: done'):
                # 下一行是data
                continue
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    if 'results' in data or 'route' in data:
                        first_result = data
                except:
                    pass

    first_time = time.time() - start
    print(f"✓ 第一次查询完成，耗时: {first_time:.2f}s")
    if first_result:
        print(f"  - 路由: {first_result.get('route', 'N/A')}")
        print(f"  - 域: {first_result.get('domain', 'N/A')}")
        print(f"  - 结果行数: {len(first_result.get('results', []))}")

    # 等待1秒
    time.sleep(1)

    # 第二次查询（应该命中L2缓存）
    print("\n第二次查询（应该命中L2缓存）...")
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/api/chat",
        headers=headers,
        json={
            "query": query,
            "company_id": company_id,
            "thinking_mode": "quick",
            "response_mode": "detailed",
            "multi_turn_enabled": False,
            "conversation_depth": 3
        },
        stream=True
    )

    second_result = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    if 'results' in data or 'route' in data:
                        second_result = data
                except:
                    pass

    second_time = time.time() - start
    print(f"✓ 第二次查询完成，耗时: {second_time:.2f}s")

    # 检查缓存命中
    cache_hit = second_result.get('cache_hit', False) if second_result else False
    cache_source = second_result.get('cache_source', 'N/A') if second_result else 'N/A'

    print(f"\n结果:")
    print(f"  - 缓存命中: {cache_hit}")
    print(f"  - 缓存来源: {cache_source}")
    print(f"  - 加速比: {first_time / second_time:.2f}x")

    if cache_hit and cache_source == 'l2':
        print(f"✅ 测试通过: L2缓存命中")
        return True
    else:
        print(f"❌ 测试失败: L2缓存未命中")
        return False

def main():
    print("开始测试L2缓存多期间单域查询修复...")

    # 登录
    token = login()
    print("✓ 登录成功")

    # 测试用例
    test_cases = [
        {
            "name": "多期间利润表查询（修复目标）",
            "company_id": "91310115MA2KZZZZZZ",  # TSE科技
            "query": "去年第一季度各月管理费用和财务费用比较分析"
        },
        {
            "name": "单期间利润表查询（回归测试）",
            "company_id": "91310115MA2KZZZZZZ",
            "query": "2025年1月营业收入"
        },
        {
            "name": "VAT查询（回归测试）",
            "company_id": "91310115MA2KZZZZZZ",
            "query": "2025年1月增值税"
        },
        {
            "name": "跨域查询（回归测试）",
            "company_id": "91310115MA2KZZZZZZ",
            "query": "2025年1月营业收入和增值税对比"
        }
    ]

    results = []
    for case in test_cases:
        success = test_query(token, case["company_id"], case["query"], case["name"])
        results.append((case["name"], success))
        time.sleep(2)  # 测试间隔

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试汇总:")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {name}")

    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
