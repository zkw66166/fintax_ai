"""Comprehensive data quality check engine for all financial domains.

Supports 5 check categories across 10+ domains with dual GAAP standards,
dual taxpayer types, and dual EIT periods.
"""
import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from config.settings import DB_PATH


# --- Data classes (immutable) ---

@dataclass(frozen=True)
class CheckResult:
    rule_id: str
    rule_name_cn: str
    category: str  # internal_consistency | reasonableness | cross_table | period_continuity | completeness
    severity: str  # error | warning
    status: str    # pass | fail | warn | skip
    message: str = ""
    expected: Optional[float] = None
    actual: Optional[float] = None
    difference: Optional[float] = None
    period: str = ""


@dataclass(frozen=True)
class DomainCheckResult:
    domain: str
    domain_name_cn: str
    gaap_type: Optional[str]
    total_checks: int
    passed: int
    failed: int
    warned: int
    skipped: int
    status: str
    details: tuple = ()  # tuple of CheckResult


# --- Constants: item code lists for detail-sum rules ---

ASBE_CURRENT_ASSETS = [
    'CASH', 'TRADING_FINANCIAL_ASSETS', 'DERIVATIVE_FINANCIAL_ASSETS',
    'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE', 'ACCOUNTS_RECEIVABLE_FINANCING',
    'PREPAYMENTS', 'OTHER_RECEIVABLES', 'INVENTORY', 'CONTRACT_ASSETS',
    'HELD_FOR_SALE_ASSETS', 'CURRENT_PORTION_NON_CURRENT_ASSETS', 'OTHER_CURRENT_ASSETS',
]
ASBE_NON_CURRENT_ASSETS = [
    'DEBT_INVESTMENTS', 'OTHER_DEBT_INVESTMENTS', 'LONG_TERM_RECEIVABLES',
    'LONG_TERM_EQUITY_INVESTMENTS', 'OTHER_EQUITY_INSTRUMENTS_INVEST',
    'OTHER_NON_CURRENT_FINANCIAL_ASSETS', 'INVESTMENT_PROPERTY', 'FIXED_ASSETS',
    'CONSTRUCTION_IN_PROGRESS', 'PRODUCTIVE_BIOLOGICAL_ASSETS', 'OIL_AND_GAS_ASSETS',
    'RIGHT_OF_USE_ASSETS', 'INTANGIBLE_ASSETS', 'DEVELOPMENT_EXPENDITURE',
    'GOODWILL', 'LONG_TERM_DEFERRED_EXPENSES', 'DEFERRED_TAX_ASSETS',
    'OTHER_NON_CURRENT_ASSETS',
]
ASBE_CURRENT_LIABILITIES = [
    'SHORT_TERM_LOANS', 'TRADING_FINANCIAL_LIABILITIES', 'DERIVATIVE_FINANCIAL_LIABILITIES',
    'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE', 'ADVANCES_FROM_CUSTOMERS', 'CONTRACT_LIABILITIES',
    'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE', 'OTHER_PAYABLES',
    'HELD_FOR_SALE_LIABILITIES', 'CURRENT_PORTION_NON_CURRENT_LIABILITIES',
    'OTHER_CURRENT_LIABILITIES',
]
ASBE_NON_CURRENT_LIABILITIES = [
    'LONG_TERM_LOANS', 'BONDS_PAYABLE', 'LEASE_LIABILITIES', 'LONG_TERM_PAYABLES',
    'PROVISIONS', 'DEFERRED_INCOME', 'DEFERRED_TAX_LIABILITIES',
    'OTHER_NON_CURRENT_LIABILITIES',
]
ASBE_EQUITY_ITEMS = [
    'SHARE_CAPITAL', 'CAPITAL_RESERVE', 'OTHER_COMPREHENSIVE_INCOME',
    'SPECIAL_RESERVE', 'SURPLUS_RESERVE', 'RETAINED_EARNINGS',
]
ASBE_EQUITY_SUBTRACT = ['TREASURY_STOCK']

ASSE_CURRENT_ASSETS = [
    'CASH', 'SHORT_TERM_INVESTMENTS', 'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE',
    'PREPAYMENTS', 'DIVIDENDS_RECEIVABLE', 'INTEREST_RECEIVABLE', 'OTHER_RECEIVABLES',
    'INVENTORY', 'OTHER_CURRENT_ASSETS',
]
ASSE_NON_CURRENT_ASSETS = [
    'LONG_TERM_BOND_INVESTMENTS', 'LONG_TERM_EQUITY_INVESTMENTS', 'FIXED_ASSETS_NET',
    'CONSTRUCTION_IN_PROGRESS', 'ENGINEERING_MATERIALS', 'FIXED_ASSETS_LIQUIDATION',
    'PRODUCTIVE_BIOLOGICAL_ASSETS', 'INTANGIBLE_ASSETS', 'DEVELOPMENT_EXPENDITURE',
    'LONG_TERM_DEFERRED_EXPENSES', 'OTHER_NON_CURRENT_ASSETS',
]
ASSE_CURRENT_LIABILITIES = [
    'SHORT_TERM_LOANS', 'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE', 'ADVANCES_FROM_CUSTOMERS',
    'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE', 'INTEREST_PAYABLE', 'PROFIT_PAYABLE',
    'OTHER_PAYABLES', 'OTHER_CURRENT_LIABILITIES',
]
ASSE_NON_CURRENT_LIABILITIES = [
    'LONG_TERM_LOANS', 'LONG_TERM_PAYABLES', 'DEFERRED_INCOME',
    'OTHER_NON_CURRENT_LIABILITIES',
]
ASSE_EQUITY_ITEMS = ['SHARE_CAPITAL', 'CAPITAL_RESERVE', 'SURPLUS_RESERVE', 'RETAINED_EARNINGS']

# CAS income statement items for operating profit formula
CAS_OP_ADD = ['operating_revenue', 'other_gains', 'investment_income',
              'net_exposure_hedge_income', 'fair_value_change_income',
              'credit_impairment_loss', 'asset_impairment_loss', 'asset_disposal_gains']
CAS_OP_SUB = ['operating_cost', 'taxes_and_surcharges', 'selling_expense',
              'administrative_expense', 'rd_expense', 'financial_expense']

# SAS income statement items for operating profit formula
SAS_OP_ADD = ['operating_revenue', 'investment_income']
SAS_OP_SUB = ['operating_cost', 'taxes_and_surcharges', 'selling_expense',
              'administrative_expense', 'financial_expense']

# CAS cash flow item codes
CAS_OP_INFLOW = ['operating_inflow_sales', 'operating_inflow_tax_refund', 'operating_inflow_other']
CAS_OP_OUTFLOW = ['operating_outflow_purchase', 'operating_outflow_labor',
                  'operating_outflow_tax', 'operating_outflow_other']
CAS_INV_INFLOW = ['investing_inflow_sale_investment', 'investing_inflow_returns',
                  'investing_inflow_disposal_assets', 'investing_inflow_disposal_subsidiary',
                  'investing_inflow_other']
CAS_INV_OUTFLOW = ['investing_outflow_purchase_assets', 'investing_outflow_purchase_investment',
                   'investing_outflow_acquire_subsidiary', 'investing_outflow_other']
CAS_FIN_INFLOW = ['financing_inflow_capital', 'financing_inflow_borrowing', 'financing_inflow_other']
CAS_FIN_OUTFLOW = ['financing_outflow_debt_repayment', 'financing_outflow_dividend_interest',
                   'financing_outflow_other']

# SAS cash flow item codes
SAS_OP_INFLOW_CF = ['operating_receipts_sales', 'operating_receipts_other']
SAS_OP_OUTFLOW_CF = ['operating_payments_purchase', 'operating_payments_staff',
                     'operating_payments_tax', 'operating_payments_other']
SAS_INV_INFLOW_CF = ['investing_receipts_disposal_investment', 'investing_receipts_returns',
                     'investing_receipts_disposal_assets']
SAS_INV_OUTFLOW_CF = ['investing_payments_purchase_investment', 'investing_payments_purchase_assets']
SAS_FIN_INFLOW_CF = ['financing_receipts_borrowing', 'financing_receipts_capital']
SAS_FIN_OUTFLOW_CF = ['financing_payments_debt_principal', 'financing_payments_debt_interest',
                      'financing_payments_dividend']


