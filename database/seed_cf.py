"""现金流量表种子数据：项目字典 + 同义词"""


def seed_cf_item_dict(cur):
    """现金流量表项目字典（CAS 35项 + SAS 22项）"""
    cas_items = [
        (1, 'operating_inflow_sales', '销售商品、提供劳务收到的现金', '经营活动'),
        (2, 'operating_inflow_tax_refund', '收到的税费返还', '经营活动'),
        (3, 'operating_inflow_other', '收到其他与经营活动有关的现金', '经营活动'),
        (4, 'operating_inflow_subtotal', '经营活动现金流入小计', '经营活动'),
        (5, 'operating_outflow_purchase', '购买商品、接受劳务支付的现金', '经营活动'),
        (6, 'operating_outflow_labor', '支付给职工以及为职工支付的现金', '经营活动'),
        (7, 'operating_outflow_tax', '支付的各项税费', '经营活动'),
        (8, 'operating_outflow_other', '支付其他与经营活动有关的现金', '经营活动'),
        (9, 'operating_outflow_subtotal', '经营活动现金流出小计', '经营活动'),
        (10, 'operating_net_cash', '经营活动产生的现金流量净额', '经营活动'),
        (11, 'investing_inflow_sale_investment', '收回投资收到的现金', '投资活动'),
        (12, 'investing_inflow_returns', '取得投资收益收到的现金', '投资活动'),
        (13, 'investing_inflow_disposal_assets', '处置固定资产、无形资产和其他长期资产收回的现金净额', '投资活动'),
        (14, 'investing_inflow_disposal_subsidiary', '处置子公司及其他营业单位收到的现金净额', '投资活动'),
        (15, 'investing_inflow_other', '收到其他与投资活动有关的现金', '投资活动'),
        (16, 'investing_inflow_subtotal', '投资活动现金流入小计', '投资活动'),
        (17, 'investing_outflow_purchase_assets', '购建固定资产、无形资产和其他长期资产支付的现金', '投资活动'),
        (18, 'investing_outflow_purchase_investment', '投资支付的现金', '投资活动'),
        (19, 'investing_outflow_acquire_subsidiary', '取得子公司及其他营业单位支付的现金净额', '投资活动'),
        (20, 'investing_outflow_other', '支付其他与投资活动有关的现金', '投资活动'),
        (21, 'investing_outflow_subtotal', '投资活动现金流出小计', '投资活动'),
        (22, 'investing_net_cash', '投资活动产生的现金流量净额', '投资活动'),
        (23, 'financing_inflow_capital', '吸收投资收到的现金', '筹资活动'),
        (24, 'financing_inflow_borrowing', '取得借款收到的现金', '筹资活动'),
        (25, 'financing_inflow_other', '收到其他与筹资活动有关的现金', '筹资活动'),
        (26, 'financing_inflow_subtotal', '筹资活动现金流入小计', '筹资活动'),
        (27, 'financing_outflow_debt_repayment', '偿还债务支付的现金', '筹资活动'),
        (28, 'financing_outflow_dividend_interest', '分配股利、利润或偿付利息支付的现金', '筹资活动'),
        (29, 'financing_outflow_other', '支付其他与筹资活动有关的现金', '筹资活动'),
        (30, 'financing_outflow_subtotal', '筹资活动现金流出小计', '筹资活动'),
        (31, 'financing_net_cash', '筹资活动产生的现金流量净额', '筹资活动'),
        (32, 'fx_impact', '汇率变动对现金及现金等价物的影响', '汇总'),
        (33, 'net_increase_cash', '现金及现金等价物净增加额', '汇总'),
        (34, 'beginning_cash', '期初现金及现金等价物余额', '汇总'),
        (35, 'ending_cash', '期末现金及现金等价物余额', '汇总'),
    ]
    for line, code, name, cat in cas_items:
        cur.execute(
            """INSERT OR REPLACE INTO fs_cash_flow_item_dict
            (gaap_type, item_code, item_name, line_number, category, display_order, is_total)
            VALUES ('CAS', ?, ?, ?, ?, ?, ?)""",
            (code, name, line, cat, line,
             1 if code.endswith('_subtotal') or code in ('operating_net_cash', 'investing_net_cash', 'financing_net_cash', 'net_increase_cash', 'ending_cash') else 0)
        )

    sas_items = [
        (1, 'operating_receipts_sales', '销售产成品、商品、提供劳务收到的现金', '经营活动'),
        (2, 'operating_receipts_other', '收到其他与经营活动有关的现金', '经营活动'),
        (3, 'operating_payments_purchase', '购买原材料、商品、接受劳务支付的现金', '经营活动'),
        (4, 'operating_payments_staff', '支付的职工薪酬', '经营活动'),
        (5, 'operating_payments_tax', '支付的税费', '经营活动'),
        (6, 'operating_payments_other', '支付其他与经营活动有关的现金', '经营活动'),
        (7, 'operating_net_cash', '经营活动产生的现金流量净额', '经营活动'),
        (8, 'investing_receipts_disposal_investment', '收回短期投资、长期债券投资和长期股权投资收到的现金', '投资活动'),
        (9, 'investing_receipts_returns', '取得投资收益收到的现金', '投资活动'),
        (10, 'investing_receipts_disposal_assets', '处置固定资产、无形资产和其他非流动资产收回的现金净额', '投资活动'),
        (11, 'investing_payments_purchase_investment', '短期投资、长期债券投资和长期股权投资支付的现金', '投资活动'),
        (12, 'investing_payments_purchase_assets', '购建固定资产、无形资产和其他非流动资产支付的现金', '投资活动'),
        (13, 'investing_net_cash', '投资活动产生的现金流量净额', '投资活动'),
        (14, 'financing_receipts_borrowing', '取得借款收到的现金', '筹资活动'),
        (15, 'financing_receipts_capital', '吸收投资者投资收到的现金', '筹资活动'),
        (16, 'financing_payments_debt_principal', '偿还借款本金支付的现金', '筹资活动'),
        (17, 'financing_payments_debt_interest', '偿还借款利息支付的现金', '筹资活动'),
        (18, 'financing_payments_dividend', '分配利润支付的现金', '筹资活动'),
        (19, 'financing_net_cash', '筹资活动产生的现金流量净额', '筹资活动'),
        (20, 'net_increase_cash', '现金净增加额', '汇总'),
        (21, 'beginning_cash', '期初现金余额', '汇总'),
        (22, 'ending_cash', '期末现金余额', '汇总'),
    ]
    for line, code, name, cat in sas_items:
        cur.execute(
            """INSERT OR REPLACE INTO fs_cash_flow_item_dict
            (gaap_type, item_code, item_name, line_number, category, display_order, is_total)
            VALUES ('SAS', ?, ?, ?, ?, ?, ?)""",
            (code, name, line, cat, line,
             1 if code in ('operating_net_cash', 'investing_net_cash', 'financing_net_cash', 'net_increase_cash', 'ending_cash') else 0)
        )
    print(f"  现金流量表项目字典: CAS {len(cas_items)}项 + SAS {len(sas_items)}项")


