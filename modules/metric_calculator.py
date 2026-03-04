"""计算指标引擎：支持资产负债率、ROE、毛利率等跨域计算指标"""

# 指标公式注册表
# 每个指标定义：
#   formula: Python表达式（变量名对应sources中的key）
#   sources: 每个变量的数据来源（域+列名/表达式）
#   label: 中文名称
#   unit: 单位（%表示百分比）
METRIC_FORMULAS = {
    '资产负债率': {
        'formula': 'total_liabilities / total_assets * 100 if total_assets else None',
        'sources': {
            'total_liabilities': {
                'domain': 'balance_sheet',
                'column': 'liabilities_end',
            },
            'total_assets': {
                'domain': 'balance_sheet',
                'column': 'assets_end',
            },
        },
        'label': '资产负债率',
        'unit': '%',
    },
    '净资产收益率': {
        'formula': 'net_profit / avg_equity * 100 if avg_equity else None',
        'sources': {
            'net_profit': {
                'domain': 'profit',
                'column': 'net_profit',
                'time_range': '本年累计',
            },
            'avg_equity': {
                'domain': 'balance_sheet',
                'expression': '(equity_begin + equity_end) / 2.0',
                'columns': ['equity_begin', 'equity_end'],
            },
        },
        'label': '净资产收益率(ROE)',
        'unit': '%',
    },
    'ROE': {  # alias
        'alias': '净资产收益率',
    },
    '毛利率': {
        'formula': '(revenue - cost) / revenue * 100 if revenue else None',
        'sources': {
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
            'cost': {
                'domain': 'profit',
                'column': 'operating_cost',
            },
        },
        'label': '毛利率',
        'unit': '%',
    },
    '总资产周转率': {
        'formula': 'revenue / avg_assets if avg_assets else None',
        'sources': {
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
                'time_range': '本年累计',
            },
            'avg_assets': {
                'domain': 'balance_sheet',
                'expression': '(assets_begin + assets_end) / 2.0',
                'columns': ['assets_begin', 'assets_end'],
            },
        },
        'label': '总资产周转率',
        'unit': '次',
    },
    '净利润率': {
        'formula': 'net_profit / revenue * 100 if revenue else None',
        'sources': {
            'net_profit': {
                'domain': 'profit',
                'column': 'net_profit',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '净利润率',
        'unit': '%',
    },
    '流动比率': {
        'formula': 'current_assets / current_liabilities if current_liabilities else None',
        'sources': {
            'current_assets': {
                'domain': 'balance_sheet',
                'column': 'current_assets_end',
            },
            'current_liabilities': {
                'domain': 'balance_sheet',
                'column': 'current_liabilities_end',
            },
        },
        'label': '流动比率',
        'unit': '',
    },
    '现金债务保障比率': {
        'formula': 'operating_cash / total_liabilities * 100 if total_liabilities else None',
        'sources': {
            'operating_cash': {
                'domain': 'cash_flow',
                'column': 'operating_net_cash',
                'time_range': '本年累计',
            },
            'total_liabilities': {
                'domain': 'balance_sheet',
                'column': 'liabilities_end',
            },
        },
        'label': '现金债务保障比率',
        'unit': '%',
    },
    '管理费用率': {
        'formula': 'admin_expense / revenue * 100 if revenue else None',
        'sources': {
            'admin_expense': {
                'domain': 'profit',
                'column': 'administrative_expense',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '管理费用率',
        'unit': '%',
    },
    '销售费用率': {
        'formula': 'selling_expense / revenue * 100 if revenue else None',
        'sources': {
            'selling_expense': {
                'domain': 'profit',
                'column': 'selling_expense',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '销售费用率',
        'unit': '%',
    },
}

# 指标同义词映射
METRIC_SYNONYMS = {
    '资产负债率': '资产负债率',
    '负债率': '资产负债率',
    '净资产收益率': '净资产收益率',
    'ROE': '净资产收益率',
    '毛利率': '毛利率',
    '销售毛利率': '毛利率',
    '总资产周转率': '总资产周转率',
    '资产周转率': '总资产周转率',
    '净利润率': '净利润率',
    '销售净利率': '净利润率',
    '流动比率': '流动比率',
    '现金债务保障比率': '现金债务保障比率',
    '现金比率': '现金债务保障比率',
    '管理费用率': '管理费用率',
    '管理费用占比': '管理费用率',
    '销售费用率': '销售费用率',
    '销售费用占比': '销售费用率',
    '利润率': '净利润率',
}


def is_multi_period_query(entities: dict) -> bool:
    """检测是否为多期间查询（比较/趋势），应绕过G3单点计算。"""
    if entities.get('period_years') and len(entities['period_years']) > 1:
        return True
    if entities.get('period_end_year') and entities.get('period_year'):
        if entities['period_end_year'] != entities['period_year']:
            return True
        if entities.get('period_end_month') and entities.get('period_month'):
            if entities['period_end_month'] != entities['period_month']:
                return True
    if entities.get('time_granularity'):
        return True
    return False


def detect_computed_metrics(query: str) -> list:
    """检测查询中是否包含计算指标，返回匹配的指标名列表。"""
    found = []
    for synonym, canonical in METRIC_SYNONYMS.items():
        if synonym in query:
            metric = METRIC_FORMULAS.get(canonical)
            if metric and metric not in found:
                # 解析alias
                if 'alias' in metric:
                    canonical = metric['alias']
                    metric = METRIC_FORMULAS[canonical]
                if canonical not in found:
                    found.append(canonical)
    return found


def get_metric_required_domains(metric_names: list) -> set:
    """获取计算指标所需的所有域。"""
    domains = set()
    for name in metric_names:
        metric = METRIC_FORMULAS.get(name, {})
        if 'alias' in metric:
            metric = METRIC_FORMULAS[metric['alias']]
        for src in metric.get('sources', {}).values():
            domains.add(src['domain'])
    return domains


def compute_metric(metric_name: str, source_data: dict) -> dict:
    """根据子查询结果计算指标值。

    Args:
        metric_name: 指标名称
        source_data: {变量名: 数值} 映射

    Returns:
        {'label': str, 'value': float|None, 'unit': str, 'sources': dict}
    """
    metric = METRIC_FORMULAS.get(metric_name, {})
    if 'alias' in metric:
        metric = METRIC_FORMULAS[metric['alias']]

    formula = metric.get('formula', '')
    label = metric.get('label', metric_name)
    unit = metric.get('unit', '')

    try:
        # 检查是否有 None 值
        for var, val in source_data.items():
            if val is None:
                return {
                    'label': label,
                    'value': None,
                    'unit': unit,
                    'formula': formula,
                    'sources': source_data,
                    'error': f'缺少数据: {var}',
                }
        value = eval(formula, {"__builtins__": {}}, source_data)
        if value is not None:
            value = round(value, 2)
    except (ZeroDivisionError, TypeError, NameError, KeyError):
        value = None

    return {
        'label': label,
        'value': value,
        'unit': unit,
        'formula': formula,
        'sources': source_data,
    }