# --- Helper ---

def _v(d: dict, key: str) -> float:
    """Get value from dict, default 0.0."""
    val = d.get(key)
    if val is None:
        return 0.0
    return float(val)


def _check(rule_id, name_cn, category, severity, expected, actual, tolerance, period=""):
    """Create a CheckResult from expected vs actual comparison."""
    diff = abs(expected - actual)
    if diff <= tolerance:
        return CheckResult(rule_id=rule_id, rule_name_cn=name_cn, category=category,
                           severity=severity, status="pass", period=period,
                           expected=expected, actual=actual, difference=diff)
    status = "warn" if severity == "warning" else "fail"
    msg = f"{name_cn}差异{diff:.2f}(容差{tolerance})"
    return CheckResult(rule_id=rule_id, rule_name_cn=name_cn, category=category,
                       severity=severity, status=status, message=msg, period=period,
                       expected=expected, actual=actual, difference=diff)


class DataQualityChecker:
    """Comprehensive data quality checker for all financial domains."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)

    def _conn(self):
        from modules.db_utils import get_connection
        return get_connection(self.db_path)

    def _get_eav_batch(self, conn, table, taxpayer_id, year, month,
                       item_codes, col="ending_balance", gaap_type=None):
        """Fetch multiple EAV values in one query. Returns {item_code: float}."""
        if not item_codes:
            return {}
        placeholders = ",".join("?" for _ in item_codes)
        gaap_clause = "AND gaap_type = ?" if gaap_type else ""
        params = [taxpayer_id, year, month] + ([] if not gaap_type else [gaap_type]) + list(item_codes)
        sql = (
            f"SELECT item_code, {col} FROM {table} "
            f"WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
            f"{gaap_clause} AND item_code IN ({placeholders}) "
            f"ORDER BY revision_no DESC"
        )
        rows = conn.execute(sql, params).fetchall()
        result = {}
        for r in rows:
            code = r["item_code"]
            if code not in result:  # first row = latest revision
                result[code] = float(r[col] or 0) if r[col] is not None else 0.0
        return result

    def _get_periods(self, conn, table, taxpayer_id, gaap_type=None):
        """Get distinct (year, month) periods for a taxpayer."""
        gaap_clause = "AND gaap_type = ?" if gaap_type else ""
        params = [taxpayer_id] + ([gaap_type] if gaap_type else [])
        rows = conn.execute(
            f"SELECT DISTINCT period_year, period_month FROM {table} "
            f"WHERE taxpayer_id = ? {gaap_clause} ORDER BY period_year, period_month",
            params
        ).fetchall()
        return [(r["period_year"], r["period_month"]) for r in rows]

    def _get_taxpayer_info(self, conn, taxpayer_id):
        """Get taxpayer info dict."""
        r = conn.execute(
            "SELECT taxpayer_name, taxpayer_type, accounting_standard FROM taxpayer_info WHERE taxpayer_id = ?",
            (taxpayer_id,)
        ).fetchone()
        if not r:
            return None
        return {"name": r["taxpayer_name"], "type": r["taxpayer_type"],
                "standard": r["accounting_standard"] or ""}

    def check_all(self, taxpayer_id, categories=None, domains=None):
        """Run all applicable checks. Returns dict suitable for JSON response."""
        conn = self._conn()
        try:
            info = self._get_taxpayer_info(conn, taxpayer_id)
            if not info:
                return {"error": f"Taxpayer {taxpayer_id} not found"}

            is_general = info["type"] == "一般纳税人"
            bs_gaap = "ASBE" if info["standard"] == "企业会计准则" else "ASSE"
            is_gaap = "CAS" if bs_gaap == "ASBE" else "SAS"

            all_results = []

            # Internal consistency
            if not categories or "internal_consistency" in categories:
                all_results.extend(self._check_account_balance(conn, taxpayer_id))
                if bs_gaap == "ASBE":
                    all_results.extend(self._check_balance_sheet_asbe(conn, taxpayer_id))
                else:
                    all_results.extend(self._check_balance_sheet_asse(conn, taxpayer_id))
                if is_gaap == "CAS":
                    all_results.extend(self._check_income_statement_cas(conn, taxpayer_id))
                    all_results.extend(self._check_cash_flow_cas(conn, taxpayer_id))
                else:
                    all_results.extend(self._check_income_statement_sas(conn, taxpayer_id))
                    all_results.extend(self._check_cash_flow_sas(conn, taxpayer_id))
                if is_general:
                    all_results.extend(self._check_vat_general(conn, taxpayer_id))
                else:
                    all_results.extend(self._check_vat_small(conn, taxpayer_id))
                all_results.extend(self._check_eit_annual(conn, taxpayer_id))
                all_results.extend(self._check_eit_quarter(conn, taxpayer_id))
                all_results.extend(self._check_invoice(conn, taxpayer_id))

            # Reasonableness
            if not categories or "reasonableness" in categories:
                all_results.extend(self._check_reasonableness(conn, taxpayer_id, bs_gaap, is_gaap, is_general))

            # Cross-table
            if not categories or "cross_table" in categories:
                all_results.extend(self._check_cross_table(conn, taxpayer_id, bs_gaap, is_gaap, is_general))

            # Period continuity
            if not categories or "period_continuity" in categories:
                all_results.extend(self._check_period_continuity(conn, taxpayer_id, bs_gaap, is_gaap, is_general))

            return self._build_response(taxpayer_id, info, bs_gaap, is_gaap, all_results)
        finally:
            conn.close()

    def _build_response(self, taxpayer_id, info, bs_gaap, is_gaap, results):
        """Aggregate CheckResults into structured response."""
        total = len(results)
        passed = sum(1 for r in results if r.status == "pass")
        failed = sum(1 for r in results if r.status == "fail")
        warned = sum(1 for r in results if r.status == "warn")

        by_category = {}
        for r in results:
            cat = r.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0, "failed": 0, "warned": 0}
            by_category[cat]["total"] += 1
            if r.status == "pass":
                by_category[cat]["passed"] += 1
            elif r.status == "fail":
                by_category[cat]["failed"] += 1
            elif r.status == "warn":
                by_category[cat]["warned"] += 1

        # Group by domain
        domain_map = {}
        for r in results:
            key = r.rule_id.split("-")[0] if "-" in r.rule_id else r.rule_id[:4]
            domain_key = self._rule_to_domain(r.rule_id)
            if domain_key not in domain_map:
                domain_map[domain_key] = {"details": [], "name_cn": self._domain_name(domain_key)}
            domain_map[domain_key]["details"].append(r)

        domains_list = []
        for dk, dv in domain_map.items():
            details = dv["details"]
            d_total = len(details)
            d_passed = sum(1 for r in details if r.status == "pass")
            d_failed = sum(1 for r in details if r.status == "fail")
            d_warned = sum(1 for r in details if r.status == "warn")
            d_status = "pass" if d_failed == 0 else "fail"
            domains_list.append({
                "domain": dk,
                "domain_name_cn": dv["name_cn"],
                "status": d_status,
                "total_checks": d_total,
                "passed": d_passed,
                "failed": d_failed,
                "warned": d_warned,
                "details": [
                    {
                        "rule_id": r.rule_id, "rule_name_cn": r.rule_name_cn,
                        "category": r.category, "severity": r.severity,
                        "status": r.status, "period": r.period,
                        "expected": r.expected, "actual": r.actual,
                        "difference": r.difference, "message": r.message,
                    }
                    for r in details if r.status != "pass"
                ],
            })

        return {
            "taxpayer_id": taxpayer_id,
            "taxpayer_name": info["name"],
            "taxpayer_type": info["type"],
            "gaap_type": f"{bs_gaap}/{is_gaap}",
            "summary": {
                "total_checks": total, "passed": passed, "failed": failed,
                "warned": warned, "pass_rate": round(passed / max(total, 1) * 100, 1),
                "by_category": by_category,
            },
            "domains": domains_list,
        }

    @staticmethod
    def _rule_to_domain(rule_id):
        prefix = rule_id.split("-")[0] if "-" in rule_id else ""
        mapping = {
            "SB": "account_balance", "BS": "balance_sheet", "IS": "income_statement",
            "CF": "cash_flow", "VAT": "vat_return", "EIT": "eit_return",
            "INV": "invoice", "REAS": "reasonableness", "CROSS": "cross_table",
            "CONT": "period_continuity", "COMP": "completeness",
        }
        return mapping.get(prefix, "other")

    @staticmethod
    def _domain_name(key):
        names = {
            "account_balance": "科目余额表", "balance_sheet": "资产负债表",
            "income_statement": "利润表", "cash_flow": "现金流量表",
            "vat_return": "增值税申报表", "eit_return": "企业所得税申报表",
            "invoice": "发票", "reasonableness": "合理性检查",
            "cross_table": "跨表校验", "period_continuity": "期间连续性",
            "completeness": "完整性检查",
        }
        return names.get(key, key)

    # ── Category 2: Internal Consistency ──

    def _check_account_balance(self, conn, tid):
        """SB-01/01b: opening +/- debit -/+ credit = closing."""
        results = []
        periods = self._get_periods(conn, "account_balance", tid)
        for y, m in periods:
            rows = conn.execute(
                "SELECT a.account_code, m.account_name, m.balance_direction, "
                "a.opening_balance, a.debit_amount, a.credit_amount, a.closing_balance "
                "FROM account_balance a LEFT JOIN account_master m ON a.account_code = m.account_code "
                "WHERE a.taxpayer_id = ? AND a.period_year = ? AND a.period_month = ? "
                "ORDER BY a.revision_no DESC", (tid, y, m)
            ).fetchall()
            seen = set()
            for r in rows:
                code = r["account_code"]
                if code in seen:
                    continue
                seen.add(code)
                ob = float(r["opening_balance"] or 0)
                db = float(r["debit_amount"] or 0)
                cr = float(r["credit_amount"] or 0)
                cb = float(r["closing_balance"] or 0)
                direction = r["balance_direction"] or "借"
                if direction == "借":
                    expected = ob + db - cr
                    rid = "SB-01"
                else:
                    expected = ob - db + cr
                    rid = "SB-01b"
                diff = abs(expected - cb)
                if diff > 0.01:
                    name = r["account_name"] or code
                    results.append(CheckResult(
                        rule_id=rid, rule_name_cn=f"科目余额等式({name})",
                        category="internal_consistency", severity="error",
                        status="fail", period=f"{y}-{str(m).zfill(2)}",
                        expected=expected, actual=cb, difference=diff,
                        message=f"{name}余额差异{diff:.2f}"
                    ))
            if not any(r.period == f"{y}-{str(m).zfill(2)}" for r in results):
                results.append(CheckResult(
                    rule_id="SB-01", rule_name_cn="科目余额等式",
                    category="internal_consistency", severity="error",
                    status="pass", period=f"{y}-{str(m).zfill(2)}"
                ))
        return results

    def _check_bs_common(self, conn, tid, gaap, prefix,
                         ca_items, nca_items, cl_items, ncl_items,
                         eq_items, eq_sub=None):
        """Common balance sheet checks for both ASBE and ASSE."""
        results = []
        periods = self._get_periods(conn, "fs_balance_sheet_item", tid, gaap)
        totals = ['ASSETS', 'LIABILITIES', 'EQUITY', 'LIABILITIES_AND_EQUITY',
                  'CURRENT_ASSETS', 'NON_CURRENT_ASSETS', 'CURRENT_LIABILITIES',
                  'NON_CURRENT_LIABILITIES']
        all_codes = list(set(totals + ca_items + nca_items + cl_items + ncl_items + eq_items + (eq_sub or [])))

        for y, m in periods:
            per = f"{y}-{str(m).zfill(2)}"
            for col, suffix in [("ending_balance", ""), ("beginning_balance", "b")]:
                d = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y, m, all_codes, col, gaap)
                # BS-x01: ASSETS = LIABILITIES + EQUITY
                rid = f"{prefix}01{suffix}"
                results.append(_check(rid, f"会计等式({'期初' if suffix else '期末'})",
                    "internal_consistency", "error",
                    _v(d, 'LIABILITIES') + _v(d, 'EQUITY'), _v(d, 'ASSETS'), 1.0, per))
                if not suffix:  # only check these for ending_balance
                    # BS-x02: ASSETS = LIABILITIES_AND_EQUITY
                    results.append(_check(f"{prefix}02", "资产=负债+权益总计",
                        "internal_consistency", "error",
                        _v(d, 'ASSETS'), _v(d, 'LIABILITIES_AND_EQUITY'), 0.01, per))
                    # BS-x03: ASSETS = CURRENT + NON_CURRENT
                    results.append(_check(f"{prefix}03", "资产结构",
                        "internal_consistency", "error",
                        _v(d, 'ASSETS'), _v(d, 'CURRENT_ASSETS') + _v(d, 'NON_CURRENT_ASSETS'), 1.0, per))
                    # BS-x04: LIABILITIES = CURRENT + NON_CURRENT
                    results.append(_check(f"{prefix}04", "负债结构",
                        "internal_consistency", "error",
                        _v(d, 'LIABILITIES'), _v(d, 'CURRENT_LIABILITIES') + _v(d, 'NON_CURRENT_LIABILITIES'), 1.0, per))
                    # BS-x05: Current assets detail
                    ca_sum = sum(_v(d, c) for c in ca_items)
                    results.append(_check(f"{prefix}05", "流动资产明细",
                        "internal_consistency", "error", _v(d, 'CURRENT_ASSETS'), ca_sum, 1000, per))
                    # BS-x06: Non-current assets detail
                    nca_sum = sum(_v(d, c) for c in nca_items)
                    results.append(_check(f"{prefix}06", "非流动资产明细",
                        "internal_consistency", "error", _v(d, 'NON_CURRENT_ASSETS'), nca_sum, 1000, per))
                    # BS-x07: Current liabilities detail
                    cl_sum = sum(_v(d, c) for c in cl_items)
                    results.append(_check(f"{prefix}07", "流动负债明细",
                        "internal_consistency", "error", _v(d, 'CURRENT_LIABILITIES'), cl_sum, 1000, per))
                    # BS-x08: Non-current liabilities detail
                    ncl_sum = sum(_v(d, c) for c in ncl_items)
                    results.append(_check(f"{prefix}08", "非流动负债明细",
                        "internal_consistency", "error", _v(d, 'NON_CURRENT_LIABILITIES'), ncl_sum, 1000, per))
                    # BS-x09: Equity detail
                    eq_sum = sum(_v(d, c) for c in eq_items) - sum(_v(d, c) for c in (eq_sub or []))
                    results.append(_check(f"{prefix}09", "权益明细",
                        "internal_consistency", "error", _v(d, 'EQUITY'), eq_sum, 1000, per))
        return results

    def _check_balance_sheet_asbe(self, conn, tid):
        return self._check_bs_common(conn, tid, "ASBE", "BS-A",
            ASBE_CURRENT_ASSETS, ASBE_NON_CURRENT_ASSETS,
            ASBE_CURRENT_LIABILITIES, ASBE_NON_CURRENT_LIABILITIES,
            ASBE_EQUITY_ITEMS, ASBE_EQUITY_SUBTRACT)

    def _check_balance_sheet_asse(self, conn, tid):
        results = self._check_bs_common(conn, tid, "ASSE", "BS-S",
            ASSE_CURRENT_ASSETS, ASSE_NON_CURRENT_ASSETS,
            ASSE_CURRENT_LIABILITIES, ASSE_NON_CURRENT_LIABILITIES,
            ASSE_EQUITY_ITEMS)
        # BS-S10: FIXED_ASSETS_NET = FIXED_ASSETS_ORIGINAL - ACCUMULATED_DEPRECIATION
        periods = self._get_periods(conn, "fs_balance_sheet_item", tid, "ASSE")
        codes = ['FIXED_ASSETS_ORIGINAL', 'ACCUMULATED_DEPRECIATION', 'FIXED_ASSETS_NET']
        for y, m in periods:
            d = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y, m, codes, "ending_balance", "ASSE")
            orig = _v(d, 'FIXED_ASSETS_ORIGINAL')
            dep = _v(d, 'ACCUMULATED_DEPRECIATION')
            net = _v(d, 'FIXED_ASSETS_NET')
            if orig == 0 and dep == 0 and net != 0:
                # ASSE data may only have net value without split items, skip check
                continue
            expected = orig - dep
            results.append(_check("BS-S10", "固定资产净值", "internal_consistency", "error",
                                  expected, _v(d, 'FIXED_ASSETS_NET'), 0.01, f"{y}-{str(m).zfill(2)}"))
        return results

    def _check_is_common(self, conn, tid, gaap, prefix, add_items, sub_items):
        """Common income statement checks."""
        results = []
        periods = self._get_periods(conn, "fs_income_statement_item", tid, gaap)
        key_codes = list(set(add_items + sub_items + [
            'operating_profit', 'non_operating_income', 'non_operating_expense',
            'total_profit', 'income_tax_expense', 'net_profit',
            'other_comprehensive_income_net', 'comprehensive_income_total',
        ]))
        for y, m in periods:
            per = f"{y}-{str(m).zfill(2)}"
            for col in ["current_amount", "cumulative_amount"]:
                d = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, m, key_codes, col, gaap)
                tag = "本期" if col == "current_amount" else "累计"
                # IS-x01: Operating profit
                expected_op = sum(_v(d, c) for c in add_items) - sum(_v(d, c) for c in sub_items)
                results.append(_check(f"{prefix}01", f"营业利润({tag})",
                    "internal_consistency", "error", expected_op, _v(d, 'operating_profit'), 1.0, per))
                # IS-x02: Total profit
                expected_tp = _v(d, 'operating_profit') + _v(d, 'non_operating_income') - _v(d, 'non_operating_expense')
                results.append(_check(f"{prefix}02", f"利润总额({tag})",
                    "internal_consistency", "error", expected_tp, _v(d, 'total_profit'), 1.0, per))
                # IS-x03: Net profit
                expected_np = _v(d, 'total_profit') - _v(d, 'income_tax_expense')
                results.append(_check(f"{prefix}03", f"净利润({tag})",
                    "internal_consistency", "error", expected_np, _v(d, 'net_profit'), 1.0, per))
                # IS-C04: Comprehensive income (CAS only)
                if gaap == "CAS" and col == "current_amount":
                    expected_ci = _v(d, 'net_profit') + _v(d, 'other_comprehensive_income_net')
                    results.append(_check(f"{prefix}04", "综合收益",
                        "internal_consistency", "error", expected_ci,
                        _v(d, 'comprehensive_income_total'), 1.0, per))
        return results

    def _check_income_statement_cas(self, conn, tid):
        return self._check_is_common(conn, tid, "CAS", "IS-C", CAS_OP_ADD, CAS_OP_SUB)

    def _check_income_statement_sas(self, conn, tid):
        return self._check_is_common(conn, tid, "SAS", "IS-S", SAS_OP_ADD, SAS_OP_SUB)

    def _check_cf_common(self, conn, tid, gaap, prefix,
                         op_in, op_out, inv_in, inv_out, fin_in, fin_out,
                         has_subtotals=True, has_fx=True):
        """Common cash flow checks."""
        results = []
        periods = self._get_periods(conn, "fs_cash_flow_item", tid, gaap)
        all_codes = list(set(
            op_in + op_out + inv_in + inv_out + fin_in + fin_out +
            (['operating_inflow_subtotal', 'operating_outflow_subtotal',
              'investing_inflow_subtotal', 'investing_outflow_subtotal',
              'financing_inflow_subtotal', 'financing_outflow_subtotal'] if has_subtotals else []) +
            ['operating_net_cash', 'investing_net_cash', 'financing_net_cash',
             'net_increase_cash', 'beginning_cash', 'ending_cash'] +
            (['fx_impact'] if has_fx else [])
        ))
        for y, m in periods:
            per = f"{y}-{str(m).zfill(2)}"
            d = self._get_eav_batch(conn, "fs_cash_flow_item", tid, y, m, all_codes, "current_amount", gaap)

            if has_subtotals:
                # CF-x01~02: subtotals
                op_in_sum = sum(_v(d, c) for c in op_in)
                results.append(_check(f"{prefix}01", "经营流入小计", "internal_consistency", "error",
                    op_in_sum, _v(d, 'operating_inflow_subtotal'), 0.01, per))
                op_out_sum = sum(_v(d, c) for c in op_out)
                results.append(_check(f"{prefix}02", "经营流出小计", "internal_consistency", "error",
                    op_out_sum, _v(d, 'operating_outflow_subtotal'), 0.01, per))
                # CF-x03: operating net
                results.append(_check(f"{prefix}03", "经营净额", "internal_consistency", "error",
                    _v(d, 'operating_inflow_subtotal') - _v(d, 'operating_outflow_subtotal'),
                    _v(d, 'operating_net_cash'), 0.01, per))
                # CF-x04~05: investing subtotals
                inv_in_sum = sum(_v(d, c) for c in inv_in)
                results.append(_check(f"{prefix}04", "投资流入小计", "internal_consistency", "error",
                    inv_in_sum, _v(d, 'investing_inflow_subtotal'), 0.01, per))
                inv_out_sum = sum(_v(d, c) for c in inv_out)
                results.append(_check(f"{prefix}05", "投资流出小计", "internal_consistency", "error",
                    inv_out_sum, _v(d, 'investing_outflow_subtotal'), 0.01, per))
                # CF-x06: investing net
                results.append(_check(f"{prefix}06", "投资净额", "internal_consistency", "error",
                    _v(d, 'investing_inflow_subtotal') - _v(d, 'investing_outflow_subtotal'),
                    _v(d, 'investing_net_cash'), 0.01, per))
                # CF-x07~08: financing subtotals
                fin_in_sum = sum(_v(d, c) for c in fin_in)
                results.append(_check(f"{prefix}07", "筹资流入小计", "internal_consistency", "error",
                    fin_in_sum, _v(d, 'financing_inflow_subtotal'), 0.01, per))
                fin_out_sum = sum(_v(d, c) for c in fin_out)
                results.append(_check(f"{prefix}08", "筹资流出小计", "internal_consistency", "error",
                    fin_out_sum, _v(d, 'financing_outflow_subtotal'), 0.01, per))
                # CF-x09: financing net
                results.append(_check(f"{prefix}09", "筹资净额", "internal_consistency", "error",
                    _v(d, 'financing_inflow_subtotal') - _v(d, 'financing_outflow_subtotal'),
                    _v(d, 'financing_net_cash'), 0.01, per))
                # CF-x10: net increase
                fx = _v(d, 'fx_impact') if has_fx else 0.0
                expected_net = _v(d, 'operating_net_cash') + _v(d, 'investing_net_cash') + _v(d, 'financing_net_cash') + fx
                results.append(_check(f"{prefix}10", "现金净增加额", "internal_consistency", "error",
                    expected_net, _v(d, 'net_increase_cash'), 1.0, per))
                # CF-x11: ending cash
                results.append(_check(f"{prefix}11", "期末现金", "internal_consistency", "error",
                    _v(d, 'beginning_cash') + _v(d, 'net_increase_cash'), _v(d, 'ending_cash'), 0.01, per))
            else:
                # SAS: no subtotals, compute directly
                op_net = sum(_v(d, c) for c in op_in) - sum(_v(d, c) for c in op_out)
                results.append(_check(f"{prefix}01", "经营净额", "internal_consistency", "error",
                    op_net, _v(d, 'operating_net_cash'), 0.01, per))
                inv_net = sum(_v(d, c) for c in inv_in) - sum(_v(d, c) for c in inv_out)
                results.append(_check(f"{prefix}02", "投资净额", "internal_consistency", "error",
                    inv_net, _v(d, 'investing_net_cash'), 0.01, per))
                fin_net = sum(_v(d, c) for c in fin_in) - sum(_v(d, c) for c in fin_out)
                results.append(_check(f"{prefix}03", "筹资净额", "internal_consistency", "error",
                    fin_net, _v(d, 'financing_net_cash'), 0.01, per))
                expected_net = _v(d, 'operating_net_cash') + _v(d, 'investing_net_cash') + _v(d, 'financing_net_cash')
                results.append(_check(f"{prefix}04", "现金净增加额", "internal_consistency", "error",
                    expected_net, _v(d, 'net_increase_cash'), 1.0, per))
                results.append(_check(f"{prefix}05", "期末现金", "internal_consistency", "error",
                    _v(d, 'beginning_cash') + _v(d, 'net_increase_cash'), _v(d, 'ending_cash'), 0.01, per))
        return results

    def _check_cash_flow_cas(self, conn, tid):
        return self._check_cf_common(conn, tid, "CAS", "CF-C",
            CAS_OP_INFLOW, CAS_OP_OUTFLOW, CAS_INV_INFLOW, CAS_INV_OUTFLOW,
            CAS_FIN_INFLOW, CAS_FIN_OUTFLOW, has_subtotals=True, has_fx=True)

    def _check_cash_flow_sas(self, conn, tid):
        return self._check_cf_common(conn, tid, "SAS", "CF-S",
            SAS_OP_INFLOW_CF, SAS_OP_OUTFLOW_CF, SAS_INV_INFLOW_CF, SAS_INV_OUTFLOW_CF,
            SAS_FIN_INFLOW_CF, SAS_FIN_OUTFLOW_CF, has_subtotals=False, has_fx=False)

    # ── VAT checks ──

    def _get_vat_rows(self, conn, table, tid):
        """Get VAT rows grouped by (year, month). Returns {(y,m): [rows]}."""
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE taxpayer_id = ? ORDER BY period_year, period_month, revision_no DESC",
            (tid,)
        ).fetchall()
        periods = {}
        seen = set()
        for r in rows:
            key = (r["period_year"], r["period_month"], r["item_type"], r["time_range"])
            if key in seen:
                continue
            seen.add(key)
            pk = (r["period_year"], r["period_month"])
            periods.setdefault(pk, []).append(dict(r))
        return periods

    def _check_vat_general(self, conn, tid):
        """VAT-G01~G05: 一般纳税人增值税表内勾稽."""
        results = []
        period_rows = self._get_vat_rows(conn, "vat_return_general", tid)
        for (y, m), rows in period_rows.items():
            per = f"{y}-{str(m).zfill(2)}"
            cur = [r for r in rows if r["item_type"] == "一般项目" and r["time_range"] == "本月"]
            if not cur:
                continue
            d = cur[0]
            # VAT-G01: 应抵扣税额合计
            expected = _v(d, 'input_tax') + _v(d, 'last_period_credit') - _v(d, 'transfer_out') - _v(d, 'export_refund') + _v(d, 'tax_check_supplement')
            results.append(_check("VAT-G01", "应抵扣税额合计", "internal_consistency", "error",
                expected, _v(d, 'deductible_total'), 1.0, per))
            # VAT-G02: 应纳税额
            results.append(_check("VAT-G02", "应纳税额", "internal_consistency", "error",
                _v(d, 'output_tax') - _v(d, 'actual_deduct'), _v(d, 'tax_payable'), 1.0, per))
            # VAT-G03: 期末留抵
            results.append(_check("VAT-G03", "期末留抵", "internal_consistency", "error",
                _v(d, 'deductible_total') - _v(d, 'actual_deduct'), _v(d, 'end_credit'), 1.0, per))
            # VAT-G04: 应纳税额合计
            expected_total = _v(d, 'tax_payable') + _v(d, 'simple_tax') + _v(d, 'simple_tax_check_supplement') - _v(d, 'tax_reduction')
            results.append(_check("VAT-G04", "应纳税额合计", "internal_consistency", "error",
                expected_total, _v(d, 'total_tax_payable'), 1.0, per))
            # VAT-G05: 期末未缴
            expected_unpaid = _v(d, 'unpaid_begin') + _v(d, 'total_tax_payable') - _v(d, 'paid_current')
            results.append(_check("VAT-G05", "期末未缴", "internal_consistency", "error",
                expected_unpaid, _v(d, 'unpaid_end'), 1000, per))
        return results

    def _check_vat_small(self, conn, tid):
        """VAT-S01~S02: 小规模纳税人增值税表内勾稽."""
        results = []
        period_rows = self._get_vat_rows(conn, "vat_return_small", tid)
        for (y, m), rows in period_rows.items():
            per = f"{y}-{str(m).zfill(2)}"
            cur = [r for r in rows if r["item_type"] == "货物及劳务" and r["time_range"] == "本期"]
            if not cur:
                continue
            d = cur[0]
            # VAT-S01: 应纳税额合计
            results.append(_check("VAT-S01", "应纳税额合计", "internal_consistency", "error",
                _v(d, 'tax_due_current') - _v(d, 'tax_due_reduction') - _v(d, 'tax_free_amount'),
                _v(d, 'tax_due_total'), 1.0, per))
            # VAT-S02: 应补退税额
            results.append(_check("VAT-S02", "应补退税额", "internal_consistency", "error",
                _v(d, 'tax_due_total') - _v(d, 'tax_prepaid'),
                _v(d, 'tax_supplement_refund'), 1.0, per))
        return results

    # ── EIT checks ──

    def _get_eit_annual(self, conn, tid):
        """Get EIT annual main rows. Returns [(year, row_dict)]."""
        rows = conn.execute(
            "SELECT f.period_year, m.* FROM eit_annual_filing f "
            "JOIN eit_annual_main m ON f.filing_id = m.filing_id "
            "WHERE f.taxpayer_id = ? ORDER BY f.period_year, f.revision_no DESC",
            (tid,)
        ).fetchall()
        seen = set()
        result = []
        for r in rows:
            y = r["period_year"]
            if y in seen:
                continue
            seen.add(y)
            result.append((y, dict(r)))
        return result

    def _get_eit_quarter(self, conn, tid):
        """Get EIT quarter main rows. Returns [(year, quarter, row_dict)]."""
        rows = conn.execute(
            "SELECT f.period_year, f.period_quarter, m.* FROM eit_quarter_filing f "
            "JOIN eit_quarter_main m ON f.filing_id = m.filing_id "
            "WHERE f.taxpayer_id = ? ORDER BY f.period_year, f.period_quarter, f.revision_no DESC",
            (tid,)
        ).fetchall()
        seen = set()
        result = []
        for r in rows:
            key = (r["period_year"], r["period_quarter"])
            if key in seen:
                continue
            seen.add(key)
            result.append((r["period_year"], r["period_quarter"], dict(r)))
        return result

    def _check_eit_annual(self, conn, tid):
        """EIT-A01~A05: 企业所得税年报表内勾稽."""
        results = []
        for y, d in self._get_eit_annual(conn, tid):
            per = f"{y}-年报"
            # EIT-A01: 营业利润
            op_add = sum(_v(d, c) for c in ['revenue', 'other_gains', 'investment_income',
                'net_exposure_hedge_gains', 'fair_value_change_gains',
                'credit_impairment_loss', 'asset_impairment_loss', 'asset_disposal_gains'])
            op_sub = sum(_v(d, c) for c in ['cost', 'taxes_surcharges', 'selling_expenses',
                'admin_expenses', 'rd_expenses', 'financial_expenses'])
            results.append(_check("EIT-A01", "营业利润", "internal_consistency", "error",
                op_add - op_sub, _v(d, 'operating_profit'), 1.0, per))
            # EIT-A02: 利润总额
            results.append(_check("EIT-A02", "利润总额", "internal_consistency", "error",
                _v(d, 'operating_profit') + _v(d, 'non_operating_income') - _v(d, 'non_operating_expenses'),
                _v(d, 'total_profit'), 1.0, per))
            # EIT-A03: 应纳税额
            results.append(_check("EIT-A03", "应纳税额", "internal_consistency", "error",
                _v(d, 'taxable_income') * _v(d, 'tax_rate'), _v(d, 'tax_payable'), 1.0, per))
            # EIT-A04: 实际应纳税额
            results.append(_check("EIT-A04", "实际应纳税额", "internal_consistency", "error",
                _v(d, 'tax_payable') - _v(d, 'tax_credit_total'), _v(d, 'actual_tax_payable'), 1.0, per))
            # EIT-A05: 应补退税额
            results.append(_check("EIT-A05", "应补退税额", "internal_consistency", "error",
                _v(d, 'actual_tax_payable') - _v(d, 'less_prepaid_tax'),
                _v(d, 'tax_payable_or_refund'), 1.0, per))
        return results

    def _check_eit_quarter(self, conn, tid):
        """EIT-Q01~Q03: 企业所得税季报表内勾稽."""
        results = []
        for y, q, d in self._get_eit_quarter(conn, tid):
            per = f"{y}-Q{q}"
            # EIT-Q01: 利润总额 = 收入 - 成本
            results.append(_check("EIT-Q01", "利润总额", "internal_consistency", "error",
                _v(d, 'revenue') - _v(d, 'cost'), _v(d, 'total_profit'), 1.0, per))
            # EIT-Q02: 应纳税额
            results.append(_check("EIT-Q02", "应纳税额", "internal_consistency", "error",
                _v(d, 'actual_profit') * _v(d, 'tax_rate'), _v(d, 'tax_payable'), 1.0, per))
            # EIT-Q03: 本期应补退
            results.append(_check("EIT-Q03", "本期应补退", "internal_consistency", "error",
                _v(d, 'tax_payable') - _v(d, 'tax_credit_total') - _v(d, 'less_prepaid_tax_current_year') - _v(d, 'less_specific_business_prepaid'),
                _v(d, 'current_tax_payable_or_refund'), 1.0, per))
        return results

    # ── Invoice checks ──

    def _check_invoice(self, conn, tid):
        """INV-01~02: 发票价税合计/金额校验."""
        results = []
        for table, label in [("inv_spec_purchase", "进项"), ("inv_spec_sales", "销项")]:
            rows = conn.execute(
                f"SELECT invoice_pk, line_no, amount, tax_amount, total_amount, "
                f"{'quantity, unit_price,' if table == 'inv_spec_purchase' else ''} "
                f"period_year, period_month FROM {table} WHERE taxpayer_id = ?",
                (tid,)
            ).fetchall()
            for r in rows:
                per = f"{r['period_year']}-{str(r['period_month']).zfill(2)}"
                amt = float(r["amount"] or 0)
                tax = float(r["tax_amount"] or 0)
                total = float(r["total_amount"] or 0)
                # INV-01: 价税合计 = 金额 + 税额
                diff = abs((amt + tax) - total)
                if diff > 0.01:
                    results.append(CheckResult(
                        rule_id="INV-01", rule_name_cn=f"{label}发票价税合计",
                        category="internal_consistency", severity="error", status="fail",
                        period=per, expected=amt + tax, actual=total, difference=diff,
                        message=f"{label}发票{r['invoice_pk']}行{r['line_no']}价税合计差异{diff:.2f}"
                    ))
                # INV-02: 金额 = 数量 x 单价 (purchase only)
                if table == "inv_spec_purchase":
                    qty = float(r["quantity"] or 0) if r["quantity"] else 0
                    price = float(r["unit_price"] or 0) if r["unit_price"] else 0
                    if qty != 0 and price != 0:
                        expected_amt = qty * price
                        diff2 = abs(expected_amt - amt)
                        if diff2 > 1.0:
                            results.append(CheckResult(
                                rule_id="INV-02", rule_name_cn=f"{label}发票金额=数量x单价",
                                category="internal_consistency", severity="error", status="fail",
                                period=per, expected=expected_amt, actual=amt, difference=diff2,
                                message=f"{label}发票{r['invoice_pk']}行{r['line_no']}金额差异{diff2:.2f}"
                            ))
        # If no failures found, add a pass result
        if not results:
            results.append(CheckResult(rule_id="INV-01", rule_name_cn="发票价税合计",
                category="internal_consistency", severity="error", status="pass"))
        return results

    # ── Reasonableness checks ──

    def _check_reasonableness(self, conn, tid, bs_gaap, is_gaap, is_general):
        """REAS-01~11: 合理性检查."""
        results = []
        # BS checks
        bs_periods = self._get_periods(conn, "fs_balance_sheet_item", tid, bs_gaap)
        for y, m in bs_periods:
            per = f"{y}-{str(m).zfill(2)}"
            d = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y, m,
                ["ASSETS", "LIABILITIES", "CURRENT_ASSETS", "CURRENT_LIABILITIES"],
                "ending_balance", bs_gaap)
            assets = _v(d, "ASSETS")
            liabilities = _v(d, "LIABILITIES")
            # REAS-01: 资产总计非负
            if assets < 0:
                results.append(CheckResult(rule_id="REAS-01", rule_name_cn="资产总计非负",
                    category="reasonableness", severity="error", status="fail", period=per,
                    expected=0, actual=assets, difference=abs(assets),
                    message=f"资产总计为负数{assets:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-01", rule_name_cn="资产总计非负",
                    category="reasonableness", severity="error", status="pass", period=per))
            # REAS-02: 负债合计非负
            if liabilities < 0:
                results.append(CheckResult(rule_id="REAS-02", rule_name_cn="负债合计非负",
                    category="reasonableness", severity="error", status="fail", period=per,
                    expected=0, actual=liabilities, difference=abs(liabilities),
                    message=f"负债合计为负数{liabilities:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-02", rule_name_cn="负债合计非负",
                    category="reasonableness", severity="error", status="pass", period=per))
            # REAS-11: 资产负债率 0~1
            if assets > 0:
                ratio = liabilities / assets
                if ratio < 0 or ratio > 1:
                    results.append(CheckResult(rule_id="REAS-11", rule_name_cn="资产负债率0~1",
                        category="reasonableness", severity="warning", status="warn", period=per,
                        expected=0.5, actual=ratio, difference=0,
                        message=f"资产负债率{ratio:.2%}超出合理范围"))
                else:
                    results.append(CheckResult(rule_id="REAS-11", rule_name_cn="资产负债率0~1",
                        category="reasonableness", severity="warning", status="pass", period=per))

        # IS checks
        is_periods = self._get_periods(conn, "fs_income_statement_item", tid, is_gaap)
        for y, m in is_periods:
            per = f"{y}-{str(m).zfill(2)}"
            d = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, m,
                ["operating_revenue", "operating_cost", "income_tax_expense"],
                "current_amount", is_gaap)
            rev = _v(d, "operating_revenue")
            cost = _v(d, "operating_cost")
            tax_exp = _v(d, "income_tax_expense")
            # REAS-03: 营业收入非负
            if rev < 0:
                results.append(CheckResult(rule_id="REAS-03", rule_name_cn="营业收入非负",
                    category="reasonableness", severity="error", status="fail", period=per,
                    expected=0, actual=rev, difference=abs(rev),
                    message=f"营业收入为负数{rev:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-03", rule_name_cn="营业收入非负",
                    category="reasonableness", severity="error", status="pass", period=per))
            # REAS-04: 收入=0但成本>0
            if rev == 0 and cost > 0:
                results.append(CheckResult(rule_id="REAS-04", rule_name_cn="收入为零但成本大于零",
                    category="reasonableness", severity="warning", status="warn", period=per,
                    expected=0, actual=cost, difference=cost,
                    message=f"营业收入为0但营业成本为{cost:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-04", rule_name_cn="收入为零但成本大于零",
                    category="reasonableness", severity="warning", status="pass", period=per))
            # REAS-05: 所得税费用非负
            if tax_exp < 0:
                results.append(CheckResult(rule_id="REAS-05", rule_name_cn="所得税费用非负",
                    category="reasonableness", severity="error", status="fail", period=per,
                    expected=0, actual=tax_exp, difference=abs(tax_exp),
                    message=f"所得税费用为负数{tax_exp:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-05", rule_name_cn="所得税费用非负",
                    category="reasonableness", severity="error", status="pass", period=per))

        # VAT reasonableness
        if is_general:
            vat_rows = self._get_vat_rows(conn, "vat_return_general", tid)
            for (y, m_), rows in vat_rows.items():
                per = f"{y}-{str(m_).zfill(2)}"
                cur = [r for r in rows if r["item_type"] == "一般项目" and r["time_range"] == "本月"]
                if not cur:
                    continue
                d = cur[0]
                # REAS-06: 销项税额非负
                ot = _v(d, 'output_tax')
                if ot < 0:
                    results.append(CheckResult(rule_id="REAS-06", rule_name_cn="销项税额非负",
                        category="reasonableness", severity="error", status="fail", period=per,
                        expected=0, actual=ot, difference=abs(ot),
                        message=f"销项税额为负数{ot:.2f}"))
                else:
                    results.append(CheckResult(rule_id="REAS-06", rule_name_cn="销项税额非负",
                        category="reasonableness", severity="error", status="pass", period=per))
                # REAS-07: 进项税额非负
                it = _v(d, 'input_tax')
                if it < 0:
                    results.append(CheckResult(rule_id="REAS-07", rule_name_cn="进项税额非负",
                        category="reasonableness", severity="error", status="fail", period=per,
                        expected=0, actual=it, difference=abs(it),
                        message=f"进项税额为负数{it:.2f}"))
                else:
                    results.append(CheckResult(rule_id="REAS-07", rule_name_cn="进项税额非负",
                        category="reasonableness", severity="error", status="pass", period=per))

        # REAS-08: EIT税率范围
        valid_rates = {0.05, 0.10, 0.15, 0.20, 0.25}
        for y, d in self._get_eit_annual(conn, tid):
            rate = _v(d, 'tax_rate')
            if rate not in valid_rates:
                results.append(CheckResult(rule_id="REAS-08", rule_name_cn="EIT税率范围",
                    category="reasonableness", severity="warning", status="warn", period=f"{y}-年报",
                    expected=0.25, actual=rate, difference=0,
                    message=f"税率{rate}不在常见范围{valid_rates}"))
            else:
                results.append(CheckResult(rule_id="REAS-08", rule_name_cn="EIT税率范围",
                    category="reasonableness", severity="warning", status="pass", period=f"{y}-年报"))

        # REAS-10: CF期末现金非负
        cf_periods = self._get_periods(conn, "fs_cash_flow_item", tid, is_gaap)
        for y, m in cf_periods:
            per = f"{y}-{str(m).zfill(2)}"
            ending_code = "ending_cash" if is_gaap == "CAS" else "ending_cash"
            d = self._get_eav_batch(conn, "fs_cash_flow_item", tid, y, m,
                [ending_code], "current_amount", is_gaap)
            cash = _v(d, ending_code)
            if cash < 0:
                results.append(CheckResult(rule_id="REAS-10", rule_name_cn="期末现金非负",
                    category="reasonableness", severity="warning", status="warn", period=per,
                    expected=0, actual=cash, difference=abs(cash),
                    message=f"期末现金为负数{cash:.2f}"))
            else:
                results.append(CheckResult(rule_id="REAS-10", rule_name_cn="期末现金非负",
                    category="reasonableness", severity="warning", status="pass", period=per))

        return results

    # ── Cross-table validation ──

    def _check_cross_table(self, conn, tid, bs_gaap, is_gaap, is_general):
        """CROSS-01~08: 跨表校验."""
        results = []
        # Find overlapping periods between BS and CF
        bs_periods = self._get_periods(conn, "fs_balance_sheet_item", tid, bs_gaap)
        cf_periods = set(self._get_periods(conn, "fs_cash_flow_item", tid, is_gaap))

        for y, m in bs_periods:
            per = f"{y}-{str(m).zfill(2)}"
            # CROSS-01: BS货币资金 vs CF期末现金
            if (y, m) in cf_periods:
                bs_d = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y, m,
                    ["CASH"], "ending_balance", bs_gaap)
                cf_d = self._get_eav_batch(conn, "fs_cash_flow_item", tid, y, m,
                    ["ending_cash"], "current_amount", is_gaap)
                bs_cash = _v(bs_d, "CASH")
                cf_cash = _v(cf_d, "ending_cash")
                results.append(_check("CROSS-01", "BS货币资金 vs CF期末现金",
                    "cross_table", "error", bs_cash, cf_cash, 1000, per))

            # CROSS-02: BS货币资金 vs 科目余额表(1001库存现金 + 1002银行存款)
            ab_row = conn.execute(
                "SELECT SUM(closing_balance) as closing_balance FROM account_balance "
                "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
                "AND (account_code LIKE '1001%' OR account_code LIKE '1002%') "
                "AND revision_no = (SELECT MAX(revision_no) FROM account_balance ab2 "
                "  WHERE ab2.taxpayer_id = account_balance.taxpayer_id "
                "  AND ab2.period_year = account_balance.period_year "
                "  AND ab2.period_month = account_balance.period_month "
                "  AND ab2.account_code = account_balance.account_code)",
                (tid, y, m)
            ).fetchone()
            if ab_row and ab_row["closing_balance"] is not None:
                bs_d2 = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y, m,
                    ["CASH"], "ending_balance", bs_gaap)
                ab_cash = float(ab_row["closing_balance"] or 0)
                results.append(_check("CROSS-02", "BS货币资金 vs 科目余额(1001+1002)",
                    "cross_table", "error", _v(bs_d2, "CASH"), ab_cash, 1000, per))

        # CROSS-03~04: IS年累计 vs EIT年报 (12月)
        for y, d_eit in self._get_eit_annual(conn, tid):
            per = f"{y}-年报"
            # Find December IS data
            is_d = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, 12,
                ["operating_revenue", "total_profit"], "cumulative_amount", is_gaap)
            if is_d:
                # CROSS-03: IS营业收入 vs EIT收入
                results.append(_check("CROSS-03", "IS营业收入 vs EIT收入",
                    "cross_table", "error",
                    _v(is_d, "operating_revenue"), _v(d_eit, "revenue"), 10000, per))
                # CROSS-04: IS利润总额 vs EIT利润总额
                results.append(_check("CROSS-04", "IS利润总额 vs EIT利润总额",
                    "cross_table", "error",
                    _v(is_d, "total_profit"), _v(d_eit, "total_profit"), 10000, per))

        # CROSS-05~07: 发票 vs VAT (warning级别, 50000容差)
        if is_general:
            vat_rows = self._get_vat_rows(conn, "vat_return_general", tid)
            for (y, m_), rows in vat_rows.items():
                per = f"{y}-{str(m_).zfill(2)}"
                cur = [r for r in rows if r["item_type"] == "一般项目" and r["time_range"] == "本月"]
                if not cur:
                    continue
                vd = cur[0]
                # Purchase invoice tax sum
                inv_purchase_tax = conn.execute(
                    "SELECT COALESCE(SUM(tax_amount), 0) as total FROM inv_spec_purchase "
                    "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?",
                    (tid, y, m_)
                ).fetchone()
                if inv_purchase_tax:
                    results.append(_check("CROSS-06", "进项发票税额 vs VAT进项税额",
                        "cross_table", "warning",
                        float(inv_purchase_tax["total"]), _v(vd, 'input_tax'), 50000, per))
                # Sales invoice tax sum
                inv_sales_tax = conn.execute(
                    "SELECT COALESCE(SUM(tax_amount), 0) as total FROM inv_spec_sales "
                    "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?",
                    (tid, y, m_)
                ).fetchone()
                if inv_sales_tax:
                    results.append(_check("CROSS-07", "销项发票税额 vs VAT销项税额",
                        "cross_table", "warning",
                        float(inv_sales_tax["total"]), _v(vd, 'output_tax'), 50000, per))
                # Sales invoice amount vs VAT sales
                inv_sales_amt = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) as total FROM inv_spec_sales "
                    "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ?",
                    (tid, y, m_)
                ).fetchone()
                if inv_sales_amt:
                    vat_sales = _v(vd, 'sales_goods') + _v(vd, 'sales_services')
                    results.append(_check("CROSS-05", "销项发票金额 vs VAT销售额",
                        "cross_table", "warning",
                        float(inv_sales_amt["total"]), vat_sales, 50000, per))

        # CROSS-08: IS所得税费用 vs EIT实际应纳税额
        for y, d_eit in self._get_eit_annual(conn, tid):
            per = f"{y}-年报"
            is_d = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, 12,
                ["income_tax_expense"], "cumulative_amount", is_gaap)
            if is_d:
                results.append(_check("CROSS-08", "IS所得税费用 vs EIT实际应纳税额",
                    "cross_table", "error",
                    _v(is_d, "income_tax_expense"), _v(d_eit, "actual_tax_payable"), 10000, per))

        if not results:
            results.append(CheckResult(rule_id="CROSS-01", rule_name_cn="跨表校验",
                category="cross_table", severity="error", status="skip",
                message="无可比较的跨表数据"))
        return results

    # ── Period continuity ──

    def _check_period_continuity(self, conn, tid, bs_gaap, is_gaap, is_general):
        """CONT-01~06: 期间连续性检查."""
        results = []

        # CONT-01: BS期末 = 下月期初
        bs_periods = self._get_periods(conn, "fs_balance_sheet_item", tid, bs_gaap)
        for i in range(len(bs_periods) - 1):
            y1, m1 = bs_periods[i]
            y2, m2 = bs_periods[i + 1]
            # Check if consecutive months
            expected_next = (y1, m1 + 1) if m1 < 12 else (y1 + 1, 1)
            if (y2, m2) != expected_next:
                continue
            per = f"{y1}-{str(m1).zfill(2)}→{y2}-{str(m2).zfill(2)}"
            for code in ["ASSETS", "LIABILITIES", "EQUITY"]:
                d1 = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y1, m1,
                    [code], "ending_balance", bs_gaap)
                d2 = self._get_eav_batch(conn, "fs_balance_sheet_item", tid, y2, m2,
                    [code], "beginning_balance", bs_gaap)
                results.append(_check("CONT-01", f"BS连续性({code})",
                    "period_continuity", "error",
                    _v(d1, code), _v(d2, code), 0.01, per))

        # CONT-02: CF期末现金 = 下月期初现金
        cf_periods = self._get_periods(conn, "fs_cash_flow_item", tid, is_gaap)
        for i in range(len(cf_periods) - 1):
            y1, m1 = cf_periods[i]
            y2, m2 = cf_periods[i + 1]
            expected_next = (y1, m1 + 1) if m1 < 12 else (y1 + 1, 1)
            if (y2, m2) != expected_next:
                continue
            per = f"{y1}-{str(m1).zfill(2)}→{y2}-{str(m2).zfill(2)}"
            d1 = self._get_eav_batch(conn, "fs_cash_flow_item", tid, y1, m1,
                ["ending_cash"], "current_amount", is_gaap)
            d2 = self._get_eav_batch(conn, "fs_cash_flow_item", tid, y2, m2,
                ["beginning_cash"], "current_amount", is_gaap)
            results.append(_check("CONT-02", "CF期末现金连续性",
                "period_continuity", "error",
                _v(d1, "ending_cash"), _v(d2, "beginning_cash"), 0.01, per))

        # CONT-03: VAT-G期末留抵 = 下月上期留抵
        if is_general:
            vat_rows = self._get_vat_rows(conn, "vat_return_general", tid)
            sorted_periods = sorted(vat_rows.keys())
            for i in range(len(sorted_periods) - 1):
                y1, m1 = sorted_periods[i]
                y2, m2 = sorted_periods[i + 1]
                expected_next = (y1, m1 + 1) if m1 < 12 else (y1 + 1, 1)
                if (y2, m2) != expected_next:
                    continue
                per = f"{y1}-{str(m1).zfill(2)}→{y2}-{str(m2).zfill(2)}"
                cur1 = [r for r in vat_rows[(y1, m1)] if r["item_type"] == "一般项目" and r["time_range"] == "本月"]
                cur2 = [r for r in vat_rows[(y2, m2)] if r["item_type"] == "一般项目" and r["time_range"] == "本月"]
                if cur1 and cur2:
                    results.append(_check("CONT-03", "VAT期末留抵连续性",
                        "period_continuity", "error",
                        _v(cur1[0], 'end_credit'), _v(cur2[0], 'last_period_credit'), 0.01, per))

        # CONT-04: 科目余额表期末 = 下月期初
        ab_periods = self._get_periods(conn, "account_balance", tid)
        for i in range(len(ab_periods) - 1):
            y1, m1 = ab_periods[i]
            y2, m2 = ab_periods[i + 1]
            expected_next = (y1, m1 + 1) if m1 < 12 else (y1 + 1, 1)
            if (y2, m2) != expected_next:
                continue
            per = f"{y1}-{str(m1).zfill(2)}→{y2}-{str(m2).zfill(2)}"
            # Check top-level accounts (4-digit codes)
            rows1 = conn.execute(
                "SELECT account_code, closing_balance FROM account_balance "
                "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
                "AND LENGTH(account_code) = 4 ORDER BY revision_no DESC",
                (tid, y1, m1)
            ).fetchall()
            seen = set()
            for r in rows1:
                code = r["account_code"]
                if code in seen:
                    continue
                seen.add(code)
                cb = float(r["closing_balance"] or 0)
                r2 = conn.execute(
                    "SELECT opening_balance FROM account_balance "
                    "WHERE taxpayer_id = ? AND period_year = ? AND period_month = ? "
                    "AND account_code = ? ORDER BY revision_no DESC LIMIT 1",
                    (tid, y2, m2, code)
                ).fetchone()
                if r2:
                    ob = float(r2["opening_balance"] or 0)
                    diff = abs(cb - ob)
                    if diff > 0.01:
                        results.append(CheckResult(
                            rule_id="CONT-04", rule_name_cn=f"科目余额连续性({code})",
                            category="period_continuity", severity="error", status="fail",
                            period=per, expected=cb, actual=ob, difference=diff,
                            message=f"科目{code}期末{cb:.2f}≠下月期初{ob:.2f}"))

        # CONT-05: IS累计金额单调递增(年内)
        is_periods = self._get_periods(conn, "fs_income_statement_item", tid, is_gaap)
        year_groups = {}
        for y, m in is_periods:
            year_groups.setdefault(y, []).append(m)
        for y, months in year_groups.items():
            months.sort()
            for i in range(len(months) - 1):
                m1, m2 = months[i], months[i + 1]
                d1 = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, m1,
                    ["operating_revenue"], "cumulative_amount", is_gaap)
                d2 = self._get_eav_batch(conn, "fs_income_statement_item", tid, y, m2,
                    ["operating_revenue"], "cumulative_amount", is_gaap)
                rev1 = _v(d1, "operating_revenue")
                rev2 = _v(d2, "operating_revenue")
                per = f"{y}-{str(m1).zfill(2)}→{y}-{str(m2).zfill(2)}"
                if rev2 < rev1:
                    results.append(CheckResult(
                        rule_id="CONT-05", rule_name_cn="IS累计收入单调递增",
                        category="period_continuity", severity="warning", status="warn",
                        period=per, expected=rev1, actual=rev2, difference=rev1 - rev2,
                        message=f"累计收入从{rev1:.2f}降至{rev2:.2f}"))
                else:
                    results.append(CheckResult(rule_id="CONT-05", rule_name_cn="IS累计收入单调递增",
                        category="period_continuity", severity="warning", status="pass", period=per))

        # CONT-06: EIT-Q季度累计一致性
        quarters = self._get_eit_quarter(conn, tid)
        year_q = {}
        for y, q, d in quarters:
            year_q.setdefault(y, []).append((q, d))
        for y, qlist in year_q.items():
            qlist.sort(key=lambda x: x[0])
            for i in range(len(qlist) - 1):
                q1, d1 = qlist[i]
                q2, d2 = qlist[i + 1]
                rev1 = _v(d1, 'revenue')
                rev2 = _v(d2, 'revenue')
                per = f"{y}-Q{q1}→Q{q2}"
                if rev2 < rev1 - 1.0:
                    results.append(CheckResult(
                        rule_id="CONT-06", rule_name_cn="EIT季报累计一致性",
                        category="period_continuity", severity="error", status="fail",
                        period=per, expected=rev1, actual=rev2, difference=rev1 - rev2,
                        message=f"Q{q2}累计收入{rev2:.2f}<Q{q1}累计{rev1:.2f}"))
                else:
                    results.append(CheckResult(rule_id="CONT-06", rule_name_cn="EIT季报累计一致性",
                        category="period_continuity", severity="error", status="pass", period=per))

        if not results:
            results.append(CheckResult(rule_id="CONT-01", rule_name_cn="期间连续性",
                category="period_continuity", severity="error", status="skip",
                message="数据期间不足，无法检查连续性"))
        return results