def seed_cf_synonyms(cur):
    """现金流量表同义词（CAS + SAS，gaap_type 替代 scope_view）"""
    # (phrase, column_name, priority, gaap_type)
    cas_synonyms = [
        # 经营活动 - 流入
        ('销售商品收到的现金', 'operating_inflow_sales', 10, 'CAS'),
        ('提供劳务收到的现金', 'operating_inflow_sales', 8, 'CAS'),
        ('经营收到的现金', 'operating_inflow_sales', 5, 'CAS'),
        ('税费返还', 'operating_inflow_tax_refund', 10, 'CAS'),
        ('收到的税费返还', 'operating_inflow_tax_refund', 10, 'CAS'),
        ('经营活动其他现金流入', 'operating_inflow_other', 8, 'CAS'),
        ('经营活动现金流入', 'operating_inflow_subtotal', 10, 'CAS'),
        ('经营活动现金流入小计', 'operating_inflow_subtotal', 10, 'CAS'),
        # 经营活动 - 流出
        ('购买商品支付的现金', 'operating_outflow_purchase', 10, 'CAS'),
        ('接受劳务支付的现金', 'operating_outflow_purchase', 8, 'CAS'),
        ('支付给职工的现金', 'operating_outflow_labor', 10, 'CAS'),
        ('职工薪酬现金', 'operating_outflow_labor', 8, 'CAS'),
        ('支付的各项税费', 'operating_outflow_tax', 10, 'CAS'),
        ('经营活动其他现金流出', 'operating_outflow_other', 8, 'CAS'),
        ('经营活动现金流出', 'operating_outflow_subtotal', 10, 'CAS'),
        ('经营活动现金流出小计', 'operating_outflow_subtotal', 10, 'CAS'),
        # 经营活动 - 净额
        ('经营活动现金流量净额', 'operating_net_cash', 10, 'CAS'),
        ('经营活动净现金', 'operating_net_cash', 8, 'CAS'),
        ('经营现金净额', 'operating_net_cash', 8, 'CAS'),
        ('经营现金流净额', 'operating_net_cash', 8, 'CAS'),
        ('经营现金流', 'operating_net_cash', 7, 'CAS'),
        ('经营现金流入', 'operating_inflow_subtotal', 8, 'CAS'),
        ('经营现金流出', 'operating_outflow_subtotal', 8, 'CAS'),
        # 投资活动 - 流入
        ('收回投资收到的现金', 'investing_inflow_sale_investment', 10, 'CAS'),
        ('取得投资收益收到的现金', 'investing_inflow_returns', 10, 'CAS'),
        ('投资收益现金', 'investing_inflow_returns', 8, 'CAS'),
        ('处置固定资产收回的现金', 'investing_inflow_disposal_assets', 10, 'CAS'),
        ('处置子公司收到的现金', 'investing_inflow_disposal_subsidiary', 10, 'CAS'),
        ('投资活动其他现金流入', 'investing_inflow_other', 8, 'CAS'),
        ('投资活动现金流入', 'investing_inflow_subtotal', 10, 'CAS'),
        ('投资活动现金流入小计', 'investing_inflow_subtotal', 10, 'CAS'),
        # 投资活动 - 流出
        ('购建固定资产支付的现金', 'investing_outflow_purchase_assets', 10, 'CAS'),
        ('投资支付的现金', 'investing_outflow_purchase_investment', 10, 'CAS'),
        ('取得子公司支付的现金', 'investing_outflow_acquire_subsidiary', 10, 'CAS'),
        ('投资活动其他现金流出', 'investing_outflow_other', 8, 'CAS'),
        ('投资活动现金流出', 'investing_outflow_subtotal', 10, 'CAS'),
        ('投资活动现金流出小计', 'investing_outflow_subtotal', 10, 'CAS'),
        # 投资活动 - 净额
        ('投资活动现金流量净额', 'investing_net_cash', 10, 'CAS'),
        ('投资活动净现金', 'investing_net_cash', 8, 'CAS'),
        ('投资现金净额', 'investing_net_cash', 8, 'CAS'),
        ('投资现金流净额', 'investing_net_cash', 8, 'CAS'),
        ('投资现金流', 'investing_net_cash', 7, 'CAS'),
        ('投资现金流入', 'investing_inflow_subtotal', 8, 'CAS'),
        ('投资现金流出', 'investing_outflow_subtotal', 8, 'CAS'),
        # 筹资活动 - 流入
        ('吸收投资收到的现金', 'financing_inflow_capital', 10, 'CAS'),
        ('取得借款收到的现金', 'financing_inflow_borrowing', 10, 'CAS'),
        ('借款收到的现金', 'financing_inflow_borrowing', 8, 'CAS'),
        ('筹资活动其他现金流入', 'financing_inflow_other', 8, 'CAS'),
        ('筹资活动现金流入', 'financing_inflow_subtotal', 10, 'CAS'),
        ('筹资活动现金流入小计', 'financing_inflow_subtotal', 10, 'CAS'),
        # 筹资活动 - 流出
        ('偿还债务支付的现金', 'financing_outflow_debt_repayment', 10, 'CAS'),
        ('分配股利支付的现金', 'financing_outflow_dividend_interest', 10, 'CAS'),
        ('偿付利息支付的现金', 'financing_outflow_dividend_interest', 8, 'CAS'),
        ('筹资活动其他现金流出', 'financing_outflow_other', 8, 'CAS'),
        ('筹资活动现金流出', 'financing_outflow_subtotal', 10, 'CAS'),
        ('筹资活动现金流出小计', 'financing_outflow_subtotal', 10, 'CAS'),
        # 筹资活动 - 净额
        ('筹资活动现金流量净额', 'financing_net_cash', 10, 'CAS'),
        ('筹资活动净现金', 'financing_net_cash', 8, 'CAS'),
        ('筹资现金净额', 'financing_net_cash', 8, 'CAS'),
        ('筹资现金流净额', 'financing_net_cash', 8, 'CAS'),
        ('筹资现金流', 'financing_net_cash', 7, 'CAS'),
        ('筹资现金流入', 'financing_inflow_subtotal', 8, 'CAS'),
        ('筹资现金流出', 'financing_outflow_subtotal', 8, 'CAS'),
        ('现金流净额', 'net_increase_cash', 7, 'CAS'),
        # 汇总
        ('汇率变动影响', 'fx_impact', 10, 'CAS'),
        ('汇率变动对现金的影响', 'fx_impact', 10, 'CAS'),
        ('现金净增加额', 'net_increase_cash', 10, 'CAS'),
        ('现金及现金等价物净增加额', 'net_increase_cash', 10, 'CAS'),
        ('期初现金', 'beginning_cash', 10, 'CAS'),
        ('期初现金余额', 'beginning_cash', 10, 'CAS'),
        ('期初现金及现金等价物余额', 'beginning_cash', 10, 'CAS'),
        ('期末现金', 'ending_cash', 10, 'CAS'),
        ('期末现金余额', 'ending_cash', 10, 'CAS'),
        ('期末现金及现金等价物余额', 'ending_cash', 10, 'CAS'),
    ]

    sas_synonyms = [
        # 经营活动
        ('销售产成品收到的现金', 'operating_receipts_sales', 10, 'SAS'),
        ('销售商品收到的现金', 'operating_receipts_sales', 8, 'SAS'),
        ('经营收到的现金', 'operating_receipts_sales', 5, 'SAS'),
        ('经营活动其他现金流入', 'operating_receipts_other', 8, 'SAS'),
        ('购买原材料支付的现金', 'operating_payments_purchase', 10, 'SAS'),
        ('购买商品支付的现金', 'operating_payments_purchase', 8, 'SAS'),
        ('支付的职工薪酬', 'operating_payments_staff', 10, 'SAS'),
        ('职工薪酬现金', 'operating_payments_staff', 8, 'SAS'),
        ('支付的税费', 'operating_payments_tax', 10, 'SAS'),
        ('经营活动其他现金流出', 'operating_payments_other', 8, 'SAS'),
        ('经营活动现金流量净额', 'operating_net_cash', 10, 'SAS'),
        ('经营活动净现金', 'operating_net_cash', 8, 'SAS'),
        ('经营现金净额', 'operating_net_cash', 8, 'SAS'),
        ('经营现金流净额', 'operating_net_cash', 8, 'SAS'),
        ('经营现金流', 'operating_net_cash', 7, 'SAS'),
        ('经营现金流入', 'operating_inflow_subtotal', 8, 'SAS'),
        ('经营现金流出', 'operating_outflow_subtotal', 8, 'SAS'),
        # 投资活动
        ('收回投资收到的现金', 'investing_receipts_disposal_investment', 10, 'SAS'),
        ('取得投资收益收到的现金', 'investing_receipts_returns', 10, 'SAS'),
        ('处置固定资产收回的现金', 'investing_receipts_disposal_assets', 10, 'SAS'),
        ('投资支付的现金', 'investing_payments_purchase_investment', 10, 'SAS'),
        ('购建固定资产支付的现金', 'investing_payments_purchase_assets', 10, 'SAS'),
        ('投资活动现金流量净额', 'investing_net_cash', 10, 'SAS'),
        ('投资活动净现金', 'investing_net_cash', 8, 'SAS'),
        ('投资现金净额', 'investing_net_cash', 8, 'SAS'),
        ('投资现金流净额', 'investing_net_cash', 8, 'SAS'),
        ('投资现金流', 'investing_net_cash', 7, 'SAS'),
        ('投资现金流入', 'investing_inflow_subtotal', 8, 'SAS'),
        ('投资现金流出', 'investing_outflow_subtotal', 8, 'SAS'),
        # 筹资活动
        ('取得借款收到的现金', 'financing_receipts_borrowing', 10, 'SAS'),
        ('借款收到的现金', 'financing_receipts_borrowing', 8, 'SAS'),
        ('吸收投资者投资收到的现金', 'financing_receipts_capital', 10, 'SAS'),
        ('偿还借款本金', 'financing_payments_debt_principal', 10, 'SAS'),
        ('偿还借款利息', 'financing_payments_debt_interest', 10, 'SAS'),
        ('分配利润支付的现金', 'financing_payments_dividend', 10, 'SAS'),
        ('筹资活动现金流量净额', 'financing_net_cash', 10, 'SAS'),
        ('筹资活动净现金', 'financing_net_cash', 8, 'SAS'),
        ('筹资现金净额', 'financing_net_cash', 8, 'SAS'),
        ('筹资现金流净额', 'financing_net_cash', 8, 'SAS'),
        ('筹资现金流', 'financing_net_cash', 7, 'SAS'),
        ('筹资现金流入', 'financing_inflow_subtotal', 8, 'SAS'),
        ('筹资现金流出', 'financing_outflow_subtotal', 8, 'SAS'),
        ('现金流净额', 'net_increase_cash', 7, 'SAS'),
        # 汇总
        ('现金净增加额', 'net_increase_cash', 10, 'SAS'),
        ('期初现金余额', 'beginning_cash', 10, 'SAS'),
        ('期初现金', 'beginning_cash', 8, 'SAS'),
        ('期末现金余额', 'ending_cash', 10, 'SAS'),
        ('期末现金', 'ending_cash', 8, 'SAS'),
    ]

    for phrase, col, pri, gaap in cas_synonyms:
        cur.execute(
            "INSERT OR IGNORE INTO fs_cash_flow_synonyms (phrase, column_name, priority, gaap_type) VALUES (?,?,?,?)",
            (phrase, col, pri, gaap)
        )
    for phrase, col, pri, gaap in sas_synonyms:
        cur.execute(
            "INSERT OR IGNORE INTO fs_cash_flow_synonyms (phrase, column_name, priority, gaap_type) VALUES (?,?,?,?)",
            (phrase, col, pri, gaap)
        )
    count = cur.execute("SELECT COUNT(*) FROM fs_cash_flow_synonyms").fetchone()[0]
    print(f"  现金流量表同义词: {count} 条")
