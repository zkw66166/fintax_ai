"""
fix_data_quality.py — 修复6家企业的数据质量问题

按依赖顺序修复7类数据：
1. 科目余额表 (account_balance) — 等式 + 连续性
2. 发票 (inv_spec_purchase) — 金额浮点误差
3. 资产负债表 (fs_balance_sheet_item) — 连续性 + ASSE固定资产拆分
4. 利润表 (fs_income_statement_item) — 营业利润/利润总额/净利润公式
5. 现金流量表 (fs_cash_flow_item) — 小计/净增加额/期末现金/连续性
6. 增值税申报表 (vat_return_general) — 计算字段填充 + 连续性
7. 企业所得税季报 (eit_quarter_main) — 利润总额=收入-成本
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fintax_ai.db")

ALL_TAXPAYERS = [
    '91310000MA1FL8XQ30',  # 华兴科技 一般纳税人 ASBE/CAS
    '92440300MA5EQXL17P',  # 鑫源贸易 小规模纳税人 ASSE/SAS
    '91330200MA2KXXXXXX',  # 创智软件 一般纳税人 ASBE/CAS
    '91330200MA2KYYYYYY',  # 大华智能制造 小规模纳税人 ASSE/SAS
    '91310115MA2KZZZZZZ',  # TSE科技 一般纳税人 ASBE/CAS
    '91330100MA2KWWWWWW',  # 环球机械 小规模纳税人 ASSE/SAS
]

# CAS income statement: operating_profit = sum(add) - sum(sub)
CAS_OP_ADD = ['operating_revenue', 'other_gains', 'investment_income',
              'net_exposure_hedge_income', 'fair_value_change_income',
              'credit_impairment_loss', 'asset_impairment_loss', 'asset_disposal_gains']
CAS_OP_SUB = ['operating_cost', 'taxes_and_surcharges', 'selling_expense',
              'administrative_expense', 'rd_expense', 'financial_expense']

# SAS income statement
SAS_OP_ADD = ['operating_revenue', 'investment_income']
SAS_OP_SUB = ['operating_cost', 'taxes_and_surcharges', 'selling_expense',
              'administrative_expense', 'financial_expense']

# CAS cash flow item codes
CAS_OP_IN = ['operating_inflow_sales', 'operating_inflow_tax_refund', 'operating_inflow_other']
CAS_OP_OUT = ['operating_outflow_purchase', 'operating_outflow_labor',
              'operating_outflow_tax', 'operating_outflow_other']
CAS_INV_IN = ['investing_inflow_sale_investment', 'investing_inflow_returns',
              'investing_inflow_disposal_assets', 'investing_inflow_disposal_subsidiary',
              'investing_inflow_other']
CAS_INV_OUT = ['investing_outflow_purchase_assets', 'investing_outflow_purchase_investment',
               'investing_outflow_acquire_subsidiary', 'investing_outflow_other']
CAS_FIN_IN = ['financing_inflow_capital', 'financing_inflow_borrowing', 'financing_inflow_other']
CAS_FIN_OUT = ['financing_outflow_debt_repayment', 'financing_outflow_dividend_interest',
               'financing_outflow_other']

# SAS cash flow item codes
SAS_OP_IN = ['operating_receipts_sales', 'operating_receipts_other']
SAS_OP_OUT = ['operating_payments_purchase', 'operating_payments_staff',
              'operating_payments_tax', 'operating_payments_other']
SAS_INV_IN = ['investing_receipts_disposal_investment', 'investing_receipts_returns',
              'investing_receipts_disposal_assets']
SAS_INV_OUT = ['investing_payments_purchase_investment', 'investing_payments_purchase_assets']
SAS_FIN_IN = ['financing_receipts_borrowing', 'financing_receipts_capital']
SAS_FIN_OUT = ['financing_payments_debt_principal', 'financing_payments_debt_interest',
               'financing_payments_dividend']


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_taxpayer_info(conn):
    """Return {taxpayer_id: {type, bs_gaap, is_gaap}}."""
    rows = conn.execute(
        "SELECT taxpayer_id, taxpayer_type, accounting_standard FROM taxpayer_info"
    ).fetchall()
    info = {}
    for r in rows:
        tid = r['taxpayer_id']
        is_general = r['taxpayer_type'] == '一般纳税人'
        std = r['accounting_standard'] or ('企业会计准则' if is_general else '小企业会计准则')
        info[tid] = {
            'type': r['taxpayer_type'],
            'is_general': is_general,
            'bs_gaap': 'ASBE' if std == '企业会计准则' else 'ASSE',
            'is_gaap': 'CAS' if std == '企业会计准则' else 'SAS',
        }
    return info


# ============================================================
# Step 1: 科目余额表 — 等式修复 + 连续性
# ============================================================
def fix_account_balance(conn):
    print("\n=== Step 1: 修复科目余额表 ===")
    fixed = 0
    # Get balance_direction from account_master
    dir_map = {}
    for r in conn.execute("SELECT account_code, balance_direction FROM account_master").fetchall():
        dir_map[r['account_code']] = r['balance_direction']

    for tid in ALL_TAXPAYERS:
        # Get all periods sorted
        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM account_balance "
            "WHERE taxpayer_id = ? ORDER BY period_year, period_month", (tid,)
        ).fetchall()
        # Get all account codes for this taxpayer
        codes = conn.execute(
            "SELECT DISTINCT account_code FROM account_balance WHERE taxpayer_id = ?", (tid,)
        ).fetchall()

        for code_row in codes:
            code = code_row['account_code']
            direction = dir_map.get(code, '借')
            prev_closing = None

            for p in periods:
                y, m = p['period_year'], p['period_month']
                row = conn.execute(
                    "SELECT rowid, opening_balance, debit_amount, credit_amount, closing_balance "
                    "FROM account_balance WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                    "AND account_code=? ORDER BY revision_no DESC LIMIT 1",
                    (tid, y, m, code)
                ).fetchone()
                if not row:
                    prev_closing = None
                    continue

                ob = float(row['opening_balance'] or 0)
                db = float(row['debit_amount'] or 0)
                cr = float(row['credit_amount'] or 0)
                cb = float(row['closing_balance'] or 0)
                rid = row['rowid']
                updates = {}

                # Fix continuity: opening = prev month's closing
                if prev_closing is not None and abs(ob - prev_closing) > 0.01:
                    updates['opening_balance'] = prev_closing
                    ob = prev_closing

                # Fix equation: closing = opening +/- debit/credit
                if direction == '借':
                    expected = ob + db - cr
                else:
                    expected = ob - db + cr
                if abs(cb - expected) > 0.01:
                    updates['closing_balance'] = round(expected, 2)
                    cb = round(expected, 2)

                if updates:
                    sets = ', '.join(f"{k}=?" for k in updates)
                    conn.execute(f"UPDATE account_balance SET {sets} WHERE rowid=?",
                                 list(updates.values()) + [rid])
                    fixed += 1

                prev_closing = cb

    conn.commit()
    print(f"  修复 {fixed} 条科目余额记录")


# ============================================================
# Step 2: 发票 — amount = round(quantity * unit_price, 2)
# ============================================================
def fix_invoices(conn):
    print("\n=== Step 2: 修复发票金额 ===")
    fixed = 0
    rows = conn.execute(
        "SELECT rowid, quantity, unit_price, amount, tax_amount, total_amount "
        "FROM inv_spec_purchase WHERE quantity IS NOT NULL AND unit_price IS NOT NULL"
    ).fetchall()
    for r in rows:
        qty = float(r['quantity'] or 0)
        price = float(r['unit_price'] or 0)
        amt = float(r['amount'] or 0)
        tax = float(r['tax_amount'] or 0)
        total = float(r['total_amount'] or 0)
        updates = {}

        expected_amt = round(qty * price, 2)
        if abs(amt - expected_amt) > 0.001:
            updates['amount'] = expected_amt
            amt = expected_amt

        expected_total = round(amt + tax, 2)
        if abs(total - expected_total) > 0.001:
            updates['total_amount'] = expected_total

        if updates:
            sets = ', '.join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE inv_spec_purchase SET {sets} WHERE rowid=?",
                         list(updates.values()) + [r['rowid']])
            fixed += 1

    conn.commit()
    print(f"  修复 {fixed} 条发票记录")


# ============================================================
# Step 3: 资产负债表 — 连续性 + ASSE固定资产拆分
# ============================================================
def fix_balance_sheet(conn):
    print("\n=== Step 3: 修复资产负债表 ===")
    info = get_taxpayer_info(conn)
    fixed_cont = 0
    fixed_asse = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti:
            continue
        gaap = ti['bs_gaap']

        # Get all periods sorted
        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM fs_balance_sheet_item "
            "WHERE taxpayer_id=? AND gaap_type=? ORDER BY period_year, period_month",
            (tid, gaap)
        ).fetchall()

        # Get all item_codes
        codes = conn.execute(
            "SELECT DISTINCT item_code FROM fs_balance_sheet_item "
            "WHERE taxpayer_id=? AND gaap_type=?", (tid, gaap)
        ).fetchall()

        for code_row in codes:
            code = code_row['item_code']
            prev_ending = None

            for p in periods:
                y, m = p['period_year'], p['period_month']
                row = conn.execute(
                    "SELECT rowid, beginning_balance, ending_balance "
                    "FROM fs_balance_sheet_item "
                    "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                    "AND gaap_type=? AND item_code=? ORDER BY revision_no DESC LIMIT 1",
                    (tid, y, m, gaap, code)
                ).fetchone()
                if not row:
                    prev_ending = None
                    continue

                bb = float(row['beginning_balance'] or 0)
                eb = float(row['ending_balance'] or 0)

                if prev_ending is not None and abs(bb - prev_ending) > 0.01:
                    conn.execute(
                        "UPDATE fs_balance_sheet_item SET beginning_balance=? WHERE rowid=?",
                        (round(prev_ending, 2), row['rowid']))
                    fixed_cont += 1

                prev_ending = eb

        # ASSE: supplement FIXED_ASSETS_ORIGINAL and ACCUMULATED_DEPRECIATION
        if gaap == 'ASSE':
            for p in periods:
                y, m = p['period_year'], p['period_month']
                d = {}
                for r in conn.execute(
                    "SELECT item_code, ending_balance, beginning_balance FROM fs_balance_sheet_item "
                    "WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type='ASSE' "
                    "AND item_code IN ('FIXED_ASSETS_NET','FIXED_ASSETS_ORIGINAL','ACCUMULATED_DEPRECIATION') "
                    "ORDER BY revision_no DESC", (tid, y, m)
                ).fetchall():
                    if r['item_code'] not in d:
                        d[r['item_code']] = dict(r)

                net_row = d.get('FIXED_ASSETS_NET')
                if not net_row:
                    continue
                net_end = float(net_row['ending_balance'] or 0)
                net_beg = float(net_row['beginning_balance'] or 0)

                orig = d.get('FIXED_ASSETS_ORIGINAL')
                dep = d.get('ACCUMULATED_DEPRECIATION')

                if (not orig or float(orig['ending_balance'] or 0) == 0) and net_end != 0:
                    # Estimate: original ~= net * 1.3, depreciation = original - net
                    est_orig_end = round(net_end * 1.3, 2)
                    est_dep_end = round(est_orig_end - net_end, 2)
                    est_orig_beg = round(net_beg * 1.3, 2)
                    est_dep_beg = round(est_orig_beg - net_beg, 2)

                    if not orig:
                        conn.execute(
                            "INSERT OR REPLACE INTO fs_balance_sheet_item "
                            "(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no, "
                            "beginning_balance, ending_balance, item_name, section) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (tid, y, m, 'ASSE', 'FIXED_ASSETS_ORIGINAL', 0,
                             est_orig_beg, est_orig_end, '固定资产原价', '非流动资产'))
                    else:
                        conn.execute(
                            "UPDATE fs_balance_sheet_item SET ending_balance=?, beginning_balance=? "
                            "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                            "AND gaap_type='ASSE' AND item_code='FIXED_ASSETS_ORIGINAL' AND revision_no=0",
                            (est_orig_end, est_orig_beg, tid, y, m))

                    if not dep:
                        conn.execute(
                            "INSERT OR REPLACE INTO fs_balance_sheet_item "
                            "(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no, "
                            "beginning_balance, ending_balance, item_name, section) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (tid, y, m, 'ASSE', 'ACCUMULATED_DEPRECIATION', 0,
                             est_dep_beg, est_dep_end, '累计折旧', '非流动资产'))
                    else:
                        conn.execute(
                            "UPDATE fs_balance_sheet_item SET ending_balance=?, beginning_balance=? "
                            "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                            "AND gaap_type='ASSE' AND item_code='ACCUMULATED_DEPRECIATION' AND revision_no=0",
                            (est_dep_end, est_dep_beg, tid, y, m))
                    fixed_asse += 1

    conn.commit()
    print(f"  修复 {fixed_cont} 条BS连续性, {fixed_asse} 条ASSE固定资产拆分")


# ============================================================
# Step 4: 利润表 — 营业利润/利润总额/净利润公式修复
# ============================================================
def _get_eav(conn, table, tid, y, m, codes, col, gaap):
    """Fetch EAV values. Returns {item_code: float}."""
    if not codes:
        return {}
    ph = ",".join("?" for _ in codes)
    rows = conn.execute(
        f"SELECT item_code, {col} FROM {table} "
        f"WHERE taxpayer_id=? AND period_year=? AND period_month=? "
        f"AND gaap_type=? AND item_code IN ({ph}) ORDER BY revision_no DESC",
        [tid, y, m, gaap] + list(codes)
    ).fetchall()
    result = {}
    for r in rows:
        if r['item_code'] not in result:
            result[r['item_code']] = float(r[col] or 0) if r[col] is not None else 0.0
    return result


def _update_eav(conn, table, tid, y, m, gaap, code, col, value):
    """Update a single EAV cell."""
    conn.execute(
        f"UPDATE {table} SET {col}=? "
        f"WHERE taxpayer_id=? AND period_year=? AND period_month=? "
        f"AND gaap_type=? AND item_code=? AND revision_no="
        f"(SELECT MAX(revision_no) FROM {table} "
        f" WHERE taxpayer_id=? AND period_year=? AND period_month=? AND gaap_type=? AND item_code=?)",
        (round(value, 2), tid, y, m, gaap, code, tid, y, m, gaap, code)
    )


def fix_income_statement(conn):
    print("\n=== Step 4: 修复利润表 ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti:
            continue
        gaap = ti['is_gaap']
        add_items = CAS_OP_ADD if gaap == 'CAS' else SAS_OP_ADD
        sub_items = CAS_OP_SUB if gaap == 'CAS' else SAS_OP_SUB

        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM fs_income_statement_item "
            "WHERE taxpayer_id=? AND gaap_type=? ORDER BY period_year, period_month",
            (tid, gaap)
        ).fetchall()

        all_codes = list(set(add_items + sub_items + [
            'operating_profit', 'non_operating_income', 'non_operating_expense',
            'total_profit', 'income_tax_expense', 'net_profit',
            'other_comprehensive_income_net', 'comprehensive_income_total',
        ]))

        for p in periods:
            y, m = p['period_year'], p['period_month']
            for col in ['current_amount', 'cumulative_amount']:
                d = _get_eav(conn, "fs_income_statement_item", tid, y, m, all_codes, col, gaap)
                if not d:
                    continue

                # operating_profit = sum(add) - sum(sub)
                exp_op = sum(d.get(c, 0) for c in add_items) - sum(d.get(c, 0) for c in sub_items)
                if abs(d.get('operating_profit', 0) - exp_op) > 1.0:
                    _update_eav(conn, "fs_income_statement_item", tid, y, m, gaap,
                                'operating_profit', col, exp_op)
                    d['operating_profit'] = exp_op
                    fixed += 1

                # total_profit = operating_profit + non_op_income - non_op_expense
                exp_tp = d.get('operating_profit', 0) + d.get('non_operating_income', 0) - d.get('non_operating_expense', 0)
                if abs(d.get('total_profit', 0) - exp_tp) > 1.0:
                    _update_eav(conn, "fs_income_statement_item", tid, y, m, gaap,
                                'total_profit', col, exp_tp)
                    d['total_profit'] = exp_tp
                    fixed += 1

                # net_profit = total_profit - income_tax_expense
                exp_np = d.get('total_profit', 0) - d.get('income_tax_expense', 0)
                if abs(d.get('net_profit', 0) - exp_np) > 1.0:
                    _update_eav(conn, "fs_income_statement_item", tid, y, m, gaap,
                                'net_profit', col, exp_np)
                    d['net_profit'] = exp_np
                    fixed += 1

                # CAS: comprehensive_income_total = net_profit + other_comprehensive_income_net
                if gaap == 'CAS':
                    exp_ci = d.get('net_profit', 0) + d.get('other_comprehensive_income_net', 0)
                    if abs(d.get('comprehensive_income_total', 0) - exp_ci) > 1.0:
                        _update_eav(conn, "fs_income_statement_item", tid, y, m, gaap,
                                    'comprehensive_income_total', col, exp_ci)
                        fixed += 1

    conn.commit()
    print(f"  修复 {fixed} 条利润表记录")


# ============================================================
# Step 5: 现金流量表 — 小计/净额/净增加额/期末现金/连续性
# ============================================================
def fix_cash_flow(conn):
    print("\n=== Step 5: 修复现金流量表 ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti:
            continue
        gaap = ti['is_gaap']
        is_cas = gaap == 'CAS'

        op_in = CAS_OP_IN if is_cas else SAS_OP_IN
        op_out = CAS_OP_OUT if is_cas else SAS_OP_OUT
        inv_in = CAS_INV_IN if is_cas else SAS_INV_IN
        inv_out = CAS_INV_OUT if is_cas else SAS_INV_OUT
        fin_in = CAS_FIN_IN if is_cas else SAS_FIN_IN
        fin_out = CAS_FIN_OUT if is_cas else SAS_FIN_OUT

        subtotal_codes = (['operating_inflow_subtotal', 'operating_outflow_subtotal',
                           'investing_inflow_subtotal', 'investing_outflow_subtotal',
                           'financing_inflow_subtotal', 'financing_outflow_subtotal']
                          if is_cas else [])
        all_codes = list(set(
            op_in + op_out + inv_in + inv_out + fin_in + fin_out + subtotal_codes +
            ['operating_net_cash', 'investing_net_cash', 'financing_net_cash',
             'net_increase_cash', 'beginning_cash', 'ending_cash'] +
            (['fx_impact'] if is_cas else [])
        ))

        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM fs_cash_flow_item "
            "WHERE taxpayer_id=? AND gaap_type=? ORDER BY period_year, period_month",
            (tid, gaap)
        ).fetchall()

        prev_ending_cash = None
        for p in periods:
            y, m = p['period_year'], p['period_month']
            d = _get_eav(conn, "fs_cash_flow_item", tid, y, m, all_codes, "current_amount", gaap)
            if not d:
                prev_ending_cash = None
                continue

            # Fix beginning_cash continuity
            if prev_ending_cash is not None:
                beg = d.get('beginning_cash', 0)
                if abs(beg - prev_ending_cash) > 0.01:
                    _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                'beginning_cash', 'current_amount', prev_ending_cash)
                    d['beginning_cash'] = prev_ending_cash
                    fixed += 1

            if is_cas:
                # Fix subtotals
                pairs = [
                    (op_in, 'operating_inflow_subtotal'),
                    (op_out, 'operating_outflow_subtotal'),
                    (inv_in, 'investing_inflow_subtotal'),
                    (inv_out, 'investing_outflow_subtotal'),
                    (fin_in, 'financing_inflow_subtotal'),
                    (fin_out, 'financing_outflow_subtotal'),
                ]
                for items, sub_code in pairs:
                    exp = sum(d.get(c, 0) for c in items)
                    if abs(d.get(sub_code, 0) - exp) > 0.01:
                        _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                    sub_code, 'current_amount', exp)
                        d[sub_code] = exp
                        fixed += 1

                # Fix net amounts from subtotals
                net_pairs = [
                    ('operating_inflow_subtotal', 'operating_outflow_subtotal', 'operating_net_cash'),
                    ('investing_inflow_subtotal', 'investing_outflow_subtotal', 'investing_net_cash'),
                    ('financing_inflow_subtotal', 'financing_outflow_subtotal', 'financing_net_cash'),
                ]
                for in_sub, out_sub, net_code in net_pairs:
                    exp = d.get(in_sub, 0) - d.get(out_sub, 0)
                    if abs(d.get(net_code, 0) - exp) > 0.01:
                        _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                    net_code, 'current_amount', exp)
                        d[net_code] = exp
                        fixed += 1

                # net_increase = op_net + inv_net + fin_net + fx
                fx = d.get('fx_impact', 0)
                exp_net = d.get('operating_net_cash', 0) + d.get('investing_net_cash', 0) + d.get('financing_net_cash', 0) + fx
            else:
                # SAS: compute net directly from items
                op_net = sum(d.get(c, 0) for c in op_in) - sum(d.get(c, 0) for c in op_out)
                if abs(d.get('operating_net_cash', 0) - op_net) > 0.01:
                    _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                'operating_net_cash', 'current_amount', op_net)
                    d['operating_net_cash'] = op_net
                    fixed += 1

                inv_net = sum(d.get(c, 0) for c in inv_in) - sum(d.get(c, 0) for c in inv_out)
                if abs(d.get('investing_net_cash', 0) - inv_net) > 0.01:
                    _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                'investing_net_cash', 'current_amount', inv_net)
                    d['investing_net_cash'] = inv_net
                    fixed += 1

                fin_net = sum(d.get(c, 0) for c in fin_in) - sum(d.get(c, 0) for c in fin_out)
                if abs(d.get('financing_net_cash', 0) - fin_net) > 0.01:
                    _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                                'financing_net_cash', 'current_amount', fin_net)
                    d['financing_net_cash'] = fin_net
                    fixed += 1

                exp_net = d.get('operating_net_cash', 0) + d.get('investing_net_cash', 0) + d.get('financing_net_cash', 0)

            if abs(d.get('net_increase_cash', 0) - exp_net) > 1.0:
                _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                            'net_increase_cash', 'current_amount', exp_net)
                d['net_increase_cash'] = exp_net
                fixed += 1

            # ending_cash = beginning_cash + net_increase_cash
            exp_end = d.get('beginning_cash', 0) + d.get('net_increase_cash', 0)
            if abs(d.get('ending_cash', 0) - exp_end) > 0.01:
                _update_eav(conn, "fs_cash_flow_item", tid, y, m, gaap,
                            'ending_cash', 'current_amount', exp_end)
                d['ending_cash'] = exp_end
                fixed += 1

            prev_ending_cash = d.get('ending_cash', 0)

    conn.commit()
    print(f"  修复 {fixed} 条现金流量表记录")


# ============================================================
# Step 6: 增值税申报表 — 计算字段填充 + 连续性
# ============================================================
def fix_vat_general(conn):
    print("\n=== Step 6: 修复增值税申报表(一般纳税人) ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti or not ti['is_general']:
            continue

        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM vat_return_general "
            "WHERE taxpayer_id=? ORDER BY period_year, period_month", (tid,)
        ).fetchall()

        prev_end_credit = None
        for p in periods:
            y, m = p['period_year'], p['period_month']
            row = conn.execute(
                "SELECT rowid, * FROM vat_return_general "
                "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                "AND item_type='一般项目' AND time_range='本月' "
                "ORDER BY revision_no DESC LIMIT 1", (tid, y, m)
            ).fetchone()
            if not row:
                prev_end_credit = None
                continue

            d = dict(row)
            rid = d['rowid']
            updates = {}

            def v(key):
                val = d.get(key)
                return float(val) if val is not None else 0.0

            # Fix continuity: last_period_credit = prev month's end_credit
            if prev_end_credit is not None and d.get('last_period_credit') is None:
                updates['last_period_credit'] = prev_end_credit
                d['last_period_credit'] = prev_end_credit
            elif prev_end_credit is not None and abs(v('last_period_credit') - prev_end_credit) > 1.0:
                updates['last_period_credit'] = prev_end_credit
                d['last_period_credit'] = prev_end_credit

            # deductible_total = input_tax + last_period_credit - transfer_out - export_refund + tax_check_supplement
            exp_ded = v('input_tax') + v('last_period_credit') - v('transfer_out') - v('export_refund') + v('tax_check_supplement')
            if d.get('deductible_total') is None or abs(v('deductible_total') - exp_ded) > 1.0:
                updates['deductible_total'] = round(exp_ded, 2)
                d['deductible_total'] = round(exp_ded, 2)

            # actual_deduct = min(deductible_total, output_tax) — can't deduct more than output
            exp_actual = min(v('deductible_total'), v('output_tax'))
            if d.get('actual_deduct') is None or abs(v('actual_deduct') - exp_actual) > 1.0:
                updates['actual_deduct'] = round(exp_actual, 2)
                d['actual_deduct'] = round(exp_actual, 2)

            # end_credit = deductible_total - actual_deduct
            exp_credit = v('deductible_total') - v('actual_deduct')
            if d.get('end_credit') is None or abs(v('end_credit') - exp_credit) > 1.0:
                updates['end_credit'] = round(exp_credit, 2)
                d['end_credit'] = round(exp_credit, 2)

            # tax_payable = output_tax - actual_deduct
            exp_tax = v('output_tax') - v('actual_deduct')
            if abs(v('tax_payable') - exp_tax) > 1.0:
                updates['tax_payable'] = round(exp_tax, 2)
                d['tax_payable'] = round(exp_tax, 2)

            # total_tax_payable = tax_payable + simple_tax + simple_tax_check_supplement - tax_reduction
            exp_total = v('tax_payable') + v('simple_tax') + v('simple_tax_check_supplement') - v('tax_reduction')
            if d.get('total_tax_payable') is None or abs(v('total_tax_payable') - exp_total) > 1.0:
                updates['total_tax_payable'] = round(exp_total, 2)
                d['total_tax_payable'] = round(exp_total, 2)

            # unpaid_end = unpaid_begin + total_tax_payable - paid_current
            exp_unpaid = v('unpaid_begin') + v('total_tax_payable') - v('paid_current')
            if d.get('unpaid_end') is None or abs(v('unpaid_end') - exp_unpaid) > 1000:
                updates['unpaid_end'] = round(exp_unpaid, 2)
                d['unpaid_end'] = round(exp_unpaid, 2)

            if updates:
                sets = ', '.join(f"{k}=?" for k in updates)
                conn.execute(f"UPDATE vat_return_general SET {sets} WHERE rowid=?",
                             list(updates.values()) + [rid])
                fixed += 1

            prev_end_credit = v('end_credit')

    conn.commit()
    print(f"  修复 {fixed} 条VAT记录")


# ============================================================
# Step 7: 企业所得税季报 — total_profit = revenue - cost
# ============================================================
def fix_eit_quarter(conn):
    print("\n=== Step 7: 修复企业所得税季报 ===")
    fixed = 0

    rows = conn.execute(
        "SELECT m.rowid, m.filing_id, m.revenue, m.cost, m.total_profit, "
        "m.actual_profit, m.tax_rate, m.tax_payable, m.tax_credit_total, "
        "m.less_prepaid_tax_current_year, m.current_tax_payable_or_refund "
        "FROM eit_quarter_main m "
        "JOIN eit_quarter_filing f ON m.filing_id = f.filing_id "
        "WHERE f.taxpayer_id IN ({})".format(','.join('?' for _ in ALL_TAXPAYERS)),
        ALL_TAXPAYERS
    ).fetchall()

    for r in rows:
        rev = float(r['revenue'] or 0)
        cost = float(r['cost'] or 0)
        tp = float(r['total_profit'] or 0)
        ap = float(r['actual_profit'] or 0)
        rate = float(r['tax_rate'] or 0.25)
        tax = float(r['tax_payable'] or 0)
        credit = float(r['tax_credit_total'] or 0)
        prepaid = float(r['less_prepaid_tax_current_year'] or 0)
        cur_tax = float(r['current_tax_payable_or_refund'] or 0)
        updates = {}

        # total_profit = revenue - cost
        exp_tp = round(rev - cost, 2)
        if abs(tp - exp_tp) > 1.0:
            updates['total_profit'] = exp_tp
            tp = exp_tp

        # actual_profit = total_profit (simplified, no adjustments)
        if abs(ap - tp) > 1.0:
            updates['actual_profit'] = tp
            ap = tp

        # tax_payable = actual_profit * tax_rate
        exp_tax = round(ap * rate, 2)
        if abs(tax - exp_tax) > 1.0:
            updates['tax_payable'] = exp_tax
            tax = exp_tax

        # current_tax_payable_or_refund = tax_payable - tax_credit - prepaid
        exp_cur = round(tax - credit - prepaid, 2)
        if abs(cur_tax - exp_cur) > 1.0:
            updates['current_tax_payable_or_refund'] = exp_cur

        if updates:
            sets = ', '.join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE eit_quarter_main SET {sets} WHERE filing_id=?",
                         list(updates.values()) + [r['filing_id']])
            fixed += 1

    conn.commit()
    print(f"  修复 {fixed} 条EIT季报记录")


# ============================================================
# Step 8: 跨表对齐 — BS CASH vs CF ending_cash vs 科目余额 1001+1002
# ============================================================
def fix_cross_table_cash(conn):
    print("\n=== Step 8: 跨表对齐 — 货币资金 ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti:
            continue
        bs_gaap = ti['bs_gaap']
        is_gaap = ti['is_gaap']
        is_cas = is_gaap == 'CAS'

        # Get all BS periods with CASH value
        periods = conn.execute(
            "SELECT DISTINCT period_year, period_month FROM fs_balance_sheet_item "
            "WHERE taxpayer_id=? AND gaap_type=? AND item_code='CASH' "
            "ORDER BY period_year, period_month", (tid, bs_gaap)
        ).fetchall()

        prev_1002_closing = None
        prev_cf_ending = None
        for p in periods:
            y, m = p['period_year'], p['period_month']

            # Get BS CASH (the truth source)
            bs_row = conn.execute(
                "SELECT ending_balance FROM fs_balance_sheet_item "
                "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                "AND gaap_type=? AND item_code='CASH' ORDER BY revision_no DESC LIMIT 1",
                (tid, y, m, bs_gaap)
            ).fetchone()
            if not bs_row:
                prev_1002_closing = None
                continue
            bs_cash = float(bs_row['ending_balance'] or 0)

            # Align CF ending_cash to BS CASH
            cf_row = conn.execute(
                "SELECT rowid, current_amount FROM fs_cash_flow_item "
                "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                "AND gaap_type=? AND item_code='ending_cash' ORDER BY revision_no DESC LIMIT 1",
                (tid, y, m, is_gaap)
            ).fetchone()
            if cf_row:
                cf_cash = float(cf_row['current_amount'] or 0)
                # Get/fix beginning_cash from prev month's ending
                beg_row = conn.execute(
                    "SELECT rowid, current_amount FROM fs_cash_flow_item "
                    "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                    "AND gaap_type=? AND item_code='beginning_cash' ORDER BY revision_no DESC LIMIT 1",
                    (tid, y, m, is_gaap)
                ).fetchone()
                beg_cash = float(beg_row['current_amount'] or 0) if beg_row else 0
                if prev_cf_ending is not None and abs(beg_cash - prev_cf_ending) > 0.01 and beg_row:
                    beg_cash = prev_cf_ending
                    conn.execute("UPDATE fs_cash_flow_item SET current_amount=? WHERE rowid=?",
                                 (round(beg_cash, 2), beg_row['rowid']))

                if abs(cf_cash - bs_cash) > 1.0:
                    conn.execute("UPDATE fs_cash_flow_item SET current_amount=? WHERE rowid=?",
                                 (bs_cash, cf_row['rowid']))
                    # Update net_increase_cash = ending_cash - beginning_cash
                    new_net = round(bs_cash - beg_cash, 2)
                    _update_eav(conn, "fs_cash_flow_item", tid, y, m, is_gaap,
                                'net_increase_cash', 'current_amount', new_net)
                    # Adjust operating items to absorb the difference
                    net_codes = ['operating_net_cash', 'investing_net_cash', 'financing_net_cash']
                    if is_cas:
                        net_codes.append('fx_impact')
                    nd = _get_eav(conn, "fs_cash_flow_item", tid, y, m, net_codes, "current_amount", is_gaap)
                    old_sum = sum(nd.get(c, 0) for c in net_codes)
                    diff = new_net - old_sum
                    if abs(diff) > 0.01:
                        new_op_net = round(nd.get('operating_net_cash', 0) + diff, 2)
                        _update_eav(conn, "fs_cash_flow_item", tid, y, m, is_gaap,
                                    'operating_net_cash', 'current_amount', new_op_net)
                        if is_cas:
                            out_sub = _get_eav(conn, "fs_cash_flow_item", tid, y, m,
                                ['operating_outflow_subtotal'], "current_amount", is_gaap)
                            new_in_sub = round(new_op_net + out_sub.get('operating_outflow_subtotal', 0), 2)
                            _update_eav(conn, "fs_cash_flow_item", tid, y, m, is_gaap,
                                        'operating_inflow_subtotal', 'current_amount', new_in_sub)
                            in_items = _get_eav(conn, "fs_cash_flow_item", tid, y, m,
                                ['operating_inflow_tax_refund', 'operating_inflow_other'],
                                "current_amount", is_gaap)
                            other_in = sum(in_items.get(c, 0) for c in in_items)
                            new_sales = round(new_in_sub - other_in, 2)
                            _update_eav(conn, "fs_cash_flow_item", tid, y, m, is_gaap,
                                        'operating_inflow_sales', 'current_amount', new_sales)
                        else:
                            out_items = _get_eav(conn, "fs_cash_flow_item", tid, y, m,
                                SAS_OP_OUT, "current_amount", is_gaap)
                            out_sum = sum(out_items.get(c, 0) for c in SAS_OP_OUT)
                            new_in_total = round(new_op_net + out_sum, 2)
                            other_in = _get_eav(conn, "fs_cash_flow_item", tid, y, m,
                                ['operating_receipts_other'], "current_amount", is_gaap)
                            new_sales = round(new_in_total - other_in.get('operating_receipts_other', 0), 2)
                            _update_eav(conn, "fs_cash_flow_item", tid, y, m, is_gaap,
                                        'operating_receipts_sales', 'current_amount', new_sales)
                    fixed += 1
                prev_cf_ending = bs_cash
            else:
                prev_cf_ending = None

            # Align account_balance 1001+1002 sum to BS CASH
            row_1001 = conn.execute(
                "SELECT closing_balance FROM account_balance "
                "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                "AND account_code='1001' ORDER BY revision_no DESC LIMIT 1",
                (tid, y, m)
            ).fetchone()
            cash_1001 = float(row_1001['closing_balance'] or 0) if row_1001 else 0
            target_1002 = round(bs_cash - cash_1001, 2)

            row_1002 = conn.execute(
                "SELECT rowid, opening_balance, debit_amount, credit_amount, closing_balance "
                "FROM account_balance "
                "WHERE taxpayer_id=? AND period_year=? AND period_month=? "
                "AND account_code='1002' ORDER BY revision_no DESC LIMIT 1",
                (tid, y, m)
            ).fetchone()
            if row_1002:
                cur_1002 = float(row_1002['closing_balance'] or 0)
                if abs(cur_1002 - target_1002) > 1.0:
                    ob = float(row_1002['opening_balance'] or 0)
                    cr = float(row_1002['credit_amount'] or 0)
                    # Fix opening from prev month's closing if needed
                    if prev_1002_closing is not None and abs(ob - prev_1002_closing) > 0.01:
                        ob = prev_1002_closing
                    # Adjust debit to make equation work: closing = opening + debit - credit
                    new_debit = round(target_1002 - ob + cr, 2)
                    conn.execute(
                        "UPDATE account_balance SET closing_balance=?, debit_amount=?, opening_balance=? "
                        "WHERE rowid=?",
                        (target_1002, new_debit, ob, row_1002['rowid']))
                    fixed += 1
                prev_1002_closing = target_1002
            else:
                prev_1002_closing = None

    conn.commit()
    print(f"  修复 {fixed} 条跨表货币资金对齐")


# ============================================================
# Step 9: 跨表对齐 — IS年度累计 vs EIT年报
# ============================================================
def fix_cross_table_eit(conn):
    print("\n=== Step 9: 跨表对齐 — IS vs EIT年报 ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    for tid in ALL_TAXPAYERS:
        ti = info.get(tid)
        if not ti:
            continue
        is_gaap = ti['is_gaap']

        # Get EIT annual filings
        eit_rows = conn.execute(
            "SELECT f.period_year, m.filing_id, m.revenue, m.total_profit, m.actual_tax_payable "
            "FROM eit_annual_filing f JOIN eit_annual_main m ON f.filing_id = m.filing_id "
            "WHERE f.taxpayer_id=? ORDER BY f.period_year, f.revision_no DESC", (tid,)
        ).fetchall()

        seen_years = set()
        for er in eit_rows:
            year = er['period_year']
            if year in seen_years:
                continue
            seen_years.add(year)

            # Get IS December cumulative data
            is_d = _get_eav(conn, "fs_income_statement_item", tid, year, 12,
                            ['operating_revenue', 'total_profit', 'income_tax_expense'],
                            'cumulative_amount', is_gaap)
            if not is_d:
                continue

            updates = {}
            is_rev = is_d.get('operating_revenue', 0)
            is_tp = is_d.get('total_profit', 0)
            is_tax = is_d.get('income_tax_expense', 0)

            eit_rev = float(er['revenue'] or 0)
            eit_tp = float(er['total_profit'] or 0)
            eit_tax = float(er['actual_tax_payable'] or 0)

            # Align EIT to IS values
            if abs(eit_rev - is_rev) > 10000:
                updates['revenue'] = round(is_rev, 2)
            if abs(eit_tp - is_tp) > 10000:
                updates['total_profit'] = round(is_tp, 2)
            if abs(eit_tax - is_tax) > 10000:
                updates['actual_tax_payable'] = round(is_tax, 2)
                # Also fix dependent fields
                updates['tax_payable'] = round(is_tax, 2)
                updates['tax_payable_or_refund'] = round(is_tax, 2)

            if updates:
                # Also need to fix cost = revenue - total_profit (approximately)
                if 'revenue' in updates and 'total_profit' in updates:
                    new_rev = updates['revenue']
                    new_tp = updates['total_profit']
                    # Keep original operating_profit structure but fix cost
                    eit_main = conn.execute(
                        "SELECT * FROM eit_annual_main WHERE filing_id=?", (er['filing_id'],)
                    ).fetchone()
                    if eit_main:
                        old_cost = float(eit_main['cost'] or 0)
                        old_rev = float(eit_main['revenue'] or 0)
                        if old_rev != 0:
                            cost_ratio = old_cost / old_rev
                        else:
                            cost_ratio = 0.7
                        # Recalculate cost to be consistent
                        # operating_profit + non_op = total_profit, so we adjust cost
                        op_profit = float(eit_main['operating_profit'] or 0)
                        non_op_inc = float(eit_main['non_operating_income'] or 0)
                        non_op_exp = float(eit_main['non_operating_expenses'] or 0)
                        # total_profit = op_profit + non_op_inc - non_op_exp
                        # We want new total_profit, so: new_op_profit = new_tp - non_op_inc + non_op_exp
                        new_op = round(new_tp - non_op_inc + non_op_exp, 2)
                        updates['operating_profit'] = new_op
                        # op_profit = rev - cost - taxes_surcharges - expenses...
                        # Simplification: adjust cost to make equation work
                        taxes = float(eit_main['taxes_surcharges'] or 0)
                        selling = float(eit_main['selling_expenses'] or 0)
                        admin = float(eit_main['admin_expenses'] or 0)
                        rd = float(eit_main['rd_expenses'] or 0)
                        fin = float(eit_main['financial_expenses'] or 0)
                        other_adds = sum(float(eit_main[c] or 0) for c in [
                            'other_gains', 'investment_income', 'net_exposure_hedge_gains',
                            'fair_value_change_gains', 'credit_impairment_loss',
                            'asset_impairment_loss', 'asset_disposal_gains'])
                        # new_op = new_rev - cost - taxes - sell - admin - rd - fin + other_adds
                        new_cost = round(new_rev - taxes - selling - admin - rd - fin + other_adds - new_op, 2)
                        updates['cost'] = new_cost
                        # taxable_income ≈ total_profit (no adjustments)
                        updates['taxable_income'] = round(new_tp, 2)

                sets = ', '.join(f"{k}=?" for k in updates)
                conn.execute(f"UPDATE eit_annual_main SET {sets} WHERE filing_id=?",
                             list(updates.values()) + [er['filing_id']])
                fixed += 1

    conn.commit()
    print(f"  修复 {fixed} 条EIT年报跨表对齐")


# ============================================================
# Step 10: EIT年报 — 修复 tax_payable_or_refund 和 tax_payable
# ============================================================
def fix_eit_annual(conn):
    print("\n=== Step 10: 修复EIT年报公式 ===")
    info = get_taxpayer_info(conn)
    fixed = 0

    rows = conn.execute(
        "SELECT f.taxpayer_id, f.period_year, m.filing_id, m.taxable_income, m.tax_rate, "
        "m.tax_payable, m.tax_credit_total, m.actual_tax_payable, "
        "m.less_prepaid_tax, m.tax_payable_or_refund "
        "FROM eit_annual_filing f JOIN eit_annual_main m ON f.filing_id = m.filing_id "
        "WHERE f.taxpayer_id IN ({}) "
        "ORDER BY f.taxpayer_id, f.period_year, f.revision_no DESC".format(
            ','.join('?' for _ in ALL_TAXPAYERS)),
        ALL_TAXPAYERS
    ).fetchall()

    seen = set()
    for r in rows:
        key = (r['taxpayer_id'], r['period_year'])
        if key in seen:
            continue
        seen.add(key)

        tid = r['taxpayer_id']
        year = r['period_year']
        ti = info.get(tid)
        if not ti:
            continue
        is_gaap = ti['is_gaap']

        updates = {}
        taxable = float(r['taxable_income'] or 0)
        rate = float(r['tax_rate'] or 0.25)
        tp = float(r['tax_payable'] or 0)
        credit = float(r['tax_credit_total'] or 0)
        atp = float(r['actual_tax_payable'] or 0)
        prepaid = float(r['less_prepaid_tax'] or 0)
        refund = float(r['tax_payable_or_refund'] or 0)

        # Get IS December cumulative income_tax_expense as truth source for CROSS-08
        is_d = _get_eav(conn, "fs_income_statement_item", tid, year, 12,
                        ['income_tax_expense'], 'cumulative_amount', is_gaap)
        is_tax = is_d.get('income_tax_expense', 0)

        # Check if EIT tax matches nominal rate calculation
        exp_tp_nominal = round(taxable * rate, 2)
        # If IS tax differs from nominal rate, IS is the truth (e.g. preferential rates)
        uses_preferential = is_tax > 0 and abs(exp_tp_nominal - is_tax) > 10000

        if uses_preferential:
            # Align EIT to IS income_tax_expense (preferential rate scenario)
            if abs(tp - is_tax) > 1.0:
                updates['tax_payable'] = round(is_tax, 2)
                tp = round(is_tax, 2)
            if abs(atp - is_tax) > 1.0:
                updates['actual_tax_payable'] = round(is_tax, 2)
                atp = round(is_tax, 2)
            # Adjust taxable_income so that taxable_income * tax_rate = tax_payable
            if rate > 0:
                exp_taxable = round(tp / rate, 2)
                if abs(taxable - exp_taxable) > 1.0:
                    updates['taxable_income'] = exp_taxable
        else:
            # EIT-A03: tax_payable = taxable_income * tax_rate
            if abs(tp - exp_tp_nominal) > 1.0:
                updates['tax_payable'] = exp_tp_nominal
                tp = exp_tp_nominal
            # EIT-A04: actual_tax_payable = tax_payable - tax_credit_total
            exp_atp = round(tp - credit, 2)
            if abs(atp - exp_atp) > 1.0:
                updates['actual_tax_payable'] = exp_atp
                atp = exp_atp

        # EIT-A05: tax_payable_or_refund = actual_tax_payable - less_prepaid_tax
        exp_refund = round(atp - prepaid, 2)
        if abs(refund - exp_refund) > 1.0:
            updates['tax_payable_or_refund'] = exp_refund

        if updates:
            sets = ', '.join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE eit_annual_main SET {sets} WHERE filing_id=?",
                         list(updates.values()) + [r['filing_id']])
            fixed += 1

    conn.commit()
    print(f"  修复 {fixed} 条EIT年报记录")


# ============================================================
# Main
# ============================================================
def main():
    print(f"数据库: {DB_PATH}")
    conn = get_conn()
    try:
        # Phase 1: Fix internal consistency
        fix_account_balance(conn)
        fix_invoices(conn)
        fix_balance_sheet(conn)
        fix_income_statement(conn)
        fix_cash_flow(conn)
        fix_vat_general(conn)
        fix_eit_quarter(conn)
        # Phase 2: Cross-table alignment (handles continuity internally)
        fix_cross_table_cash(conn)
        fix_cross_table_eit(conn)
        fix_eit_annual(conn)
        print("\n=== 全部修复完成 ===")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
