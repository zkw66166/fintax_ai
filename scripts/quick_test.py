"""Quick test script - run a few queries to populate cache and history"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

# Login
response = requests.post(f"{API_BASE}/api/auth/login", json={
    "username": "user1",
    "password": "123456"
})
token = response.json()['access_token']
print(f"✓ Logged in")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Test queries (using correct taxpayer_ids)
queries = [
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年年底的银行存款余额还有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每个月末的现金余额变化情况"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年3月底的应收账款有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月的净利润是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年12月的销项税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年年底的银行存款余额还有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年3月底的应收账款有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月的净利润是多少？"),
]

success = 0
for company_id, query in queries:
    print(f"\n{query[:40]}...")

    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": "quick",
        "conversation_enabled": False,
        "conversation_depth": 2
    }

    response = requests.post(f"{API_BASE}/api/chat", json=payload, headers=headers, stream=True, timeout=30)

    # Collect SSE (proper format: event: xxx\ndata: {...}\n\n)
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
                        if data.get('success'):
                            success += 1
                            print(f"  ✓ Success (route: {data.get('route', 'unknown')})")
                        else:
                            print(f"  ✗ Failed: {data.get('error', 'Unknown')}")
                        break
                except Exception as e:
                    print(f"  ✗ Parse error: {e}")

    time.sleep(0.5)

print(f"\n\nCompleted: {success}/{len(queries)} successful")
