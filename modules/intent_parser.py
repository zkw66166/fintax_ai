"""阶段1：LLM意图解析 → 严格JSON（域感知）"""
import json
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


def parse_intent(user_query: str, entities: dict, synonym_hits: list) -> dict:
    """调用LLM阶段1，返回意图JSON"""
    system_prompt = (PROMPTS_DIR / "stage1_system.txt").read_text(encoding='utf-8')

    # 构造用户消息
    entity_info = []
    if entities.get('taxpayer_id'):
        entity_info.append(f"taxpayer_id={entities['taxpayer_id']}")
    if entities.get('taxpayer_name'):
        entity_info.append(f"taxpayer_name={entities['taxpayer_name']}")
    if entities.get('taxpayer_type'):
        entity_info.append(f"taxpayer_type={entities['taxpayer_type']}")
    if entities.get('period_year'):
        entity_info.append(f"period_year={entities['period_year']}")
    if entities.get('period_month'):
        entity_info.append(f"period_month={entities['period_month']}")
    if entities.get('period_end_month'):
        entity_info.append(f"period_end_month={entities['period_end_month']}")
    if entities.get('period_end_year'):
        entity_info.append(f"period_end_year={entities['period_end_year']}")
    if entities.get('period_years'):
        entity_info.append(f"period_years={entities['period_years']}")
    if entities.get('period_months'):
        entity_info.append(f"period_months={entities['period_months']}")
    if entities.get('period_quarter'):
        entity_info.append(f"period_quarter={entities['period_quarter']}")
    if entities.get('all_quarters'):
        entity_info.append("all_quarters=true（各季度/每个季度，查询全部4个季度，不需要澄清）")
    if entities.get('domain_hint'):
        entity_info.append(f"domain_hint={entities['domain_hint']}")

    hit_info = ""
    if synonym_hits:
        hit_info = "\n同义词命中: " + ", ".join(
            f"{h['phrase']}→{h['column_name']}" for h in synonym_hits
        )

    user_msg = f"用户问题: {user_query}\n已识别实体: {', '.join(entity_info)}{hit_info}\n\n请输出JSON。"

    client = _get_client()

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )
        content = resp.choices[0].message.content.strip()
        intent = json.loads(content)

        # 基本校验 — 域默认值
        domain_hint = entities.get('domain_hint')
        if 'domain' not in intent:
            intent['domain'] = domain_hint or 'vat'

        if 'need_clarification' not in intent:
            intent['need_clarification'] = False
        if 'select' not in intent:
            intent['select'] = {'metrics': [], 'dimensions': []}
        if 'filters' not in intent:
            intent['filters'] = {}
        if 'aggregation' not in intent:
            intent['aggregation'] = {'group_by': [], 'order_by': [], 'limit': 1000}

        # EIT域默认值
        if intent['domain'] == 'eit' and not intent.get('eit_scope'):
            # 根据是否有季度信息判断报表类型
            if entities.get('period_quarter'):
                intent['eit_scope'] = {
                    'report_type': 'quarter',
                    'views': ['vw_eit_quarter_main'],
                }
            else:
                intent['eit_scope'] = {
                    'report_type': 'annual',
                    'views': ['vw_eit_annual_main'],
                }

        # 资产负债表域默认值
        if intent['domain'] == 'balance_sheet' and not intent.get('balance_sheet_scope'):
            # 根据纳税人类型/会计准则判断GAAP类型
            taxpayer_type = entities.get('taxpayer_type')
            if taxpayer_type == '小规模纳税人':
                intent['balance_sheet_scope'] = {
                    'gaap_type': 'ASSE',
                    'views': ['vw_balance_sheet_sas'],
                }
            else:
                intent['balance_sheet_scope'] = {
                    'gaap_type': 'ASBE',
                    'views': ['vw_balance_sheet_eas'],
                }

        # 利润表域默认值
        if intent['domain'] == 'profit' and not intent.get('profit_scope'):
            taxpayer_type = entities.get('taxpayer_type')
            if taxpayer_type == '小规模纳税人':
                intent['profit_scope'] = {
                    'accounting_standard': 'SAS',
                    'views': ['vw_profit_sas'],
                }
            else:
                intent['profit_scope'] = {
                    'accounting_standard': 'ASBE',
                    'views': ['vw_profit_eas'],
                }

        # 现金流量表域默认值
        if intent['domain'] == 'cash_flow' and not intent.get('cash_flow_scope'):
            taxpayer_type = entities.get('taxpayer_type')
            if taxpayer_type == '小规模纳税人':
                intent['cash_flow_scope'] = {
                    'accounting_standard': '小企业会计准则',
                    'views': ['vw_cash_flow_sas'],
                }
            else:
                intent['cash_flow_scope'] = {
                    'accounting_standard': '企业会计准则',
                    'views': ['vw_cash_flow_eas'],
                }

        # 财务指标域默认值
        if intent['domain'] == 'financial_metrics' and not intent.get('financial_metrics_scope'):
            intent['financial_metrics_scope'] = {
                'views': ['vw_financial_metrics'],
            }

        # 跨域查询处理：
        # 1. entity_preprocessor检测到cross_domain时，强制使用其cross_domain_list
        # 2. LLM返回cross_domain但entity_preprocessor未检测到时，也需要设置scope
        if domain_hint == 'cross_domain':
            intent['domain'] = 'cross_domain'
            # 优先使用entity_preprocessor检测的子域列表
            cross_list = entities.get('cross_domain_list', [])
            intent['cross_domain_list'] = cross_list
        elif intent.get('domain') == 'cross_domain':
            # LLM自行判断为跨域（如用户有错别字导致entity_preprocessor未检测到）
            cross_list = intent.get('cross_domain_list', [])
            if not cross_list:
                # 从LLM返回的scope中推断子域列表
                _all_domains = ['vat', 'eit', 'balance_sheet', 'profit',
                                'cash_flow', 'account_balance', 'financial_metrics']
                cross_list = [d for d in _all_domains
                              if intent.get(f'{d}_scope') and
                              intent[f'{d}_scope'] not in (None, {}, {'views': []})]
                intent['cross_domain_list'] = cross_list

        # 统一为跨域查询设置默认scope
        if intent.get('domain') == 'cross_domain':
            cross_list = intent.get('cross_domain_list', [])
            taxpayer_type = entities.get('taxpayer_type')
            for sd in cross_list:
                scope_key = f'{sd}_scope'
                # 确保每个子域的scope中有正确的views
                existing_scope = intent.get(scope_key)
                if not existing_scope or not existing_scope.get('views'):
                    if sd == 'vat':
                        if taxpayer_type == '小规模纳税人':
                            intent[scope_key] = {
                                'taxpayer_type_hint': '小规模纳税人',
                                'views': ['vw_vat_return_small'],
                            }
                        else:
                            intent[scope_key] = {
                                'taxpayer_type_hint': '一般纳税人',
                                'views': ['vw_vat_return_general'],
                            }
                    elif sd == 'eit':
                        if entities.get('period_quarter'):
                            intent[scope_key] = {
                                'report_type': 'quarter',
                                'views': ['vw_eit_quarter_main'],
                            }
                        else:
                            intent[scope_key] = {
                                'report_type': 'annual',
                                'views': ['vw_eit_annual_main'],
                            }
                    elif sd == 'balance_sheet':
                        if taxpayer_type == '小规模纳税人':
                            intent[scope_key] = {
                                'gaap_type': 'ASSE',
                                'views': ['vw_balance_sheet_sas'],
                            }
                        else:
                            intent[scope_key] = {
                                'gaap_type': 'ASBE',
                                'views': ['vw_balance_sheet_eas'],
                            }
                    elif sd == 'profit':
                        if taxpayer_type == '小规模纳税人':
                            intent[scope_key] = {
                                'accounting_standard': 'SAS',
                                'views': ['vw_profit_sas'],
                            }
                        else:
                            intent[scope_key] = {
                                'accounting_standard': 'ASBE',
                                'views': ['vw_profit_eas'],
                            }
                    elif sd == 'cash_flow':
                        if taxpayer_type == '小规模纳税人':
                            intent[scope_key] = {
                                'accounting_standard': '小企业会计准则',
                                'views': ['vw_cash_flow_sas'],
                            }
                        else:
                            intent[scope_key] = {
                                'accounting_standard': '企业会计准则',
                                'views': ['vw_cash_flow_eas'],
                            }
                    elif sd == 'account_balance':
                        intent[scope_key] = {'views': ['vw_account_balance']}
                    elif sd == 'financial_metrics':
                        intent[scope_key] = {'views': ['vw_financial_metrics']}

        return intent

    except json.JSONDecodeError as e:
        fallback_domain = entities.get('domain_hint', 'vat')
        return {
            'domain': fallback_domain,
            'need_clarification': True,
            'clarifying_questions': [f'意图解析失败，请重新描述您的问题。(JSON解析错误: {e})'],
            'select': {'metrics': [], 'dimensions': []},
            'filters': {},
            'aggregation': {'group_by': [], 'order_by': [], 'limit': 1000},
        }
    except Exception as e:
        fallback_domain = entities.get('domain_hint', 'vat')
        return {
            'domain': fallback_domain,
            'need_clarification': True,
            'clarifying_questions': [f'LLM调用失败: {e}'],
            'select': {'metrics': [], 'dimensions': []},
            'filters': {},
            'aggregation': {'group_by': [], 'order_by': [], 'limit': 1000},
        }
