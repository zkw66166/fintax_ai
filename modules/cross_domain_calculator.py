"""跨域计算引擎：支持差异比较、比率计算、勾稽核对等跨域操作"""
import re
import logging

# PHASE 4 FIX: 添加日志记录器
logger = logging.getLogger(__name__)


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
    """合并多个子域查询结果（比较操作）。

    特殊处理：
    - financial_metrics 域：保留 metric_name 维度，按指标名称分组
    - 其他域：按期间分组（原有逻辑）
    """
    if len(sub_results) < 2:
        return _merge_list(sub_results)

    # 检测是否所有子域都是 financial_metrics
    all_fm = all(sr.get('domain') == 'financial_metrics' for sr in sub_results)

    if all_fm:
        # 新增：financial_metrics 专用合并逻辑
        return _merge_compare_financial_metrics(sub_results, query)

    # 原有逻辑：按期间合并
    return _merge_compare_by_period(sub_results, query)


def _merge_compare_financial_metrics(sub_results: list, query: str) -> dict:
    """financial_metrics 域专用比较合并：按 metric_name 分组。

    输入示例：
    sub_results[0] = {
        'domain': 'financial_metrics',
        'data': [
            {'metric_name': '净利率', 'period_year': 2024, 'period_month': 3, 'metric_value': 25.5},
            {'metric_name': '增值税税负率', 'period_year': 2024, 'period_month': 3, 'metric_value': 3.7},
        ]
    }

    输出示例：
    {
        'operation': 'compare',
        'merged_data': [
            {'metric_name': '净利率', '2024年3月': 25.5, '2025年3月': 25.5, '变动': 0.0},
            {'metric_name': '增值税税负率', '2024年3月': 3.7, '2025年3月': 3.7, '变动': 0.0},
        ],
        'summary': '财务指标比较，共2个指标'
    }
    """
    # 1. 收集所有期间
    all_periods = set()
    for sr in sub_results:
        for row in sr.get('data', []):
            year = row.get('period_year')
            month = row.get('period_month')
            if year and month:
                all_periods.add((year, month))

    # 2. 按 metric_name 分组
    metric_groups = {}
    for sr in sub_results:
        for row in sr.get('data', []):
            metric_name = row.get('metric_name')
            if not metric_name:
                continue
            if metric_name not in metric_groups:
                metric_groups[metric_name] = {}

            year = row.get('period_year')
            month = row.get('period_month')
            if year and month:
                period_key = (year, month)
                metric_groups[metric_name][period_key] = row.get('metric_value')

    # 3. 构建输出行
    merged = []
    sorted_periods = sorted(all_periods)

    for metric_name, period_values in metric_groups.items():
        result_row = {'metric_name': metric_name}

        # 添加各期间列
        for year, month in sorted_periods:
            period_label = f'{year}年{month}月'
            result_row[period_label] = period_values.get((year, month))

        # 计算变动（如果有2个期间）
        if len(sorted_periods) == 2:
            val1 = period_values.get(sorted_periods[0])
            val2 = period_values.get(sorted_periods[1])
            if val1 is not None and val2 is not None:
                result_row['变动'] = round(val2 - val1, 2)
                if val1 != 0:
                    result_row['变动率(%)'] = round((val2 - val1) / val1 * 100, 2)

        merged.append(result_row)

    return {
        'operation': 'compare',
        'merged_data': merged,
        'summary': f'财务指标比较，共{len(merged)}个指标',
    }


def _extract_requested_periods(query: str, entities: dict) -> set:
    """从查询和实体中提取用户明确请求的期间。

    Returns:
        set of (year, month) tuples, or empty set if cannot determine
    """
    requested = set()

    # 从 entities 提取
    year = entities.get('period_year')
    month = entities.get('period_month')
    end_year = entities.get('period_end_year')
    end_month = entities.get('period_end_month')

    if year and month:
        requested.add((year, month))
    if end_year and end_month:
        requested.add((end_year, end_month))

    # 从查询文本提取（正则匹配 "YYYY年M月"）
    pattern = r'(\d{4})年(\d{1,2})月'
    for match in re.finditer(pattern, query):
        y = int(match.group(1))
        m = int(match.group(2))
        requested.add((y, m))

    return requested


