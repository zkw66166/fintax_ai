"""阶段2：LLM SQL生成（在白名单约束内，域感知）"""
from typing import List, Dict, Optional
from openai import OpenAI
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import LLM_API_KEY, LLM_API_BASE, LLM_MODEL, LLM_TIMEOUT, PROMPTS_DIR

# 模块级OpenAI客户端单例（复用httpx连接池）
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE, timeout=LLM_TIMEOUT)
    return _client

# 域 → prompt模板映射
_DOMAIN_PROMPT_MAP = {
    'vat': 'stage2_vat.txt',
    'eit': 'stage2_eit.txt',
    'account_balance': 'stage2_account_balance.txt',
    'balance_sheet': 'stage2_balance_sheet.txt',
    'profit': 'stage2_profit.txt',
    'cash_flow': 'stage2_cash_flow.txt',
    'cross_domain': 'stage2_cross_domain.txt',
    'financial_metrics': 'stage2_financial_metrics.txt',
    'invoice': 'stage2_invoice.txt',
}


def generate_sql(constraints: dict, retry_feedback: str = None, domain: str = 'vat', conversation_history: Optional[List[Dict]] = None) -> str:
    """调用LLM阶段2，生成SQL（根据域选择prompt模板）

    Args:
        constraints: 约束字典
        retry_feedback: 重试反馈（可选）
        domain: 域名称
        conversation_history: 对话历史（可选）

    Returns:
        生成的SQL字符串
    """
    from typing import List, Dict, Optional

    prompt_file = _DOMAIN_PROMPT_MAP.get(domain, 'stage2_vat.txt')
    template = (PROMPTS_DIR / prompt_file).read_text(encoding='utf-8')

    system_prompt = template.format(
        allowed_views_text=constraints['allowed_views_text'],
        allowed_columns_text=constraints['allowed_columns_text'],
        max_rows=constraints['max_rows'],
        intent_json=constraints['intent_json_text'],
    )

    user_msg = "请根据上述意图JSON和schema约束，生成SQLite SQL。只输出SQL，不要解释。"
    if constraints.get('user_query'):
        user_msg = f"用户原始问题：{constraints['user_query']}\n\n" + user_msg
    if retry_feedback:
        user_msg += f"\n\n上次生成的SQL审核失败，原因：{retry_feedback}\n请修正后重新生成。"

    client = _get_client()

    try:
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 添加上一轮的SQL作为上下文（如果有）
        if conversation_history and len(conversation_history) >= 2:
            last_user = conversation_history[-2]
            last_assistant = conversation_history[-1]
            last_sql = last_assistant.get('metadata', {}).get('sql', '')
            if last_sql:
                messages.append({"role": "user", "content": last_user["content"]})
                messages.append({"role": "assistant", "content": f"-- 上一轮生成的SQL\n{last_sql}"})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_msg})

        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,  # 多轮上下文
            temperature=0.1,
            max_tokens=2000,
            stream=True,
        )
        sql = ""
        for chunk in resp:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                sql += delta.content
        sql = sql.strip()
        # 清理markdown代码块
        if sql.startswith('```'):
            lines = sql.split('\n')
            sql = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        return sql.strip()
    except Exception as e:
        raise RuntimeError(f"SQL生成LLM调用失败: {e}")
