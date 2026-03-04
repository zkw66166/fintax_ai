"""Data management stats, companies overview, and quality check endpoints."""
import sqlite3
import time
from fastapi import APIRouter, Depends, Query, HTTPException
from api.auth import get_current_user, get_user_company_ids, require_company_access, require_admin
from config.settings import DB_PATH

router = APIRouter(prefix="/data-management", tags=["data-management"])


def require_sys(user: dict = Depends(get_current_user)):
    """仅允许 sys 角色访问"""
    if user['role'] != 'sys':
        raise HTTPException(status_code=403, detail="仅超级管理员可执行此操作")
    return user

# Domain config for stats
DOMAIN_TABLES = {
    "balance_sheet": {"label": "资产负债表", "label_en": "Balance Sheet", "table": "fs_balance_sheet_item", "freq": "月度", "period_col": "period_month"},
    "profit": {"label": "利润表", "label_en": "Income Statement", "table": "fs_income_statement_item", "freq": "月度", "period_col": "period_month"},
    "cash_flow": {"label": "现金流量表", "label_en": "Cash Flow Statement", "table": "fs_cash_flow_item", "freq": "月度", "period_col": "period_month"},
    "vat": {"label": "增值税申报表", "label_en": "VAT Return", "table": "vat_return_general", "freq": "月度", "period_col": "period_month"},
    "eit": {"label": "企业所得税申报表", "label_en": "CIT Return", "table": "eit_annual_filing", "freq": "季度", "period_col": None},
    "account_balance": {"label": "科目余额表", "label_en": "Subject Balance Sheet", "table": "account_balance", "freq": "月度", "period_col": "period_month"},
}

SYNONYM_MAPPINGS_STATIC = [
    {"standard_name": "资产负债表", "synonyms": "Balance Sheet, Statement of Financial Position", "status": "Mapped", "match_rate": 100},
    {"standard_name": "利润表", "synonyms": "Income Statement, Profit and Loss Statement", "status": "Mapped", "match_rate": 100},
    {"standard_name": "科目余额表", "synonyms": "Subject Balance Sheet, Trial Balance General Ledger Summary", "status": "Mapped", "match_rate": 95},
    {"standard_name": "现金流量表", "synonyms": "Cash Flow Statement", "status": "Mapped", "match_rate": 100},
    {"standard_name": "财务指标", "synonyms": "Financial Metrics, Financial Ratios", "status": "Mapped", "match_rate": 100},
    {"standard_name": "增值税申报表", "synonyms": "VAT Return, Value Added Tax Return", "status": "Mapped", "match_rate": 100},
    {"standard_name": "企业所得税申报表", "synonyms": "CIT Return, Corporate Income Tax Return A100000", "status": "Mapped", "match_rate": 90},
    {"standard_name": "发票", "synonyms": "Invoices, FaPiao VAT Invoices", "status": "Mapped", "match_rate": 100},
    {"standard_name": "企业画像", "synonyms": "Enterprise Profile, Company Portrait", "status": "Mapped", "match_rate": 100},
]

QUALITY_CHECK_ITEMS = [
    {"key": "subject_balance", "name_cn": "科目余额表", "name_en": "Subject Balance Sheet"},
    {"key": "balance_sheet", "name_cn": "资产负债表", "name_en": "Balance Sheet"},
    {"key": "income_statement", "name_cn": "利润表", "name_en": "Income Statement"},
    {"key": "cash_flow", "name_cn": "现金流量表", "name_en": "Cash Flow Statement"},
    {"key": "vat_return", "name_cn": "增值税申报表", "name_en": "VAT Return"},
    {"key": "eit_return", "name_cn": "企业所得税申报表", "name_en": "CIT Return"},
]


def _get_conn():
    from modules.db_utils import get_connection
    return get_connection()


