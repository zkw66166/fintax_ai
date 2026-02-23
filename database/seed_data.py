"""种子数据：栏次映射 + 同义词 + 字典表 + metric_registry"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def seed_reference_data(db_path=None):
    """插入栏次映射、同义词、字典数据、指标注册表"""
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    _seed_column_mappings(cur)
    _seed_synonyms(cur)
    _seed_dictionaries(cur)
    _seed_metric_registry(cur)
    _seed_eit_column_mappings(cur)
    _seed_eit_synonyms(cur)
    _seed_eit_metric_registry(cur)
    _seed_account_master(cur)
    _seed_account_synonyms(cur)
    _seed_account_balance_column_mapping(cur)
    _seed_bs_item_dict(cur)
    _seed_bs_synonyms(cur)
    _seed_is_item_dict(cur)
    _seed_is_synonyms(cur)
    _seed_cf_item_dict(cur)
    _seed_cf_synonyms(cur)
    _seed_inv_column_mappings(cur)
    _seed_inv_synonyms(cur)
    _seed_financial_metrics_item_dict(cur)

    conn.commit()
    conn.close()
    print("[seed_data] 种子数据插入完成")


def _seed_cf_item_dict(cur):
    from database.seed_cf import seed_cf_item_dict
    seed_cf_item_dict(cur)


def _seed_cf_synonyms(cur):
    from database.seed_cf import seed_cf_synonyms
    seed_cf_synonyms(cur)


def _seed_column_mappings(cur):
    """41条一般纳税人 + 25条小规模纳税人栏次映射"""
    general_mappings = [
        (1, 'sales_taxable_rate', '按适用税率计税销售额'),
        (2, 'sales_goods', '应税货物销售额'),
        (3, 'sales_services', '应税劳务销售额'),
        (4, 'sales_adjustment_check', '纳税检查调整的销售额'),
        (5, 'sales_simple_method', '按简易办法计税销售额'),
        (6, 'sales_simple_adjust_check', '简易办法纳税检查调整'),
        (7, 'sales_export_credit_refund', '免、抵、退办法出口销售额'),
        (8, 'sales_tax_free', '免税销售额'),
        (9, 'sales_tax_free_goods', '免税货物销售额'),
        (10, 'sales_tax_free_services', '免税劳务销售额'),
        (11, 'output_tax', '销项税额'),
        (12, 'input_tax', '进项税额'),
        (13, 'last_period_credit', '上期留抵税额'),
        (14, 'transfer_out', '进项税额转出'),
        (15, 'export_refund', '免、抵、退应退税额'),
        (16, 'tax_check_supplement', '按适用税率计算的纳税检查应补缴税额'),
        (17, 'deductible_total', '应抵扣税额合计'),
        (18, 'actual_deduct', '实际抵扣税额'),
        (19, 'tax_payable', '应纳税额'),
        (20, 'end_credit', '期末留抵税额'),
        (21, 'simple_tax', '简易计税办法计算的应纳税额'),
        (22, 'simple_tax_check_supplement', '按简易计税办法计算的纳税检查应补缴税额'),
        (23, 'tax_reduction', '应纳税额减征额'),
        (24, 'total_tax_payable', '应纳税额合计'),
        (25, 'unpaid_begin', '期初未缴税额'),
        (26, 'export_receipt_tax', '实收出口开具专用缴款书退税额'),
        (27, 'paid_current', '本期已缴税额'),
        (28, 'prepaid_installment', '分次预缴税额'),
        (29, 'prepaid_export_receipt', '出口开具专用缴款书预缴税额'),
        (30, 'paid_last_period', '本期缴纳上期应纳税额'),
        (31, 'paid_arrears', '本期缴纳欠缴税额'),
        (32, 'unpaid_end', '期末未缴税额'),
        (33, 'arrears', '欠缴税额'),
        (34, 'supplement_refund', '本期应补退税额'),
        (35, 'immediate_refund', '即征即退实际退税额'),
        (36, 'unpaid_check_begin', '期初未缴查补税额'),
        (37, 'paid_check_current', '本期入库查补税额'),
        (38, 'unpaid_check_end', '期末未缴查补税额'),
        (39, 'city_maintenance_tax', '城市维护建设税本期应补（退）税额'),
        (40, 'education_surcharge', '教育费附加本期应补（退）费额'),
        (41, 'local_education_surcharge', '地方教育附加本期应补（退）费额'),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO vat_general_column_mapping (line_number, column_name, business_name) VALUES (?,?,?)",
        general_mappings
    )

    small_mappings = [
        (1, 'sales_3percent', '应征增值税不含税销售额（3%征收率）'),
        (2, 'sales_3percent_invoice_spec', '增值税专用发票不含税销售额'),
        (3, 'sales_3percent_invoice_other', '其他增值税发票不含税销售额'),
        (4, 'sales_5percent', '应征增值税不含税销售额（5%征收率）'),
        (5, 'sales_5percent_invoice_spec', '增值税专用发票不含税销售额（5%征收率）'),
        (6, 'sales_5percent_invoice_other', '其他增值税发票不含税销售额（5%征收率）'),
        (7, 'sales_used_assets', '销售使用过的固定资产不含税销售额'),
        (8, 'sales_used_assets_invoice_other', '其中其他增值税发票不含税销售额'),
        (9, 'sales_tax_free', '免税销售额'),
        (10, 'sales_tax_free_micro', '小微企业免税销售额'),
        (11, 'sales_tax_free_threshold', '未达起征点销售额'),
        (12, 'sales_tax_free_other', '其他免税销售额'),
        (13, 'sales_export_tax_free', '出口免税销售额'),
        (14, 'sales_export_tax_free_invoice_other', '其中其他增值税发票不含税销售额'),
        (15, 'tax_due_current', '本期应纳税额'),
        (16, 'tax_due_reduction', '本期应纳税额减征额'),
        (17, 'tax_free_amount', '本期免税额'),
        (18, 'tax_free_micro', '其中小微企业免税额'),
        (19, 'tax_free_threshold', '未达起征点免税额'),
        (20, 'tax_due_total', '应纳税额合计'),
        (21, 'tax_prepaid', '本期预缴税额'),
        (22, 'tax_supplement_refund', '本期应补（退）税额'),
        (23, 'city_maintenance_tax', '城市维护建设税本期应补（退）税额'),
        (24, 'education_surcharge', '教育费附加本期应补（退）费额'),
        (25, 'local_education_surcharge', '地方教育附加本期应补（退）费额'),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO vat_small_column_mapping (line_number, column_name, business_name) VALUES (?,?,?)",
        small_mappings
    )
    print("  栏次映射: 41+25 条")


def _seed_synonyms(cur):
    """~400条同义词映射"""
    # (phrase, column_name, priority, taxpayer_type, scope_view)
    # 一般纳税人 41 字段同义词
    general_synonyms = [
        # 第1栏：sales_taxable_rate
        ('第1栏', 'sales_taxable_rate', 3), ('1栏', 'sales_taxable_rate', 3),
        ('栏次1', 'sales_taxable_rate', 3), ('按适用税率计税销售额', 'sales_taxable_rate', 2),
        ('适用税率计税销售额', 'sales_taxable_rate', 2), ('计税销售额', 'sales_taxable_rate', 1),
        ('适用税率销售额', 'sales_taxable_rate', 1), ('一般计税销售额', 'sales_taxable_rate', 1),
        # 第2栏：sales_goods
        ('第2栏', 'sales_goods', 3), ('2栏', 'sales_goods', 3), ('栏次2', 'sales_goods', 3),
        ('应税货物销售额', 'sales_goods', 2), ('货物销售额', 'sales_goods', 1), ('应税货物', 'sales_goods', 1),
        # 第3栏：sales_services
        ('第3栏', 'sales_services', 3), ('3栏', 'sales_services', 3), ('栏次3', 'sales_services', 3),
        ('应税劳务销售额', 'sales_services', 2), ('应税服务销售额', 'sales_services', 2),
        ('劳务销售额', 'sales_services', 1), ('服务销售额', 'sales_services', 1),
        # 第4栏：sales_adjustment_check
        ('第4栏', 'sales_adjustment_check', 3), ('4栏', 'sales_adjustment_check', 3),
        ('纳税检查调整的销售额', 'sales_adjustment_check', 2), ('查补销售额', 'sales_adjustment_check', 1),
        # 第5栏：sales_simple_method
        ('第5栏', 'sales_simple_method', 3), ('5栏', 'sales_simple_method', 3),
        ('按简易办法计税销售额', 'sales_simple_method', 2), ('简易计税销售额', 'sales_simple_method', 1),
        # 第6栏：sales_simple_adjust_check
        ('第6栏', 'sales_simple_adjust_check', 3), ('6栏', 'sales_simple_adjust_check', 3),
        ('简易办法纳税检查调整', 'sales_simple_adjust_check', 2),
        # 第7栏：sales_export_credit_refund
        ('第7栏', 'sales_export_credit_refund', 3), ('7栏', 'sales_export_credit_refund', 3),
        ('免、抵、退办法出口销售额', 'sales_export_credit_refund', 2),
        ('免抵退出口销售额', 'sales_export_credit_refund', 1),
        # 第8栏：sales_tax_free
        ('第8栏', 'sales_tax_free', 3), ('8栏', 'sales_tax_free', 3),
        ('免税销售额', 'sales_tax_free', 2), ('免税销售', 'sales_tax_free', 1),
        # 第9栏：sales_tax_free_goods
        ('第9栏', 'sales_tax_free_goods', 3), ('9栏', 'sales_tax_free_goods', 3),
        ('免税货物销售额', 'sales_tax_free_goods', 2), ('免税货物', 'sales_tax_free_goods', 1),
        # 第10栏：sales_tax_free_services
        ('第10栏', 'sales_tax_free_services', 3), ('10栏', 'sales_tax_free_services', 3),
        ('免税劳务销售额', 'sales_tax_free_services', 2), ('免税服务销售额', 'sales_tax_free_services', 2),
        # 第11栏：output_tax
        ('第11栏', 'output_tax', 3), ('11栏', 'output_tax', 3), ('栏次11', 'output_tax', 3),
        ('销项税额', 'output_tax', 2), ('销项税', 'output_tax', 1), ('销项', 'output_tax', 1),
        # 第12栏：input_tax
        ('第12栏', 'input_tax', 3), ('12栏', 'input_tax', 3), ('栏次12', 'input_tax', 3),
        ('进项税额', 'input_tax', 2), ('进项税', 'input_tax', 1), ('进项', 'input_tax', 1),
        # 第13栏：last_period_credit
        ('第13栏', 'last_period_credit', 3), ('13栏', 'last_period_credit', 3),
        ('上期留抵税额', 'last_period_credit', 2), ('上期留抵', 'last_period_credit', 1),
        ('期初留抵税额', 'last_period_credit', 1),
        # 第14栏：transfer_out
        ('第14栏', 'transfer_out', 3), ('14栏', 'transfer_out', 3),
        ('进项税额转出', 'transfer_out', 2), ('进项转出', 'transfer_out', 1),
        # 第15栏：export_refund
        ('第15栏', 'export_refund', 3), ('15栏', 'export_refund', 3),
        ('免、抵、退应退税额', 'export_refund', 2), ('免抵退应退税额', 'export_refund', 1),
        ('应退税额', 'export_refund', 1),
        # 第16栏：tax_check_supplement
        ('第16栏', 'tax_check_supplement', 3), ('16栏', 'tax_check_supplement', 3),
        ('按适用税率计算的纳税检查应补缴税额', 'tax_check_supplement', 2), ('查补税额', 'tax_check_supplement', 1),
        # 第17栏：deductible_total
        ('第17栏', 'deductible_total', 3), ('17栏', 'deductible_total', 3),
        ('应抵扣税额合计', 'deductible_total', 2), ('应抵扣税额', 'deductible_total', 1),
        # 第18栏：actual_deduct
        ('第18栏', 'actual_deduct', 3), ('18栏', 'actual_deduct', 3),
        ('实际抵扣税额', 'actual_deduct', 2), ('实际抵扣', 'actual_deduct', 1),
        # 第19栏：tax_payable
        ('第19栏', 'tax_payable', 3), ('19栏', 'tax_payable', 3), ('栏次19', 'tax_payable', 3),
        ('应纳税额', 'tax_payable', 2), ('应纳增值税', 'tax_payable', 1), ('应纳额', 'tax_payable', 1),
        ('增值税应纳税额', 'tax_payable', 1),
        # 第20栏：end_credit
        ('第20栏', 'end_credit', 3), ('20栏', 'end_credit', 3), ('栏次20', 'end_credit', 3),
        ('期末留抵税额', 'end_credit', 2), ('期末留抵', 'end_credit', 1), ('留抵税额', 'end_credit', 1),
        # 第21栏：simple_tax
        ('第21栏', 'simple_tax', 3), ('21栏', 'simple_tax', 3),
        ('简易计税办法计算的应纳税额', 'simple_tax', 2), ('简易计税应纳税额', 'simple_tax', 1),
        # 第22栏：simple_tax_check_supplement
        ('第22栏', 'simple_tax_check_supplement', 3), ('22栏', 'simple_tax_check_supplement', 3),
        ('按简易计税办法计算的纳税检查应补缴税额', 'simple_tax_check_supplement', 2),
        ('简易计税查补税额', 'simple_tax_check_supplement', 1),
        # 第23栏：tax_reduction
        ('第23栏', 'tax_reduction', 3), ('23栏', 'tax_reduction', 3),
        ('应纳税额减征额', 'tax_reduction', 2), ('减征额', 'tax_reduction', 1),
        # 第24栏：total_tax_payable
        ('第24栏', 'total_tax_payable', 3), ('24栏', 'total_tax_payable', 3),
        ('栏次24', 'total_tax_payable', 3), ('应纳税额合计', 'total_tax_payable', 2),
        ('应纳税合计', 'total_tax_payable', 1), ('应纳总额', 'total_tax_payable', 1),
        ('本期应纳合计', 'total_tax_payable', 1),
        # 第25栏：unpaid_begin
        ('第25栏', 'unpaid_begin', 3), ('25栏', 'unpaid_begin', 3),
        ('期初未缴税额', 'unpaid_begin', 2), ('期初未缴', 'unpaid_begin', 1),
        # 第26栏：export_receipt_tax
        ('第26栏', 'export_receipt_tax', 3), ('26栏', 'export_receipt_tax', 3),
        ('实收出口开具专用缴款书退税额', 'export_receipt_tax', 2),
        # 第27栏：paid_current
        ('第27栏', 'paid_current', 3), ('27栏', 'paid_current', 3),
        ('本期已缴税额', 'paid_current', 2), ('本期已缴', 'paid_current', 1),
        # 第28栏：prepaid_installment
        ('第28栏', 'prepaid_installment', 3), ('28栏', 'prepaid_installment', 3),
        ('分次预缴税额', 'prepaid_installment', 2), ('预缴税额', 'prepaid_installment', 1),
        # 第29栏：prepaid_export_receipt
        ('第29栏', 'prepaid_export_receipt', 3), ('29栏', 'prepaid_export_receipt', 3),
        ('出口开具专用缴款书预缴税额', 'prepaid_export_receipt', 2),
        # 第30栏：paid_last_period
        ('第30栏', 'paid_last_period', 3), ('30栏', 'paid_last_period', 3),
        ('本期缴纳上期应纳税额', 'paid_last_period', 2),
        # 第31栏：paid_arrears
        ('第31栏', 'paid_arrears', 3), ('31栏', 'paid_arrears', 3),
        ('本期缴纳欠缴税额', 'paid_arrears', 2), ('缴纳欠税', 'paid_arrears', 1),
        # 第32栏：unpaid_end
        ('第32栏', 'unpaid_end', 3), ('32栏', 'unpaid_end', 3),
        ('期末未缴税额', 'unpaid_end', 2), ('期末未缴', 'unpaid_end', 1),
        # 第33栏：arrears
        ('第33栏', 'arrears', 3), ('33栏', 'arrears', 3),
        ('欠缴税额', 'arrears', 2), ('欠税', 'arrears', 1),
        # 第34栏：supplement_refund
        ('第34栏', 'supplement_refund', 3), ('34栏', 'supplement_refund', 3),
        ('本期应补退税额', 'supplement_refund', 2), ('应补退税额', 'supplement_refund', 1),
        ('应补退税', 'supplement_refund', 1),
        # 第35栏：immediate_refund
        ('第35栏', 'immediate_refund', 3), ('35栏', 'immediate_refund', 3),
        ('即征即退实际退税额', 'immediate_refund', 2), ('即征即退税额', 'immediate_refund', 1),
        # 第36栏：unpaid_check_begin
        ('第36栏', 'unpaid_check_begin', 3), ('36栏', 'unpaid_check_begin', 3),
        ('期初未缴查补税额', 'unpaid_check_begin', 2),
        # 第37栏：paid_check_current
        ('第37栏', 'paid_check_current', 3), ('37栏', 'paid_check_current', 3),
        ('本期入库查补税额', 'paid_check_current', 2),
        # 第38栏：unpaid_check_end
        ('第38栏', 'unpaid_check_end', 3), ('38栏', 'unpaid_check_end', 3),
        ('期末未缴查补税额', 'unpaid_check_end', 2),
        # 第39栏：city_maintenance_tax
        ('第39栏', 'city_maintenance_tax', 3), ('39栏', 'city_maintenance_tax', 3),
        ('城市维护建设税本期应补退税额', 'city_maintenance_tax', 2),
        ('城建税', 'city_maintenance_tax', 1), ('城市维护建设税', 'city_maintenance_tax', 1),
        # 第40栏：education_surcharge
        ('第40栏', 'education_surcharge', 3), ('40栏', 'education_surcharge', 3),
        ('教育费附加本期应补退费额', 'education_surcharge', 2),
        ('教育费附加', 'education_surcharge', 1), ('教育附加', 'education_surcharge', 1),
        # 第41栏：local_education_surcharge
        ('第41栏', 'local_education_surcharge', 3), ('41栏', 'local_education_surcharge', 3),
        ('地方教育附加本期应补退费额', 'local_education_surcharge', 2),
        ('地方教育附加', 'local_education_surcharge', 1), ('地方教育费附加', 'local_education_surcharge', 1),
    ]

    # 小规模纳税人 25 字段同义词
    small_synonyms = [
        # 第1栏：sales_3percent
        ('第1栏', 'sales_3percent', 3), ('1栏', 'sales_3percent', 3),
        ('应征增值税不含税销售额（3%征收率）', 'sales_3percent', 2),
        ('3%销售额', 'sales_3percent', 1), ('3%不含税销售额', 'sales_3percent', 1),
        ('3%征收率销售额', 'sales_3percent', 1),
        # 第2栏：sales_3percent_invoice_spec
        ('第2栏', 'sales_3percent_invoice_spec', 3), ('2栏', 'sales_3percent_invoice_spec', 3),
        ('增值税专用发票不含税销售额', 'sales_3percent_invoice_spec', 2),
        ('3%专票销售额', 'sales_3percent_invoice_spec', 1), ('专用发票销售额', 'sales_3percent_invoice_spec', 1),
        # 第3栏：sales_3percent_invoice_other
        ('第3栏', 'sales_3percent_invoice_other', 3), ('3栏', 'sales_3percent_invoice_other', 3),
        ('其他增值税发票不含税销售额', 'sales_3percent_invoice_other', 2),
        ('普票销售额', 'sales_3percent_invoice_other', 1),
        # 第4栏：sales_5percent
        ('第4栏', 'sales_5percent', 3), ('4栏', 'sales_5percent', 3),
        ('应征增值税不含税销售额（5%征收率）', 'sales_5percent', 2),
        ('5%销售额', 'sales_5percent', 1), ('5%征收率销售额', 'sales_5percent', 1),
        # 第5栏：sales_5percent_invoice_spec
        ('第5栏', 'sales_5percent_invoice_spec', 3), ('5栏', 'sales_5percent_invoice_spec', 3),
        ('5%专票销售额', 'sales_5percent_invoice_spec', 1),
        # 第6栏：sales_5percent_invoice_other
        ('第6栏', 'sales_5percent_invoice_other', 3), ('6栏', 'sales_5percent_invoice_other', 3),
        ('5%其他发票销售额', 'sales_5percent_invoice_other', 1),
        # 第7栏：sales_used_assets
        ('第7栏', 'sales_used_assets', 3), ('7栏', 'sales_used_assets', 3),
        ('销售使用过的固定资产不含税销售额', 'sales_used_assets', 2),
        ('使用过的固定资产销售额', 'sales_used_assets', 1),
        # 第8栏：sales_used_assets_invoice_other
        ('第8栏', 'sales_used_assets_invoice_other', 3), ('8栏', 'sales_used_assets_invoice_other', 3),
        # 第9栏：sales_tax_free
        ('第9栏', 'sales_tax_free', 3), ('9栏', 'sales_tax_free', 3),
        ('免税销售额', 'sales_tax_free', 2),
        # 第10栏：sales_tax_free_micro
        ('第10栏', 'sales_tax_free_micro', 3), ('10栏', 'sales_tax_free_micro', 3),
        ('小微企业免税销售额', 'sales_tax_free_micro', 2), ('小微免税销售额', 'sales_tax_free_micro', 1),
        # 第11栏：sales_tax_free_threshold
        ('第11栏', 'sales_tax_free_threshold', 3), ('11栏', 'sales_tax_free_threshold', 3),
        ('未达起征点销售额', 'sales_tax_free_threshold', 2), ('未达起征点', 'sales_tax_free_threshold', 1),
        # 第12栏：sales_tax_free_other
        ('第12栏', 'sales_tax_free_other', 3), ('12栏', 'sales_tax_free_other', 3),
        ('其他免税销售额', 'sales_tax_free_other', 2),
        # 第13栏：sales_export_tax_free
        ('第13栏', 'sales_export_tax_free', 3), ('13栏', 'sales_export_tax_free', 3),
        ('出口免税销售额', 'sales_export_tax_free', 2),
        # 第14栏：sales_export_tax_free_invoice_other
        ('第14栏', 'sales_export_tax_free_invoice_other', 3),
        # 第15栏：tax_due_current
        ('第15栏', 'tax_due_current', 3), ('15栏', 'tax_due_current', 3),
        ('本期应纳税额', 'tax_due_current', 2), ('本期应纳', 'tax_due_current', 1),
        # 第16栏：tax_due_reduction
        ('第16栏', 'tax_due_reduction', 3), ('16栏', 'tax_due_reduction', 3),
        ('本期应纳税额减征额', 'tax_due_reduction', 2),
        # 第17栏：tax_free_amount
        ('第17栏', 'tax_free_amount', 3), ('17栏', 'tax_free_amount', 3),
        ('本期免税额', 'tax_free_amount', 2), ('免税额', 'tax_free_amount', 1),
        # 第18栏：tax_free_micro
        ('第18栏', 'tax_free_micro', 3), ('18栏', 'tax_free_micro', 3),
        ('小微企业免税额', 'tax_free_micro', 2), ('小微免税额', 'tax_free_micro', 1),
        # 第19栏：tax_free_threshold
        ('第19栏', 'tax_free_threshold', 3), ('19栏', 'tax_free_threshold', 3),
        ('未达起征点免税额', 'tax_free_threshold', 2),
        # 第20栏：tax_due_total
        ('第20栏', 'tax_due_total', 3), ('20栏', 'tax_due_total', 3),
        ('应纳税额合计', 'tax_due_total', 2), ('应纳税合计', 'tax_due_total', 1),
        # 第21栏：tax_prepaid
        ('第21栏', 'tax_prepaid', 3), ('21栏', 'tax_prepaid', 3),
        ('本期预缴税额', 'tax_prepaid', 2), ('预缴税额', 'tax_prepaid', 1),
        # 第22栏：tax_supplement_refund
        ('第22栏', 'tax_supplement_refund', 3), ('22栏', 'tax_supplement_refund', 3),
        ('本期应补（退）税额', 'tax_supplement_refund', 2), ('应补退税额', 'tax_supplement_refund', 1),
        # 第23栏：city_maintenance_tax
        ('第23栏', 'city_maintenance_tax', 3), ('23栏', 'city_maintenance_tax', 3),
        ('城市维护建设税本期应补（退）税额', 'city_maintenance_tax', 2),
        ('城建税', 'city_maintenance_tax', 1),
        # 第24栏：education_surcharge
        ('第24栏', 'education_surcharge', 3), ('24栏', 'education_surcharge', 3),
        ('教育费附加本期应补（退）费额', 'education_surcharge', 2),
        ('教育费附加', 'education_surcharge', 1),
        # 第25栏：local_education_surcharge
        ('第25栏', 'local_education_surcharge', 3), ('25栏', 'local_education_surcharge', 3),
        ('地方教育附加本期应补（退）费额', 'local_education_surcharge', 2),
        ('地方教育附加', 'local_education_surcharge', 1),
    ]

    # 插入一般纳税人同义词（带scope）
    for phrase, col, pri in general_synonyms:
        cur.execute(
            "INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority, taxpayer_type, scope_view) VALUES (?,?,?,?,?)",
            (phrase, col, pri, '一般纳税人', 'vw_vat_return_general')
        )

    # 插入小规模纳税人同义词（带scope）
    for phrase, col, pri in small_synonyms:
        cur.execute(
            "INSERT OR IGNORE INTO vat_synonyms (phrase, column_name, priority, taxpayer_type, scope_view) VALUES (?,?,?,?,?)",
            (phrase, col, pri, '小规模纳税人', 'vw_vat_return_small')
        )

    count = cur.execute("SELECT COUNT(*) FROM vat_synonyms").fetchone()[0]
    print(f"  同义词: {count} 条")


def _seed_dictionaries(cur):
    """字典表示例数据"""
    industries = [
        ('I6510', '软件和信息技术服务业', 'I65'),
        ('I6520', '信息系统集成和物联网技术服务', 'I65'),
        ('F5191', '其他综合零售', 'F51'),
        ('C3311', '输配电及控制设备制造', 'C33'),
        ('K7010', '货币金融服务', 'K70'),
    ]
    cur.executemany("INSERT OR REPLACE INTO dim_industry VALUES (?,?,?)", industries)

    authorities = [
        ('13101040000', '国家税务总局上海市浦东新区税务局', '310115', '区县'),
        ('14403040000', '国家税务总局深圳市南山区税务局', '440305', '区县'),
        ('11101010000', '国家税务总局北京市海淀区税务局', '110108', '区县'),
    ]
    cur.executemany("INSERT OR REPLACE INTO dim_tax_authority VALUES (?,?,?,?)", authorities)

    regions = [
        ('310100', '上海市', '310000'),
        ('310115', '浦东新区', '310100'),
        ('440300', '深圳市', '440000'),
        ('440305', '南山区', '440300'),
    ]
    cur.executemany("INSERT OR REPLACE INTO dim_region VALUES (?,?,?)", regions)
    print("  字典表: 行业/税务机关/区划")


def _seed_metric_registry(cur):
    """指标注册表示例"""
    registries = [
        ('vat_tax_payable', '应纳税额', '增值税应纳税额（对齐口径）', '元', 'NUMERIC', 'vat', 1, 0),
        ('vat_output_tax', '销项税额', '一般纳税人销项税额', '元', 'NUMERIC', 'vat', 0, 0),
        ('vat_input_tax', '进项税额', '一般纳税人进项税额', '元', 'NUMERIC', 'vat', 0, 0),
        ('vat_sales_total', '销售额合计', '增值税销售额（对齐口径）', '元', 'NUMERIC', 'vat', 1, 0),
    ]
    cur.executemany("INSERT OR REPLACE INTO metric_registry VALUES (?,?,?,?,?,?,?,?)", registries)

    definitions = [
        ('vat_tax_payable', '一般纳税人', 'vat', 'vw_vat_return_general', '一般项目', '本月',
         'total_tax_payable', 'SUM', 'latest', '应纳税额', 1, 1),
        ('vat_tax_payable', '小规模纳税人', 'vat', 'vw_vat_return_small', '货物及劳务', '本期',
         'tax_due_total', 'SUM', 'latest', '应纳税额', 1, 1),
        ('vat_output_tax', '一般纳税人', 'vat', 'vw_vat_return_general', '一般项目', '本月',
         'output_tax', 'SUM', 'latest', '销项税额', 1, 1),
        ('vat_sales_total', '一般纳税人', 'vat', 'vw_vat_return_general', '一般项目', '本月',
         'sales_taxable_rate', 'SUM', 'latest', '销售额合计', 1, 1),
        ('vat_sales_total', '小规模纳税人', 'vat', 'vw_vat_return_small', '货物及劳务', '本期',
         'sales_3percent', 'SUM', 'latest', '销售额合计', 1, 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO metric_definition (metric_key, taxpayer_type, source_domain, source_view, "
        "dim_item_type, dim_time_range, value_expr, agg_func, revision_strategy, normalized_metric_name, priority, is_active) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", definitions
    )

    synonyms = [
        ('应纳税额', 'vat_tax_payable', 2),
        ('应纳增值税', 'vat_tax_payable', 1),
        ('销项税额', 'vat_output_tax', 2),
        ('进项税额', 'vat_input_tax', 2),
        ('销售额', 'vat_sales_total', 1),
    ]
    cur.executemany("INSERT OR REPLACE INTO metric_synonyms (phrase, metric_key, priority) VALUES (?,?,?)", synonyms)
    print("  指标注册表: metric_registry/definition/synonyms")


def _seed_eit_column_mappings(cur):
    """EIT年度45行 + 季度24行栏次映射"""
    annual_mappings = [
        (1, 'revenue', '营业收入'), (2, 'cost', '营业成本'),
        (3, 'taxes_surcharges', '税金及附加'), (4, 'selling_expenses', '销售费用'),
        (5, 'admin_expenses', '管理费用'), (6, 'rd_expenses', '研发费用'),
        (7, 'financial_expenses', '财务费用'), (8, 'other_gains', '其他收益'),
        (9, 'investment_income', '投资收益'), (10, 'net_exposure_hedge_gains', '净敞口套期收益'),
        (11, 'fair_value_change_gains', '公允价值变动收益'),
        (12, 'credit_impairment_loss', '信用减值损失'),
        (13, 'asset_impairment_loss', '资产减值损失'),
        (14, 'asset_disposal_gains', '资产处置收益'),
        (15, 'operating_profit', '营业利润'),
        (16, 'non_operating_income', '营业外收入'),
        (17, 'non_operating_expenses', '营业外支出'),
        (18, 'total_profit', '利润总额'),
        (19, 'less_foreign_income', '减：境外所得'),
        (20, 'add_tax_adjust_increase', '加：纳税调整增加额'),
        (21, 'less_tax_adjust_decrease', '减：纳税调整减少额'),
        (22, 'exempt_income_deduction_total', '减：免税、减计收入及加计扣除'),
        (23, 'add_foreign_tax_offset', '加：境外应税所得抵减境内亏损'),
        (24, 'adjusted_taxable_income', '纳税调整后所得'),
        (25, 'less_income_exemption', '减：所得减免'),
        (26, 'less_losses_carried_forward', '减：弥补以前年度亏损'),
        (27, 'less_taxable_income_deduction', '减：抵扣应纳税所得额'),
        (28, 'taxable_income', '应纳税所得额'),
        (29, 'tax_rate', '税率'),
        (30, 'tax_payable', '应纳所得税额'),
        (31, 'tax_credit_total', '减：减免所得税额'),
        (32, 'less_foreign_tax_credit', '减：抵免所得税额'),
        (33, 'tax_due', '应纳税额'),
        (34, 'add_foreign_tax_due', '加：境外所得应纳所得税额'),
        (35, 'less_foreign_tax_credit_amount', '减：境外所得抵免所得税额'),
        (36, 'actual_tax_payable', '实际应纳所得税额'),
        (37, 'less_prepaid_tax', '减：本年累计预缴所得税额'),
        (38, 'tax_payable_or_refund', '本年应补（退）所得税额'),
        (39, 'hq_share', '总机构分摊本年应补（退）所得税额'),
        (40, 'fiscal_central_share', '财政集中分配本年应补（退）所得税额'),
        (41, 'hq_dept_share', '总机构主体生产经营部门分摊本年应补（退）所得税额'),
        (42, 'less_ethnic_autonomous_relief', '减：民族自治地区企业所得税地方分享部分'),
        (43, 'less_audit_adjustment', '减：稽查查补（退）所得税额'),
        (44, 'less_special_adjustment', '减：特别纳税调整补（退）所得税额'),
        (45, 'final_tax_payable_or_refund', '本年实际应补（退）所得税额'),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO eit_annual_main_column_mapping (line_number, column_name, business_name) VALUES (?,?,?)",
        annual_mappings
    )

    quarter_mappings = [
        (1, 'revenue', '营业收入'), (2, 'cost', '营业成本'),
        (3, 'total_profit', '利润总额'),
        (4, 'add_specific_business_taxable_income', '加：特定业务计算的应纳税所得额'),
        (5, 'less_non_taxable_income', '减：不征税收入'),
        (6, 'less_accelerated_depreciation', '减：资产加速折旧、摊销（扣除）调减额'),
        (7, 'tax_free_income_deduction_total', '减：免税收入、减计收入、加计扣除'),
        (8, 'income_exemption_total', '减：所得减免'),
        (9, 'less_losses_carried_forward', '减：弥补以前年度亏损'),
        (10, 'actual_profit', '实际利润额'),
        (11, 'tax_rate', '税率'),
        (12, 'tax_payable', '应纳所得税额'),
        (13, 'tax_credit_total', '减：减免所得税额'),
        (14, 'less_prepaid_tax_current_year', '减：本年实际已缴纳所得税额'),
        (15, 'less_specific_business_prepaid', '减：特定业务预缴（征）所得税额'),
        (16, 'current_tax_payable_or_refund', '本期应补（退）所得税额'),
        (17, 'hq_share_total', '总机构本期分摊应补（退）所得税额'),
        (18, 'hq_share', '总机构分摊应补（退）所得税额'),
        (19, 'fiscal_central_share', '财政集中分配应补（退）所得税额'),
        (20, 'hq_business_dept_share', '总机构具有主体生产经营职能的部门分摊所得税额'),
        (21, 'branch_share_ratio', '分支机构本期分摊比例'),
        (22, 'branch_share_amount', '分支机构本期分摊应补（退）所得税额'),
        (23, 'ethnic_autonomous_relief_amount', '民族自治地区企业所得税地方分享部分减免金额'),
        (24, 'final_tax_payable_or_refund', '实际应补（退）所得税额'),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO eit_quarter_main_column_mapping (line_number, column_name, business_name) VALUES (?,?,?)",
        quarter_mappings
    )
    print("  EIT栏次映射: 年度45条 + 季度24条")


def _seed_eit_synonyms(cur):
    """EIT同义词：年度主表45栏 + 季度主表24栏"""
    # (phrase, column_name, priority, scope_view)
    annual_synonyms = [
        # 第1栏：revenue
        ('第1栏', 'revenue', 3), ('1栏', 'revenue', 3),
        ('营业收入', 'revenue', 2), ('收入', 'revenue', 1), ('主营收入', 'revenue', 1),
        # 第2栏：cost
        ('第2栏', 'cost', 3), ('2栏', 'cost', 3),
        ('营业成本', 'cost', 2), ('成本', 'cost', 1), ('主营业务成本', 'cost', 1),
        # 第3栏：taxes_surcharges
        ('第3栏', 'taxes_surcharges', 3), ('3栏', 'taxes_surcharges', 3),
        ('税金及附加', 'taxes_surcharges', 2), ('税金', 'taxes_surcharges', 1),
        # 第4栏：selling_expenses
        ('第4栏', 'selling_expenses', 3), ('4栏', 'selling_expenses', 3),
        ('销售费用', 'selling_expenses', 2), ('销售费', 'selling_expenses', 1),
        # 第5栏：admin_expenses
        ('第5栏', 'admin_expenses', 3), ('5栏', 'admin_expenses', 3),
        ('管理费用', 'admin_expenses', 2), ('管理费', 'admin_expenses', 1),
        # 第6栏：rd_expenses
        ('第6栏', 'rd_expenses', 3), ('6栏', 'rd_expenses', 3),
        ('研发费用', 'rd_expenses', 2), ('研发费', 'rd_expenses', 1),
        # 第7栏：financial_expenses
        ('第7栏', 'financial_expenses', 3), ('7栏', 'financial_expenses', 3),
        ('财务费用', 'financial_expenses', 2), ('财务费', 'financial_expenses', 1),
        # 第8栏：other_gains
        ('第8栏', 'other_gains', 3), ('8栏', 'other_gains', 3),
        ('其他收益', 'other_gains', 2),
        # 第9栏：investment_income
        ('第9栏', 'investment_income', 3), ('9栏', 'investment_income', 3),
        ('投资收益', 'investment_income', 2),
        # 第10栏：net_exposure_hedge_gains
        ('第10栏', 'net_exposure_hedge_gains', 3), ('10栏', 'net_exposure_hedge_gains', 3),
        ('净敞口套期收益', 'net_exposure_hedge_gains', 2),
        # 第11栏：fair_value_change_gains
        ('第11栏', 'fair_value_change_gains', 3), ('11栏', 'fair_value_change_gains', 3),
        ('公允价值变动收益', 'fair_value_change_gains', 2),
        # 第12栏：credit_impairment_loss
        ('第12栏', 'credit_impairment_loss', 3), ('12栏', 'credit_impairment_loss', 3),
        ('信用减值损失', 'credit_impairment_loss', 2),
        # 第13栏：asset_impairment_loss
        ('第13栏', 'asset_impairment_loss', 3), ('13栏', 'asset_impairment_loss', 3),
        ('资产减值损失', 'asset_impairment_loss', 2),
        # 第14栏：asset_disposal_gains
        ('第14栏', 'asset_disposal_gains', 3), ('14栏', 'asset_disposal_gains', 3),
        ('资产处置收益', 'asset_disposal_gains', 2),
        # 第15栏：operating_profit
        ('第15栏', 'operating_profit', 3), ('15栏', 'operating_profit', 3),
        ('营业利润', 'operating_profit', 2), ('经营利润', 'operating_profit', 1),
        # 第16栏：non_operating_income
        ('第16栏', 'non_operating_income', 3), ('16栏', 'non_operating_income', 3),
        ('营业外收入', 'non_operating_income', 2),
        # 第17栏：non_operating_expenses
        ('第17栏', 'non_operating_expenses', 3), ('17栏', 'non_operating_expenses', 3),
        ('营业外支出', 'non_operating_expenses', 2),
        # 第18栏：total_profit
        ('第18栏', 'total_profit', 3), ('18栏', 'total_profit', 3),
        ('利润总额', 'total_profit', 2), ('税前利润', 'total_profit', 1), ('会计利润', 'total_profit', 1),
    ]
    # 第19-45栏
    annual_synonyms_2 = [
        ('第19栏', 'less_foreign_income', 3), ('19栏', 'less_foreign_income', 3),
        ('境外所得', 'less_foreign_income', 2),
        ('第20栏', 'add_tax_adjust_increase', 3), ('20栏', 'add_tax_adjust_increase', 3),
        ('纳税调整增加额', 'add_tax_adjust_increase', 2), ('调增', 'add_tax_adjust_increase', 1),
        ('纳税调增', 'add_tax_adjust_increase', 1),
        ('第21栏', 'less_tax_adjust_decrease', 3), ('21栏', 'less_tax_adjust_decrease', 3),
        ('纳税调整减少额', 'less_tax_adjust_decrease', 2), ('调减', 'less_tax_adjust_decrease', 1),
        ('纳税调减', 'less_tax_adjust_decrease', 1),
        ('第22栏', 'exempt_income_deduction_total', 3), ('22栏', 'exempt_income_deduction_total', 3),
        ('免税减计收入加计扣除', 'exempt_income_deduction_total', 2),
        ('第23栏', 'add_foreign_tax_offset', 3), ('23栏', 'add_foreign_tax_offset', 3),
        ('境外应税所得抵减境内亏损', 'add_foreign_tax_offset', 2),
        ('第24栏', 'adjusted_taxable_income', 3), ('24栏', 'adjusted_taxable_income', 3),
        ('纳税调整后所得', 'adjusted_taxable_income', 2), ('调整后所得', 'adjusted_taxable_income', 1),
        ('第25栏', 'less_income_exemption', 3), ('25栏', 'less_income_exemption', 3),
        ('所得减免', 'less_income_exemption', 2),
        ('第26栏', 'less_losses_carried_forward', 3), ('26栏', 'less_losses_carried_forward', 3),
        ('弥补以前年度亏损', 'less_losses_carried_forward', 2), ('弥补亏损', 'less_losses_carried_forward', 1),
        ('补亏', 'less_losses_carried_forward', 1),
        ('第27栏', 'less_taxable_income_deduction', 3), ('27栏', 'less_taxable_income_deduction', 3),
        ('抵扣应纳税所得额', 'less_taxable_income_deduction', 2),
        ('第28栏', 'taxable_income', 3), ('28栏', 'taxable_income', 3),
        ('应纳税所得额', 'taxable_income', 2), ('应税所得', 'taxable_income', 1),
        ('第29栏', 'tax_rate', 3), ('29栏', 'tax_rate', 3),
        ('税率', 'tax_rate', 2), ('所得税率', 'tax_rate', 1),
        ('第30栏', 'tax_payable', 3), ('30栏', 'tax_payable', 3),
        ('应纳所得税额', 'tax_payable', 2), ('应纳税额', 'tax_payable', 1),
        ('第31栏', 'tax_credit_total', 3), ('31栏', 'tax_credit_total', 3),
        ('减免所得税额', 'tax_credit_total', 2), ('减免税额', 'tax_credit_total', 1),
        ('第32栏', 'less_foreign_tax_credit', 3), ('32栏', 'less_foreign_tax_credit', 3),
        ('抵免所得税额', 'less_foreign_tax_credit', 2),
        ('第33栏', 'tax_due', 3), ('33栏', 'tax_due', 3),
        ('应纳税额（33栏）', 'tax_due', 2),
        ('第34栏', 'add_foreign_tax_due', 3), ('34栏', 'add_foreign_tax_due', 3),
        ('境外所得应纳所得税额', 'add_foreign_tax_due', 2),
        ('第35栏', 'less_foreign_tax_credit_amount', 3), ('35栏', 'less_foreign_tax_credit_amount', 3),
        ('境外所得抵免所得税额', 'less_foreign_tax_credit_amount', 2),
        ('第36栏', 'actual_tax_payable', 3), ('36栏', 'actual_tax_payable', 3),
        ('实际应纳所得税额', 'actual_tax_payable', 2), ('实际应纳税', 'actual_tax_payable', 1),
        ('第37栏', 'less_prepaid_tax', 3), ('37栏', 'less_prepaid_tax', 3),
        ('本年累计预缴所得税额', 'less_prepaid_tax', 2), ('预缴税额', 'less_prepaid_tax', 1),
        ('第38栏', 'tax_payable_or_refund', 3), ('38栏', 'tax_payable_or_refund', 3),
        ('本年应补退所得税额', 'tax_payable_or_refund', 2), ('应补退税', 'tax_payable_or_refund', 1),
        ('第39栏', 'hq_share', 3), ('39栏', 'hq_share', 3),
        ('总机构分摊', 'hq_share', 2),
        ('第40栏', 'fiscal_central_share', 3), ('40栏', 'fiscal_central_share', 3),
        ('财政集中分配', 'fiscal_central_share', 2),
        ('第41栏', 'hq_dept_share', 3), ('41栏', 'hq_dept_share', 3),
        ('总机构主体部门分摊', 'hq_dept_share', 2),
        ('第42栏', 'less_ethnic_autonomous_relief', 3), ('42栏', 'less_ethnic_autonomous_relief', 3),
        ('民族自治地方减免', 'less_ethnic_autonomous_relief', 2),
        ('第43栏', 'less_audit_adjustment', 3), ('43栏', 'less_audit_adjustment', 3),
        ('稽查查补退税额', 'less_audit_adjustment', 2),
        ('第44栏', 'less_special_adjustment', 3), ('44栏', 'less_special_adjustment', 3),
        ('特别纳税调整补退税', 'less_special_adjustment', 2),
        ('第45栏', 'final_tax_payable_or_refund', 3), ('45栏', 'final_tax_payable_or_refund', 3),
        ('本年实际应补退所得税额', 'final_tax_payable_or_refund', 2),
        ('最终应补退税', 'final_tax_payable_or_refund', 1), ('实际应补退', 'final_tax_payable_or_refund', 1),
    ]

    # 季度主表同义词
    quarter_synonyms = [
        ('第1栏', 'revenue', 3), ('1栏', 'revenue', 3),
        ('营业收入', 'revenue', 2), ('收入', 'revenue', 1),
        ('第2栏', 'cost', 3), ('2栏', 'cost', 3),
        ('营业成本', 'cost', 2), ('成本', 'cost', 1),
        ('第3栏', 'total_profit', 3), ('3栏', 'total_profit', 3),
        ('利润总额', 'total_profit', 2), ('利润', 'total_profit', 1), ('税前利润', 'total_profit', 1),
        ('第4栏', 'add_specific_business_taxable_income', 3), ('4栏', 'add_specific_business_taxable_income', 3),
        ('特定业务计算的应纳税所得额', 'add_specific_business_taxable_income', 2),
        ('特定业务所得', 'add_specific_business_taxable_income', 1),
        ('第5栏', 'less_non_taxable_income', 3), ('5栏', 'less_non_taxable_income', 3),
        ('不征税收入', 'less_non_taxable_income', 2),
        ('第6栏', 'less_accelerated_depreciation', 3), ('6栏', 'less_accelerated_depreciation', 3),
        ('资产加速折旧调减额', 'less_accelerated_depreciation', 2), ('加速折旧', 'less_accelerated_depreciation', 1),
        ('第7栏', 'tax_free_income_deduction_total', 3), ('7栏', 'tax_free_income_deduction_total', 3),
        ('免税收入减计收入加计扣除', 'tax_free_income_deduction_total', 2),
        ('第8栏', 'income_exemption_total', 3), ('8栏', 'income_exemption_total', 3),
        ('所得减免', 'income_exemption_total', 2),
        ('第9栏', 'less_losses_carried_forward', 3), ('9栏', 'less_losses_carried_forward', 3),
        ('弥补以前年度亏损', 'less_losses_carried_forward', 2), ('弥补亏损', 'less_losses_carried_forward', 1),
        ('第10栏', 'actual_profit', 3), ('10栏', 'actual_profit', 3),
        ('实际利润额', 'actual_profit', 2), ('实际利润', 'actual_profit', 1),
        ('第11栏', 'tax_rate', 3), ('11栏', 'tax_rate', 3),
        ('税率', 'tax_rate', 2), ('所得税率', 'tax_rate', 1),
        ('第12栏', 'tax_payable', 3), ('12栏', 'tax_payable', 3),
        ('应纳所得税额', 'tax_payable', 2), ('应纳税额', 'tax_payable', 1),
        ('第13栏', 'tax_credit_total', 3), ('13栏', 'tax_credit_total', 3),
        ('减免所得税额', 'tax_credit_total', 2), ('减免税额', 'tax_credit_total', 1),
        ('第14栏', 'less_prepaid_tax_current_year', 3), ('14栏', 'less_prepaid_tax_current_year', 3),
        ('本年实际已缴纳所得税额', 'less_prepaid_tax_current_year', 2),
        ('已预缴', 'less_prepaid_tax_current_year', 1),
        ('第15栏', 'less_specific_business_prepaid', 3), ('15栏', 'less_specific_business_prepaid', 3),
        ('特定业务预缴所得税额', 'less_specific_business_prepaid', 2),
        ('第16栏', 'current_tax_payable_or_refund', 3), ('16栏', 'current_tax_payable_or_refund', 3),
        ('本期应补退所得税额', 'current_tax_payable_or_refund', 2),
        ('应补退', 'current_tax_payable_or_refund', 1),
        ('第17栏', 'hq_share_total', 3), ('17栏', 'hq_share_total', 3),
        ('总机构本期分摊应补退所得税额', 'hq_share_total', 2),
        ('第18栏', 'hq_share', 3), ('18栏', 'hq_share', 3),
        ('总机构分摊应补退所得税额', 'hq_share', 2),
        ('第19栏', 'fiscal_central_share', 3), ('19栏', 'fiscal_central_share', 3),
        ('财政集中分配应补退所得税额', 'fiscal_central_share', 2),
        ('第20栏', 'hq_business_dept_share', 3), ('20栏', 'hq_business_dept_share', 3),
        ('总机构主体生产经营部门分摊', 'hq_business_dept_share', 2),
        ('第21栏', 'branch_share_ratio', 3), ('21栏', 'branch_share_ratio', 3),
        ('分支机构本期分摊比例', 'branch_share_ratio', 2),
        ('第22栏', 'branch_share_amount', 3), ('22栏', 'branch_share_amount', 3),
        ('分支机构本期分摊应补退所得税额', 'branch_share_amount', 2),
        ('第23栏', 'ethnic_autonomous_relief_amount', 3), ('23栏', 'ethnic_autonomous_relief_amount', 3),
        ('民族自治地区减免金额', 'ethnic_autonomous_relief_amount', 2),
        ('第24栏', 'final_tax_payable_or_refund', 3), ('24栏', 'final_tax_payable_or_refund', 3),
        ('实际应补退所得税额', 'final_tax_payable_or_refund', 2),
        ('最终应补退', 'final_tax_payable_or_refund', 1),
    ]

    for phrase, col, pri in annual_synonyms + annual_synonyms_2:
        cur.execute(
            "INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES (?,?,?,?)",
            (phrase, col, pri, 'vw_eit_annual_main')
        )
    for phrase, col, pri in quarter_synonyms:
        cur.execute(
            "INSERT OR IGNORE INTO eit_synonyms (phrase, column_name, priority, scope_view) VALUES (?,?,?,?)",
            (phrase, col, pri, 'vw_eit_quarter_main')
        )
    count = cur.execute("SELECT COUNT(*) FROM eit_synonyms").fetchone()[0]
    print(f"  EIT同义词: {count} 条")


def _seed_eit_metric_registry(cur):
    """EIT指标注册表"""
    registries = [
        ('eit_total_profit', '利润总额', '企业所得税利润总额', '元', 'NUMERIC', 'eit', 0, 1),
        ('eit_taxable_income', '应纳税所得额', '企业所得税应纳税所得额', '元', 'NUMERIC', 'eit', 0, 1),
        ('eit_tax_payable', '应纳所得税额', '企业所得税应纳所得税额', '元', 'NUMERIC', 'eit', 0, 1),
        ('eit_actual_tax', '实际应纳所得税额', '企业所得税实际应纳所得税额', '元', 'NUMERIC', 'eit', 0, 1),
        ('eit_revenue', '营业收入', '企业所得税营业收入', '元', 'NUMERIC', 'eit', 0, 1),
    ]
    cur.executemany("INSERT OR REPLACE INTO metric_registry VALUES (?,?,?,?,?,?,?,?)", registries)

    definitions = [
        ('eit_total_profit', None, 'eit', 'vw_eit_annual_main', None, None,
         'total_profit', 'SUM', 'latest', '利润总额', 1, 1),
        ('eit_taxable_income', None, 'eit', 'vw_eit_annual_main', None, None,
         'taxable_income', 'SUM', 'latest', '应纳税所得额', 1, 1),
        ('eit_tax_payable', None, 'eit', 'vw_eit_annual_main', None, None,
         'tax_payable', 'SUM', 'latest', '应纳所得税额', 1, 1),
        ('eit_actual_tax', None, 'eit', 'vw_eit_annual_main', None, None,
         'actual_tax_payable', 'SUM', 'latest', '实际应纳所得税额', 1, 1),
        ('eit_revenue', None, 'eit', 'vw_eit_annual_main', None, None,
         'revenue', 'SUM', 'latest', '营业收入', 1, 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO metric_definition (metric_key, taxpayer_type, source_domain, source_view, "
        "dim_item_type, dim_time_range, value_expr, agg_func, revision_strategy, normalized_metric_name, priority, is_active) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", definitions
    )

    synonyms = [
        ('利润总额', 'eit_total_profit', 2),
        ('应纳税所得额', 'eit_taxable_income', 2),
        ('应纳所得税额', 'eit_tax_payable', 2),
        ('实际应纳所得税额', 'eit_actual_tax', 2),
    ]
    cur.executemany("INSERT OR REPLACE INTO metric_synonyms (phrase, metric_key, priority) VALUES (?,?,?)", synonyms)
    print("  EIT指标注册表: metric_registry/definition/synonyms")


def _seed_account_master(cur):
    """科目字典：常用会计科目（企业会计准则 + 小企业会计准则）"""
    # (account_code, account_name, level, category, balance_direction, is_gaap, is_small)
    accounts = [
        # 资产类
        ('1001', '库存现金', 1, '资产', '借', 1, 1),
        ('1002', '银行存款', 1, '资产', '借', 1, 1),
        ('1012', '其他货币资金', 1, '资产', '借', 1, 1),
        ('1101', '交易性金融资产', 1, '资产', '借', 1, 0),
        ('1121', '应收票据', 1, '资产', '借', 1, 1),
        ('1122', '应收账款', 1, '资产', '借', 1, 1),
        ('1123', '预付账款', 1, '资产', '借', 1, 1),
        ('1131', '应收股利', 1, '资产', '借', 1, 1),
        ('1132', '应收利息', 1, '资产', '借', 1, 1),
        ('1221', '其他应收款', 1, '资产', '借', 1, 1),
        ('1401', '材料采购', 1, '资产', '借', 1, 1),
        ('1403', '原材料', 1, '资产', '借', 1, 1),
        ('1405', '库存商品', 1, '资产', '借', 1, 1),
        ('1501', '持有至到期投资', 1, '资产', '借', 1, 0),
        ('1511', '长期股权投资', 1, '资产', '借', 1, 1),
        ('1601', '固定资产', 1, '资产', '借', 1, 1),
        ('1602', '累计折旧', 1, '资产', '贷', 1, 1),
        ('1604', '在建工程', 1, '资产', '借', 1, 1),
        ('1701', '无形资产', 1, '资产', '借', 1, 1),
        ('1702', '累计摊销', 1, '资产', '贷', 1, 1),
        ('1801', '长期待摊费用', 1, '资产', '借', 1, 1),
        ('1811', '递延所得税资产', 1, '资产', '借', 1, 0),
        # 负债类
        ('2001', '短期借款', 1, '负债', '贷', 1, 1),
        ('2201', '应付票据', 1, '负债', '贷', 1, 1),
        ('2202', '应付账款', 1, '负债', '贷', 1, 1),
        ('2203', '预收账款', 1, '负债', '贷', 1, 1),
        ('2211', '应付职工薪酬', 1, '负债', '贷', 1, 1),
        ('2221', '应交税费', 1, '负债', '贷', 1, 1),
        ('222101', '应交增值税', 2, '负债', '贷', 1, 1),
        ('222102', '未交增值税', 2, '负债', '贷', 1, 1),
        ('222103', '应交企业所得税', 2, '负债', '贷', 1, 1),
        ('2231', '应付利息', 1, '负债', '贷', 1, 1),
        ('2232', '应付股利', 1, '负债', '贷', 1, 1),
        ('2241', '其他应付款', 1, '负债', '贷', 1, 1),
        ('2501', '长期借款', 1, '负债', '贷', 1, 1),
        ('2701', '递延所得税负债', 1, '负债', '贷', 1, 0),
        # 权益类
        ('4001', '实收资本', 1, '权益', '贷', 1, 1),
        ('4002', '资本公积', 1, '权益', '贷', 1, 1),
        ('4101', '盈余公积', 1, '权益', '贷', 1, 1),
        ('4103', '本年利润', 1, '权益', '贷', 1, 1),
        ('4104', '利润分配', 1, '权益', '贷', 1, 1),
        # 成本类
        ('5001', '生产成本', 1, '成本', '借', 1, 1),
        ('5101', '制造费用', 1, '成本', '借', 1, 1),
        # 损益类
        ('6001', '主营业务收入', 1, '损益', '贷', 1, 1),
        ('6051', '其他业务收入', 1, '损益', '贷', 1, 1),
        ('6111', '投资收益', 1, '损益', '贷', 1, 0),
        ('6301', '营业外收入', 1, '损益', '贷', 1, 1),
        ('6401', '主营业务成本', 1, '损益', '借', 1, 1),
        ('6402', '其他业务成本', 1, '损益', '借', 1, 1),
        ('6403', '营业税金及附加', 1, '损益', '借', 1, 1),
        ('6601', '销售费用', 1, '损益', '借', 1, 1),
        ('6602', '管理费用', 1, '损益', '借', 1, 1),
        ('5602', '管理费用', 1, '损益', '借', 0, 1),
        ('6603', '财务费用', 1, '损益', '借', 1, 1),
        ('6604', '研发费用', 1, '损益', '借', 1, 0),
        ('6701', '资产减值损失', 1, '损益', '借', 1, 0),
        ('6711', '营业外支出', 1, '损益', '借', 1, 1),
        ('6801', '所得税费用', 1, '损益', '借', 1, 1),
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO account_master
        (account_code, account_name, level, category, balance_direction, is_gaap, is_small)
        VALUES (?,?,?,?,?,?,?)""",
        accounts
    )
    print(f"  科目字典: {len(accounts)} 条")


