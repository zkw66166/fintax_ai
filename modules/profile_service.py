"""企业画像数据聚合服务

从 fintax_ai.db 各域视图/表中提取数据，聚合为企业画像结构化 JSON。
"""
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH
from config.config_loader import load_json as _load_json

_CFG_profile = _load_json(Path(__file__).resolve().parent.parent / "config" / "profile" / "evaluation_rules.json", {})

# ── 画像结果缓存（TTL 5分钟）──────────────────────────────
_profile_cache = {}  # key: (taxpayer_id, year) → {'data': dict, 'ts': float}
_PROFILE_CACHE_TTL = _CFG_profile.get("cache_ttl", 300)  # 5 minutes


# ── 评价规则 ──────────────────────────────────────────────
_EVAL_RULES_RAW = _CFG_profile.get("eval_rules", None)
if _EVAL_RULES_RAW:
    EVAL_RULES = {k: [tuple(r) for r in v] for k, v in _EVAL_RULES_RAW.items()}
else:
    EVAL_RULES = {
        "debt_ratio": [
            (30, "优秀", "positive"), (50, "良好", "positive"),
            (70, "偏高", "warning"), (100, "风险", "negative"),
        ],
        "current_ratio": [
            (1.0, "偏低", "warning"), (1.5, "一般", "neutral"),
            (2.0, "良好", "positive"), (9999, "优秀", "positive"),
        ],
        "quick_ratio": [
            (0.8, "偏低", "warning"), (1.0, "一般", "neutral"),
            (1.5, "良好", "positive"), (9999, "优秀", "positive"),
        ],
        "gross_margin": [
            (10, "偏低", "warning"), (20, "一般", "neutral"),
            (40, "良好", "positive"), (100, "优秀", "positive"),
        ],
        "net_margin": [
            (3, "偏低", "warning"), (8, "一般", "neutral"),
            (15, "良好", "positive"), (100, "优秀", "positive"),
        ],
        "roe": [
            (5, "偏低", "warning"), (10, "一般", "neutral"),
            (20, "良好", "positive"), (100, "优秀", "positive"),
        ],
        "revenue_growth": [
            (0, "负增长", "negative"), (10, "低速", "neutral"),
            (20, "中速", "positive"), (9999, "高速增长", "growth"),
        ],
        "total_tax_burden": [
            (2, "偏低", "warning"), (5, "合理", "positive"),
            (10, "偏高", "warning"), (100, "过高", "negative"),
        ],
    }


def evaluate_metric(code: str, value) -> Optional[dict]:
    """根据指标代码和值返回评价"""
    if value is None:
        return None
    rules = EVAL_RULES.get(code)
    if not rules:
        return None
    for threshold, level, eval_type in rules:
        if value <= threshold:
            return {"level": level, "type": eval_type}
    last = rules[-1]
    return {"level": last[1], "type": last[2]}


def evaluate_growth(current, previous) -> Optional[dict]:
    """计算增长率并评价"""
    if current is None or previous is None:
        return None
    if previous == 0:
        return {"rate": None, "eval": None}
    rate = round((current - previous) / abs(previous) * 100, 1)
    if rate > 20:
        ev = {"level": "高速增长", "type": "growth"}
    elif rate > 0:
        ev = {"level": "增长", "type": "positive"}
    elif rate == 0:
        ev = {"level": "持平", "type": "neutral"}
    else:
        ev = {"level": "下降", "type": "negative"}
    return {"rate": rate, "eval": ev}


def _safe_div(a, b, pct=True):
    """安全除法，pct=True 时结果乘 100"""
    if a is None or b is None or b == 0:
        return None
    r = a / b
    return round(r * 100, 2) if pct else round(r, 4)


def _get_gaap(conn, taxpayer_id: str) -> Tuple[str, str]:
    """获取纳税人的 GAAP 类型和会计准则"""
    row = conn.execute(
        "SELECT taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
        (taxpayer_id,),
    ).fetchone()
    if not row:
        return "CAS", "企业会计准则"
    std = row["accounting_standard"] or "企业会计准则"
    if std == "小企业会计准则":
        return "SAS", std
    return "CAS", std


def _get_bs_gaap(conn, taxpayer_id: str) -> str:
    """获取资产负债表 GAAP 类型"""
    gaap, _ = _get_gaap(conn, taxpayer_id)
    return "ASBE" if gaap == "CAS" else "ASSE"


def _latest_revision_bs(conn, tid, year, month, gaap):
    """获取资产负债表最新修订号"""
    row = conn.execute(
        """SELECT MAX(revision_no) FROM fs_balance_sheet_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=?""",
        (tid, year, month, gaap),
    ).fetchone()
    return row[0] if row and row[0] is not None else 0


