from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.statistics import (
    DashboardResponse, DashboardOverview, HotSpotsResponse,
    ShiftHandoverResponse, NightMapResponse, DailyStatsResponse,
    HotSpotSegment, DailyClosureStats
)
from app.schemas.common import DataResponse
from app.services.statistics_service import StatisticsService
from app.core.security import get_current_active_user, require_role

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    data = await stats_service.get_dashboard_full_data()

    return DashboardResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=data["overview"],
        hot_spots=data["hot_spots"],
        recent_cases=data["recent_cases"]
    )


@router.get("/dashboard/overview", response_model=DataResponse[DashboardOverview])
async def get_dashboard_overview(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    overview = await stats_service.get_dashboard_overview()

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=overview
    )


@router.get("/hot-spots", response_model=HotSpotsResponse)
async def get_hot_spots(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    segments, total = await stats_service.get_hot_spots(limit=limit, days=days)

    return HotSpotsResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=segments,
        total=total,
        page=1,
        page_size=limit
    )


@router.get("/shift-handover", response_model=ShiftHandoverResponse)
async def get_shift_handover(
    request: Request,
    shift_type: str = Query("day", description="班次类型: day/night"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    items, start_time, end_time = await stats_service.get_shift_handover(shift_type)

    urgent_count = sum(
        1 for item in items
        if item.priority in ["critical", "high"]
    )

    return ShiftHandoverResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=items,
        shift_start_time=start_time,
        shift_end_time=end_time,
        total_items=len(items),
        urgent_count=urgent_count
    )


@router.get("/night-hotspots", response_model=NightMapResponse)
async def get_night_hotspots(
    request: Request,
    days: int = Query(30, ge=1, le=180, description="统计天数"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    points, extra_info = await stats_service.get_night_hotspot_map(days=days)

    return NightMapResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=points,
        date_range=extra_info["date_range"],
        total_night_violations=extra_info["total_night_violations"],
        peak_night_hour=extra_info["peak_night_hour"]
    )


@router.get("/daily-closure", response_model=DailyStatsResponse)
async def get_daily_closure_stats(
    request: Request,
    target_date: Optional[date] = Query(None, description="查询日期，默认今日"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stats_service = StatisticsService(db)
    stats = await stats_service.get_daily_closure_stats(target_date)

    return DailyStatsResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=stats
    )


@router.get("/realtime-stats", response_model=DataResponse)
async def get_realtime_stats(
    request: Request,
    current_user: User = Depends(require_role("admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository
    from datetime import datetime, timedelta

    case_repo = CaseRepository(db)
    now = datetime.now()
    start_of_hour = datetime(now.year, now.month, now.day, now.hour, 0, 0)
    start_of_day = datetime(now.year, now.month, now.day)

    stats = {
        "current_hour": {
            "received": await case_repo.count([Case.created_at >= start_of_hour]),
            "handled": await case_repo.count([Case.handled_at >= start_of_hour]),
            "pending": await case_repo.count([Case.status == "pending_review"])
        },
        "today": {
            "received": await case_repo.count([Case.created_at >= start_of_day]),
            "handled": await case_repo.count([Case.handled_at >= start_of_day]),
            "closed": await case_repo.count([Case.closed_at >= start_of_day])
        },
        "by_source": {
            "roadside_camera": await case_repo.count([
                Case.source_type == "roadside_camera",
                Case.created_at >= start_of_day
            ]),
            "vehicle_video": await case_repo.count([
                Case.source_type == "vehicle_video",
                Case.created_at >= start_of_day
            ]),
            "public_report": await case_repo.count([
                Case.source_type == "public_report",
                Case.created_at >= start_of_day
            ])
        },
        "by_priority": {
            "critical": await case_repo.count([
                Case.priority == "critical",
                Case.status.notin_(["closed", "dismissed"])
            ]),
            "high": await case_repo.count([
                Case.priority == "high",
                Case.status.notin_(["closed", "dismissed"])
            ]),
            "medium": await case_repo.count([
                Case.priority == "medium",
                Case.status.notin_(["closed", "dismissed"])
            ]),
            "normal": await case_repo.count([
                Case.priority == "normal",
                Case.status.notin_(["closed", "dismissed"])
            ]),
            "low": await case_repo.count([
                Case.priority == "low",
                Case.status.notin_(["closed", "dismissed"])
            ])
        }
    }

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=stats
    )
