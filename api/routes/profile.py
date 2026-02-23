"""企业画像 API 路由"""
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/profile/{taxpayer_id}")
async def get_profile(taxpayer_id: str, year: int = Query(default=2025)):
    """获取企业画像完整数据"""
    from modules.profile_service import get_company_profile
    return get_company_profile(taxpayer_id, year)
