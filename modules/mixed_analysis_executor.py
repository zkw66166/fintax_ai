"""
混合分析执行器 - 执行跨路由混合多轮查询的综合分析

从对话历史中提取不同路由的数据，调用LLM进行税务筹划专家级别的综合分析。
"""
import json
from typing import List, Dict, Generator
from collections import defaultdict
from datetime import datetime
from config.settings import (
    LLM_API_KEY,
    LLM_API_BASE,
    MIXED_ANALYSIS_LLM_MODEL,
    MIXED_ANALYSIS_MAX_CONTEXT_TOKENS,
    MIXED_ANALYSIS_STREAM_CHUNK_SIZE
)
from openai import OpenAI


def execute_mixed_analysis_stream(
    user_query: str,
    conversation_history: List[Dict],
    conversation_depth: int,
    taxpayer_id: str = None
) -> Generator[Dict, None, None]:
    """
    执行混合分析，流式返回结果

    Args:
        user_query: 当前用户查询
        conversation_history: 对话历史
        conversation_depth: 对话轮数
        taxpayer_id: 纳税人ID（可选）

    Yields:
        {'type': 'stage', 'text': '...'}
        {'type': 'chunk', 'text': '...'}
        {'type': 'done', 'result': {...}}
    """
    # 1. 提取历史数据
    yield {'type': 'stage', 'text': '正在提取历史对话数据...'}
    try:
        context_data = extract_context_data(conversation_history, conversation_depth)
    except Exception as e:
        yield {
            'type': 'done',
            'result': {
                'route': 'mixed_analysis',
                'error': f'历史数据提取失败: {str(e)}',
                'analysis': f'抱歉，无法提取历史对话数据。错误信息：{str(e)}'
            }
        }
        return

    # 2. 构建综合分析提示词
    yield {'type': 'stage', 'text': '正在构建分析上下文...'}
    try:
        analysis_prompt = build_analysis_prompt(
            user_query=user_query,
            context_data=context_data,
            taxpayer_id=taxpayer_id
        )
    except Exception as e:
        yield {
            'type': 'done',
            'result': {
                'route': 'mixed_analysis',
                'error': f'提示词构建失败: {str(e)}',
                'analysis': f'抱歉，无法构建分析提示词。错误信息：{str(e)}'
            }
        }
        return

    # 3. 调用LLM流式分析
    yield {'type': 'stage', 'text': '正在进行综合分析...'}
    full_analysis_text = ''
    try:
        for chunk in llm_stream_analysis(analysis_prompt):
            full_analysis_text += chunk
            yield {'type': 'chunk', 'text': chunk}
    except Exception as e:
        yield {
            'type': 'done',
            'result': {
                'route': 'mixed_analysis',
                'error': f'LLM分析失败: {str(e)}',
                'analysis': f'抱歉，综合分析过程中出现错误。错误信息：{str(e)}'
            }
        }
        return

    # 4. 返回最终结果
    yield {
        'type': 'done',
        'result': {
            'route': 'mixed_analysis',
            'analysis': full_analysis_text,
            'context_summary': context_data['summary'],
            'routes_used': context_data['routes'],
            'timestamp': datetime.now().isoformat()
        }
    }


def extract_context_data(
    conversation_history: List[Dict],
    depth: int
) -> Dict:
    """
    从对话历史中提取所需数据

    Args:
        conversation_history: 对话历史
        depth: 对话轮数

    Returns:
        {
            'routes': ['financial_data', 'tax_incentive'],
            'summary': '...',
            'financial_data': [...],  # 财务查询结果
            'tax_incentive': [...],   # 税收优惠政策
            'regulation': [...]       # 法规知识
        }
    """
    # 按路由分组
    data_by_route = defaultdict(list)

    # 取最近 depth*2 条消息（每轮包含 user + assistant）
    recent_messages = conversation_history[-(depth * 2):]

    for i, msg in enumerate(recent_messages):
        if msg.get('role') == 'user':
            # 记录用户问题
            user_query = msg.get('content', '')
            # 查找对应的assistant回答
            if i + 1 < len(recent_messages) and recent_messages[i + 1].get('role') == 'assistant':
                assistant_msg = recent_messages[i + 1]
                route = assistant_msg.get('metadata', {}).get('route', 'unknown')
                result_content = assistant_msg.get('content', '')

                data_by_route[route].append({
                    'query': user_query,
                    'result': result_content,
                    'timestamp': assistant_msg.get('timestamp', ''),
                    'metadata': assistant_msg.get('metadata', {})
                })

    routes = list(data_by_route.keys())
    summary = _generate_summary(data_by_route)

    return {
        'routes': routes,
        'summary': summary,
        **data_by_route
    }