def _latest_revision_is(conn, tid, year, month, gaap):
    """获取利润表最新修订号"""
    row = conn.execute(
        """SELECT MAX(revision_no) FROM fs_income_statement_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=?""",
        (tid, year, month, gaap),
    ).fetchone()
    return row[0] if row and row[0] is not None else 0


def _latest_revision_cf(conn, tid, year, month, gaap):
    """获取现金流量表最新修订号"""
    row = conn.execute(
        """SELECT MAX(revision_no) FROM fs_cash_flow_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=?""",
        (tid, year, month, gaap),
    ).fetchone()
    return row[0] if row and row[0] is not None else 0


def _find_latest_month(conn, table, tid, year, gaap_col="gaap_type", gaap_val=None):
    """找到指定年度有数据的最大月份"""
    if gaap_val:
        row = conn.execute(
            f"SELECT MAX(period_month) FROM {table} WHERE taxpayer_id=? AND period_year=? AND {gaap_col}=?",
            (tid, year, gaap_val),
        ).fetchone()
    else:
        row = conn.execute(
            f"SELECT MAX(period_month) FROM {table} WHERE taxpayer_id=? AND period_year=?",
            (tid, year),
        ).fetchone()
    return row[0] if row and row[0] else None


# ── 子查询函数 ────────────────────────────────────────────

def _query_basic_info(conn, tid):
    """基本信息：合并 taxpayer_info + company_business_registration"""
    row = conn.execute("SELECT * FROM taxpayer_info WHERE taxpayer_id = ?", (tid,)).fetchone()
    if not row:
        return None
    result = dict(row)

    # 从 company_business_registration 补充工商注册信息
    cbr = conn.execute(
        "SELECT * FROM company_business_registration WHERE taxpayer_id = ? OR unified_social_credit_code = ?",
        (tid, tid),
    ).fetchone()
    if cbr:
        cbr = dict(cbr)
        # 补充 taxpayer_info 中没有的字段
        for key in (
            "company_type", "established_date", "paid_in_capital",
            "insured_count", "company_scale", "english_name",
            "contact_phone", "email", "province", "city", "district",
            "industry_level1", "industry_level2", "industry_level3",
            "registration_authority", "website", "approval_date",
            "business_term", "industry_commerce_reg_no", "organization_code",
            "former_name",
        ):
            result.setdefault(key, cbr.get(key))
        # 工商信息更权威，优先使用 CBR 值
        for key in ("registered_capital", "business_scope", "registered_address", "legal_representative"):
            if cbr.get(key):
                result[key] = cbr[key]
    return result


def _query_asset_structure(conn, tid, year):
    """资产结构：从资产负债表取期末数据"""
    gaap = _get_bs_gaap(conn, tid)
    month = _find_latest_month(conn, "fs_balance_sheet_item", tid, year, "gaap_type", gaap)
    if not month:
        return None
    rev = _latest_revision_bs(conn, tid, year, month, gaap)
    rows = conn.execute(
        """SELECT item_code, ending_balance, beginning_balance
           FROM fs_balance_sheet_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
        (tid, year, month, gaap, rev),
    ).fetchall()
    data = {r["item_code"]: {"end": r["ending_balance"], "begin": r["beginning_balance"]} for r in rows}

    total_assets = (data.get("ASSETS") or {}).get("end")
    current_assets = (data.get("CURRENT_ASSETS") or {}).get("end")
    fixed_assets = (data.get("FIXED_ASSETS") or {}).get("end")
    intangible = (data.get("INTANGIBLE_ASSETS") or {}).get("end")
    total_liabilities = (data.get("LIABILITIES") or {}).get("end")
    total_equity = (data.get("EQUITY") or {}).get("end")

    other_assets = None
    if total_assets is not None and current_assets is not None:
        non_current = (data.get("NON_CURRENT_ASSETS") or {}).get("end") or 0
        known = (fixed_assets or 0) + (intangible or 0)
        other_assets = max(0, non_current - known)

    debt_ratio = _safe_div(total_liabilities, total_assets)

    return {
        "period": f"{year}-{month:02d}",
        "total_assets": total_assets,
        "current_assets": current_assets,
        "fixed_assets": fixed_assets,
        "intangible_assets": intangible,
        "other_non_current": other_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "debt_ratio": debt_ratio,
        "debt_ratio_eval": evaluate_metric("debt_ratio", debt_ratio),
        "begin_total_assets": (data.get("ASSETS") or {}).get("begin"),
    }


def _query_profit_data(conn, tid, year):
    """利润表年度数据"""
    gaap, _ = _get_gaap(conn, tid)
    month = _find_latest_month(conn, "fs_income_statement_item", tid, year, "gaap_type", gaap)
    if not month:
        return None
    rev = _latest_revision_is(conn, tid, year, month, gaap)
    rows = conn.execute(
        """SELECT item_code, current_amount, cumulative_amount
           FROM fs_income_statement_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
        (tid, year, month, gaap, rev),
    ).fetchall()
    data = {r["item_code"]: {"current": r["current_amount"], "cumulative": r["cumulative_amount"]} for r in rows}

    revenue = (data.get("operating_revenue") or {}).get("cumulative")
    cost = (data.get("operating_cost") or {}).get("cumulative")
    net_profit = (data.get("net_profit") or {}).get("cumulative")
    selling = (data.get("selling_expense") or {}).get("cumulative")
    admin = (data.get("administrative_expense") or {}).get("cumulative")
    rd = (data.get("rd_expense") or {}).get("cumulative")
    financial = (data.get("financial_expense") or {}).get("cumulative")

    gross_margin = _safe_div((revenue or 0) - (cost or 0), revenue) if revenue else None
    net_margin = _safe_div(net_profit, revenue)

    return {
        "period": f"{year}-{month:02d}",
        "revenue": revenue,
        "cost": cost,
        "net_profit": net_profit,
        "selling_expense": selling,
        "admin_expense": admin,
        "rd_expense": rd,
        "financial_expense": financial,
        "gross_margin": gross_margin,
        "gross_margin_eval": evaluate_metric("gross_margin", gross_margin),
        "net_margin": net_margin,
        "net_margin_eval": evaluate_metric("net_margin", net_margin),
        "selling_expense_rate": _safe_div(selling, revenue),
        "admin_expense_rate": _safe_div(admin, revenue),
    }


