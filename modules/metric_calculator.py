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
    # ========== 新增指标（2026-03-10 Phase 3）==========
    # 比例型指标（8个）
    '流动资产占比': {
        'formula': 'current_assets / total_assets * 100 if total_assets else None',
        'sources': {
            'current_assets': {
                'domain': 'balance_sheet',
                'column': 'current_assets_end',
            },
            'total_assets': {
                'domain': 'balance_sheet',
                'column': 'assets_end',
            },
        },
        'label': '流动资产占比',
        'unit': '%',
    },
    '固定资产占比': {
        'formula': 'fixed_assets / total_assets * 100 if total_assets else None',
        'sources': {
            'fixed_assets': {
                'domain': 'balance_sheet',
                'column': 'fixed_assets_end',
            },
            'total_assets': {
                'domain': 'balance_sheet',
                'column': 'assets_end',
            },
        },
        'label': '固定资产占比',
        'unit': '%',
    },
    '流动负债占比': {
        'formula': 'current_liabilities / total_liabilities * 100 if total_liabilities else None',
        'sources': {
            'current_liabilities': {
                'domain': 'balance_sheet',
                'column': 'current_liabilities_end',
            },
            'total_liabilities': {
                'domain': 'balance_sheet',
                'column': 'liabilities_end',
            },
        },
        'label': '流动负债占比',
        'unit': '%',
    },
    '营业成本占比': {
        'formula': 'cost / revenue * 100 if revenue else None',
        'sources': {
            'cost': {
                'domain': 'profit',
                'column': 'operating_cost',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '营业成本占比',
        'unit': '%',
    },
    '期间费用占比': {
        'formula': '(admin + selling + finance) / revenue * 100 if revenue else None',
        'sources': {
            'admin': {
                'domain': 'profit',
                'column': 'administrative_expense',
            },
            'selling': {
                'domain': 'profit',
                'column': 'selling_expense',
            },
            'finance': {
                'domain': 'profit',
                'column': 'financial_expense',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '期间费用占比',
        'unit': '%',
    },
    '研发费用占比': {
        'formula': 'rd_expense / revenue * 100 if revenue else None',
        'sources': {
            'rd_expense': {
                'domain': 'profit',
                'column': 'rd_expense',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
            },
        },
        'label': '研发费用占比',
        'unit': '%',
    },
    '进项税额占比': {
        'formula': 'input_tax / output_tax * 100 if output_tax else None',
        'sources': {
            'input_tax': {
                'domain': 'vat',
                'column': 'input_tax',
            },
            'output_tax': {
                'domain': 'vat',
                'column': 'output_tax',
            },
        },
        'label': '进项税额占比',
        'unit': '%',
    },
    '留抵税额占比': {
        'formula': 'carryover_tax / output_tax * 100',
        'sources': {
            'carryover_tax': {
                'domain': 'vat',
                'column': 'carryover_tax_end',
            },
            'output_tax': {
                'domain': 'vat',
                'column': 'output_tax',
            },
        },
        'label': '留抵税额占比',
        'unit': '%',
    },
    '产权比率': {
        'formula': 'total_liabilities / equity',
        'sources': {
            'total_liabilities': {
                'domain': 'balance_sheet',
                'column': 'total_liabilities_end',
            },
            'equity': {
                'domain': 'balance_sheet',
                'column': 'equity_end',
            },
        },
        'label': '产权比率',
        'unit': '',
    },
    '权益乘数': {
        'formula': 'total_assets / equity',
        'sources': {
            'total_assets': {
                'domain': 'balance_sheet',
                'column': 'total_assets_end',
            },
            'equity': {
                'domain': 'balance_sheet',
                'column': 'equity_end',
            },
        },
        'label': '权益乘数',
        'unit': '',
    },
    '营业利润率': {
        'formula': 'operating_profit / revenue * 100',
        'sources': {
            'operating_profit': {
                'domain': 'profit',
                'column': 'operating_profit',
                'time_range': '本年累计',
            },
            'revenue': {
                'domain': 'profit',
                'column': 'operating_revenue',
                'time_range': '本年累计',
            },
        },
        'label': '营业利润率',
        'unit': '%',
    },
    '成本费用利润率': {
        'formula': 'total_profit / (cost + admin + selling + finance) * 100',
        'sources': {
            'total_profit': {
                'domain': 'profit',
                'column': 'total_profit',
                'time_range': '本年累计',
            },
            'cost': {
                'domain': 'profit',
                'column': 'operating_cost',
                'time_range': '本年累计',
            },
            'admin': {
                'domain': 'profit',
                'column': 'admin_expense',
                'time_range': '本年累计',
            },
            'selling': {
                'domain': 'profit',
                'column': 'selling_expense',
                'time_range': '本年累计',
            },
            'finance': {
                'domain': 'profit',
                'column': 'finance_expense',
                'time_range': '本年累计',
            },
        },
        'label': '成本费用利润率',
        'unit': '%',
    },
    '总资产报酬率': {
        'formula': 'net_profit / avg_assets * 100',
        'sources': {
            'net_profit': {
                'domain': 'profit',
                'column': 'net_profit',
                'time_range': '本年累计',
            },
            'avg_assets': {
                'domain': 'balance_sheet',
                'column': 'total_assets_end',
                'aggregate': 'AVG',
            },
        },
        'label': '总资产报酬率',
        'unit': '%',
    },
    'ROA': {
        'alias': '总资产报酬率',
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
    # 新增指标同义词（2026-03-10）
    '流动资产占比': '流动资产占比',
    '固定资产占比': '固定资产占比',
    '流动负债占比': '流动负债占比',
    '营业成本占比': '营业成本占比',
    '期间费用占比': '期间费用占比',
    '研发费用占比': '研发费用占比',
    '研发占比': '研发费用占比',
    '进项税额占比': '进项税额占比',
    '留抵税额占比': '留抵税额占比',
    '产权比率': '产权比率',
    '权益乘数': '权益乘数',
    '营业利润率': '营业利润率',
    '成本费用利润率': '成本费用利润率',
    '总资产报酬率': '总资产报酬率',
    'ROA': '总资产报酬率',
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


def extract_all_rate_metrics(query: str) -> list:
    """提取查询中所有'率'型指标（包括计算指标和存储指标）。

    用于 financial_metrics 域锁定场景，需要提取所有用户请求的指标名称。

    Returns:
        指标名称列表（去重）
    """
    import re

    # 2026-03-17: 直接匹配的已知率型指标名称（优先级最高，无需regex）
    # 解决短指标名（毛利率、净利率等）因前缀长度要求无法被regex匹配的问题
    _KNOWN_RATE_METRICS = [
        '增值税税负率', '企业所得税税负率', '综合税负率', '所得税税负率',
        '毛利率', '净利率', '利润率', '净利润率', '营业利润率', '成本费用利润率', '销售净利率',
        '资产负债率', '产权比率', '流动比率', '速动比率',
        '净资产收益率', '总资产报酬率', '总资产收益率',
        '应收账款周转率', '存货周转率', '总资产周转率',
        '营业收入增长率', '收入增长率', '净利润增长率', '利润增长率', '资产增长率', '总资产增长率',
        '管理费用率', '销售费用率', '期间费用率',
        '销项进项配比率', '进项税额转出占比', '应税所得率', '零申报率',
        '发票开具异常率', '发票异常率', '顶额开具率',
        '权益乘数', '利息保障倍数', '现金债务保障比率', '现金流量利息保障倍数',
        '销售收现比', '长期资本负债率',
        'ROE', 'ROA',
    ]

    found = []

    # 阶段1: 直接匹配已知指标名（按名称长度降序，优先匹配长名称避免子串冲突）
    sorted_known = sorted(_KNOWN_RATE_METRICS, key=len, reverse=True)
    remaining_query = query
    for metric_name in sorted_known:
        if metric_name in remaining_query:
            if metric_name not in found:
                found.append(metric_name)
            # 从查询中移除已匹配的指标名，防止子串被后续regex重复匹配
            remaining_query = remaining_query.replace(metric_name, '')

    # 阶段2: regex模式兜底匹配（在remaining_query上，捕获阶段1未覆盖的率型指标）
    rate_patterns = [
        r'([\u4e00-\u9fa5]{2,8}税负率)',  # X税负率（2-8个汉字）
        r'([\u4e00-\u9fa5]{2,8}利润率)',  # X利润率
        r'([\u4e00-\u9fa5]{2,8}资产收益率)',  # X资产收益率
        r'([\u4e00-\u9fa5]{2,8}负债率)',  # X负债率
        r'([\u4e00-\u9fa5]{2,8}周转率)',  # X周转率
        r'([\u4e00-\u9fa5]{2,8}费用率)',  # X费用率
        r'([\u4e00-\u9fa5]{2,8}毛利率)',  # X毛利率
        r'([\u4e00-\u9fa5]{2,8}净利率)',  # X净利率
        r'([\u4e00-\u9fa5]{2,8}比率)',  # X比率
        r'([\u4e00-\u9fa5]{2,8}增长率)',  # X增长率
        r'(ROE|ROA)',  # 英文缩写
    ]

    for pattern in rate_patterns:
        matches = re.findall(pattern, remaining_query)
        for match in matches:
            if re.search(r'\d', match):
                continue
            if '和' in match:
                continue
            if match not in found:
                found.append(match)

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
