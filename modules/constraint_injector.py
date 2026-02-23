"""约束注入器：从阶段1 JSON派生allowed_views/columns，生成阶段2 schema文本"""
import json
from modules.schema_catalog import (
    DOMAIN_VIEWS, VIEW_COLUMNS,
    EIT_ANNUAL_DIM_COLS, EIT_QUARTER_DIM_COLS,
    ACCOUNT_BALANCE_DIM_COLS, BALANCE_SHEET_DIM_COLS,
    PROFIT_DIM_COLS, CASH_FLOW_DIM_COLS, FINANCIAL_METRICS_DIM_COLS,
    INVOICE_DIM_COLS,
)
from config.settings import MAX_ROWS

# VAT 维度列
_VAT_DIM_COLS = {
    'taxpayer_id', 'taxpayer_name', 'period_year', 'period_month',
    'item_type', 'time_range', 'taxpayer_type', 'revision_no',
}

# EIT 元数据列（不作为指标展示）
_META_COLS = {
    'submitted_at', 'etl_batch_id', 'source_doc_id', 'source_unit',
    'etl_confidence', 'filing_id',
}


def inject_constraints(intent_json: dict) -> dict:
    """根据意图JSON生成约束集合"""
    domain = intent_json.get('domain', 'vat')

    # 确定允许视图
    if domain == 'cross_domain':
        # 跨域：合并所有子域的视图
        sub_domains = intent_json.get('cross_domain_list', [])
        allowed_views = []
        for sd in sub_domains:
            sd_views = DOMAIN_VIEWS.get(sd, [])
            # 如果有scope信息，使用scope中的视图
            scope_key = f'{sd}_scope'
            if intent_json.get(scope_key):
                sd_views = intent_json[scope_key].get('views', sd_views)
            for v in sd_views:
                if v not in allowed_views:
                    allowed_views.append(v)
    elif domain == 'vat' and intent_json.get('vat_scope'):
        allowed_views = intent_json['vat_scope'].get('views', DOMAIN_VIEWS.get('vat', []))
    elif domain == 'eit' and intent_json.get('eit_scope'):
        allowed_views = intent_json['eit_scope'].get('views', DOMAIN_VIEWS.get('eit', []))
    elif domain == 'account_balance':
        allowed_views = DOMAIN_VIEWS.get('account_balance', ['vw_account_balance'])
    elif domain == 'balance_sheet' and intent_json.get('balance_sheet_scope'):
        allowed_views = intent_json['balance_sheet_scope'].get('views', DOMAIN_VIEWS.get('balance_sheet', []))
    elif domain == 'balance_sheet':
        allowed_views = DOMAIN_VIEWS.get('balance_sheet', ['vw_balance_sheet_eas'])
    elif domain == 'profit' and intent_json.get('profit_scope'):
        allowed_views = intent_json['profit_scope'].get('views', DOMAIN_VIEWS.get('profit', []))
    elif domain == 'profit':
        allowed_views = DOMAIN_VIEWS.get('profit', ['vw_profit_eas'])
    elif domain == 'cash_flow' and intent_json.get('cash_flow_scope'):
        allowed_views = intent_json['cash_flow_scope'].get('views', DOMAIN_VIEWS.get('cash_flow', []))
    elif domain == 'cash_flow':
        allowed_views = DOMAIN_VIEWS.get('cash_flow', ['vw_cash_flow_eas'])
    elif domain == 'financial_metrics' and intent_json.get('financial_metrics_scope'):
        allowed_views = intent_json['financial_metrics_scope'].get('views', DOMAIN_VIEWS.get('financial_metrics', []))
    elif domain == 'financial_metrics':
        allowed_views = DOMAIN_VIEWS.get('financial_metrics', ['vw_financial_metrics'])
    elif domain == 'invoice' and intent_json.get('invoice_scope'):
        allowed_views = intent_json['invoice_scope'].get('views', DOMAIN_VIEWS.get('invoice', []))
    elif domain == 'invoice':
        allowed_views = DOMAIN_VIEWS.get('invoice', ['vw_inv_spec_purchase', 'vw_inv_spec_sales'])
    else:
        allowed_views = DOMAIN_VIEWS.get(domain, [])

    if not allowed_views:
        allowed_views = DOMAIN_VIEWS.get(domain, DOMAIN_VIEWS.get('vat', []))

    # 获取每个视图的允许列
    allowed_columns = {}
    for view in allowed_views:
        if view in VIEW_COLUMNS:
            allowed_columns[view] = VIEW_COLUMNS[view]

    # 构建阶段2注入文本
    max_rows = intent_json.get('aggregation', {}).get('limit', MAX_ROWS)
    max_rows = min(max_rows, MAX_ROWS)

    views_text = ", ".join(allowed_views)
    columns_text_parts = []
    for view, cols in allowed_columns.items():
        # 根据域/视图名选择维度列集合
        view_domain = domain
        if domain == 'cross_domain':
            # 跨域时根据视图名推断子域
            if 'vat' in view:
                view_domain = 'vat'
            elif 'eit' in view:
                view_domain = 'eit'
            elif 'balance_sheet' in view:
                view_domain = 'balance_sheet'
            elif 'profit' in view:
                view_domain = 'profit'
            elif 'cash_flow' in view:
                view_domain = 'cash_flow'
            elif 'account_balance' in view:
                view_domain = 'account_balance'
            elif 'financial_metrics' in view:
                view_domain = 'financial_metrics'
            elif 'inv' in view:
                view_domain = 'invoice'

        if view_domain == 'eit':
            if 'quarter' in view:
                dim_set = set(EIT_QUARTER_DIM_COLS)
            else:
                dim_set = set(EIT_ANNUAL_DIM_COLS)
        elif view_domain == 'account_balance':
            dim_set = set(ACCOUNT_BALANCE_DIM_COLS)
        elif view_domain == 'balance_sheet':
            dim_set = set(BALANCE_SHEET_DIM_COLS)
        elif view_domain == 'profit':
            dim_set = set(PROFIT_DIM_COLS)
        elif view_domain == 'cash_flow':
            dim_set = set(CASH_FLOW_DIM_COLS)
        elif view_domain == 'financial_metrics':
            dim_set = set(FINANCIAL_METRICS_DIM_COLS)
        elif view_domain == 'invoice':
            dim_set = set(INVOICE_DIM_COLS)
        else:
            dim_set = _VAT_DIM_COLS

        dim_cols = [c for c in cols if c in dim_set]
        indicator_cols = [c for c in cols if c not in dim_set and c not in _META_COLS]
        columns_text_parts.append(
            f"{view}:\n  维度: {', '.join(dim_cols)}\n  指标: {', '.join(indicator_cols)}"
        )

    return {
        'allowed_views': allowed_views,
        'allowed_columns': allowed_columns,
        'max_rows': max_rows,
        'allowed_views_text': views_text,
        'allowed_columns_text': "\n".join(columns_text_parts),
        'intent_json_text': json.dumps(intent_json, ensure_ascii=False, indent=2),
    }
