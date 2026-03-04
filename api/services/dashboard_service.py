import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional
from config.settings import DB_PATH


class DashboardService:
    """Service for aggregating dashboard data."""

    def __init__(self):
        self.db_path = DB_PATH

    async def get_summary(self, company_id: str, user: dict) -> Dict[str, Any]:
        """
        Get aggregated dashboard summary for a company.

        Args:
            company_id: Taxpayer ID
            user: Current user dict

        Returns:
            Dict with health_score, top_metrics, data_quality_summary, recent_activity
        """
        if not company_id:
            return {
                "health_score": 0,
                "top_metrics": [],
                "data_quality_summary": {
                    "pass_rate": 0,
                    "critical_issues": 0
                },
                "recent_activity": [],
                "upcoming_deadlines": []
            }

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get top 3 financial metrics
            top_metrics = self._get_top_metrics(cursor, company_id)

            # Get recent activity from query log
            recent_activity = self._get_recent_activity(cursor, company_id)

            # Calculate health score (simplified version)
            health_score = self._calculate_health_score(cursor, company_id)

            return {
                "health_score": health_score,
                "top_metrics": top_metrics,
                "data_quality_summary": {
                    "pass_rate": 0,  # Would need to run quality check
                    "critical_issues": 0
                },
                "recent_activity": recent_activity,
                "upcoming_deadlines": []  # Phase 2 feature
            }
        finally:
            conn.close()

    def _get_top_metrics(self, cursor, company_id: str) -> list:
        """Get top 3 financial metrics with trends."""
        query = """
        SELECT
            metric_code,
            metric_value,
            evaluation_level,
            period_year,
            period_month
        FROM financial_metrics_item
        WHERE taxpayer_id = ?
            AND period_type = 'monthly'
        ORDER BY period_year DESC, period_month DESC
        LIMIT 10
        """

        cursor.execute(query, (company_id,))
        rows = cursor.fetchall()

        if not rows:
            return []

        # Get metric names
        cursor.execute("SELECT metric_code, metric_name FROM financial_metrics_item_dict")
        metric_names = {row[0]: row[1] for row in cursor.fetchall()}

        # Group by metric and calculate trend
        metrics_by_code = {}
        for row in rows:
            code = row['metric_code']
            if code not in metrics_by_code:
                metrics_by_code[code] = []
            metrics_by_code[code].append(float(row['metric_value']) if row['metric_value'] else 0)

        # Select top 3 metrics
        top_3 = []
        priority_metrics = ['roe', 'debt_ratio', 'gross_margin']

        for code in priority_metrics:
            if code in metrics_by_code and len(metrics_by_code[code]) >= 2:
                values = metrics_by_code[code]
                current = values[0]
                previous = values[1]
                trend = ((current - previous) / previous * 100) if previous != 0 else 0

                top_3.append({
                    "code": code,
                    "name": metric_names.get(code, code),
                    "value": current,
                    "trend": round(trend, 1)
                })

        return top_3[:3]

    def _get_recent_activity(self, cursor, company_id: str) -> list:
        """Get recent activity from query log."""
        query = """
        SELECT
            user_query,
            domain,
            created_at
        FROM user_query_log
        WHERE taxpayer_id = ?
        ORDER BY created_at DESC
        LIMIT 5
        """

        cursor.execute(query, (company_id,))
        rows = cursor.fetchall()

        activities = []
        for row in rows:
            activities.append({
                "type": "query",
                "description": row['user_query'][:50] + "..." if len(row['user_query']) > 50 else row['user_query'],
                "route": row['domain'] or 'unknown',
                "timestamp": row['created_at']
            })

        return activities

    def _calculate_health_score(self, cursor, company_id: str) -> int:
        """Calculate simplified health score based on latest metrics."""
        query = """
        SELECT
            metric_code,
            metric_value,
            evaluation_level
        FROM financial_metrics_item
        WHERE taxpayer_id = ?
            AND period_type = 'monthly'
        ORDER BY period_year DESC, period_month DESC
        LIMIT 5
        """

        cursor.execute(query, (company_id,))
        rows = cursor.fetchall()

        if not rows:
            return 0

        level_scores = {
            'excellent': 100,
            'good': 80,
            'normal': 60,
            'warning': 40,
            'risk': 20,
            'poor': 20
        }

        total_score = 0
        count = 0

        for row in rows:
            level = row['evaluation_level']
            if level:
                score = level_scores.get(level.lower(), 50)
                total_score += score
                count += 1

        return round(total_score / count) if count > 0 else 0