def _seed_account_synonyms(cur):
    """科目同义词：口语化表达 → 标准科目名称"""
    # (phrase, account_code, account_name, priority, applicable_standards)
    synonyms = [
        ('现金', None, '库存现金', 2, None),
        ('银行', None, '银行存款', 1, None),
        ('银行存款', None, '银行存款', 2, None),
        ('应收', None, '应收账款', 1, None),
        ('应收款', None, '应收账款', 1, None),
        ('应付', None, '应付账款', 1, None),
        ('应付款', None, '应付账款', 1, None),
        ('预付', None, '预付账款', 1, None),
        ('预收', None, '预收账款', 1, None),
        ('固定资产', None, '固定资产', 2, None),
        ('折旧', None, '累计折旧', 1, None),
        ('累计折旧', None, '累计折旧', 2, None),
        ('无形资产', None, '无形资产', 2, None),
        ('摊销', None, '累计摊销', 1, None),
        ('原材料', None, '原材料', 2, None),
        ('库存商品', None, '库存商品', 2, None),
        ('存货', None, '库存商品', 1, None),
        ('短期借款', None, '短期借款', 2, None),
        ('长期借款', None, '长期借款', 2, None),
        ('应付职工薪酬', None, '应付职工薪酬', 2, None),
        ('工资', None, '应付职工薪酬', 1, None),
        ('薪酬', None, '应付职工薪酬', 1, None),
        ('应交税费', None, '应交税费', 2, None),
        ('应交增值税', '222101', '应交增值税', 2, None),
        ('未交增值税', '222102', '未交增值税', 2, None),
        ('应交所得税', '222103', '应交企业所得税', 2, None),
        ('实收资本', None, '实收资本', 2, None),
        ('资本公积', None, '资本公积', 2, None),
        ('盈余公积', None, '盈余公积', 2, None),
        ('本年利润', None, '本年利润', 2, None),
        ('利润分配', None, '利润分配', 2, None),
        ('收入', None, '主营业务收入', 1, None),
        ('主营业务收入', None, '主营业务收入', 2, None),
        ('主营业务成本', None, '主营业务成本', 2, None),
        ('销售费用', None, '销售费用', 2, None),
        ('管理费用', None, '管理费用', 2, None),
        ('财务费用', None, '财务费用', 2, None),
        ('研发费用', None, '研发费用', 2, '企业会计准则'),
        ('所得税费用', None, '所得税费用', 2, None),
        ('营业外收入', None, '营业外收入', 2, None),
        ('营业外支出', None, '营业外支出', 2, None),
        ('在建工程', None, '在建工程', 2, None),
        ('长期股权投资', None, '长期股权投资', 2, None),
        ('其他应收款', None, '其他应收款', 2, None),
        ('其他应付款', None, '其他应付款', 2, None),
        # P3: 子科目同义词（G7）
        ('管理费用-办公费', None, '管理费用-办公费', 3, None),
        ('管理费用办公费', None, '管理费用-办公费', 3, None),
        ('办公费', None, '管理费用-办公费', 1, None),
        ('管理费用-差旅费', None, '管理费用-差旅费', 3, None),
        ('差旅费', None, '管理费用-差旅费', 1, None),
        ('管理费用-业务招待费', None, '管理费用-业务招待费', 3, None),
        ('业务招待费', None, '管理费用-业务招待费', 1, None),
        ('销售费用-广告费', None, '销售费用-广告费', 3, None),
        ('广告费', None, '销售费用-广告费', 1, None),
        ('销售费用-运输费', None, '销售费用-运输费', 3, None),
        ('财务费用-利息支出', None, '财务费用-利息支出', 3, None),
        ('利息支出', None, '财务费用-利息支出', 1, None),
        ('财务费用-利息收入', None, '财务费用-利息收入', 3, None),
        ('财务费用-手续费', None, '财务费用-手续费', 3, None),
        ('手续费', None, '财务费用-手续费', 1, None),
        ('应交税费-应交增值税', '222101', '应交增值税', 3, None),
        ('应交税费-未交增值税', '222102', '未交增值税', 3, None),
        ('应交税费-应交企业所得税', '222103', '应交企业所得税', 3, None),
        ('应交税费-应交城市维护建设税', None, '应交城市维护建设税', 3, None),
        ('进项税额转出', None, '应交增值税-进项税额转出', 2, None),
        ('主营业务收入-内销', None, '主营业务收入-内销', 3, None),
        ('主营业务收入-外销', None, '主营业务收入-外销', 3, None),
    ]
    for phrase, code, name, pri, std in synonyms:
        cur.execute(
            """INSERT OR IGNORE INTO account_synonyms
            (phrase, account_code, account_name, priority, applicable_standards)
            VALUES (?,?,?,?,?)""",
            (phrase, code, name, pri, std)
        )
    count = cur.execute("SELECT COUNT(*) FROM account_synonyms").fetchone()[0]
    print(f"  科目同义词: {count} 条")