def _query_cash_flow(conn, tid, year):
    """现金流量表年度数据"""
    gaap, _ = _get_gaap(conn, tid)
    month = _find_latest_month(conn, "fs_cash_flow_item", tid, year, "gaap_type", gaap)
    if not month:
        return None
    rev = _latest_revision_cf(conn, tid, year, month, gaap)
    rows = conn.execute(
        """SELECT item_code, cumulative_amount
           FROM fs_cash_flow_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
        (tid, year, month, gaap, rev),
    ).fetchall()
    data = {r["item_code"]: r["cumulative_amount"] for r in rows}

    operating = data.get("operating_net_cash")
    investing = data.get("investing_net_cash")
    financing = data.get("financing_net_cash")

    op_eval = None
    if operating is not None:
        if operating > 0:
            op_eval = {"level": "充足", "type": "positive"}
        else:
            op_eval = {"level": "不足", "type": "negative"}

    return {
        "period": f"{year}-{month:02d}",
        "operating": operating,
        "operating_eval": op_eval,
        "investing": investing,
        "financing": financing,
    }


def _query_growth_metrics(conn, tid, year):
    """增长指标：对比当年与上年"""
    gaap, _ = _get_gaap(conn, tid)
    bs_gaap = _get_bs_gaap(conn, tid)

    def get_profit_cumulative(y):
        m = _find_latest_month(conn, "fs_income_statement_item", tid, y, "gaap_type", gaap)
        if not m:
            return None, None
        rev = _latest_revision_is(conn, tid, y, m, gaap)
        rows = conn.execute(
            """SELECT item_code, cumulative_amount FROM fs_income_statement_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
            (tid, y, m, gaap, rev),
        ).fetchall()
        d = {r["item_code"]: r["cumulative_amount"] for r in rows}
        return d.get("operating_revenue"), d.get("net_profit")

    def get_total_assets(y):
        m = _find_latest_month(conn, "fs_balance_sheet_item", tid, y, "gaap_type", bs_gaap)
        if not m:
            return None
        rev = _latest_revision_bs(conn, tid, y, m, bs_gaap)
        row = conn.execute(
            """SELECT ending_balance FROM fs_balance_sheet_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=? AND item_code='ASSETS'""",
            (tid, y, m, bs_gaap, rev),
        ).fetchone()
        return row["ending_balance"] if row else None

    rev_cur, np_cur = get_profit_cumulative(year)
    rev_prev, np_prev = get_profit_cumulative(year - 1)
    assets_cur = get_total_assets(year)
    assets_prev = get_total_assets(year - 1)

    return {
        "revenue_growth": evaluate_growth(rev_cur, rev_prev),
        "net_profit_growth": evaluate_growth(np_cur, np_prev),
        "asset_growth": evaluate_growth(assets_cur, assets_prev),
    }


