"""
批量测试查询脚本 - 生成 query_history.json 和 cache 文件
"""
import requests
import json
import time
from pathlib import Path

# API endpoint
API_BASE = "http://localhost:8000"
LOGIN_URL = f"{API_BASE}/api/auth/login"
CHAT_URL = f"{API_BASE}/api/chat"

# Test queries organized by domain and company
TEST_QUERIES = {
    'TSE科技有限公司': {
        '科目余额表': [
            'TSE科技有限公司去年年底的银行存款余额还有多少？',
            'TSE科技有限公司今年每个月末的现金余额变化情况',
            'TSE科技有限公司去年第一季度各月管理费用和财务费用的发生额',
        ],
        '资产负债表': [
            'TSE科技有限公司今年3月底的应收账款有多少？',
            'TSE科技有限公司去年每个季度末的短期借款是多少？',
            'TSE科技有限公司近两年每年末的总资产和总负债',
        ],
        '利润表': [
            'TSE科技有限公司上个月的净利润是多少？',
            'TSE科技有限公司去年各季度的营业收入',
            'TSE科技有限公司今年上半年的营业收入、营业成本和销售费用',
        ],
        '现金流量表': [
            'TSE科技有限公司今年5月的经营现金流净额',
            'TSE科技有限公司去年每个月的投资活动现金流出',
            'TSE科技有限公司今年第一季度各月的经营流入和经营流出',
        ],
        '增值税申报表': [
            'TSE科技有限公司去年12月的销项税',
            'TSE科技有限公司今年各季度的应交增值税',
            'TSE科技有限公司去年每月增值税申报的销售额、销项税和进项税',
        ],
        '企业所得税申报表': [
            'TSE科技有限公司2023年汇算清缴的应纳税所得额',
            'TSE科技有限公司去年每个季度预缴的所得税',
            'TSE科技有限公司2023年各季度申报的营业收入、营业成本和利润总额',
        ],
        '进项发票': [
            'TSE科技有限公司去年12月采购发票的进项税总额',
            'TSE科技有限公司今年每个月的采购金额（不含税）',
            'TSE科技有限公司去年各季度采购发票的金额和税额',
        ],
        '销项发票': [
            'TSE科技有限公司上个月销售发票的总销售额（不含税）',
            'TSE科技有限公司去年各月的销项税',
            'TSE科技有限公司今年第一季度各月销售发票的金额和税额',
        ],
        '关键财务指标': [
            'TSE科技有限公司去年年底的资产负债率是多少？',
            'TSE科技有限公司今年每月的增值税税负率走势',
            'TSE科技有限公司去年各季度的销售收现比和应收账款周转率',
        ],
    },
    '大华智能制造厂': {
        '科目余额表': [
            '大华智能制造厂去年年底的银行存款余额还有多少？',
            '大华智能制造厂今年每个月末的现金余额变化情况',
            '大华智能制造厂去年第一季度各月管理费用和财务费用的发生额',
        ],
        '资产负债表': [
            '大华智能制造厂今年3月底的应收账款有多少？',
            '大华智能制造厂去年每个季度末的短期借款是多少？',
            '大华智能制造厂近两年每年末的总资产和总负债',
        ],
        '利润表': [
            '大华智能制造厂上个月的净利润是多少？',
            '大华智能制造厂去年各季度的营业收入',
            '大华智能制造厂今年上半年的营业收入、营业成本和销售费用',
        ],
        '现金流量表': [
            '大华智能制造厂今年5月的经营现金流净额',
            '大华智能制造厂去年每个月的投资活动现金流出',
            '大华智能制造厂今年第一季度各月的经营流入和经营流出',
        ],
        '增值税申报表': [
            '大华智能制造厂去年12月的销项税',
            '大华智能制造厂今年各季度的应交增值税',
            '大华智能制造厂去年每月增值税申报的销售额、销项税和进项税',
        ],
        '企业所得税申报表': [
            '大华智能制造厂2023年汇算清缴的应纳税所得额',
            '大华智能制造厂去年每个季度预缴的所得税',
            '大华智能制造厂2023年各季度申报的营业收入、营业成本和利润总额',
        ],
        '进项发票': [
            '大华智能制造厂去年12月采购发票的进项税总额',
            '大华智能制造厂今年每个月的采购金额（不含税）',
            '大华智能制造厂去年各季度采购发票的金额和税额',
        ],
        '销项发票': [
            '大华智能制造厂上个月销售发票的总销售额（不含税）',
            '大华智能制造厂去年各月的销项税',
            '大华智能制造厂今年第一季度各月销售发票的金额和税额',
        ],
        '关键财务指标': [
            '大华智能制造厂去年年底的资产负债率是多少？',
            '大华智能制造厂今年每月的增值税税负率走势',
            '大华智能制造厂去年各季度的销售收现比和应收账款周转率',
        ],
    }
}

