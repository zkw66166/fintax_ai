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

    # 检查跨域查询：sub_results 或 sub_tables
    if result.get('cross_domain_summary') or result.get('sub_results'):
        return {'scenario': 'cross_domain'}

    dd = result.get('display_data', {})
    if dd.get('sub_tables'):
        return {'scenario': 'cross_domain'}

    # NEW: 检测 financial_metrics 域的 EAV 结构（metric_name 作为维度）
    domain = result.get('domain', '')
    results = result.get('results', [])
    if domain == 'financial_metrics' and results:
        first_row = results[0]
        if 'metric_name' in first_row:
            # 检查是否有多个期间列（如 "2024年末", "2025年末"）
            period_cols = [k for k in first_row.keys()
                          if '年' in k and ('月' in k or '末' in k or '初' in k)]
            if len(period_cols) >= 2:
                return {'scenario': 'financial_metrics_multi_period'}
            else:
                return {'scenario': 'financial_metrics_single_period'}

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
    'financial_metrics_single_period': (
        "本次查询返回多个财务指标、单一期间的数据（EAV结构，metric_name为维度）。请分析：\n"
        "- 按指标类别分组解读（盈利能力、偿债能力、运营效率、税务负担等）\n"
        "- 评价各指标的当前水平（优/良/中/差）\n"
        "- 说明各指标的通用合理区间\n"
        "- 分析不同类别指标间的关联性\n"
        "- 指出异常指标"
    ),
    'financial_metrics_multi_period': (
        "本次查询返回多个财务指标、多个期间的数据（EAV结构，metric_name为维度）。请分析：\n"
        "- **重要**：数据结构为 metric_name（指标名称）+ 多个期间列（如2024年末、2025年末）\n"
        "- **计算变动时**：必须**分别计算每个指标**的期间变动，不要跨指标计算\n"
        "- 例如：净利率从2024年末的25.5%变为2025年末的25.5%，变动为0%\n"
        "- 例如：增值税税负率从2024年末的3.7%变为2025年末的3.7%，变动为0%\n"
        "- **不要**将第一行的期末值与第二行的期初值进行比较（这是错误的跨指标计算）\n"
        "- 按指标类别分组，分析各指标的跨期变动趋势\n"
        "- 评价各指标的变动幅度是否合理\n"
        "- 分析不同类别指标变动的同步性\n"
        "- 综合总结财务指标组合呈现的企业经营特征"
    ),
    'metric_computed': (
        "本次查询返回计算型财务指标。请分析：\n"
        "- 解读该指标的含义\n"
        "- 评价当前水平（优/良/中/差）\n"
        "- 说明该指标的通用合理区间\n"
        "- 如有行业参考值，进行对比"
    ),
    'cross_domain': (
        "本次查询涉及跨域数据（如利润与增值税、资产负债表与利润表等）。请分析：\n"
        "- **数据完整性检查**：首先确认各域数据是否完整返回（检查\"数据来源\"列）\n"
        "- **各域数据解读**：分别解读各域的关键指标和数值水平\n"
        "- **跨域关联分析**：分析各域数据之间的逻辑一致性和关联关系\n"
        "- **数值匹配度**：评估跨域指标的数值匹配度（如净利润与所得税、营业收入与销项税额）\n"
        "- **异常识别**：如存在背离或差异，分析可能原因\n"
        "- **注意**：只有当数据确实缺失时才报告缺失，不要因为数据来自不同域就误判为缺失"
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

    # 跨域 list 操作：从 sub_tables 提取数据
    sub_tables = dd.get('sub_tables', [])
    if sub_tables:
        # 2026-03-17: 按子域分别展示数据（而非合并为一个稀疏大表）
        # 原问题：合并后每行只有自己域的列有值，其他域列为空，LLM误判为"数据缺失"
        # 新方案：每个子域独立展示，LLM能清晰看到每个域的完整数据
        for st in sub_tables:
            domain_cn = st.get('domain_cn', st.get('domain', ''))
            st_table = st.get('table', {})
            st_headers = st_table.get('headers', [])
            st_rows = st_table.get('rows', [])

            if st_headers and st_rows:
                display_rows = st_rows[:20]  # 每域最多20行，避免prompt过长
                lines = [f"【{domain_cn}】({len(st_rows)}行)"]
                lines.append(" | ".join(st_headers))
                for row in display_rows:
                    lines.append(" | ".join(str(row.get(h, '')) for h in st_headers))
                if len(st_rows) > 20:
                    lines.append(f"... (共{len(st_rows)}行，仅展示前20行)")
                parts.append("\n".join(lines))

        # 添加子域数据摘要
        summary_lines = ["各子域数据概览："]
        for st in sub_tables:
            domain_cn = st.get('domain_cn', '')
            st_table = st.get('table', {})
            row_count = len(st_table.get('rows', []))
            st_headers = st_table.get('headers', [])
            col_count = len(st_headers)
            # 列出具体指标列名，帮助LLM理解每个域包含哪些数据
            metric_cols = [h for h in st_headers if h not in ('纳税人识别号', '纳税人名称', '年度', '月份', '季度', '项目类型', '时间范围')]
            col_info = f"指标: {', '.join(metric_cols)}" if metric_cols else f"{col_count}列"
            summary_lines.append(f"  - {domain_cn}: {row_count}行, {col_info}")
        parts.append("\n".join(summary_lines))

    # 单域或其他跨域操作
    else:
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
