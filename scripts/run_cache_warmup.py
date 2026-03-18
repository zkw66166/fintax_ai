"""
缓存预热测试脚本 — 57个问题 × 4家企业 = 228次查询
Step 1: TSE科技 deep模式（生成L1+L2缓存）
Step 2: 恒泰/博雅/鑫源 quick模式（命中L2缓存，生成L1缓存）

用法: python scripts/run_cache_warmup.py [--step 1|2] [--company TSE|恒泰|博雅|鑫源]
      默认运行全部步骤。
前提: 服务器已启动 (uvicorn api.main:app --host 0.0.0.0 --port 8000)
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# 强制无缓冲输出
os.environ["PYTHONUNBUFFERED"] = "1"

# ── 配置 ──────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
LOGIN_USER = "admin"
LOGIN_PASS = "admin123"
RESPONSE_MODE = "detailed"
DEEP_TIMEOUT = 180      # deep模式超时（秒）
QUICK_TIMEOUT = 120     # quick模式超时（秒）
DEEP_DELAY = 1.0        # deep模式查询间隔（秒）
QUICK_DELAY = 0.5       # quick模式查询间隔（秒）

# ── 企业定义（按L2缓存命中优化排序）──────────────────────
COMPANIES = [
    {
        "id": "91310115MA2KZZZZZZ",
        "name": "TSE科技有限公司",
        "short": "TSE",
        "step": 1,
        "thinking_mode": "deep",
    },
    {
        "id": "91320200MA02BBBBB2",
        "name": "恒泰建材有限公司",
        "short": "恒泰",
        "step": 2,
        "thinking_mode": "quick",
    },
    {
        "id": "91110108MA01AAAAA1",
        "name": "博雅文化传媒有限公司",
        "short": "博雅",
        "step": 2,
        "thinking_mode": "quick",
    },
    {
        "id": "92440300MA5EQXL17P",
        "name": "鑫源贸易商行",
        "short": "鑫源",
        "step": 2,
        "thinking_mode": "quick",
    },
]

# ── 57个测试问题 (raw_text, domain_label) ──────────────────
# 注意：问题不含企业名称，后端自动根据company_id拼接
QUESTIONS = [
    # ═══ 一、单域问题（27个）═══

    # 1. 科目余额表 (3)
    ("去年年底的银行存款余额还有多少？", "科目余额表"),
    ("今年每个月末的现金余额变化情况。", "科目余额表"),
    ("去年第一季度各月管理费用和财务费用的发生额。", "科目余额表"),

    # 2. 资产负债表 (3)
    ("2024年3月底的应收账款有多少？", "资产负债表"),
    ("去年每个季度末的短期借款是多少？", "资产负债表"),
    ("近两年每年末的总资产和总负债构成。", "资产负债表"),

    # 3. 利润表 (3)
    ("上个月的净利润是多少？", "利润表"),
    ("去年各季度的营业收入。", "利润表"),
    ("前年上半年的营业收入、营业成本和销售费用。", "利润表"),

    # 4. 现金流量表 (3)
    ("今年5月的经营现金流净额。", "现金流量表"),
    ("去年每个月的投资活动现金流出。", "现金流量表"),
    ("去年第一季度各月的经营流入和经营流出。", "现金流量表"),

    # 5. 增值税申报表 (3)
    ("去年12月的销项税。", "增值税"),
    ("今年各季度的应交增值税。", "增值税"),
    ("去年每月增值税申报的销售额、销项税和进项税。", "增值税"),

    # 6. 企业所得税申报表 (3)
    ("2023年汇算清缴的应纳税所得额。", "企业所得税"),
    ("去年每个季度预缴的所得税。", "企业所得税"),
    ("2023年各季度申报的营业收入、营业成本和利润总额。", "企业所得税"),

    # 7. 进项发票 (3)
    ("去年12月采购发票的进项税总额。", "进项发票"),
    ("今年每个月的采购金额（不含税）。", "进项发票"),
    ("去年各季度采购发票的金额和税额。", "进项发票"),

    # 8. 销项发票 (3)
    ("上个月销售发票的总销售额（不含税）。", "销项发票"),
    ("去年各月的销项税。", "销项发票"),
    ("今年第一季度各月销售发票的金额和税额。", "销项发票"),

    # 9. 关键财务指标 (3)
    ("去年年底的资产负债率是多少？", "财务指标"),
    ("今年每月的增值税税负率走势。", "财务指标"),
    ("去年各季度的销售收现比和应收账款周转率。", "财务指标"),

    # ═══ 二、跨域问题（30个）═══

    # （一）跨域单指标单期间 (10)
    ("上个月进项税和销项税的比例是多少？", "跨域-单指标单期间"),
    ("今年一季度的所得税费用占利润总额的比重？", "跨域-单指标单期间"),
    ("今年3月底的银行存款余额相当于当月营业收入的几倍？", "跨域-单指标单期间"),
    ("上个月销项税占营业收入的比例？", "跨域-单指标单期间"),
    ("去年全年所得税费用与经营现金流净额的比率？", "跨域-单指标单期间"),
    ("去年12月的（销项税额 - 进项税额）与应纳税额的比值？", "跨域-单指标单期间-3域"),
    ("今年5月的销售收现、营业收入和应收账款余额的比值？", "跨域-单指标单期间-3域"),
    ("2025年第四季度的采购金额、销售金额、存货增加额和经营现金流出的关系？", "跨域-单指标单期间-4域"),
    ("去年12月的（银行存款余额 + 应收账款余额 - 短期借款余额）与（销项税额 + 进项税额）的比值？", "跨域-单指标单期间-4域"),
    ("2025全年的（所得税费用 + 增值税应纳税额）与利润总额的比值？", "跨域-单指标单期间-3域"),

    # （二）跨域单指标多期间 (10)
    ("今年每月的进项税与销项税之比。", "跨域-单指标多期间"),
    ("去年各季度所得税费用占利润总额的比例。", "跨域-单指标多期间"),
    ("今年每月末的银行存款余额占当月营业收入的比重。", "跨域-单指标多期间"),
    ("今年每月销项税占营业收入的比例。", "跨域-单指标多期间"),
    ("去年各月所得税费用与经营现金流净额的比率。", "跨域-单指标多期间"),
    ("去年各月的（销项税额 - 进项税额）与应纳税额的比值。", "跨域-单指标多期间-3域"),
    ("今年各月的销售收现、营业收入和应收账款余额的比值。", "跨域-单指标多期间-3域"),
    ("去年各季度的采购金额、销售金额、存货增加额和经营现金流出的关系。", "跨域-单指标多期间-4域"),
    ("今年各月的（银行存款余额 + 应收账款余额 - 短期借款余额）与（销项税额 + 进项税额）的比值。", "跨域-单指标多期间-4域"),
    ("去年各月的（所得税费用 + 增值税应纳税额）与利润总额的比值。", "跨域-单指标多期间-3域"),

    # （三）跨域多指标多期间 (10)
    ("23-25年营业收入、销项税和经营现金流净额。", "跨域-多指标多期间-3域"),
    ("今年各季度总资产、总负债和净利润情况。", "跨域-多指标多期间-2域"),
    ("去年每月采购发票金额、销售发票金额和营业成本。", "跨域-多指标多期间-3域"),
    ("今年每月银行存款余额、应收账款余额和短期借款余额。", "跨域-多指标多期间-2域"),
    ("去年各季度应纳所得税额、利润总额和支付的各项税费。", "跨域-多指标多期间-3域"),
    ("2023-25年毛利率、资产负债率和营业收入。", "跨域-多指标多期间-2域"),
    ("去年每月销售收现、营业收入和应收账款余额。", "跨域-多指标多期间-3域"),
    ("今年各月进项税额、销项税额和应交增值税。", "跨域-多指标多期间-3域"),
    ("去年各月的营业收入、净利润、经营活动现金流净额、资产总计、销项税额、应纳所得税额。", "跨域-多指标多期间-5域"),
    ("今年各季度的营业收入、营业成本、利润总额、所得税费用、经营活动现金流净额、投资活动现金流净额、资产总计、负债合计、应交增值税、进项税额。", "跨域-多指标多期间-6域"),
]

assert len(QUESTIONS) == 57, f"Expected 57 questions, got {len(QUESTIONS)}"


# ── 工具函数 ──────────────────────────────────────────────

def strip_annotations(q: str) -> str:
    """移除问题末尾的域标注和补充说明，保留问题中间的数学括号。

    Examples:
        "上个月进项税和销项税的比例是多少？（进项发票、销项发票）"
        → "上个月进项税和销项税的比例是多少？"

        "去年12月的（销项税额 - 进项税额）与应纳税额的比值？（销项发票、进项发票、增值税申报表）——跨3个域"
        → "去年12月的（销项税额 - 进项税额）与应纳税额的比值？"
    """
    # 先移除 ——... 尾注
    q = re.sub(r'——[^（）]*$', '', q)
    # 移除末尾的域标注括号（含域关键词的括号）
    q = re.sub(
        r'（[^（）]*(?:发票|申报|余额|利润|资产|现金|指标|科目|所得税|增值税|跨)[^（）]*）$',
        '', q
    )
    return q.strip()


def login() -> str:
    """登录获取JWT token。"""
    resp = requests.post(f"{API_BASE}/api/auth/login", json={
        "username": LOGIN_USER,
        "password": LOGIN_PASS,
    }, timeout=10)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print(f"Login failed: {resp.json()}")
        sys.exit(1)
    return token


def send_query(token: str, query: str, company_id: str,
               thinking_mode: str = "quick") -> dict | None:
    """发送查询到 /api/chat，解析SSE流，返回done事件的result。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "company_id": company_id,
        "response_mode": RESPONSE_MODE,
        "thinking_mode": thinking_mode,
    }
    timeout = DEEP_TIMEOUT if thinking_mode == "deep" else QUICK_TIMEOUT

    resp = requests.post(
        f"{API_BASE}/api/chat",
        json=payload,
        headers=headers,
        stream=True,
        timeout=timeout,
    )
    resp.raise_for_status()

    result = None
    current_event = None

    for line in resp.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8")
        if line_str.startswith("event: "):
            current_event = line_str[7:]
        elif line_str.startswith("data: ") and current_event == "done":
            try:
                result = json.loads(line_str[6:])
            except json.JSONDecodeError:
                pass
            break

    return result