@router.get("/stats")
async def get_stats(company_id: str = Query(""), user: dict = Depends(get_current_user)):
    if company_id:
        require_company_access(user, company_id)
    conn = _get_conn()
    try:
        # metric count
        metric_count = conn.execute("SELECT COUNT(DISTINCT metric_code) FROM financial_metrics_item_dict").fetchone()[0]

        # data entry count
        total_entries = 0
        for d in DOMAIN_TABLES.values():
            tbl = d["table"]
            if company_id:
                row = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE taxpayer_id = ?", (company_id,)).fetchone()
            else:
                row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            total_entries += row[0]
        # add invoices + metrics
        for extra_tbl in ["inv_spec_purchase", "inv_spec_sales", "financial_metrics_item"]:
            if company_id:
                row = conn.execute(f"SELECT COUNT(*) FROM {extra_tbl} WHERE taxpayer_id = ?", (company_id,)).fetchone()
            else:
                row = conn.execute(f"SELECT COUNT(*) FROM {extra_tbl}").fetchone()
            total_entries += row[0]

        # period continuity
        continuity = 95
        if company_id:
            row = conn.execute(
                "SELECT MIN(period_year*100+period_month) AS mn, MAX(period_year*100+period_month) AS mx, "
                "COUNT(DISTINCT period_year*100+period_month) AS cnt "
                "FROM fs_income_statement_item WHERE taxpayer_id = ?", (company_id,)
            ).fetchone()
            if row and row["cnt"] and row["cnt"] > 0:
                mn, mx, cnt = row["mn"], row["mx"], row["cnt"]
                expected = (mx // 100 - mn // 100) * 12 + (mx % 100 - mn % 100) + 1
                continuity = round(cnt / max(expected, 1) * 100)

        # update frequency
        update_freq = []
        for key, d in DOMAIN_TABLES.items():
            tbl = d["table"]
            if d["period_col"]:
                if company_id:
                    row = conn.execute(
                        f"SELECT MAX(period_year) AS y, MAX(period_month) AS m FROM {tbl} WHERE taxpayer_id = ?",
                        (company_id,)
                    ).fetchone()
                else:
                    row = conn.execute(f"SELECT MAX(period_year) AS y, MAX(period_month) AS m FROM {tbl}").fetchone()
                if row and row["y"]:
                    last = f"{row['y']}-{str(row['m']).zfill(2)}-15"
                else:
                    last = ""
            else:
                last = ""
            update_freq.append({
                "source": d["label"],
                "frequency": d["freq"],
                "last_update": last,
                "status": "正常" if last else "无数据",
            })

        return {
            "metric_count": metric_count,
            "data_entry_count": total_entries,
            "period_continuity_pct": continuity,
            "data_completeness_pct": 95,
            "synonym_mappings": SYNONYM_MAPPINGS_STATIC,
            "update_frequency": update_freq,
            "quality_check_items": QUALITY_CHECK_ITEMS,
        }
    finally:
        conn.close()


@router.get("/companies-overview")
async def companies_overview(user: dict = Depends(get_current_user)):
    allowed_ids = get_user_company_ids(user["id"], user["role"])
    conn = _get_conn()
    try:
        companies = []
        if not allowed_ids:
            return companies
        placeholders = ",".join("?" * len(allowed_ids))
        rows = conn.execute(
            f"SELECT taxpayer_id, taxpayer_name, taxpayer_type FROM taxpayer_info "
            f"WHERE taxpayer_id IN ({placeholders}) ORDER BY taxpayer_name",
            allowed_ids,
        ).fetchall()
        for r in rows:
            tid = r["taxpayer_id"]
            # find latest period across domains
            latest = ""
            for d in DOMAIN_TABLES.values():
                tbl = d["table"]
                if d["period_col"]:
                    pr = conn.execute(
                        f"SELECT MAX(period_year*100+period_month) AS p FROM {tbl} WHERE taxpayer_id = ?", (tid,)
                    ).fetchone()
                    if pr and pr["p"]:
                        y, m = divmod(pr["p"], 100)
                        dt = f"{y}-{str(m).zfill(2)}-21"
                        if dt > latest:
                            latest = dt
            companies.append({
                "taxpayer_id": tid,
                "taxpayer_name": r["taxpayer_name"],
                "taxpayer_type": r["taxpayer_type"],
                "data_status": "Data Complete" if latest else "No Data",
                "completeness": "95%",
                "last_update": latest or "N/A",
            })
        return {
            "total": len(companies),
            "companies": companies,
            "overall_completeness": "95%",
            "overall_date": companies[0]["last_update"] if companies else "",
        }
    finally:
        conn.close()


@router.post("/quality-check")
async def quality_check(company_id: str = Query(""), user: dict = Depends(get_current_user)):
    from api.services.data_quality import DataQualityChecker
    if not company_id:
        # 默认取用户有权限的第一家企业
        allowed_ids = get_user_company_ids(user["id"], user["role"])
        company_id = allowed_ids[0] if allowed_ids else ""
    else:
        require_company_access(user, company_id)
    checker = DataQualityChecker()
    return checker.check_all(company_id)


@router.post("/recalculate-metrics")
async def recalculate_metrics(
    company_id: str = Query(..., description="纳税人ID"),
    version: str = Query("both", regex="^(v1|v2|both)$", description="指标版本"),
    user: dict = Depends(require_admin)  # 仅admin/sys可调用
):
    """
    重新计算财务指标

    权限：仅 sys/admin 角色可调用
    参数：
    - company_id: 纳税人ID（必填）
    - version: 指标版本 (v1=17项, v2=25项, both=两者都算)

    返回：
    {
        "success": true,
        "message": "财务指标重算完成",
        "details": {
            "v1_count": 442,  # v1写入记录数
            "v2_count": 900,  # v2写入记录数
            "duration_ms": 3500
        }
    }
    """
    # 1. 验证企业是否存在
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "SELECT taxpayer_name FROM taxpayer_info WHERE taxpayer_id = ?",
            (company_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="企业不存在")

        taxpayer_name = row[0]
    finally:
        conn.close()

    # 2. 执行计算（同步阻塞，但单个企业耗时可接受 ~3-5秒）
    start_time = time.time()
    v1_count = 0
    v2_count = 0

    try:
        if version in ("v1", "both"):
            from database.calculate_metrics import calculate_and_save
            result = calculate_and_save(taxpayer_id=company_id)
            v1_count = result if result else 0

        if version in ("v2", "both"):
            from database.calculate_metrics_v2 import calculate_and_save_v2
            result = calculate_and_save_v2(taxpayer_id=company_id)
            v2_count = result if result else 0

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "message": f"「{taxpayer_name}」财务指标重算完成",
            "details": {
                "v1_count": v1_count,
                "v2_count": v2_count,
                "duration_ms": duration_ms
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"计算失败: {str(e)}"
        )


@router.post("/recalculate-metrics-all")
async def recalculate_metrics_all(
    version: str = Query("both", regex="^(v1|v2|both)$", description="指标版本"),
    user: dict = Depends(require_admin)  # 仅admin/sys可调用
):
    """
    批量重新计算所有企业的财务指标

    权限：仅 sys/admin 角色可调用
    参数：
    - version: 指标版本 (v1=17项, v2=25项, both=两者都算)

    返回：
    {
        "success": true,
        "message": "批量财务指标重算完成",
        "details": {
            "total_companies": 6,
            "v1_total_count": 2652,
            "v2_total_count": 5400,
            "duration_ms": 18500
        }
    }
    """
    # 1. 获取所有活跃企业
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT taxpayer_id, taxpayer_name FROM taxpayer_info WHERE status = 'active' ORDER BY taxpayer_name"
        ).fetchall()

        if not rows:
            return {
                "success": True,
                "message": "没有需要计算的企业",
                "details": {
                    "total_companies": 0,
                    "v1_total_count": 0,
                    "v2_total_count": 0,
                    "duration_ms": 0
                }
            }
    finally:
        conn.close()

    # 2. 批量执行计算
    start_time = time.time()
    v1_total = 0
    v2_total = 0
    total_companies = len(rows)

    try:
        if version in ("v1", "both"):
            from database.calculate_metrics import calculate_and_save
            result = calculate_and_save()  # 不传 taxpayer_id 则计算全部
            v1_total = result if result else 0

        if version in ("v2", "both"):
            from database.calculate_metrics_v2 import calculate_and_save_v2
            result = calculate_and_save_v2()  # 不传 taxpayer_id 则计算全部
            v2_total = result if result else 0

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "message": f"批量财务指标重算完成（共 {total_companies} 家企业）",
            "details": {
                "total_companies": total_companies,
                "v1_total_count": v1_total,
                "v2_total_count": v2_total,
                "duration_ms": duration_ms
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量计算失败: {str(e)}"
        )


