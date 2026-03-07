"""
Comprehensive test script - runs all 57 test queries (27 single-domain + 30 cross-domain)
for both TSE科技有限公司 and 大华智能制造厂
"""
import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000"

# Company ID mapping
COMPANIES = {
    'TSE科技有限公司': '91310115MA2KZZZZZZ',
    '大华智能制造厂': '91330200MA2KYYYYYY'
}

# Single-domain queries (27 per company)
SINGLE_DOMAIN_QUERIES = {
    '科目余额表': [
        '{company}去年年底的银行存款余额还有多少？',
        '{company}今年每个月末的现金余额变化情况',
        '{company}去年第一季度各月管理费用和财务费用的发生额',
    ],
    '资产负债表': [
        '{company}今年3月底的应收账款有多少？',
        '{company}去年每个季度末的短期借款是多少？',
        '{company}近两年每年末的总资产和总负债',
    ],
    '利润表': [
        '{company}上个月的净利润是多少？',
        '{company}去年各季度的营业收入',
        '{company}今年上半年的营业收入、营业成本和销售费用',
    ],
    '现金流量表': [
        '{company}今年5月的经营现金流净额',
        '{company}去年每个月的投资活动现金流出',
        '{company}今年第一季度各月的经营流入和经营流出',
    ],
    '增值税申报表': [
        '{company}去年12月的销项税',
        '{company}今年各季度的应交增值税',
        '{company}去年每月增值税申报的销售额、销项税和进项税',
    ],
    '企业所得税申报表': [
        '{company}2023年汇算清缴的应纳税所得额',
        '{company}去年每个季度预缴的所得税',
        '{company}2023年各季度申报的营业收入、营业成本和利润总额',
    ],
    '进项发票': [
        '{company}去年12月采购发票的进项税总额',
        '{company}今年每个月的采购金额（不含税）',
        '{company}去年各季度采购发票的金额和税额',
    ],
    '销项发票': [
        '{company}上个月销售发票的总销售额（不含税）',
        '{company}去年各月的销项税',
        '{company}今年第一季度各月销售发票的金额和税额',
    ],
    '关键财务指标': [
        '{company}去年年底的资产负债率是多少？',
        '{company}今年每月的增值税税负率走势',
        '{company}去年各季度的销售收现比和应收账款周转率',
    ],
}

# Cross-domain queries (30 per company)
CROSS_DOMAIN_QUERIES = [
    # 跨域单指标单期间 (10)
    '{company}上个月进项税和销项税的比例是多少？',
    '{company}今年一季度的所得税费用占利润总额的比重？',
    '{company}今年3月底的银行存款余额相当于当月营业收入的几倍？',
    '{company}上个月销项税占营业收入的比例？',
    '{company}去年全年所得税费用与经营现金流净额的比率？',
    '{company}去年12月的（销项税额 - 进项税额）与应纳税额的比值？',
    '{company}今年5月的销售收现、营业收入和应收账款余额的比值？',
    '{company}25年第四季度的采购金额、销售金额、存货增加额和经营现金流出的关系？',
    '{company}去年12月的（银行存款余额 + 应收账款余额 - 短期借款余额）与（销项税额 + 进项税额）的比值？',
    '{company}2025全年的（所得税费用 + 增值税应纳税额）与利润总额的比值？',

    # 跨域单指标多期间 (10)
    '{company}今年每月的进项税与销项税之比',
    '{company}去年各季度所得税费用占利润总额的比例',
    '{company}今年每月末的银行存款余额占当月营业收入的比重',
    '{company}今年每月销项税占营业收入的比例',
    '{company}去年各月所得税费用与经营现金流净额的比率',
    '{company}去年各月的（销项税额 - 进项税额）与应纳税额的比值',
    '{company}今年各月的销售收现、营业收入和应收账款余额的比值',
    '{company}去年各季度的采购金额、销售金额、存货增加额和经营现金流出的关系',
    '{company}今年各月的（银行存款余额 + 应收账款余额 - 短期借款余额）与（销项税额 + 进项税额）的比值',
    '{company}去年各月的（所得税费用 + 增值税应纳税额）与利润总额的比值',

    # 跨域多指标多期间 (10)
    '{company}23-25年营业收入、销项税和经营现金流净额',
    '{company}今年各季度总资产、总负债和净利润情况',
    '{company}去年每月采购发票金额、销售发票金额和营业成本',
    '{company}今年每月银行存款余额、应收账款余额和短期借款余额',
    '{company}去年各季度应纳所得税额、利润总额和支付的各项税费',
    '{company}2023-25年毛利率、资产负债率和营业收入',
    '{company}去年每月销售收现、营业收入和应收账款余额',
    '{company}今年各月进项税额、销项税额和应交增值税',
    '{company}去年各月的营业收入、净利润、经营活动现金流净额、资产总计、销项税额、应纳所得税额',
    '{company}今年各季度的营业收入、营业成本、利润总额、所得税费用、经营活动现金流净额、投资活动现金流净额、资产总计、负债合计、应交增值税、进项税额',
]


