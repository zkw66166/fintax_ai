# fintax_ai 数据库 Schema 完整文档

> 生成日期：2026-02-20 | 数据库：SQLite (`database/fintax_ai.db`)

## 目录

1. [维度表（字典表 & 纳税人主表）](#1-维度表)
2. [增值税申报表](#2-增值税申报表)
3. [企业所得税申报表](#3-企业所得税申报表)
4. [科目余额表](#4-科目余额表)
5. [财务报表（资产负债表 / 利润表 / 现金流量表）](#5-财务报表)
6. [发票表](#6-发票表)
7. [财务指标表](#7-财务指标表)
8. [跨域指标注册表](#8-跨域指标注册表)
9. [同义词映射表](#9-同义词映射表)
10. [字段映射表](#10-字段映射表)
11. [日志与审计表](#11-日志与审计表)
12. [视图](#12-视图)
13. [索引](#13-索引)
14. [设计模式总结](#14-设计模式总结)

---

## 1. 维度表

### 1.1 dim_industry（行业字典）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| industry_code | TEXT | PK | 行业代码 |
| industry_name | TEXT | NOT NULL | 行业名称 |
| parent_code | TEXT | | 上级行业代码 |

### 1.2 dim_tax_authority（税务机关字典）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| tax_authority_code | TEXT | PK | 税务机关代码 |
| tax_authority_name | TEXT | NOT NULL | 税务机关名称 |
| region_code | TEXT | | 区域代码 |
| level | TEXT | | 级别 |

### 1.3 dim_region（区域字典）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| region_code | TEXT | PK | 区域代码 |
| region_name | TEXT | NOT NULL | 区域名称 |
| parent_code | TEXT | | 上级区域代码 |

### 1.4 taxpayer_info（纳税人主表）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| taxpayer_id | TEXT | PK | 纳税人识别号 |
| taxpayer_name | TEXT | NOT NULL | 纳税人名称 |
| taxpayer_type | TEXT | NOT NULL | 纳税人类型：'一般纳税人' / '小规模纳税人' |
| registration_type | TEXT | | 登记注册类型 |
| legal_representative | TEXT | | 法定代表人 |
| establish_date | DATE | | 成立日期 |
| industry_code | TEXT | | 行业代码 |
| industry_name | TEXT | | 行业名称 |
| tax_authority_code | TEXT | | 主管税务机关代码 |
| tax_authority_name | TEXT | | 主管税务机关名称 |
| tax_bureau_level | TEXT | | 税务局级别 |
| region_code | TEXT | | 区域代码 |
| region_name | TEXT | | 区域名称 |
| credit_grade_current | TEXT | | 当前纳税信用等级 |
| credit_grade_year | INTEGER | | 信用等级评定年度 |
| accounting_standard | TEXT | | 会计准则：'企业会计准则' / '小企业会计准则' |
| status | TEXT | DEFAULT 'active' | 状态 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

索引：`idx_taxpayer_name(taxpayer_name)`, `idx_taxpayer_industry(industry_code)`, `idx_taxpayer_region(region_code)`, `idx_taxpayer_authority(tax_authority_code)`, `idx_taxpayer_type(taxpayer_type)`, `idx_taxpayer_type_industry(taxpayer_type, industry_code)`

### 1.5 taxpayer_profile_snapshot_month（纳税人月度快照）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| taxpayer_id | TEXT | PK(1), FK→taxpayer_info | 纳税人识别号 |
| period_year | INTEGER | PK(2) | 年度 |
| period_month | INTEGER | PK(3) | 月份 |
| industry_code | TEXT | | 行业代码 |
| tax_authority_code | TEXT | | 税务机关代码 |
| region_code | TEXT | | 区域代码 |
| credit_grade | TEXT | | 信用等级 |
| employee_scale | TEXT | | 员工规模 |
| revenue_scale | TEXT | | 收入规模 |
| source_doc_id | TEXT | | 来源文档ID |
| etl_batch_id | TEXT | | ETL批次ID |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

### 1.6 taxpayer_credit_grade_year（年度纳税信用等级）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| taxpayer_id | TEXT | PK(1), FK→taxpayer_info | 纳税人识别号 |
| year | INTEGER | PK(2) | 年度 |
| credit_grade | TEXT | NOT NULL | 信用等级 |
| published_at | DATE | | 发布日期 |
| source_doc_id | TEXT | | 来源文档ID |
| etl_batch_id | TEXT | | ETL批次ID |

---

## 2. 增值税申报表

### 2.1 vat_return_general（一般纳税人增值税申报表）

PK: `(taxpayer_id, period_year, period_month, item_type, time_range, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 申报年度 |
| period_month | INTEGER | 申报月份 |
| item_type | TEXT | '一般项目' / '即征即退项目' |
| time_range | TEXT | '本月' / '累计' |
| revision_no | INTEGER | 修订版本号（≥0，默认0） |
| submitted_at | TIMESTAMP | 提交时间 |
| etl_batch_id | TEXT | ETL批次ID |
| source_doc_id | TEXT | 来源文档ID |
| source_unit | TEXT | 金额单位（默认'元'） |
| etl_confidence | REAL | ETL置信度 |
| **销售额字段** | | |
| sales_taxable_rate | NUMERIC | 按适用税率计税销售额 |
| sales_goods | NUMERIC | 应税货物销售额 |
| sales_services | NUMERIC | 应税劳务销售额 |
| sales_adjustment_check | NUMERIC | 纳税检查调整的销售额 |
| sales_simple_method | NUMERIC | 按简易办法计税销售额 |
| sales_simple_adjust_check | NUMERIC | 简易办法纳税检查调整 |
| sales_export_credit_refund | NUMERIC | 免抵退办法出口销售额 |
| sales_tax_free | NUMERIC | 免税销售额 |
| sales_tax_free_goods | NUMERIC | 免税货物销售额 |
| sales_tax_free_services | NUMERIC | 免税劳务销售额 |
| **税额字段** | | |
| output_tax | NUMERIC | 销项税额（第11行） |
| input_tax | NUMERIC | 进项税额（第12行） |
| last_period_credit | NUMERIC | 上期留抵税额（第13行） |
| transfer_out | NUMERIC | 进项税额转出（第14行） |
| export_refund | NUMERIC | 免抵退应退税额（第15行） |
| tax_check_supplement | NUMERIC | 纳税检查应补缴税额（第16行） |
| deductible_total | NUMERIC | 应抵扣税额合计（第17行） |
| actual_deduct | NUMERIC | 实际抵扣税额（第18行） |
| tax_payable | NUMERIC | 应纳税额（第19行） |
| end_credit | NUMERIC | 期末留抵税额（第20行） |
| simple_tax | NUMERIC | 简易计税应纳税额（第21行） |
| simple_tax_check_supplement | NUMERIC | 简易计税纳税检查应补缴（第22行） |
| tax_reduction | NUMERIC | 应纳税额减征额（第23行） |
| total_tax_payable | NUMERIC | 应纳税额合计（第24行） |
| **缴款字段** | | |
| unpaid_begin | NUMERIC | 期初未缴税额（第25行） |
| export_receipt_tax | NUMERIC | 实收出口专用缴款书退税额（第26行） |
| paid_current | NUMERIC | 本期已缴税额（第27行） |
| prepaid_installment | NUMERIC | 分次预缴税额（第28行） |
| prepaid_export_receipt | NUMERIC | 出口专用缴款书预缴税额（第29行） |
| paid_last_period | NUMERIC | 本期缴纳上期应纳税额（第30行） |
| paid_arrears | NUMERIC | 本期缴纳欠缴税额（第31行） |
| unpaid_end | NUMERIC | 期末未缴税额（第32行） |
| arrears | NUMERIC | 欠缴税额（第33行） |
| supplement_refund | NUMERIC | 本期应补退税额（第34行） |
| immediate_refund | NUMERIC | 即征即退实际退税额（第35行） |
| unpaid_check_begin | NUMERIC | 期初未缴查补税额（第36行） |
| paid_check_current | NUMERIC | 本期入库查补税额（第37行） |
| unpaid_check_end | NUMERIC | 期末未缴查补税额（第38行） |
| **附加税字段** | | |
| city_maintenance_tax | NUMERIC | 城市维护建设税应补退税额（第39行） |
| education_surcharge | NUMERIC | 教育费附加应补退费额（第40行） |
| local_education_surcharge | NUMERIC | 地方教育附加应补退费额（第41行） |

### 2.2 vat_return_small（小规模纳税人增值税申报表）

PK: `(taxpayer_id, period_year, period_month, item_type, time_range, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 申报年度 |
| period_month | INTEGER | 申报月份 |
| item_type | TEXT | '货物及劳务' / '服务不动产无形资产' |
| time_range | TEXT | '本期' / '累计' |
| revision_no | INTEGER | 修订版本号（≥0，默认0） |
| submitted_at | TIMESTAMP | 提交时间 |
| etl_batch_id / source_doc_id / source_unit / etl_confidence | | 同一般纳税人表 |
| **3%征收率** | | |
| sales_3percent | NUMERIC | 应征增值税不含税销售额（3%）（第1行） |
| sales_3percent_invoice_spec | NUMERIC | 增值税专用发票不含税销售额（第2行） |
| sales_3percent_invoice_other | NUMERIC | 其他增值税发票不含税销售额（第3行） |
| **5%征收率** | | |
| sales_5percent | NUMERIC | 应征增值税不含税销售额（5%）（第4行） |
| sales_5percent_invoice_spec | NUMERIC | 专用发票不含税销售额（5%）（第5行） |
| sales_5percent_invoice_other | NUMERIC | 其他发票不含税销售额（5%）（第6行） |
| **旧固定资产** | | |
| sales_used_assets | NUMERIC | 销售使用过的固定资产不含税销售额（第7行） |
| sales_used_assets_invoice_other | NUMERIC | 其中其他发票不含税销售额（第8行） |
| **免税** | | |
| sales_tax_free | NUMERIC | 免税销售额（第9行） |
| sales_tax_free_micro | NUMERIC | 小微企业免税销售额（第10行） |
| sales_tax_free_threshold | NUMERIC | 未达起征点销售额（第11行） |
| sales_tax_free_other | NUMERIC | 其他免税销售额（第12行） |
| **出口免税** | | |
| sales_export_tax_free | NUMERIC | 出口免税销售额（第13行） |
| sales_export_tax_free_invoice_other | NUMERIC | 其中其他发票不含税销售额（第14行） |
| **税额** | | |
| tax_due_current | NUMERIC | 本期应纳税额（第15行） |
| tax_due_reduction | NUMERIC | 本期应纳税额减征额（第16行） |
| tax_free_amount | NUMERIC | 本期免税额（第17行） |
| tax_free_micro | NUMERIC | 其中小微企业免税额（第18行） |
| tax_free_threshold | NUMERIC | 未达起征点免税额（第19行） |
| tax_due_total | NUMERIC | 应纳税额合计（第20行） |
| tax_prepaid | NUMERIC | 本期预缴税额（第21行） |
| tax_supplement_refund | NUMERIC | 本期应补退税额（第22行） |
| **附加税** | | |
| city_maintenance_tax | NUMERIC | 城市维护建设税应补退税额（第23行） |
| education_surcharge | NUMERIC | 教育费附加应补退费额（第24行） |
| local_education_surcharge | NUMERIC | 地方教育附加应补退费额（第25行） |

---

## 3. 企业所得税申报表

### 3.1 eit_annual_filing（年度所得税申报主记录）

PK: `filing_id` | UNIQUE: `(taxpayer_id, period_year, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| filing_id | TEXT | PK，申报记录ID |
| taxpayer_id | TEXT | FK→taxpayer_info |
| period_year | INTEGER | 申报年度 |
| revision_no | INTEGER | 修订版本号（默认0） |
| amount_unit | TEXT | 金额单位（默认'元'） |
| preparer / preparer_id | TEXT | 填报人 / 填报人ID |
| agent_organization / agent_credit_code | TEXT | 代理机构 / 统一社会信用代码 |
| taxpayer_sign_date | DATE | 纳税人签章日期 |
| accepted_by / accepting_tax_office | TEXT | 受理人 / 受理税务机关 |
| date_accepted | DATE | 受理日期 |
| submitted_at | TIMESTAMP | 提交时间 |
| etl_batch_id / source_doc_id / etl_confidence | | ETL元数据 |
| created_at | TIMESTAMP | 创建时间 |

### 3.2 eit_annual_basic_info（年度基本信息 A000000）

PK/FK: `filing_id → eit_annual_filing`

| 列名 | 类型 | 说明 |
|------|------|------|
| tax_return_type_code | TEXT | 申报类型代码 |
| branch_tax_payment_ratio | NUMERIC | 分支机构就地纳税比例 |
| asset_avg | NUMERIC | 资产总额（万元） |
| employee_avg | INTEGER | 从业人数 |
| industry_code | TEXT | 所属行业代码 |
| restricted_or_prohibited | BOOLEAN | 是否从事限制/禁止行业 |
| accounting_standard_code | TEXT | 会计准则代码 |
| small_micro_enterprise | BOOLEAN | 是否小型微利企业 |
| listed_company | TEXT | 上市公司类型 |
| *(其余30+字段涵盖高新技术、创投、海南自贸港、重组等专项信息)* | | |

### 3.3 eit_annual_main（年度主表 A100000）

PK/FK: `filing_id → eit_annual_filing`

| 列名 | 类型 | 说明 |
|------|------|------|
| revenue | NUMERIC | 营业收入（第1行） |
| cost | NUMERIC | 营业成本（第2行） |
| taxes_surcharges | NUMERIC | 税金及附加（第3行） |
| selling_expenses | NUMERIC | 销售费用（第4行） |
| admin_expenses | NUMERIC | 管理费用（第5行） |
| rd_expenses | NUMERIC | 研发费用（第6行） |
| financial_expenses | NUMERIC | 财务费用（第7行） |
| other_gains | NUMERIC | 其他收益（第8行） |
| investment_income | NUMERIC | 投资收益（第9行） |
| net_exposure_hedge_gains | NUMERIC | 净敞口套期收益（第10行） |
| fair_value_change_gains | NUMERIC | 公允价值变动收益（第11行） |
| credit_impairment_loss | NUMERIC | 信用减值损失（第12行） |
| asset_impairment_loss | NUMERIC | 资产减值损失（第13行） |
| asset_disposal_gains | NUMERIC | 资产处置收益（第14行） |
| operating_profit | NUMERIC | 营业利润（第15行） |
| non_operating_income | NUMERIC | 营业外收入（第16行） |
| non_operating_expenses | NUMERIC | 营业外支出（第17行） |
| total_profit | NUMERIC | 利润总额（第18行） |
| less_foreign_income | NUMERIC | 减：境外所得（第19行） |
| add_tax_adjust_increase | NUMERIC | 加：纳税调整增加额（第20行） |
| less_tax_adjust_decrease | NUMERIC | 减：纳税调整减少额（第21行） |
| exempt_income_deduction_total | NUMERIC | 减：免税减计收入及加计扣除（第22行） |
| add_foreign_tax_offset | NUMERIC | 加：境外应税所得抵减境内亏损（第23行） |
| adjusted_taxable_income | NUMERIC | 纳税调整后所得（第24行） |
| less_income_exemption | NUMERIC | 减：所得减免（第25行） |
| less_losses_carried_forward | NUMERIC | 减：弥补以前年度亏损（第26行） |
| less_taxable_income_deduction | NUMERIC | 减：抵扣应纳税所得额（第27行） |
| taxable_income | NUMERIC | 应纳税所得额（第28行） |
| tax_rate | NUMERIC | 税率（第29行） |
| tax_payable | NUMERIC | 应纳所得税额（第30行） |
| tax_credit_total | NUMERIC | 减：减免所得税额（第31行） |
| less_foreign_tax_credit | NUMERIC | 减：抵免所得税额（第32行） |
| tax_due | NUMERIC | 应纳税额（第33行） |
| add_foreign_tax_due | NUMERIC | 加：境外所得应纳所得税额（第34行） |
| less_foreign_tax_credit_amount | NUMERIC | 减：境外所得抵免所得税额（第35行） |
| actual_tax_payable | NUMERIC | 实际应纳所得税额（第36行） |
| less_prepaid_tax | NUMERIC | 减：本年累计预缴所得税额（第37行） |
| tax_payable_or_refund | NUMERIC | 本年应补退所得税额（第38行） |
| hq_share | NUMERIC | 总机构分摊应补退（第39行） |
| fiscal_central_share | NUMERIC | 财政集中分配应补退（第40行） |
| hq_dept_share | NUMERIC | 总机构主体部门分摊应补退（第41行） |
| less_ethnic_autonomous_relief | NUMERIC | 减：民族自治地区地方分享（第42行） |
| less_audit_adjustment | NUMERIC | 减：稽查查补退所得税额（第43行） |
| less_special_adjustment | NUMERIC | 减：特别纳税调整补退（第44行） |
| final_tax_payable_or_refund | NUMERIC | 本年实际应补退所得税额（第45行） |

### 3.4 eit_annual_shareholder（年度股东明细）

PK: `id (AUTOINCREMENT)` | UNIQUE: `(filing_id, shareholder_name, id_number)`

| 列名 | 类型 | 说明 |
|------|------|------|
| filing_id | TEXT | FK→eit_annual_filing |
| shareholder_name | TEXT | 股东名称 |
| id_type | TEXT | 证件类型 |
| id_number | TEXT | 证件号码 |
| investment_ratio | NUMERIC | 投资比例 |
| dividend_amount | NUMERIC | 分配金额 |
| nationality_or_address | TEXT | 国籍/地址 |
| is_remaining_total | BOOLEAN | 是否为"其余股东合计"行 |

### 3.5 eit_annual_incentive_items（年度优惠明细）

PK: `id` | UNIQUE: `(filing_id, section, line_number)`

| 列名 | 类型 | 说明 |
|------|------|------|
| filing_id | TEXT | FK→eit_annual_filing |
| section | TEXT | 所属附表 |
| line_number | TEXT | 行号 |
| incentive_name | TEXT | 优惠项目名称 |
| amount | NUMERIC | 金额 |

### 3.6 eit_quarter_filing（季度所得税申报主记录）

PK: `filing_id` | UNIQUE: `(taxpayer_id, period_year, period_quarter, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| filing_id | TEXT | PK |
| taxpayer_id | TEXT | FK→taxpayer_info |
| period_year | INTEGER | 年度 |
| period_quarter | INTEGER | 季度 |
| revision_no | INTEGER | 修订版本号 |
| *(其余字段同 eit_annual_filing)* | | |

### 3.7 eit_quarter_main（季度主表 A200000）

PK/FK: `filing_id → eit_quarter_filing`

| 列名 | 类型 | 说明 |
|------|------|------|
| employee_quarter_avg | INTEGER | 季度平均从业人数 |
| asset_quarter_avg | NUMERIC | 季度平均资产总额 |
| restricted_or_prohibited_industry | BOOLEAN | 是否限制/禁止行业 |
| small_micro_enterprise | BOOLEAN | 是否小型微利企业 |
| revenue | NUMERIC | 营业收入 |
| cost | NUMERIC | 营业成本 |
| total_profit | NUMERIC | 利润总额 |
| add_specific_business_taxable_income | NUMERIC | 加：特定业务计算的应纳税所得额 |
| less_non_taxable_income | NUMERIC | 减：不征税收入 |
| less_accelerated_depreciation | NUMERIC | 减：固定资产加速折旧调减额 |
| tax_free_income_deduction_total | NUMERIC | 免税减计收入及加计扣除 |
| income_exemption_total | NUMERIC | 所得减免 |
| less_losses_carried_forward | NUMERIC | 减：弥补以前年度亏损 |
| actual_profit | NUMERIC | 实际利润额 |
| tax_rate | NUMERIC | 税率 |
| tax_payable | NUMERIC | 应纳所得税额 |
| tax_credit_total | NUMERIC | 减：减免所得税额 |
| less_prepaid_tax_current_year | NUMERIC | 减：本年累计预缴 |
| less_specific_business_prepaid | NUMERIC | 减：特定业务预缴 |
| current_tax_payable_or_refund | NUMERIC | 本期应补退所得税额 |
| hq_share_total | NUMERIC | 总机构分摊合计 |
| hq_share | NUMERIC | 总机构分摊 |
| fiscal_central_share | NUMERIC | 财政集中分配 |
| hq_business_dept_share | NUMERIC | 总机构主体部门分摊 |
| branch_share_ratio | NUMERIC | 分支机构分摊比例 |
| branch_share_amount | NUMERIC | 分支机构分摊税额 |
| ethnic_autonomous_relief_amount | NUMERIC | 民族自治地区减免 |
| final_tax_payable_or_refund | NUMERIC | 本期实际应补退 |

### 3.8 eit_quarter_incentive_items（季度优惠明细）

结构同 `eit_annual_incentive_items`，FK→`eit_quarter_filing`

---

## 4. 科目余额表

### 4.1 account_master（科目字典）

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| account_code | TEXT | PK | 科目代码 |
| account_name | TEXT | NOT NULL | 科目名称 |
| level | INTEGER | | 科目级别 |
| category | TEXT | NOT NULL, CHECK | '资产'/'负债'/'权益'/'成本'/'损益' |
| balance_direction | TEXT | NOT NULL, CHECK | '借' / '贷' |
| is_gaap | INTEGER | DEFAULT 0 | 1=企业会计准则适用 |
| is_small | INTEGER | DEFAULT 0 | 1=小企业会计准则适用 |
| is_active | INTEGER | DEFAULT 1 | 是否启用 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### 4.2 account_balance（科目余额明细）

PK: `(taxpayer_id, period_year, period_month, account_code, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| account_code | TEXT | FK→account_master |
| revision_no | INTEGER | 修订版本号（≥0） |
| submitted_at / etl_batch_id / source_doc_id / source_unit / etl_confidence | | ETL元数据 |
| opening_balance | NUMERIC | 期初余额 |
| debit_amount | NUMERIC | 本期借方发生额 |
| credit_amount | NUMERIC | 本期贷方发生额 |
| closing_balance | NUMERIC | 期末余额 |

---

## 5. 财务报表

### 5.1 资产负债表

#### fs_balance_sheet_item_dict（资产负债表项目字典）

PK: `id` | UNIQUE: `(gaap_type, item_code)`

| 列名 | 类型 | 说明 |
|------|------|------|
| gaap_type | TEXT | 'ASBE'（企业会计准则）/ 'ASSE'（小企业会计准则） |
| item_code | TEXT | 项目代码 |
| item_name | TEXT | 项目名称 |
| line_number | INTEGER | 行号 |
| section | TEXT | 所属区域 |
| display_order | INTEGER | 显示顺序 |
| is_total | BOOLEAN | 是否合计行 |

ASBE 67项 / ASSE 53项（详见 `seed_data.py` 中完整列表）

#### fs_balance_sheet_item（资产负债表明细 - EAV纵表）

PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| gaap_type | TEXT | 'ASBE' / 'ASSE' |
| item_code | TEXT | 项目代码 |
| revision_no | INTEGER | 修订版本号 |
| beginning_balance | NUMERIC | 期初余额（年初数） |
| ending_balance | NUMERIC | 期末余额 |
| item_name | TEXT | 项目名称 |
| line_number | INTEGER | 行号 |
| section | TEXT | 所属区域 |

### 5.2 利润表

#### fs_income_statement_item_dict（利润表项目字典）

PK: `id` | UNIQUE: `(gaap_type, item_code)`

| 列名 | 类型 | 说明 |
|------|------|------|
| gaap_type | TEXT | 'CAS'（企业会计准则）/ 'SAS'（小企业会计准则） |
| item_code | TEXT | 项目代码 |
| item_name | TEXT | 项目名称 |
| line_number | INTEGER | 行号 |
| category | TEXT | 分类 |
| display_order | INTEGER | 显示顺序 |
| is_total | BOOLEAN | 是否合计行 |

CAS 42项 / SAS 32项

#### fs_income_statement_item（利润表明细 - EAV纵表）

PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| gaap_type | TEXT | 'CAS' / 'SAS' |
| item_code | TEXT | 项目代码 |
| revision_no | INTEGER | 修订版本号 |
| current_amount | NUMERIC | 本期金额 |
| cumulative_amount | NUMERIC | 本年累计金额 |
| item_name | TEXT | 项目名称 |
| line_number | INTEGER | 行号 |
| category | TEXT | 分类 |

### 5.3 现金流量表

#### fs_cash_flow_item_dict（现金流量表项目字典）

PK: `id` | UNIQUE: `(gaap_type, item_code)`

结构同 `fs_income_statement_item_dict`。CAS 35项 / SAS 22项。

#### fs_cash_flow_item（现金流量表明细 - EAV纵表）

PK: `(taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no)`

结构同 `fs_income_statement_item`（current_amount=本期金额, cumulative_amount=本年累计金额）。

---

## 6. 发票表

### 6.1 inv_spec_purchase（进项发票宽表）

PK: `(taxpayer_id, invoice_pk, line_no)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | 纳税人识别号 |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| invoice_format | TEXT | '数电' / '非数电' |
| invoice_pk | TEXT | 逻辑主键（数电票号码或发票号码） |
| line_no | INTEGER | 行号（多行明细，默认1） |
| invoice_code | TEXT | 发票代码 |
| invoice_number | TEXT | 发票号码 |
| digital_invoice_no | TEXT | 数电票号码 |
| seller_tax_id | TEXT | 销方纳税人识别号 |
| seller_name | TEXT | 销方名称 |
| buyer_tax_id | TEXT | 购方纳税人识别号（我方） |
| buyer_name | TEXT | 购方名称（我方） |
| invoice_date | TEXT | 开票日期 |
| tax_category_code | TEXT | 税收分类编码 |
| special_business_type | TEXT | 特殊业务类型 |
| **商品明细（进项独有）** | | |
| goods_name | TEXT | 货物或应税劳务名称 |
| specification | TEXT | 规格型号 |
| unit | TEXT | 单位 |
| quantity | REAL | 数量 |
| unit_price | REAL | 单价 |
| amount | REAL | 金额 |
| tax_rate | TEXT | 税率 |
| tax_amount | REAL | 税额 |
| total_amount | REAL | 价税合计 |
| **状态字段** | | |
| invoice_source | TEXT | 发票来源 |
| invoice_type | TEXT | 发票类型 |
| invoice_status | TEXT | 发票状态 |
| is_positive | TEXT | 正负票标识 |
| risk_level | TEXT | 风险等级 |
| issuer | TEXT | 开票人 |
| remark | TEXT | 备注 |

### 6.2 inv_spec_sales（销项发票宽表）

PK: `(taxpayer_id, invoice_pk, line_no)`

结构同 `inv_spec_purchase`，但**无商品明细8列**（goods_name, specification, unit, quantity, unit_price, tax_rate, tax_category_code, special_business_type）。seller_tax_id/seller_name 为我方。

---

## 7. 财务指标表

### 7.1 financial_metrics（预计算财务指标 - 旧表）

PK: `(taxpayer_id, period_year, period_month, metric_code)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | FK→taxpayer_info |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| metric_category | TEXT | 指标分类（9类） |
| metric_code | TEXT | 指标代码 |
| metric_name | TEXT | 指标名称 |
| metric_value | NUMERIC | 指标值 |
| metric_unit | TEXT | 单位 |
| evaluation_level | TEXT | 评价等级 |
| calculated_at | TIMESTAMP | 计算时间 |

指标分类（9类）：盈利能力、偿债能力、营运能力、成长能力、现金流、税负率类、增值税重点指标、所得税重点指标、风险预警类

### 7.2 financial_metrics_item_dict（指标字典）

PK: `metric_code`

| 列名 | 类型 | 说明 |
|------|------|------|
| metric_code | TEXT | PK，指标代码 |
| metric_name | TEXT | 指标名称 |
| metric_category | TEXT | 指标分类 |
| metric_unit | TEXT | 单位 |
| formula_desc | TEXT | 公式描述 |
| source_domains | TEXT | 数据来源域（逗号分隔） |
| period_types | TEXT | 'monthly' / 'yearly' / 'both' |
| eval_rules | TEXT | 评价规则（JSON） |
| eval_ascending | INTEGER | 1=越高越好，0=越低越好 |
| display_order | INTEGER | 显示顺序 |
| is_active | INTEGER | 是否启用 |

### 7.3 financial_metrics_item（带期间类型的指标明细）

PK: `(taxpayer_id, period_year, period_month, period_type, metric_code)`

| 列名 | 类型 | 说明 |
|------|------|------|
| taxpayer_id | TEXT | FK→taxpayer_info |
| period_year | INTEGER | 年度 |
| period_month | INTEGER | 月份 |
| period_type | TEXT | 'monthly' / 'yearly' |
| metric_code | TEXT | FK→financial_metrics_item_dict |
| metric_name | TEXT | 指标名称 |
| metric_category | TEXT | 指标分类 |
| metric_value | NUMERIC | 指标值 |
| metric_unit | TEXT | 单位 |
| evaluation_level | TEXT | 评价等级 |
| calculated_at | TIMESTAMP | 计算时间 |

---

## 8. 跨域指标注册表

### 8.1 metric_registry（指标注册）

PK: `metric_key`

| 列名 | 类型 | 说明 |
|------|------|------|
| metric_key | TEXT | PK，指标键 |
| metric_name | TEXT | 指标名称 |
| description | TEXT | 描述 |
| unit | TEXT | 单位（默认'元'） |
| value_type | TEXT | 值类型（默认'NUMERIC'） |
| domain | TEXT | 所属域 |
| allow_cross_type | INTEGER | 1=允许跨纳税人类型比较 |
| allow_cross_domain | INTEGER | 1=允许跨域计算 |

### 8.2 metric_definition（指标定义 - 数据源映射）

PK: `id`

| 列名 | 类型 | 说明 |
|------|------|------|
| metric_key | TEXT | FK→metric_registry |
| taxpayer_type | TEXT | 纳税人类型（NULL=全部） |
| source_domain | TEXT | 来源域 |
| source_view | TEXT | 来源视图 |
| dim_item_type | TEXT | 维度：项目类型 |
| dim_time_range | TEXT | 维度：时间范围 |
| value_expr | TEXT | 取值表达式或列名 |
| agg_func | TEXT | 聚合函数（默认'SUM'） |
| revision_strategy | TEXT | 版本策略（默认'latest'） |
| normalized_metric_name | TEXT | 标准化指标名 |
| priority | INTEGER | 优先级 |
| is_active | INTEGER | 是否启用 |

### 8.3 metric_synonyms（指标同义词）

| 列名 | 类型 | 说明 |
|------|------|------|
| phrase | TEXT | 自然语言短语 |
| metric_key | TEXT | FK→metric_registry |
| priority | INTEGER | 优先级 |

---

## 9. 同义词映射表

所有同义词表用于 NL2SQL 管线中的自然语言→字段名映射。

| 表名 | 作用域 | 特殊字段 |
|------|--------|----------|
| vat_synonyms | 增值税 | scope_view, taxpayer_type |
| eit_synonyms | 企业所得税 | scope_view, taxpayer_type |
| account_synonyms | 科目余额 | account_code, account_name, applicable_standards |
| fs_balance_sheet_synonyms | 资产负债表 | gaap_type |
| fs_income_statement_synonyms | 利润表 | gaap_type |
| fs_cash_flow_synonyms | 现金流量表 | gaap_type |
| inv_synonyms | 发票 | scope_view |
| financial_metrics_synonyms | 财务指标 | — |
| metric_synonyms | 跨域指标 | metric_key |

通用结构：`(id, phrase, column_name/metric_key, priority, [scope字段])`

---

## 10. 字段映射表

| 表名 | 说明 |
|------|------|
| vat_general_column_mapping | 一般纳税人VAT行号→字段名→中文名 |
| vat_small_column_mapping | 小规模纳税人VAT行号→字段名→中文名 |
| eit_annual_main_column_mapping | 年度所得税行号→字段名→中文名 |
| eit_quarter_main_column_mapping | 季度所得税行号→字段名→中文名 |
| account_balance_column_mapping | 科目余额源列→目标字段→描述 |
| inv_column_mapping | 发票中文列名→英文字段名→表名→描述 |

---

## 11. 日志与审计表

### 11.1 user_query_log（用户查询日志）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | PK (AUTOINCREMENT) |
| session_id | TEXT | 会话ID |
| user_query | TEXT | 用户原始查询 |
| normalized_query | TEXT | 标准化查询 |
| taxpayer_id / taxpayer_name | TEXT | 纳税人信息 |
| period_year / period_month | INTEGER | 查询期间 |
| domain | TEXT | 识别的域 |
| success | INTEGER | 是否成功 |
| error_message | TEXT | 错误信息 |
| generated_sql | TEXT | 生成的SQL |
| execution_time_ms | INTEGER | 执行耗时(ms) |
| created_at | TIMESTAMP | 创建时间 |
| user_ip / user_agent | TEXT | 客户端信息 |

### 11.2 unmatched_phrases（未匹配短语追踪）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | PK |
| phrase | TEXT | 未匹配的短语 |
| context_query | TEXT | 上下文查询 |
| frequency | INTEGER | 出现频次 |
| first_seen / last_seen | TIMESTAMP | 首次/最近出现时间 |
| status | TEXT | 'pending' / 'processed' / 'ignored' |
| suggested_column | TEXT | 建议映射的列 |
| suggested_priority | INTEGER | 建议优先级 |
| remarks | TEXT | 备注 |
| processed_by / processed_at | TEXT/TIMESTAMP | 处理人/处理时间 |

### 11.3 etl_error_log（ETL错误日志）

| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | PK |
| etl_batch_id | TEXT | ETL批次ID |
| source_doc_id | TEXT | 来源文档ID |
| taxpayer_id | TEXT | 纳税人ID |
| period_year / period_month | INTEGER | 期间 |
| table_name | TEXT | 目标表名 |
| error_type | TEXT | 错误类型 |
| error_message | TEXT | 错误信息 |
| created_at | TIMESTAMP | 创建时间 |

---

## 12. 视图

### 12.1 增值税视图

| 视图名 | 基表 | 说明 |
|--------|------|------|
| vw_vat_return_general | vat_return_general JOIN taxpayer_info | 一般纳税人增值税申报（含纳税人维度） |
| vw_vat_return_small | vat_return_small JOIN taxpayer_info | 小规模纳税人增值税申报（含纳税人维度） |

### 12.2 企业所得税视图

| 视图名 | 基表 | 说明 |
|--------|------|------|
| vw_eit_annual_main | eit_annual_filing + eit_annual_main + taxpayer_info | 年度所得税主表 |
| vw_eit_quarter_main | eit_quarter_filing + eit_quarter_main + taxpayer_info | 季度所得税主表 |

### 12.3 科目余额视图

| 视图名 | 基表 | 说明 |
|--------|------|------|
| vw_account_balance | account_balance + taxpayer_info + account_master | 科目余额（按会计准则过滤科目） |

### 12.4 资产负债表视图（EAV→宽表 Pivot）

| 视图名 | gaap_type | 项目数 | 说明 |
|--------|-----------|--------|------|
| vw_balance_sheet_eas | ASBE | 67×2=134列 | 企业会计准则资产负债表（{item_code}_begin + {item_code}_end） |
| vw_balance_sheet_sas | ASSE | 53×2=106列 | 小企业会计准则资产负债表 |

Pivot 方式：`MAX(CASE WHEN item_code='XXX' THEN beginning_balance END) AS XXX_begin`

### 12.5 利润表视图（EAV→宽表 Pivot + CROSS JOIN time_range）

| 视图名 | gaap_type | 项目数 | 说明 |
|--------|-----------|--------|------|
| vw_profit_eas | CAS | 42列 | 企业会计准则利润表 |
| vw_profit_sas | SAS | 32列 | 小企业会计准则利润表 |

含 `CROSS JOIN (VALUES ('本期'), ('本年累计')) AS tr(time_range)` 维度展开。

### 12.6 现金流量表视图（EAV→宽表 Pivot + CROSS JOIN time_range）

| 视图名 | gaap_type | 项目数 | 说明 |
|--------|-----------|--------|------|
| vw_cash_flow_eas | CAS | 35列 | 企业会计准则现金流量表 |
| vw_cash_flow_sas | SAS | 22列 | 小企业会计准则现金流量表 |

额外过滤：`accounting_standard = '企业会计准则'/'小企业会计准则'`

### 12.7 发票视图

| 视图名 | 基表 | 说明 |
|--------|------|------|
| vw_inv_spec_purchase | inv_spec_purchase + taxpayer_info | 进项发票（含纳税人维度） |
| vw_inv_spec_sales | inv_spec_sales + taxpayer_info | 销项发票（含纳税人维度） |

### 12.8 财务指标视图

| 视图名 | 基表 | 说明 |
|--------|------|------|
| vw_financial_metrics | financial_metrics_item + taxpayer_info | 财务指标（含纳税人维度、期间类型） |

### 12.9 占位视图

| 视图名 | 说明 |
|--------|------|
| vw_enterprise_profile | 企业画像（空桩，待实现） |

---

## 13. 索引

### 核心业务索引

| 索引名 | 表 | 列 | 用途 |
|--------|----|----|------|
| idx_general_taxpayer_period_revision | vat_return_general | (taxpayer_id, period_year, period_month, revision_no DESC) | 最新版本查询 |
| idx_small_taxpayer_period_revision | vat_return_small | (taxpayer_id, period_year, period_month, revision_no DESC) | 最新版本查询 |
| idx_general_dimensions | vat_return_general | (taxpayer_id, period_year, period_month, item_type, time_range) | 常用过滤组合 |
| idx_small_dimensions | vat_return_small | (taxpayer_id, period_year, period_month, item_type, time_range) | 常用过滤组合 |
| idx_eit_annual_filing_taxpayer_period | eit_annual_filing | (taxpayer_id, period_year, revision_no DESC) | 最新年度申报 |
| idx_eit_quarter_filing_taxpayer_period | eit_quarter_filing | (taxpayer_id, period_year, period_quarter, revision_no DESC) | 最新季度申报 |
| idx_balance_taxpayer_period_revision | account_balance | (taxpayer_id, period_year, period_month, revision_no DESC) | 最新科目余额 |
| idx_bs_taxpayer_period_gaap | fs_balance_sheet_item | (taxpayer_id, period_year, period_month, gaap_type, revision_no DESC) | 最新资产负债表 |

### 同义词索引

所有同义词表均有 `idx_*_phrase(phrase)` 索引，部分有 `idx_*_scope/gaap` 复合索引。

### 日志索引

| 索引名 | 表 | 列 |
|--------|----|----|
| idx_query_log_created | user_query_log | (created_at) |
| idx_query_log_success | user_query_log | (success) |
| idx_query_log_taxpayer_period | user_query_log | (taxpayer_id, created_at DESC) |
| idx_unmatched_phrase | unmatched_phrases | (phrase) |
| idx_unmatched_status | unmatched_phrases | (status) |
| idx_etl_error_batch | etl_error_log | (etl_batch_id) |

---

## 14. 设计模式总结

### 14.1 EAV 纵表 + 宽表视图 Pivot

资产负债表、利润表、现金流量表均采用 EAV（Entity-Attribute-Value）纵表存储，通过 `MAX(CASE WHEN)` 聚合在视图层 Pivot 为宽表。优势：灵活扩展项目、支持双准则。

### 14.2 修订版本管理

所有事实表包含 `revision_no` 字段，通过 `ROW_NUMBER() OVER (... ORDER BY revision_no DESC)` 窗口函数取最新版本。

### 14.3 双准则支持

| 域 | 企业会计准则 | 小企业会计准则 |
|----|-------------|---------------|
| 资产负债表 | ASBE → vw_balance_sheet_eas | ASSE → vw_balance_sheet_sas |
| 利润表 | CAS → vw_profit_eas | SAS → vw_profit_sas |
| 现金流量表 | CAS → vw_cash_flow_eas | SAS → vw_cash_flow_sas |
| 增值税 | 一般纳税人 → vw_vat_return_general | 小规模纳税人 → vw_vat_return_small |

路由依据：`taxpayer_info.accounting_standard` 或 `taxpayer_type`

### 14.4 存储-查询解耦

NL2SQL 管线只访问视图（`vw_*`），不直接查询明细表。视图负责 JOIN 维度表、Pivot 宽表、过滤准则。

### 14.5 同义词三层容错

1. 同义词表精确匹配（最长匹配优先）
2. 字段映射表回退
3. LLM 语义理解兜底

### 14.6 复合主键模式

| 域 | 主键 |
|----|------|
| VAT | (taxpayer_id, period_year, period_month, item_type, time_range, revision_no) |
| EIT年度 | (taxpayer_id, period_year, revision_no) via filing_id |
| EIT季度 | (taxpayer_id, period_year, period_quarter, revision_no) via filing_id |
| 财务报表 | (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no) |
| 科目余额 | (taxpayer_id, period_year, period_month, account_code, revision_no) |
| 发票 | (taxpayer_id, invoice_pk, line_no) |

### 14.7 白名单安全机制

`schema_catalog.py` 定义 `DOMAIN_VIEWS`（域→允许视图）和 `VIEW_COLUMNS`（视图→允许列），SQL 审计器在执行前强制校验。