def _query_financial_metrics(conn, tid, year):
    """从 financial_metrics_item 取预计算指标"""
    rows = conn.execute(
        """SELECT metric_code, metric_name, metric_category, metric_value, metric_unit, evaluation_level
           FROM financial_metrics_item
           WHERE taxpayer_id=? AND period_year=? AND period_type='yearly'
           ORDER BY metric_category, metric_code""",
        (tid, year),
    ).fetchall()
    if not rows:
        # 回退到 financial_metrics 表，取最新月份去重
        rows = conn.execute(
            """SELECT m.metric_code, m.metric_name, m.metric_category,
                      m.metric_value, m.metric_unit, m.evaluation_level
               FROM financial_metrics m
               INNER JOIN (
                   SELECT metric_code, MAX(period_month) AS max_month
                   FROM financial_metrics
                   WHERE taxpayer_id=? AND period_year=?
                   GROUP BY metric_code
               ) latest ON m.metric_code = latest.metric_code
                        AND m.period_month = latest.max_month
               WHERE m.taxpayer_id=? AND m.period_year=?
               ORDER BY m.metric_category, m.metric_code""",
            (tid, year, tid, year),
        ).fetchall()
    if not rows:
        return None

    by_category = {}
    for r in rows:
        cat = r["metric_category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "code": r["metric_code"],
            "name": r["metric_name"],
            "value": r["metric_value"],
            "unit": r["metric_unit"],
            "eval_level": r["evaluation_level"],
        })
    return by_category


def _query_tax_summary(conn, tid, year):
    """税务汇总：VAT + EIT"""
    info = conn.execute(
        "SELECT taxpayer_type FROM taxpayer_info WHERE taxpayer_id=?", (tid,)
    ).fetchone()
    tp_type = info["taxpayer_type"] if info else "一般纳税人"

    vat_total = None
    if tp_type == "一般纳税人":
        row = conn.execute(
            """SELECT SUM(total_tax_payable) AS vat_total
               FROM vat_return_general
               WHERE taxpayer_id=? AND period_year=? AND item_type='一般项目' AND time_range='本月'
                 AND revision_no = (
                     SELECT MAX(revision_no) FROM vat_return_general v2
                     WHERE v2.taxpayer_id=vat_return_general.taxpayer_id
                       AND v2.period_year=vat_return_general.period_year
                       AND v2.period_month=vat_return_general.period_month
                       AND v2.item_type=vat_return_general.item_type
                       AND v2.time_range=vat_return_general.time_range
                 )""",
            (tid, year),
        ).fetchone()
        vat_total = row["vat_total"] if row else None
    else:
        row = conn.execute(
            """SELECT SUM(tax_supplement_refund) AS vat_total
               FROM vat_return_small
               WHERE taxpayer_id=? AND period_year=? AND item_type='货物及劳务' AND time_range='本期'
                 AND revision_no = (
                     SELECT MAX(revision_no) FROM vat_return_small v2
                     WHERE v2.taxpayer_id=vat_return_small.taxpayer_id
                       AND v2.period_year=vat_return_small.period_year
                       AND v2.period_month=vat_return_small.period_month
                       AND v2.item_type=vat_return_small.item_type
                       AND v2.time_range=vat_return_small.time_range
                 )""",
            (tid, year),
        ).fetchone()
        vat_total = row["vat_total"] if row else None

    # EIT
    eit_total = None
    row = conn.execute(
        """SELECT m.actual_tax_payable
           FROM eit_annual_filing f JOIN eit_annual_main m ON f.filing_id = m.filing_id
           WHERE f.taxpayer_id=? AND f.period_year=?
           ORDER BY f.revision_no DESC LIMIT 1""",
        (tid, year),
    ).fetchone()
    if row:
        eit_total = row["actual_tax_payable"]

    total = (vat_total or 0) + (eit_total or 0)

    return {
        "vat_total": vat_total,
        "eit_total": eit_total,
        "tax_total": total if (vat_total is not None or eit_total is not None) else None,
    }


def _query_invoice_summary(conn, tid, year):
    """发票统计"""
    sales = conn.execute(
        """SELECT COUNT(DISTINCT invoice_pk) AS cnt, SUM(total_amount) AS amt
           FROM inv_spec_sales WHERE taxpayer_id=? AND period_year=?""",
        (tid, year),
    ).fetchone()
    purchase = conn.execute(
        """SELECT COUNT(DISTINCT invoice_pk) AS cnt, SUM(total_amount) AS amt
           FROM inv_spec_purchase WHERE taxpayer_id=? AND period_year=?""",
        (tid, year),
    ).fetchone()
    return {
        "sales_count": sales["cnt"] if sales else 0,
        "sales_amount": sales["amt"] if sales else None,
        "purchase_count": purchase["cnt"] if purchase else 0,
        "purchase_amount": purchase["amt"] if purchase else None,
    }


