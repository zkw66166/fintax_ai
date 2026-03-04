"""Company list endpoint."""
from fastapi import APIRouter, Depends
from api.auth import get_current_user, get_user_company_ids, get_default_companies_for_role, ROLES
from modules.db_utils import get_connection

router = APIRouter()


@router.get("/companies/by-role/{role}")
async def get_companies_by_role(role: str, user: dict = Depends(get_current_user)):
    """返回指定角色的默认企业列表（含企业详情）。非 admin 返回交集。"""
    if role not in ROLES:
        return []
    default_ids = get_default_companies_for_role(role, user["id"], user["role"])
    if not default_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(default_ids))
    rows = conn.execute(
        f"SELECT taxpayer_id, taxpayer_name, taxpayer_type FROM taxpayer_info "
        f"WHERE taxpayer_id IN ({placeholders}) ORDER BY taxpayer_name",
        default_ids,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/companies")
async def list_companies(user: dict = Depends(get_current_user)):
    allowed_ids = get_user_company_ids(user["id"], user["role"])
    if not allowed_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(allowed_ids))
    rows = conn.execute(
        f"SELECT taxpayer_id, taxpayer_name, taxpayer_type FROM taxpayer_info "
        f"WHERE taxpayer_id IN ({placeholders}) ORDER BY taxpayer_name",
        allowed_ids,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
