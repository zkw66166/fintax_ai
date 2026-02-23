"""财务指标自动计算脚本 v2：25项指标，支持月度/季度/年度三种粒度，写入 financial_metrics_item 表"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


# ============================================================
# 工具函数
# ============================================================

def _safe_div(a, b):
    if b is None or b == 0 or a is None:
        return None
    return a / b


def _get_accounting_info(conn, taxpayer_id):
    """返回 (accounting_standard, taxpayer_type)"""
    r = conn.execute(
        "SELECT accounting_standard, taxpayer_type FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,)
    ).fetchone()
    if not r:
        return None, None
    return r['accounting_standard'], r['taxpayer_type']


def _profit_view(std):
    return 'vw_profit_sas' if std == '小企业会计准则' else 'vw_profit_eas'


def _bs_view(std):
    return 'vw_balance_sheet_sas' if std == '小企业会计准则' else 'vw_balance_sheet_eas'


def _cf_view(std):
    return 'vw_cash_flow_sas' if std == '小企业会计准则' else 'vw_cash_flow_eas'


def _vat_view(tp):
    return 'vw_vat_return_small' if tp == '小规模纳税人' else 'vw_vat_return_general'


def _is_small(tp):
    return tp == '小规模纳税人'


# ============================================================
# 评价规则
# ============================================================

def _load_eval_rules(conn):
    """从 financial_metrics_item_dict 加载评价规则"""
    rows = conn.execute(
        "SELECT metric_code, eval_rules, eval_ascending FROM financial_metrics_item_dict WHERE is_active = 1"
    ).fetchall()
    rules = {}
    for r in rows:
        parsed = json.loads(r['eval_rules']) if r['eval_rules'] else None
        rules[r['metric_code']] = {
            'eval_rules': parsed,
            'eval_ascending': bool(r['eval_ascending']),
        }
    return rules


def _evaluate(value, rules_entry):
    if not rules_entry or value is None:
        return None
    rules = rules_entry.get('eval_rules')
    if not rules:
        return None
    ascending = rules_entry.get('eval_ascending', False)
    if ascending:
        for threshold, level in rules:
            if threshold is None:
                return level
            if value <= threshold:
                return level
    else:
        for threshold, level in rules:
            if threshold is None:
                return level
            if value >= threshold:
                return level
    return None


# ============================================================
# 数据获取辅助
# ============================================================

def _fetch_profit(conn, tid, pv, year, month, time_range):
    """获取利润表数据"""
    return conn.execute(
        f"SELECT operating_revenue, operating_cost, net_profit, "
        f"selling_expense, administrative_expense "
        f"FROM {pv} WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        f"AND time_range = ? LIMIT 1",
        (tid, year, month, time_range)
    ).fetchone()


def _fetch_bs(conn, tid, bv, year, month):
    """获取资产负债表数据"""
    return conn.execute(
        f"SELECT assets_end, assets_begin, liabilities_end, liabilities_begin, "
        f"equity_end, equity_begin, current_assets_end, current_liabilities_end, "
        f"inventory_end, inventory_begin, accounts_receivable_end, "
        f"accounts_receivable_begin FROM {bv} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? LIMIT 1",
        (tid, year, month)
    ).fetchone()


def _fetch_cf(conn, tid, cv, year, month, time_range, small):
    """获取现金流量表数据"""
    col = 'operating_receipts_sales' if small else 'operating_inflow_sales'
    return conn.execute(
        f"SELECT {col} AS sales_cash, operating_net_cash FROM {cv} "
        f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        f"AND time_range = ? LIMIT 1",
        (tid, year, month, time_range)
    ).fetchone()


def _fetch_vat_general(conn, tid, year, month, time_range):
    return conn.execute(
        "SELECT output_tax, input_tax, transfer_out, total_tax_payable, "
        "sales_taxable_rate, city_maintenance_tax, education_surcharge, "
        "local_education_surcharge FROM vw_vat_return_general "
        "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        "AND time_range = ? AND item_type = '一般项目' LIMIT 1",
        (tid, year, month, time_range)
    ).fetchone()


def _fetch_vat_small(conn, tid, year, month, time_range):
    return conn.execute(
        "SELECT tax_due_total, sales_3percent, sales_5percent, "
        "city_maintenance_tax, education_surcharge, local_education_surcharge "
        "FROM vw_vat_return_small "
        "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
        "AND time_range = ? LIMIT 1",
        (tid, year, month, time_range)
    ).fetchone()


# PLACEHOLDER_METRICS


# ============================================================
# 发票异常率计算
# ============================================================

_INVOICE_TIERS = [10000, 100000, 1000000, 10000000]


def _calc_invoice_anomaly(conn, tid, year, month_start, month_end):
    """计算发票开具异常率（顶额开具率）"""
    invoices = conn.execute(
        "SELECT invoice_pk, SUM(amount) AS total_amount "
        "FROM inv_spec_sales "
        "WHERE taxpayer_id = ? AND period_year = ? "
        "AND period_month >= ? AND period_month <= ? "
        "GROUP BY invoice_pk",
        (tid, year, month_start, month_end)
    ).fetchall()
    if not invoices:
        return None
    total = len(invoices)
    anomaly = 0
    for inv in invoices:
        amt = inv['total_amount']
        if amt is None or amt <= 0:
            continue
        for tier in _INVOICE_TIERS:
            if tier * 0.9 <= amt < tier:
                anomaly += 1
                break
    return round(anomaly / total * 100, 2) if total > 0 else None


# ============================================================
# 零申报率计算
# ============================================================

def _calc_zero_filing(conn, tid, year, month_start, month_end, small):
    """统计零申报月份数 / 总月份数"""
    total_months = month_end - month_start + 1
    if total_months <= 0:
        return None
    if not small:
        zero_months = conn.execute(
            "SELECT COUNT(DISTINCT period_month) FROM vw_vat_return_general "
            "WHERE taxpayer_id = ? AND period_year = ? "
            "AND period_month >= ? AND period_month <= ? "
            "AND time_range = '本月' AND item_type = '一般项目' "
            "AND (total_tax_payable IS NULL OR total_tax_payable = 0)",
            (tid, year, month_start, month_end)
        ).fetchone()[0]
    else:
        zero_months = conn.execute(
            "SELECT COUNT(DISTINCT period_month) FROM vw_vat_return_small "
            "WHERE taxpayer_id = ? AND period_year = ? "
            "AND period_month >= ? AND period_month <= ? "
            "AND time_range = '本期' "
            "AND (tax_due_total IS NULL OR tax_due_total = 0)",
            (tid, year, month_start, month_end)
        ).fetchone()[0]
    return round(zero_months / total_months * 100, 2)


# PLACEHOLDER_COMPUTE


# ============================================================
# 通用指标计算（利润/BS/CF 相关的 17 个指标）
# ============================================================

def _compute_common_metrics(
    profit, prev_profit, bs, prev_bs, cf,
    revenue, cost, net_profit, small
):
    """计算利润/BS/CF 相关的通用指标，返回 {code: value}"""
    results = {}

    # 1. 毛利率
    if revenue and cost is not None:
        results['gross_margin'] = round(_safe_div(revenue - cost, revenue) * 100, 2) if revenue else None
    else:
        results['gross_margin'] = None

    # 2. 净利率
    v = _safe_div(net_profit, revenue)
    results['net_margin'] = round(v * 100, 2) if v is not None else None

    # 3. ROE
    avg_equity = None
    if bs and bs['equity_begin'] is not None and bs['equity_end'] is not None:
        avg_equity = (bs['equity_begin'] + bs['equity_end']) / 2.0
    v = _safe_div(net_profit, avg_equity)
    results['roe'] = round(v * 100, 2) if v is not None else None

    # 4. 净利润增长率
    prev_np = prev_profit['net_profit'] if prev_profit else None
    v = _safe_div((net_profit - prev_np) if net_profit is not None and prev_np is not None else None, prev_np)
    results['net_profit_growth'] = round(v * 100, 2) if v is not None else None

    # 5. 管理费用率
    admin_exp = profit['administrative_expense'] if profit else None
    v = _safe_div(admin_exp, revenue)
    results['admin_expense_ratio'] = round(v * 100, 2) if v is not None else None

    # 6. 销售费用率
    sell_exp = profit['selling_expense'] if profit else None
    v = _safe_div(sell_exp, revenue)
    results['sales_expense_ratio'] = round(v * 100, 2) if v is not None else None

    # 7. 资产负债率
    v = _safe_div(bs['liabilities_end'] if bs else None, bs['assets_end'] if bs else None)
    results['debt_ratio'] = round(v * 100, 2) if v is not None else None

    # 8. 流动比率
    v = _safe_div(bs['current_assets_end'] if bs else None, bs['current_liabilities_end'] if bs else None)
    results['current_ratio'] = round(v, 2) if v is not None else None

    # 9. 速动比率
    quick_assets = None
    if bs and bs['current_assets_end'] is not None:
        quick_assets = bs['current_assets_end'] - (bs['inventory_end'] or 0)
    v = _safe_div(quick_assets, bs['current_liabilities_end'] if bs else None)
    results['quick_ratio'] = round(v, 2) if v is not None else None

    # 10. 现金债务保障比率
    op_cash = cf['operating_net_cash'] if cf else None
    liab = bs['liabilities_end'] if bs else None
    v = _safe_div(op_cash, liab)
    results['cash_debt_coverage'] = round(v * 100, 2) if v is not None else None

    # 11. 应收账款周转率
    avg_ar = None
    if bs and bs['accounts_receivable_begin'] is not None and bs['accounts_receivable_end'] is not None:
        avg_ar = (bs['accounts_receivable_begin'] + bs['accounts_receivable_end']) / 2.0
    v = _safe_div(revenue, avg_ar)
    results['ar_turnover'] = round(v, 2) if v is not None else None

    # 12. 应收款周转天数
    results['ar_days'] = round(360 / results['ar_turnover'], 2) if results['ar_turnover'] else None

    # 13. 存货周转率
    avg_inv = None
    if bs and bs['inventory_begin'] is not None and bs['inventory_end'] is not None:
        avg_inv = (bs['inventory_begin'] + bs['inventory_end']) / 2.0
    v = _safe_div(cost, avg_inv)
    results['inventory_turnover'] = round(v, 2) if v is not None else None

    # 14. 总资产周转率
    avg_assets = None
    if bs and bs['assets_begin'] is not None and bs['assets_end'] is not None:
        avg_assets = (bs['assets_begin'] + bs['assets_end']) / 2.0
    v = _safe_div(revenue, avg_assets)
    results['asset_turnover'] = round(v, 2) if v is not None else None

    # 15. 营业收入增长率
    prev_rev = prev_profit['operating_revenue'] if prev_profit else None
    v = _safe_div((revenue - prev_rev) if revenue is not None and prev_rev is not None else None, prev_rev)
    results['revenue_growth'] = round(v * 100, 2) if v is not None else None

    # 16. 资产增长率
    prev_assets = prev_bs['assets_end'] if prev_bs else None
    cur_assets = bs['assets_end'] if bs else None
    v = _safe_div((cur_assets - prev_assets) if cur_assets is not None and prev_assets is not None else None, prev_assets)
    results['asset_growth'] = round(v * 100, 2) if v is not None else None

    # 17. 销售收现比
    sales_cash = cf['sales_cash'] if cf else None
    v = _safe_div(sales_cash, revenue)
    results['cash_to_revenue'] = round(v, 2) if v is not None else None

    return results


# ============================================================
# VAT/EIT 税务指标计算
# ============================================================

def _compute_vat_metrics(vat, small, revenue):
    """计算 VAT 相关指标，返回 {code: value}"""
    results = {}
    if not small and vat:
        vat_payable = vat['total_tax_payable'] or 0
        taxable_sales = vat['sales_taxable_rate'] or 0
        v = _safe_div(vat_payable, taxable_sales)
        results['vat_burden'] = round(v * 100, 2) if v is not None else None
        v = _safe_div(vat['output_tax'], vat['input_tax'])
        results['output_input_ratio'] = round(v, 2) if v is not None else None
        v = _safe_div(vat['transfer_out'], vat['input_tax'])
        results['transfer_out_ratio'] = round(v * 100, 2) if v is not None else None
    elif small and vat:
        tax_total = vat['tax_due_total'] or 0
        sales_total = (vat['sales_3percent'] or 0) + (vat['sales_5percent'] or 0)
        v = _safe_div(tax_total, sales_total) if sales_total else None
        results['vat_burden'] = round(v * 100, 2) if v is not None else None
        results['output_input_ratio'] = None
        results['transfer_out_ratio'] = None
    else:
        results['vat_burden'] = None
        results['output_input_ratio'] = None
        results['transfer_out_ratio'] = None
    return results


def _compute_total_tax_burden(vat, small, eit_tax, revenue):
    """综合税负率"""
    vat_tax = 0
    surcharges = 0
    if not small and vat:
        vat_tax = vat['total_tax_payable'] or 0
        surcharges = (vat['city_maintenance_tax'] or 0) + \
                     (vat['education_surcharge'] or 0) + \
                     (vat['local_education_surcharge'] or 0)
    elif small and vat:
        vat_tax = vat['tax_due_total'] or 0
        surcharges = (vat['city_maintenance_tax'] or 0) + \
                     (vat['education_surcharge'] or 0) + \
                     (vat['local_education_surcharge'] or 0)
    total = vat_tax + surcharges + (eit_tax or 0)
    v = _safe_div(total, revenue) if total > 0 else None
    return round(v * 100, 2) if v is not None else None


# ============================================================
# 月度指标计算
# ============================================================

def _compute_monthly(conn, tid, year, month, std, tp):
    """月度指标：利润用'本期'，BS用当月快照，CF用'本期'，VAT用'本月'/'本期'"""
    pv = _profit_view(std)
    bv = _bs_view(std)
    cv = _cf_view(std)
    small = _is_small(tp)

    profit = _fetch_profit(conn, tid, pv, year, month, '本期')
    revenue = profit['operating_revenue'] if profit else None
    cost = profit['operating_cost'] if profit else None
    net_profit = profit['net_profit'] if profit else None

    # 上期同比
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    prev_profit = _fetch_profit(conn, tid, pv, prev_y, prev_m, '本期')

    bs = _fetch_bs(conn, tid, bv, year, month)
    prev_bs = _fetch_bs(conn, tid, bv, prev_y, prev_m)

    cf = _fetch_cf(conn, tid, cv, year, month, '本期', small)

    results = _compute_common_metrics(profit, prev_profit, bs, prev_bs, cf, revenue, cost, net_profit, small)

    # VAT（月度用'本月'/'本期'）
    vat_tr = '本期' if small else '本月'
    vat = _fetch_vat_small(conn, tid, year, month, vat_tr) if small else _fetch_vat_general(conn, tid, year, month, vat_tr)
    results.update(_compute_vat_metrics(vat, small, revenue))

    # 月度综合税负率：无 EIT，仅 VAT + 附加税
    results['total_tax_burden'] = _compute_total_tax_burden(vat, small, 0, revenue)

    # EIT 月度不可用
    results['eit_burden'] = None
    results['taxable_income_ratio'] = None
    results['zero_filing_ratio'] = None

    # 发票异常率
    results['invoice_anomaly_ratio'] = _calc_invoice_anomaly(conn, tid, year, month, month)

    return [_to_row(tid, year, month, 'monthly', code, val) for code, val in results.items()]


# PLACEHOLDER_QUARTERLY


def _to_row(tid, year, month, period_type, code, value):
    """构造一条指标记录元组"""
    return (tid, year, month, period_type, code, value)


# ============================================================
# 季度指标计算（YTD差值法）
# ============================================================

def _compute_quarterly(conn, tid, year, quarter, std, tp):
    """季度指标：利润/CF用YTD差值法，BS用季末快照，EIT用季度表"""
    pv = _profit_view(std)
    bv = _bs_view(std)
    cv = _cf_view(std)
    small = _is_small(tp)
    q_end = quarter * 3
    q_prev = q_end - 3

    # 利润表 YTD 差值
    ytd_cur = _fetch_profit(conn, tid, pv, year, q_end, '本年累计')
    ytd_prev = _fetch_profit(conn, tid, pv, year, q_prev, '本年累计') if q_prev > 0 else None

    def _ytd_diff(field):
        cur_val = ytd_cur[field] if ytd_cur else None
        prev_val = ytd_prev[field] if ytd_prev else None
        if cur_val is None:
            return None
        return cur_val - (prev_val or 0)

    revenue = _ytd_diff('operating_revenue')
    cost = _ytd_diff('operating_cost')
    net_profit = _ytd_diff('net_profit')

    # 构造 pseudo profit dict for common metrics
    class _PseudoRow:
        def __init__(self, data):
            self._data = data
        def __getitem__(self, key):
            return self._data.get(key)
    profit_pseudo = _PseudoRow({
        'operating_revenue': revenue, 'operating_cost': cost, 'net_profit': net_profit,
        'selling_expense': _ytd_diff('selling_expense'),
        'administrative_expense': _ytd_diff('administrative_expense'),
    })

    # 上年同季度
    prev_ytd_cur = _fetch_profit(conn, tid, pv, year - 1, q_end, '本年累计')
    prev_ytd_prev = _fetch_profit(conn, tid, pv, year - 1, q_prev, '本年累计') if q_prev > 0 else None
    prev_rev = None
    prev_np = None
    if prev_ytd_cur:
        prev_rev_ytd = prev_ytd_cur['operating_revenue']
        prev_rev_prev = prev_ytd_prev['operating_revenue'] if prev_ytd_prev else None
        prev_rev = (prev_rev_ytd or 0) - (prev_rev_prev or 0) if prev_rev_ytd is not None else None
        prev_np_ytd = prev_ytd_cur['net_profit']
        prev_np_prev = prev_ytd_prev['net_profit'] if prev_ytd_prev else None
        prev_np = (prev_np_ytd or 0) - (prev_np_prev or 0) if prev_np_ytd is not None else None
    prev_profit_pseudo = _PseudoRow({
        'operating_revenue': prev_rev, 'net_profit': prev_np,
    })

    bs = _fetch_bs(conn, tid, bv, year, q_end)
    prev_bs = _fetch_bs(conn, tid, bv, year - 1, q_end)

    # CF YTD 差值
    cf_cur = _fetch_cf(conn, tid, cv, year, q_end, '本年累计', small)
    cf_prev = _fetch_cf(conn, tid, cv, year, q_prev, '本年累计', small) if q_prev > 0 else None
    cf_sales = None
    cf_op = None
    if cf_cur:
        cf_sales = (cf_cur['sales_cash'] or 0) - ((cf_prev['sales_cash'] or 0) if cf_prev else 0)
        cf_op = (cf_cur['operating_net_cash'] or 0) - ((cf_prev['operating_net_cash'] or 0) if cf_prev else 0)
    cf_pseudo = _PseudoRow({'sales_cash': cf_sales, 'operating_net_cash': cf_op})

    results = _compute_common_metrics(
        profit_pseudo, prev_profit_pseudo, bs, prev_bs, cf_pseudo,
        revenue, cost, net_profit, small
    )

    # VAT 累计差值
    vat_tr = '累计'
    vat_cur = _fetch_vat_small(conn, tid, year, q_end, vat_tr) if small else _fetch_vat_general(conn, tid, year, q_end, vat_tr)
    results.update(_compute_vat_metrics(vat_cur, small, revenue))

    # EIT 季度
    eit = conn.execute(
        "SELECT revenue, actual_profit, tax_rate, tax_payable FROM vw_eit_quarter_main "
        "WHERE taxpayer_id = ? AND period_year = ? AND period_quarter = ? LIMIT 1",
        (tid, year, quarter)
    ).fetchone()
    eit_tax = eit['tax_payable'] if eit else None
    v = _safe_div(eit_tax, revenue)
    results['eit_burden'] = round(v * 100, 2) if v is not None else None

    results['total_tax_burden'] = _compute_total_tax_burden(vat_cur, small, eit_tax, revenue)

    # 应税所得率（季度表用 actual_profit 近似）
    eit_taxable = eit['actual_profit'] if eit else None
    eit_rev = eit['revenue'] if eit else None
    v = _safe_div(eit_taxable, eit_rev)
    results['taxable_income_ratio'] = round(v * 100, 2) if v is not None else None

    # 零申报率
    q_start = q_prev + 1
    results['zero_filing_ratio'] = _calc_zero_filing(conn, tid, year, q_start, q_end, small)

    # 发票异常率
    results['invoice_anomaly_ratio'] = _calc_invoice_anomaly(conn, tid, year, q_start, q_end)

    return [_to_row(tid, year, q_end, 'quarterly', code, val) for code, val in results.items()]


# PLACEHOLDER_ANNUAL


# ============================================================
# 年度指标计算
# ============================================================

def _compute_annual(conn, tid, year, std, tp):
    """年度指标：利润/CF用'本年累计'(month=12)，BS用12月快照，EIT用年度表"""
    pv = _profit_view(std)
    bv = _bs_view(std)
    cv = _cf_view(std)
    small = _is_small(tp)

    profit = _fetch_profit(conn, tid, pv, year, 12, '本年累计')
    revenue = profit['operating_revenue'] if profit else None
    cost = profit['operating_cost'] if profit else None
    net_profit = profit['net_profit'] if profit else None

    prev_profit = _fetch_profit(conn, tid, pv, year - 1, 12, '本年累计')

    bs = _fetch_bs(conn, tid, bv, year, 12)
    prev_bs = _fetch_bs(conn, tid, bv, year - 1, 12)

    cf = _fetch_cf(conn, tid, cv, year, 12, '本年累计', small)

    results = _compute_common_metrics(profit, prev_profit, bs, prev_bs, cf, revenue, cost, net_profit, small)

    # VAT 累计
    vat = _fetch_vat_small(conn, tid, year, 12, '累计') if small else _fetch_vat_general(conn, tid, year, 12, '累计')
    results.update(_compute_vat_metrics(vat, small, revenue))

    # EIT 年度
    eit = conn.execute(
        "SELECT revenue, taxable_income, actual_tax_payable FROM vw_eit_annual_main "
        "WHERE taxpayer_id = ? AND period_year = ? LIMIT 1",
        (tid, year)
    ).fetchone()
    eit_tax = eit['actual_tax_payable'] if eit else None
    v = _safe_div(eit_tax, revenue)
    results['eit_burden'] = round(v * 100, 2) if v is not None else None

    results['total_tax_burden'] = _compute_total_tax_burden(vat, small, eit_tax, revenue)

    eit_taxable = eit['taxable_income'] if eit else None
    eit_rev = eit['revenue'] if eit else None
    v = _safe_div(eit_taxable, eit_rev)
    results['taxable_income_ratio'] = round(v * 100, 2) if v is not None else None

    results['zero_filing_ratio'] = _calc_zero_filing(conn, tid, year, 1, 12, small)
    results['invoice_anomaly_ratio'] = _calc_invoice_anomaly(conn, tid, year, 1, 12)

    return [_to_row(tid, year, 12, 'annual', code, val) for code, val in results.items()]


# ============================================================
# 主入口
# ============================================================

def _load_metric_dict(conn):
    """加载指标字典 {code: {name, category, unit}}"""
    rows = conn.execute(
        "SELECT metric_code, metric_name, metric_category, metric_unit "
        "FROM financial_metrics_item_dict WHERE is_active = 1"
    ).fetchall()
    return {r['metric_code']: dict(r) for r in rows}


def calculate_and_save_v2(db_path=None, taxpayer_id=None, year=None, month=None):
    """主入口：遍历纳税人/期间，计算月度+季度+年度指标，写入 financial_metrics_item"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    metric_dict = _load_metric_dict(conn)
    eval_rules = _load_eval_rules(conn)

    if taxpayer_id:
        taxpayers = [(taxpayer_id,)]
    else:
        taxpayers = conn.execute(
            "SELECT taxpayer_id FROM taxpayer_info WHERE status = 'active'"
        ).fetchall()

    total_inserted = 0

    for (tid,) in taxpayers:
        std, tp = _get_accounting_info(conn, tid)
        if not std:
            continue

        # 确定期间
        pv = _profit_view(std)
        if year and month:
            periods = [(year, month)]
        else:
            periods = conn.execute(
                f"SELECT DISTINCT period_year, period_month FROM {pv} "
                f"WHERE taxpayer_id = ? ORDER BY period_year, period_month",
                (tid,)
            ).fetchall()

        years_done_quarterly = set()
        years_done_annual = set()

        for (py, pm) in periods:
            # --- 月度 ---
            print(f"  月度: {tid} {py}年{pm}月...")
            rows = _compute_monthly(conn, tid, py, pm, std, tp)
            total_inserted += _save_rows(conn, rows, metric_dict, eval_rules)

            # --- 季度（季末月触发）---
            if pm in (3, 6, 9, 12):
                q = pm // 3
                key = (py, q)
                if key not in years_done_quarterly:
                    years_done_quarterly.add(key)
                    print(f"  季度: {tid} {py}年Q{q}...")
                    rows = _compute_quarterly(conn, tid, py, q, std, tp)
                    total_inserted += _save_rows(conn, rows, metric_dict, eval_rules)

            # --- 年度（12月触发）---
            if pm == 12 and py not in years_done_annual:
                years_done_annual.add(py)
                print(f"  年度: {tid} {py}年...")
                rows = _compute_annual(conn, tid, py, std, tp)
                total_inserted += _save_rows(conn, rows, metric_dict, eval_rules)

    conn.commit()
    conn.close()
    print(f"\n[calculate_metrics_v2] 完成，共写入 {total_inserted} 条指标记录")
    return total_inserted


def _save_rows(conn, rows, metric_dict, eval_rules):
    """将计算结果写入 financial_metrics_item，返回写入条数"""
    count = 0
    now = datetime.now().isoformat()
    for (tid, year, month, period_type, code, value) in rows:
        mdef = metric_dict.get(code)
        if not mdef:
            continue
        eval_level = _evaluate(value, eval_rules.get(code))
        conn.execute(
            """INSERT OR REPLACE INTO financial_metrics_item
            (taxpayer_id, period_year, period_month, period_type, metric_code,
             metric_name, metric_category, metric_value, metric_unit,
             evaluation_level, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tid, year, month, period_type, code,
             mdef['metric_name'], mdef['metric_category'], value, mdef['metric_unit'],
             eval_level, now)
        )
        count += 1
    return count


if __name__ == '__main__':
    print("=" * 60)
    print("财务指标自动计算 v2（月度/季度/年度）")
    print("=" * 60)
    # 先确保同义词已写入
    from database.calculate_metrics import seed_metric_synonyms
    seed_metric_synonyms()
    calculate_and_save_v2()
