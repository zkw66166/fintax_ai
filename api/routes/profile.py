"""企业画像 API 路由"""
from fastapi import APIRouter, Depends, Query
from api.auth import get_current_user, require_company_access

router = APIRouter()


@router.get("/profile/{taxpayer_id}")
async def get_profile(taxpayer_id: str, year: int = Query(default=2025), user: dict = Depends(get_current_user)):
    """获取企业画像完整数据"""
    require_company_access(user, taxpayer_id)
    from modules.profile_service import get_company_profile
    return get_company_profile(taxpayer_id, year)
