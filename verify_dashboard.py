#!/usr/bin/env python3
"""Verification script for Dashboard implementation."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print("Dashboard Implementation Verification")
print("=" * 70)

# 1. Check frontend files
print("\n1. Checking frontend files...")
frontend_files = [
    "frontend/src/components/Dashboard/Dashboard.jsx",
    "frontend/src/components/Dashboard/Dashboard.module.css",
    "frontend/src/components/Dashboard/widgets/HealthScorecard.jsx",
    "frontend/src/components/Dashboard/widgets/TaxBurdenSummary.jsx",
    "frontend/src/components/Dashboard/widgets/DataQualityAlert.jsx",
    "frontend/src/components/Dashboard/widgets/QuickQueryShortcuts.jsx",
    "frontend/src/components/Dashboard/widgets/RecentQueries.jsx",
    "frontend/src/components/Dashboard/widgets/ClientPortfolio.jsx",
    "frontend/src/components/Dashboard/shared/WidgetCard.jsx",
    "frontend/src/components/Dashboard/shared/MetricDisplay.jsx",
    "frontend/src/components/Dashboard/hooks/useDashboardData.js",
]

for file in frontend_files:
    path = PROJECT_ROOT / file
    status = "✓" if path.exists() else "✗"
    print(f"  {status} {file}")

# 2. Check backend files
print("\n2. Checking backend files...")
backend_files = [
    "api/routes/dashboard.py",
    "api/services/dashboard_service.py",
]

for file in backend_files:
    path = PROJECT_ROOT / file
    status = "✓" if path.exists() else "✗"
    print(f"  {status} {file}")

# 3. Check App.jsx integration
print("\n3. Checking App.jsx integration...")
app_jsx = PROJECT_ROOT / "frontend/src/App.jsx"
if app_jsx.exists():
    content = app_jsx.read_text(encoding='utf-8')
    checks = [
        ("Dashboard import", "import Dashboard from"),
        ("Dashboard case", "case 'dashboard':"),
        ("Default page", "useState('dashboard')"),
    ]
    for check_name, check_str in checks:
        status = "✓" if check_str in content else "✗"
        print(f"  {status} {check_name}")

# 4. Check Sidebar.jsx integration
print("\n4. Checking Sidebar.jsx integration...")
sidebar_jsx = PROJECT_ROOT / "frontend/src/components/Sidebar/Sidebar.jsx"
if sidebar_jsx.exists():
    content = sidebar_jsx.read_text(encoding='utf-8')
    checks = [
        ("Dashboard menu enabled", "key: 'dashboard'" in content and "disabled: true" not in content),
    ]
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        print(f"  {status} {check_name}")

# 5. Check main.py router registration
print("\n5. Checking main.py router registration...")
main_py = PROJECT_ROOT / "api/main.py"
if main_py.exists():
    content = main_py.read_text(encoding='utf-8')
    checks = [
        ("Dashboard import", "dashboard"),
        ("Dashboard router", "dashboard.router"),
    ]
    for check_name, check_str in checks:
        status = "✓" if check_str in content else "✗"
        print(f"  {status} {check_name}")

# 6. Test dashboard service
print("\n6. Testing dashboard service...")
try:
    import asyncio
    from api.services.dashboard_service import DashboardService

    async def test():
        service = DashboardService()
        company_id = "91310000MA1FL8XQ30"
        user = {"user_id": 1, "role": "enterprise"}
        result = await service.get_summary(company_id, user)
        return result

    result = asyncio.run(test())
    print(f"  ✓ Dashboard service working")
    print(f"    - Health score: {result['health_score']}")
    print(f"    - Top metrics: {len(result['top_metrics'])}")
    print(f"    - Recent activity: {len(result['recent_activity'])}")
except Exception as e:
    print(f"  ✗ Dashboard service error: {e}")

# 7. Check frontend build
print("\n7. Checking frontend build...")
dist_dir = PROJECT_ROOT / "frontend/dist"
if dist_dir.exists():
    print(f"  ✓ Frontend build exists")
    index_html = dist_dir / "index.html"
    if index_html.exists():
        print(f"  ✓ index.html exists")
else:
    print(f"  ✗ Frontend build not found (run: cd frontend && npm run build)")

print("\n" + "=" * 70)
print("Verification complete!")
print("=" * 70)
print("\nNext steps:")
print("1. Start backend: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
print("2. Open browser: http://localhost:8000")
print("3. Login and verify dashboard is the landing page")
print("4. Test all 6 widgets with different user roles")