def _merge_compare_by_period(sub_results: list, query: str) -> dict:
    """按期间合并多个子域查询结果（支持2个及以上子域）。

    支持N个子域：每个子域的数值列以 domain_col 方式命名合并到一行。
    新增：期间过滤（仅保留用户请求的期间）
    新增：期间键标准化（季度键→月份键，确保跨域合并时期间匹配）
    """
    if len(sub_results) < 2:
        return _merge_list(sub_results)

    # 季度→月份映射（季末月份）
    _QUARTER_TO_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}

    # 构建所有子域的索引，并标准化期间键
    domain_indexed = []
    for sr in sub_results:
        domain = sr.get('domain', f'domain{len(domain_indexed)}')
        indexed = _index_by_period(sr.get('data', []))

        # 标准化期间键：将 "YYYY-QN" 转换为 "YYYY-MM"（季末月份）
        normalized_indexed = {}
        for period_key, row in indexed.items():
            # 检测季度格式 "YYYY-Q1"
            quarter_match = re.match(r'(\d{4})-Q(\d)', period_key)
            if quarter_match:
                year = int(quarter_match.group(1))
                quarter = int(quarter_match.group(2))
                month = _QUARTER_TO_MONTH.get(quarter, 3)  # 默认Q1→3月
                normalized_key = f'{year}-{month:02d}'
                normalized_indexed[normalized_key] = row
            else:
                # 保持原键（已经是 "YYYY-MM" 或其他格式）
                normalized_indexed[period_key] = row

        domain_indexed.append((domain, normalized_indexed))

    # 合并所有期间（UNION）
    all_periods_set = set()
    for _, indexed in domain_indexed:
        all_periods_set.update(indexed.keys())
    all_periods = sorted(all_periods_set)

    # 期间过滤：仅保留用户请求的期间
    entities = sub_results[0].get('entities', {})
    requested_periods = _extract_requested_periods(query, entities)

    if requested_periods:
        filtered_periods = []
        for period_str in all_periods:
            match = re.match(r'(\d{4})-(\d{2})', period_str)
            if match:
                y = int(match.group(1))
                m = int(match.group(2))
                if (y, m) in requested_periods:
                    filtered_periods.append(period_str)
        if filtered_periods:
            all_periods = filtered_periods

    # 合并所有子域的数据
    merged = []
    for period in all_periods:
        result_row = {'period': period}
        all_nums = {}  # {domain: nums_dict}

        # PHASE 4 FIX: 记录哪些域有数据，哪些域缺失数据
        domains_with_data = []
        domains_without_data = []

        for domain, indexed in domain_indexed:
            row = indexed.get(period, {})
            nums = _extract_numeric(row)

            # PHASE 4 FIX: 即使域返回0行，也创建占位列（值为NULL）
            if nums:
                for col, val in nums.items():
                    result_row[f'{domain}_{col}'] = val
                domains_with_data.append(domain)
            else:
                # 域缺失数据：从第一个有数据的期间推断列名，创建NULL占位
                # 如果该域在其他期间有数据，使用那些列名；否则使用通用占位
                domain_cols = set()
                for other_period in all_periods:
                    other_row = indexed.get(other_period, {})
                    other_nums = _extract_numeric(other_row)
                    domain_cols.update(other_nums.keys())

                if domain_cols:
                    # 使用该域在其他期间的列名
                    for col in domain_cols:
                        result_row[f'{domain}_{col}'] = None
                else:
                    # 该域在所有期间都无数据，创建通用占位列
                    result_row[f'{domain}_value'] = None
                domains_without_data.append(domain)

            all_nums[domain] = nums

        # PHASE 4 FIX: 记录日志，帮助诊断缺失列问题
        if domains_without_data:
            logger.warning(f"Period {period}: domains without data: {domains_without_data}")

        # 兼容原2域差异计算（仅当所有子域各有1个数值列时）
        if len(domain_indexed) == 2:
            a_nums = all_nums.get(domain_indexed[0][0], {})
            b_nums = all_nums.get(domain_indexed[1][0], {})
            if len(a_nums) == 1 and len(b_nums) == 1:
                a_val = list(a_nums.values())[0]
                b_val = list(b_nums.values())[0]
                if a_val is not None and b_val is not None:
                    result_row['差异'] = round(a_val - b_val, 2)
                    result_row['差异率(%)'] = round((a_val - b_val) / b_val * 100, 2) if b_val != 0 else None

        merged.append(result_row)

    domain_names = ' vs '.join(d for d, _ in domain_indexed)
    return {
        'operation': 'compare',
        'merged_data': merged,
        'summary': f'{domain_names}，共{len(merged)}个期间',
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
