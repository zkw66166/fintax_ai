"""综合测试：57个用户问题全域验证
覆盖9个数据域 × 单域/跨域 × 全链路验证
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mvp_pipeline import run_pipeline
from config.settings import DB_PATH

# 默认企业名前缀
PREFIX = "华兴科技"

# ============================================================
# 57个测试问题定义
# ============================================================
TEST_CASES = [
    # ── 一、单域问题（27个）──
    # 科目余额
    {"id": "SD-AB-01", "query": f"{PREFIX}去年年底的银行存款余额还有多少？",
     "expected_domain": "account_balance", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-AB-02", "query": f"{PREFIX}今年每个月末的现金余额变化情况",
     "expected_domain": "account_balance", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-AB-03", "query": f"{PREFIX}去年第一季度各月管理费用和财务费用的发生额",
     "expected_domain": "account_balance", "expected_path": "standard", "min_rows": 1},

    # 资产负债表
    {"id": "SD-BS-01", "query": f"{PREFIX}今年3月底的应收账款有多少？",
     "expected_domain": "balance_sheet", "expected_path": "standard", "min_rows": 0},
    {"id": "SD-BS-02", "query": f"{PREFIX}去年每个季度末的短期借款是多少？",
     "expected_domain": "balance_sheet", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-BS-03", "query": f"{PREFIX}近两年每年末的总资产和总负债",
     "expected_domain": "balance_sheet", "expected_path": "standard", "min_rows": 1},

    # 利润表
    {"id": "SD-PF-01", "query": f"{PREFIX}上个月的净利润是多少？",
     "expected_domain": "profit", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-PF-02", "query": f"{PREFIX}去年各季度的营业收入",
     "expected_domain": "profit", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-PF-03", "query": f"{PREFIX}今年上半年的营业收入、营业成本和销售费用",
     "expected_domain": "profit", "expected_path": "standard", "min_rows": 0},

    # 现金流量表
    {"id": "SD-CF-01", "query": f"{PREFIX}今年5月的经营现金流净额",
     "expected_domain": "cash_flow", "expected_path": "standard", "min_rows": 0},
    {"id": "SD-CF-02", "query": f"{PREFIX}去年每个月的投资活动现金流出",
     "expected_domain": "cash_flow", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-CF-03", "query": f"{PREFIX}今年第一季度各月的经营流入和经营流出",
     "expected_domain": "cash_flow", "expected_path": "standard", "min_rows": 1},

    # VAT
    {"id": "SD-VAT-01", "query": f"{PREFIX}去年12月的销项税",
     "expected_domain": "vat", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-VAT-02", "query": f"{PREFIX}今年各季度的应交增值税",
     "expected_domain": "vat", "expected_path": "standard", "min_rows": 0},
    {"id": "SD-VAT-03", "query": f"{PREFIX}去年每月增值税申报的销售额、销项税和进项税",
     "expected_domain": "vat", "expected_path": "standard", "min_rows": 1},

    # EIT
    {"id": "SD-EIT-01", "query": f"{PREFIX}2023年汇算清缴的应纳税所得额",
     "expected_domain": "eit", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-EIT-02", "query": f"{PREFIX}去年每个季度预缴的所得税",
     "expected_domain": "eit", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-EIT-03", "query": f"{PREFIX}2023年各季度申报的营业收入、营业成本和利润总额",
     "expected_domain": "eit", "expected_path": "standard", "min_rows": 1},

    # 发票-进项
    {"id": "SD-INV-P-01", "query": f"{PREFIX}去年12月采购发票的进项税总额",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 1,
     "allow_cross_domain": True},
    {"id": "SD-INV-P-02", "query": f"{PREFIX}今年每个月的采购金额（不含税）",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-INV-P-03", "query": f"{PREFIX}去年各季度采购发票的金额和税额",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 0},

    # 发票-销项
    {"id": "SD-INV-S-01", "query": f"{PREFIX}上个月销售发票的总销售额（不含税）",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-INV-S-02", "query": f"{PREFIX}去年各月的销项发票税额",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 1},
    {"id": "SD-INV-S-03", "query": f"{PREFIX}今年第一季度各月销售发票的金额和税额",
     "expected_domain": "invoice", "expected_path": "standard", "min_rows": 1},

    # 财务指标
    {"id": "SD-FM-01", "query": f"{PREFIX}去年年底的资产负债率是多少？",
     "expected_domain": "financial_metrics", "expected_path": "metric", "min_rows": 1},
    {"id": "SD-FM-02", "query": f"{PREFIX}今年每月的增值税税负率走势",
     "expected_domain": "financial_metrics", "expected_path": "standard", "min_rows": 1,
     "allow_cross_domain": True},
    {"id": "SD-FM-03", "query": f"{PREFIX}去年各季度的销售收现比和应收账款周转率",
     "expected_domain": "financial_metrics", "expected_path": "standard", "min_rows": 1},

    # ── 二、跨域问题（30个）──
    # 单指标单期间
    {"id": "XD-S1-01", "query": f"{PREFIX}上个月进项发票税额和销项发票税额的比例",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1,
     "allow_single_domain": True},
    {"id": "XD-S1-02", "query": f"{PREFIX}今年一季度的所得税费用占利润总额的比重",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0,
     "allow_single_domain": True},
    {"id": "XD-S1-03", "query": f"{PREFIX}今年3月底银行存款余额相当于当月营业收入几倍",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0},
    {"id": "XD-S1-04", "query": f"{PREFIX}上个月销项发票税额占营业收入的比例",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-S1-05", "query": f"{PREFIX}去年全年所得税费用与经营现金流净额的比率",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-S1-06", "query": f"{PREFIX}去年12月销项发票税额减进项发票税额与增值税应纳税额的比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-S1-07", "query": f"{PREFIX}今年5月销售收现、营业收入和应收账款余额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0},
    {"id": "XD-S1-08", "query": f"{PREFIX}2025年第四季度采购金额、销售金额、存货和经营现金流出",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-S1-09", "query": f"{PREFIX}去年12月银行存款加应收账款减短期借款与销项税加进项税的比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-S1-10", "query": f"{PREFIX}2025全年所得税加增值税与利润总额的比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},

    # 单指标多期间
    {"id": "XD-M1-01", "query": f"{PREFIX}今年每月进项发票税额与销项发票税额之比",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1,
     "allow_single_domain": True},
    {"id": "XD-M1-02", "query": f"{PREFIX}去年各季度所得税费用占利润总额比例",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1,
     "allow_single_domain": True},
    {"id": "XD-M1-03", "query": f"{PREFIX}今年每月末银行存款占当月营业收入比重",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-04", "query": f"{PREFIX}今年每月销项发票税额占营业收入比例",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-05", "query": f"{PREFIX}去年各月所得税费用与经营现金流净额比率",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-06", "query": f"{PREFIX}去年各月销项发票税额减进项发票税额与增值税应纳税额比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-07", "query": f"{PREFIX}今年各月销售收现、营业收入和应收账款余额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-08", "query": f"{PREFIX}去年各季度采购金额、销售金额、存货和经营现金流出",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0},
    {"id": "XD-M1-09", "query": f"{PREFIX}今年各月银行存款加应收账款减短期借款与销项税加进项税比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-M1-10", "query": f"{PREFIX}去年各月所得税加增值税与利润总额比值",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},

    # 多指标多期间
    {"id": "XD-MM-01", "query": f"{PREFIX}2024到2025年营业收入、销项税和经营现金流净额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-02", "query": f"{PREFIX}今年各季度总资产、总负债和净利润",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0},
    {"id": "XD-MM-03", "query": f"{PREFIX}去年每月采购金额、销售金额和营业成本",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-04", "query": f"{PREFIX}今年每月银行存款、应收账款和短期借款余额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1,
     "allow_single_domain": True},
    {"id": "XD-MM-05", "query": f"{PREFIX}去年各季度应纳所得税、利润总额和支付税费现金",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-06", "query": f"{PREFIX}2024到2025年毛利率、资产负债率和营业收入",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-07", "query": f"{PREFIX}去年每月销售收现、营业收入和应收账款余额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-08", "query": f"{PREFIX}今年各月进项发票税额、销项发票税额和应交增值税",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-09", "query": f"{PREFIX}去年各月营业收入、净利润、经营现金流净额、总资产、销项税和所得税",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 1},
    {"id": "XD-MM-10", "query": f"{PREFIX}今年各季度营业收入、营业成本、净利润、总资产、总负债、经营现金流净额、销项税、进项税、应纳所得税和采购金额",
     "expected_domain": "cross_domain", "expected_path": "cross_domain", "min_rows": 0},
]


# ============================================================
# 验证函数
# ============================================================
def validate_result(tc, result):
    """验证单个测试结果，返回 (passed, failures)"""
    failures = []

    # 1. 管线无报错
    if not result.get('success'):
        failures.append(f"pipeline failed: {result.get('error', 'unknown')}")

    # 2. 未触发澄清
    if result.get('clarification'):
        failures.append(f"clarification triggered: {result['clarification'][:80]}")

    # 3. 域检测 — 检查 intent domain（LLM最终判断）或 entity domain_hint
    entities = result.get('entities', {})
    intent = result.get('intent', {})
    detected_domain = intent.get('domain') or entities.get('domain_hint', '')
    entity_domain = entities.get('domain_hint', '')
    expected = tc['expected_domain']

    # 跨域：entity_preprocessor 或 intent 任一检测到即可
    if expected == 'cross_domain':
        if detected_domain != 'cross_domain' and entity_domain != 'cross_domain':
            # 允许LLM将跨域问题路由为单域（如果标记了allow_single_domain）
            if not tc.get('allow_single_domain'):
                failures.append(f"domain: expected cross_domain, got entity={entity_domain} intent={detected_domain}")
    elif expected == 'financial_metrics' and tc['expected_path'] == 'metric':
        pass  # metric path may detect differently
    else:
        # 允许 entity_preprocessor 和 LLM intent 任一匹配
        if detected_domain != expected and entity_domain != expected:
            # 允许跨域检测（如果标记了allow_cross_domain）
            if tc.get('allow_cross_domain') and (detected_domain == 'cross_domain' or entity_domain == 'cross_domain'):
                pass  # acceptable
            else:
                # 特殊情况：account_balance 和 balance_sheet 可互换
                compatible = {
                    'account_balance': {'balance_sheet'},
                    'balance_sheet': {'account_balance'},
                }
                if detected_domain not in compatible.get(expected, set()):
                    failures.append(f"domain: expected {expected}, got entity={entity_domain} intent={detected_domain}")

    # 4. 返回行数
    results_data = result.get('results', [])
    if results_data is None:
        results_data = []
    # metric path returns dicts with 'value' key
    if isinstance(results_data, list) and len(results_data) > 0:
        if isinstance(results_data[0], dict) and 'value' in results_data[0]:
            # metric result
            if tc['min_rows'] > 0 and all(r.get('value') is None for r in results_data):
                failures.append(f"metric results all None")
        elif tc['min_rows'] > 0 and len(results_data) < tc['min_rows']:
            failures.append(f"rows: expected >= {tc['min_rows']}, got {len(results_data)}")
    elif tc['min_rows'] > 0:
        failures.append(f"rows: expected >= {tc['min_rows']}, got 0")

    return len(failures) == 0, failures


# ============================================================
# 主测试运行器
# ============================================================
def run_tests():
    """运行全部57个测试"""
    print("=" * 70)
    print(f"综合测试：{len(TEST_CASES)} 个问题全域验证")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 70)

    all_results = []
    passed_count = 0
    failed_count = 0
    error_count = 0

    for i, tc in enumerate(TEST_CASES):
        tc_id = tc['id']
        query = tc['query']
        print(f"\n{'─'*60}")
        print(f"[{i+1}/{len(TEST_CASES)}] {tc_id}: {query}")
        print(f"{'─'*60}")

        start = time.time()
        try:
            result = run_pipeline(query)
            elapsed = round(time.time() - start, 1)

            passed, failures = validate_result(tc, result)

            status = "PASS" if passed else "FAIL"
            if passed:
                passed_count += 1
            else:
                failed_count += 1

            print(f"\n  >>> {status} ({elapsed}s)")
            if failures:
                for f in failures:
                    print(f"      - {f}")

            # 收集结果
            entry = {
                "id": tc_id,
                "query": query,
                "passed": passed,
                "elapsed_s": elapsed,
                "failures": failures,
                "domain_detected": result.get('entities', {}).get('domain_hint'),
                "rows_returned": len(result.get('results') or []),
                "error": result.get('error'),
            }
            # 保存SQL（如果有）
            if result.get('sql'):
                entry['sql'] = result['sql']
            # 保存前3行结果
            res_data = result.get('results') or []
            if res_data and len(res_data) > 0:
                entry['sample_results'] = res_data[:3]

            all_results.append(entry)

        except Exception as e:
            elapsed = round(time.time() - start, 1)
            error_count += 1
            failed_count += 1
            print(f"\n  >>> ERROR ({elapsed}s): {e}")
            all_results.append({
                "id": tc_id, "query": query, "passed": False,
                "elapsed_s": elapsed, "failures": [f"exception: {str(e)}"],
                "error": str(e),
            })

    # 汇总
    print(f"\n{'='*70}")
    print(f"测试汇总")
    print(f"{'='*70}")
    print(f"  总计: {len(TEST_CASES)}")
    print(f"  通过: {passed_count}")
    print(f"  失败: {failed_count}")
    print(f"  异常: {error_count}")
    print(f"  通过率: {passed_count/len(TEST_CASES)*100:.1f}%")

    # 列出失败项
    failed_items = [r for r in all_results if not r['passed']]
    if failed_items:
        print(f"\n失败项:")
        for r in failed_items:
            print(f"  {r['id']}: {', '.join(r['failures'][:2])}")

    # 保存JSON
    output = {
        "test_date": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed_count,
        "failed": failed_count,
        "errors": error_count,
        "pass_rate": f"{passed_count/len(TEST_CASES)*100:.1f}%",
        "results": all_results,
    }

    output_path = Path(__file__).parent / "docs" / "test_comprehensive_results.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已保存: {output_path}")

    return output


if __name__ == '__main__':
    run_tests()