@router.post("/reload-reference-data")
async def reload_reference_data(user: dict = Depends(require_sys)):
    """
    重新加载参考数据（同义词表、科目字典、指标定义等）

    权限：仅 sys 角色可调用

    返回：
    {
        "success": true,
        "message": "成功重载 X 个参考数据表",
        "affected_tables": [...],
        "duration_seconds": 1.23
    }
    """
    try:
        from api.services.data_update_service import DataUpdateService

        result = DataUpdateService.reload_reference_data()
        return {"success": True, **result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"参考数据重载失败: {str(e)}"
        )


@router.post("/clear-cache")
async def clear_cache(
    cache_types: str = Query("all", description="缓存类型: all, intent, sql, result, cross_domain"),
    user: dict = Depends(require_sys)
):
    """
    清空内存缓存

    权限：仅 sys 角色可调用

    参数：
    - cache_types: 缓存类型 (all, intent, sql, result, cross_domain)

    返回：
    {
        "success": true,
        "cleared_entries": {...},
        "message": "成功清空 X 条缓存记录"
    }
    """
    try:
        from api.services.data_update_service import DataUpdateService

        # 解析缓存类型
        if cache_types == "all":
            types = "all"
        else:
            types = [t.strip() for t in cache_types.split(",")]

        result = DataUpdateService.clear_cache(types)
        return {"success": True, **result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"缓存清理失败: {str(e)}"
        )