def _query_rd_innovation(conn, tid, year):
    """研发创新：从利润表取研发费用"""
    gaap, _ = _get_gaap(conn, tid)
    month = _find_latest_month(conn, "fs_income_statement_item", tid, year, "gaap_type", gaap)
    if not month:
        return None
    rev = _latest_revision_is(conn, tid, year, month, gaap)
    rows = conn.execute(
        """SELECT item_code, cumulative_amount FROM fs_income_statement_item
           WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?
             AND item_code IN ('rd_expense', 'operating_revenue')""",
        (tid, year, month, gaap, rev),
    ).fetchall()
    data = {r["item_code"]: r["cumulative_amount"] for r in rows}
    rd = data.get("rd_expense")
    revenue = data.get("operating_revenue")
    intensity = _safe_div(rd, revenue)
    intensity_eval = None
    if intensity is not None:
        if intensity >= 6:
            intensity_eval = {"level": "高", "type": "positive"}
        elif intensity >= 3:
            intensity_eval = {"level": "中", "type": "neutral"}
        else:
            intensity_eval = {"level": "低", "type": "warning"}
    return {
        "rd_expense": rd,
        "rd_intensity": intensity,
        "rd_intensity_eval": intensity_eval,
    }


def _query_cross_border(conn, tid, year):
    """跨境业务：从 EIT 年度取境外所得"""
    row = conn.execute(
        """SELECT m.less_foreign_income, m.add_foreign_tax_due,
                  m.less_foreign_tax_credit_amount, m.revenue
           FROM eit_annual_filing f JOIN eit_annual_main m ON f.filing_id = m.filing_id
           WHERE f.taxpayer_id=? AND f.period_year=?
           ORDER BY f.revision_no DESC LIMIT 1""",
        (tid, year),
    ).fetchone()
    if not row:
        return None
    foreign_income = row["less_foreign_income"]
    revenue = row["revenue"]
    return {
        "foreign_income": foreign_income,
        "foreign_income_ratio": _safe_div(foreign_income, revenue),
        "foreign_tax_due": row["add_foreign_tax_due"],
        "foreign_tax_credit": row["less_foreign_tax_credit_amount"],
    }


def _query_shareholders(conn, tid, year):
    """股权与治理：从 eit_annual_shareholder 取股东信息"""
    # filing_id 格式: {taxpayer_id}_{year}_0
    rows = conn.execute(
        """SELECT s.shareholder_name, s.investment_ratio, s.dividend_amount,
                  s.nationality_or_address, s.is_remaining_total
           FROM eit_annual_filing f
           JOIN eit_annual_shareholder s ON f.filing_id = s.filing_id
           WHERE f.taxpayer_id=? AND f.period_year=?
           ORDER BY f.revision_no DESC, s.investment_ratio DESC""",
        (tid, year),
    ).fetchall()
    if not rows:
        # 尝试上一年
        rows = conn.execute(
            """SELECT s.shareholder_name, s.investment_ratio, s.dividend_amount,
                      s.nationality_or_address, s.is_remaining_total
               FROM eit_annual_filing f
               JOIN eit_annual_shareholder s ON f.filing_id = s.filing_id
               WHERE f.taxpayer_id=? AND f.period_year=?
               ORDER BY f.revision_no DESC, s.investment_ratio DESC""",
            (tid, year - 1),
        ).fetchall()
    if not rows:
        return None

    shareholders = []
    for r in rows:
        shareholders.append({
            "name": r["shareholder_name"],
            "ratio": r["investment_ratio"],
            "dividend": r["dividend_amount"],
            "address": r["nationality_or_address"],
        })

    total_count = len(shareholders)
    top = shareholders[0] if shareholders else None
    top_name = top["name"] if top else None
    top_ratio = top["ratio"] if top else None
    is_controlling = top_ratio is not None and top_ratio > 50

    return {
        "shareholders": shareholders,
        "total_count": total_count,
        "top_shareholder": top_name,
        "top_ratio": top_ratio,
        "is_controlling": is_controlling,
        "total_dividend": sum(s["dividend"] or 0 for s in shareholders),
    }


