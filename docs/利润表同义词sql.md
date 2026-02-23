```
-- 企业会计准则（cas）同义词插入语句
INSERT INTO fs_income_statement_synonyms (phrase, column_name, gaap_type, priority) VALUES
-- 营业收入
('营业收入', 'operating_revenue_current', 'cas', 2),
('营业收入本期', 'operating_revenue_current', 'cas', 2),
('营业收入累计', 'operating_revenue_cumulative', 'cas', 2),
('营收', 'operating_revenue_current', 'cas', 2),
('经营收入', 'operating_revenue_current', 'cas', 2),
('主营收入', 'operating_revenue_current', 'cas', 2),
('第1行', 'operating_revenue_current', 'cas', 3),
('1行', 'operating_revenue_current', 'cas', 3),
('第一行', 'operating_revenue_current', 'cas', 3),

-- 营业成本
('营业成本', 'operating_cost_current', 'cas', 2),
('营业成本本期', 'operating_cost_current', 'cas', 2),
('营业成本累计', 'operating_cost_cumulative', 'cas', 2),
('经营成本', 'operating_cost_current', 'cas', 2),
('主营成本', 'operating_cost_current', 'cas', 2),
('成本', 'operating_cost_current', 'cas', 2),
('减：营业成本', 'operating_cost_current', 'cas', 2),
('第2行', 'operating_cost_current', 'cas', 3),
('2行', 'operating_cost_current', 'cas', 3),
('第二行', 'operating_cost_current', 'cas', 3),

-- 税金及附加
('税金及附加', 'taxes_and_surcharges_current', 'cas', 2),
('税费及附加', 'taxes_and_surcharges_current', 'cas', 2),
('税金附加', 'taxes_and_surcharges_current', 'cas', 2),
('附加税', 'taxes_and_surcharges_current', 'cas', 2),
('税及附加', 'taxes_and_surcharges_current', 'cas', 2),
('第3行', 'taxes_and_surcharges_current', 'cas', 3),
('3行', 'taxes_and_surcharges_current', 'cas', 3),
('第三行', 'taxes_and_surcharges_current', 'cas', 3),

-- 销售费用
('销售费用', 'selling_expense_current', 'cas', 2),
('销售费', 'selling_expense_current', 'cas', 2),
('营销费用', 'selling_expense_current', 'cas', 2),
('营销费', 'selling_expense_current', 'cas', 2),
('售卖费用', 'selling_expense_current', 'cas', 2),
('第4行', 'selling_expense_current', 'cas', 3),
('4行', 'selling_expense_current', 'cas', 3),
('第四行', 'selling_expense_current', 'cas', 3),

-- 管理费用
('管理费用', 'administrative_expense_current', 'cas', 2),
('管理费', 'administrative_expense_current', 'cas', 2),
('管理开支', 'administrative_expense_current', 'cas', 2),
('行政费用', 'administrative_expense_current', 'cas', 2),
('行政费', 'administrative_expense_current', 'cas', 2),
('第5行', 'administrative_expense_current', 'cas', 3),
('5行', 'administrative_expense_current', 'cas', 3),
('第五行', 'administrative_expense_current', 'cas', 3),

-- 研发费用
('研发费用', 'rd_expense_current', 'cas', 2),
('研发费', 'rd_expense_current', 'cas', 2),
('研发支出', 'rd_expense_current', 'cas', 2),
('研发投入', 'rd_expense_current', 'cas', 2),
('研究开发费用', 'rd_expense_current', 'cas', 2),
('研发开销', 'rd_expense_current', 'cas', 2),
('第6行', 'rd_expense_current', 'cas', 3),
('6行', 'rd_expense_current', 'cas', 3),
('第六行', 'rd_expense_current', 'cas', 3),

-- 财务费用
('财务费用', 'financial_expense_current', 'cas', 2),
('财务费', 'financial_expense_current', 'cas', 2),
('财务开支', 'financial_expense_current', 'cas', 2),
('筹资费用', 'financial_expense_current', 'cas', 2),
('资金费用', 'financial_expense_current', 'cas', 2),
('第7行', 'financial_expense_current', 'cas', 3),
('7行', 'financial_expense_current', 'cas', 3),
('第七行', 'financial_expense_current', 'cas', 3),

-- 利息费用
('利息费用', 'interest_expense_current', 'cas', 2),
('利息费', 'interest_expense_current', 'cas', 2),
('利息支出', 'interest_expense_current', 'cas', 2),
('利息开支', 'interest_expense_current', 'cas', 2),
('借款利息', 'interest_expense_current', 'cas', 2),
('第8行', 'interest_expense_current', 'cas', 3),
('8行', 'interest_expense_current', 'cas', 3),
('第八行', 'interest_expense_current', 'cas', 3),

-- 利息收入
('利息收入', 'interest_income_current', 'cas', 2),
('利息收益', 'interest_income_current', 'cas', 2),
('存款利息', 'interest_income_current', 'cas', 2),
('利息所得', 'interest_income_current', 'cas', 2),
('利息回款', 'interest_income_current', 'cas', 2),
('第9行', 'interest_income_current', 'cas', 3),
('9行', 'interest_income_current', 'cas', 3),
('第九行', 'interest_income_current', 'cas', 3),

-- 其他收益
('其他收益', 'other_gains_current', 'cas', 2),
('其他收益收入', 'other_gains_current', 'cas', 2),
('其他利得', 'other_gains_current', 'cas', 2),
('其他盈利', 'other_gains_current', 'cas', 2),
('其他收益项', 'other_gains_current', 'cas', 2),
('第10行', 'other_gains_current', 'cas', 3),
('10行', 'other_gains_current', 'cas', 3),
('第十行', 'other_gains_current', 'cas', 3),

-- 投资收益
('投资收益', 'investment_income_current', 'cas', 2),
('投资收益（损失以“－”号填列）', 'investment_income_current', 'cas', 2),
('投资利润', 'investment_income_current', 'cas', 2),
('投资回报', 'investment_income_current', 'cas', 2),
('投资所得', 'investment_income_current', 'cas', 2),
('理财收益', 'investment_income_current', 'cas', 2),
('第11行', 'investment_income_current', 'cas', 3),
('11行', 'investment_income_current', 'cas', 3),
('第十一行', 'investment_income_current', 'cas', 3),

-- 对联营企业和合营企业的投资收益
('对联营企业和合营企业的投资收益', 'investment_income_associates_current', 'cas', 2),
('联营合营企业投资收益', 'investment_income_associates_current', 'cas', 2),
('联营企业投资收益', 'investment_income_associates_current', 'cas', 2),
('合营企业投资收益', 'investment_income_associates_current', 'cas', 2),
('联营合营收益', 'investment_income_associates_current', 'cas', 2),
('第12行', 'investment_income_associates_current', 'cas', 3),
('12行', 'investment_income_associates_current', 'cas', 3),
('第十二行', 'investment_income_associates_current', 'cas', 3),

-- 以摊余成本计量的金融资产终止确认收益
('以摊余成本计量的金融资产终止确认收益', 'amortized_cost_termination_income_current', 'cas', 2),
('摊余成本金融资产终止确认收益', 'amortized_cost_termination_income_current', 'cas', 2),
('金融资产终止确认收益', 'amortized_cost_termination_income_current', 'cas', 2),
('摊余成本资产终止收益', 'amortized_cost_termination_income_current', 'cas', 2),
('金融资产终止收益', 'amortized_cost_termination_income_current', 'cas', 2),
('第13行', 'amortized_cost_termination_income_current', 'cas', 3),
('13行', 'amortized_cost_termination_income_current', 'cas', 3),
('第十三行', 'amortized_cost_termination_income_current', 'cas', 3),

-- 净敞口套期收益
('净敞口套期收益', 'net_exposure_hedge_income_current', 'cas', 2),
('套期收益', 'net_exposure_hedge_income_current', 'cas', 2),
('净敞口套期利得', 'net_exposure_hedge_income_current', 'cas', 2),
('套期盈利', 'net_exposure_hedge_income_current', 'cas', 2),
('敞口套期收益', 'net_exposure_hedge_income_current', 'cas', 2),
('第14行', 'net_exposure_hedge_income_current', 'cas', 3),
('14行', 'net_exposure_hedge_income_current', 'cas', 3),
('第十四行', 'net_exposure_hedge_income_current', 'cas', 3),

-- 公允价值变动收益
('公允价值变动收益', 'fair_value_change_income_current', 'cas', 2),
('公允价变动收益', 'fair_value_change_income_current', 'cas', 2),
('公允价值变动利得', 'fair_value_change_income_current', 'cas', 2),
('公允价变动利得', 'fair_value_change_income_current', 'cas', 2),
('市价变动收益', 'fair_value_change_income_current', 'cas', 2),
('第15行', 'fair_value_change_income_current', 'cas', 3),
('15行', 'fair_value_change_income_current', 'cas', 3),
('第十五行', 'fair_value_change_income_current', 'cas', 3),

-- 信用减值损失
('信用减值损失', 'credit_impairment_loss_current', 'cas', 2),
('信用减值亏损', 'credit_impairment_loss_current', 'cas', 2),
('坏账减值损失', 'credit_impairment_loss_current', 'cas', 2),
('信用损失', 'credit_impairment_loss_current', 'cas', 2),
('减值损失（信用）', 'credit_impairment_loss_current', 'cas', 2),
('第16行', 'credit_impairment_loss_current', 'cas', 3),
('16行', 'credit_impairment_loss_current', 'cas', 3),
('第十六行', 'credit_impairment_loss_current', 'cas', 3),

-- 资产减值损失
('资产减值损失', 'asset_impairment_loss_current', 'cas', 2),
('资产减值亏损', 'asset_impairment_loss_current', 'cas', 2),
('资产减值', 'asset_impairment_loss_current', 'cas', 2),
('减值损失（资产）', 'asset_impairment_loss_current', 'cas', 2),
('资产跌价损失', 'asset_impairment_loss_current', 'cas', 2),
('第17行', 'asset_impairment_loss_current', 'cas', 3),
('17行', 'asset_impairment_loss_current', 'cas', 3),
('第十七行', 'asset_impairment_loss_current', 'cas', 3),

-- 资产处置收益
('资产处置收益', 'asset_disposal_gains_current', 'cas', 2),
('资产处置利得', 'asset_disposal_gains_current', 'cas', 2),
('处置资产收益', 'asset_disposal_gains_current', 'cas', 2),
('资产出售收益', 'asset_disposal_gains_current', 'cas', 2),
('固定资产处置收益', 'asset_disposal_gains_current', 'cas', 2),
('第18行', 'asset_disposal_gains_current', 'cas', 3),
('18行', 'asset_disposal_gains_current', 'cas', 3),
('第十八行', 'asset_disposal_gains_current', 'cas', 3),

-- 营业利润
('营业利润', 'operating_profit_current', 'cas', 2),
('营业利润（亏损以“－”号填列）', 'operating_profit_current', 'cas', 2),
('营业利润本期', 'operating_profit_current', 'cas', 2),
('营业利润累计', 'operating_profit_cumulative', 'cas', 2),
('经营利润', 'operating_profit_current', 'cas', 2),
('主营利润', 'operating_profit_current', 'cas', 2),
('营业盈利', 'operating_profit_current', 'cas', 2),
('第19行', 'operating_profit_current', 'cas', 3),
('19行', 'operating_profit_current', 'cas', 3),
('第十九行', 'operating_profit_current', 'cas', 3),

-- 营业外收入
('营业外收入', 'non_operating_income_current', 'cas', 2),
('非营业收入', 'non_operating_income_current', 'cas', 2),
('营业外收益', 'non_operating_income_current', 'cas', 2),
('非经营收入', 'non_operating_income_current', 'cas', 2),
('额外收入', 'non_operating_income_current', 'cas', 2),
('第20行', 'non_operating_income_current', 'cas', 3),
('20行', 'non_operating_income_current', 'cas', 3),
('第二十行', 'non_operating_income_current', 'cas', 3),

-- 营业外支出
('营业外支出', 'non_operating_expense_current', 'cas', 2),
('非营业支出', 'non_operating_expense_current', 'cas', 2),
('营业外开销', 'non_operating_expense_current', 'cas', 2),
('非经营支出', 'non_operating_expense_current', 'cas', 2),
('额外支出', 'non_operating_expense_current', 'cas', 2),
('第21行', 'non_operating_expense_current', 'cas', 3),
('21行', 'non_operating_expense_current', 'cas', 3),
('第二十一行', 'non_operating_expense_current', 'cas', 3),

-- 利润总额
('利润总额', 'total_profit_current', 'cas', 2),
('利润总额（亏损总额以“－”号填列）', 'total_profit_current', 'cas', 2),
('税前利润', 'total_profit_current', 'cas', 2),
('总利润', 'total_profit_current', 'cas', 2),
('利润总和', 'total_profit_current', 'cas', 2),
('第22行', 'total_profit_current', 'cas', 3),
('22行', 'total_profit_current', 'cas', 3),
('第二十二行', 'total_profit_current', 'cas', 3),

-- 所得税费用
('所得税费用', 'income_tax_expense_current', 'cas', 2),
('所得税', 'income_tax_expense_current', 'cas', 2),
('所得税费', 'income_tax_expense_current', 'cas', 2),
('企业所得税', 'income_tax_expense_current', 'cas', 2),
('所得税开支', 'income_tax_expense_current', 'cas', 2),
('第23行', 'income_tax_expense_current', 'cas', 3),
('23行', 'income_tax_expense_current', 'cas', 3),
('第二十三行', 'income_tax_expense_current', 'cas', 3),

-- 净利润
('净利润', 'net_profit_current', 'cas', 2),
('净利润（净亏损以“－”号填列）', 'net_profit_current', 'cas', 2),
('净利润本期', 'net_profit_current', 'cas', 2),
('净利润累计', 'net_profit_cumulative', 'cas', 2),
('纯利润', 'net_profit_current', 'cas', 2),
('税后利润', 'net_profit_current', 'cas', 2),
('净利', 'net_profit_current', 'cas', 2),
('第24行', 'net_profit_current', 'cas', 3),
('24行', 'net_profit_current', 'cas', 3),
('第二十四行', 'net_profit_current', 'cas', 3),

-- 持续经营净利润
('持续经营净利润', 'continued_ops_net_profit_current', 'cas', 2),
('持续经营净利', 'continued_ops_net_profit_current', 'cas', 2),
('持续经营利润', 'continued_ops_net_profit_current', 'cas', 2),
('持续经营纯利润', 'continued_ops_net_profit_current', 'cas', 2),
('（一）持续经营净利润', 'continued_ops_net_profit_current', 'cas', 2),
('第25行', 'continued_ops_net_profit_current', 'cas', 3),
('25行', 'continued_ops_net_profit_current', 'cas', 3),
('第二十五行', 'continued_ops_net_profit_current', 'cas', 3),

-- 终止经营净利润
('终止经营净利润', 'discontinued_ops_net_profit_current', 'cas', 2),
('终止经营净利', 'discontinued_ops_net_profit_current', 'cas', 2),
('终止经营利润', 'discontinued_ops_net_profit_current', 'cas', 2),
('终止经营纯利润', 'discontinued_ops_net_profit_current', 'cas', 2),
('（二）终止经营净利润', 'discontinued_ops_net_profit_current', 'cas', 2),
('第26行', 'discontinued_ops_net_profit_current', 'cas', 3),
('26行', 'discontinued_ops_net_profit_current', 'cas', 3),
('第二十六行', 'discontinued_ops_net_profit_current', 'cas', 3),

-- 其他综合收益的税后净额
('其他综合收益', 'other_comprehensive_income_net_current', 'cas', 2),
('其他综合收益的税后净额', 'other_comprehensive_income_net_current', 'cas', 2),
('其他综合收益净额', 'other_comprehensive_income_net_current', 'cas', 2),
('综合收益（其他）', 'other_comprehensive_income_net_current', 'cas', 2),
('其他综合净利', 'other_comprehensive_income_net_current', 'cas', 2),
('五、其他综合收益的税后净额', 'other_comprehensive_income_net_current', 'cas', 2),
('第27行', 'other_comprehensive_income_net_current', 'cas', 3),
('27行', 'other_comprehensive_income_net_current', 'cas', 3),
('第二十七行', 'other_comprehensive_income_net_current', 'cas', 3),

-- 不能重分类进损益的其他综合收益
('不能重分类进损益的其他综合收益', 'oci_non_reclass_current', 'cas', 2),
('不可重分类其他综合收益', 'oci_non_reclass_current', 'cas', 2),
('非重分类其他综合收益', 'oci_non_reclass_current', 'cas', 2),
('（一）不能重分类进损益的其他综合收益', 'oci_non_reclass_current', 'cas', 2),
('不可转损益其他综合收益', 'oci_non_reclass_current', 'cas', 2),
('第28行', 'oci_non_reclass_current', 'cas', 3),
('28行', 'oci_non_reclass_current', 'cas', 3),
('第二十八行', 'oci_non_reclass_current', 'cas', 3),

-- 重新计量设定受益计划变动额
('重新计量设定受益计划变动额', 'oci_remeasurement_defined_benefit_current', 'cas', 2),
('设定受益计划变动额', 'oci_remeasurement_defined_benefit_current', 'cas', 2),
('受益计划重新计量变动', 'oci_remeasurement_defined_benefit_current', 'cas', 2),
('1.重新计量设定受益计划变动额', 'oci_remeasurement_defined_benefit_current', 'cas', 2),
('设定受益计划调整额', 'oci_remeasurement_defined_benefit_current', 'cas', 2),
('第29行', 'oci_remeasurement_defined_benefit_current', 'cas', 3),
('29行', 'oci_remeasurement_defined_benefit_current', 'cas', 3),
('第二十九行', 'oci_remeasurement_defined_benefit_current', 'cas', 3),

-- 权益法下不能转损益的其他综合收益
('权益法下不能转损益的其他综合收益', 'oci_eq_method_non_reclass_current', 'cas', 2),
('权益法不可转损益其他综合收益', 'oci_eq_method_non_reclass_current', 'cas', 2),
('权益法非转损益其他综合收益', 'oci_eq_method_non_reclass_current', 'cas', 2),
('2.权益法下不能转损益的其他综合收益', 'oci_eq_method_non_reclass_current', 'cas', 2),
('权益法不可重分类收益', 'oci_eq_method_non_reclass_current', 'cas', 2),
('第30行', 'oci_eq_method_non_reclass_current', 'cas', 3),
('30行', 'oci_eq_method_non_reclass_current', 'cas', 3),
('第三十行', 'oci_eq_method_non_reclass_current', 'cas', 3),

-- 其他权益工具投资公允价值变动
('其他权益工具投资公允价值变动', 'oci_fair_value_change_other_equity_current', 'cas', 2),
('权益工具投资公允价变动', 'oci_fair_value_change_other_equity_current', 'cas', 2),
('其他权益工具公允价变动', 'oci_fair_value_change_other_equity_current', 'cas', 2),
('3.其他权益工具投资公允价值变动', 'oci_fair_value_change_other_equity_current', 'cas', 2),
('权益工具市价变动', 'oci_fair_value_change_other_equity_current', 'cas', 2),
('第31行', 'oci_fair_value_change_other_equity_current', 'cas', 3),
('31行', 'oci_fair_value_change_other_equity_current', 'cas', 3),
('第三十一行', 'oci_fair_value_change_other_equity_current', 'cas', 3),

-- 企业自身信用风险公允价值变动
('企业自身信用风险公允价值变动', 'oci_credit_risk_change_current', 'cas', 2),
('自身信用风险公允价变动', 'oci_credit_risk_change_current', 'cas', 2),
('信用风险公允价值变动', 'oci_credit_risk_change_current', 'cas', 2),
('4.企业自身信用风险公允价值变动', 'oci_credit_risk_change_current', 'cas', 2),
('自身信用风险变动', 'oci_credit_risk_change_current', 'cas', 2),
('第32行', 'oci_credit_risk_change_current', 'cas', 3),
('32行', 'oci_credit_risk_change_current', 'cas', 3),
('第三十二行', 'oci_credit_risk_change_current', 'cas', 3),

-- 将重分类进损益的其他综合收益
('将重分类进损益的其他综合收益', 'oci_reclass_current', 'cas', 2),
('可重分类其他综合收益', 'oci_reclass_current', 'cas', 2),
('重分类进损益收益', 'oci_reclass_current', 'cas', 2),
('（二）将重分类进损益的其他综合收益', 'oci_reclass_current', 'cas', 2),
('可转损益其他综合收益', 'oci_reclass_current', 'cas', 2),
('第33行', 'oci_reclass_current', 'cas', 3),
('33行', 'oci_reclass_current', 'cas', 3),
('第三十三行', 'oci_reclass_current', 'cas', 3),

-- 权益法下可转损益的其他综合收益
('权益法下可转损益的其他综合收益', 'oci_eq_method_reclass_current', 'cas', 2),
('权益法可转损益其他综合收益', 'oci_eq_method_reclass_current', 'cas', 2),
('权益法重分类收益', 'oci_eq_method_reclass_current', 'cas', 2),
('1.权益法下可转损益的其他综合收益', 'oci_eq_method_reclass_current', 'cas', 2),
('权益法可重分类收益', 'oci_eq_method_reclass_current', 'cas', 2),
('第34行', 'oci_eq_method_reclass_current', 'cas', 3),
('34行', 'oci_eq_method_reclass_current', 'cas', 3),
('第三十四行', 'oci_eq_method_reclass_current', 'cas', 3),

-- 其他债权投资公允价值变动
('其他债权投资公允价值变动', 'oci_fair_value_change_other_debt_current', 'cas', 2),
('债权投资公允价变动', 'oci_fair_value_change_other_debt_current', 'cas', 2),
('其他债权公允价变动', 'oci_fair_value_change_other_debt_current', 'cas', 2),
('2.其他债权投资公允价值变动', 'oci_fair_value_change_other_debt_current', 'cas', 2),
('债权投资市价变动', 'oci_fair_value_change_other_debt_current', 'cas', 2),
('第35行', 'oci_fair_value_change_other_debt_current', 'cas', 3),
('35行', 'oci_fair_value_change_other_debt_current', 'cas', 3),
('第三十五行', 'oci_fair_value_change_other_debt_current', 'cas', 3),

-- 金融资产重分类计入其他综合收益的金额
('金融资产重分类计入其他综合收益的金额', 'oci_reclassification_adjustment_current', 'cas', 2),
('金融资产重分类其他综合收益', 'oci_reclassification_adjustment_current', 'cas', 2),
('资产重分类综合收益', 'oci_reclassification_adjustment_current', 'cas', 2),
('3.金融资产重分类计入其他综合收益的金额', 'oci_reclassification_adjustment_current', 'cas', 2),
('重分类综合收益金额', 'oci_reclassification_adjustment_current', 'cas', 2),
('第36行', 'oci_reclassification_adjustment_current', 'cas', 3),
('36行', 'oci_reclassification_adjustment_current', 'cas', 3),
('第三十六行', 'oci_reclassification_adjustment_current', 'cas', 3),

-- 其他债权投资信用减值准备
('其他债权投资信用减值准备', 'oci_credit_impairment_other_debt_current', 'cas', 2),
('债权投资信用减值准备', 'oci_credit_impairment_other_debt_current', 'cas', 2),
('其他债权减值准备', 'oci_credit_impairment_other_debt_current', 'cas', 2),
('4.其他债权投资信用减值准备', 'oci_credit_impairment_other_debt_current', 'cas', 2),
('债权投资减值准备', 'oci_credit_impairment_other_debt_current', 'cas', 2),
('第37行', 'oci_credit_impairment_other_debt_current', 'cas', 3),
('37行', 'oci_credit_impairment_other_debt_current', 'cas', 3),
('第三十七行', 'oci_credit_impairment_other_debt_current', 'cas', 3),

-- 现金流量套期储备
('现金流量套期储备', 'oci_cash_flow_hedge_reserve_current', 'cas', 2),
('现金流套期储备', 'oci_cash_flow_hedge_reserve_current', 'cas', 2),
('套期储备（现金流量）', 'oci_cash_flow_hedge_reserve_current', 'cas', 2),
('5.现金流量套期储备', 'oci_cash_flow_hedge_reserve_current', 'cas', 2),
('现金流套期准备金', 'oci_cash_flow_hedge_reserve_current', 'cas', 2),
('第38行', 'oci_cash_flow_hedge_reserve_current', 'cas', 3),
('38行', 'oci_cash_flow_hedge_reserve_current', 'cas', 3),
('第三十八行', 'oci_cash_flow_hedge_reserve_current', 'cas', 3),

-- 外币财务报表折算差额
('外币财务报表折算差额', 'oci_foreign_currency_translation_current', 'cas', 2),
('外币报表折算差额', 'oci_foreign_currency_translation_current', 'cas', 2),
('外币折算差额', 'oci_foreign_currency_translation_current', 'cas', 2),
('6.外币财务报表折算差额', 'oci_foreign_currency_translation_current', 'cas', 2),
('外币报表差额', 'oci_foreign_currency_translation_current', 'cas', 2),
('第39行', 'oci_foreign_currency_translation_current', 'cas', 3),
('39行', 'oci_foreign_currency_translation_current', 'cas', 3),
('第三十九行', 'oci_foreign_currency_translation_current', 'cas', 3),

-- 综合收益总额
('综合收益总额', 'total_comprehensive_income_current', 'cas', 2),
('综合收益合计', 'total_comprehensive_income_current', 'cas', 2),
('总综合收益', 'total_comprehensive_income_current', 'cas', 2),
('六、综合收益总额', 'total_comprehensive_income_current', 'cas', 2),
('综合收益总计', 'total_comprehensive_income_current', 'cas', 2),
('第40行', 'total_comprehensive_income_current', 'cas', 3),
('40行', 'total_comprehensive_income_current', 'cas', 3),
('第四十行', 'total_comprehensive_income_current', 'cas', 3),

-- 基本每股收益
('基本每股收益', 'eps_basic_current', 'cas', 2),
('基本每股盈利', 'eps_basic_current', 'cas', 2),
('基本EPS', 'eps_basic_current', 'cas', 2),
('(一) 基本每股收益', 'eps_basic_current', 'cas', 2),
('每股基本收益', 'eps_basic_current', 'cas', 2),
('第42行', 'eps_basic_current', 'cas', 3),
('42行', 'eps_basic_current', 'cas', 3),
('第四十二行', 'eps_basic_current', 'cas', 3),

-- 稀释每股收益
('稀释每股收益', 'eps_diluted_current', 'cas', 2),
('稀释每股盈利', 'eps_diluted_current', 'cas', 2),
('稀释EPS', 'eps_diluted_current', 'cas', 2),
('(二) 稀释每股收益', 'eps_diluted_current', 'cas', 2),
('每股稀释收益', 'eps_diluted_current', 'cas', 2),
('第43行', 'eps_diluted_current', 'cas', 3),
('43行', 'eps_diluted_current', 'cas', 3),
('第四十三行', 'eps_diluted_current', 'cas', 3);

-- 小企业会计准则（sas）同义词插入语句
INSERT INTO fs_income_statement_synonyms (phrase, column_name, gaap_type, priority) VALUES
-- 营业收入
('营业收入', 'operating_revenue_current', 'sas', 2),
('营业收入本期', 'operating_revenue_current', 'sas', 2),
('营业收入累计', 'operating_revenue_cumulative', 'sas', 2),
('营收', 'operating_revenue_current', 'sas', 2),
('经营收入', 'operating_revenue_current', 'sas', 2),
('主营收入', 'operating_revenue_current', 'sas', 2),
('一、营业收入', 'operating_revenue_current', 'sas', 2),
('第1行', 'operating_revenue_current', 'sas', 3),
('1行', 'operating_revenue_current', 'sas', 3),
('第一行', 'operating_revenue_current', 'sas', 3),

-- 营业成本
('营业成本', 'operating_cost_current', 'sas', 2),
('减：营业成本', 'operating_cost_current', 'sas', 2),
('经营成本', 'operating_cost_current', 'sas', 2),
('主营成本', 'operating_cost_current', 'sas', 2),
('成本', 'operating_cost_current', 'sas', 2),
('第2行', 'operating_cost_current', 'sas', 3),
('2行', 'operating_cost_current', 'sas', 3),
('第二行', 'operating_cost_current', 'sas', 3),

-- 税金及附加
('税金及附加', 'taxes_and_surcharges_current', 'sas', 2),
('税费及附加', 'taxes_and_surcharges_current', 'sas', 2),
('税金附加', 'taxes_and_surcharges_current', 'sas', 2),
('附加税', 'taxes_and_surcharges_current', 'sas', 2),
('税及附加', 'taxes_and_surcharges_current', 'sas', 2),
('第3行', 'taxes_and_surcharges_current', 'sas', 3),
('3行', 'taxes_and_surcharges_current', 'sas', 3),
('第三行', 'taxes_and_surcharges_current', 'sas', 3),

-- 消费税
('消费税', 'consumption_tax_current', 'sas', 2),
('消费税费', 'consumption_tax_current', 'sas', 2),
('消费税金额', 'consumption_tax_current', 'sas', 2),
('其中：消费税', 'consumption_tax_current', 'sas', 2),
('消费税金', 'consumption_tax_current', 'sas', 2),
('第4行', 'consumption_tax_current', 'sas', 3),
('4行', 'consumption_tax_current', 'sas', 3),
('第四行', 'consumption_tax_current', 'sas', 3),

-- 营业税
('营业税', 'business_tax_current', 'sas', 2),
('营业税费', 'business_tax_current', 'sas', 2),
('营业税金', 'business_tax_current', 'sas', 2),
('营业税额', 'business_tax_current', 'sas', 2),
('第5行', 'business_tax_current', 'sas', 3),
('5行', 'business_tax_current', 'sas', 3),
('第五行', 'business_tax_current', 'sas', 3),

-- 城市维护建设税
('城市维护建设税', 'city_maintenance_tax_current', 'sas', 2),
('城建税', 'city_maintenance_tax_current', 'sas', 2),
('城市维护税', 'city_maintenance_tax_current', 'sas', 2),
('城建税费', 'city_maintenance_tax_current', 'sas', 2),
('城建税金', 'city_maintenance_tax_current', 'sas', 2),
('第6行', 'city_maintenance_tax_current', 'sas', 3),
('6行', 'city_maintenance_tax_current', 'sas', 3),
('第六行', 'city_maintenance_tax_current', 'sas', 3),

-- 资源税
('资源税', 'resource_tax_current', 'sas', 2),
('资源税费', 'resource_tax_current', 'sas', 2),
('资源税金', 'resource_tax_current', 'sas', 2),
('资源税额', 'resource_tax_current', 'sas', 2),
('第7行', 'resource_tax_current', 'sas', 3),
('7行', 'resource_tax_current', 'sas', 3),
('第七行', 'resource_tax_current', 'sas', 3),

-- 土地增值税
('土地增值税', 'land_appreciation_tax_current', 'sas', 2),
('土增税', 'land_appreciation_tax_current', 'sas', 2),
('土地增值税费', 'land_appreciation_tax_current', 'sas', 2),
('土增税金', 'land_appreciation_tax_current', 'sas', 2),
('第8行', 'land_appreciation_tax_current', 'sas', 3),
('8行', 'land_appreciation_tax_current', 'sas', 3),
('第八行', 'land_appreciation_tax_current', 'sas', 3),

-- 城镇土地使用税、房产税、车船税、印花税
('城镇土地使用税、房产税、车船税、印花税', 'property_and_other_taxes_current', 'sas', 2),
('土地使用税、房产税、车船税、印花税', 'property_and_other_taxes_current', 'sas', 2),
('房产税、车船税、印花税、土地使用税', 'property_and_other_taxes_current', 'sas', 2),
('小税种合计', 'property_and_other_taxes_current', 'sas', 2),
('财产税及其他税', 'property_and_other_taxes_current', 'sas', 2),
('第9行', 'property_and_other_taxes_current', 'sas', 3),
('9行', 'property_and_other_taxes_current', 'sas', 3),
('第九行', 'property_and_other_taxes_current', 'sas', 3),

-- 教育费附加、矿产资源补偿费、排污费
('教育费附加、矿产资源补偿费、排污费', 'education_surcharge_and_other_current', 'sas', 2),
('教育费附加及其他', 'education_surcharge_and_other_current', 'sas', 2),
('教育附加费', 'education_surcharge_and_other_current', 'sas', 2),
('矿产资源补偿费', 'education_surcharge_and_other_current', 'sas', 2),
('排污费', 'education_surcharge_and_other_current', 'sas', 2),
('第10行', 'education_surcharge_and_other_current', 'sas', 3),
('10行', 'education_surcharge_and_other_current', 'sas', 3),
('第十行', 'education_surcharge_and_other_current', 'sas', 3),

-- 销售费用
('销售费用', 'selling_expense_current', 'sas', 2),
('销售费', 'selling_expense_current', 'sas', 2),
('营销费用', 'selling_expense_current', 'sas', 2),
('营销费', 'selling_expense_current', 'sas', 2),
('售卖费用', 'selling_expense_current', 'sas', 2),
('第11行', 'selling_expense_current', 'sas', 3),
('11行', 'selling_expense_current', 'sas', 3),
('第十一行', 'selling_expense_current', 'sas', 3),

-- 商品维修费
('商品维修费', 'selling_expense_repair_current', 'sas', 2),
('维修费', 'selling_expense_repair_current', 'sas', 2),
('产品维修费', 'selling_expense_repair_current', 'sas', 2),
('商品维修费用', 'selling_expense_repair_current', 'sas', 2),
('其中：商品维修费', 'selling_expense_repair_current', 'sas', 2),
('第12行', 'selling_expense_repair_current', 'sas', 3),
('12行', 'selling_expense_repair_current', 'sas', 3),
('第十二行', 'selling_expense_repair_current', 'sas', 3),

-- 广告费和业务宣传费
('广告费和业务宣传费', 'selling_expense_advertising_current', 'sas', 2),
('广告费', 'selling_expense_advertising_current', 'sas', 2),
('宣传费', 'selling_expense_advertising_current', 'sas', 2),
('广告宣传费', 'selling_expense_advertising_current', 'sas', 2),
('业务宣传费', 'selling_expense_advertising_current', 'sas', 2),
('第13行', 'selling_expense_advertising_current', 'sas', 3),
('13行', 'selling_expense_advertising_current', 'sas', 3),
('第十三行', 'selling_expense_advertising_current', 'sas', 3),

-- 管理费用
('管理费用', 'administrative_expense_current', 'sas', 2),
('管理费', 'administrative_expense_current', 'sas', 2),
('管理开支', 'administrative_expense_current', 'sas', 2),
('行政费用', 'administrative_expense_current', 'sas', 2),
('行政费', 'administrative_expense_current', 'sas', 2),
('第14行', 'administrative_expense_current', 'sas', 3),
('14行', 'administrative_expense_current', 'sas', 3),
('第十四行', 'administrative_expense_current', 'sas', 3),

-- 开办费
('开办费', 'administrative_expense_organization_current', 'sas', 2),
('开办费用', 'administrative_expense_organization_current', 'sas', 2),
('筹备费', 'administrative_expense_organization_current', 'sas', 2),
('设立费', 'administrative_expense_organization_current', 'sas', 2),
('其中：开办费', 'administrative_expense_organization_current', 'sas', 2),
('第15行', 'administrative_expense_organization_current', 'sas', 3),
('15行', 'administrative_expense_organization_current', 'sas', 3),
('第十五行', 'administrative_expense_organization_current', 'sas', 3),

-- 业务招待费
('业务招待费', 'administrative_expense_entertainment_current', 'sas', 2),
('招待费', 'administrative_expense_entertainment_current', 'sas', 2),
('业务招待费用', 'administrative_expense_entertainment_current', 'sas', 2),
('交际费', 'administrative_expense_entertainment_current', 'sas', 2),
('应酬费', 'administrative_expense_entertainment_current', 'sas', 2),
('第16行', 'administrative_expense_entertainment_current', 'sas', 3),
('16行', 'administrative_expense_entertainment_current', 'sas', 3),
('第十六行', 'administrative_expense_entertainment_current', 'sas', 3),

-- 研究费用
('研究费用', 'administrative_expense_research_current', 'sas', 2),
('研究费', 'administrative_expense_research_current', 'sas', 2),
('研发费用', 'administrative_expense_research_current', 'sas', 2),
('研发费', 'administrative_expense_research_current', 'sas', 2),
('研发支出', 'administrative_expense_research_current', 'sas', 2),
('第17行', 'administrative_expense_research_current', 'sas', 3),
('17行', 'administrative_expense_research_current', 'sas', 3),
('第十七行', 'administrative_expense_research_current', 'sas', 3),

-- 财务费用
('财务费用', 'financial_expense_current', 'sas', 2),
('财务费', 'financial_expense_current', 'sas', 2),
('财务开支', 'financial_expense_current', 'sas', 2),
('筹资费用', 'financial_expense_current', 'sas', 2),
('资金费用', 'financial_expense_current', 'sas', 2),
('第18行', 'financial_expense_current', 'sas', 3),
('18行', 'financial_expense_current', 'sas', 3),
('第十八行', 'financial_expense_current', 'sas', 3),

-- 利息费用
('利息费用', 'interest_expense_current', 'sas', 2),
('利息费用（收入以“-”号填列）', 'interest_expense_current', 'sas', 2),
('利息费', 'interest_expense_current', 'sas', 2),
('利息支出', 'interest_expense_current', 'sas', 2),
('借款利息', 'interest_expense_current', 'sas', 2),
('第19行', 'interest_expense_current', 'sas', 3),
('19行', 'interest_expense_current', 'sas', 3),
('第十九行', 'interest_expense_current', 'sas', 3),

-- 投资收益
('投资收益', 'investment_income_current', 'sas', 2),
('投资收益（亏损以“-”号填列）', 'investment_income_current', 'sas', 2),
('加：投资收益', 'investment_income_current', 'sas', 2),
('投资利润', 'investment_income_current', 'sas', 2),
('投资回报', 'investment_income_current', 'sas', 2),
('第20行', 'investment_income_current', 'sas', 3),
('20行', 'investment_income_current', 'sas', 3),
('第二十行', 'investment_income_current', 'sas', 3),

-- 营业利润
('营业利润', 'operating_profit_current', 'sas', 2),
('营业利润（亏损以“-”号填列）', 'operating_profit_current', 'sas', 2),
('二、营业利润', 'operating_profit_current', 'sas', 2),
('经营利润', 'operating_profit_current', 'sas', 2),
('主营利润', 'operating_profit_current', 'sas', 2),
('第21行', 'operating_profit_current', 'sas', 3),
('21行', 'operating_profit_current', 'sas', 3),
('第二十一行', 'operating_profit_current', 'sas', 3),

-- 营业外收入
('营业外收入', 'non_operating_income_current', 'sas', 2),
('加：营业外收入', 'non_operating_income_current', 'sas', 2),
('非营业收入', 'non_operating_income_current', 'sas', 2),
('营业外收益', 'non_operating_income_current', 'sas', 2),
('额外收入', 'non_operating_income_current', 'sas', 2),
('第22行', 'non_operating_income_current', 'sas', 3),
('22行', 'non_operating_income_current', 'sas', 3),
('第二十二行', 'non_operating_income_current', 'sas', 3),

-- 政府补助
('政府补助', 'non_operating_income_gov_grant_current', 'sas', 2),
('政府补贴', 'non_operating_income_gov_grant_current', 'sas', 2),
('财政补助', 'non_operating_income_gov_grant_current', 'sas', 2),
('其中：政府补助', 'non_operating_income_gov_grant_current', 'sas', 2),
('政府扶持资金', 'non_operating_income_gov_grant_current', 'sas', 2),
('第23行', 'non_operating_income_gov_grant_current', 'sas', 3),
('23行', 'non_operating_income_gov_grant_current', 'sas', 3),
('第二十三行', 'non_operating_income_gov_grant_current', 'sas', 3),

-- 营业外支出
('营业外支出', 'non_operating_expense_current', 'sas', 2),
('减：营业外支出', 'non_operating_expense_current', 'sas', 2),
('非营业支出', 'non_operating_expense_current', 'sas', 2),
('营业外开销', 'non_operating_expense_current', 'sas', 2),
('额外支出', 'non_operating_expense_current', 'sas', 2),
('第24行', 'non_operating_expense_current', 'sas', 3),
('24行', 'non_operating_expense_current', 'sas', 3),
('第二十四行', 'non_operating_expense_current', 'sas', 3),

-- 坏账损失
('坏账损失', 'non_operating_expense_bad_debt_current', 'sas', 2),
('坏账亏损', 'non_operating_expense_bad_debt_current', 'sas', 2),
('坏账减值损失', 'non_operating_expense_bad_debt_current', 'sas', 2),
('其中：坏账损失', 'non_operating_expense_bad_debt_current', 'sas', 2),
('坏账费用', 'non_operating_expense_bad_debt_current', 'sas', 2),
('第25行', 'non_operating_expense_bad_debt_current', 'sas', 3),
('25行', 'non_operating_expense_bad_debt_current', 'sas', 3),
('第二十五行', 'non_operating_expense_bad_debt_current', 'sas', 3),

-- 无法收回的长期债券投资损失
('无法收回的长期债券投资损失', 'non_operating_expense_loss_long_term_bond_current', 'sas', 2),
('长期债券投资损失', 'non_operating_expense_loss_long_term_bond_current', 'sas', 2),
('债券投资无法收回损失', 'non_operating_expense_loss_long_term_bond_current', 'sas', 2),
('长期债券坏账损失', 'non_operating_expense_loss_long_term_bond_current', 'sas', 2),
('债券投资损失', 'non_operating_expense_loss_long_term_bond_current', 'sas', 2),
('第26行', 'non_operating_expense_loss_long_term_bond_current', 'sas', 3),
('26行', 'non_operating_expense_loss_long_term_bond_current', 'sas', 3),
('第二十六行', 'non_operating_expense_loss_long_term_bond_current', 'sas', 3),

-- 无法收回的长期股权投资损失
('无法收回的长期股权投资损失', 'non_operating_expense_loss_long_term_equity_current', 'sas', 2),
('长期股权投资损失', 'non_operating_expense_loss_long_term_equity_current', 'sas', 2),
('股权投资无法收回损失', 'non_operating_expense_loss_long_term_equity_current', 'sas', 2),
('长期股权坏账损失', 'non_operating_expense_loss_long_term_equity_current', 'sas', 2),
('股权投资损失', 'non_operating_expense_loss_long_term_equity_current', 'sas', 2),
('第27行', 'non_operating_expense_loss_long_term_equity_current', 'sas', 3),
('27行', 'non_operating_expense_loss_long_term_equity_current', 'sas', 3),
('第二十七行', 'non_operating_expense_loss_long_term_equity_current', 'sas', 3),

-- 自然灾害等不可抗力因素造成的损失
('自然灾害等不可抗力因素造成的损失', 'non_operating_expense_force_majeure_current', 'sas', 2),
('自然灾害损失', 'non_operating_expense_force_majeure_current', 'sas', 2),
('不可抗力损失', 'non_operating_expense_force_majeure_current', 'sas', 2),
('天灾损失', 'non_operating_expense_force_majeure_current', 'sas', 2),
('意外损失', 'non_operating_expense_force_majeure_current', 'sas', 2),
('第28行', 'non_operating_expense_force_majeure_current', 'sas', 3),
('28行', 'non_operating_expense_force_majeure_current', 'sas', 3),
('第二十八行', 'non_operating_expense_force_majeure_current', 'sas', 3),

-- 税收滞纳金
('税收滞纳金', 'non_operating_expense_tax_late_fee_current', 'sas', 2),
('滞纳金', 'non_operating_expense_tax_late_fee_current', 'sas', 2),
('税务滞纳金', 'non_operating_expense_tax_late_fee_current', 'sas', 2),
('税款滞纳金', 'non_operating_expense_tax_late_fee_current', 'sas', 2),
('税收罚款', 'non_operating_expense_tax_late_fee_current', 'sas', 2),
('第29行', 'non_operating_expense_tax_late_fee_current', 'sas', 3),
('29行', 'non_operating_expense_tax_late_fee_current', 'sas', 3),
('第二十九行', 'non_operating_expense_tax_late_fee_current', 'sas', 3),

-- 利润总额
('利润总额', 'total_profit_current', 'sas', 2),
('利润总额（亏损总额以“-”号填列）', 'total_profit_current', 'sas', 2),
('三、利润总额', 'total_profit_current', 'sas', 2),
('税前利润', 'total_profit_current', 'sas', 2),
('总利润', 'total_profit_current', 'sas', 2),
('第30行', 'total_profit_current', 'sas', 3),
('30行', 'total_profit_current', 'sas', 3),
('第三十行', 'total_profit_current', 'sas', 3),

-- 所得税费用
('所得税费用', 'income_tax_expense_current', 'sas', 2),
('减：所得税费用', 'income_tax_expense_current', 'sas', 2),
('所得税', 'income_tax_expense_current', 'sas', 2),
('所得税费', 'income_tax_expense_current', 'sas', 2),
('企业所得税', 'income_tax_expense_current', 'sas', 2),
('第31行', 'income_tax_expense_current', 'sas', 3),
('31行', 'income_tax_expense_current', 'sas', 3),
('第三十一行', 'income_tax_expense_current', 'sas', 3),

-- 净利润
('净利润', 'net_profit_current', 'sas', 2),
('净利润（净亏损以“-”号填列）', 'net_profit_current', 'sas', 2),
('四、净利润', 'net_profit_current', 'sas', 2),
('纯利润', 'net_profit_current', 'sas', 2),
('税后利润', 'net_profit_current', 'sas', 2),
('净利', 'net_profit_current', 'sas', 2),
('第32行', 'net_profit_current', 'sas', 3),
('32行', 'net_profit_current', 'sas', 3),
('第三十二行', 'net_profit_current', 'sas', 3);
```