"""
测试脚本 - 带历史记录保存功能
运行测试查询并保存到前端历史记录
"""
import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

# 测试查询（精简版，每个公司各10个）
TEST_QUERIES = [
    # TSE科技有限公司
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年年底的银行存款余额还有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年3月底的应收账款有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月的净利润是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年12月的销项税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司2023年汇算清缴的应纳税所得额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年年底的资产负债率是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月进项税和销项税的比例是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年一季度的所得税费用占利润总额的比重？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司23-25年营业收入、销项税和经营现金流净额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年各季度总资产、总负债和净利润情况"),

    # 大华智能制造厂
    ("91330200MA2KYYYYYY", "大华智能制造厂去年年底的银行存款余额还有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年3月底的应收账款有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月的净利润是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年12月的销项税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂2023年汇算清缴的应纳税所得额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年年底的资产负债率是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月进项税和销项税的比例是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年一季度的所得税费用占利润总额的比重？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂23-25年营业收入、销项税和经营现金流净额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年各季度总资产、总负债和净利润情况"),
]

def login():
    """登录获取 token"""
    response = requests.post(f"{API_BASE}/api/auth/login", json={
        "username": "user1",
        "password": "123456"
    })
    return response.json()['access_token']

def send_query_and_save_history(token, query, company_id):
    """发送查询并保存到历史记录"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. 执行查询
    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": "quick",
        "conversation_enabled": False,
        "conversation_depth": 2
    }

    result = None
    route = "unknown"

    try:
        response = requests.post(f"{API_BASE}/api/chat", json=payload, headers=headers, stream=True, timeout=60)

        # 解析 SSE 响应
        current_event = None
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('event: '):
                    current_event = line_str[7:]
                elif line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if current_event == 'done':
                            result = data
                            route = data.get('route', 'unknown')
                            break
                    except:
                        pass

        if not result:
            return False, "No result"

        # 2. 保存到历史记录
        history_entry = {
            "query": query,
            "company_id": company_id,
            "timestamp": datetime.now().strftime("%p%I:%M:%S"),  # 格式: 上午11:30:45
            "route": route,
            "response_mode": "detailed",
            "thinking_mode": "quick",
            "conversation_enabled": False,
            "conversation_depth": 2,
            "conversation_history": [],
            "result": result
        }

        save_response = requests.post(
            f"{API_BASE}/api/chat/history",
            json=history_entry,
            headers=headers,
            timeout=10
        )

        if save_response.status_code == 200:
            return True, route
        else:
            return False, f"History save failed: {save_response.status_code}"

    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("测试查询执行 - 带历史记录保存")
    print("=" * 80)
    print()

    # 登录
    print("登录中...")
    token = login()
    print("✓ 登录成功\n")

    success = 0
    failed = 0

    for i, (company_id, query) in enumerate(TEST_QUERIES, 1):
        company_name = "TSE" if "TSE" in query else "大华"
        print(f"[{i}/{len(TEST_QUERIES)}] {company_name}: {query[:50]}...", end=" ")

        ok, info = send_query_and_save_history(token, query, company_id)

        if ok:
            success += 1
            print(f"✓ (route: {info})")
        else:
            failed += 1
            print(f"✗ ({info[:30]})")

        time.sleep(0.3)

    print(f"\n{'='*80}")
    print(f"结果: {success}/{len(TEST_QUERIES)} 成功 ({success/len(TEST_QUERIES)*100:.1f}%)")
    print(f"失败: {failed}")
    print(f"{'='*80}")
    print("\n✓ 查询已保存到历史记录，可在前端查看")

if __name__ == '__main__':
    main()