def _generate_summary(data_by_route: Dict[str, List[Dict]]) -> str:
    """
    生成历史数据摘要

    Args:
        data_by_route: 按路由分组的数据

    Returns:
        摘要文本
    """
    summary_lines = []

    for route, entries in data_by_route.items():
        route_name_map = {
            'financial_data': '财务数据查询',
            'tax_incentive': '税收优惠政策',
            'regulation': '法规知识库'
        }
        route_name = route_name_map.get(route, route)
        summary_lines.append(f"\n【{route_name}】({len(entries)}轮)")

        for i, entry in enumerate(entries, 1):
            query = entry['query'][:50]
            result = entry['result'][:100]
            summary_lines.append(f"  {i}. 问：{query}...")
            summary_lines.append(f"     答：{result}...")

    return '\n'.join(summary_lines)


def build_analysis_prompt(
    user_query: str,
    context_data: Dict,
    taxpayer_id: str = None
) -> str:
    """
    构建综合分析提示词

    Args:
        user_query: 当前用户查询
        context_data: 历史上下文数据
        taxpayer_id: 纳税人ID（可选）

    Returns:
        完整的提示词文本
    """
    # 读取税务筹划专家提示词模板
    try:
        with open('prompts/mixed_analysis_tax_planning.txt', 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        # 降级：使用内置模板
        template = _get_default_template()

    # 格式化历史数据
    context_text = _format_context_data(context_data)

    # 替换占位符
    prompt = template.replace('{context_data}', context_text)
    prompt = prompt.replace('{user_query}', user_query)

    if taxpayer_id:
        prompt += f"\n\n注：当前企业纳税人识别号为 {taxpayer_id}"

    return prompt


def _format_context_data(context_data: Dict) -> str:
    """
    格式化历史上下文数据为可读文本

    Args:
        context_data: 历史上下文数据

    Returns:
        格式化后的文本
    """
    lines = []

    # 按路由分组展示
    for route in context_data['routes']:
        if route == 'unknown':
            continue

        route_name_map = {
            'financial_data': '📊 财务数据查询',
            'tax_incentive': '📋 税收优惠政策',
            'regulation': '📚 法规知识库'
        }
        route_name = route_name_map.get(route, route)
        lines.append(f"\n## {route_name}\n")

        entries = context_data.get(route, [])
        for i, entry in enumerate(entries, 1):
            lines.append(f"### 第{i}轮")
            lines.append(f"**用户问题**：{entry['query']}")
            lines.append(f"**系统回答**：\n{entry['result']}\n")

    return '\n'.join(lines)


def llm_stream_analysis(prompt: str) -> Generator[str, None, None]:
    """
    调用LLM进行流式综合分析

    Args:
        prompt: 完整的提示词

    Yields:
        文本片段
    """
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)

    response = client.chat.completions.create(
        model=MIXED_ANALYSIS_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=MIXED_ANALYSIS_MAX_CONTEXT_TOKENS,
        stream=True
    )

    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _get_default_template() -> str:
    """
    获取默认的税务筹划专家提示词模板（降级方案）

    Returns:
        模板文本
    """
    return """你是一位资深的税务筹划专家和财务数据分析师，拥有20年的企业财税咨询经验。

# 你的专业能力
- 深入理解中国税法和税收优惠政策
- 精通财务报表分析和财务指标解读
- 擅长发现税收筹划机会和财务优化空间
- 能够识别税务风险并提供合规建议

# 当前任务
用户在多轮对话中提供了以下信息：

## 历史对话数据
{context_data}

## 当前问题
{user_query}

# 分析要求
请基于上述历史数据，进行系统性综合分析，重点关注：

1. **数据匹配分析**
   - 企业实际财务数据与税收优惠政策的适用条件是否匹配
   - 哪些优惠政策可以直接适用
   - 哪些政策需要满足额外条件

2. **风险识别**
   - 当前财务数据是否存在税务风险点
   - 是否存在政策适用误区
   - 合规性问题提示

3. **税收筹划建议**
   - 基于现有数据，可以采取哪些合法的税收筹划措施
   - 如何优化业务结构以享受更多优惠
   - 预计可节税金额（如果数据充分）

4. **财务优化建议**
   - 财务指标改善方向
   - 资产负债结构优化
   - 现金流管理建议

5. **行动计划**
   - 短期（1-3个月）可执行的具体措施
   - 中期（3-12个月）筹划方向
   - 需要补充的数据或材料

# 输出格式
请使用清晰的结构化格式输出，包含：
- 📊 数据概览
- ✅ 可适用政策
- ⚠️ 风险提示
- 💡 筹划建议
- 📈 优化方向
- 🎯 行动计划

# 注意事项
- 所有建议必须合法合规
- 基于实际数据进行分析，不做无根据推测
- 如果数据不足，明确指出需要补充的信息
- 使用专业但易懂的语言
"""
