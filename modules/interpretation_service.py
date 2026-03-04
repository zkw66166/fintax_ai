"""LLM 数据解读服务：场景检测 + 提示词构建 + 流式生成"""
import json
from openai import OpenAI
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LLM_TIMEOUT,
    INTERPRETATION_MAX_TOKENS, INTERPRETATION_TEMPERATURE,
)

# 模块级 OpenAI 客户端单例
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE, timeout=LLM_TIMEOUT)
    return _client


DOMAIN_CN = {
    'vat': '增值税',
    'eit': '企业所得税',
    'balance_sheet': '资产负债表',
    'account_balance': '科目余额',
    'profit': '利润表',
    'cash_flow': '现金流量表',
    'financial_metrics': '财务指标',
    'invoice': '发票',
    'cross_domain': '跨域查询',
}

# ---------- 场景检测 ----------

SKIP_COLUMNS = {
    'taxpayer_id', 'taxpayer_name', 'taxpayer_type', 'period_year',
    'period_month', 'period_quarter', 'time_range', 'item_type',
    'accounting_standard', 'revision_no', 'gaap_type',
}


def _count_numeric_columns(rows: list, headers: list) -> int:
    """统计结果中数值列的数量（排除标识列）"""
    if not rows or not headers:
        return 0
    count = 0
    first_row = rows[0]
    for h in headers:
        val = first_row.get(h, '')
        if isinstance(val, str):
            cleaned = val.replace(',', '').replace('万', '').replace('亿', '').replace('%', '').replace('-', '', 1)
            try:
                float(cleaned)
                count += 1
            except (ValueError, TypeError):
                pass
        elif isinstance(val, (int, float)):
            count += 1
    return count


def detect_scenario(result: dict) -> dict:
    """根据查询结果分类场景"""
    # 优先判断特殊路径
    if result.get('metric_results'):
        return {'scenario': 'metric_computed'}

    if result.get('cross_domain_summary') or result.get('sub_results'):
        return {'scenario': 'cross_domain'}

    dd = result.get('display_data', {})
    table = dd.get('table', {})
    headers = table.get('headers', [])
    rows = table.get('rows', [])

    if not rows:
        # 回退到 raw results
        raw = result.get('results', [])
        if not raw:
            return {'scenario': 'single_indicator_single_period'}
        rows = raw
        headers = list(raw[0].keys()) if raw else []

    row_count = len(rows)
    num_cols = _count_numeric_columns(rows, headers)

    if row_count <= 1:
        if num_cols <= 2:
            return {'scenario': 'single_indicator_single_period'}
        return {'scenario': 'multi_indicator_single_period'}

    if num_cols <= 2:
        return {'scenario': 'single_indicator_multi_period'}

    return {'scenario': 'multi_indicator_multi_period'}


# ---------- 提示词构建 ----------

SCENARIO_INSTRUCTIONS = {
    'single_indicator_single_period': (
        "本次查询返回单一指标、单一期间的数据。请分析：\n"
        "- 该指标的含义和当前数值水平\n"
        "- 如果是比率/比例指标，说明通用合理区间并评价当前值是否正常\n"
        "- 如有异常值（负数余额、畸高/畸低），指出并分析可能原因"
    ),
    'single_indicator_multi_period': (
        "本次查询返回单一指标、多个期间的数据。请分析：\n"
        "- 计算各期间的环比变动幅度\n"
        "- 梳理变动趋势（持续上升/下降/波动/平稳）\n"
        "- 识别变动幅度最大的期间，分析可能的驱动因素\n"
        "- 如有拐点，分析拐点前后的变化特征\n"
        "- 判断趋势是否异常"
    ),
    'multi_indicator_single_period': (
        "本次查询返回多个指标、单一期间的数据。请分析：\n"
        "- 按类别分组解读（如盈利能力、偿债能力、现金流、税务等）\n"
        "- 对同类指标计算内部占比（如成本/收入、各费用/总费用、流动资产/总资产等）\n"
        "- 比率指标单独解读，与通用合理区间对比\n"
        "- 分析不同类别指标间的配比关系和关联性\n"
        "- 指出异常指标"
    ),
    'multi_indicator_multi_period': (
        "本次查询返回多个指标、多个期间的数据。请分析：\n"
        "- 按类别分组，分析各类指标的变动趋势和幅度\n"
        "- 对比同类指标内部占比的跨期变化\n"
        "- 比率指标的跨期变动趋势和波动幅度\n"
        "- 分析不同类别指标跨期变动的同步性（如营收与税额是否同步变动）\n"
        "- 综合总结多指标组合呈现的财税特征和异常点"
    ),
    'metric_computed': (
        "本次查询返回计算型财务指标。请分析：\n"
        "- 解读该指标的含义\n"
        "- 评价当前水平（优/良/中/差）\n"
        "- 说明该指标的通用合理区间\n"
        "- 如有行业参考值，进行对比"
    ),
    'cross_domain': (
        "本次查询涉及跨域数据（如利润与增值税、进项与销项等）。请分析：\n"
        "- 各域数据之间的逻辑一致性和关联关系\n"
        "- 跨域指标的数值匹配度（如净利润与所得税、营业收入与销项税额）\n"
        "- 如存在背离或差异，分析可能原因"
    ),
}

