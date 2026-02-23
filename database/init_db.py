"""数据库初始化：全部DDL（表、视图、索引）"""
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def get_ddl_statements():
    """返回全部DDL语句列表"""
    return [
        # ============================================================
        # 1. 字典表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS dim_industry (
            industry_code TEXT PRIMARY KEY,
            industry_name TEXT NOT NULL,
            parent_code   TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS dim_tax_authority (
            tax_authority_code TEXT PRIMARY KEY,
            tax_authority_name TEXT NOT NULL,
            region_code        TEXT,
            level              TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS dim_region (
            region_code TEXT PRIMARY KEY,
            region_name TEXT NOT NULL,
            parent_code TEXT
        )""",

        # ============================================================
        # 2. 纳税人主维表 + 快照表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS taxpayer_info (
            taxpayer_id           TEXT PRIMARY KEY,
            taxpayer_name         TEXT NOT NULL,
            taxpayer_type         TEXT NOT NULL,
            registration_type     TEXT,
            legal_representative  TEXT,
            establish_date        DATE,
            industry_code         TEXT,
            industry_name         TEXT,
            tax_authority_code    TEXT,
            tax_authority_name    TEXT,
            tax_bureau_level      TEXT,
            region_code           TEXT,
            region_name           TEXT,
            credit_grade_current  TEXT,
            credit_grade_year     INTEGER,
            accounting_standard   TEXT,
            status                TEXT DEFAULT 'active',
            updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_name ON taxpayer_info(taxpayer_name)",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_industry ON taxpayer_info(industry_code)",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_region ON taxpayer_info(region_code)",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_authority ON taxpayer_info(tax_authority_code)",

        """CREATE TABLE IF NOT EXISTS taxpayer_profile_snapshot_month (
            taxpayer_id        TEXT NOT NULL,
            period_year        INTEGER NOT NULL,
            period_month       INTEGER NOT NULL,
            industry_code      TEXT,
            tax_authority_code TEXT,
            region_code        TEXT,
            credit_grade       TEXT,
            employee_scale     TEXT,
            revenue_scale      TEXT,
            source_doc_id      TEXT,
            etl_batch_id       TEXT,
            updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (taxpayer_id, period_year, period_month),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_snap_month_industry ON taxpayer_profile_snapshot_month(period_year, period_month, industry_code)",
        "CREATE INDEX IF NOT EXISTS idx_snap_month_credit ON taxpayer_profile_snapshot_month(period_year, period_month, credit_grade)",

        """CREATE TABLE IF NOT EXISTS taxpayer_credit_grade_year (
            taxpayer_id    TEXT NOT NULL,
            year           INTEGER NOT NULL,
            credit_grade   TEXT NOT NULL,
            published_at   DATE,
            source_doc_id  TEXT,
            etl_batch_id   TEXT,
            PRIMARY KEY (taxpayer_id, year),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_credit_year_grade ON taxpayer_credit_grade_year(year, credit_grade)",

        # ============================================================
        # 3. 增值税明细表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS vat_return_general (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            item_type           TEXT NOT NULL,
            time_range          TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            sales_taxable_rate            NUMERIC,
            sales_goods                  NUMERIC,
            sales_services               NUMERIC,
            sales_adjustment_check       NUMERIC,
            sales_simple_method          NUMERIC,
            sales_simple_adjust_check    NUMERIC,
            sales_export_credit_refund   NUMERIC,
            sales_tax_free               NUMERIC,
            sales_tax_free_goods         NUMERIC,
            sales_tax_free_services      NUMERIC,
            output_tax                   NUMERIC,
            input_tax                    NUMERIC,
            last_period_credit           NUMERIC,
            transfer_out                 NUMERIC,
            export_refund                NUMERIC,
            tax_check_supplement         NUMERIC,
            deductible_total             NUMERIC,
            actual_deduct                NUMERIC,
            tax_payable                  NUMERIC,
            end_credit                   NUMERIC,
            simple_tax                   NUMERIC,
            simple_tax_check_supplement  NUMERIC,
            tax_reduction                NUMERIC,
            total_tax_payable            NUMERIC,
            unpaid_begin                 NUMERIC,
            export_receipt_tax           NUMERIC,
            paid_current                 NUMERIC,
            prepaid_installment          NUMERIC,
            prepaid_export_receipt       NUMERIC,
            paid_last_period             NUMERIC,
            paid_arrears                 NUMERIC,
            unpaid_end                   NUMERIC,
            arrears                      NUMERIC,
            supplement_refund            NUMERIC,
            immediate_refund             NUMERIC,
            unpaid_check_begin           NUMERIC,
            paid_check_current           NUMERIC,
            unpaid_check_end             NUMERIC,
            city_maintenance_tax         NUMERIC,
            education_surcharge          NUMERIC,
            local_education_surcharge    NUMERIC,
            PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no),
            CHECK (item_type IN ('一般项目', '即征即退项目')),
            CHECK (time_range IN ('本月', '累计')),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_vat_period ON vat_return_general(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_vat_taxpayer ON vat_return_general(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_general_taxpayer_period ON vat_return_general(taxpayer_id, period_year, period_month)",

        """CREATE TABLE IF NOT EXISTS vat_return_small (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            item_type           TEXT NOT NULL,
            time_range          TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            sales_3percent              NUMERIC,
            sales_3percent_invoice_spec NUMERIC,
            sales_3percent_invoice_other NUMERIC,
            sales_5percent              NUMERIC,
            sales_5percent_invoice_spec NUMERIC,
            sales_5percent_invoice_other NUMERIC,
            sales_used_assets           NUMERIC,
            sales_used_assets_invoice_other NUMERIC,
            sales_tax_free             NUMERIC,
            sales_tax_free_micro       NUMERIC,
            sales_tax_free_threshold   NUMERIC,
            sales_tax_free_other       NUMERIC,
            sales_export_tax_free      NUMERIC,
            sales_export_tax_free_invoice_other NUMERIC,
            tax_due_current            NUMERIC,
            tax_due_reduction          NUMERIC,
            tax_free_amount            NUMERIC,
            tax_free_micro             NUMERIC,
            tax_free_threshold         NUMERIC,
            tax_due_total              NUMERIC,
            tax_prepaid                NUMERIC,
            tax_supplement_refund      NUMERIC,
            city_maintenance_tax       NUMERIC,
            education_surcharge        NUMERIC,
            local_education_surcharge  NUMERIC,
            PRIMARY KEY (taxpayer_id, period_year, period_month, item_type, time_range, revision_no),
            CHECK (item_type IN ('货物及劳务', '服务不动产无形资产')),
            CHECK (time_range IN ('本期', '累计')),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_small_period ON vat_return_small(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_small_taxpayer ON vat_return_small(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_small_taxpayer_period ON vat_return_small(taxpayer_id, period_year, period_month)",

        # ============================================================
        # 4. ETL 栏次映射表（VAT）
        # ============================================================
        """CREATE TABLE IF NOT EXISTS vat_general_column_mapping (
            line_number   INTEGER PRIMARY KEY,
            column_name   TEXT NOT NULL,
            business_name TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS vat_small_column_mapping (
            line_number   INTEGER PRIMARY KEY,
            column_name   TEXT NOT NULL,
            business_name TEXT
        )""",

        # ============================================================
        # 4b. 企业所得税物理表
        # ============================================================
        # --- 年度申报主记录表（封面信息）---
        """CREATE TABLE IF NOT EXISTS eit_annual_filing (
            filing_id           TEXT PRIMARY KEY,
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            amount_unit         TEXT DEFAULT '元',
            preparer            TEXT,
            preparer_id         TEXT,
            agent_organization  TEXT,
            agent_credit_code   TEXT,
            taxpayer_sign_date  DATE,
            accepted_by         TEXT,
            accepting_tax_office TEXT,
            date_accepted       DATE,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            etl_confidence      REAL,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (taxpayer_id, period_year, revision_no),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_annual_filing_taxpayer ON eit_annual_filing(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_eit_annual_filing_period ON eit_annual_filing(period_year)",

        # --- 年度基础信息表（EIT-A000000）---
        """CREATE TABLE IF NOT EXISTS eit_annual_basic_info (
            filing_id           TEXT PRIMARY KEY REFERENCES eit_annual_filing(filing_id),
            tax_return_type_code        TEXT,
            branch_tax_payment_ratio    NUMERIC,
            asset_avg                   NUMERIC,
            employee_avg                INTEGER,
            industry_code               TEXT,
            restricted_or_prohibited    BOOLEAN,
            accounting_standard_code    TEXT,
            use_general_fs_2019         BOOLEAN,
            small_micro_enterprise      BOOLEAN,
            listed_company              TEXT,
            equity_investment_business   BOOLEAN,
            overseas_related_transaction BOOLEAN,
            foreign_tax_credit_method    TEXT,
            hainan_ftz_foreign_invest    BOOLEAN,
            hainan_ftz_industry_category TEXT,
            venture_investment_partner   BOOLEAN,
            venture_investment_enterprise BOOLEAN,
            tas_enterprise_type          TEXT,
            non_profit_org               BOOLEAN,
            software_ic_enterprise_type  TEXT,
            ic_project_type              TEXT,
            tech_sme_reg_no1             TEXT,
            tech_sme_reg_date1           DATE,
            tech_sme_reg_no2             TEXT,
            tech_sme_reg_date2           DATE,
            hi_tech_cert_no1             TEXT,
            hi_tech_cert_date1           DATE,
            hi_tech_cert_no2             TEXT,
            hi_tech_cert_date2           DATE,
            reorganization_tax_treatment TEXT,
            reorganization_type_code     TEXT,
            reorganization_party_type    TEXT,
            relocation_start_date        DATE,
            relocation_no_income_year    BOOLEAN,
            relocation_loss_deduction_year INTEGER,
            nonmonetary_asset_invest     BOOLEAN,
            nonmonetary_asset_defer_year INTEGER,
            tech_achievement_invest      BOOLEAN,
            tech_achievement_defer_year  INTEGER,
            asset_transfer_special_treatment BOOLEAN,
            debt_restructuring_defer_year INTEGER,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # --- 年度股东分红明细表 ---
        """CREATE TABLE IF NOT EXISTS eit_annual_shareholder (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            filing_id           TEXT NOT NULL REFERENCES eit_annual_filing(filing_id),
            shareholder_name    TEXT NOT NULL,
            id_type             TEXT,
            id_number           TEXT,
            investment_ratio    NUMERIC,
            dividend_amount     NUMERIC,
            nationality_or_address TEXT,
            is_remaining_total  BOOLEAN DEFAULT 0,
            UNIQUE (filing_id, shareholder_name, id_number)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_annual_shareholder_filing ON eit_annual_shareholder(filing_id)",

        # --- 年度主表（EIT-A100000）---
        """CREATE TABLE IF NOT EXISTS eit_annual_main (
            filing_id           TEXT PRIMARY KEY REFERENCES eit_annual_filing(filing_id),
            revenue                     NUMERIC,
            cost                        NUMERIC,
            taxes_surcharges            NUMERIC,
            selling_expenses            NUMERIC,
            admin_expenses              NUMERIC,
            rd_expenses                 NUMERIC,
            financial_expenses          NUMERIC,
            other_gains                 NUMERIC,
            investment_income           NUMERIC,
            net_exposure_hedge_gains    NUMERIC,
            fair_value_change_gains     NUMERIC,
            credit_impairment_loss      NUMERIC,
            asset_impairment_loss       NUMERIC,
            asset_disposal_gains        NUMERIC,
            operating_profit            NUMERIC,
            non_operating_income        NUMERIC,
            non_operating_expenses      NUMERIC,
            total_profit                NUMERIC,
            less_foreign_income         NUMERIC,
            add_tax_adjust_increase     NUMERIC,
            less_tax_adjust_decrease    NUMERIC,
            exempt_income_deduction_total NUMERIC,
            add_foreign_tax_offset      NUMERIC,
            adjusted_taxable_income     NUMERIC,
            less_income_exemption       NUMERIC,
            less_losses_carried_forward NUMERIC,
            less_taxable_income_deduction NUMERIC,
            taxable_income              NUMERIC,
            tax_rate                    NUMERIC,
            tax_payable                 NUMERIC,
            tax_credit_total            NUMERIC,
            less_foreign_tax_credit     NUMERIC,
            tax_due                     NUMERIC,
            add_foreign_tax_due         NUMERIC,
            less_foreign_tax_credit_amount NUMERIC,
            actual_tax_payable          NUMERIC,
            less_prepaid_tax            NUMERIC,
            tax_payable_or_refund       NUMERIC,
            hq_share                    NUMERIC,
            fiscal_central_share        NUMERIC,
            hq_dept_share               NUMERIC,
            less_ethnic_autonomous_relief NUMERIC,
            less_audit_adjustment       NUMERIC,
            less_special_adjustment     NUMERIC,
            final_tax_payable_or_refund NUMERIC,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # --- 年度优惠事项明细表（动态子行22.x、31.x）---
        """CREATE TABLE IF NOT EXISTS eit_annual_incentive_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            filing_id           TEXT NOT NULL REFERENCES eit_annual_filing(filing_id),
            section             TEXT NOT NULL,
            line_number         TEXT NOT NULL,
            incentive_name      TEXT NOT NULL,
            amount              NUMERIC,
            UNIQUE (filing_id, section, line_number)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_annual_incentive_filing ON eit_annual_incentive_items(filing_id)",

        # --- 季度申报主记录表 ---
        """CREATE TABLE IF NOT EXISTS eit_quarter_filing (
            filing_id           TEXT PRIMARY KEY,
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_quarter      INTEGER NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            amount_unit         TEXT DEFAULT '元',
            preparer            TEXT,
            preparer_id         TEXT,
            agent_organization  TEXT,
            agent_credit_code   TEXT,
            taxpayer_sign_date  DATE,
            accepted_by         TEXT,
            accepting_tax_office TEXT,
            date_accepted       DATE,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            etl_confidence      REAL,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (taxpayer_id, period_year, period_quarter, revision_no),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_quarter_filing_taxpayer ON eit_quarter_filing(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_eit_quarter_filing_period ON eit_quarter_filing(period_year, period_quarter)",

        # --- 季度主表（EIT-A200000）---
        """CREATE TABLE IF NOT EXISTS eit_quarter_main (
            filing_id           TEXT PRIMARY KEY REFERENCES eit_quarter_filing(filing_id),
            employee_quarter_avg INTEGER,
            asset_quarter_avg   NUMERIC,
            restricted_or_prohibited_industry BOOLEAN,
            small_micro_enterprise           BOOLEAN,
            revenue                         NUMERIC,
            cost                            NUMERIC,
            total_profit                    NUMERIC,
            add_specific_business_taxable_income NUMERIC,
            less_non_taxable_income         NUMERIC,
            less_accelerated_depreciation   NUMERIC,
            tax_free_income_deduction_total NUMERIC,
            income_exemption_total          NUMERIC,
            less_losses_carried_forward     NUMERIC,
            actual_profit                   NUMERIC,
            tax_rate                        NUMERIC,
            tax_payable                     NUMERIC,
            tax_credit_total                NUMERIC,
            less_prepaid_tax_current_year   NUMERIC,
            less_specific_business_prepaid  NUMERIC,
            current_tax_payable_or_refund   NUMERIC,
            hq_share_total                  NUMERIC,
            hq_share                        NUMERIC,
            fiscal_central_share            NUMERIC,
            hq_business_dept_share          NUMERIC,
            branch_share_ratio              NUMERIC,
            branch_share_amount             NUMERIC,
            ethnic_autonomous_relief_amount NUMERIC,
            final_tax_payable_or_refund     NUMERIC,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # --- 季度优惠事项明细表（动态子行7.x、8.x、13.x）---
        """CREATE TABLE IF NOT EXISTS eit_quarter_incentive_items (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            filing_id           TEXT NOT NULL REFERENCES eit_quarter_filing(filing_id),
            section             TEXT NOT NULL,
            line_number         TEXT NOT NULL,
            incentive_name      TEXT NOT NULL,
            amount              NUMERIC,
            UNIQUE (filing_id, section, line_number)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_quarter_incentive_filing ON eit_quarter_incentive_items(filing_id)",

        # --- EIT 栏次映射表 ---
        """CREATE TABLE IF NOT EXISTS eit_annual_main_column_mapping (
            line_number   INTEGER PRIMARY KEY,
            column_name   TEXT NOT NULL,
            business_name TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS eit_quarter_main_column_mapping (
            line_number   INTEGER PRIMARY KEY,
            column_name   TEXT NOT NULL,
            business_name TEXT
        )""",

        # --- EIT 同义词表 ---
        """CREATE TABLE IF NOT EXISTS eit_synonyms (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase        TEXT NOT NULL,
            column_name   TEXT NOT NULL,
            priority      INTEGER DEFAULT 1,
            scope_view    TEXT,
            taxpayer_type TEXT,
            UNIQUE(phrase, column_name, scope_view)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_eit_synonyms_phrase ON eit_synonyms(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_eit_synonyms_scope ON eit_synonyms(scope_view, priority)",

        # ============================================================
        # 4c. 科目余额表
        # ============================================================
        # --- 科目字典表 ---
        """CREATE TABLE IF NOT EXISTS account_master (
            account_code        TEXT PRIMARY KEY,
            account_name        TEXT NOT NULL,
            level               INTEGER,
            category            TEXT NOT NULL,
            balance_direction   TEXT NOT NULL,
            is_gaap             INTEGER DEFAULT 0,
            is_small            INTEGER DEFAULT 0,
            is_active           INTEGER DEFAULT 1,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (balance_direction IN ('借', '贷')),
            CHECK (category IN ('资产','负债','权益','成本','损益'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_account_name ON account_master(account_name)",
        "CREATE INDEX IF NOT EXISTS idx_account_category ON account_master(category)",

        # --- 科目余额明细表 ---
        """CREATE TABLE IF NOT EXISTS account_balance (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            account_code        TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            opening_balance     NUMERIC,
            debit_amount        NUMERIC,
            credit_amount       NUMERIC,
            closing_balance     NUMERIC,
            PRIMARY KEY (taxpayer_id, period_year, period_month, account_code, revision_no),
            FOREIGN KEY (account_code) REFERENCES account_master(account_code),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_balance_period ON account_balance(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_balance_taxpayer ON account_balance(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_balance_taxpayer_period ON account_balance(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_balance_account ON account_balance(account_code)",
        "CREATE INDEX IF NOT EXISTS idx_balance_taxpayer_period_revision ON account_balance(taxpayer_id, period_year, period_month, revision_no DESC)",

        # --- ETL 列映射表 ---
        """CREATE TABLE IF NOT EXISTS account_balance_column_mapping (
            source_column   TEXT PRIMARY KEY,
            target_field    TEXT NOT NULL,
            description     TEXT
        )""",

        # --- 科目同义词表 ---
        """CREATE TABLE IF NOT EXISTS account_synonyms (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase          TEXT NOT NULL,
            account_code    TEXT,
            account_name    TEXT,
            priority        INTEGER DEFAULT 1,
            applicable_standards TEXT,
            UNIQUE(phrase, account_code, account_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_account_synonyms_phrase ON account_synonyms(phrase)",

        # ============================================================
        # 5. NL2SQL 同义词表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS vat_synonyms (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase        TEXT NOT NULL,
            column_name   TEXT NOT NULL,
            priority      INTEGER DEFAULT 1,
            taxpayer_type TEXT,
            scope_view    TEXT,
            UNIQUE(phrase, column_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_synonyms_phrase ON vat_synonyms(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_synonyms_scope ON vat_synonyms(scope_view, taxpayer_type, priority)",

        # ============================================================
        # 6. 指标注册表（跨域对齐）
        # ============================================================
        """CREATE TABLE IF NOT EXISTS metric_registry (
            metric_key         TEXT PRIMARY KEY,
            metric_name        TEXT NOT NULL,
            description        TEXT,
            unit               TEXT DEFAULT '元',
            value_type         TEXT DEFAULT 'NUMERIC',
            domain             TEXT,
            allow_cross_type   INTEGER DEFAULT 0,
            allow_cross_domain INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS metric_definition (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_key            TEXT NOT NULL,
            taxpayer_type         TEXT,
            source_domain         TEXT,
            source_view           TEXT,
            dim_item_type         TEXT,
            dim_time_range        TEXT,
            value_expr            TEXT NOT NULL,
            agg_func              TEXT DEFAULT 'SUM',
            revision_strategy     TEXT DEFAULT 'latest',
            normalized_metric_name TEXT,
            priority              INTEGER DEFAULT 1,
            is_active             INTEGER DEFAULT 1,
            FOREIGN KEY (metric_key) REFERENCES metric_registry(metric_key)
        )""",
        """CREATE TABLE IF NOT EXISTS metric_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            metric_key  TEXT NOT NULL,
            priority    INTEGER DEFAULT 1,
            FOREIGN KEY (metric_key) REFERENCES metric_registry(metric_key)
        )""",

        # ============================================================
        # 7. 日志表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS user_query_log (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id        TEXT,
            user_query        TEXT NOT NULL,
            normalized_query  TEXT,
            taxpayer_id       TEXT,
            taxpayer_name     TEXT,
            period_year       INTEGER,
            period_month      INTEGER,
            domain            TEXT,
            success           INTEGER DEFAULT 0,
            error_message     TEXT,
            generated_sql     TEXT,
            execution_time_ms INTEGER,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_ip           TEXT,
            user_agent        TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_query_log_created ON user_query_log(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_query_log_success ON user_query_log(success)",
        "CREATE INDEX IF NOT EXISTS idx_query_log_taxpayer ON user_query_log(taxpayer_id)",

        """CREATE TABLE IF NOT EXISTS unmatched_phrases (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase           TEXT NOT NULL,
            context_query    TEXT,
            frequency        INTEGER DEFAULT 1,
            first_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status           TEXT DEFAULT 'pending',
            suggested_column TEXT,
            suggested_priority INTEGER DEFAULT 2,
            remarks          TEXT,
            processed_by     TEXT,
            processed_at     TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_unmatched_phrase ON unmatched_phrases(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_unmatched_status ON unmatched_phrases(status)",

        """CREATE TABLE IF NOT EXISTS etl_error_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            etl_batch_id  TEXT,
            source_doc_id TEXT,
            taxpayer_id   TEXT,
            period_year   INTEGER,
            period_month  INTEGER,
            table_name    TEXT,
            error_type    TEXT,
            error_message TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_etl_error_batch ON etl_error_log(etl_batch_id)",

        # ============================================================
        # 8. VAT 查询视图
        # ============================================================
        """CREATE VIEW IF NOT EXISTS vw_vat_return_general AS
        SELECT
            g.taxpayer_id, t.taxpayer_name,
            g.period_year, g.period_month, g.item_type, g.time_range,
            t.taxpayer_type, g.revision_no, g.submitted_at,
            g.etl_batch_id, g.source_doc_id, g.source_unit, g.etl_confidence,
            g.sales_taxable_rate, g.sales_goods, g.sales_services,
            g.sales_adjustment_check, g.sales_simple_method,
            g.sales_simple_adjust_check, g.sales_export_credit_refund,
            g.sales_tax_free, g.sales_tax_free_goods, g.sales_tax_free_services,
            g.output_tax, g.input_tax, g.last_period_credit, g.transfer_out,
            g.export_refund, g.tax_check_supplement, g.deductible_total,
            g.actual_deduct, g.tax_payable, g.end_credit, g.simple_tax,
            g.simple_tax_check_supplement, g.tax_reduction, g.total_tax_payable,
            g.unpaid_begin, g.export_receipt_tax, g.paid_current,
            g.prepaid_installment, g.prepaid_export_receipt, g.paid_last_period,
            g.paid_arrears, g.unpaid_end, g.arrears, g.supplement_refund,
            g.immediate_refund, g.unpaid_check_begin, g.paid_check_current,
            g.unpaid_check_end, g.city_maintenance_tax, g.education_surcharge,
            g.local_education_surcharge
        FROM vat_return_general g
        JOIN taxpayer_info t ON g.taxpayer_id = t.taxpayer_id
        WHERE t.taxpayer_type = '一般纳税人'""",

        """CREATE VIEW IF NOT EXISTS vw_vat_return_small AS
        SELECT
            s.taxpayer_id, t.taxpayer_name,
            s.period_year, s.period_month, s.item_type, s.time_range,
            t.taxpayer_type, s.revision_no, s.submitted_at,
            s.etl_batch_id, s.source_doc_id, s.source_unit, s.etl_confidence,
            s.sales_3percent, s.sales_3percent_invoice_spec,
            s.sales_3percent_invoice_other, s.sales_5percent,
            s.sales_5percent_invoice_spec, s.sales_5percent_invoice_other,
            s.sales_used_assets, s.sales_used_assets_invoice_other,
            s.sales_tax_free, s.sales_tax_free_micro, s.sales_tax_free_threshold,
            s.sales_tax_free_other, s.sales_export_tax_free,
            s.sales_export_tax_free_invoice_other,
            s.tax_due_current, s.tax_due_reduction, s.tax_free_amount,
            s.tax_free_micro, s.tax_free_threshold, s.tax_due_total,
            s.tax_prepaid, s.tax_supplement_refund,
            s.city_maintenance_tax, s.education_surcharge,
            s.local_education_surcharge
        FROM vat_return_small s
        JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id
        WHERE t.taxpayer_type = '小规模纳税人'""",

        # ============================================================
        # 9. EIT 查询视图（年度 + 季度）
        # ============================================================
        """CREATE VIEW IF NOT EXISTS vw_eit_annual_main AS
        SELECT
            f.filing_id, f.taxpayer_id, t.taxpayer_name, t.taxpayer_type,
            f.period_year, f.revision_no,
            f.submitted_at, f.etl_batch_id, f.source_doc_id, f.etl_confidence,
            m.revenue, m.cost, m.taxes_surcharges,
            m.selling_expenses, m.admin_expenses, m.rd_expenses, m.financial_expenses,
            m.other_gains, m.investment_income, m.net_exposure_hedge_gains,
            m.fair_value_change_gains, m.credit_impairment_loss, m.asset_impairment_loss,
            m.asset_disposal_gains, m.operating_profit,
            m.non_operating_income, m.non_operating_expenses, m.total_profit,
            m.less_foreign_income, m.add_tax_adjust_increase, m.less_tax_adjust_decrease,
            m.exempt_income_deduction_total, m.add_foreign_tax_offset,
            m.adjusted_taxable_income, m.less_income_exemption,
            m.less_losses_carried_forward, m.less_taxable_income_deduction,
            m.taxable_income, m.tax_rate, m.tax_payable,
            m.tax_credit_total, m.less_foreign_tax_credit, m.tax_due,
            m.add_foreign_tax_due, m.less_foreign_tax_credit_amount,
            m.actual_tax_payable, m.less_prepaid_tax, m.tax_payable_or_refund,
            m.hq_share, m.fiscal_central_share, m.hq_dept_share,
            m.less_ethnic_autonomous_relief, m.less_audit_adjustment,
            m.less_special_adjustment, m.final_tax_payable_or_refund
        FROM eit_annual_filing f
        JOIN eit_annual_main m ON f.filing_id = m.filing_id
        JOIN taxpayer_info t ON f.taxpayer_id = t.taxpayer_id""",

        """CREATE VIEW IF NOT EXISTS vw_eit_quarter_main AS
        SELECT
            f.filing_id, f.taxpayer_id, t.taxpayer_name, t.taxpayer_type,
            f.period_year, f.period_quarter, f.revision_no,
            f.submitted_at, f.etl_batch_id, f.source_doc_id, f.etl_confidence,
            m.employee_quarter_avg, m.asset_quarter_avg,
            m.restricted_or_prohibited_industry, m.small_micro_enterprise,
            m.revenue, m.cost, m.total_profit,
            m.add_specific_business_taxable_income, m.less_non_taxable_income,
            m.less_accelerated_depreciation, m.tax_free_income_deduction_total,
            m.income_exemption_total, m.less_losses_carried_forward,
            m.actual_profit, m.tax_rate, m.tax_payable,
            m.tax_credit_total, m.less_prepaid_tax_current_year,
            m.less_specific_business_prepaid, m.current_tax_payable_or_refund,
            m.hq_share_total, m.hq_share, m.fiscal_central_share,
            m.hq_business_dept_share, m.branch_share_ratio, m.branch_share_amount,
            m.ethnic_autonomous_relief_amount, m.final_tax_payable_or_refund
        FROM eit_quarter_filing f
        JOIN eit_quarter_main m ON f.filing_id = m.filing_id
        JOIN taxpayer_info t ON f.taxpayer_id = t.taxpayer_id""",

        # ============================================================
        # 4h. 发票表（进项/销项宽表）
        # ============================================================
        # --- 进项发票（采购发票）---
        """CREATE TABLE IF NOT EXISTS inv_spec_purchase (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            invoice_format      TEXT NOT NULL,
            invoice_pk          TEXT NOT NULL,
            line_no             INTEGER NOT NULL DEFAULT 1,
            invoice_code        TEXT,
            invoice_number      TEXT,
            digital_invoice_no  TEXT,
            seller_tax_id       TEXT,
            seller_name         TEXT,
            buyer_tax_id        TEXT,
            buyer_name          TEXT,
            invoice_date        TEXT,
            tax_category_code   TEXT,
            special_business_type TEXT,
            goods_name          TEXT,
            specification       TEXT,
            unit                TEXT,
            quantity            REAL,
            unit_price          REAL,
            amount              REAL,
            tax_rate            TEXT,
            tax_amount          REAL,
            total_amount        REAL,
            invoice_source      TEXT,
            invoice_type        TEXT,
            invoice_status      TEXT,
            is_positive         TEXT,
            risk_level          TEXT,
            issuer              TEXT,
            remark              TEXT,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            PRIMARY KEY (taxpayer_id, invoice_pk, line_no),
            CHECK (invoice_format IN ('数电', '非数电'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_inv_purchase_taxpayer_period ON inv_spec_purchase(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_inv_purchase_pk ON inv_spec_purchase(invoice_pk)",
        "CREATE INDEX IF NOT EXISTS idx_inv_purchase_date ON inv_spec_purchase(invoice_date)",

        # --- 销项发票（销售发票）---
        """CREATE TABLE IF NOT EXISTS inv_spec_sales (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            invoice_format      TEXT NOT NULL,
            invoice_pk          TEXT NOT NULL,
            line_no             INTEGER NOT NULL DEFAULT 1,
            invoice_code        TEXT,
            invoice_number      TEXT,
            digital_invoice_no  TEXT,
            seller_tax_id       TEXT,
            seller_name         TEXT,
            buyer_tax_id        TEXT,
            buyer_name          TEXT,
            invoice_date        TEXT,
            amount              REAL,
            tax_amount          REAL,
            total_amount        REAL,
            invoice_source      TEXT,
            invoice_type        TEXT,
            invoice_status      TEXT,
            is_positive         TEXT,
            risk_level          TEXT,
            issuer              TEXT,
            remark              TEXT,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            PRIMARY KEY (taxpayer_id, invoice_pk, line_no),
            CHECK (invoice_format IN ('数电', '非数电'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_inv_sales_taxpayer_period ON inv_spec_sales(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_inv_sales_pk ON inv_spec_sales(invoice_pk)",
        "CREATE INDEX IF NOT EXISTS idx_inv_sales_date ON inv_spec_sales(invoice_date)",

        # --- 发票字段映射表 ---
        """CREATE TABLE IF NOT EXISTS inv_column_mapping (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_column   TEXT NOT NULL,
            target_field    TEXT NOT NULL,
            table_name      TEXT,
            description     TEXT
        )""",

        # --- 发票同义词表 ---
        """CREATE TABLE IF NOT EXISTS inv_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            priority    INTEGER DEFAULT 1,
            scope_view  TEXT,
            UNIQUE(phrase, column_name, scope_view)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_inv_synonyms_phrase ON inv_synonyms(phrase)",

        # ============================================================
        # 9b. 其他域桩视图（空结构，保证管线路由不崩溃）
        # ============================================================
        """CREATE VIEW IF NOT EXISTS vw_account_balance AS
        SELECT
            b.taxpayer_id,
            t.taxpayer_name,
            t.accounting_standard,
            b.period_year,
            b.period_month,
            b.account_code,
            a.account_name,
            a.level,
            a.category,
            a.balance_direction,
            a.is_gaap,
            a.is_small,
            b.revision_no,
            b.opening_balance,
            b.debit_amount,
            b.credit_amount,
            b.closing_balance,
            b.source_unit
        FROM account_balance b
        JOIN taxpayer_info t ON b.taxpayer_id = t.taxpayer_id
        JOIN account_master a ON b.account_code = a.account_code
        WHERE (
            (t.accounting_standard = '企业会计准则' AND a.is_gaap = 1)
            OR (t.accounting_standard = '小企业会计准则' AND a.is_small = 1)
            OR (a.is_gaap = 1 AND a.is_small = 1)
            OR t.accounting_standard IS NULL
        )""",
        # --- 发票视图（替换原空桩 vw_invoice）---
        """CREATE VIEW IF NOT EXISTS vw_inv_spec_purchase AS
        SELECT p.*, t.taxpayer_name, t.taxpayer_type
        FROM inv_spec_purchase p
        JOIN taxpayer_info t ON p.taxpayer_id = t.taxpayer_id""",

        """CREATE VIEW IF NOT EXISTS vw_inv_spec_sales AS
        SELECT s.*, t.taxpayer_name, t.taxpayer_type
        FROM inv_spec_sales s
        JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id""",

        """CREATE VIEW IF NOT EXISTS vw_enterprise_profile AS
        SELECT NULL AS taxpayer_id, NULL AS taxpayer_name, NULL AS period_year,
               NULL AS period_month, NULL AS metric_name, NULL AS metric_value WHERE 0""",

        # ============================================================
        # 4d. 资产负债表
        # ============================================================
        # --- 项目字典表 ---
        """CREATE TABLE IF NOT EXISTS fs_balance_sheet_item_dict (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gaap_type       TEXT NOT NULL,
            item_code       TEXT NOT NULL,
            item_name       TEXT NOT NULL,
            line_number     INTEGER,
            section         TEXT,
            display_order   INTEGER,
            is_total        BOOLEAN DEFAULT 0,
            UNIQUE (gaap_type, item_code)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bs_dict_gaap ON fs_balance_sheet_item_dict(gaap_type)",

        # --- 项目明细表（EAV纵表）---
        """CREATE TABLE IF NOT EXISTS fs_balance_sheet_item (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            gaap_type           TEXT NOT NULL,
            item_code           TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            beginning_balance   NUMERIC,
            ending_balance      NUMERIC,
            item_name           TEXT,
            line_number         INTEGER,
            section             TEXT,
            PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
            CHECK (gaap_type IN ('ASBE', 'ASSE')),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bs_period ON fs_balance_sheet_item(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_bs_taxpayer ON fs_balance_sheet_item(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_bs_taxpayer_period ON fs_balance_sheet_item(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_bs_taxpayer_period_gaap ON fs_balance_sheet_item(taxpayer_id, period_year, period_month, gaap_type, revision_no DESC)",

        # --- 同义词映射表 ---
        """CREATE TABLE IF NOT EXISTS fs_balance_sheet_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            gaap_type   TEXT,
            priority    INTEGER DEFAULT 1,
            UNIQUE(phrase, column_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_bs_synonyms_phrase ON fs_balance_sheet_synonyms(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_bs_synonyms_gaap ON fs_balance_sheet_synonyms(gaap_type, priority)",

        # ============================================================
        # 4e. 利润表（EAV纵表）
        # ============================================================
        # --- 利润表明细表（EAV纵表，替代原宽表 fs_profit_statement_detail）---
        """CREATE TABLE IF NOT EXISTS fs_income_statement_item (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            gaap_type           TEXT NOT NULL,
            item_code           TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            current_amount      NUMERIC,
            cumulative_amount   NUMERIC,
            item_name           TEXT,
            line_number         INTEGER,
            category            TEXT,
            PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
            CHECK (gaap_type IN ('CAS', 'SAS')),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_is_period ON fs_income_statement_item(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_is_taxpayer ON fs_income_statement_item(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_is_taxpayer_period ON fs_income_statement_item(taxpayer_id, period_year, period_month)",

        # --- 利润表项目字典表 ---
        """CREATE TABLE IF NOT EXISTS fs_income_statement_item_dict (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gaap_type       TEXT NOT NULL,
            item_code       TEXT NOT NULL,
            item_name       TEXT NOT NULL,
            line_number     INTEGER,
            category        TEXT,
            display_order   INTEGER,
            is_total        BOOLEAN DEFAULT 0,
            UNIQUE (gaap_type, item_code)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_is_dict_gaap ON fs_income_statement_item_dict(gaap_type)",

        # --- 利润表同义词表 ---
        """CREATE TABLE IF NOT EXISTS fs_income_statement_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            gaap_type   TEXT,
            priority    INTEGER DEFAULT 1,
            UNIQUE(phrase, column_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_is_synonyms_phrase ON fs_income_statement_synonyms(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_is_synonyms_gaap ON fs_income_statement_synonyms(gaap_type, priority)",

        # ============================================================
        # 4f. 现金流量表（EAV纵表）
        # ============================================================
        # --- 现金流量表明细表（EAV纵表，合并原 fs_cash_flow_eas / fs_cash_flow_sas）---
        """CREATE TABLE IF NOT EXISTS fs_cash_flow_item (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            gaap_type           TEXT NOT NULL,
            item_code           TEXT NOT NULL,
            revision_no         INTEGER NOT NULL DEFAULT 0,
            submitted_at        TIMESTAMP,
            etl_batch_id        TEXT,
            source_doc_id       TEXT,
            source_unit         TEXT DEFAULT '元',
            etl_confidence      REAL,
            current_amount      NUMERIC,
            cumulative_amount   NUMERIC,
            item_name           TEXT,
            line_number         INTEGER,
            category            TEXT,
            PRIMARY KEY (taxpayer_id, period_year, period_month, gaap_type, item_code, revision_no),
            CHECK (gaap_type IN ('CAS', 'SAS')),
            CHECK (revision_no >= 0)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cf_period ON fs_cash_flow_item(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_cf_taxpayer ON fs_cash_flow_item(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_cf_taxpayer_period ON fs_cash_flow_item(taxpayer_id, period_year, period_month)",

        # --- 现金流量表项目字典表 ---
        """CREATE TABLE IF NOT EXISTS fs_cash_flow_item_dict (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            gaap_type       TEXT NOT NULL,
            item_code       TEXT NOT NULL,
            item_name       TEXT NOT NULL,
            line_number     INTEGER,
            category        TEXT,
            display_order   INTEGER,
            is_total        BOOLEAN DEFAULT 0,
            UNIQUE (gaap_type, item_code)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cf_dict_gaap ON fs_cash_flow_item_dict(gaap_type)",

        # --- 现金流量表同义词表 ---
        """CREATE TABLE IF NOT EXISTS fs_cash_flow_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            gaap_type   TEXT,
            priority    INTEGER DEFAULT 1,
            UNIQUE(phrase, column_name, gaap_type)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_cf_synonyms_phrase ON fs_cash_flow_synonyms(phrase)",
        "CREATE INDEX IF NOT EXISTS idx_cf_synonyms_gaap ON fs_cash_flow_synonyms(gaap_type, priority)",

        # ============================================================
        # 4g. 财务指标表
        # ============================================================
        """CREATE TABLE IF NOT EXISTS financial_metrics (
            taxpayer_id         TEXT NOT NULL,
            period_year         INTEGER NOT NULL,
            period_month        INTEGER NOT NULL,
            metric_category     TEXT NOT NULL,
            metric_code         TEXT NOT NULL,
            metric_name         TEXT NOT NULL,
            metric_value        NUMERIC,
            metric_unit         TEXT,
            evaluation_level    TEXT,
            calculated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (taxpayer_id, period_year, period_month, metric_code),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fm_taxpayer ON financial_metrics(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_fm_period ON financial_metrics(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_fm_taxpayer_period ON financial_metrics(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_fm_category ON financial_metrics(metric_category)",
        "CREATE INDEX IF NOT EXISTS idx_fm_code ON financial_metrics(metric_code)",

        # --- 财务指标同义词表 ---
        """CREATE TABLE IF NOT EXISTS financial_metrics_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            priority    INTEGER DEFAULT 1,
            UNIQUE(phrase, column_name)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fm_synonyms_phrase ON financial_metrics_synonyms(phrase)",

        # --- 财务指标项目字典表 ---
        """CREATE TABLE IF NOT EXISTS financial_metrics_item_dict (
            metric_code     TEXT PRIMARY KEY,
            metric_name     TEXT NOT NULL,
            metric_category TEXT NOT NULL,
            metric_unit     TEXT DEFAULT '',
            formula_desc    TEXT,
            source_domains  TEXT,
            period_types    TEXT NOT NULL,
            eval_rules      TEXT,
            eval_ascending  INTEGER DEFAULT 0,
            display_order   INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1
        )""",

        # --- 财务指标明细表（新，含 period_type 维度）---
        """CREATE TABLE IF NOT EXISTS financial_metrics_item (
            taxpayer_id      TEXT NOT NULL,
            period_year      INTEGER NOT NULL,
            period_month     INTEGER NOT NULL,
            period_type      TEXT NOT NULL,
            metric_code      TEXT NOT NULL,
            metric_name      TEXT NOT NULL,
            metric_category  TEXT NOT NULL,
            metric_value     NUMERIC,
            metric_unit      TEXT,
            evaluation_level TEXT,
            calculated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (taxpayer_id, period_year, period_month, period_type, metric_code),
            FOREIGN KEY (taxpayer_id) REFERENCES taxpayer_info(taxpayer_id),
            FOREIGN KEY (metric_code) REFERENCES financial_metrics_item_dict(metric_code)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_fmi_taxpayer ON financial_metrics_item(taxpayer_id)",
        "CREATE INDEX IF NOT EXISTS idx_fmi_period ON financial_metrics_item(period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_fmi_taxpayer_period ON financial_metrics_item(taxpayer_id, period_year, period_month)",
        "CREATE INDEX IF NOT EXISTS idx_fmi_category ON financial_metrics_item(metric_category)",
        "CREATE INDEX IF NOT EXISTS idx_fmi_code ON financial_metrics_item(metric_code)",
        "CREATE INDEX IF NOT EXISTS idx_fmi_period_type ON financial_metrics_item(period_type)",

        # ============================================================
        # 4i. 人事薪金表（HR）
        # ============================================================

        # --- 员工信息表 ---
        """CREATE TABLE IF NOT EXISTS hr_employee_info (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            company_code          TEXT NOT NULL,        -- 公司编码（多公司场景）
            company_name          TEXT NOT NULL,        -- 公司名称
            dept_code             TEXT NOT NULL,        -- 部门编码
            dept_name             TEXT NOT NULL,        -- 部门名称
            dept_level            INTEGER NOT NULL,     -- 部门层级（1=一级部门，2=二级部门...）
            employee_id           TEXT NOT NULL UNIQUE,  -- 员工工号（唯一）
            employee_name         TEXT NOT NULL,        -- 员工姓名
            id_card               TEXT NOT NULL,        -- 身份证号（建议脱敏）
            gender                TEXT NOT NULL,        -- 性别（1=男，2=女）
            birth_date            DATE NOT NULL,        -- 出生日期
            age                   INTEGER NOT NULL,     -- 年龄
            education             TEXT NOT NULL,        -- 学历（本科/硕士/博士/大专等）
            education_degree      INTEGER NOT NULL,     -- 学历编码（1=大专，2=本科，3=硕士，4=博士）
            major                 TEXT,                 -- 所学专业
            major_type            TEXT,                 -- 专业类型（理工/文科/经管等）
            entry_date            DATE NOT NULL,        -- 入职日期
            work_years            DECIMAL(4,1) NOT NULL, -- 司龄（年）
            total_work_years      DECIMAL(4,1),         -- 总工作年限（年）
            position_code         TEXT NOT NULL,        -- 岗位编码
            position_name         TEXT NOT NULL,        -- 岗位名称
            position_type         TEXT NOT NULL,        -- 岗位类型（研发/生产/销售/管理等）
            employment_type       TEXT NOT NULL,        -- 用工类型（正式/劳务派遣/实习/外包）
            social_insurance_city TEXT,                 -- 社保缴纳城市
            is_on_the_job         INTEGER NOT NULL,     -- 是否在职（1=是，0=否）
            resign_date           DATE,                 -- 离职日期
            is_high_tech_person   INTEGER,              -- 是否符合高新人员要求（1=是，0=否）
            high_tech_cert_type   TEXT,                 -- 高新认定资质类型
            high_tech_cert_name   TEXT,                 -- 高新认定资质名称
            high_tech_work_days   INTEGER,              -- 年度在企业累计工作天数
            create_time           DATETIME DEFAULT CURRENT_TIMESTAMP,
            update_time           DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_hr_emp_dept_code ON hr_employee_info(dept_code)",
        "CREATE INDEX IF NOT EXISTS idx_hr_emp_position_type ON hr_employee_info(position_type)",
        "CREATE INDEX IF NOT EXISTS idx_hr_emp_is_high_tech ON hr_employee_info(is_high_tech_person)",
        "CREATE INDEX IF NOT EXISTS idx_hr_emp_is_on_job ON hr_employee_info(is_on_the_job)",

        # --- 员工信息字段映射表 ---
        """CREATE TABLE IF NOT EXISTS hr_employee_column_mapping (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_column   TEXT NOT NULL,
            target_field    TEXT NOT NULL,
            table_name      TEXT,
            description     TEXT
        )""",

        # --- 员工信息同义词表 ---
        """CREATE TABLE IF NOT EXISTS hr_employee_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            priority    INTEGER DEFAULT 1,
            scope_view  TEXT,
            UNIQUE(phrase, column_name, scope_view)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_hr_emp_syn_phrase ON hr_employee_synonyms(phrase)",

        # --- 员工薪资表 ---
        """CREATE TABLE IF NOT EXISTS hr_employee_salary (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id                 TEXT NOT NULL,           -- 员工工号
            salary_month                TEXT NOT NULL,           -- 薪资所属月份（YYYYMM）
            -- 收入额
            income_wage                 DECIMAL(12,2),           -- 工资薪金收入
            income_bonus_yearly         DECIMAL(12,2),           -- 全年一次性奖金
            income_bonus_quarterly      DECIMAL(12,2),           -- 季度奖
            income_bonus_monthly        DECIMAL(12,2),           -- 月度奖
            income_bonus_performance    DECIMAL(12,2),           -- 绩效奖金
            income_bonus_other          DECIMAL(12,2),           -- 其他奖金
            allowance_transport         DECIMAL(12,2),           -- 交通补贴
            allowance_meal              DECIMAL(12,2),           -- 餐补
            allowance_housing           DECIMAL(12,2),           -- 住房补贴
            allowance_high_temp         DECIMAL(12,2),           -- 高温补贴
            allowance_shift             DECIMAL(12,2),           -- 夜班/加班补贴
            allowance_other             DECIMAL(12,2),           -- 其他补贴
            total_income                DECIMAL(12,2) NOT NULL,  -- 收入合计
            cost_deductible             DECIMAL(12,2),           -- 减除费用
            tax_free_income             DECIMAL(12,2),           -- 免税收入
            other_income_deduct         DECIMAL(12,2),           -- 其他减除费用
            -- 专项扣除
            deduction_si_pension        DECIMAL(12,2),           -- 基本养老保险费
            deduction_si_medical        DECIMAL(12,2),           -- 基本医疗保险费
            deduction_si_unemployment   DECIMAL(12,2),           -- 失业保险费
            deduction_housing_fund      DECIMAL(12,2),           -- 住房公积金
            total_special_deduction     DECIMAL(12,2),           -- 专项扣除合计
            -- 专项附加扣除
            deduction_child_edu         DECIMAL(12,2),           -- 子女教育
            deduction_continue_edu      DECIMAL(12,2),           -- 继续教育
            deduction_housing_loan      DECIMAL(12,2),           -- 住房贷款利息
            deduction_housing_rent      DECIMAL(12,2),           -- 住房租金
            deduction_elderly_care      DECIMAL(12,2),           -- 赡养老人
            deduction_3yo_child_care    DECIMAL(12,2),           -- 3岁以下婴幼儿照护
            total_special_add_deduction DECIMAL(12,2),           -- 专项附加扣除合计
            -- 其他扣除
            deduction_enterprise_annuity   DECIMAL(12,2),        -- 企业年金/职业年金
            deduction_commercial_health    DECIMAL(12,2),        -- 商业健康保险
            deduction_tax_deferred_pension DECIMAL(12,2),        -- 税收递延型商业养老保险
            deduction_other_allowable      DECIMAL(12,2),        -- 其他允许扣除的税费
            total_other_deduction          DECIMAL(12,2),        -- 其他扣除合计
            -- 准予扣除的捐赠额
            donation_allowable          DECIMAL(12,2),           -- 准予扣除的捐赠额
            -- 税款计算
            taxable_income              DECIMAL(12,2) NOT NULL,  -- 应纳税所得额
            tax_rate                    DECIMAL(5,2),            -- 税率
            quick_deduction             DECIMAL(12,2),           -- 速算扣除数
            tax_payable                 DECIMAL(12,2) NOT NULL,  -- 应纳税额
            tax_reduction               DECIMAL(12,2),           -- 减免税额
            tax_withheld                DECIMAL(12,2),           -- 已预缴税额
            tax_refund_or_pay           DECIMAL(12,2),           -- 应补/退税额
            -- 公司承担部分
            company_si_pension          DECIMAL(12,2),           -- 公司承担养老保险
            company_si_medical          DECIMAL(12,2),           -- 公司承担医疗保险
            company_si_unemployment     DECIMAL(12,2),           -- 公司承担失业保险
            company_si_injury           DECIMAL(12,2),           -- 公司承担工伤保险
            company_si_maternity        DECIMAL(12,2),           -- 公司承担生育保险
            company_housing_fund        DECIMAL(12,2),           -- 公司承担住房公积金
            company_total_benefit       DECIMAL(12,2),           -- 公司承担五险一金合计
            -- 实发与备注
            gross_salary                DECIMAL(12,2) NOT NULL,  -- 应发工资总额
            net_salary                  DECIMAL(12,2) NOT NULL,  -- 实发工资
            remark                      TEXT,                    -- 备注
            -- 审计字段
            create_time                 DATETIME DEFAULT CURRENT_TIMESTAMP,
            update_time                 DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, salary_month)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_hr_sal_month ON hr_employee_salary(salary_month)",
        "CREATE INDEX IF NOT EXISTS idx_hr_sal_employee ON hr_employee_salary(employee_id)",

        # --- 薪资字段映射表 ---
        """CREATE TABLE IF NOT EXISTS hr_salary_column_mapping (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_column   TEXT NOT NULL,
            target_field    TEXT NOT NULL,
            table_name      TEXT,
            description     TEXT
        )""",

        # --- 薪资同义词表 ---
        """CREATE TABLE IF NOT EXISTS hr_salary_synonyms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase      TEXT NOT NULL,
            column_name TEXT NOT NULL,
            priority    INTEGER DEFAULT 1,
            scope_view  TEXT,
            UNIQUE(phrase, column_name, scope_view)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_hr_sal_syn_phrase ON hr_salary_synonyms(phrase)",

        # ============================================================
        # 10. 性能优化索引（2025-02-14添加）
        # ============================================================
        "CREATE INDEX IF NOT EXISTS idx_general_taxpayer_period_revision ON vat_return_general(taxpayer_id, period_year, period_month, revision_no DESC)",
        "CREATE INDEX IF NOT EXISTS idx_small_taxpayer_period_revision ON vat_return_small(taxpayer_id, period_year, period_month, revision_no DESC)",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_type ON taxpayer_info(taxpayer_type)",
        "CREATE INDEX IF NOT EXISTS idx_general_dimensions ON vat_return_general(taxpayer_id, period_year, period_month, item_type, time_range)",
        "CREATE INDEX IF NOT EXISTS idx_small_dimensions ON vat_return_small(taxpayer_id, period_year, period_month, item_type, time_range)",
        "CREATE INDEX IF NOT EXISTS idx_taxpayer_type_industry ON taxpayer_info(taxpayer_type, industry_code)",
        "CREATE INDEX IF NOT EXISTS idx_query_log_taxpayer_period ON user_query_log(taxpayer_id, created_at DESC)",

        # ============================================================
        # 10b. EIT 性能优化索引
        # ============================================================
        "CREATE INDEX IF NOT EXISTS idx_eit_annual_filing_taxpayer_period ON eit_annual_filing(taxpayer_id, period_year, revision_no DESC)",
        "CREATE INDEX IF NOT EXISTS idx_eit_quarter_filing_taxpayer_period ON eit_quarter_filing(taxpayer_id, period_year, period_quarter, revision_no DESC)",
    ]


def _get_bs_view_ddl():
    """动态生成资产负债表宽表视图DDL"""
    # 企业会计准则项目编码列表（与字典表一致）
    ASBE_ITEMS = [
        'CASH', 'TRADING_FINANCIAL_ASSETS', 'DERIVATIVE_FINANCIAL_ASSETS',
        'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE', 'ACCOUNTS_RECEIVABLE_FINANCING',
        'PREPAYMENTS', 'OTHER_RECEIVABLES', 'INVENTORY', 'CONTRACT_ASSETS',
        'HELD_FOR_SALE_ASSETS', 'CURRENT_PORTION_NON_CURRENT_ASSETS',
        'OTHER_CURRENT_ASSETS', 'CURRENT_ASSETS',
        'DEBT_INVESTMENTS', 'OTHER_DEBT_INVESTMENTS', 'LONG_TERM_RECEIVABLES',
        'LONG_TERM_EQUITY_INVESTMENTS', 'OTHER_EQUITY_INSTRUMENTS_INVEST',
        'OTHER_NON_CURRENT_FINANCIAL_ASSETS', 'INVESTMENT_PROPERTY',
        'FIXED_ASSETS', 'CONSTRUCTION_IN_PROGRESS', 'PRODUCTIVE_BIOLOGICAL_ASSETS',
        'OIL_AND_GAS_ASSETS', 'RIGHT_OF_USE_ASSETS', 'INTANGIBLE_ASSETS',
        'DEVELOPMENT_EXPENDITURE', 'GOODWILL', 'LONG_TERM_DEFERRED_EXPENSES',
        'DEFERRED_TAX_ASSETS', 'OTHER_NON_CURRENT_ASSETS', 'NON_CURRENT_ASSETS',
        'ASSETS',
        'SHORT_TERM_LOANS', 'TRADING_FINANCIAL_LIABILITIES',
        'DERIVATIVE_FINANCIAL_LIABILITIES', 'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE',
        'ADVANCES_FROM_CUSTOMERS', 'CONTRACT_LIABILITIES',
        'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE', 'OTHER_PAYABLES',
        'HELD_FOR_SALE_LIABILITIES', 'CURRENT_PORTION_NON_CURRENT_LIABILITIES',
        'OTHER_CURRENT_LIABILITIES', 'CURRENT_LIABILITIES',
        'LONG_TERM_LOANS', 'BONDS_PAYABLE', 'LEASE_LIABILITIES',
        'LONG_TERM_PAYABLES', 'PROVISIONS', 'DEFERRED_INCOME',
        'DEFERRED_TAX_LIABILITIES', 'OTHER_NON_CURRENT_LIABILITIES',
        'NON_CURRENT_LIABILITIES', 'LIABILITIES',
        'SHARE_CAPITAL', 'CAPITAL_RESERVE', 'TREASURY_STOCK',
        'OTHER_COMPREHENSIVE_INCOME', 'SPECIAL_RESERVE', 'SURPLUS_RESERVE',
        'RETAINED_EARNINGS', 'EQUITY', 'LIABILITIES_AND_EQUITY',
    ]

    # 小企业会计准则项目编码列表
    ASSE_ITEMS = [
        'CASH', 'SHORT_TERM_INVESTMENTS', 'NOTES_RECEIVABLE', 'ACCOUNTS_RECEIVABLE',
        'PREPAYMENTS', 'DIVIDENDS_RECEIVABLE', 'INTEREST_RECEIVABLE',
        'OTHER_RECEIVABLES', 'INVENTORY', 'RAW_MATERIALS', 'WORK_IN_PROCESS',
        'FINISHED_GOODS', 'TURNOVER_MATERIALS', 'OTHER_CURRENT_ASSETS',
        'CURRENT_ASSETS',
        'LONG_TERM_BOND_INVESTMENTS', 'LONG_TERM_EQUITY_INVESTMENTS',
        'FIXED_ASSETS_ORIGINAL', 'ACCUMULATED_DEPRECIATION', 'FIXED_ASSETS_NET',
        'CONSTRUCTION_IN_PROGRESS', 'ENGINEERING_MATERIALS',
        'FIXED_ASSETS_LIQUIDATION', 'PRODUCTIVE_BIOLOGICAL_ASSETS',
        'INTANGIBLE_ASSETS', 'DEVELOPMENT_EXPENDITURE',
        'LONG_TERM_DEFERRED_EXPENSES', 'OTHER_NON_CURRENT_ASSETS',
        'NON_CURRENT_ASSETS', 'ASSETS',
        'SHORT_TERM_LOANS', 'NOTES_PAYABLE', 'ACCOUNTS_PAYABLE',
        'ADVANCES_FROM_CUSTOMERS', 'EMPLOYEE_BENEFITS_PAYABLE', 'TAXES_PAYABLE',
        'INTEREST_PAYABLE', 'PROFIT_PAYABLE', 'OTHER_PAYABLES',
        'OTHER_CURRENT_LIABILITIES', 'CURRENT_LIABILITIES',
        'LONG_TERM_LOANS', 'LONG_TERM_PAYABLES', 'DEFERRED_INCOME',
        'OTHER_NON_CURRENT_LIABILITIES', 'NON_CURRENT_LIABILITIES', 'LIABILITIES',
        'SHARE_CAPITAL', 'CAPITAL_RESERVE', 'SURPLUS_RESERVE',
        'RETAINED_EARNINGS', 'EQUITY', 'LIABILITIES_AND_EQUITY',
    ]

    def _build_view(view_name, gaap_type, items):
        cols = []
        for code in items:
            col = code.lower()
            cols.append(
                f"    MAX(CASE WHEN i.item_code = '{code}' THEN i.beginning_balance END) AS {col}_begin,\n"
                f"    MAX(CASE WHEN i.item_code = '{code}' THEN i.ending_balance END) AS {col}_end"
            )
        cols_sql = ",\n".join(cols)
        return f"""CREATE VIEW IF NOT EXISTS {view_name} AS
SELECT
    i.taxpayer_id,
    t.taxpayer_name,
    t.accounting_standard,
    i.period_year,
    i.period_month,
    i.revision_no,
    i.submitted_at,
    i.etl_batch_id,
    i.source_doc_id,
    i.source_unit,
    i.etl_confidence,
{cols_sql}
FROM fs_balance_sheet_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
WHERE i.gaap_type = '{gaap_type}'
GROUP BY i.taxpayer_id, t.taxpayer_name, t.accounting_standard,
         i.period_year, i.period_month, i.revision_no,
         i.submitted_at, i.etl_batch_id, i.source_doc_id,
         i.source_unit, i.etl_confidence"""

    return [
        _build_view('vw_balance_sheet_eas', 'ASBE', ASBE_ITEMS),
        _build_view('vw_balance_sheet_sas', 'ASSE', ASSE_ITEMS),
    ]


def _get_profit_view_ddl():
    """动态生成利润表宽表视图DDL（从EAV纵表透视）"""
    # 企业会计准则(CAS)项目编码列表 — 与原视图列名一致，保证向后兼容
    CAS_ITEMS = [
        'operating_revenue', 'operating_cost', 'taxes_and_surcharges',
        'selling_expense', 'administrative_expense', 'rd_expense',
        'financial_expense', 'interest_expense', 'interest_income',
        'other_gains', 'investment_income', 'investment_income_associates',
        'amortized_cost_termination_income', 'net_exposure_hedge_income',
        'fair_value_change_income', 'credit_impairment_loss', 'asset_impairment_loss',
        'asset_disposal_gains', 'operating_profit',
        'non_operating_income', 'non_operating_expense',
        'total_profit', 'income_tax_expense', 'net_profit',
        'continued_ops_net_profit', 'discontinued_ops_net_profit',
        'other_comprehensive_income_net', 'oci_not_reclassifiable', 'oci_reclassifiable',
        'comprehensive_income_total', 'eps_basic', 'eps_diluted',
        'oci_remeasurement_pension', 'oci_equity_method_nonreclassifiable',
        'oci_equity_investment_fv_change', 'oci_credit_risk_change',
        'oci_equity_method_reclassifiable', 'oci_debt_investment_fv_change',
        'oci_reclassify_to_pnl', 'oci_debt_impairment',
        'oci_cash_flow_hedge', 'oci_foreign_currency_translation',
    ]

    # 小企业会计准则(SAS)项目编码列表 — 与原视图列名一致
    SAS_ITEMS = [
        'operating_revenue', 'operating_cost', 'taxes_and_surcharges',
        'consumption_tax', 'business_tax', 'city_maintenance_tax',
        'resource_tax', 'land_appreciation_tax', 'property_related_taxes',
        'education_surcharge',
        'selling_expense', 'goods_repair_expense', 'advertising_expense',
        'administrative_expense', 'organization_expense',
        'business_entertainment_expense', 'research_expense',
        'financial_expense', 'interest_expense_net',
        'investment_income', 'operating_profit',
        'non_operating_income', 'government_grant',
        'non_operating_expense', 'bad_debt_loss',
        'long_term_bond_loss', 'long_term_equity_loss',
        'force_majeure_loss', 'tax_late_payment',
        'total_profit', 'income_tax_expense', 'net_profit',
    ]

    def _build_profit_view(view_name, gaap_type, items, std_name):
        cols = []
        for code in items:
            cols.append(
                f"    MAX(CASE WHEN i.item_code = '{code}' THEN\n"
                f"        CASE WHEN tr.time_range = '本期' THEN i.current_amount\n"
                f"             ELSE i.cumulative_amount END END) AS {code}"
            )
        cols_sql = ",\n".join(cols)
        return f"""CREATE VIEW IF NOT EXISTS {view_name} AS
SELECT
    i.taxpayer_id,
    t.taxpayer_name,
    i.period_year,
    i.period_month,
    tr.time_range,
    '{std_name}' AS accounting_standard_name,
    i.revision_no,
    i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence,
{cols_sql}
FROM fs_income_statement_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
CROSS JOIN (SELECT '本期' AS time_range UNION ALL SELECT '本年累计') tr
WHERE i.gaap_type = '{gaap_type}'
GROUP BY i.taxpayer_id, t.taxpayer_name, i.period_year, i.period_month,
         tr.time_range, i.revision_no,
         i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence"""

    return [
        _build_profit_view('vw_profit_eas', 'CAS', CAS_ITEMS, '企业会计准则'),
        _build_profit_view('vw_profit_sas', 'SAS', SAS_ITEMS, '小企业会计准则'),
    ]


def _get_cash_flow_view_ddl():
    """动态生成现金流量表宽表视图DDL（从EAV纵表透视，同利润表模式）"""
    CAS_ITEMS = [
        'operating_inflow_sales', 'operating_inflow_tax_refund', 'operating_inflow_other',
        'operating_inflow_subtotal', 'operating_outflow_purchase', 'operating_outflow_labor',
        'operating_outflow_tax', 'operating_outflow_other', 'operating_outflow_subtotal',
        'operating_net_cash', 'investing_inflow_sale_investment', 'investing_inflow_returns',
        'investing_inflow_disposal_assets', 'investing_inflow_disposal_subsidiary',
        'investing_inflow_other', 'investing_inflow_subtotal',
        'investing_outflow_purchase_assets', 'investing_outflow_purchase_investment',
        'investing_outflow_acquire_subsidiary', 'investing_outflow_other',
        'investing_outflow_subtotal', 'investing_net_cash',
        'financing_inflow_capital', 'financing_inflow_borrowing', 'financing_inflow_other',
        'financing_inflow_subtotal', 'financing_outflow_debt_repayment',
        'financing_outflow_dividend_interest', 'financing_outflow_other',
        'financing_outflow_subtotal', 'financing_net_cash',
        'fx_impact', 'net_increase_cash', 'beginning_cash', 'ending_cash',
    ]
    SAS_ITEMS = [
        'operating_receipts_sales', 'operating_receipts_other',
        'operating_payments_purchase', 'operating_payments_staff',
        'operating_payments_tax', 'operating_payments_other', 'operating_net_cash',
        'investing_receipts_disposal_investment', 'investing_receipts_returns',
        'investing_receipts_disposal_assets',
        'investing_payments_purchase_investment', 'investing_payments_purchase_assets',
        'investing_net_cash',
        'financing_receipts_borrowing', 'financing_receipts_capital',
        'financing_payments_debt_principal', 'financing_payments_debt_interest',
        'financing_payments_dividend', 'financing_net_cash',
        'net_increase_cash', 'beginning_cash', 'ending_cash',
    ]

    def _build_cf_view(view_name, gaap_type, items, acct_std):
        cols = []
        for code in items:
            cols.append(
                f"    MAX(CASE WHEN i.item_code = '{code}' THEN\n"
                f"        CASE WHEN tr.time_range = '本期' THEN i.current_amount\n"
                f"             ELSE i.cumulative_amount END END) AS {code}"
            )
        cols_sql = ",\n".join(cols)
        return f"""CREATE VIEW IF NOT EXISTS {view_name} AS
SELECT
    i.taxpayer_id,
    t.taxpayer_name,
    i.period_year,
    i.period_month,
    tr.time_range,
    t.taxpayer_type,
    t.accounting_standard,
    i.revision_no,
    i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence,
{cols_sql}
FROM fs_cash_flow_item i
JOIN taxpayer_info t ON i.taxpayer_id = t.taxpayer_id
CROSS JOIN (SELECT '本期' AS time_range UNION ALL SELECT '本年累计') tr
WHERE i.gaap_type = '{gaap_type}'
  AND t.accounting_standard = '{acct_std}'
GROUP BY i.taxpayer_id, t.taxpayer_name, i.period_year, i.period_month,
         tr.time_range, t.taxpayer_type, t.accounting_standard, i.revision_no,
         i.submitted_at, i.etl_batch_id, i.source_doc_id, i.source_unit, i.etl_confidence"""

    return [
        _build_cf_view('vw_cash_flow_eas', 'CAS', CAS_ITEMS, '企业会计准则'),
        _build_cf_view('vw_cash_flow_sas', 'SAS', SAS_ITEMS, '小企业会计准则'),
    ]


def _get_financial_metrics_view_ddl():
    """生成财务指标视图DDL（基于 financial_metrics_item 新表）"""
    return [
        "DROP VIEW IF EXISTS vw_financial_metrics",
        """CREATE VIEW IF NOT EXISTS vw_financial_metrics AS
SELECT
    fm.taxpayer_id,
    t.taxpayer_name,
    t.taxpayer_type,
    t.accounting_standard,
    fm.period_year,
    fm.period_month,
    CASE
        WHEN fm.period_month = 12 THEN 'annual'
        WHEN fm.period_month IN (3, 6, 9, 12) THEN 'quarterly'
        ELSE 'monthly'
    END AS period_type,
    fm.metric_category,
    fm.metric_code,
    fm.metric_name,
    fm.metric_value,
    fm.metric_unit,
    fm.evaluation_level,
    fm.calculated_at
FROM financial_metrics fm
JOIN taxpayer_info t ON fm.taxpayer_id = t.taxpayer_id""",
    ]


def init_database(db_path=None):
    """创建全部表、索引、视图。幂等可重复执行。"""
    db_path = db_path or str(DB_PATH)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()
    for stmt in get_ddl_statements():
        cur.execute(stmt)
    # 动态生成资产负债表宽表视图
    for view_ddl in _get_bs_view_ddl():
        cur.execute(view_ddl)
    # 利润表视图
    for view_ddl in _get_profit_view_ddl():
        cur.execute(view_ddl)
    # 现金流量表视图
    for view_ddl in _get_cash_flow_view_ddl():
        cur.execute(view_ddl)
    # 财务指标视图
    for view_ddl in _get_financial_metrics_view_ddl():
        cur.execute(view_ddl)
    conn.commit()
    conn.close()
    print(f"[init_db] 数据库初始化完成: {db_path}")


if __name__ == "__main__":
    init_database()
