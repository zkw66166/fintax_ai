"""财务指标自动计算脚本：从各域视图取数，计算18项财税指标，写入financial_metrics表"""
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


# ============================================================
# 指标定义注册表
# ============================================================
METRIC_DEFS = [
    # --- 盈利能力 ---
    {
        'code': 'gross_margin',
        'name': '毛利率',
        'category': '盈利能力',
        'unit': '%',
        'eval_rules': [(30, '优'), (15, '良'), (5, '中'), (None, '差')],
    },
    {
        'code': 'net_margin',
        'name': '净利率',
        'category': '盈利能力',
        'unit': '%',
        'eval_rules': [(15, '优'), (8, '良'), (3, '中'), (None, '差')],
    },
    {
        'code': 'roe',
        'name': '净资产收益率(ROE)',
        'category': '盈利能力',
        'unit': '%',
        'eval_rules': [(15, '优'), (8, '良'), (3, '中'), (None, '差')],
    },
    # --- 偿债能力 ---
    {
        'code': 'debt_ratio',
        'name': '资产负债率',
        'category': '偿债能力',
        'unit': '%',
        'eval_rules': [(40, '优'), (60, '良'), (70, '中'), (None, '差')],
        'eval_ascending': True,  # 越低越好
    },
    {
        'code': 'current_ratio',
        'name': '流动比率',
        'category': '偿债能力',
        'unit': '',
        'eval_rules': [(2.0, '优'), (1.5, '良'), (1.0, '中'), (None, '差')],
    },
    {
        'code': 'quick_ratio',
        'name': '速动比率',
        'category': '偿债能力',
        'unit': '',
        'eval_rules': [(1.5, '优'), (1.0, '良'), (0.5, '中'), (None, '差')],
    },
    # --- 营运能力 ---
    {
        'code': 'ar_turnover',
        'name': '应收账款周转率',
        'category': '营运能力',
        'unit': '次',
        'eval_rules': [(12, '优'), (6, '良'), (3, '中'), (None, '差')],
    },
    {
        'code': 'inventory_turnover',
        'name': '存货周转率',
        'category': '营运能力',
        'unit': '次',
        'eval_rules': [(8, '优'), (4, '良'), (2, '中'), (None, '差')],
    },
    # --- 成长能力 ---
    {
        'code': 'revenue_growth',
        'name': '营业收入增长率',
        'category': '成长能力',
        'unit': '%',
        'eval_rules': [(20, '优'), (10, '良'), (0, '中'), (None, '差')],
    },
    # --- 现金流 ---
    {
        'code': 'cash_to_revenue',
        'name': '销售收现比',
        'category': '现金流',
        'unit': '',
        'eval_rules': [(1.0, '优'), (0.8, '良'), (0.5, '中'), (None, '差')],
    },
    # --- 税负率类 ---
    {
        'code': 'vat_burden',
        'name': '增值税税负率',
        'category': '税负率类',
        'unit': '%',
        'eval_rules': None,  # 行业差异大，不做通用评价
    },
    {
        'code': 'eit_burden',
        'name': '企业所得税税负率',
        'category': '税负率类',
        'unit': '%',
        'eval_rules': None,
    },
    {
        'code': 'total_tax_burden',
        'name': '综合税负率',
        'category': '税负率类',
        'unit': '%',
        'eval_rules': None,
    },
    # --- 增值税重点指标 ---
    {
        'code': 'output_input_ratio',
        'name': '销项进项配比率',
        'category': '增值税重点指标',
        'unit': '',
        'eval_rules': None,
    },
    {
        'code': 'transfer_out_ratio',
        'name': '进项税额转出占比',
        'category': '增值税重点指标',
        'unit': '%',
        'eval_rules': None,
    },
    # --- 所得税重点指标 ---
    {
        'code': 'taxable_income_ratio',
        'name': '应税所得率',
        'category': '所得税重点指标',
        'unit': '%',
        'eval_rules': None,
    },
    # --- 风险预警类 ---
    {
        'code': 'zero_filing_ratio',
        'name': '零申报率',
        'category': '风险预警类',
        'unit': '%',
        'eval_rules': None,
    },
]

