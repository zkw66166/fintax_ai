from fastapi import APIRouter, Depends, Query
from api.auth import get_current_user, require_company_access
from api.services.dashboard_service import DashboardService

router = APIRouter()
dashboard_service = DashboardService()


@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    company_id: str = Query(""),
    user: dict = Depends(get_current_user)
):
    """
    Get aggregated dashboard data for a company.
    Returns health score, top metrics, data quality summary, and recent activity.
    """
    if company_id:
        require_company_access(user, company_id)

    return await dashboard_service.get_summary(company_id, user)
