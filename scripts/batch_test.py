"""Simple batch test - runs all queries and reports results"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

# Login
response = requests.post(f"{API_BASE}/api/auth/login", json={"username": "user1", "password": "123456"})
token = response.json()['access_token']
print("✓ Logged in\n")

# All test queries with correct company IDs
queries = [
    # TSE科技有限公司 - Single domain (27 queries)
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年年底的银行存款余额还有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每个月末的现金余额变化情况"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年第一季度各月管理费用和财务费用的发生额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年3月底的应收账款有多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每个季度末的短期借款是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司近两年每年末的总资产和总负债"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月的净利润是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各季度的营业收入"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年上半年的营业收入、营业成本和销售费用"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年5月的经营现金流净额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每个月的投资活动现金流出"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年第一季度各月的经营流入和经营流出"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年12月的销项税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年各季度的应交增值税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每月增值税申报的销售额、销项税和进项税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司2023年汇算清缴的应纳税所得额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每个季度预缴的所得税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司2023年各季度申报的营业收入、营业成本和利润总额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年12月采购发票的进项税总额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每个月的采购金额（不含税）"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各季度采购发票的金额和税额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月销售发票的总销售额（不含税）"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各月的销项税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年第一季度各月销售发票的金额和税额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年年底的资产负债率是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每月的增值税税负率走势"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各季度的销售收现比和应收账款周转率"),

    # TSE科技有限公司 - Cross domain (15 queries - subset)
    ("91310115MA2KZZZZZZ", "TSE科技有限公司上个月进项税和销项税的比例是多少？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年一季度的所得税费用占利润总额的比重？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年3月底的银行存款余额相当于当月营业收入的几倍？"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每月的进项税与销项税之比"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各季度所得税费用占利润总额的比例"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司23-25年营业收入、销项税和经营现金流净额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年各季度总资产、总负债和净利润情况"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每月采购发票金额、销售发票金额和营业成本"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年每月银行存款余额、应收账款余额和短期借款余额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各季度应纳所得税额、利润总额和支付的各项税费"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司2023-25年毛利率、资产负债率和营业收入"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年每月销售收现、营业收入和应收账款余额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年各月进项税额、销项税额和应交增值税"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司去年各月的营业收入、净利润、经营活动现金流净额、资产总计、销项税额、应纳所得税额"),
    ("91310115MA2KZZZZZZ", "TSE科技有限公司今年各季度的营业收入、营业成本、利润总额、所得税费用、经营活动现金流净额、投资活动现金流净额、资产总计、负债合计、应交增值税、进项税额"),

    # 大华智能制造厂 - Single domain (27 queries)
    ("91330200MA2KYYYYYY", "大华智能制造厂去年年底的银行存款余额还有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年每个月末的现金余额变化情况"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年第一季度各月管理费用和财务费用的发生额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年3月底的应收账款有多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每个季度末的短期借款是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂近两年每年末的总资产和总负债"),
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月的净利润是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各季度的营业收入"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年上半年的营业收入、营业成本和销售费用"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年5月的经营现金流净额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每个月的投资活动现金流出"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年第一季度各月的经营流入和经营流出"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年12月的销项税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年各季度的应交增值税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每月增值税申报的销售额、销项税和进项税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂2023年汇算清缴的应纳税所得额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每个季度预缴的所得税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂2023年各季度申报的营业收入、营业成本和利润总额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年12月采购发票的进项税总额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年每个月的采购金额（不含税）"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各季度采购发票的金额和税额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月销售发票的总销售额（不含税）"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各月的销项税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年第一季度各月销售发票的金额和税额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年年底的资产负债率是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年每月的增值税税负率走势"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各季度的销售收现比和应收账款周转率"),

    # 大华智能制造厂 - Cross domain (15 queries - subset)
    ("91330200MA2KYYYYYY", "大华智能制造厂上个月进项税和销项税的比例是多少？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年一季度的所得税费用占利润总额的比重？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年3月底的银行存款余额相当于当月营业收入的几倍？"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年每月的进项税与销项税之比"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各季度所得税费用占利润总额的比例"),
    ("91330200MA2KYYYYYY", "大华智能制造厂23-25年营业收入、销项税和经营现金流净额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年各季度总资产、总负债和净利润情况"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每月采购发票金额、销售发票金额和营业成本"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年每月银行存款余额、应收账款余额和短期借款余额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各季度应纳所得税额、利润总额和支付的各项税费"),
    ("91330200MA2KYYYYYY", "大华智能制造厂2023-25年毛利率、资产负债率和营业收入"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年每月销售收现、营业收入和应收账款余额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年各月进项税额、销项税额和应交增值税"),
    ("91330200MA2KYYYYYY", "大华智能制造厂去年各月的营业收入、净利润、经营活动现金流净额、资产总计、销项税额、应纳所得税额"),
    ("91330200MA2KYYYYYY", "大华智能制造厂今年各季度的营业收入、营业成本、利润总额、所得税费用、经营活动现金流净额、投资活动现金流净额、资产总计、负债合计、应交增值税、进项税额"),
]

print(f"Total queries to run: {len(queries)}\n")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
success = 0
failed = 0

for i, (company_id, query) in enumerate(queries, 1):
    company_name = "TSE" if "TSE" in query else "DH"
    print(f"[{i}/{len(queries)}] {company_name}: {query[:50]}...", end=" ")

    payload = {
        "query": query,
        "company_id": company_id,
        "thinking_mode": "quick",
        "conversation_enabled": False,
        "conversation_depth": 2
    }

    try:
        response = requests.post(f"{API_BASE}/api/chat", json=payload, headers=headers, stream=True, timeout=60)

        current_event = None
        query_success = False
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('event: '):
                    current_event = line_str[7:]
                elif line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        if current_event == 'done':
                            query_success = data.get('success', False)
                            break
                    except:
                        pass

        if query_success:
            success += 1
            print("✓")
        else:
            failed += 1
            print("✗")

    except Exception as e:
        failed += 1
        print(f"✗ ({str(e)[:30]})")

    time.sleep(0.2)

print(f"\n{'='*60}")
print(f"Results: {success}/{len(queries)} successful ({success/len(queries)*100:.1f}%)")
print(f"Failed: {failed}")
print(f"{'='*60}")