def _query_employee_structure(conn, tid):
    """组织与人力：从 hr_employee_info 取人员结构"""
    # 通过 taxpayer_name 关联 company_name
    tp = conn.execute(
        "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id=?", (tid,)
    ).fetchone()
    if not tp:
        return None
    company_name = tp["taxpayer_name"]

    # 在职员工统计
    base_where = "company_name=? AND is_on_the_job=1"
    total = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM hr_employee_info WHERE {base_where}",
        (company_name,),
    ).fetchone()["cnt"]
    if total == 0:
        return None

    # 按岗位类型分组
    position_rows = conn.execute(
        f"""SELECT position_type, COUNT(*) AS cnt
            FROM hr_employee_info WHERE {base_where}
            GROUP BY position_type ORDER BY cnt DESC""",
        (company_name,),
    ).fetchall()
    position_dist = [{"type": r["position_type"], "count": r["cnt"],
                       "ratio": round(r["cnt"] / total * 100, 1)} for r in position_rows]

    # 研发人员
    rd_count = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM hr_employee_info WHERE {base_where} AND position_type='研发'",
        (company_name,),
    ).fetchone()["cnt"]
    rd_ratio = round(rd_count / total * 100, 1) if total else 0

    # 学历分布
    edu_rows = conn.execute(
        f"""SELECT education, COUNT(*) AS cnt
            FROM hr_employee_info WHERE {base_where}
            GROUP BY education ORDER BY education_degree DESC""",
        (company_name,),
    ).fetchall()
    edu_dist = [{"education": r["education"], "count": r["cnt"],
                  "ratio": round(r["cnt"] / total * 100, 1)} for r in edu_rows]

    # 本科及以上占比
    bachelor_plus = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM hr_employee_info WHERE {base_where} AND education_degree >= 2",
        (company_name,),
    ).fetchone()["cnt"]
    bachelor_ratio = round(bachelor_plus / total * 100, 1) if total else 0

    # 高新技术人员
    high_tech = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM hr_employee_info WHERE {base_where} AND is_high_tech_person=1",
        (company_name,),
    ).fetchone()["cnt"]
    high_tech_ratio = round(high_tech / total * 100, 1) if total else 0

    # 平均年龄
    avg_age = conn.execute(
        f"SELECT AVG(age) AS avg_age FROM hr_employee_info WHERE {base_where}",
        (company_name,),
    ).fetchone()["avg_age"]

    # 平均工龄
    avg_work_years = conn.execute(
        f"SELECT AVG(work_years) AS avg_wy FROM hr_employee_info WHERE {base_where}",
        (company_name,),
    ).fetchone()["avg_wy"]

    # 性别分布
    gender_rows = conn.execute(
        f"""SELECT gender, COUNT(*) AS cnt
            FROM hr_employee_info WHERE {base_where}
            GROUP BY gender""",
        (company_name,),
    ).fetchall()
    male = sum(r["cnt"] for r in gender_rows if r["gender"] == "1")
    female = sum(r["cnt"] for r in gender_rows if r["gender"] == "2")

    return {
        "total_employees": total,
        "rd_count": rd_count,
        "rd_ratio": rd_ratio,
        "position_dist": position_dist,
        "edu_dist": edu_dist,
        "bachelor_ratio": bachelor_ratio,
        "high_tech_count": high_tech,
        "high_tech_ratio": high_tech_ratio,
        "avg_age": round(avg_age, 1) if avg_age else None,
        "avg_work_years": round(avg_work_years, 1) if avg_work_years else None,
        "male_count": male,
        "female_count": female,
    }


def _query_compliance_risk(conn, tid, year):
    """合规风险：从 financial_metrics 取风险指标"""
    rows = conn.execute(
        """SELECT m.metric_code, m.metric_name, m.metric_value, m.metric_unit, m.evaluation_level
           FROM financial_metrics m
           INNER JOIN (
               SELECT metric_code, MAX(period_month) AS max_month
               FROM financial_metrics
               WHERE taxpayer_id=? AND period_year=? AND metric_category='风险预警类'
               GROUP BY metric_code
           ) latest ON m.metric_code = latest.metric_code
                    AND m.period_month = latest.max_month
           WHERE m.taxpayer_id=? AND m.period_year=? AND m.metric_category='风险预警类'
           ORDER BY m.metric_code""",
        (tid, year, tid, year),
    ).fetchall()
    risk_metrics = [dict(r) for r in rows] if rows else []

    # 补充流动性风险评估
    asset_data = _query_asset_structure(conn, tid, year)
    liquidity_eval = None
    if asset_data and asset_data.get("debt_ratio") is not None:
        dr = asset_data["debt_ratio"]
        if dr < 50:
            liquidity_eval = {"level": "安全", "type": "positive"}
        elif dr < 70:
            liquidity_eval = {"level": "关注", "type": "warning"}
        else:
            liquidity_eval = {"level": "风险", "type": "negative"}

    return {
        "risk_metrics": risk_metrics,
        "liquidity_eval": liquidity_eval,
    }


# ── 主入口 ────────────────────────────────────────────────

