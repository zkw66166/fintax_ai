"""SQL审核器：正则硬拦截，10条核心规则（域感知）"""
import re
from modules.schema_catalog import DENIED_KEYWORDS, DENIED_FUNCTIONS, SYSTEM_TABLES


def audit_sql(sql: str, allowed_views: list, max_rows: int = 1000, domain: str = 'vat') -> tuple:
    """
    审核LLM生成的SQL。
    返回 (passed: bool, violations: list[str])
    """
    violations = []
    sql_stripped = sql.strip().rstrip(';')

    # 1. 单语句（无中间分号）
    if ';' in sql_stripped:
        violations.append("多语句: SQL中包含多条语句")

    # 2. 只读（SELECT/WITH开头）
    if not re.match(r'^\s*(SELECT|WITH)\b', sql_stripped, re.I):
        violations.append("非只读: SQL必须以SELECT或WITH开头")

    # 3. 禁用危险关键字
    sql_upper = sql_stripped.upper()
    for kw in DENIED_KEYWORDS:
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, sql_upper):
            violations.append(f"危险关键字: {kw}")

    # 4. 视图白名单
    # 先提取所有CTE名称
    _cte_names = re.findall(r'(?:WITH|,)\s+(\w+)\s+AS\s*\(', sql_stripped, re.I)
    _first_cte = re.findall(r'WITH\s+(\w+)\s+AS\s*\(', sql_stripped, re.I)
    all_ctes = set(c.lower() for c in _cte_names + _first_cte)

    table_refs = re.findall(
        r'(?:FROM|JOIN)\s+(\w+)', sql_stripped, re.I
    )
    for ref in table_refs:
        if ref.lower() in [t.lower() for t in SYSTEM_TABLES]:
            violations.append(f"系统表访问: {ref}")
        elif ref.lower() not in [v.lower() for v in allowed_views]:
            if ref.lower() not in all_ctes:
                violations.append(f"视图不在白名单: {ref}")

    # 5. 禁止 SELECT *（允许 SELECT * FROM <CTE名> 的情况）
    select_star_matches = re.finditer(r'\bSELECT\s+\*\s+FROM\s+(\w+)', sql_stripped, re.I)
    has_bad_select_star = False
    for m in select_star_matches:
        target = m.group(1).lower()
        if target not in all_ctes:
            has_bad_select_star = True
            break
    # Also check bare SELECT * without FROM
    if re.search(r'\bSELECT\s+\*\s*(?:,|\s+(?!FROM))', sql_stripped, re.I):
        has_bad_select_star = True
    if has_bad_select_star:
        violations.append("禁止SELECT *")

    # 6. 必须含 taxpayer_id 过滤
    if not re.search(r'taxpayer_id\s*=\s*[:\?]', sql_stripped, re.I):
        if not re.search(r"taxpayer_id\s*=\s*'", sql_stripped, re.I):
            violations.append("缺少taxpayer_id过滤")

    # 7. 必须含期间过滤（域感知）
    has_period = (
        re.search(r'period_year\s*=', sql_stripped, re.I) or
        re.search(r'period_year\s*BETWEEN', sql_stripped, re.I) or
        re.search(r'period_year\s*>=', sql_stripped, re.I) or
        re.search(r'period_year\s*IN\b', sql_stripped, re.I) or
        re.search(r'period_year\s*<=', sql_stripped, re.I) or
        re.search(r'period_year\s*\*\s*100', sql_stripped, re.I)
    )
    # EIT域：如果查询所有季度数据，period_year可能只出现在SELECT/PARTITION中
    # 此时只要有period_quarter过滤即可视为有期间过滤
    if not has_period and domain == 'eit':
        has_quarter_filter = (
            re.search(r'period_quarter\s*=', sql_stripped, re.I) or
            re.search(r'period_quarter\s*IN\b', sql_stripped, re.I) or
            re.search(r'period_quarter\s*BETWEEN\b', sql_stripped, re.I) or
            re.search(r'period_quarter\s*>=', sql_stripped, re.I) or
            re.search(r'period_quarter\s*<=', sql_stripped, re.I) or
            re.search(r'period_quarter\s*IS\s+NOT\s+NULL', sql_stripped, re.I) or
            re.search(r'ORDER\s+BY\s+.*period_quarter', sql_stripped, re.I)
        )
        if has_quarter_filter:
            has_period = True
    if not has_period:
        violations.append("缺少期间过滤(period_year)")

    # EIT季度需要period_quarter过滤（仅当视图包含季度视图时）
    if domain == 'eit':
        has_quarter_view = any('quarter' in v.lower() for v in allowed_views)
        if has_quarter_view:
            has_quarter = (
                re.search(r'period_quarter\s*=', sql_stripped, re.I) or
                re.search(r'period_quarter\s*IN\b', sql_stripped, re.I) or
                re.search(r'period_quarter\s*BETWEEN\b', sql_stripped, re.I) or
                re.search(r'period_quarter\s*>=', sql_stripped, re.I) or
                re.search(r'period_quarter\s*<=', sql_stripped, re.I) or
                re.search(r'period_quarter\s*IS\s+NOT\s+NULL', sql_stripped, re.I) or
                re.search(r'ORDER\s+BY\s+.*period_quarter', sql_stripped, re.I)
            )
            if not has_quarter:
                violations.append("缺少季度过滤(period_quarter)")

    # 科目余额需要period_month过滤（月度数据）
    _month_domains = ['account_balance', 'balance_sheet', 'profit', 'cash_flow',
                      'financial_metrics', 'invoice']
    if domain in _month_domains:
        has_month = (
            re.search(r'period_month\s*=', sql_stripped, re.I) or
            re.search(r'period_month\s*BETWEEN', sql_stripped, re.I) or
            re.search(r'period_month\s*>=', sql_stripped, re.I) or
            re.search(r'period_month\s*<=', sql_stripped, re.I) or
            re.search(r'period_month\s*IN\b', sql_stripped, re.I) or
            re.search(r'period_year\s*\*\s*100\s*\+\s*period_month', sql_stripped, re.I) or
            re.search(r'\w+\.period_year\s*\*\s*100\s*\+\s*\w+\.period_month', sql_stripped, re.I)
        )
        if not has_month:
            violations.append("缺少月份过滤(period_month)")

    # 8. 必须有 LIMIT
    if not re.search(r'\bLIMIT\b', sql_stripped, re.I):
        violations.append("缺少LIMIT")
    else:
        m = re.search(r'\bLIMIT\s+(\d+)', sql_stripped, re.I)
        if m and int(m.group(1)) > max_rows:
            violations.append(f"LIMIT超限: {m.group(1)} > {max_rows}")

    # 9. 禁用危险函数
    sql_lower = sql_stripped.lower()
    for func in DENIED_FUNCTIONS:
        if func.lower() in sql_lower:
            violations.append(f"危险函数: {func}")

    return (len(violations) == 0, violations)