def _evaluate(value, metric_def):
    """根据评价规则返回等级"""
    rules = metric_def.get('eval_rules')
    if not rules or value is None:
        return None
    ascending = metric_def.get('eval_ascending', False)
    if ascending:
        # 越低越好（如资产负债率）
        for threshold, level in rules:
            if threshold is None:
                return level
            if value <= threshold:
                return level
    else:
        # 越高越好（默认）
        for threshold, level in rules:
            if threshold is None:
                return level
            if value >= threshold:
                return level
    return None


def _safe_div(a, b):
    """安全除法"""
    if b is None or b == 0:
        return None
    if a is None:
        return None
    return a / b


def _get_profit_view(conn, taxpayer_id):
    """根据纳税人会计准则返回利润表视图名"""
    r = conn.execute(
        "SELECT accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()
    if r and r[0] == '小企业会计准则':
        return 'vw_profit_sas'
    return 'vw_profit_eas'


def _get_bs_view(conn, taxpayer_id):
    """根据纳税人会计准则返回资产负债表视图名"""
    r = conn.execute(
        "SELECT accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()
    if r and r[0] == '小企业会计准则':
        return 'vw_balance_sheet_sas'
    return 'vw_balance_sheet_eas'


def _get_cf_view(conn, taxpayer_id):
    """根据纳税人会计准则返回现金流量表视图名"""
    r = conn.execute(
        "SELECT accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()
    if r and r[0] == '小企业会计准则':
        return 'vw_cash_flow_sas'
    return 'vw_cash_flow_eas'


def _get_vat_view(conn, taxpayer_id):
    """根据纳税人类型返回VAT视图名"""
    r = conn.execute(
        "SELECT taxpayer_type FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()
    if r and r[0] == '小规模纳税人':
        return 'vw_vat_return_small'
    return 'vw_vat_return_general'


def compute_all_metrics(conn, taxpayer_id, year, month):
    """计算指定纳税人、指定期间的全部指标，返回结果列表"""
    results = []
    profit_view = _get_profit_view(conn, taxpayer_id)
    bs_view = _get_bs_view(conn, taxpayer_id)
    cf_view = _get_cf_view(conn, taxpayer_id)
    vat_view = _get_vat_view(conn, taxpayer_id)
    is_small = vat_view == 'vw_vat_return_small'

    # --- 取利润表数据（本年累计）---
    profit = conn.execute(
        f"SELECT operating_revenue, operating_cost, net_profit, total_profit, "
        f"income_tax_expense FROM {profit_view} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        f"AND time_range = '本年累计' LIMIT 1",
        (taxpayer_id, year, month)
    ).fetchone()
    revenue = profit['operating_revenue'] if profit else None
    cost = profit['operating_cost'] if profit else None
    net_profit = profit['net_profit'] if profit else None

    # --- 取资产负债表数据 ---
    bs = conn.execute(
        f"SELECT assets_end, assets_begin, liabilities_end, liabilities_begin, "
        f"equity_end, equity_begin, current_assets_end, current_liabilities_end, "
        f"inventory_end, inventory_begin, accounts_receivable_end, "
        f"accounts_receivable_begin FROM {bs_view} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? LIMIT 1",
        (taxpayer_id, year, month)
    ).fetchone()

    # --- 取现金流量表数据（本年累计）---
    cf_col = 'operating_inflow_sales' if not is_small else 'operating_receipts_sales'
    cf = conn.execute(
        f"SELECT {cf_col} AS sales_cash, operating_net_cash FROM {cf_view} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        f"AND time_range = '本年累计' LIMIT 1",
        (taxpayer_id, year, month)
    ).fetchone()

    # --- 取VAT数据（累计）---
    vat = None
    if not is_small:
        vat = conn.execute(
            f"SELECT output_tax, input_tax, transfer_out, total_tax_payable, "
            f"sales_taxable_rate FROM {vat_view} "
            f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
            f"AND time_range = '累计' AND item_type = '一般项目' LIMIT 1",
            (taxpayer_id, year, month)
        ).fetchone()
    else:
        vat = conn.execute(
            f"SELECT tax_due_total, sales_3percent, sales_5percent FROM {vat_view} "
            f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
            f"AND time_range = '累计' LIMIT 1",
            (taxpayer_id, year, month)
        ).fetchone()

    # --- 取EIT数据（年度）---
    eit = conn.execute(
        "SELECT revenue, taxable_income, actual_tax_payable FROM vw_eit_annual_main "
        "WHERE taxpayer_id = ? AND period_year = ? LIMIT 1",
        (taxpayer_id, year)
    ).fetchone()

    # --- 取上期利润表数据（用于增长率计算）---
    prev_year, prev_month = (year - 1, month) if month == 12 else (year, month)
    # 同比：去年同期本年累计
    prev_profit = conn.execute(
        f"SELECT operating_revenue FROM {profit_view} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        f"AND time_range = '本年累计' LIMIT 1",
        (taxpayer_id, year - 1, month)
    ).fetchone()

    # ============================================================
    # 逐项计算
    # ============================================================

    # 1. 毛利率
    v = _safe_div((revenue - cost) if revenue and cost else None,
                  revenue) if revenue else None
    results.append(('gross_margin', round(v * 100, 2) if v is not None else None))

    # 2. 净利率
    v = _safe_div(net_profit, revenue)
    results.append(('net_margin', round(v * 100, 2) if v is not None else None))

    # 3. ROE
    avg_equity = None
    if bs and bs['equity_begin'] is not None and bs['equity_end'] is not None:
        avg_equity = (bs['equity_begin'] + bs['equity_end']) / 2.0
    v = _safe_div(net_profit, avg_equity)
    results.append(('roe', round(v * 100, 2) if v is not None else None))

    # 4. 资产负债率
    v = _safe_div(bs['liabilities_end'] if bs else None,
                  bs['assets_end'] if bs else None)
    results.append(('debt_ratio', round(v * 100, 2) if v is not None else None))

    # 5. 流动比率
    v = _safe_div(bs['current_assets_end'] if bs else None,
                  bs['current_liabilities_end'] if bs else None)
    results.append(('current_ratio', round(v, 2) if v is not None else None))

    # 6. 速动比率
    if bs and bs['current_assets_end'] is not None and bs['inventory_end'] is not None:
        quick_assets = bs['current_assets_end'] - (bs['inventory_end'] or 0)
    else:
        quick_assets = None
    v = _safe_div(quick_assets, bs['current_liabilities_end'] if bs else None)
    results.append(('quick_ratio', round(v, 2) if v is not None else None))

    # 7. 应收账款周转率
    avg_ar = None
    if bs and bs['accounts_receivable_begin'] is not None and bs['accounts_receivable_end'] is not None:
        avg_ar = (bs['accounts_receivable_begin'] + bs['accounts_receivable_end']) / 2.0
    v = _safe_div(revenue, avg_ar)
    results.append(('ar_turnover', round(v, 2) if v is not None else None))

    # 8. 存货周转率
    avg_inv = None
    if bs and bs['inventory_begin'] is not None and bs['inventory_end'] is not None:
        avg_inv = (bs['inventory_begin'] + bs['inventory_end']) / 2.0
    v = _safe_div(cost, avg_inv)
    results.append(('inventory_turnover', round(v, 2) if v is not None else None))

    # 9. 营业收入增长率
    prev_rev = prev_profit['operating_revenue'] if prev_profit else None
    v = _safe_div((revenue - prev_rev) if revenue and prev_rev else None, prev_rev)
    results.append(('revenue_growth', round(v * 100, 2) if v is not None else None))

    # 10. 销售收现比
    sales_cash = cf['sales_cash'] if cf else None
    v = _safe_div(sales_cash, revenue)
    results.append(('cash_to_revenue', round(v, 2) if v is not None else None))

    # 11. 增值税税负率
    if not is_small and vat:
        vat_payable = vat['total_tax_payable'] or 0
        taxable_sales = vat['sales_taxable_rate'] or 0
        v = _safe_div(vat_payable, taxable_sales)
        results.append(('vat_burden', round(v * 100, 2) if v is not None else None))
    else:
        # 小规模纳税人：税额/销售额
        if is_small and vat:
            tax_total = vat['tax_due_total'] or 0
            sales_total = (vat['sales_3percent'] or 0) + (vat['sales_5percent'] or 0)
            v = _safe_div(tax_total, sales_total) if sales_total else None
            results.append(('vat_burden', round(v * 100, 2) if v is not None else None))
        else:
            results.append(('vat_burden', None))

    # 12. 企业所得税税负率
    eit_tax = eit['actual_tax_payable'] if eit else None
    v = _safe_div(eit_tax, revenue)
    results.append(('eit_burden', round(v * 100, 2) if v is not None else None))

    # 13. 综合税负率
    vat_tax = 0
    if not is_small and vat:
        vat_tax = vat['total_tax_payable'] or 0
    elif is_small and vat:
        vat_tax = vat['tax_due_total'] or 0
    eit_tax_val = eit_tax or 0
    total_tax = vat_tax + eit_tax_val
    v = _safe_div(total_tax, revenue) if total_tax > 0 else None
    results.append(('total_tax_burden', round(v * 100, 2) if v is not None else None))

    # 14. 销项进项配比率（仅一般纳税人）
    if not is_small and vat:
        v = _safe_div(vat['output_tax'], vat['input_tax'])
        results.append(('output_input_ratio', round(v, 2) if v is not None else None))
    else:
        results.append(('output_input_ratio', None))

    # 15. 进项税额转出占比（仅一般纳税人）
    if not is_small and vat:
        v = _safe_div(vat['transfer_out'], vat['input_tax'])
        results.append(('transfer_out_ratio', round(v * 100, 2) if v is not None else None))
    else:
        results.append(('transfer_out_ratio', None))

    # 16. 应税所得率
    eit_taxable = eit['taxable_income'] if eit else None
    eit_rev = eit['revenue'] if eit else None
    v = _safe_div(eit_taxable, eit_rev)
    results.append(('taxable_income_ratio', round(v * 100, 2) if v is not None else None))

    # 17. 零申报率（统计本年截至当月的零申报月份数）
    if not is_small:
        zero_months = conn.execute(
            "SELECT COUNT(*) FROM vw_vat_return_general "
            "WHERE taxpayer_id = ? AND period_year = ? AND period_month <= ? "
            "AND time_range = '本月' AND item_type = '一般项目' "
            "AND (total_tax_payable IS NULL OR total_tax_payable = 0)",
            (taxpayer_id, year, month)
        ).fetchone()[0]
    else:
        zero_months = conn.execute(
            "SELECT COUNT(*) FROM vw_vat_return_small "
            "WHERE taxpayer_id = ? AND period_year = ? AND period_month <= ? "
            "AND time_range = '本期' "
            "AND (tax_due_total IS NULL OR tax_due_total = 0)",
            (taxpayer_id, year, month)
        ).fetchone()[0]
    v = _safe_div(zero_months, month)
    results.append(('zero_filing_ratio', round(v * 100, 2) if v is not None else None))

    return results


def _metric_def_by_code(code):
    """根据code查找指标定义"""
    for d in METRIC_DEFS:
        if d['code'] == code:
            return d
    return None


def calculate_and_save(db_path=None, taxpayer_id=None, year=None, month=None):
    """计算并保存财务指标到数据库。

    Args:
        db_path: 数据库路径，默认使用配置
        taxpayer_id: 指定纳税人，None则计算全部
        year: 指定年份，None则计算全部已有数据的年份
        month: 指定月份，None则计算全部已有数据的月份
    """
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 确定要计算的纳税人列表
    if taxpayer_id:
        taxpayers = [(taxpayer_id,)]
    else:
        taxpayers = conn.execute(
            "SELECT taxpayer_id FROM taxpayer_info WHERE status = 'active'"
        ).fetchall()

    total_inserted = 0

    for (tid,) in taxpayers:
        # 确定要计算的期间列表
        if year and month:
            periods = [(year, month)]
        else:
            # 从利润表取已有期间（利润表是最基础的数据源）
            profit_view = _get_profit_view(conn, tid)
            periods = conn.execute(
                f"SELECT DISTINCT period_year, period_month FROM {profit_view} "
                f"WHERE taxpayer_id = ? ORDER BY period_year, period_month",
                (tid,)
            ).fetchall()

        for (py, pm) in periods:
            print(f"  计算 {tid} {py}年{pm}月...")
            metric_results = compute_all_metrics(conn, tid, py, pm)

            # 写入数据库（REPLACE模式，支持重算）
            for code, value in metric_results:
                mdef = _metric_def_by_code(code)
                if not mdef:
                    continue
                eval_level = _evaluate(value, mdef)
                conn.execute(
                    """INSERT OR REPLACE INTO financial_metrics
                    (taxpayer_id, period_year, period_month, metric_category,
                     metric_code, metric_name, metric_value, metric_unit,
                     evaluation_level, calculated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (tid, py, pm, mdef['category'], code, mdef['name'],
                     value, mdef['unit'], eval_level, datetime.now().isoformat())
                )
                total_inserted += 1

    conn.commit()
    conn.close()
    print(f"\n[calculate_metrics] 完成，共写入 {total_inserted} 条指标记录")
    return total_inserted


def seed_metric_synonyms(db_path=None):
    """写入财务指标同义词数据"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)

    synonyms = [
        # metric_name → metric_code 映射
        ('毛利率', 'metric_name', 1), ('销售毛利率', 'metric_name', 2),
        ('净利率', 'metric_name', 1), ('销售净利率', 'metric_name', 2),
        ('净资产收益率', 'metric_name', 1), ('ROE', 'metric_name', 1),
        ('资产负债率', 'metric_name', 1), ('负债率', 'metric_name', 2),
        ('流动比率', 'metric_name', 1), ('速动比率', 'metric_name', 1),
        ('应收账款周转率', 'metric_name', 1), ('存货周转率', 'metric_name', 1),
        ('营业收入增长率', 'metric_name', 1), ('收入增长率', 'metric_name', 2),
        ('销售收现比', 'metric_name', 1),
        ('增值税税负率', 'metric_name', 1), ('增值税税负', 'metric_name', 2),
        ('企业所得税税负率', 'metric_name', 1), ('所得税税负率', 'metric_name', 2),
        ('综合税负率', 'metric_name', 1), ('综合税负', 'metric_name', 2),
        ('销项进项配比率', 'metric_name', 1), ('进项税额转出占比', 'metric_name', 1),
        ('应税所得率', 'metric_name', 1), ('零申报率', 'metric_name', 1),
        # 新增指标同义词
        ('净利润增长率', 'metric_name', 1), ('利润增长率', 'metric_name', 2),
        ('管理费用率', 'metric_name', 1), ('管理费用占比', 'metric_name', 2),
        ('销售费用率', 'metric_name', 1), ('销售费用占比', 'metric_name', 2),
        ('应收款周转天数', 'metric_name', 1), ('应收账款周转天数', 'metric_name', 2),
        ('回款天数', 'metric_name', 2),
        ('总资产周转率', 'metric_name', 1), ('资产周转率', 'metric_name', 2),
        ('资产增长率', 'metric_name', 1), ('总资产增长率', 'metric_name', 2),
        ('发票开具异常率', 'metric_name', 1), ('发票异常率', 'metric_name', 2),
        ('顶额开具率', 'metric_name', 2),
        ('现金债务保障比率', 'metric_name', 1), ('现金比率', 'metric_name', 2),
        # 类别同义词
        ('盈利能力', 'metric_category', 1), ('盈利指标', 'metric_category', 2),
        ('偿债能力', 'metric_category', 1), ('偿债指标', 'metric_category', 2),
        ('营运能力', 'metric_category', 1), ('营运指标', 'metric_category', 2),
        ('成长能力', 'metric_category', 1), ('成长指标', 'metric_category', 2),
        ('现金流', 'metric_category', 1), ('现金流指标', 'metric_category', 2),
        ('税负率', 'metric_category', 1), ('税负指标', 'metric_category', 2),
        ('风险预警', 'metric_category', 1), ('风险指标', 'metric_category', 2),
        ('费用控制', 'metric_category', 1), ('费用指标', 'metric_category', 2),
        # period_type 同义词
        ('月度', 'period_type', 1), ('按月', 'period_type', 2),
        ('季度', 'period_type', 1), ('按季', 'period_type', 2),
        ('年度', 'period_type', 1), ('按年', 'period_type', 2),
    ]

    for phrase, col, pri in synonyms:
        conn.execute(
            "INSERT OR IGNORE INTO financial_metrics_synonyms (phrase, column_name, priority) "
            "VALUES (?, ?, ?)",
            (phrase, col, pri)
        )
    conn.commit()
    conn.close()
    print(f"[seed_metric_synonyms] 写入 {len(synonyms)} 条同义词")


if __name__ == '__main__':
    print("=" * 60)
    print("财务指标自动计算")
    print("=" * 60)
    seed_metric_synonyms()
    calculate_and_save()
