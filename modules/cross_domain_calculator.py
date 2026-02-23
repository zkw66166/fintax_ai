"""跨域计算引擎：支持差异比较、比率计算、勾稽核对等跨域操作"""
import re


# 跨域操作类型
CROSS_DOMAIN_OPS = {
    'compare': '比较',
    'ratio': '比率',
    'reconcile': '勾稽核对',
    'list': '列举',
}

# 跨域操作检测关键词
_COMPARE_KEYWORDS = ['对比', '比较', '一致', '差异', '差额', 'vs', 'VS']
_RATIO_KEYWORDS = ['比重', '占比', '比率', '百分比']
_RECONCILE_KEYWORDS = ['核对', '勾稽', '一致性', '是否一致', '是否相符']


def detect_cross_domain_operation(query: str) -> str:
    """检测跨域查询的操作类型。"""
    if any(kw in query for kw in _RECONCILE_KEYWORDS):
        return 'reconcile'
    if any(kw in query for kw in _RATIO_KEYWORDS):
        return 'ratio'
    if any(kw in query for kw in _COMPARE_KEYWORDS):
        return 'compare'
    return 'list'


def merge_cross_domain_results(sub_results: list, operation: str,
                                query: str = '') -> dict:
    """合并多个子域查询结果。"""
    if operation == 'compare':
        return _merge_compare(sub_results, query)
    elif operation == 'ratio':
        return _merge_ratio(sub_results, query)
    elif operation == 'reconcile':
        return _merge_reconcile(sub_results, query)
    return _merge_list(sub_results)


def _merge_list(sub_results: list) -> dict:
    merged = []
    for sr in sub_results:
        domain = sr.get('domain', 'unknown')
        for row in sr.get('data', []):
            row_copy = dict(row)
            row_copy['_source_domain'] = domain
            merged.append(row_copy)
    return {
        'operation': 'list',
        'merged_data': merged,
        'summary': f'共{len(sub_results)}个域，合计{len(merged)}行数据',
    }


def _merge_compare(sub_results: list, query: str) -> dict:
    if len(sub_results) < 2:
        return _merge_list(sub_results)
    a_data = sub_results[0].get('data', [])
    b_data = sub_results[1].get('data', [])
    a_domain = sub_results[0].get('domain', 'A')
    b_domain = sub_results[1].get('domain', 'B')

    a_by_period = _index_by_period(a_data)
    b_by_period = _index_by_period(b_data)
    all_periods = sorted(set(a_by_period.keys()) | set(b_by_period.keys()))

    merged = []
    for period in all_periods:
        a_row = a_by_period.get(period, {})
        b_row = b_by_period.get(period, {})
        result_row = {'period': period}
        a_nums = _extract_numeric(a_row)
        b_nums = _extract_numeric(b_row)
        for col, val in a_nums.items():
            result_row[f'{a_domain}_{col}'] = val
        for col, val in b_nums.items():
            result_row[f'{b_domain}_{col}'] = val
        if len(a_nums) == 1 and len(b_nums) == 1:
            a_val = list(a_nums.values())[0]
            b_val = list(b_nums.values())[0]
            if a_val is not None and b_val is not None:
                result_row['差异'] = round(a_val - b_val, 2)
                result_row['差异率(%)'] = round((a_val - b_val) / b_val * 100, 2) if b_val != 0 else None
        merged.append(result_row)

    return {
        'operation': 'compare',
        'merged_data': merged,
        'summary': f'{a_domain} vs {b_domain}，共{len(merged)}个期间',
    }


def _merge_ratio(sub_results: list, query: str) -> dict:
    if len(sub_results) < 2:
        return _merge_list(sub_results)
    a_data = sub_results[0].get('data', [])
    b_data = sub_results[1].get('data', [])
    a_domain = sub_results[0].get('domain', 'A')
    b_domain = sub_results[1].get('domain', 'B')

    a_by_period = _index_by_period(a_data)
    b_by_period = _index_by_period(b_data)
    all_periods = sorted(set(a_by_period.keys()) | set(b_by_period.keys()))

    merged = []
    for period in all_periods:
        a_row = a_by_period.get(period, {})
        b_row = b_by_period.get(period, {})
        a_nums = _extract_numeric(a_row)
        b_nums = _extract_numeric(b_row)
        result_row = {'period': period}
        if a_nums and b_nums:
            a_val = list(a_nums.values())[0]
            b_val = list(b_nums.values())[0]
            result_row[f'{a_domain}'] = a_val
            result_row[f'{b_domain}'] = b_val
            result_row['比率(%)'] = round(a_val / b_val * 100, 2) if b_val else None
        merged.append(result_row)

    return {
        'operation': 'ratio',
        'merged_data': merged,
        'summary': f'{a_domain}/{b_domain} 比率，共{len(merged)}个期间',
    }


def _merge_reconcile(sub_results: list, query: str) -> dict:
    if len(sub_results) < 2:
        return _merge_list(sub_results)

    all_indexed = [(sr.get('domain', '?'), _index_by_period(sr.get('data', [])))
                   for sr in sub_results]
    all_periods = set()
    for _, indexed in all_indexed:
        all_periods |= set(indexed.keys())
    all_periods = sorted(all_periods)

    merged = []
    all_match = True
    for period in all_periods:
        result_row = {'period': period}
        values = []
        for domain, indexed in all_indexed:
            row = indexed.get(period, {})
            nums = _extract_numeric(row)
            if nums:
                val = list(nums.values())[0]
                col = list(nums.keys())[0]
                result_row[f'{domain}_{col}'] = val
                values.append(val)
        if len(values) >= 2:
            is_match = all(abs(v - values[0]) < 0.01 for v in values[1:])
            result_row['一致'] = '是' if is_match else '否'
            if not is_match:
                all_match = False
                result_row['最大差异'] = round(max(values) - min(values), 2)
        merged.append(result_row)

    return {
        'operation': 'reconcile',
        'merged_data': merged,
        'summary': f'勾稽核对{"通过" if all_match else "存在差异"}，共{len(merged)}个期间',
        'all_match': all_match,
    }


def _extract_numeric(row: dict) -> dict:
    """提取行中的数值列（排除期间维度列）。"""
    skip = {'period_year', 'period_month', 'period_quarter', 'revision_no',
            'taxpayer_id', '_source_domain'}
    return {k: v for k, v in row.items()
            if isinstance(v, (int, float)) and k not in skip}


def _index_by_period(data: list) -> dict:
    """将数据按期间索引。"""
    indexed = {}
    for row in data:
        year = row.get('period_year')
        month = row.get('period_month')
        quarter = row.get('period_quarter')
        if year and month:
            key = f'{year}-{month:02d}'
        elif year and quarter:
            key = f'{year}-Q{quarter}'
        elif year:
            key = str(year)
        else:
            key = str(len(indexed))
        indexed[key] = row
    return indexed
