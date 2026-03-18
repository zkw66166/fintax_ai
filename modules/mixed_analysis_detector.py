"""
混合分析检测器 - 判断是否应触发跨路由混合多轮查询分析

只有当用户在前端勾选"多轮对话"且历史对话包含≥2种路由时，才可能触发混合分析。
"""
import json
from typing import List, Dict, Tuple, Set
from pathlib import Path as _Path
from config.config_loader import load_json as _load_json
from config.settings import (
    LLM_API_KEY,
    LLM_API_BASE,
    LLM_MODEL,
    MIXED_ANALYSIS_ENABLED,
    MIXED_ANALYSIS_MIN_ROUTES
)
from openai import OpenAI

_CFG_mixed = _load_json(_Path(__file__).resolve().parent.parent / "config" / "analysis" / "mixed_analysis_keywords.json", {})
_SYNTHESIS_KEYWORDS = _CFG_mixed.get("synthesis_keywords", ['综合', '匹配', '建议', '筹划', '优化', '对比', '结合', '根据上述', '根据前面'])
_SYNTHESIS_PROMPT_CRITERIA = _CFG_mixed.get("synthesis_prompt_criteria", '如果查询要求"综合分析"、"匹配"、"建议"、"筹划"、"优化"、"对比"、"结合"、"根据上述"等，返回true')


def should_trigger_mixed_analysis(
    user_query: str,
    conversation_history: List[Dict],
    conversation_depth: int,
    multi_turn_enabled: bool
) -> Tuple[bool, str]:
    """
    检测是否应触发混合分析路由

    ⚠️ 关键：只有当用户在前端勾选"多轮对话"时才进行检测
    如果未勾选，直接返回 False，走原有三大路由逻辑

    Args:
        user_query: 当前用户查询
        conversation_history: 对话历史
        conversation_depth: 对话轮数
        multi_turn_enabled: 前端是否勾选多轮对话

    Returns:
        (should_trigger, reason)
    """
    # 0. 主开关检查
    if not MIXED_ANALYSIS_ENABLED:
        return False, "mixed_analysis_disabled"

    # 1. 前置检查：用户是否勾选多轮对话
    if not multi_turn_enabled:
        return False, "multi_turn_disabled"

    # 2. 检查轮数是否满足
    if conversation_depth < 2:
        return False, "single_turn"

    # 3. 检查历史是否为空
    if not conversation_history or len(conversation_history) == 0:
        return False, "no_history"

    # 4. 提取历史路由类型
    routes_used = extract_routes_from_history(conversation_history, conversation_depth)

    # 5. 检查是否混合路由
    if len(routes_used) < MIXED_ANALYSIS_MIN_ROUTES:
        return False, f"single_route_{list(routes_used)[0] if routes_used else 'unknown'}"

    # 6. LLM判断当前查询是否需要综合分析
    try:
        needs_synthesis = llm_check_synthesis_need(user_query, conversation_history, routes_used)
    except Exception as e:
        print(f"[mixed_analysis_detector] LLM检测失败: {e}")
        return False, "llm_check_failed"

    if needs_synthesis:
        return True, f"mixed_routes_{'+'.join(sorted(routes_used))}"
    else:
        return False, "no_synthesis_needed"


def extract_routes_from_history(
    conversation_history: List[Dict],
    depth: int
) -> Set[str]:
    """
    从对话历史中提取最近N轮使用的路由类型

    Args:
        conversation_history: 对话历史
        depth: 对话轮数

    Returns:
        路由类型集合，如 {'financial_data', 'tax_incentive'}
    """
    routes = set()

    # 取最近 depth*2 条消息（每轮包含 user + assistant）
    recent_messages = conversation_history[-(depth * 2):]

    for msg in recent_messages:
        if msg.get('role') == 'assistant' and 'metadata' in msg:
            route = msg['metadata'].get('route')
            if route:
                routes.add(route)

    return routes


def llm_check_synthesis_need(
    user_query: str,
    conversation_history: List[Dict],
    routes_used: Set[str]
) -> bool:
    """
    使用LLM判断当前查询是否需要综合分析历史数据

    Args:
        user_query: 当前用户查询
        conversation_history: 对话历史
        routes_used: 历史使用的路由类型

    Returns:
        True if 需要综合分析, False otherwise
    """
    # 生成历史对话摘要
    conversation_summary = _generate_conversation_summary(conversation_history, routes_used)

    # 构建检测提示词
    prompt = f"""你是路由判断专家。判断用户当前查询是否需要综合分析历史对话数据。

历史对话摘要：
{conversation_summary}

当前查询：{user_query}

判断标准：
- {_SYNTHESIS_PROMPT_CRITERIA}
- 如果查询只是独立的新问题（不依赖历史数据），返回false

返回JSON格式：{{"needs_synthesis": true/false, "reason": "..."}}
"""

    # 调用LLM
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200
    )

    result_text = response.choices[0].message.content.strip()

    # 解析JSON（处理可能的markdown代码块包裹）
    try:
        # 移除可能的markdown代码块标记
        if result_text.startswith('```'):
            # 移除开头的 ```json 或 ```
            result_text = result_text.split('\n', 1)[1] if '\n' in result_text else result_text[3:]
            # 移除结尾的 ```
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()

        result = json.loads(result_text)
        needs_synthesis = result.get('needs_synthesis', False)
        reason = result.get('reason', '')
        print(f"[mixed_analysis_detector] LLM判断: needs_synthesis={needs_synthesis}, reason={reason}")
        return needs_synthesis
    except json.JSONDecodeError:
        print(f"[mixed_analysis_detector] LLM返回非JSON: {result_text}")
        # 降级策略：检查关键词
        keywords = _SYNTHESIS_KEYWORDS
        return any(kw in user_query for kw in keywords)


def _generate_conversation_summary(
    conversation_history: List[Dict],
    routes_used: Set[str]
) -> str:
    """
    生成对话历史摘要

    Args:
        conversation_history: 对话历史
        routes_used: 历史使用的路由类型

    Returns:
        摘要文本
    """
    summary_lines = [f"涉及路由: {', '.join(sorted(routes_used))}"]
    summary_lines.append("\n历史对话:")

    # 只取最近5轮（10条消息）
    recent_messages = conversation_history[-10:]

    for i, msg in enumerate(recent_messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:100]  # 截断到100字符
        route = ''
        if role == 'assistant' and 'metadata' in msg:
            route = f" [{msg['metadata'].get('route', 'unknown')}]"

        summary_lines.append(f"{i+1}. {role}{route}: {content}...")

    return '\n'.join(summary_lines)
