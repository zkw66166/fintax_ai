"""企业画像分析报告生成服务 — 流式LLM报告生成"""
import json
import logging
from typing import Generator, Dict
from pathlib import Path

from openai import OpenAI
from config.settings import (
    LLM_API_KEY,
    LLM_API_BASE,
    PROFILE_REPORT_LLM_MODEL,
    PROFILE_REPORT_MAX_TOKENS,
    PROFILE_REPORT_TEMPERATURE,
    PROMPTS_DIR,
)

logger = logging.getLogger(__name__)

# 画像模块中文名映射
SECTION_NAMES = {
    "basic_info": "企业基本信息",
    "asset_structure": "资产结构",
    "profit_data": "利润数据",
    "cash_flow": "现金流量",
    "growth_metrics": "成长指标",
    "financial_metrics": "财务指标",
    "tax_summary": "税务汇总",
    "invoice_summary": "发票统计",
    "rd_innovation": "研发创新",
    "cross_border": "跨境业务",
    "compliance_risk": "合规风险",
    "shareholders": "股东信息",
    "employee_structure": "员工结构",
    "external_relations": "外部关系",
    "digitalization": "数字化",
    "esg": "ESG",
    "policy_matching": "政策匹配",
    "special_business": "特殊业务",
}


def _load_prompt_template() -> str:
    """加载报告提示词模板"""
    path = PROMPTS_DIR / "profile_report.txt"
    return path.read_text(encoding="utf-8")


def _filter_available_sections(profile_data: dict) -> dict:
    """过滤掉值为 None 或空的画像模块"""
    available = {}
    for key, value in profile_data.items():
        if value is None:
            continue
        if isinstance(value, dict) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        available[key] = value
    return available


def _build_prompt(profile_data: dict) -> str:
    """构建完整的LLM提示词"""
    template = _load_prompt_template()

    basic_info = profile_data.get("basic_info", {})
    basic_info_text = json.dumps(basic_info, ensure_ascii=False, indent=2) if basic_info else "无"

    available = _filter_available_sections(profile_data)
    available.pop("basic_info", None)

    sections_text_parts = []
    section_index = 1
    for key, value in available.items():
        name = SECTION_NAMES.get(key, key)
        sections_text_parts.append(f"### {section_index}. {name}\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```")
        section_index += 1

    available_sections_text = "\n\n".join(sections_text_parts) if sections_text_parts else "无可用画像数据"

    prompt = template.replace("{basic_info}", basic_info_text).replace("{available_sections}", available_sections_text)

    section_counter = [1]
    def replace_placeholder(match):
        result = f"### {section_counter[0]}"
        section_counter[0] += 1
        return result

    import re
    prompt = re.sub(r'###\s*\{序号\}', replace_placeholder, prompt)

    return prompt


def generate_report_stream(
    profile_data: dict,
    taxpayer_name: str,
    year: int,
) -> Generator[Dict, None, None]:
    """
    流式生成企业画像分析报告

    Yields:
        {'type': 'stage', 'text': str}
        {'type': 'chunk', 'text': str}
        {'type': 'done', 'result': {'content': str}}
    """
    yield {"type": "stage", "text": "正在准备画像数据..."}

    available = _filter_available_sections(profile_data)
    available_count = len([k for k in available if k != "basic_info"])
    if available_count == 0:
        yield {
            "type": "done",
            "result": {"content": "当前企业暂无可用画像数据，无法生成分析报告。"},
        }
        return

    yield {"type": "stage", "text": f"已采集 {available_count} 个模块数据，正在生成分析报告..."}

    prompt = _build_prompt(profile_data)
    logger.info(
        "[ProfileReport] Generating report for %s (%d), prompt length: %d chars",
        taxpayer_name, year, len(prompt),
    )

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)
    full_text = ""

    try:
        stream = client.chat.completions.create(
            model=PROFILE_REPORT_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=PROFILE_REPORT_MAX_TOKENS,
            temperature=PROFILE_REPORT_TEMPERATURE,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
                yield {"type": "chunk", "text": delta.content}

    except Exception as e:
        logger.error("[ProfileReport] LLM streaming error: %s", e)
        yield {
            "type": "done",
            "result": {
                "content": full_text or "",
                "error": f"报告生成过程中出现错误: {str(e)}",
            },
        }
        return

    yield {
        "type": "done",
        "result": {"content": full_text},
    }