def save_history(token: str, query: str, company_id: str,
                 result: dict, thinking_mode: str) -> bool:
    """保存查询结果到历史记录。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    entry = {
        "query": query,
        "company_id": company_id,
        "timestamp": datetime.now().isoformat(),
        "route": result.get("route", ""),
        "cache_key": result.get("cache_key", ""),
        "response_mode": RESPONSE_MODE,
        "thinking_mode": thinking_mode,
        "conversation_enabled": False,
        "conversation_depth": 3,
        "conversation_history": [],
        "result": result,
    }
    try:
        resp = requests.post(
            f"{API_BASE}/api/chat/history",
            json=entry,
            headers=headers,
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"    [history save error: {e}]")
        return False


def run_company(token: str, company: dict, questions: list,
                global_idx: int, total: int, skip: int = 0) -> dict:
    """运行一家企业的全部问题，返回统计。"""
    stats = {"success": 0, "failed": 0, "errors": 0, "l2_hits": 0, "failed_list": []}
    mode = company["thinking_mode"]
    delay = DEEP_DELAY if mode == "deep" else QUICK_DELAY
    cid = company["id"]
    short = company["short"]

    print(f"\n{'─'*60}")
    print(f"  {company['name']} ({mode}模式)")
    print(f"{'─'*60}")

    for i, (raw_q, domain) in enumerate(questions):
        if i < skip:
            continue
        query = strip_annotations(raw_q)
        idx = global_idx + i + 1
        t0 = time.time()

        try:
            result = send_query(token, query, cid, mode)
            elapsed = time.time() - t0

            if result and result.get("success"):
                stats["success"] += 1
                route = result.get("route", "?")
                cache_src = result.get("cache_source", "")
                if cache_src == "l2":
                    stats["l2_hits"] += 1
                src_tag = f" [{cache_src}]" if cache_src else ""
                print(f"  [{idx}/{total}] {short}: {query[:40]}... ✓ ({route}{src_tag}, {elapsed:.1f}s)", flush=True)

                save_history(token, query, cid, result, mode)
            else:
                stats["failed"] += 1
                err = result.get("error", "empty/failed") if result else "no result"
                print(f"  [{idx}/{total}] {short}: {query[:40]}... ✗ ({err[:40]})", flush=True)
                stats["failed_list"].append({"query": query[:50], "domain": domain, "error": str(err)[:60]})

                # 即使失败也保存历史（记录失败状态）
                if result:
                    save_history(token, query, cid, result, mode)

        except requests.exceptions.Timeout:
            stats["errors"] += 1
            elapsed = time.time() - t0
            print(f"  [{idx}/{total}] {short}: {query[:40]}... ✗ (TIMEOUT {elapsed:.0f}s)", flush=True)
            stats["failed_list"].append({"query": query[:50], "domain": domain, "error": "TIMEOUT"})
        except Exception as e:
            stats["errors"] += 1
            print(f"  [{idx}/{total}] {short}: {query[:40]}... ✗ ({str(e)[:40]})", flush=True)
            stats["failed_list"].append({"query": query[:50], "domain": domain, "error": str(e)[:60]})

        if i < len(questions) - 1:
            time.sleep(delay)

    return stats


def print_summary(all_stats: dict, start_time: float):
    """打印汇总报告。"""
    elapsed = time.time() - start_time
    cache_dir = Path(__file__).resolve().parent.parent / "cache"

    print(f"\n{'='*60}")
    print(f"  汇总报告")
    print(f"{'='*60}")

    total_s = total_f = total_e = total_l2 = 0
    for short, st in all_stats.items():
        s, f, e, l2 = st["success"], st["failed"], st["errors"], st["l2_hits"]
        total_s += s
        total_f += f
        total_e += e
        total_l2 += l2
        n = s + f + e
        pct = s / n * 100 if n else 0
        print(f"  {short:6s}: {s}/{n} 成功 ({pct:.0f}%)  L2命中: {l2}")

    total = total_s + total_f + total_e
    print(f"  {'─'*40}")
    print(f"  总计: {total_s}/{total} 成功 ({total_s/total*100:.0f}%)  L2命中: {total_l2}")
    print(f"  耗时: {elapsed/60:.1f} 分钟")

    # 缓存文件统计
    if cache_dir.exists():
        l1 = len([f for f in cache_dir.glob("*.json") if not f.name.startswith("template_")])
        l2 = len(list(cache_dir.glob("template_*.json")))
        print(f"  L1缓存文件: {l1}  L2模板文件: {l2}")

    # 失败列表
    all_failed = []
    for short, st in all_stats.items():
        for f in st["failed_list"]:
            all_failed.append(f"{short}: {f['query']} [{f['domain']}] — {f['error']}")

    if all_failed:
        print(f"\n  失败查询 ({len(all_failed)}):")
        for line in all_failed[:20]:
            print(f"    {line}")
        if len(all_failed) > 20:
            print(f"    ... 还有 {len(all_failed)-20} 条")

    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="缓存预热测试")
    parser.add_argument("--step", type=int, choices=[1, 2], help="只运行指定步骤")
    parser.add_argument("--company", type=str, help="只运行指定企业 (TSE/恒泰/博雅/鑫源)")
    parser.add_argument("--skip", type=int, default=0, help="每家企业跳过前N个问题（用于断点续跑）")
    args = parser.parse_args()

    # 筛选企业
    companies = COMPANIES
    if args.step:
        companies = [c for c in companies if c["step"] == args.step]
    if args.company:
        companies = [c for c in companies if c["short"] == args.company]

    if not companies:
        print("No matching companies found.")
        sys.exit(1)

    total_queries = len(QUESTIONS) * len(companies)

    print("=" * 60)
    print("  缓存预热测试")
    print(f"  {len(QUESTIONS)} 问题 × {len(companies)} 企业 = {total_queries} 查询")
    print("=" * 60)

    # 登录
    print("\n登录中...")
    token = login()
    print(f"✓ 登录成功 (user: {LOGIN_USER})")

    # 执行
    start_time = time.time()
    all_stats = {}
    global_idx = 0

    for company in companies:
        stats = run_company(token, company, QUESTIONS, global_idx, total_queries, skip=args.skip)
        all_stats[company["short"]] = stats
        global_idx += len(QUESTIONS)

    print_summary(all_stats, start_time)


if __name__ == "__main__":
    main()
