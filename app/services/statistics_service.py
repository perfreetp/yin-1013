from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape

from app.models.user import User
from app.models.case import Case
from app.repositories.case_repository import CaseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.statistics import (
    DashboardOverview,
    HotSpotSegment,
    ShiftHandoverItem,
    NightHotspotPoint,
    DailyClosureStats
)
from app.core.logger import logger


class StatisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_repo = CaseRepository(db)
        self.user_repo = UserRepository(db)

    async def get_dashboard_overview(self) -> DashboardOverview:
        today = datetime.now()
        start_of_today = datetime(today.year, today.month, today.day)
        end_of_today = start_of_today + timedelta(days=1)
        start_of_week = start_of_today - timedelta(days=today.weekday())
        start_of_month = datetime(today.year, today.month, 1)

        today_stats = await self.case_repo.get_daily_stats(today)

        pending_review = await self.case_repo.count([Case.status == "pending_review"])
        pending_handling = await self.case_repo.count([Case.status.in_(["filed", "pending_supplement"])])
        pending_closure = await self.case_repo.count([Case.status.in_(["handled", "pending_penalty"])])

        week_violations = await self.case_repo.count([
            Case.created_at >= start_of_week,
            Case.status != "dismissed"
        ])

        month_violations = await self.case_repo.count([
            Case.created_at >= start_of_month,
            Case.status != "dismissed"
        ])

        hot_spots = await self.case_repo.get_hot_spot_segments(limit=10)
        hot_spot_count = len([h for h in hot_spots if h["violation_count"] >= 5])

        high_priority_count = await self.case_repo.count([
            Case.priority.in_(["critical", "high"]),
            Case.status.notin_(["closed", "dismissed"])
        ])

        return DashboardOverview(
            today_received=today_stats["total_received"],
            today_handled=today_stats["total_handled"],
            today_closed=today_stats["total_closed"],
            today_closure_rate=today_stats["closure_rate"],
            pending_review=pending_review,
            pending_handling=pending_handling,
            pending_closure=pending_closure,
            total_violations_week=week_violations,
            total_violations_month=month_violations,
            hot_spot_count=hot_spot_count,
            high_priority_count=high_priority_count
        )

    async def get_hot_spots(self, limit: int = 20, days: int = 7) -> Tuple[List[HotSpotSegment], int]:
        raw_data = await self.case_repo.get_hot_spot_segments(limit=limit, days=days)
        segments = []

        for item in raw_data:
            center_point = None
            priority_level = "normal"
            if item["violation_count"] >= 20:
                priority_level = "critical"
            elif item["violation_count"] >= 10:
                priority_level = "high"
            elif item["violation_count"] >= 5:
                priority_level = "medium"

            hot_spot_score = min(
                item["violation_count"] * 5 + (item["avg_impact"] or 0) * 10,
                100
            )

            segments.append(HotSpotSegment(
                road_segment_id=item["road_segment_id"],
                road_name=item["road_name"],
                district=item["district"],
                violation_count=item["violation_count"],
                hot_spot_score=round(hot_spot_score, 1),
                priority_level=priority_level,
                center_point=center_point,
                trend="stable"
            ))

        return segments, len(segments)

    async def get_shift_handover(
        self,
        shift_type: str = "day"
    ) -> Tuple[List[ShiftHandoverItem], datetime, datetime]:
        now = datetime.now()

        if shift_type == "day":
            start_time = datetime(now.year, now.month, now.day, 8, 0, 0)
            end_time = datetime(now.year, now.month, now.day, 20, 0, 0)
        else:
            start_time = datetime(now.year, now.month, now.day, 20, 0, 0)
            end_time = datetime(now.year, now.month, now.day + 1, 8, 0, 0)

        cases = await self.case_repo.get_shift_handover(start_time, end_time)
        items = []

        for case in cases:
            handler = None
            if case.handled_by:
                handler = await self.user_repo.get_by_id(case.handled_by)

            waiting_minutes = 0
            if case.created_at:
                waiting_minutes = int((now - case.created_at).total_seconds() // 60)

            urgent_notes = []
            if case.priority in ["critical", "high"]:
                urgent_notes.append("高优先级")
            if case.is_affecting_traffic:
                urgent_notes.append("影响通行")
            if case.near_school:
                urgent_notes.append("学校附近")
            if waiting_minutes > 120:
                urgent_notes.append("等待超时")

            latest_operation = None
            operations = await self.case_repo.get_case_operations(case.id)
            if operations:
                latest_operation = operations[0].created_at

            items.append(ShiftHandoverItem(
                case_id=case.id,
                case_number=case.case_number,
                plate_number=case.plate_number,
                violation_type=case.violation_type,
                location_text=case.location_text,
                priority=case.priority,
                severity_level=case.severity_level,
                status=case.status,
                handler_name=handler.real_name if handler else None,
                latest_operation_time=latest_operation,
                waiting_minutes=waiting_minutes,
                urgent_notes="、".join(urgent_notes) if urgent_notes else None
            ))

        return items, start_time, end_time

    async def get_night_hotspot_map(self, days: int = 30) -> Tuple[List[NightHotspotPoint], Dict[str, Any]]:
        raw_data = await self.case_repo.get_night_hotspots(days=days)
        points = []
        total_count = 0
        hour_counts = {}

        for item in raw_data:
            total_count += item["violation_count"]

            hour = item["peak_hour"]
            hour_counts[hour] = hour_counts.get(hour, 0) + item["violation_count"]

            location = None
            if item["location"]:
                try:
                    point = to_shape(item["location"])
                    location = {"lng": point.x, "lat": point.y}
                except Exception:
                    pass

            heat_level = 1
            if item["violation_count"] >= 20:
                heat_level = 5
            elif item["violation_count"] >= 15:
                heat_level = 4
            elif item["violation_count"] >= 10:
                heat_level = 3
            elif item["violation_count"] >= 5:
                heat_level = 2

            points.append(NightHotspotPoint(
                location=location,
                location_text=item["location_text"] or "未知位置",
                road_name=item["road_name"],
                violation_count=item["violation_count"],
                peak_hour=f"{item['peak_hour']}:00-{int(item['peak_hour']) + 2}:00",
                most_common_violation=item["most_common_violation"] or "占道停车",
                heat_level=heat_level
            ))

        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else "22"

        extra_info = {
            "total_night_violations": total_count,
            "peak_night_hour": f"{peak_hour}:00-{int(peak_hour) + 2}:00",
            "date_range": f"最近{days}天"
        }

        return points, extra_info

    async def get_daily_closure_stats(self, target_date: date = None) -> DailyClosureStats:
        if target_date is None:
            target_date = datetime.now().date()

        dt = datetime(target_date.year, target_date.month, target_date.day)
        stats = await self.case_repo.get_daily_stats(dt)

        return DailyClosureStats(**stats)

    async def get_dashboard_full_data(self) -> Dict[str, Any]:
        overview = await self.get_dashboard_overview()
        hot_spots, _ = await self.get_hot_spots(limit=5, days=7)

        from app.models.case import Case
        recent_query = Case.__table__.select().order_by(Case.created_at.desc()).limit(10)
        result = await self.db.execute(recent_query)
        recent_cases = []
        for row in result.mappings().all():
            recent_cases.append({
                "id": row["id"],
                "case_number": row["case_number"],
                "plate_number": row["plate_number"],
                "status": row["status"],
                "priority": row["priority"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })

        return {
            "overview": overview,
            "hot_spots": hot_spots,
            "recent_cases": recent_cases
        }
