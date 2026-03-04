#!/usr/bin/env python3
"""Test script for Dashboard functionality."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
from api.services.dashboard_service import DashboardService


async def test_dashboard():
    """Test dashboard service."""
    service = DashboardService()

    # Test with华兴科技
    company_id = "91310000MA1FL8XQ30"
    user = {"user_id": 1, "role": "enterprise"}

    print(f"Testing dashboard summary for company: {company_id}")
    print("-" * 60)

    result = await service.get_summary(company_id, user)

    print(f"Health Score: {result['health_score']}")
    print(f"\nTop Metrics ({len(result['top_metrics'])}):")
    for metric in result['top_metrics']:
        print(f"  - {metric['name']}: {metric['value']} (trend: {metric['trend']}%)")

    print(f"\nData Quality:")
    print(f"  Pass Rate: {result['data_quality_summary']['pass_rate']}%")
    print(f"  Critical Issues: {result['data_quality_summary']['critical_issues']}")

    print(f"\nRecent Activity ({len(result['recent_activity'])}):")
    for activity in result['recent_activity']:
        print(f"  - [{activity['route']}] {activity['description']}")

    print("\n" + "=" * 60)
    print("Dashboard test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_dashboard())
