"""阶段2：LLM SQL生成（在白名单约束内，域感知）"""
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


def generate_sql(constraints: dict, retry_feedback: str = None, domain: str = 'vat') -> str:
    """调用LLM阶段2，生成SQL（根据域选择prompt模板）"""
    prompt_file = _DOMAIN_PROMPT_MAP.get(domain, 'stage2_vat.txt')
    template = (PROMPTS_DIR / prompt_file).read_text(encoding='utf-8')

    system_prompt = template.format(
        allowed_views_text=constraints['allowed_views_text'],
        allowed_columns_text=constraints['allowed_columns_text'],
        max_rows=constraints['max_rows'],
        intent_json=constraints['intent_json_text'],
    )

    user_msg = "请根据上述意图JSON和schema约束，生成SQLite SQL。只输出SQL，不要解释。"
    if retry_feedback:
        user_msg += f"\n\n上次生成的SQL审核失败，原因：{retry_feedback}\n请修正后重新生成。"

    client = _get_client()

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        sql = resp.choices[0].message.content.strip()
        # 清理markdown代码块
        if sql.startswith('```'):
            lines = sql.split('\n')
            sql = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        return sql.strip()
    except Exception as e:
        raise RuntimeError(f"SQL生成LLM调用失败: {e}")