SYSTEM_PROMPT_TEMPLATE = """你是一位资深的中国企业财税数据分析师、注册会计师。请根据以下SQL查询结果，为用户提供专业的数据解读。

## 分析要求
{scenario_instructions}

## 分析规范
- 使用中文，Markdown格式（加粗关键数字，使用列表）
- 先给出1-2句总结判断，再展开具体分析
- 数值引用保持原始精度和单位（万/亿）
- 发现异常数据（负数余额、比率畸高/畸低）要明确指出并给出可能原因
- 不要复述原始数据表格，提炼洞察和结论
- 数据不足以支撑某项分析时直接说明，不要猜测
- 分析篇幅控制在300字以内"""


def _format_data_for_prompt(result: dict, query: str) -> str:
    """将查询结果打包为 LLM user message"""
    parts = [f"用户提问：{query}"]

    domain = (result.get('intent') or {}).get('domain', '')
    if domain:
        parts.append(f"查询域：{DOMAIN_CN.get(domain, domain)}")

    # 优先使用 display_data（已有中文表头和格式化数值）
    dd = result.get('display_data', {})
    table = dd.get('table', {})
    headers = table.get('headers', [])
    rows = table.get('rows', [])

    if headers and rows:
        display_rows = rows[:50]
        lines = [" | ".join(headers)]
        for row in display_rows:
            lines.append(" | ".join(str(row.get(h, '')) for h in headers))
        if len(rows) > 50:
            lines.append(f"... (共{len(rows)}行，仅展示前50行)")
        parts.append(f"查询结果：\n{chr(10).join(lines)}")
    elif result.get('results'):
        raw = result['results'][:50]
        if raw:
            keys = list(raw[0].keys())
            lines = [" | ".join(keys)]
            for row in raw:
                lines.append(" | ".join(str(row.get(k, '')) for k in keys))
            parts.append(f"查询结果：\n{chr(10).join(lines)}")

    # 包含计算型指标信息
    if result.get('metric_results'):
        for m in result['metric_results']:
            parts.append(f"指标：{m.get('label')} = {m.get('value')} {m.get('unit', '')}")
            if m.get('sources'):
                parts.append(f"  计算依据：{json.dumps(m['sources'], ensure_ascii=False)}")

    # 包含环比变动数据
    if dd.get('growth'):
        growth_lines = ["环比变动数据："]
        for g in dd['growth'][:10]:
            period = g.get('period', '')
            for key, val in g.items():
                if key != 'period' and isinstance(val, dict):
                    pct = val.get('change_pct')
                    if pct is not None:
                        growth_lines.append(f"  {period} {key}: {pct:+.2f}%")
        if len(growth_lines) > 1:
            parts.append("\n".join(growth_lines))

    return "\n\n".join(parts)


def build_interpretation_prompt(result: dict, query: str, scenario: dict) -> list:
    """构建 LLM 消息数组"""
    scenario_name = scenario.get('scenario', 'multi_indicator_single_period')
    instructions = SCENARIO_INSTRUCTIONS.get(scenario_name, SCENARIO_INSTRUCTIONS['multi_indicator_single_period'])

    system_msg = SYSTEM_PROMPT_TEMPLATE.format(scenario_instructions=instructions)
    user_msg = _format_data_for_prompt(result, query)

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


# ---------- 流式生成 ----------

def interpret_stream(result: dict, query: str, response_mode: str = "detailed"):
    """
    流式生成数据解读。
    Yields: (chunk_text: str, is_done: bool)
    """
    # 空结果直接跳过
    results = result.get('results') or []
    metric_results = result.get('metric_results') or []
    if not results and not metric_results:
        yield ("", True)
        return

    scenario = detect_scenario(result)
    messages = build_interpretation_prompt(result, query, scenario)

    # standard 模式要求简短
    if response_mode == "standard":
        messages[-1]["content"] += "\n\n注意：请简要分析，限3句话以内。"

    accumulated = []
    try:
        client = _get_client()
        stream = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=INTERPRETATION_MAX_TOKENS,
            temperature=INTERPRETATION_TEMPERATURE,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                accumulated.append(delta.content)
                yield (delta.content, False)

        full_text = "".join(accumulated)
        if not full_text.strip():
            yield ("未能生成有效的数据解读。", True)
        else:
            yield (full_text, True)

    except Exception as e:
        print(f"[interpretation] LLM 调用失败: {e}")
        if accumulated:
            yield ("".join(accumulated), True)
        else:
            yield ("数据解读暂时不可用。", True)
