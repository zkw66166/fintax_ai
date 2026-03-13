"""测试跨域L2缓存功能

测试场景：
1. 首次跨域查询 - 创建L2模板
2. 相同查询 + 相同组合 - 命中L2缓存
3. 相同查询 + 不同组合 - 创建新模板
4. 验证4种组合逐步积累
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
CACHE_DIR = Path("D:/fintax_ai/cache")

# 测试公司配置
TEST_COMPANIES = {
    "TSE科技": {
        "id": "91310115MA2KZZZZZZ",
        "type": "一般纳税人",
        "standard": "企业会计准则"
    },
    "创智软件": {
        "id": "91330200MA2KXXXXXX",
        "type": "一般纳税人",
        "standard": "企业会计准则"
    },
    "鑫源贸易": {
        "id": "XY002",
        "type": "小规模纳税人",
        "standard": "小企业会计准则"
    },
    "环球机械": {
        "id": "HQ006",
        "type": "小规模纳税人",
        "standard": "企业会计准则"
    }
}

# 测试查询
TEST_QUERY = "今年各季度总资产、总负债和净利润情况"


def login(username="user1", password="123456"):
    """登录获取token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        raise Exception(f"Login failed: {response.text}")


def chat_query(token, company_id, query, thinking_mode="quick"):
    """发送聊天查询"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": thinking_mode,
        "response_mode": "detailed"
    }

    response = requests.post(
        f"{BASE_URL}/api/chat",
        headers=headers,
        json=payload,
        stream=True
    )

    result = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('event: done'):
                continue
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    data = json.loads(data_str)
                    if data.get('route') or data.get('success') is not None:
                        result = data
                except:
                    pass

    return result


def count_l2_templates():
    """统计L2模板文件数量"""
    if not CACHE_DIR.exists():
        return 0
    return len(list(CACHE_DIR.glob("template_*.json")))


def get_l2_template_info():
    """获取所有L2模板信息"""
    if not CACHE_DIR.exists():
        return []

    templates = []
    for fp in CACHE_DIR.glob("template_*.json"):
        try:
            data = json.loads(fp.read_text(encoding='utf-8'))
            templates.append({
                "file": fp.name,
                "query": data.get("query", "")[:50],
                "domain": data.get("domain", ""),
                "cache_domain": data.get("cache_domain", ""),
                "taxpayer_type": data.get("taxpayer_type", ""),
                "accounting_standard": data.get("accounting_standard", ""),
                "subdomains": data.get("subdomains", []),
                "hit_count": data.get("hit_count", 0)
            })
        except:
            pass

    return templates


def clear_l2_cache():
    """清空L2缓存"""
    if CACHE_DIR.exists():
        for fp in CACHE_DIR.glob("template_*.json"):
            fp.unlink()
    print("✓ L2缓存已清空")


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def run_test():
    """运行测试"""
    print_separator("跨域L2缓存测试")

    # 清空缓存
    print("\n[前置条件] 清空所有L2缓存")
    clear_l2_cache()
    print(f"当前L2模板数量: {count_l2_templates()}")

    # 登录
    print("\n[登录] 获取访问令牌")
    token = login()
    print("✓ 登录成功")

    # 场景1：首次查询 - 创建第1个模板
    print_separator("场景1: 首次跨域查询 - 创建第1个模板")
    company = TEST_COMPANIES["TSE科技"]
    print(f"公司: TSE科技")
    print(f"  - ID: {company['id']}")
    print(f"  - 类型: {company['type']}")
    print(f"  - 准则: {company['standard']}")
    print(f"查询: {TEST_QUERY}")

    start = time.time()
    result = chat_query(token, company['id'], TEST_QUERY, thinking_mode="deep")
    elapsed = time.time() - start

    print(f"\n结果:")
    print(f"  - 成功: {result.get('success')}")
    print(f"  - 路由: {result.get('route')}")
    print(f"  - 域: {result.get('domain')}")
    print(f"  - 缓存命中: {result.get('cache_hit', False)}")
    print(f"  - 缓存来源: {result.get('cache_source', 'N/A')}")
    print(f"  - 耗时: {elapsed:.2f}s")

    if result.get('domain') == 'cross_domain':
        sub_results = result.get('sub_results', [])
        print(f"  - 子域数量: {len(sub_results)}")
        for sr in sub_results:
            print(f"    - {sr['domain']}: {len(sr.get('data', []))} 行")

    template_count = count_l2_templates()
    print(f"\n当前L2模板数量: {template_count}")
    if template_count > 0:
        print("✓ 场景1通过: 创建了第1个模板")
    else:
        print("✗ 场景1失败: 未创建模板")
        return

    # 场景2：相同查询 + 相同组合 - 命中L2缓存
    print_separator("场景2: 相同查询 + 相同组合 - 命中L2缓存")
    company = TEST_COMPANIES["创智软件"]
    print(f"公司: 创智软件")
    print(f"  - ID: {company['id']}")
    print(f"  - 类型: {company['type']}")
    print(f"  - 准则: {company['standard']}")
    print(f"查询: {TEST_QUERY}")

    start = time.time()
    result = chat_query(token, company['id'], TEST_QUERY, thinking_mode="quick")
    elapsed = time.time() - start

    print(f"\n结果:")
    print(f"  - 成功: {result.get('success')}")
    print(f"  - 缓存命中: {result.get('cache_hit', False)}")
    print(f"  - 缓存来源: {result.get('cache_source', 'N/A')}")
    print(f"  - 耗时: {elapsed:.2f}s")

    template_count = count_l2_templates()
    print(f"\n当前L2模板数量: {template_count}")

    if result.get('cache_hit') and result.get('cache_source') == 'l2':
        print("✓ 场景2通过: 命中L2缓存")
    else:
        print("✗ 场景2失败: 未命中L2缓存")

    # 场景3：相同查询 + 不同组合1 - 创建第2个模板
    print_separator("场景3: 相同查询 + 不同组合 - 创建第2个模板")
    company = TEST_COMPANIES["鑫源贸易"]
    print(f"公司: 鑫源贸易")
    print(f"  - ID: {company['id']}")
    print(f"  - 类型: {company['type']}")
    print(f"  - 准则: {company['standard']}")
    print(f"查询: {TEST_QUERY}")

    start = time.time()
    result = chat_query(token, company['id'], TEST_QUERY, thinking_mode="deep")
    elapsed = time.time() - start

    print(f"\n结果:")
    print(f"  - 成功: {result.get('success')}")
    print(f"  - 缓存命中: {result.get('cache_hit', False)}")
    print(f"  - 耗时: {elapsed:.2f}s")

    template_count = count_l2_templates()
    print(f"\n当前L2模板数量: {template_count}")

    if template_count == 2:
        print("✓ 场景3通过: 创建了第2个模板")
    else:
        print(f"✗ 场景3失败: 预期2个模板，实际{template_count}个")

    # 场景4：相同查询 + 不同组合2 - 创建第3个模板
    print_separator("场景4: 相同查询 + 不同组合 - 创建第3个模板")
    company = TEST_COMPANIES["环球机械"]
    print(f"公司: 环球机械")
    print(f"  - ID: {company['id']}")
    print(f"  - 类型: {company['type']}")
    print(f"  - 准则: {company['standard']}")
    print(f"查询: {TEST_QUERY}")

    start = time.time()
    result = chat_query(token, company['id'], TEST_QUERY, thinking_mode="deep")
    elapsed = time.time() - start

    print(f"\n结果:")
    print(f"  - 成功: {result.get('success')}")
    print(f"  - 缓存命中: {result.get('cache_hit', False)}")
    print(f"  - 耗时: {elapsed:.2f}s")

    template_count = count_l2_templates()
    print(f"\n当前L2模板数量: {template_count}")

    if template_count == 3:
        print("✓ 场景4通过: 创建了第3个模板")
    else:
        print(f"✗ 场景4失败: 预期3个模板，实际{template_count}个")

    # 场景5：验证所有组合都能命中缓存
    print_separator("场景5: 验证所有组合都能命中缓存")

    for name, company in TEST_COMPANIES.items():
        if name == "大华智能制造":  # 跳过没有数据的公司
            continue

        print(f"\n测试公司: {name}")
        print(f"  - 类型: {company['type']}")
        print(f"  - 准则: {company['standard']}")

        start = time.time()
        result = chat_query(token, company['id'], TEST_QUERY, thinking_mode="quick")
        elapsed = time.time() - start

        cache_hit = result.get('cache_hit', False)
        cache_source = result.get('cache_source', 'N/A')

        print(f"  - 缓存命中: {cache_hit}")
        print(f"  - 缓存来源: {cache_source}")
        print(f"  - 耗时: {elapsed:.2f}s")

        if cache_hit and cache_source == 'l2':
            print(f"  ✓ {name} 命中L2缓存")
        else:
            print(f"  ✗ {name} 未命中L2缓存")

    # 总结
    print_separator("测试总结")
    templates = get_l2_template_info()
    print(f"\n总共创建了 {len(templates)} 个L2模板:")
    for i, t in enumerate(templates, 1):
        print(f"\n模板 {i}:")
        print(f"  - 文件: {t['file']}")
        print(f"  - 查询: {t['query']}")
        print(f"  - 域: {t['domain']}")
        print(f"  - 缓存域: {t['cache_domain']}")
        print(f"  - 纳税人类型: {t['taxpayer_type']}")
        print(f"  - 会计准则: {t['accounting_standard']}")
        print(f"  - 子域: {', '.join(t['subdomains'])}")
        print(f"  - 命中次数: {t['hit_count']}")

    print("\n" + "=" * 80)
    print("测试完成!")


if __name__ == "__main__":
    run_test()