def _seed_account_balance_column_mapping(cur):
    """科目余额表ETL列映射"""
    mappings = [
        ('本币期初余额', 'opening_balance', '期初余额（本币）'),
        ('本币借方发生', 'debit_amount', '本期借方发生额（本币）'),
        ('本币贷方发生', 'credit_amount', '本期贷方发生额（本币）'),
        ('本币期末余额', 'closing_balance', '期末余额（本币）'),
        ('期初余额', 'opening_balance', '期初余额'),
        ('借方发生额', 'debit_amount', '借方发生额'),
        ('贷方发生额', 'credit_amount', '贷方发生额'),
        ('期末余额', 'closing_balance', '期末余额'),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO account_balance_column_mapping (source_column, target_field, description) VALUES (?,?,?)",
        mappings
    )
    print(f"  科目余额列映射: {len(mappings)} 条")


def _seed_bs_item_dict(cur):
    """资产负债表项目字典：企业会计准则(ASBE) + 小企业会计准则(ASSE)"""
    asbe_items = [
        ('ASBE', 'CASH', '货币资金', 1, 'ASSET', 10, 0),
        ('ASBE', 'TRADING_FINANCIAL_ASSETS', '交易性金融资产', 2, 'ASSET', 20, 0),
        ('ASBE', 'DERIVATIVE_FINANCIAL_ASSETS', '衍生金融资产', 3, 'ASSET', 30, 0),
        ('ASBE', 'NOTES_RECEIVABLE', '应收票据', 4, 'ASSET', 40, 0),
        ('ASBE', 'ACCOUNTS_RECEIVABLE', '应收账款', 5, 'ASSET', 50, 0),
        ('ASBE', 'ACCOUNTS_RECEIVABLE_FINANCING', '应收账款融资', 6, 'ASSET', 60, 0),
        ('ASBE', 'PREPAYMENTS', '预付账款', 7, 'ASSET', 70, 0),
        ('ASBE', 'OTHER_RECEIVABLES', '其他应收款', 8, 'ASSET', 80, 0),
        ('ASBE', 'INVENTORY', '存货', 9, 'ASSET', 90, 0),
        ('ASBE', 'CONTRACT_ASSETS', '合同资产', 10, 'ASSET', 100, 0),
        ('ASBE', 'HELD_FOR_SALE_ASSETS', '持有待售资产', 11, 'ASSET', 110, 0),
        ('ASBE', 'CURRENT_PORTION_NON_CURRENT_ASSETS', '一年内到期的非流动资产', 12, 'ASSET', 120, 0),
        ('ASBE', 'OTHER_CURRENT_ASSETS', '其他流动资产', 13, 'ASSET', 130, 0),
        ('ASBE', 'CURRENT_ASSETS', '流动资产合计', 14, 'ASSET', 140, 1),
        ('ASBE', 'DEBT_INVESTMENTS', '债权投资', 15, 'ASSET', 150, 0),
        ('ASBE', 'OTHER_DEBT_INVESTMENTS', '其他债权投资', 16, 'ASSET', 160, 0),
        ('ASBE', 'LONG_TERM_RECEIVABLES', '长期应收款', 17, 'ASSET', 170, 0),
        ('ASBE', 'LONG_TERM_EQUITY_INVESTMENTS', '长期股权投资', 18, 'ASSET', 180, 0),
        ('ASBE', 'OTHER_EQUITY_INSTRUMENTS_INVEST', '其他权益工具投资', 19, 'ASSET', 190, 0),
        ('ASBE', 'OTHER_NON_CURRENT_FINANCIAL_ASSETS', '其他非流动金融资产', 20, 'ASSET', 200, 0),
        ('ASBE', 'INVESTMENT_PROPERTY', '投资性房地产', 21, 'ASSET', 210, 0),
        ('ASBE', 'FIXED_ASSETS', '固定资产', 22, 'ASSET', 220, 0),
        ('ASBE', 'CONSTRUCTION_IN_PROGRESS', '在建工程', 23, 'ASSET', 230, 0),
        ('ASBE', 'PRODUCTIVE_BIOLOGICAL_ASSETS', '生产性生物资产', 24, 'ASSET', 240, 0),
        ('ASBE', 'OIL_AND_GAS_ASSETS', '油气资产', 25, 'ASSET', 250, 0),
        ('ASBE', 'RIGHT_OF_USE_ASSETS', '使用权资产', 26, 'ASSET', 260, 0),
        ('ASBE', 'INTANGIBLE_ASSETS', '无形资产', 27, 'ASSET', 270, 0),
        ('ASBE', 'DEVELOPMENT_EXPENDITURE', '开发支出', 28, 'ASSET', 280, 0),
        ('ASBE', 'GOODWILL', '商誉', 29, 'ASSET', 290, 0),
        ('ASBE', 'LONG_TERM_DEFERRED_EXPENSES', '长期待摊费用', 30, 'ASSET', 300, 0),
        ('ASBE', 'DEFERRED_TAX_ASSETS', '递延所得税资产', 31, 'ASSET', 310, 0),
        ('ASBE', 'OTHER_NON_CURRENT_ASSETS', '其他非流动资产', 32, 'ASSET', 320, 0),
        ('ASBE', 'NON_CURRENT_ASSETS', '非流动资产合计', 33, 'ASSET', 330, 1),
        ('ASBE', 'ASSETS', '资产总计', 34, 'ASSET', 340, 1),
        ('ASBE', 'SHORT_TERM_LOANS', '短期借款', 35, 'LIABILITY', 350, 0),
        ('ASBE', 'TRADING_FINANCIAL_LIABILITIES', '交易性金融负债', 36, 'LIABILITY', 360, 0),
        ('ASBE', 'DERIVATIVE_FINANCIAL_LIABILITIES', '衍生金融负债', 37, 'LIABILITY', 370, 0),
        ('ASBE', 'NOTES_PAYABLE', '应付票据', 38, 'LIABILITY', 380, 0),
        ('ASBE', 'ACCOUNTS_PAYABLE', '应付账款', 39, 'LIABILITY', 390, 0),
        ('ASBE', 'ADVANCES_FROM_CUSTOMERS', '预收款项', 40, 'LIABILITY', 400, 0),
        ('ASBE', 'CONTRACT_LIABILITIES', '合同负债', 41, 'LIABILITY', 410, 0),
        ('ASBE', 'EMPLOYEE_BENEFITS_PAYABLE', '应付职工薪酬', 42, 'LIABILITY', 420, 0),
        ('ASBE', 'TAXES_PAYABLE', '应交税费', 43, 'LIABILITY', 430, 0),
        ('ASBE', 'OTHER_PAYABLES', '其他应付款', 44, 'LIABILITY', 440, 0),
        ('ASBE', 'HELD_FOR_SALE_LIABILITIES', '持有待售负债', 45, 'LIABILITY', 450, 0),
        ('ASBE', 'CURRENT_PORTION_NON_CURRENT_LIABILITIES', '一年内到期的非流动负债', 46, 'LIABILITY', 460, 0),
        ('ASBE', 'OTHER_CURRENT_LIABILITIES', '其他流动负债', 47, 'LIABILITY', 470, 0),
        ('ASBE', 'CURRENT_LIABILITIES', '流动负债合计', 48, 'LIABILITY', 480, 1),
        # PLACEHOLDER_ASBE_PART2
        ('ASBE', 'LONG_TERM_LOANS', '长期借款', 49, 'LIABILITY', 490, 0),
        ('ASBE', 'BONDS_PAYABLE', '应付债券', 50, 'LIABILITY', 500, 0),
        ('ASBE', 'LEASE_LIABILITIES', '租赁负债', 51, 'LIABILITY', 510, 0),
        ('ASBE', 'LONG_TERM_PAYABLES', '长期应付款', 52, 'LIABILITY', 520, 0),
        ('ASBE', 'PROVISIONS', '预计负债', 53, 'LIABILITY', 530, 0),
        ('ASBE', 'DEFERRED_INCOME', '递延收益', 54, 'LIABILITY', 540, 0),
        ('ASBE', 'DEFERRED_TAX_LIABILITIES', '递延所得税负债', 55, 'LIABILITY', 550, 0),
        ('ASBE', 'OTHER_NON_CURRENT_LIABILITIES', '其他非流动负债', 56, 'LIABILITY', 560, 0),
        ('ASBE', 'NON_CURRENT_LIABILITIES', '非流动负债合计', 57, 'LIABILITY', 570, 1),
        ('ASBE', 'LIABILITIES', '负债合计', 58, 'LIABILITY', 580, 1),
        ('ASBE', 'SHARE_CAPITAL', '实收资本（或股本）', 59, 'EQUITY', 590, 0),
        ('ASBE', 'CAPITAL_RESERVE', '资本公积', 60, 'EQUITY', 600, 0),
        ('ASBE', 'TREASURY_STOCK', '减：库存股', 61, 'EQUITY', 610, 0),
        ('ASBE', 'OTHER_COMPREHENSIVE_INCOME', '其他综合收益', 62, 'EQUITY', 620, 0),
        ('ASBE', 'SPECIAL_RESERVE', '专项储备', 63, 'EQUITY', 630, 0),
        ('ASBE', 'SURPLUS_RESERVE', '盈余公积', 64, 'EQUITY', 640, 0),
        ('ASBE', 'RETAINED_EARNINGS', '未分配利润', 65, 'EQUITY', 650, 0),
        ('ASBE', 'EQUITY', '所有者权益合计', 66, 'EQUITY', 660, 1),
        ('ASBE', 'LIABILITIES_AND_EQUITY', '负债和所有者权益总计', 67, 'LIABILITY_EQUITY', 670, 1),
    ]
    asbe_part2 = [
        # 非流动负债 + 权益 (continued from above)
    ]

    asse_items = [
        ('ASSE', 'CASH', '货币资金', 1, 'ASSET', 10, 0),
        ('ASSE', 'SHORT_TERM_INVESTMENTS', '短期投资', 2, 'ASSET', 20, 0),
        ('ASSE', 'NOTES_RECEIVABLE', '应收票据', 3, 'ASSET', 30, 0),
        ('ASSE', 'ACCOUNTS_RECEIVABLE', '应收账款', 4, 'ASSET', 40, 0),
        ('ASSE', 'PREPAYMENTS', '预付账款', 5, 'ASSET', 50, 0),
        ('ASSE', 'DIVIDENDS_RECEIVABLE', '应收股利', 6, 'ASSET', 60, 0),
        ('ASSE', 'INTEREST_RECEIVABLE', '应收利息', 7, 'ASSET', 70, 0),
        ('ASSE', 'OTHER_RECEIVABLES', '其他应收款', 8, 'ASSET', 80, 0),
        ('ASSE', 'INVENTORY', '存货', 9, 'ASSET', 90, 0),
        ('ASSE', 'RAW_MATERIALS', '其中：原材料', 10, 'ASSET', 100, 0),
        ('ASSE', 'WORK_IN_PROCESS', '在产品', 11, 'ASSET', 110, 0),
        ('ASSE', 'FINISHED_GOODS', '库存商品', 12, 'ASSET', 120, 0),
        ('ASSE', 'TURNOVER_MATERIALS', '周转材料', 13, 'ASSET', 130, 0),
        ('ASSE', 'OTHER_CURRENT_ASSETS', '其他流动资产', 14, 'ASSET', 140, 0),
        ('ASSE', 'CURRENT_ASSETS', '流动资产合计', 15, 'ASSET', 150, 1),
        ('ASSE', 'LONG_TERM_BOND_INVESTMENTS', '长期债券投资', 16, 'ASSET', 160, 0),
        ('ASSE', 'LONG_TERM_EQUITY_INVESTMENTS', '长期股权投资', 17, 'ASSET', 170, 0),
        ('ASSE', 'FIXED_ASSETS_ORIGINAL', '固定资产原价', 18, 'ASSET', 180, 0),
        ('ASSE', 'ACCUMULATED_DEPRECIATION', '减：累计折旧', 19, 'ASSET', 190, 0),
        ('ASSE', 'FIXED_ASSETS_NET', '固定资产账面价值', 20, 'ASSET', 200, 0),
        ('ASSE', 'CONSTRUCTION_IN_PROGRESS', '在建工程', 21, 'ASSET', 210, 0),
        ('ASSE', 'ENGINEERING_MATERIALS', '工程物资', 22, 'ASSET', 220, 0),
        ('ASSE', 'FIXED_ASSETS_LIQUIDATION', '固定资产清理', 23, 'ASSET', 230, 0),
        ('ASSE', 'PRODUCTIVE_BIOLOGICAL_ASSETS', '生产性生物资产', 24, 'ASSET', 240, 0),
        ('ASSE', 'INTANGIBLE_ASSETS', '无形资产', 25, 'ASSET', 250, 0),
        ('ASSE', 'DEVELOPMENT_EXPENDITURE', '开发支出', 26, 'ASSET', 260, 0),
        ('ASSE', 'LONG_TERM_DEFERRED_EXPENSES', '长期待摊费用', 27, 'ASSET', 270, 0),
        ('ASSE', 'OTHER_NON_CURRENT_ASSETS', '其他非流动资产', 28, 'ASSET', 280, 0),
        ('ASSE', 'NON_CURRENT_ASSETS', '非流动资产合计', 29, 'ASSET', 290, 1),
        ('ASSE', 'ASSETS', '资产合计', 30, 'ASSET', 300, 1),
        ('ASSE', 'SHORT_TERM_LOANS', '短期借款', 31, 'LIABILITY', 310, 0),
        ('ASSE', 'NOTES_PAYABLE', '应付票据', 32, 'LIABILITY', 320, 0),
        ('ASSE', 'ACCOUNTS_PAYABLE', '应付账款', 33, 'LIABILITY', 330, 0),
        ('ASSE', 'ADVANCES_FROM_CUSTOMERS', '预收账款', 34, 'LIABILITY', 340, 0),
        ('ASSE', 'EMPLOYEE_BENEFITS_PAYABLE', '应付职工薪酬', 35, 'LIABILITY', 350, 0),
        ('ASSE', 'TAXES_PAYABLE', '应交税费', 36, 'LIABILITY', 360, 0),
        ('ASSE', 'INTEREST_PAYABLE', '应付利息', 37, 'LIABILITY', 370, 0),
        ('ASSE', 'PROFIT_PAYABLE', '应付利润', 38, 'LIABILITY', 380, 0),
        ('ASSE', 'OTHER_PAYABLES', '其他应付款', 39, 'LIABILITY', 390, 0),
        ('ASSE', 'OTHER_CURRENT_LIABILITIES', '其他流动负债', 40, 'LIABILITY', 400, 0),
        ('ASSE', 'CURRENT_LIABILITIES', '流动负债合计', 41, 'LIABILITY', 410, 1),
        ('ASSE', 'LONG_TERM_LOANS', '长期借款', 42, 'LIABILITY', 420, 0),
        ('ASSE', 'LONG_TERM_PAYABLES', '长期应付款', 43, 'LIABILITY', 430, 0),
        ('ASSE', 'DEFERRED_INCOME', '递延收益', 44, 'LIABILITY', 440, 0),
        ('ASSE', 'OTHER_NON_CURRENT_LIABILITIES', '其他非流动负债', 45, 'LIABILITY', 450, 0),
        ('ASSE', 'NON_CURRENT_LIABILITIES', '非流动负债合计', 46, 'LIABILITY', 460, 1),
        ('ASSE', 'LIABILITIES', '负债合计', 47, 'LIABILITY', 470, 1),
        ('ASSE', 'SHARE_CAPITAL', '实收资本（或股本）', 48, 'EQUITY', 480, 0),
        ('ASSE', 'CAPITAL_RESERVE', '资本公积', 49, 'EQUITY', 490, 0),
        ('ASSE', 'SURPLUS_RESERVE', '盈余公积', 50, 'EQUITY', 500, 0),
        ('ASSE', 'RETAINED_EARNINGS', '未分配利润', 51, 'EQUITY', 510, 0),
        ('ASSE', 'EQUITY', '所有者权益合计', 52, 'EQUITY', 520, 1),
        ('ASSE', 'LIABILITIES_AND_EQUITY', '负债和所有者权益总计', 53, 'LIABILITY_EQUITY', 530, 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO fs_balance_sheet_item_dict (gaap_type, item_code, item_name, line_number, section, display_order, is_total) VALUES (?,?,?,?,?,?,?)",
        asse_items
    )
    print(f"  资产负债表项目字典: ASBE {len(asbe_items)} + ASSE {len(asse_items)} 条")


def _seed_bs_synonyms(cur):
    """资产负债表同义词：通用 + ASBE + ASSE"""
    # 通用同义词（gaap_type=NULL，两套准则共用）
    common = [
        # 货币资金
        ('货币资金', 'cash_end', None, 2),
        ('货币资金期末', 'cash_end', None, 3),
        ('货币资金年初', 'cash_begin', None, 3),
        ('货币资金期末余额', 'cash_end', None, 3),
        ('货币资金年初余额', 'cash_begin', None, 3),
        ('现金及银行存款', 'cash_end', None, 1),
        # 应收账款
        ('应收账款期末', 'accounts_receivable_end', None, 3),
        ('应收账款年初', 'accounts_receivable_begin', None, 3),
        ('应收账款余额', 'accounts_receivable_end', None, 2),
        # 存货
        ('存货期末', 'inventory_end', None, 3),
        ('存货年初', 'inventory_begin', None, 3),
        ('存货年初余额', 'inventory_begin', None, 3),
        ('存货期末余额', 'inventory_end', None, 3),
        # 固定资产
        ('固定资产期末', 'fixed_assets_end', None, 3),
        ('固定资产年初', 'fixed_assets_begin', None, 3),
        # 预付账款
        ('预付账款期末', 'prepayments_end', None, 3),
        ('预付账款年初', 'prepayments_begin', None, 3),
        # 其他应收款
        ('其他应收款期末', 'other_receivables_end', None, 3),
        ('其他应收款年初', 'other_receivables_begin', None, 3),
        # 短期借款
        ('短期借款期末', 'short_term_loans_end', None, 3),
        ('短期借款年初', 'short_term_loans_begin', None, 3),
        ('短借', 'short_term_loans_end', None, 1),
        # 应付账款
        ('应付账款期末', 'accounts_payable_end', None, 3),
        ('应付账款年初', 'accounts_payable_begin', None, 3),
        # 应付职工薪酬
        ('应付职工薪酬期末', 'employee_benefits_payable_end', None, 3),
        ('应付职工薪酬年初', 'employee_benefits_payable_begin', None, 3),
        ('应付工资', 'employee_benefits_payable_end', None, 1),
        # 应交税费
        ('应交税费期末', 'taxes_payable_end', None, 3),
        ('应交税费年初', 'taxes_payable_begin', None, 3),
        # 其他应付款
        ('其他应付款期末', 'other_payables_end', None, 3),
        ('其他应付款年初', 'other_payables_begin', None, 3),
        # 实收资本
        ('实收资本期末', 'share_capital_end', None, 3),
        ('实收资本年初', 'share_capital_begin', None, 3),
        ('股本', 'share_capital_end', None, 1),
        # 资本公积
        ('资本公积期末', 'capital_reserve_end', None, 3),
        ('资本公积年初', 'capital_reserve_begin', None, 3),
        # 盈余公积
        ('盈余公积期末', 'surplus_reserve_end', None, 3),
        ('盈余公积年初', 'surplus_reserve_begin', None, 3),
        # 未分配利润
        ('未分配利润期末', 'retained_earnings_end', None, 3),
        ('未分配利润年初', 'retained_earnings_begin', None, 3),
        ('未分配', 'retained_earnings_end', None, 1),
        # 合计项
        ('流动资产合计', 'current_assets_end', None, 2),
        ('非流动资产合计', 'non_current_assets_end', None, 2),
        ('资产总计', 'assets_end', None, 2),
        ('总资产', 'assets_end', None, 1),
        ('资产合计', 'assets_end', None, 2),
        ('流动负债合计', 'current_liabilities_end', None, 2),
        ('非流动负债合计', 'non_current_liabilities_end', None, 2),
        ('负债合计', 'liabilities_end', None, 2),
        ('总负债', 'liabilities_end', None, 1),
        ('所有者权益合计', 'equity_end', None, 2),
        ('股东权益合计', 'equity_end', None, 1),
        ('负债和所有者权益总计', 'liabilities_and_equity_end', None, 2),
        ('负债及权益总计', 'liabilities_and_equity_end', None, 1),
        # 长期借款
        ('长期借款期末', 'long_term_loans_end', None, 3),
        ('长期借款年初', 'long_term_loans_begin', None, 3),
        # 无形资产
        ('无形资产期末', 'intangible_assets_end', None, 3),
        ('无形资产年初', 'intangible_assets_begin', None, 3),
        # 在建工程
        ('在建工程期末', 'construction_in_progress_end', None, 3),
        ('在建工程年初', 'construction_in_progress_begin', None, 3),
        # 长期待摊费用
        ('长期待摊费用期末', 'long_term_deferred_expenses_end', None, 3),
        ('长期待摊费用年初', 'long_term_deferred_expenses_begin', None, 3),
    ]

    # ASBE专有同义词
    asbe_only = [
        ('交易性金融资产', 'trading_financial_assets_end', 'ASBE', 2),
        ('衍生金融资产', 'derivative_financial_assets_end', 'ASBE', 2),
        ('应收票据', 'notes_receivable_end', 'ASBE', 2),
        ('应收账款融资', 'accounts_receivable_financing_end', 'ASBE', 2),
        ('合同资产', 'contract_assets_end', 'ASBE', 2),
        ('持有待售资产', 'held_for_sale_assets_end', 'ASBE', 2),
        ('债权投资', 'debt_investments_end', 'ASBE', 2),
        ('其他债权投资', 'other_debt_investments_end', 'ASBE', 2),
        ('长期应收款', 'long_term_receivables_end', 'ASBE', 2),
        ('长期股权投资', 'long_term_equity_investments_end', 'ASBE', 2),
        ('其他权益工具投资', 'other_equity_instruments_invest_end', 'ASBE', 2),
        ('投资性房地产', 'investment_property_end', 'ASBE', 2),
        ('生产性生物资产', 'productive_biological_assets_end', 'ASBE', 2),
        ('油气资产', 'oil_and_gas_assets_end', 'ASBE', 2),
        ('使用权资产', 'right_of_use_assets_end', 'ASBE', 2),
        ('开发支出', 'development_expenditure_end', 'ASBE', 2),
        ('商誉', 'goodwill_end', 'ASBE', 2),
        ('递延所得税资产', 'deferred_tax_assets_end', 'ASBE', 2),
        ('交易性金融负债', 'trading_financial_liabilities_end', 'ASBE', 2),
        ('衍生金融负债', 'derivative_financial_liabilities_end', 'ASBE', 2),
        ('预收款项', 'advances_from_customers_end', 'ASBE', 2),
        ('合同负债', 'contract_liabilities_end', 'ASBE', 2),
        ('持有待售负债', 'held_for_sale_liabilities_end', 'ASBE', 2),
        ('应付债券', 'bonds_payable_end', 'ASBE', 2),
        ('租赁负债', 'lease_liabilities_end', 'ASBE', 2),
        ('预计负债', 'provisions_end', 'ASBE', 2),
        ('递延收益', 'deferred_income_end', 'ASBE', 2),
        ('递延所得税负债', 'deferred_tax_liabilities_end', 'ASBE', 2),
        ('库存股', 'treasury_stock_end', 'ASBE', 2),
        ('其他综合收益', 'other_comprehensive_income_end', 'ASBE', 2),
        ('专项储备', 'special_reserve_end', 'ASBE', 2),
    ]

    # ASSE专有同义词
    asse_only = [
        ('短期投资', 'short_term_investments_end', 'ASSE', 2),
        ('应收股利', 'dividends_receivable_end', 'ASSE', 2),
        ('应收利息', 'interest_receivable_end', 'ASSE', 2),
        ('原材料', 'raw_materials_end', 'ASSE', 2),
        ('在产品', 'work_in_process_end', 'ASSE', 2),
        ('库存商品', 'finished_goods_end', 'ASSE', 2),
        ('周转材料', 'turnover_materials_end', 'ASSE', 2),
        ('长期债券投资', 'long_term_bond_investments_end', 'ASSE', 2),
        ('固定资产原价', 'fixed_assets_original_end', 'ASSE', 2),
        ('累计折旧', 'accumulated_depreciation_end', 'ASSE', 2),
        ('固定资产账面价值', 'fixed_assets_net_end', 'ASSE', 2),
        ('固定资产净值', 'fixed_assets_net_end', 'ASSE', 1),
        ('工程物资', 'engineering_materials_end', 'ASSE', 2),
        ('固定资产清理', 'fixed_assets_liquidation_end', 'ASSE', 2),
        ('预收账款', 'advances_from_customers_end', 'ASSE', 2),
        ('应付利息', 'interest_payable_end', 'ASSE', 2),
        ('应付利润', 'profit_payable_end', 'ASSE', 2),
    ]

    for phrase, col, gaap, pri in common:
        cur.execute(
            "INSERT OR IGNORE INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES (?,?,?,?)",
            (phrase, col, gaap, pri)
        )
    for phrase, col, gaap, pri in asbe_only:
        cur.execute(
            "INSERT OR IGNORE INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES (?,?,?,?)",
            (phrase, col, gaap, pri)
        )
    for phrase, col, gaap, pri in asse_only:
        cur.execute(
            "INSERT OR IGNORE INTO fs_balance_sheet_synonyms (phrase, column_name, gaap_type, priority) VALUES (?,?,?,?)",
            (phrase, col, gaap, pri)
        )
    count = cur.execute("SELECT COUNT(*) FROM fs_balance_sheet_synonyms").fetchone()[0]
    print(f"  资产负债表同义词: {count} 条")


def _seed_is_item_dict(cur):
    """利润表项目字典：企业会计准则(CAS) + 小企业会计准则(SAS)
    item_code 使用与原视图列名一致的编码，保证向后兼容。
    """
    cas_items = [
        ('CAS', 'operating_revenue', '营业收入', 1, 'operating', 10, 0),
        ('CAS', 'operating_cost', '减：营业成本', 2, 'operating', 20, 0),
        ('CAS', 'taxes_and_surcharges', '税金及附加', 3, 'operating', 30, 0),
        ('CAS', 'selling_expense', '销售费用', 4, 'operating', 40, 0),
        ('CAS', 'administrative_expense', '管理费用', 5, 'operating', 50, 0),
        ('CAS', 'rd_expense', '研发费用', 6, 'operating', 60, 0),
        ('CAS', 'financial_expense', '财务费用', 7, 'operating', 70, 0),
        ('CAS', 'interest_expense', '其中：利息费用', 8, 'operating', 80, 0),
        ('CAS', 'interest_income', '利息收入', 9, 'operating', 90, 0),
        ('CAS', 'other_gains', '其他收益', 10, 'operating', 100, 0),
        ('CAS', 'investment_income', '投资收益', 11, 'operating', 110, 0),
        ('CAS', 'investment_income_associates', '其中：对联营企业和合营企业的投资收益', 12, 'operating', 120, 0),
        ('CAS', 'amortized_cost_termination_income', '以摊余成本计量的金融资产终止确认收益', 13, 'operating', 130, 0),
        ('CAS', 'net_exposure_hedge_income', '净敞口套期收益', 14, 'operating', 140, 0),
        ('CAS', 'fair_value_change_income', '公允价值变动收益', 15, 'operating', 150, 0),
        ('CAS', 'credit_impairment_loss', '信用减值损失', 16, 'operating', 160, 0),
        ('CAS', 'asset_impairment_loss', '资产减值损失', 17, 'operating', 170, 0),
        ('CAS', 'asset_disposal_gains', '资产处置收益', 18, 'operating', 180, 0),
        ('CAS', 'operating_profit', '营业利润', 19, 'operating', 190, 1),
        ('CAS', 'non_operating_income', '营业外收入', 20, 'non_operating', 200, 0),
        ('CAS', 'non_operating_expense', '营业外支出', 21, 'non_operating', 210, 0),
        ('CAS', 'total_profit', '利润总额', 22, 'profit', 220, 1),
        ('CAS', 'income_tax_expense', '所得税费用', 23, 'profit', 230, 0),
        ('CAS', 'net_profit', '净利润', 24, 'profit', 240, 1),
        ('CAS', 'continued_ops_net_profit', '持续经营净利润', 25, 'profit', 250, 0),
        ('CAS', 'discontinued_ops_net_profit', '终止经营净利润', 26, 'profit', 260, 0),
        ('CAS', 'other_comprehensive_income_net', '其他综合收益的税后净额', 27, 'comprehensive', 270, 1),
        ('CAS', 'oci_not_reclassifiable', '不能重分类进损益的其他综合收益', 28, 'comprehensive', 280, 1),
        ('CAS', 'oci_remeasurement_pension', '重新计量设定受益计划变动额', 29, 'comprehensive', 290, 0),
        ('CAS', 'oci_equity_method_nonreclassifiable', '权益法下不能转损益的其他综合收益', 30, 'comprehensive', 300, 0),
        ('CAS', 'oci_equity_investment_fv_change', '其他权益工具投资公允价值变动', 31, 'comprehensive', 310, 0),
        ('CAS', 'oci_credit_risk_change', '企业自身信用风险公允价值变动', 32, 'comprehensive', 320, 0),
        ('CAS', 'oci_reclassifiable', '将重分类进损益的其他综合收益', 33, 'comprehensive', 330, 1),
        ('CAS', 'oci_equity_method_reclassifiable', '权益法下可转损益的其他综合收益', 34, 'comprehensive', 340, 0),
        ('CAS', 'oci_debt_investment_fv_change', '其他债权投资公允价值变动', 35, 'comprehensive', 350, 0),
        ('CAS', 'oci_reclassify_to_pnl', '金融资产重分类计入其他综合收益的金额', 36, 'comprehensive', 360, 0),
        ('CAS', 'oci_debt_impairment', '其他债权投资信用减值准备', 37, 'comprehensive', 370, 0),
        ('CAS', 'oci_cash_flow_hedge', '现金流量套期储备', 38, 'comprehensive', 380, 0),
        ('CAS', 'oci_foreign_currency_translation', '外币财务报表折算差额', 39, 'comprehensive', 390, 0),
        ('CAS', 'comprehensive_income_total', '综合收益总额', 40, 'comprehensive', 400, 1),
        ('CAS', 'eps_basic', '基本每股收益', 42, 'eps', 410, 0),
        ('CAS', 'eps_diluted', '稀释每股收益', 43, 'eps', 420, 0),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES (?,?,?,?,?,?,?)",
        cas_items
    )

    sas_items = [
        ('SAS', 'operating_revenue', '营业收入', 1, 'operating', 10, 0),
        ('SAS', 'operating_cost', '减：营业成本', 2, 'operating', 20, 0),
        ('SAS', 'taxes_and_surcharges', '税金及附加', 3, 'operating', 30, 0),
        ('SAS', 'consumption_tax', '其中：消费税', 4, 'operating', 40, 0),
        ('SAS', 'business_tax', '营业税', 5, 'operating', 50, 0),
        ('SAS', 'city_maintenance_tax', '城市维护建设税', 6, 'operating', 60, 0),
        ('SAS', 'resource_tax', '资源税', 7, 'operating', 70, 0),
        ('SAS', 'land_appreciation_tax', '土地增值税', 8, 'operating', 80, 0),
        ('SAS', 'property_related_taxes', '城镇土地使用税、房产税、车船税、印花税', 9, 'operating', 90, 0),
        ('SAS', 'education_surcharge', '教育费附加、矿产资源补偿费、排污费', 10, 'operating', 100, 0),
        ('SAS', 'selling_expense', '销售费用', 11, 'operating', 110, 0),
        ('SAS', 'goods_repair_expense', '其中：商品维修费', 12, 'operating', 120, 0),
        ('SAS', 'advertising_expense', '广告费和业务宣传费', 13, 'operating', 130, 0),
        ('SAS', 'administrative_expense', '管理费用', 14, 'operating', 140, 0),
        ('SAS', 'organization_expense', '其中：开办费', 15, 'operating', 150, 0),
        ('SAS', 'business_entertainment_expense', '业务招待费', 16, 'operating', 160, 0),
        ('SAS', 'research_expense', '研究费用', 17, 'operating', 170, 0),
        ('SAS', 'financial_expense', '财务费用', 18, 'operating', 180, 0),
        ('SAS', 'interest_expense_net', '其中：利息费用', 19, 'operating', 190, 0),
        ('SAS', 'investment_income', '投资收益', 20, 'operating', 200, 0),
        ('SAS', 'operating_profit', '营业利润', 21, 'operating', 210, 1),
        ('SAS', 'non_operating_income', '营业外收入', 22, 'non_operating', 220, 0),
        ('SAS', 'government_grant', '其中：政府补助', 23, 'non_operating', 230, 0),
        ('SAS', 'non_operating_expense', '营业外支出', 24, 'non_operating', 240, 0),
        ('SAS', 'bad_debt_loss', '其中：坏账损失', 25, 'non_operating', 250, 0),
        ('SAS', 'long_term_bond_loss', '无法收回的长期债券投资损失', 26, 'non_operating', 260, 0),
        ('SAS', 'long_term_equity_loss', '无法收回的长期股权投资损失', 27, 'non_operating', 270, 0),
        ('SAS', 'force_majeure_loss', '自然灾害等不可抗力因素造成的损失', 28, 'non_operating', 280, 0),
        ('SAS', 'tax_late_payment', '税收滞纳金', 29, 'non_operating', 290, 0),
        ('SAS', 'total_profit', '利润总额', 30, 'profit', 300, 1),
        ('SAS', 'income_tax_expense', '所得税费用', 31, 'profit', 310, 0),
        ('SAS', 'net_profit', '净利润', 32, 'profit', 320, 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO fs_income_statement_item_dict (gaap_type, item_code, item_name, line_number, category, display_order, is_total) VALUES (?,?,?,?,?,?,?)",
        sas_items
    )
    print(f"  利润表项目字典: CAS {len(cas_items)} + SAS {len(sas_items)} 条")


def _seed_is_synonyms(cur):
    """利润表同义词 — 插入到 fs_income_statement_synonyms 表
    (phrase, column_name, gaap_type, priority)
    column_name 使用旧视图的裸列名（已去除 _current/_cumulative 后缀并完成映射）。

    列名映射（文档 item_code → 旧视图列名）:
      CAS: oci_non_reclass→oci_not_reclassifiable, oci_remeasurement_defined_benefit→oci_remeasurement_pension,
           oci_eq_method_non_reclass→oci_equity_method_nonreclassifiable,
           oci_fair_value_change_other_equity→oci_equity_investment_fv_change,
           oci_reclass→oci_reclassifiable, oci_eq_method_reclass→oci_equity_method_reclassifiable,
           oci_fair_value_change_other_debt→oci_debt_investment_fv_change,
           oci_reclassification_adjustment→oci_reclassify_to_pnl,
           oci_credit_impairment_other_debt→oci_debt_impairment,
           oci_cash_flow_hedge_reserve→oci_cash_flow_hedge,
           total_comprehensive_income→comprehensive_income_total
      SAS: property_and_other_taxes→property_related_taxes, education_surcharge_and_other→education_surcharge,
           selling_expense_repair→goods_repair_expense, selling_expense_advertising→advertising_expense,
           administrative_expense_organization→organization_expense,
           administrative_expense_entertainment→business_entertainment_expense,
           administrative_expense_research→research_expense, interest_expense→interest_expense_net,
           non_operating_income_gov_grant→government_grant, non_operating_expense_bad_debt→bad_debt_loss,
           non_operating_expense_loss_long_term_bond→long_term_bond_loss,
           non_operating_expense_loss_long_term_equity→long_term_equity_loss,
           non_operating_expense_force_majeure→force_majeure_loss,
           non_operating_expense_tax_late_fee→tax_late_payment
    """

    # ── CAS 同义词 ──
    cas_rows = [
        # 营业收入
        ('营业收入', 'operating_revenue', 'CAS', 2),
        ('营业收入本期', 'operating_revenue', 'CAS', 2),
        ('营业收入累计', 'operating_revenue', 'CAS', 2),
        ('营收', 'operating_revenue', 'CAS', 2),
        ('经营收入', 'operating_revenue', 'CAS', 2),
        ('主营收入', 'operating_revenue', 'CAS', 2),
        ('第1行', 'operating_revenue', 'CAS', 3),
        ('1行', 'operating_revenue', 'CAS', 3),
        ('第一行', 'operating_revenue', 'CAS', 3),
        # 营业成本
        ('营业成本', 'operating_cost', 'CAS', 2),
        ('营业成本本期', 'operating_cost', 'CAS', 2),
        ('营业成本累计', 'operating_cost', 'CAS', 2),
        ('经营成本', 'operating_cost', 'CAS', 2),
        ('主营成本', 'operating_cost', 'CAS', 2),
        ('成本', 'operating_cost', 'CAS', 2),
        ('减：营业成本', 'operating_cost', 'CAS', 2),
        ('第2行', 'operating_cost', 'CAS', 3),
        ('2行', 'operating_cost', 'CAS', 3),
        ('第二行', 'operating_cost', 'CAS', 3),
        # 税金及附加
        ('税金及附加', 'taxes_and_surcharges', 'CAS', 2),
        ('税费及附加', 'taxes_and_surcharges', 'CAS', 2),
        ('税金附加', 'taxes_and_surcharges', 'CAS', 2),
        ('附加税', 'taxes_and_surcharges', 'CAS', 2),
        ('税及附加', 'taxes_and_surcharges', 'CAS', 2),
        ('第3行', 'taxes_and_surcharges', 'CAS', 3),
        ('3行', 'taxes_and_surcharges', 'CAS', 3),
        ('第三行', 'taxes_and_surcharges', 'CAS', 3),
        # 销售费用
        ('销售费用', 'selling_expense', 'CAS', 2),
        ('销售费', 'selling_expense', 'CAS', 2),
        ('营销费用', 'selling_expense', 'CAS', 2),
        ('营销费', 'selling_expense', 'CAS', 2),
        ('售卖费用', 'selling_expense', 'CAS', 2),
        ('第4行', 'selling_expense', 'CAS', 3),
        ('4行', 'selling_expense', 'CAS', 3),
        ('第四行', 'selling_expense', 'CAS', 3),
        # 管理费用
        ('管理费用', 'administrative_expense', 'CAS', 2),
        ('管理费', 'administrative_expense', 'CAS', 2),
        ('管理开支', 'administrative_expense', 'CAS', 2),
        ('行政费用', 'administrative_expense', 'CAS', 2),
        ('行政费', 'administrative_expense', 'CAS', 2),
        ('第5行', 'administrative_expense', 'CAS', 3),
        ('5行', 'administrative_expense', 'CAS', 3),
        ('第五行', 'administrative_expense', 'CAS', 3),
        # 研发费用
        ('研发费用', 'rd_expense', 'CAS', 2),
        ('研发费', 'rd_expense', 'CAS', 2),
        ('研发支出', 'rd_expense', 'CAS', 2),
        ('研发投入', 'rd_expense', 'CAS', 2),
        ('研究开发费用', 'rd_expense', 'CAS', 2),
        ('研发开销', 'rd_expense', 'CAS', 2),
        ('第6行', 'rd_expense', 'CAS', 3),
        ('6行', 'rd_expense', 'CAS', 3),
        ('第六行', 'rd_expense', 'CAS', 3),
        # 财务费用
        ('财务费用', 'financial_expense', 'CAS', 2),
        ('财务费', 'financial_expense', 'CAS', 2),
        ('财务开支', 'financial_expense', 'CAS', 2),
        ('筹资费用', 'financial_expense', 'CAS', 2),
        ('资金费用', 'financial_expense', 'CAS', 2),
        ('第7行', 'financial_expense', 'CAS', 3),
        ('7行', 'financial_expense', 'CAS', 3),
        ('第七行', 'financial_expense', 'CAS', 3),
        # 利息费用
        ('利息费用', 'interest_expense', 'CAS', 2),
        ('利息费', 'interest_expense', 'CAS', 2),
        ('利息支出', 'interest_expense', 'CAS', 2),
        ('利息开支', 'interest_expense', 'CAS', 2),
        ('借款利息', 'interest_expense', 'CAS', 2),
        ('第8行', 'interest_expense', 'CAS', 3),
        ('8行', 'interest_expense', 'CAS', 3),
        ('第八行', 'interest_expense', 'CAS', 3),
        # 利息收入
        ('利息收入', 'interest_income', 'CAS', 2),
        ('利息收益', 'interest_income', 'CAS', 2),
        ('存款利息', 'interest_income', 'CAS', 2),
        ('利息所得', 'interest_income', 'CAS', 2),
        ('利息回款', 'interest_income', 'CAS', 2),
        ('第9行', 'interest_income', 'CAS', 3),
        ('9行', 'interest_income', 'CAS', 3),
        ('第九行', 'interest_income', 'CAS', 3),
        # 其他收益
        ('其他收益', 'other_gains', 'CAS', 2),
        ('其他收益收入', 'other_gains', 'CAS', 2),
        ('其他利得', 'other_gains', 'CAS', 2),
        ('其他盈利', 'other_gains', 'CAS', 2),
        ('其他收益项', 'other_gains', 'CAS', 2),
        ('第10行', 'other_gains', 'CAS', 3),
        ('10行', 'other_gains', 'CAS', 3),
        ('第十行', 'other_gains', 'CAS', 3),
        # 投资收益
        ('投资收益', 'investment_income', 'CAS', 2),
        ('投资收益（损失以"－"号填列）', 'investment_income', 'CAS', 2),
        ('投资利润', 'investment_income', 'CAS', 2),
        ('投资回报', 'investment_income', 'CAS', 2),
        ('投资所得', 'investment_income', 'CAS', 2),
        ('理财收益', 'investment_income', 'CAS', 2),
        ('第11行', 'investment_income', 'CAS', 3),
        ('11行', 'investment_income', 'CAS', 3),
        ('第十一行', 'investment_income', 'CAS', 3),
        # 对联营企业和合营企业的投资收益
        ('对联营企业和合营企业的投资收益', 'investment_income_associates', 'CAS', 2),
        ('联营合营企业投资收益', 'investment_income_associates', 'CAS', 2),
        ('联营企业投资收益', 'investment_income_associates', 'CAS', 2),
        ('合营企业投资收益', 'investment_income_associates', 'CAS', 2),
        ('联营合营收益', 'investment_income_associates', 'CAS', 2),
        ('第12行', 'investment_income_associates', 'CAS', 3),
        ('12行', 'investment_income_associates', 'CAS', 3),
        ('第十二行', 'investment_income_associates', 'CAS', 3),
        # 以摊余成本计量的金融资产终止确认收益
        ('以摊余成本计量的金融资产终止确认收益', 'amortized_cost_termination_income', 'CAS', 2),
        ('摊余成本金融资产终止确认收益', 'amortized_cost_termination_income', 'CAS', 2),
        ('金融资产终止确认收益', 'amortized_cost_termination_income', 'CAS', 2),
        ('摊余成本资产终止收益', 'amortized_cost_termination_income', 'CAS', 2),
        ('金融资产终止收益', 'amortized_cost_termination_income', 'CAS', 2),
        ('第13行', 'amortized_cost_termination_income', 'CAS', 3),
        ('13行', 'amortized_cost_termination_income', 'CAS', 3),
        ('第十三行', 'amortized_cost_termination_income', 'CAS', 3),
        # 净敞口套期收益
        ('净敞口套期收益', 'net_exposure_hedge_income', 'CAS', 2),
        ('套期收益', 'net_exposure_hedge_income', 'CAS', 2),
        ('净敞口套期利得', 'net_exposure_hedge_income', 'CAS', 2),
        ('套期盈利', 'net_exposure_hedge_income', 'CAS', 2),
        ('敞口套期收益', 'net_exposure_hedge_income', 'CAS', 2),
        ('第14行', 'net_exposure_hedge_income', 'CAS', 3),
        ('14行', 'net_exposure_hedge_income', 'CAS', 3),
        ('第十四行', 'net_exposure_hedge_income', 'CAS', 3),
        # 公允价值变动收益
        ('公允价值变动收益', 'fair_value_change_income', 'CAS', 2),
        ('公允价变动收益', 'fair_value_change_income', 'CAS', 2),
        ('公允价值变动利得', 'fair_value_change_income', 'CAS', 2),
        ('公允价变动利得', 'fair_value_change_income', 'CAS', 2),
        ('市价变动收益', 'fair_value_change_income', 'CAS', 2),
        ('第15行', 'fair_value_change_income', 'CAS', 3),
        ('15行', 'fair_value_change_income', 'CAS', 3),
        ('第十五行', 'fair_value_change_income', 'CAS', 3),
        # 信用减值损失
        ('信用减值损失', 'credit_impairment_loss', 'CAS', 2),
        ('信用减值亏损', 'credit_impairment_loss', 'CAS', 2),
        ('坏账减值损失', 'credit_impairment_loss', 'CAS', 2),
        ('信用损失', 'credit_impairment_loss', 'CAS', 2),
        ('减值损失（信用）', 'credit_impairment_loss', 'CAS', 2),
        ('第16行', 'credit_impairment_loss', 'CAS', 3),
        ('16行', 'credit_impairment_loss', 'CAS', 3),
        ('第十六行', 'credit_impairment_loss', 'CAS', 3),
        # 资产减值损失
        ('资产减值损失', 'asset_impairment_loss', 'CAS', 2),
        ('资产减值亏损', 'asset_impairment_loss', 'CAS', 2),
        ('资产减值', 'asset_impairment_loss', 'CAS', 2),
        ('减值损失（资产）', 'asset_impairment_loss', 'CAS', 2),
        ('资产跌价损失', 'asset_impairment_loss', 'CAS', 2),
        ('第17行', 'asset_impairment_loss', 'CAS', 3),
        ('17行', 'asset_impairment_loss', 'CAS', 3),
        ('第十七行', 'asset_impairment_loss', 'CAS', 3),
        # 资产处置收益
        ('资产处置收益', 'asset_disposal_gains', 'CAS', 2),
        ('资产处置利得', 'asset_disposal_gains', 'CAS', 2),
        ('处置资产收益', 'asset_disposal_gains', 'CAS', 2),
        ('资产出售收益', 'asset_disposal_gains', 'CAS', 2),
        ('固定资产处置收益', 'asset_disposal_gains', 'CAS', 2),
        ('第18行', 'asset_disposal_gains', 'CAS', 3),
        ('18行', 'asset_disposal_gains', 'CAS', 3),
        ('第十八行', 'asset_disposal_gains', 'CAS', 3),
        # 营业利润
        ('营业利润', 'operating_profit', 'CAS', 2),
        ('营业利润（亏损以"－"号填列）', 'operating_profit', 'CAS', 2),
        ('营业利润本期', 'operating_profit', 'CAS', 2),
        ('营业利润累计', 'operating_profit', 'CAS', 2),
        ('经营利润', 'operating_profit', 'CAS', 2),
        ('主营利润', 'operating_profit', 'CAS', 2),
        ('营业盈利', 'operating_profit', 'CAS', 2),
        ('第19行', 'operating_profit', 'CAS', 3),
        ('19行', 'operating_profit', 'CAS', 3),
        ('第十九行', 'operating_profit', 'CAS', 3),
        # 营业外收入
        ('营业外收入', 'non_operating_income', 'CAS', 2),
        ('非营业收入', 'non_operating_income', 'CAS', 2),
        ('营业外收益', 'non_operating_income', 'CAS', 2),
        ('非经营收入', 'non_operating_income', 'CAS', 2),
        ('额外收入', 'non_operating_income', 'CAS', 2),
        ('第20行', 'non_operating_income', 'CAS', 3),
        ('20行', 'non_operating_income', 'CAS', 3),
        ('第二十行', 'non_operating_income', 'CAS', 3),
        # 营业外支出
        ('营业外支出', 'non_operating_expense', 'CAS', 2),
        ('非营业支出', 'non_operating_expense', 'CAS', 2),
        ('营业外开销', 'non_operating_expense', 'CAS', 2),
        ('非经营支出', 'non_operating_expense', 'CAS', 2),
        ('额外支出', 'non_operating_expense', 'CAS', 2),
        ('第21行', 'non_operating_expense', 'CAS', 3),
        ('21行', 'non_operating_expense', 'CAS', 3),
        ('第二十一行', 'non_operating_expense', 'CAS', 3),
        # 利润总额
        ('利润总额', 'total_profit', 'CAS', 2),
        ('利润总额（亏损总额以"－"号填列）', 'total_profit', 'CAS', 2),
        ('税前利润', 'total_profit', 'CAS', 2),
        ('总利润', 'total_profit', 'CAS', 2),
        ('利润总和', 'total_profit', 'CAS', 2),
        ('第22行', 'total_profit', 'CAS', 3),
        ('22行', 'total_profit', 'CAS', 3),
        ('第二十二行', 'total_profit', 'CAS', 3),
        # 所得税费用
        ('所得税费用', 'income_tax_expense', 'CAS', 2),
        ('所得税', 'income_tax_expense', 'CAS', 2),
        ('所得税费', 'income_tax_expense', 'CAS', 2),
        ('企业所得税', 'income_tax_expense', 'CAS', 2),
        ('所得税开支', 'income_tax_expense', 'CAS', 2),
        ('第23行', 'income_tax_expense', 'CAS', 3),
        ('23行', 'income_tax_expense', 'CAS', 3),
        ('第二十三行', 'income_tax_expense', 'CAS', 3),
        # 净利润
        ('净利润', 'net_profit', 'CAS', 2),
        ('净利润（净亏损以"－"号填列）', 'net_profit', 'CAS', 2),
        ('净利润本期', 'net_profit', 'CAS', 2),
        ('净利润累计', 'net_profit', 'CAS', 2),
        ('纯利润', 'net_profit', 'CAS', 2),
        ('税后利润', 'net_profit', 'CAS', 2),
        ('净利', 'net_profit', 'CAS', 2),
        ('第24行', 'net_profit', 'CAS', 3),
        ('24行', 'net_profit', 'CAS', 3),
        ('第二十四行', 'net_profit', 'CAS', 3),
        # 持续经营净利润
        ('持续经营净利润', 'continued_ops_net_profit', 'CAS', 2),
        ('持续经营净利', 'continued_ops_net_profit', 'CAS', 2),
        ('持续经营利润', 'continued_ops_net_profit', 'CAS', 2),
        ('持续经营纯利润', 'continued_ops_net_profit', 'CAS', 2),
        ('（一）持续经营净利润', 'continued_ops_net_profit', 'CAS', 2),
        ('第25行', 'continued_ops_net_profit', 'CAS', 3),
        ('25行', 'continued_ops_net_profit', 'CAS', 3),
        ('第二十五行', 'continued_ops_net_profit', 'CAS', 3),
        # 终止经营净利润
        ('终止经营净利润', 'discontinued_ops_net_profit', 'CAS', 2),
        ('终止经营净利', 'discontinued_ops_net_profit', 'CAS', 2),
        ('终止经营利润', 'discontinued_ops_net_profit', 'CAS', 2),
        ('终止经营纯利润', 'discontinued_ops_net_profit', 'CAS', 2),
        ('（二）终止经营净利润', 'discontinued_ops_net_profit', 'CAS', 2),
        ('第26行', 'discontinued_ops_net_profit', 'CAS', 3),
        ('26行', 'discontinued_ops_net_profit', 'CAS', 3),
        ('第二十六行', 'discontinued_ops_net_profit', 'CAS', 3),
        # 其他综合收益的税后净额
        ('其他综合收益', 'other_comprehensive_income_net', 'CAS', 2),
        ('其他综合收益的税后净额', 'other_comprehensive_income_net', 'CAS', 2),
        ('其他综合收益净额', 'other_comprehensive_income_net', 'CAS', 2),
        ('综合收益（其他）', 'other_comprehensive_income_net', 'CAS', 2),
        ('其他综合净利', 'other_comprehensive_income_net', 'CAS', 2),
        ('五、其他综合收益的税后净额', 'other_comprehensive_income_net', 'CAS', 2),
        ('第27行', 'other_comprehensive_income_net', 'CAS', 3),
        ('27行', 'other_comprehensive_income_net', 'CAS', 3),
        ('第二十七行', 'other_comprehensive_income_net', 'CAS', 3),
        # 不能重分类进损益的其他综合收益
        ('不能重分类进损益的其他综合收益', 'oci_not_reclassifiable', 'CAS', 2),
        ('不可重分类其他综合收益', 'oci_not_reclassifiable', 'CAS', 2),
        ('非重分类其他综合收益', 'oci_not_reclassifiable', 'CAS', 2),
        ('（一）不能重分类进损益的其他综合收益', 'oci_not_reclassifiable', 'CAS', 2),
        ('不可转损益其他综合收益', 'oci_not_reclassifiable', 'CAS', 2),
        ('第28行', 'oci_not_reclassifiable', 'CAS', 3),
        ('28行', 'oci_not_reclassifiable', 'CAS', 3),
        ('第二十八行', 'oci_not_reclassifiable', 'CAS', 3),
        # 重新计量设定受益计划变动额
        ('重新计量设定受益计划变动额', 'oci_remeasurement_pension', 'CAS', 2),
        ('设定受益计划变动额', 'oci_remeasurement_pension', 'CAS', 2),
        ('受益计划重新计量变动', 'oci_remeasurement_pension', 'CAS', 2),
        ('1.重新计量设定受益计划变动额', 'oci_remeasurement_pension', 'CAS', 2),
        ('设定受益计划调整额', 'oci_remeasurement_pension', 'CAS', 2),
        ('第29行', 'oci_remeasurement_pension', 'CAS', 3),
        ('29行', 'oci_remeasurement_pension', 'CAS', 3),
        ('第二十九行', 'oci_remeasurement_pension', 'CAS', 3),
        # 权益法下不能转损益的其他综合收益
        ('权益法下不能转损益的其他综合收益', 'oci_equity_method_nonreclassifiable', 'CAS', 2),
        ('权益法不可转损益其他综合收益', 'oci_equity_method_nonreclassifiable', 'CAS', 2),
        ('权益法非转损益其他综合收益', 'oci_equity_method_nonreclassifiable', 'CAS', 2),
        ('2.权益法下不能转损益的其他综合收益', 'oci_equity_method_nonreclassifiable', 'CAS', 2),
        ('权益法不可重分类收益', 'oci_equity_method_nonreclassifiable', 'CAS', 2),
        ('第30行', 'oci_equity_method_nonreclassifiable', 'CAS', 3),
        ('30行', 'oci_equity_method_nonreclassifiable', 'CAS', 3),
        ('第三十行', 'oci_equity_method_nonreclassifiable', 'CAS', 3),
        # 其他权益工具投资公允价值变动
        ('其他权益工具投资公允价值变动', 'oci_equity_investment_fv_change', 'CAS', 2),
        ('权益工具投资公允价变动', 'oci_equity_investment_fv_change', 'CAS', 2),
        ('其他权益工具公允价变动', 'oci_equity_investment_fv_change', 'CAS', 2),
        ('3.其他权益工具投资公允价值变动', 'oci_equity_investment_fv_change', 'CAS', 2),
        ('权益工具市价变动', 'oci_equity_investment_fv_change', 'CAS', 2),
        ('第31行', 'oci_equity_investment_fv_change', 'CAS', 3),
        ('31行', 'oci_equity_investment_fv_change', 'CAS', 3),
        ('第三十一行', 'oci_equity_investment_fv_change', 'CAS', 3),
        # 企业自身信用风险公允价值变动
        ('企业自身信用风险公允价值变动', 'oci_credit_risk_change', 'CAS', 2),
        ('自身信用风险公允价变动', 'oci_credit_risk_change', 'CAS', 2),
        ('信用风险公允价值变动', 'oci_credit_risk_change', 'CAS', 2),
        ('4.企业自身信用风险公允价值变动', 'oci_credit_risk_change', 'CAS', 2),
        ('自身信用风险变动', 'oci_credit_risk_change', 'CAS', 2),
        ('第32行', 'oci_credit_risk_change', 'CAS', 3),
        ('32行', 'oci_credit_risk_change', 'CAS', 3),
        ('第三十二行', 'oci_credit_risk_change', 'CAS', 3),
        # 将重分类进损益的其他综合收益
        ('将重分类进损益的其他综合收益', 'oci_reclassifiable', 'CAS', 2),
        ('可重分类其他综合收益', 'oci_reclassifiable', 'CAS', 2),
        ('重分类进损益收益', 'oci_reclassifiable', 'CAS', 2),
        ('（二）将重分类进损益的其他综合收益', 'oci_reclassifiable', 'CAS', 2),
        ('可转损益其他综合收益', 'oci_reclassifiable', 'CAS', 2),
        ('第33行', 'oci_reclassifiable', 'CAS', 3),
        ('33行', 'oci_reclassifiable', 'CAS', 3),
        ('第三十三行', 'oci_reclassifiable', 'CAS', 3),
        # 权益法下可转损益的其他综合收益
        ('权益法下可转损益的其他综合收益', 'oci_equity_method_reclassifiable', 'CAS', 2),
        ('权益法可转损益其他综合收益', 'oci_equity_method_reclassifiable', 'CAS', 2),
        ('权益法重分类收益', 'oci_equity_method_reclassifiable', 'CAS', 2),
        ('1.权益法下可转损益的其他综合收益', 'oci_equity_method_reclassifiable', 'CAS', 2),
        ('权益法可重分类收益', 'oci_equity_method_reclassifiable', 'CAS', 2),
        ('第34行', 'oci_equity_method_reclassifiable', 'CAS', 3),
        ('34行', 'oci_equity_method_reclassifiable', 'CAS', 3),
        ('第三十四行', 'oci_equity_method_reclassifiable', 'CAS', 3),
        # 其他债权投资公允价值变动
        ('其他债权投资公允价值变动', 'oci_debt_investment_fv_change', 'CAS', 2),
        ('债权投资公允价变动', 'oci_debt_investment_fv_change', 'CAS', 2),
        ('其他债权公允价变动', 'oci_debt_investment_fv_change', 'CAS', 2),
        ('2.其他债权投资公允价值变动', 'oci_debt_investment_fv_change', 'CAS', 2),
        ('债权投资市价变动', 'oci_debt_investment_fv_change', 'CAS', 2),
        ('第35行', 'oci_debt_investment_fv_change', 'CAS', 3),
        ('35行', 'oci_debt_investment_fv_change', 'CAS', 3),
        ('第三十五行', 'oci_debt_investment_fv_change', 'CAS', 3),
        # 金融资产重分类计入其他综合收益的金额
        ('金融资产重分类计入其他综合收益的金额', 'oci_reclassify_to_pnl', 'CAS', 2),
        ('金融资产重分类其他综合收益', 'oci_reclassify_to_pnl', 'CAS', 2),
        ('资产重分类综合收益', 'oci_reclassify_to_pnl', 'CAS', 2),
        ('3.金融资产重分类计入其他综合收益的金额', 'oci_reclassify_to_pnl', 'CAS', 2),
        ('重分类综合收益金额', 'oci_reclassify_to_pnl', 'CAS', 2),
        ('第36行', 'oci_reclassify_to_pnl', 'CAS', 3),
        ('36行', 'oci_reclassify_to_pnl', 'CAS', 3),
        ('第三十六行', 'oci_reclassify_to_pnl', 'CAS', 3),
        # 其他债权投资信用减值准备
        ('其他债权投资信用减值准备', 'oci_debt_impairment', 'CAS', 2),
        ('债权投资信用减值准备', 'oci_debt_impairment', 'CAS', 2),
        ('其他债权减值准备', 'oci_debt_impairment', 'CAS', 2),
        ('4.其他债权投资信用减值准备', 'oci_debt_impairment', 'CAS', 2),
        ('债权投资减值准备', 'oci_debt_impairment', 'CAS', 2),
        ('第37行', 'oci_debt_impairment', 'CAS', 3),
        ('37行', 'oci_debt_impairment', 'CAS', 3),
        ('第三十七行', 'oci_debt_impairment', 'CAS', 3),
        # 现金流量套期储备
        ('现金流量套期储备', 'oci_cash_flow_hedge', 'CAS', 2),
        ('现金流套期储备', 'oci_cash_flow_hedge', 'CAS', 2),
        ('套期储备（现金流量）', 'oci_cash_flow_hedge', 'CAS', 2),
        ('5.现金流量套期储备', 'oci_cash_flow_hedge', 'CAS', 2),
        ('现金流套期准备金', 'oci_cash_flow_hedge', 'CAS', 2),
        ('第38行', 'oci_cash_flow_hedge', 'CAS', 3),
        ('38行', 'oci_cash_flow_hedge', 'CAS', 3),
        ('第三十八行', 'oci_cash_flow_hedge', 'CAS', 3),
        # 外币财务报表折算差额
        ('外币财务报表折算差额', 'oci_foreign_currency_translation', 'CAS', 2),
        ('外币报表折算差额', 'oci_foreign_currency_translation', 'CAS', 2),
        ('外币折算差额', 'oci_foreign_currency_translation', 'CAS', 2),
        ('6.外币财务报表折算差额', 'oci_foreign_currency_translation', 'CAS', 2),
        ('外币报表差额', 'oci_foreign_currency_translation', 'CAS', 2),
        ('第39行', 'oci_foreign_currency_translation', 'CAS', 3),
        ('39行', 'oci_foreign_currency_translation', 'CAS', 3),
        ('第三十九行', 'oci_foreign_currency_translation', 'CAS', 3),
        # 综合收益总额
        ('综合收益总额', 'comprehensive_income_total', 'CAS', 2),
        ('综合收益合计', 'comprehensive_income_total', 'CAS', 2),
        ('总综合收益', 'comprehensive_income_total', 'CAS', 2),
        ('六、综合收益总额', 'comprehensive_income_total', 'CAS', 2),
        ('综合收益总计', 'comprehensive_income_total', 'CAS', 2),
        ('第40行', 'comprehensive_income_total', 'CAS', 3),
        ('40行', 'comprehensive_income_total', 'CAS', 3),
        ('第四十行', 'comprehensive_income_total', 'CAS', 3),
        # 基本每股收益
        ('基本每股收益', 'eps_basic', 'CAS', 2),
        ('基本每股盈利', 'eps_basic', 'CAS', 2),
        ('基本EPS', 'eps_basic', 'CAS', 2),
        ('(一) 基本每股收益', 'eps_basic', 'CAS', 2),
        ('每股基本收益', 'eps_basic', 'CAS', 2),
        ('第42行', 'eps_basic', 'CAS', 3),
        ('42行', 'eps_basic', 'CAS', 3),
        ('第四十二行', 'eps_basic', 'CAS', 3),
        # 稀释每股收益
        ('稀释每股收益', 'eps_diluted', 'CAS', 2),
        ('稀释每股盈利', 'eps_diluted', 'CAS', 2),
        ('稀释EPS', 'eps_diluted', 'CAS', 2),
        ('(二) 稀释每股收益', 'eps_diluted', 'CAS', 2),
        ('每股稀释收益', 'eps_diluted', 'CAS', 2),
        ('第43行', 'eps_diluted', 'CAS', 3),
        ('43行', 'eps_diluted', 'CAS', 3),
        ('第四十三行', 'eps_diluted', 'CAS', 3),
    ]

    # ── SAS 同义词 ──
    sas_rows = [
        # 营业收入
        ('营业收入', 'operating_revenue', 'SAS', 2),
        ('营业收入本期', 'operating_revenue', 'SAS', 2),
        ('营业收入累计', 'operating_revenue', 'SAS', 2),
        ('营收', 'operating_revenue', 'SAS', 2),
        ('经营收入', 'operating_revenue', 'SAS', 2),
        ('主营收入', 'operating_revenue', 'SAS', 2),
        ('一、营业收入', 'operating_revenue', 'SAS', 2),
        ('第1行', 'operating_revenue', 'SAS', 3),
        ('1行', 'operating_revenue', 'SAS', 3),
        ('第一行', 'operating_revenue', 'SAS', 3),
        # 营业成本
        ('营业成本', 'operating_cost', 'SAS', 2),
        ('减：营业成本', 'operating_cost', 'SAS', 2),
        ('经营成本', 'operating_cost', 'SAS', 2),
        ('主营成本', 'operating_cost', 'SAS', 2),
        ('成本', 'operating_cost', 'SAS', 2),
        ('第2行', 'operating_cost', 'SAS', 3),
        ('2行', 'operating_cost', 'SAS', 3),
        ('第二行', 'operating_cost', 'SAS', 3),
        # 税金及附加
        ('税金及附加', 'taxes_and_surcharges', 'SAS', 2),
        ('税费及附加', 'taxes_and_surcharges', 'SAS', 2),
        ('税金附加', 'taxes_and_surcharges', 'SAS', 2),
        ('附加税', 'taxes_and_surcharges', 'SAS', 2),
        ('税及附加', 'taxes_and_surcharges', 'SAS', 2),
        ('第3行', 'taxes_and_surcharges', 'SAS', 3),
        ('3行', 'taxes_and_surcharges', 'SAS', 3),
        ('第三行', 'taxes_and_surcharges', 'SAS', 3),
        # 消费税
        ('消费税', 'consumption_tax', 'SAS', 2),
        ('消费税费', 'consumption_tax', 'SAS', 2),
        ('消费税金额', 'consumption_tax', 'SAS', 2),
        ('其中：消费税', 'consumption_tax', 'SAS', 2),
        ('消费税金', 'consumption_tax', 'SAS', 2),
        ('第4行', 'consumption_tax', 'SAS', 3),
        ('4行', 'consumption_tax', 'SAS', 3),
        ('第四行', 'consumption_tax', 'SAS', 3),
        # 营业税
        ('营业税', 'business_tax', 'SAS', 2),
        ('营业税费', 'business_tax', 'SAS', 2),
        ('营业税金', 'business_tax', 'SAS', 2),
        ('营业税额', 'business_tax', 'SAS', 2),
        ('第5行', 'business_tax', 'SAS', 3),
        ('5行', 'business_tax', 'SAS', 3),
        ('第五行', 'business_tax', 'SAS', 3),
        # 城市维护建设税
        ('城市维护建设税', 'city_maintenance_tax', 'SAS', 2),
        ('城建税', 'city_maintenance_tax', 'SAS', 2),
        ('城市维护税', 'city_maintenance_tax', 'SAS', 2),
        ('城建税费', 'city_maintenance_tax', 'SAS', 2),
        ('城建税金', 'city_maintenance_tax', 'SAS', 2),
        ('第6行', 'city_maintenance_tax', 'SAS', 3),
        ('6行', 'city_maintenance_tax', 'SAS', 3),
        ('第六行', 'city_maintenance_tax', 'SAS', 3),
        # 资源税
        ('资源税', 'resource_tax', 'SAS', 2),
        ('资源税费', 'resource_tax', 'SAS', 2),
        ('资源税金', 'resource_tax', 'SAS', 2),
        ('资源税额', 'resource_tax', 'SAS', 2),
        ('第7行', 'resource_tax', 'SAS', 3),
        ('7行', 'resource_tax', 'SAS', 3),
        ('第七行', 'resource_tax', 'SAS', 3),
        # 土地增值税
        ('土地增值税', 'land_appreciation_tax', 'SAS', 2),
        ('土增税', 'land_appreciation_tax', 'SAS', 2),
        ('土地增值税费', 'land_appreciation_tax', 'SAS', 2),
        ('土增税金', 'land_appreciation_tax', 'SAS', 2),
        ('第8行', 'land_appreciation_tax', 'SAS', 3),
        ('8行', 'land_appreciation_tax', 'SAS', 3),
        ('第八行', 'land_appreciation_tax', 'SAS', 3),
        # 城镇土地使用税、房产税、车船税、印花税
        ('城镇土地使用税、房产税、车船税、印花税', 'property_related_taxes', 'SAS', 2),
        ('土地使用税、房产税、车船税、印花税', 'property_related_taxes', 'SAS', 2),
        ('房产税、车船税、印花税、土地使用税', 'property_related_taxes', 'SAS', 2),
        ('小税种合计', 'property_related_taxes', 'SAS', 2),
        ('财产税及其他税', 'property_related_taxes', 'SAS', 2),
        ('第9行', 'property_related_taxes', 'SAS', 3),
        ('9行', 'property_related_taxes', 'SAS', 3),
        ('第九行', 'property_related_taxes', 'SAS', 3),
        # 教育费附加、矿产资源补偿费、排污费
        ('教育费附加、矿产资源补偿费、排污费', 'education_surcharge', 'SAS', 2),
        ('教育费附加及其他', 'education_surcharge', 'SAS', 2),
        ('教育附加费', 'education_surcharge', 'SAS', 2),
        ('矿产资源补偿费', 'education_surcharge', 'SAS', 2),
        ('排污费', 'education_surcharge', 'SAS', 2),
        ('第10行', 'education_surcharge', 'SAS', 3),
        ('10行', 'education_surcharge', 'SAS', 3),
        ('第十行', 'education_surcharge', 'SAS', 3),
        # 销售费用
        ('销售费用', 'selling_expense', 'SAS', 2),
        ('销售费', 'selling_expense', 'SAS', 2),
        ('营销费用', 'selling_expense', 'SAS', 2),
        ('营销费', 'selling_expense', 'SAS', 2),
        ('售卖费用', 'selling_expense', 'SAS', 2),
        ('第11行', 'selling_expense', 'SAS', 3),
        ('11行', 'selling_expense', 'SAS', 3),
        ('第十一行', 'selling_expense', 'SAS', 3),
        # 商品维修费
        ('商品维修费', 'goods_repair_expense', 'SAS', 2),
        ('维修费', 'goods_repair_expense', 'SAS', 2),
        ('产品维修费', 'goods_repair_expense', 'SAS', 2),
        ('商品维修费用', 'goods_repair_expense', 'SAS', 2),
        ('其中：商品维修费', 'goods_repair_expense', 'SAS', 2),
        ('第12行', 'goods_repair_expense', 'SAS', 3),
        ('12行', 'goods_repair_expense', 'SAS', 3),
        ('第十二行', 'goods_repair_expense', 'SAS', 3),
        # 广告费和业务宣传费
        ('广告费和业务宣传费', 'advertising_expense', 'SAS', 2),
        ('广告费', 'advertising_expense', 'SAS', 2),
        ('宣传费', 'advertising_expense', 'SAS', 2),
        ('广告宣传费', 'advertising_expense', 'SAS', 2),
        ('业务宣传费', 'advertising_expense', 'SAS', 2),
        ('第13行', 'advertising_expense', 'SAS', 3),
        ('13行', 'advertising_expense', 'SAS', 3),
        ('第十三行', 'advertising_expense', 'SAS', 3),
        # 管理费用
        ('管理费用', 'administrative_expense', 'SAS', 2),
        ('管理费', 'administrative_expense', 'SAS', 2),
        ('管理开支', 'administrative_expense', 'SAS', 2),
        ('行政费用', 'administrative_expense', 'SAS', 2),
        ('行政费', 'administrative_expense', 'SAS', 2),
        ('第14行', 'administrative_expense', 'SAS', 3),
        ('14行', 'administrative_expense', 'SAS', 3),
        ('第十四行', 'administrative_expense', 'SAS', 3),
        # 开办费
        ('开办费', 'organization_expense', 'SAS', 2),
        ('开办费用', 'organization_expense', 'SAS', 2),
        ('筹备费', 'organization_expense', 'SAS', 2),
        ('设立费', 'organization_expense', 'SAS', 2),
        ('其中：开办费', 'organization_expense', 'SAS', 2),
        ('第15行', 'organization_expense', 'SAS', 3),
        ('15行', 'organization_expense', 'SAS', 3),
        ('第十五行', 'organization_expense', 'SAS', 3),
        # 业务招待费
        ('业务招待费', 'business_entertainment_expense', 'SAS', 2),
        ('招待费', 'business_entertainment_expense', 'SAS', 2),
        ('业务招待费用', 'business_entertainment_expense', 'SAS', 2),
        ('交际费', 'business_entertainment_expense', 'SAS', 2),
        ('应酬费', 'business_entertainment_expense', 'SAS', 2),
        ('第16行', 'business_entertainment_expense', 'SAS', 3),
        ('16行', 'business_entertainment_expense', 'SAS', 3),
        ('第十六行', 'business_entertainment_expense', 'SAS', 3),
        # 研究费用
        ('研究费用', 'research_expense', 'SAS', 2),
        ('研究费', 'research_expense', 'SAS', 2),
        ('研发费用', 'research_expense', 'SAS', 2),
        ('研发费', 'research_expense', 'SAS', 2),
        ('研发支出', 'research_expense', 'SAS', 2),
        ('第17行', 'research_expense', 'SAS', 3),
        ('17行', 'research_expense', 'SAS', 3),
        ('第十七行', 'research_expense', 'SAS', 3),
        # 财务费用
        ('财务费用', 'financial_expense', 'SAS', 2),
        ('财务费', 'financial_expense', 'SAS', 2),
        ('财务开支', 'financial_expense', 'SAS', 2),
        ('筹资费用', 'financial_expense', 'SAS', 2),
        ('资金费用', 'financial_expense', 'SAS', 2),
        ('第18行', 'financial_expense', 'SAS', 3),
        ('18行', 'financial_expense', 'SAS', 3),
        ('第十八行', 'financial_expense', 'SAS', 3),
        # 利息费用 (SAS → interest_expense_net)
        ('利息费用', 'interest_expense_net', 'SAS', 2),
        ('利息费用（收入以"-"号填列）', 'interest_expense_net', 'SAS', 2),
        ('利息费', 'interest_expense_net', 'SAS', 2),
        ('利息支出', 'interest_expense_net', 'SAS', 2),
        ('借款利息', 'interest_expense_net', 'SAS', 2),
        ('第19行', 'interest_expense_net', 'SAS', 3),
        ('19行', 'interest_expense_net', 'SAS', 3),
        ('第十九行', 'interest_expense_net', 'SAS', 3),
        # 投资收益
        ('投资收益', 'investment_income', 'SAS', 2),
        ('投资收益（亏损以"-"号填列）', 'investment_income', 'SAS', 2),
        ('加：投资收益', 'investment_income', 'SAS', 2),
        ('投资利润', 'investment_income', 'SAS', 2),
        ('投资回报', 'investment_income', 'SAS', 2),
        ('第20行', 'investment_income', 'SAS', 3),
        ('20行', 'investment_income', 'SAS', 3),
        ('第二十行', 'investment_income', 'SAS', 3),
        # 营业利润
        ('营业利润', 'operating_profit', 'SAS', 2),
        ('营业利润（亏损以"-"号填列）', 'operating_profit', 'SAS', 2),
        ('二、营业利润', 'operating_profit', 'SAS', 2),
        ('经营利润', 'operating_profit', 'SAS', 2),
        ('主营利润', 'operating_profit', 'SAS', 2),
        ('第21行', 'operating_profit', 'SAS', 3),
        ('21行', 'operating_profit', 'SAS', 3),
        ('第二十一行', 'operating_profit', 'SAS', 3),
        # 营业外收入
        ('营业外收入', 'non_operating_income', 'SAS', 2),
        ('加：营业外收入', 'non_operating_income', 'SAS', 2),
        ('非营业收入', 'non_operating_income', 'SAS', 2),
        ('营业外收益', 'non_operating_income', 'SAS', 2),
        ('额外收入', 'non_operating_income', 'SAS', 2),
        ('第22行', 'non_operating_income', 'SAS', 3),
        ('22行', 'non_operating_income', 'SAS', 3),
        ('第二十二行', 'non_operating_income', 'SAS', 3),
        # 政府补助
        ('政府补助', 'government_grant', 'SAS', 2),
        ('政府补贴', 'government_grant', 'SAS', 2),
        ('财政补助', 'government_grant', 'SAS', 2),
        ('其中：政府补助', 'government_grant', 'SAS', 2),
        ('政府扶持资金', 'government_grant', 'SAS', 2),
        ('第23行', 'government_grant', 'SAS', 3),
        ('23行', 'government_grant', 'SAS', 3),
        ('第二十三行', 'government_grant', 'SAS', 3),
        # 营业外支出
        ('营业外支出', 'non_operating_expense', 'SAS', 2),
        ('减：营业外支出', 'non_operating_expense', 'SAS', 2),
        ('非营业支出', 'non_operating_expense', 'SAS', 2),
        ('营业外开销', 'non_operating_expense', 'SAS', 2),
        ('额外支出', 'non_operating_expense', 'SAS', 2),
        ('第24行', 'non_operating_expense', 'SAS', 3),
        ('24行', 'non_operating_expense', 'SAS', 3),
        ('第二十四行', 'non_operating_expense', 'SAS', 3),
        # 坏账损失
        ('坏账损失', 'bad_debt_loss', 'SAS', 2),
        ('坏账亏损', 'bad_debt_loss', 'SAS', 2),
        ('坏账减值损失', 'bad_debt_loss', 'SAS', 2),
        ('其中：坏账损失', 'bad_debt_loss', 'SAS', 2),
        ('坏账费用', 'bad_debt_loss', 'SAS', 2),
        ('第25行', 'bad_debt_loss', 'SAS', 3),
        ('25行', 'bad_debt_loss', 'SAS', 3),
        ('第二十五行', 'bad_debt_loss', 'SAS', 3),
        # 无法收回的长期债券投资损失
        ('无法收回的长期债券投资损失', 'long_term_bond_loss', 'SAS', 2),
        ('长期债券投资损失', 'long_term_bond_loss', 'SAS', 2),
        ('债券投资无法收回损失', 'long_term_bond_loss', 'SAS', 2),
        ('长期债券坏账损失', 'long_term_bond_loss', 'SAS', 2),
        ('债券投资损失', 'long_term_bond_loss', 'SAS', 2),
        ('第26行', 'long_term_bond_loss', 'SAS', 3),
        ('26行', 'long_term_bond_loss', 'SAS', 3),
        ('第二十六行', 'long_term_bond_loss', 'SAS', 3),
        # 无法收回的长期股权投资损失
        ('无法收回的长期股权投资损失', 'long_term_equity_loss', 'SAS', 2),
        ('长期股权投资损失', 'long_term_equity_loss', 'SAS', 2),
        ('股权投资无法收回损失', 'long_term_equity_loss', 'SAS', 2),
        ('长期股权坏账损失', 'long_term_equity_loss', 'SAS', 2),
        ('股权投资损失', 'long_term_equity_loss', 'SAS', 2),
        ('第27行', 'long_term_equity_loss', 'SAS', 3),
        ('27行', 'long_term_equity_loss', 'SAS', 3),
        ('第二十七行', 'long_term_equity_loss', 'SAS', 3),
        # 自然灾害等不可抗力因素造成的损失
        ('自然灾害等不可抗力因素造成的损失', 'force_majeure_loss', 'SAS', 2),
        ('自然灾害损失', 'force_majeure_loss', 'SAS', 2),
        ('不可抗力损失', 'force_majeure_loss', 'SAS', 2),
        ('天灾损失', 'force_majeure_loss', 'SAS', 2),
        ('意外损失', 'force_majeure_loss', 'SAS', 2),
        ('第28行', 'force_majeure_loss', 'SAS', 3),
        ('28行', 'force_majeure_loss', 'SAS', 3),
        ('第二十八行', 'force_majeure_loss', 'SAS', 3),
        # 税收滞纳金
        ('税收滞纳金', 'tax_late_payment', 'SAS', 2),
        ('滞纳金', 'tax_late_payment', 'SAS', 2),
        ('税务滞纳金', 'tax_late_payment', 'SAS', 2),
        ('税款滞纳金', 'tax_late_payment', 'SAS', 2),
        ('税收罚款', 'tax_late_payment', 'SAS', 2),
        ('第29行', 'tax_late_payment', 'SAS', 3),
        ('29行', 'tax_late_payment', 'SAS', 3),
        ('第二十九行', 'tax_late_payment', 'SAS', 3),
        # 利润总额
        ('利润总额', 'total_profit', 'SAS', 2),
        ('利润总额（亏损总额以"-"号填列）', 'total_profit', 'SAS', 2),
        ('三、利润总额', 'total_profit', 'SAS', 2),
        ('税前利润', 'total_profit', 'SAS', 2),
        ('总利润', 'total_profit', 'SAS', 2),
        ('第30行', 'total_profit', 'SAS', 3),
        ('30行', 'total_profit', 'SAS', 3),
        ('第三十行', 'total_profit', 'SAS', 3),
        # 所得税费用
        ('所得税费用', 'income_tax_expense', 'SAS', 2),
        ('减：所得税费用', 'income_tax_expense', 'SAS', 2),
        ('所得税', 'income_tax_expense', 'SAS', 2),
        ('所得税费', 'income_tax_expense', 'SAS', 2),
        ('企业所得税', 'income_tax_expense', 'SAS', 2),
        ('第31行', 'income_tax_expense', 'SAS', 3),
        ('31行', 'income_tax_expense', 'SAS', 3),
        ('第三十一行', 'income_tax_expense', 'SAS', 3),
        # 净利润
        ('净利润', 'net_profit', 'SAS', 2),
        ('净利润（净亏损以"-"号填列）', 'net_profit', 'SAS', 2),
        ('四、净利润', 'net_profit', 'SAS', 2),
        ('纯利润', 'net_profit', 'SAS', 2),
        ('税后利润', 'net_profit', 'SAS', 2),
        ('净利', 'net_profit', 'SAS', 2),
        ('第32行', 'net_profit', 'SAS', 3),
        ('32行', 'net_profit', 'SAS', 3),
        ('第三十二行', 'net_profit', 'SAS', 3),
    ]

    # ── 批量插入 ──
    all_rows = cas_rows + sas_rows
    cur.executemany(
        "INSERT OR IGNORE INTO fs_income_statement_synonyms (phrase, column_name, gaap_type, priority) VALUES (?,?,?,?)",
        all_rows
    )
    count = cur.execute("SELECT COUNT(*) FROM fs_income_statement_synonyms").fetchone()[0]
    print(f"  利润表同义词: {count} 条")


def _seed_inv_column_mappings(cur):
    """发票字段映射（进项+销项）"""
    purchase_mappings = [
        ('序号', 'seq_no', 'inv_spec_purchase', '行序号'),
        ('发票代码', 'invoice_code', 'inv_spec_purchase', '发票代码'),
        ('发票号码', 'invoice_number', 'inv_spec_purchase', '发票号码'),
        ('数电票号码', 'digital_invoice_no', 'inv_spec_purchase', '数电票号码'),
        ('销方识别号', 'seller_tax_id', 'inv_spec_purchase', '销方纳税人识别号'),
        ('销方名称', 'seller_name', 'inv_spec_purchase', '销方名称'),
        ('购方识别号', 'buyer_tax_id', 'inv_spec_purchase', '购方纳税人识别号'),
        ('购买方名称', 'buyer_name', 'inv_spec_purchase', '购买方名称'),
        ('开票日期', 'invoice_date', 'inv_spec_purchase', '开票日期'),
        ('税收分类编码', 'tax_category_code', 'inv_spec_purchase', '税收分类编码'),
        ('特定业务类型', 'special_business_type', 'inv_spec_purchase', '特定业务类型'),
        ('货物或应税劳务名称', 'goods_name', 'inv_spec_purchase', '货物或应税劳务名称'),
        ('规格型号', 'specification', 'inv_spec_purchase', '规格型号'),
        ('单位', 'unit', 'inv_spec_purchase', '单位'),
        ('数量', 'quantity', 'inv_spec_purchase', '数量'),
        ('单价', 'unit_price', 'inv_spec_purchase', '单价'),
        ('金额', 'amount', 'inv_spec_purchase', '不含税金额'),
        ('税率', 'tax_rate', 'inv_spec_purchase', '税率'),
        ('税额', 'tax_amount', 'inv_spec_purchase', '税额'),
        ('价税合计', 'total_amount', 'inv_spec_purchase', '价税合计'),
        ('发票来源', 'invoice_source', 'inv_spec_purchase', '发票来源'),
        ('发票票种', 'invoice_type', 'inv_spec_purchase', '发票票种'),
        ('发票状态', 'invoice_status', 'inv_spec_purchase', '发票状态'),
        ('是否正数发票', 'is_positive', 'inv_spec_purchase', '是否正数发票'),
        ('发票风险等级', 'risk_level', 'inv_spec_purchase', '发票风险等级'),
        ('开票人', 'issuer', 'inv_spec_purchase', '开票人'),
        ('备注', 'remark', 'inv_spec_purchase', '备注'),
    ]
    sales_mappings = [
        ('发票代码', 'invoice_code', 'inv_spec_sales', '发票代码'),
        ('发票号码', 'invoice_number', 'inv_spec_sales', '发票号码'),
        ('数电票号码', 'digital_invoice_no', 'inv_spec_sales', '数电票号码'),
        ('销方识别号', 'seller_tax_id', 'inv_spec_sales', '销方纳税人识别号'),
        ('销方名称', 'seller_name', 'inv_spec_sales', '销方名称'),
        ('购方识别号', 'buyer_tax_id', 'inv_spec_sales', '购方纳税人识别号'),
        ('购买方名称', 'buyer_name', 'inv_spec_sales', '购买方名称'),
        ('开票日期', 'invoice_date', 'inv_spec_sales', '开票日期'),
        ('金额', 'amount', 'inv_spec_sales', '不含税金额'),
        ('税额', 'tax_amount', 'inv_spec_sales', '税额'),
        ('价税合计', 'total_amount', 'inv_spec_sales', '价税合计'),
        ('发票来源', 'invoice_source', 'inv_spec_sales', '发票来源'),
        ('发票票种', 'invoice_type', 'inv_spec_sales', '发票票种'),
        ('发票状态', 'invoice_status', 'inv_spec_sales', '发票状态'),
        ('是否正数发票', 'is_positive', 'inv_spec_sales', '是否正数发票'),
        ('发票风险等级', 'risk_level', 'inv_spec_sales', '发票风险等级'),
        ('开票人', 'issuer', 'inv_spec_sales', '开票人'),
        ('备注', 'remark', 'inv_spec_sales', '备注'),
    ]
    all_mappings = purchase_mappings + sales_mappings
    cur.executemany(
        "INSERT OR IGNORE INTO inv_column_mapping (source_column, target_field, table_name, description) VALUES (?,?,?,?)",
        all_mappings
    )
    print(f"  发票字段映射: {len(all_mappings)} 条")


def _seed_inv_synonyms(cur):
    """发票同义词（~80条）"""
    # (phrase, column_name, priority, scope_view)
    rows = [
        # 金额类
        ('金额', 'amount', 1, None),
        ('不含税金额', 'amount', 2, None),
        ('税额', 'tax_amount', 1, None),
        ('增值税额', 'tax_amount', 2, None),
        ('价税合计', 'total_amount', 2, None),
        ('含税金额', 'total_amount', 1, None),
        ('发票金额', 'amount', 2, None),
        # 票面信息
        ('发票代码', 'invoice_code', 2, None),
        ('发票号码', 'invoice_number', 2, None),
        ('数电票号码', 'digital_invoice_no', 2, None),
        ('票号', 'invoice_pk', 1, None),
        ('发票编号', 'invoice_pk', 1, None),
        # 对方信息
        ('购买方', 'buyer_name', 1, None),
        ('购方', 'buyer_name', 1, None),
        ('购方名称', 'buyer_name', 2, None),
        ('购买方名称', 'buyer_name', 2, None),
        ('销售方', 'seller_name', 1, None),
        ('销方', 'seller_name', 1, None),
        ('销方名称', 'seller_name', 2, None),
        ('购方识别号', 'buyer_tax_id', 2, None),
        ('销方识别号', 'seller_tax_id', 2, None),
        ('供应商', 'seller_name', 1, 'vw_inv_spec_purchase'),
        ('客户', 'buyer_name', 1, 'vw_inv_spec_sales'),
        # 状态类
        ('发票状态', 'invoice_status', 2, None),
        ('正常发票', 'invoice_status', 1, None),
        ('作废', 'invoice_status', 1, None),
        ('红冲', 'is_positive', 1, None),
        ('红字', 'is_positive', 1, None),
        ('蓝字', 'is_positive', 1, None),
        ('正数发票', 'is_positive', 2, None),
        ('负数发票', 'is_positive', 1, None),
        ('红冲发票', 'is_positive', 2, None),
        # 票种类
        ('专用发票', 'invoice_type', 2, None),
        ('普通发票', 'invoice_type', 2, None),
        ('数电票', 'invoice_format', 2, None),
        ('纸质发票', 'invoice_format', 1, None),
        # 风险类
        ('风险等级', 'risk_level', 2, None),
        ('发票风险', 'risk_level', 1, None),
        # 明细类（进项scope）
        ('商品名称', 'goods_name', 1, 'vw_inv_spec_purchase'),
        ('货物名称', 'goods_name', 1, 'vw_inv_spec_purchase'),
        ('劳务名称', 'goods_name', 1, 'vw_inv_spec_purchase'),
        ('规格型号', 'specification', 2, 'vw_inv_spec_purchase'),
        ('规格', 'specification', 1, 'vw_inv_spec_purchase'),
        ('型号', 'specification', 1, 'vw_inv_spec_purchase'),
        ('单位', 'unit', 1, 'vw_inv_spec_purchase'),
        ('数量', 'quantity', 1, 'vw_inv_spec_purchase'),
        ('单价', 'unit_price', 1, 'vw_inv_spec_purchase'),
        ('税率', 'tax_rate', 1, 'vw_inv_spec_purchase'),
        ('税收分类编码', 'tax_category_code', 2, 'vw_inv_spec_purchase'),
        # 其他
        ('开票日期', 'invoice_date', 2, None),
        ('开票时间', 'invoice_date', 1, None),
        ('开票人', 'issuer', 2, None),
        ('备注', 'remark', 1, None),
        ('发票来源', 'invoice_source', 2, None),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO inv_synonyms (phrase, column_name, priority, scope_view) VALUES (?,?,?,?)",
        rows
    )
    count = cur.execute("SELECT COUNT(*) FROM inv_synonyms").fetchone()[0]
    print(f"  发票同义词: {count} 条")


def _seed_financial_metrics_item_dict(cur):
    """插入25个财务指标定义到 financial_metrics_item_dict"""
    import json
    rows = [
        # (metric_code, metric_name, metric_category, metric_unit, formula_desc, source_domains, period_types, eval_rules, eval_ascending, display_order, is_active)
        ('gross_margin', '毛利率', '盈利能力', '%',
         '(营业收入-营业成本)/营业收入×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[30,"优"],[15,"良"],[5,"中"],[None,"差"]]), 0, 1, 1),
        ('net_margin', '净利率', '盈利能力', '%',
         '净利润/营业收入×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[15,"优"],[8,"良"],[3,"中"],[None,"差"]]), 0, 2, 1),
        ('roe', '净资产收益率(ROE)', '盈利能力', '%',
         '净利润/平均净资产×100', 'profit,balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[15,"优"],[8,"良"],[3,"中"],[None,"差"]]), 0, 3, 1),
        ('net_profit_growth', '净利润增长率', '盈利能力', '%',
         '(本期净利润-上期净利润)/上期净利润×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[20,"优"],[10,"良"],[0,"中"],[None,"差"]]), 0, 4, 1),
        ('admin_expense_ratio', '管理费用率', '费用控制', '%',
         '管理费用/营业收入×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[5,"优"],[10,"良"],[15,"中"],[None,"差"]]), 1, 5, 1),
        ('sales_expense_ratio', '销售费用率', '费用控制', '%',
         '销售费用/营业收入×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[8,"优"],[15,"良"],[20,"中"],[None,"差"]]), 1, 6, 1),
        ('debt_ratio', '资产负债率', '偿债能力', '%',
         '负债总额/资产总额×100', 'balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[40,"优"],[60,"良"],[70,"中"],[None,"差"]]), 1, 7, 1),
        ('current_ratio', '流动比率', '偿债能力', '',
         '流动资产/流动负债', 'balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[2.0,"优"],[1.5,"良"],[1.0,"中"],[None,"差"]]), 0, 8, 1),
        ('quick_ratio', '速动比率', '偿债能力', '',
         '(流动资产-存货)/流动负债', 'balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[1.5,"优"],[1.0,"良"],[0.5,"中"],[None,"差"]]), 0, 9, 1),
        ('cash_debt_coverage', '现金债务保障比率', '偿债能力', '%',
         '经营活动现金流量净额/负债总额×100', 'cash_flow,balance_sheet', 'monthly,quarterly,annual',
         None, 0, 10, 1),
        ('ar_turnover', '应收账款周转率', '营运能力', '次',
         '营业收入/平均应收账款', 'profit,balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[12,"优"],[6,"良"],[3,"中"],[None,"差"]]), 0, 11, 1),
        ('ar_days', '应收款周转天数', '营运能力', '天',
         '360/应收账款周转率', 'profit,balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[30,"优"],[60,"良"],[90,"中"],[None,"差"]]), 1, 12, 1),
        ('inventory_turnover', '存货周转率', '营运能力', '次',
         '营业成本/平均存货', 'profit,balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[8,"优"],[4,"良"],[2,"中"],[None,"差"]]), 0, 13, 1),
        ('asset_turnover', '总资产周转率', '营运能力', '次',
         '营业收入/平均总资产', 'profit,balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[1.2,"优"],[0.8,"良"],[0.5,"中"],[None,"差"]]), 0, 14, 1),
        ('revenue_growth', '营业收入增长率', '成长能力', '%',
         '(本期营业收入-上期营业收入)/上期营业收入×100', 'profit', 'monthly,quarterly,annual',
         json.dumps([[20,"优"],[10,"良"],[0,"中"],[None,"差"]]), 0, 15, 1),
        ('asset_growth', '资产增长率', '成长能力', '%',
         '(本期资产总额-上期资产总额)/上期资产总额×100', 'balance_sheet', 'monthly,quarterly,annual',
         json.dumps([[20,"优"],[10,"良"],[0,"中"],[None,"差"]]), 0, 16, 1),
        ('cash_to_revenue', '销售收现比', '现金流', '',
         '销售商品收到的现金/营业收入', 'cash_flow,profit', 'monthly,quarterly,annual',
         json.dumps([[1.0,"优"],[0.8,"良"],[0.5,"中"],[None,"差"]]), 0, 17, 1),
        ('vat_burden', '增值税税负率', '税负率类', '%',
         '应纳税额/应税销售额×100', 'vat', 'monthly,quarterly,annual',
         None, 0, 18, 1),
        ('eit_burden', '企业所得税税负率', '税负率类', '%',
         '实际应纳所得税额/营业收入×100', 'eit,profit', 'quarterly,annual',
         None, 0, 19, 1),
        ('total_tax_burden', '综合税负率', '税负率类', '%',
         '(增值税+附加税+所得税)/营业收入×100', 'vat,eit,profit', 'monthly,quarterly,annual',
         None, 0, 20, 1),
        ('output_input_ratio', '销项进项配比率', '增值税重点指标', '',
         '销项税额/进项税额', 'vat', 'monthly,quarterly,annual',
         None, 0, 21, 1),
        ('transfer_out_ratio', '进项税额转出占比', '增值税重点指标', '%',
         '进项税额转出/进项税额×100', 'vat', 'monthly,quarterly,annual',
         None, 0, 22, 1),
        ('taxable_income_ratio', '应税所得率', '所得税重点指标', '%',
         '应纳税所得额/营业收入×100', 'eit', 'quarterly,annual',
         None, 0, 23, 1),
        ('zero_filing_ratio', '零申报率', '风险预警类', '%',
         '零申报月份数/总月份数×100', 'vat', 'quarterly,annual',
         None, 0, 24, 1),
        ('invoice_anomaly_ratio', '发票开具异常率', '风险预警类', '%',
         '顶额开具发票数/总发票数×100', 'invoice', 'monthly,quarterly,annual',
         None, 0, 25, 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO financial_metrics_item_dict "
        "(metric_code, metric_name, metric_category, metric_unit, formula_desc, "
        "source_domains, period_types, eval_rules, eval_ascending, display_order, is_active) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows
    )
    count = cur.execute("SELECT COUNT(*) FROM financial_metrics_item_dict").fetchone()[0]
    print(f"  财务指标字典: {count} 条")


if __name__ == "__main__":
    seed_reference_data()