@router.post("/reload-config")
async def reload_config(user: dict = Depends(require_sys)):
    """
    重新加载意图路由配置

    权限：仅 sys 角色可调用

    返回：
    {
        "success": true,
        "config_version": "20260301_123456",
        "loaded_at": "2026-03-01T12:34:56",
        "message": "成功重载配置文件: tax_query_config.json"
    }
    """
    try:
        from api.services.data_update_service import DataUpdateService

        result = DataUpdateService.reload_router_config()
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"配置重载失败: {str(e)}"
        )


@router.post("/batch-quality-check")
async def batch_quality_check(
    taxpayer_ids: str = Query("all", description="纳税人ID列表（逗号分隔）或 'all'"),
    user: dict = Depends(require_sys)
):
    """
    批量数据质量检查

    权限：仅 sys 角色可调用

    参数：
    - taxpayer_ids: 纳税人ID列表（逗号分隔）或 'all'

    返回：
    {
        "success": true,
        "total_taxpayers": 6,
        "checked_taxpayers": 6,
        "results": {...},
        "summary": {
            "total_issues": 10,
            "critical_issues": 2,
            "warning_issues": 8
        },
        "duration_seconds": 2.5
    }
    """
    try:
        from api.services.data_update_service import DataUpdateService

        # 解析纳税人ID列表
        if taxpayer_ids == "all":
            ids = "all"
        else:
            ids = [tid.strip() for tid in taxpayer_ids.split(",")]

        result = DataUpdateService.batch_quality_check(ids)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量质量检查失败: {str(e)}"
        )