def _prefetch_eav_data(conn, tid, year, gaap, bs_gaap):
    """批量预取 EAV 表数据，减少重复查询。

    Returns dict with keys: bs_items, is_items, cf_items, is_prev_items
    """
    # 资产负债表
    bs_month = _find_latest_month(conn, "fs_balance_sheet_item", tid, year, "gaap_type", bs_gaap)
    bs_items = {}
    if bs_month:
        rev = _latest_revision_bs(conn, tid, year, bs_month, bs_gaap)
        rows = conn.execute(
            """SELECT item_code, ending_balance, beginning_balance
               FROM fs_balance_sheet_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
            (tid, year, bs_month, bs_gaap, rev),
        ).fetchall()
        bs_items = {r["item_code"]: {"end": r["ending_balance"], "begin": r["beginning_balance"]} for r in rows}

    # 利润表（当年）
    is_month = _find_latest_month(conn, "fs_income_statement_item", tid, year, "gaap_type", gaap)
    is_items = {}
    if is_month:
        rev = _latest_revision_is(conn, tid, year, is_month, gaap)
        rows = conn.execute(
            """SELECT item_code, current_amount, cumulative_amount
               FROM fs_income_statement_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
            (tid, year, is_month, gaap, rev),
        ).fetchall()
        is_items = {r["item_code"]: {"current": r["current_amount"], "cumulative": r["cumulative_amount"]} for r in rows}

    # 利润表（上年，用于增长计算）
    is_prev_month = _find_latest_month(conn, "fs_income_statement_item", tid, year - 1, "gaap_type", gaap)
    is_prev_items = {}
    if is_prev_month:
        rev = _latest_revision_is(conn, tid, year - 1, is_prev_month, gaap)
        rows = conn.execute(
            """SELECT item_code, cumulative_amount
               FROM fs_income_statement_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
            (tid, year - 1, is_prev_month, gaap, rev),
        ).fetchall()
        is_prev_items = {r["item_code"]: r["cumulative_amount"] for r in rows}

    # 现金流量表
    cf_month = _find_latest_month(conn, "fs_cash_flow_item", tid, year, "gaap_type", gaap)
    cf_items = {}
    if cf_month:
        rev = _latest_revision_cf(conn, tid, year, cf_month, gaap)
        rows = conn.execute(
            """SELECT item_code, cumulative_amount
               FROM fs_cash_flow_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=?""",
            (tid, year, cf_month, gaap, rev),
        ).fetchall()
        cf_items = {r["item_code"]: r["cumulative_amount"] for r in rows}

    # 资产负债表（上年，用于增长计算）
    bs_prev_month = _find_latest_month(conn, "fs_balance_sheet_item", tid, year - 1, "gaap_type", bs_gaap)
    bs_prev_assets = None
    if bs_prev_month:
        rev = _latest_revision_bs(conn, tid, year - 1, bs_prev_month, bs_gaap)
        row = conn.execute(
            """SELECT ending_balance FROM fs_balance_sheet_item
               WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND revision_no=? AND item_code='ASSETS'""",
            (tid, year - 1, bs_prev_month, bs_gaap, rev),
        ).fetchone()
        bs_prev_assets = row["ending_balance"] if row else None

    return {
        'bs_items': bs_items, 'bs_month': bs_month,
        'is_items': is_items, 'is_month': is_month,
        'is_prev_items': is_prev_items,
        'cf_items': cf_items, 'cf_month': cf_month,
        'bs_prev_assets': bs_prev_assets,
    }


def _build_asset_structure_from_prefetch(prefetch, year):
    """从预取数据构建资产结构"""
    data = prefetch['bs_items']
    month = prefetch['bs_month']
    if not data or not month:
        return None

    total_assets = (data.get("ASSETS") or {}).get("end")
    current_assets = (data.get("CURRENT_ASSETS") or {}).get("end")
    fixed_assets = (data.get("FIXED_ASSETS") or {}).get("end")
    intangible = (data.get("INTANGIBLE_ASSETS") or {}).get("end")
    total_liabilities = (data.get("LIABILITIES") or {}).get("end")
    total_equity = (data.get("EQUITY") or {}).get("end")

    other_assets = None
    if total_assets is not None and current_assets is not None:
        non_current = (data.get("NON_CURRENT_ASSETS") or {}).get("end") or 0
        known = (fixed_assets or 0) + (intangible or 0)
        other_assets = max(0, non_current - known)

    debt_ratio = _safe_div(total_liabilities, total_assets)

    return {
        "period": f"{year}-{month:02d}",
        "total_assets": total_assets,
        "current_assets": current_assets,
        "fixed_assets": fixed_assets,
        "intangible_assets": intangible,
        "other_non_current": other_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "debt_ratio": debt_ratio,
        "debt_ratio_eval": evaluate_metric("debt_ratio", debt_ratio),
        "begin_total_assets": (data.get("ASSETS") or {}).get("begin"),
    }


def _build_profit_data_from_prefetch(prefetch, year):
    """从预取数据构建利润表数据"""
    data = prefetch['is_items']
    month = prefetch['is_month']
    if not data or not month:
        return None

    revenue = (data.get("operating_revenue") or {}).get("cumulative")
    cost = (data.get("operating_cost") or {}).get("cumulative")
    net_profit = (data.get("net_profit") or {}).get("cumulative")
    selling = (data.get("selling_expense") or {}).get("cumulative")
    admin = (data.get("administrative_expense") or {}).get("cumulative")
    rd = (data.get("rd_expense") or {}).get("cumulative")
    financial = (data.get("financial_expense") or {}).get("cumulative")

    gross_margin = _safe_div((revenue or 0) - (cost or 0), revenue) if revenue else None
    net_margin = _safe_div(net_profit, revenue)

    return {
        "period": f"{year}-{month:02d}",
        "revenue": revenue, "cost": cost, "net_profit": net_profit,
        "selling_expense": selling, "admin_expense": admin,
        "rd_expense": rd, "financial_expense": financial,
        "gross_margin": gross_margin,
        "gross_margin_eval": evaluate_metric("gross_margin", gross_margin),
        "net_margin": net_margin,
        "net_margin_eval": evaluate_metric("net_margin", net_margin),
        "selling_expense_rate": _safe_div(selling, revenue),
        "admin_expense_rate": _safe_div(admin, revenue),
    }


def _build_cash_flow_from_prefetch(prefetch, year):
    """从预取数据构建现金流量表数据"""
    data = prefetch['cf_items']
    month = prefetch['cf_month']
    if not data or not month:
        return None

    operating = data.get("operating_net_cash")
    investing = data.get("investing_net_cash")
    financing = data.get("financing_net_cash")

    op_eval = None
    if operating is not None:
        op_eval = {"level": "充足", "type": "positive"} if operating > 0 else {"level": "不足", "type": "negative"}

    return {
        "period": f"{year}-{month:02d}",
        "operating": operating, "operating_eval": op_eval,
        "investing": investing, "financing": financing,
    }


def _build_growth_from_prefetch(prefetch, year):
    """从预取数据构建增长指标"""
    is_items = prefetch['is_items']
    is_prev = prefetch['is_prev_items']
    bs_items = prefetch['bs_items']
    bs_prev_assets = prefetch['bs_prev_assets']

    rev_cur = (is_items.get("operating_revenue") or {}).get("cumulative")
    np_cur = (is_items.get("net_profit") or {}).get("cumulative")
    rev_prev = is_prev.get("operating_revenue")
    np_prev = is_prev.get("net_profit")
    assets_cur = (bs_items.get("ASSETS") or {}).get("end")

    return {
        "revenue_growth": evaluate_growth(rev_cur, rev_prev),
        "net_profit_growth": evaluate_growth(np_cur, np_prev),
        "asset_growth": evaluate_growth(assets_cur, bs_prev_assets),
    }


def _build_rd_from_prefetch(prefetch, year):
    """从预取数据构建研发创新数据"""
    data = prefetch['is_items']
    if not data:
        return None
    rd = (data.get("rd_expense") or {}).get("cumulative")
    revenue = (data.get("operating_revenue") or {}).get("cumulative")
    intensity = _safe_div(rd, revenue)
    intensity_eval = None
    if intensity is not None:
        if intensity >= 6:
            intensity_eval = {"level": "高", "type": "positive"}
        elif intensity >= 3:
            intensity_eval = {"level": "中", "type": "neutral"}
        else:
            intensity_eval = {"level": "低", "type": "warning"}
    return {"rd_expense": rd, "rd_intensity": intensity, "rd_intensity_eval": intensity_eval}


def get_company_profile(taxpayer_id: str, year: int) -> dict:
    """聚合企业画像全部数据（带 TTL 缓存）"""
    # 检查缓存
    cache_key = (taxpayer_id, year)
    cached = _profile_cache.get(cache_key)
    if cached and (time.time() - cached['ts']) < _PROFILE_CACHE_TTL:
        return cached['data']

    from modules.db_utils import get_connection
    conn = get_connection()
    try:
        basic = _query_basic_info(conn, taxpayer_id)
        if not basic:
            return {"error": f"纳税人 {taxpayer_id} 不存在"}

        gaap, _ = _get_gaap(conn, taxpayer_id)
        bs_gaap = "ASBE" if gaap == "CAS" else "ASSE"

        # 批量预取 EAV 数据（减少 ~30 次重复查询）
        prefetch = _prefetch_eav_data(conn, taxpayer_id, year, gaap, bs_gaap)

        result = {
            "basic_info": basic,
            "asset_structure": _build_asset_structure_from_prefetch(prefetch, year),
            "profit_data": _build_profit_data_from_prefetch(prefetch, year),
            "cash_flow": _build_cash_flow_from_prefetch(prefetch, year),
            "growth_metrics": _build_growth_from_prefetch(prefetch, year),
            "financial_metrics": _query_financial_metrics(conn, taxpayer_id, year),
            "tax_summary": _query_tax_summary(conn, taxpayer_id, year),
            "invoice_summary": _query_invoice_summary(conn, taxpayer_id, year),
            "rd_innovation": _build_rd_from_prefetch(prefetch, year),
            "cross_border": _query_cross_border(conn, taxpayer_id, year),
            "compliance_risk": _query_compliance_risk(conn, taxpayer_id, year),
            "shareholders": _query_shareholders(conn, taxpayer_id, year),
            "employee_structure": _query_employee_structure(conn, taxpayer_id),
            "external_relations": None,
            "digitalization": None,
            "esg": None,
            "policy_matching": None,
            "special_business": None,
        }

        # 写入缓存
        _profile_cache[cache_key] = {'data': result, 'ts': time.time()}
        return result
    finally:
        conn.close()
