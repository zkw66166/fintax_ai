"""一次性增量迁移：为现有 DB 添加发票域对象（表、索引、视图、种子数据、示例数据）。
全部使用 IF NOT EXISTS / INSERT OR IGNORE / INSERT OR REPLACE，可安全重复执行。
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import DB_PATH


def migrate(db_path=None):
    db_path = db_path or str(DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    # ── 1. 移除旧空桩视图 ──
    cur.execute("DROP VIEW IF EXISTS vw_invoice")
    print("[migrate] 已移除旧 vw_invoice 空桩视图")

    # ── 2. 创建表 ──
    cur.execute("""CREATE TABLE IF NOT EXISTS inv_spec_purchase (
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
    )""")
    print("[migrate] inv_spec_purchase 表已就绪")

    cur.execute("""CREATE TABLE IF NOT EXISTS inv_spec_sales (
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
    )""")
    print("[migrate] inv_spec_sales 表已就绪")

    cur.execute("""CREATE TABLE IF NOT EXISTS inv_column_mapping (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        source_column   TEXT NOT NULL,
        target_field    TEXT NOT NULL,
        table_name      TEXT,
        description     TEXT
    )""")
    print("[migrate] inv_column_mapping 表已就绪")

    cur.execute("""CREATE TABLE IF NOT EXISTS inv_synonyms (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        phrase      TEXT NOT NULL,
        column_name TEXT NOT NULL,
        priority    INTEGER DEFAULT 1,
        scope_view  TEXT,
        UNIQUE(phrase, column_name, scope_view)
    )""")
    print("[migrate] inv_synonyms 表已就绪")

    # ── 3. 创建索引 ──
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_purchase_taxpayer_period ON inv_spec_purchase(taxpayer_id, period_year, period_month)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_purchase_pk ON inv_spec_purchase(invoice_pk)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_purchase_date ON inv_spec_purchase(invoice_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_sales_taxpayer_period ON inv_spec_sales(taxpayer_id, period_year, period_month)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_sales_pk ON inv_spec_sales(invoice_pk)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_sales_date ON inv_spec_sales(invoice_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_inv_synonyms_phrase ON inv_synonyms(phrase)")
    print("[migrate] 7 个索引已就绪")

    # ── 4. 创建视图 ──
    cur.execute("""CREATE VIEW IF NOT EXISTS vw_inv_spec_purchase AS
    SELECT p.*, t.taxpayer_name, t.taxpayer_type
    FROM inv_spec_purchase p
    JOIN taxpayer_info t ON p.taxpayer_id = t.taxpayer_id""")

    cur.execute("""CREATE VIEW IF NOT EXISTS vw_inv_spec_sales AS
    SELECT s.*, t.taxpayer_name, t.taxpayer_type
    FROM inv_spec_sales s
    JOIN taxpayer_info t ON s.taxpayer_id = t.taxpayer_id""")
    print("[migrate] vw_inv_spec_purchase / vw_inv_spec_sales 视图已就绪")

    # ── 5. 种子数据 ──
    from database.seed_data import _seed_inv_column_mappings, _seed_inv_synonyms
    _seed_inv_column_mappings(cur)
    _seed_inv_synonyms(cur)

    # ── 6. 示例数据 ──
    from database.sample_data import _insert_invoice_purchase, _insert_invoice_sales
    _insert_invoice_purchase(cur)
    _insert_invoice_sales(cur)

    conn.commit()
    conn.close()
    print("[migrate] 发票域增量迁移完成 ✓")


if __name__ == "__main__":
    migrate()