def login():
    """Login and get JWT token"""
    response = requests.post(f"{API_BASE}/api/auth/login", json={
        "username": "user1",
        "password": "123456"
    })
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Login failed: {response.text}")


def send_query(token, query, company_id):
    """Send query and return success status"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": "quick",
        "conversation_enabled": False,
        "conversation_depth": 2
    }

    try:
        response = requests.post(f"{API_BASE}/api/chat", json=payload, headers=headers, stream=True, timeout=60)

        # Parse SSE
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
                            return data.get('success', False), data.get('route', 'unknown'), data.get('error', '')
                    except:
                        pass

        return False, 'unknown', 'No response'

    except Exception as e:
        return False, 'error', str(e)


def main():
    print("=" * 80)
    print("Fintax AI Comprehensive Test Suite")
    print("=" * 80)
    print()

    # Login
    print("Logging in...")
    token = login()
    print("✓ Login successful\n")

    results = {
        'TSE科技有限公司': {'single': {}, 'cross': []},
        '大华智能制造厂': {'single': {}, 'cross': []}
    }

    total_queries = 0
    success_count = 0

    # Run tests for each company
    for company_name, company_id in COMPANIES.items():
        print(f"\n{'=' * 80}")
        print(f"Testing: {company_name}")
        print(f"{'=' * 80}\n")

        # Single-domain queries
        print("--- Single-Domain Queries ---\n")
        for domain, query_templates in SINGLE_DOMAIN_QUERIES.items():
            print(f"{domain}:")
            results[company_name]['single'][domain] = []

            for template in query_templates:
                query = template.format(company=company_name)
                total_queries += 1

                success, route, error = send_query(token, query, company_id)

                if success:
                    success_count += 1
                    print(f"  ✓ {query[:60]}...")
                else:
                    print(f"  ✗ {query[:60]}... (Error: {error[:30]})")

                results[company_name]['single'][domain].append({
                    'query': query,
                    'success': success,
                    'route': route,
                    'error': error if not success else None
                })

                time.sleep(0.3)  # Brief pause

            print()

        # Cross-domain queries
        print("\n--- Cross-Domain Queries ---\n")
        for template in CROSS_DOMAIN_QUERIES:
            query = template.format(company=company_name)
            total_queries += 1

            success, route, error = send_query(token, query, company_id)

            if success:
                success_count += 1
                print(f"  ✓ {query[:60]}...")
            else:
                print(f"  ✗ {query[:60]}... (Error: {error[:30]})")

            results[company_name]['cross'].append({
                'query': query,
                'success': success,
                'route': route,
                'error': error if not success else None
            })

            time.sleep(0.3)

    # Summary
    print(f"\n\n{'=' * 80}")
    print("Test Summary")
    print(f"{'=' * 80}")
    print(f"Total queries: {total_queries}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_queries - success_count}")
    print(f"Success rate: {success_count/total_queries*100:.1f}%")
    print()

    # Per-company breakdown
    for company_name in COMPANIES.keys():
        single_success = sum(1 for domain in results[company_name]['single'].values()
                           for q in domain if q['success'])
        cross_success = sum(1 for q in results[company_name]['cross'] if q['success'])
        total = single_success + cross_success
        print(f"{company_name}: {total}/57 successful ({total/57*100:.1f}%)")
        print(f"  - Single-domain: {single_success}/27")
        print(f"  - Cross-domain: {cross_success}/30")

    # Save results
    output_file = Path(__file__).parent.parent / 'test_results_comprehensive.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Results saved to: {output_file}")

    # Check cache and history
    cache_dir = Path(__file__).parent.parent / 'cache'
    history_file = Path(__file__).parent.parent / 'query_history.json'

    if cache_dir.exists():
        cache_count = len(list(cache_dir.glob('*.json')))
        print(f"✓ Cache files: {cache_count}")

    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
            print(f"✓ History entries: {len(history)}")


if __name__ == '__main__':
    main()
