"""对话上下文管理器：准备对话历史、实体继承、上下文依赖检测"""
import re
from typing import List, Dict, Optional


def prepare_conversation_context(
    history: List[Dict],
    max_turns: int = 3,
    token_budget: int = 4000
) -> List[Dict]:
    """
    准备对话历史供LLM使用

    Args:
        history: 完整对话历史 [{"role": "user|assistant", "content": str, ...}, ...]
        max_turns: 最大轮次（1轮=2条消息：user+assistant）
        token_budget: 预留token数（粗略估算：1 token ≈ 1.5字符）

    Returns:
        截断后的对话历史（最近N轮）
    """
    if not history:
        return []

    # 滑动窗口：取最近N轮（N*2条消息）
    max_messages = max_turns * 2
    recent_history = history[-max_messages:]

    # Token预算检查（粗略估算）
    total_chars = sum(len(msg.get('content', '')) for msg in recent_history)
    estimated_tokens = int(total_chars / 1.5)

    if estimated_tokens > token_budget:
        # 智能截断：优先保留最近1轮完整对话
        if len(recent_history) >= 2:
            # 保留最后1轮
            truncated = recent_history[-2:]
            return truncated

    return recent_history


def extract_last_turn_entities(history: List[Dict]) -> dict:
    """
    从最后一轮助手回复中提取实体（用于上下文继承）

    Args:
        history: 对话历史

    Returns:
        实体字典 {taxpayer_id, taxpayer_name, period_year, period_month, domain, ...}
    """
    if not history:
        return {}

    # 找到最后一条assistant消息
    last_assistant = None
    for msg in reversed(history):
        if msg.get('role') == 'assistant':
            last_assistant = msg
            break

    if not last_assistant:
        return {}

    # 从metadata中提取实体
    metadata = last_assistant.get('metadata', {})
    entities = metadata.get('entities', {})

    return entities


def is_context_dependent(query: str) -> bool:
    """
    检测查询是否依赖对话上下文

    检测规则：
    1. 代词：它/那/这个/这家/该/上述
    2. 隐式时间：呢/那/其他/还有
    3. 对比：对比/比较/差异/变化

    Args:
        query: 用户查询

    Returns:
        True if 依赖上下文, False otherwise
    """
    # 代词模式
    pronoun_patterns = [
        r'它[的]?',
        r'那[个家]?',
        r'这[个家]?',
        r'该[公司企业]?',
        r'上述',
    ]

    # 隐式时间模式
    implicit_time_patterns = [
        r'呢[？?]?$',  # 结尾的"呢"
        r'^那[？?]?$',  # 单独的"那"
        r'其他[月年季度]',
        r'还有[什么哪]',
    ]

    # 对比模式
    comparison_patterns = [
        r'对比',
        r'比较',
        r'差异',
        r'变化',
        r'增长',
        r'下降',
    ]

    all_patterns = pronoun_patterns + implicit_time_patterns + comparison_patterns

    for pattern in all_patterns:
        if re.search(pattern, query):
            return True

    return False


def _contains_pronouns(query: str) -> bool:
    """检测查询是否包含代词"""
    pronoun_patterns = [
        r'它[的]?',
        r'那[个家]?',
        r'这[个家]?',
        r'该[公司企业]?',
        r'上述',
    ]

    for pattern in pronoun_patterns:
        if re.search(pattern, query):
            return True

    return False


def _get_last_assistant_turn(history: List[Dict]) -> Optional[Dict]:
    """获取最后一条assistant消息"""
    if not history:
        return None

    for msg in reversed(history):
        if msg.get('role') == 'assistant':
            return msg

    return None


def _resolve_pronouns(query: str, history: List[Dict]) -> dict:
    """
    代词解析：将"它/那/这个"解析为具体实体

    Args:
        query: 包含代词的查询
        history: 对话历史

    Returns:
        解析后的实体字典
    """
    last_turn = _get_last_assistant_turn(history)
    if not last_turn:
        return {}

    prev_entities = last_turn.get('metadata', {}).get('entities', {})

    resolved = {}

    # 如果查询包含"它/那/这个"，继承纳税人信息
    if _contains_pronouns(query):
        if prev_entities.get('taxpayer_id'):
            resolved['taxpayer_id'] = prev_entities['taxpayer_id']
        if prev_entities.get('taxpayer_name'):
            resolved['taxpayer_name'] = prev_entities['taxpayer_name']
        if prev_entities.get('taxpayer_type'):
            resolved['taxpayer_type'] = prev_entities['taxpayer_type']

    return resolved


def _is_domain_neutral(query: str) -> bool:
    """
    检测查询是否不指定域（需要继承域）

    域中性查询示例：
    - "2月呢？"
    - "那个指标"
    - "其他月份"
    """
    # 域关键词（如果包含这些，说明指定了域）
    domain_keywords = [
        '增值税', 'VAT', '所得税', 'EIT',
        '资产负债表', '利润表', '现金流量表',
        '科目余额', '发票',
        '财务指标', '毛利率', 'ROE',
    ]

    for keyword in domain_keywords:
        if keyword in query:
            return False

    return True