# Cross-domain queries
CROSS_DOMAIN_QUERIES = {
    'TSE科技有限公司': [
        # 跨域单指标单期间
        'TSE科技有限公司上个月进项税和销项税的比例是多少？',
        'TSE科技有限公司今年一季度的所得税费用占利润总额的比重？',
        'TSE科技有限公司今年3月底的银行存款余额相当于当月营业收入的几倍？',
        'TSE科技有限公司上个月销项税占营业收入的比例？',
        'TSE科技有限公司去年全年所得税费用与经营现金流净额的比率？',

        # 跨域单指标多期间
        'TSE科技有限公司今年每月的进项税与销项税之比',
        'TSE科技有限公司去年各季度所得税费用占利润总额的比例',
        'TSE科技有限公司今年每月末的银行存款余额占当月营业收入的比重',

        # 跨域多指标多期间
        'TSE科技有限公司23-25年营业收入、销项税和经营现金流净额',
        'TSE科技有限公司今年各季度总资产、总负债和净利润情况',
        'TSE科技有限公司去年每月采购发票金额、销售发票金额和营业成本',
    ],
    '大华智能制造厂': [
        # 跨域单指标单期间
        '大华智能制造厂上个月进项税和销项税的比例是多少？',
        '大华智能制造厂今年一季度的所得税费用占利润总额的比重？',
        '大华智能制造厂今年3月底的银行存款余额相当于当月营业收入的几倍？',
        '大华智能制造厂上个月销项税占营业收入的比例？',
        '大华智能制造厂去年全年所得税费用与经营现金流净额的比率？',

        # 跨域单指标多期间
        '大华智能制造厂今年每月的进项税与销项税之比',
        '大华智能制造厂去年各季度所得税费用占利润总额的比例',
        '大华智能制造厂今年每月末的银行存款余额占当月营业收入的比重',

        # 跨域多指标多期间
        '大华智能制造厂23-25年营业收入、销项税和经营现金流净额',
        '大华智能制造厂今年各季度总资产、总负债和净利润情况',
        '大华智能制造厂去年每月采购发票金额、销售发票金额和营业成本',
    ]
}


def login():
    """Login and get JWT token"""
    response = requests.post(LOGIN_URL, json={
        "username": "user1",
        "password": "123456"
    })
    if response.status_code == 200:
        data = response.json()
        return data['access_token']
    else:
        raise Exception(f"Login failed: {response.text}")


def send_query(token, query, company_id, thinking_mode='quick'):
    """Send query to chat endpoint"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": thinking_mode,
        "conversation_enabled": False,
        "conversation_depth": 2
    }

    response = requests.post(CHAT_URL, json=payload, headers=headers, stream=True)

    # Collect SSE events
    result = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    if data.get('type') == 'done':
                        result = data.get('result', {})
                        break
                except json.JSONDecodeError:
                    pass

    return result


def main():
    print("=== Fintax AI Test Query Runner ===\n")

    # Login
    print("Logging in...")
    token = login()
    print("✓ Login successful\n")

    # Company ID mapping
    company_ids = {
        'TSE科技有限公司': 'TSE001',
        '大华智能制造厂': 'DH002'
    }

    results = []
    total_queries = 0
    success_count = 0

    # Run single-domain queries
    for company, domains in TEST_QUERIES.items():
        company_id = company_ids[company]
        print(f"\n{'='*60}")
        print(f"Testing: {company} ({company_id})")
        print(f"{'='*60}\n")

        for domain, queries in domains.items():
            print(f"\n--- {domain} ---")
            for i, query in enumerate(queries, 1):
                total_queries += 1
                print(f"{i}. {query[:50]}...")

                try:
                    result = send_query(token, query, company_id)
                    if result and result.get('success'):
                        success_count += 1
                        print(f"   ✓ Success (route: {result.get('route', 'unknown')})")
                    else:
                        print(f"   ✗ Failed: {result.get('error', 'Unknown error') if result else 'No result'}")

                    results.append({
                        'company': company,
                        'domain': domain,
                        'query': query,
                        'success': result.get('success', False) if result else False,
                        'route': result.get('route', 'unknown') if result else 'unknown'
                    })

                    time.sleep(0.5)  # Brief pause

                except Exception as e:
                    print(f"   ✗ Error: {e}")
                    results.append({
                        'company': company,
                        'domain': domain,
                        'query': query,
                        'success': False,
                        'error': str(e)
                    })

    # Run cross-domain queries
    print(f"\n\n{'='*60}")
    print("Cross-Domain Queries")
    print(f"{'='*60}\n")

    for company, queries in CROSS_DOMAIN_QUERIES.items():
        company_id = company_ids[company]
        print(f"\n--- {company} ---")

        for i, query in enumerate(queries, 1):
            total_queries += 1
            print(f"{i}. {query[:50]}...")

            try:
                result = send_query(token, query, company_id)
                if result and result.get('success'):
                    success_count += 1
                    print(f"   ✓ Success (route: {result.get('route', 'unknown')})")
                else:
                    print(f"   ✗ Failed: {result.get('error', 'Unknown error') if result else 'No result'}")

                results.append({
                    'company': company,
                    'domain': 'cross_domain',
                    'query': query,
                    'success': result.get('success', False) if result else False,
                    'route': result.get('route', 'unknown') if result else 'unknown'
                })

                time.sleep(0.5)

            except Exception as e:
                print(f"   ✗ Error: {e}")
                results.append({
                    'company': company,
                    'domain': 'cross_domain',
                    'query': query,
                    'success': False,
                    'error': str(e)
                })

    # Summary
    print(f"\n\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Total queries: {total_queries}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_queries - success_count}")
    print(f"Success rate: {success_count/total_queries*100:.1f}%")

    # Save results
    output_file = Path(__file__).parent.parent / 'test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    # Check cache and history files
    cache_dir = Path(__file__).parent.parent / 'cache'
    history_file = Path(__file__).parent.parent / 'query_history.json'

    if cache_dir.exists():
        cache_count = len(list(cache_dir.glob('*.json')))
        print(f"Cache files generated: {cache_count}")

    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            print(f"History entries: {len(history)}")


if __name__ == '__main__':
    main()
