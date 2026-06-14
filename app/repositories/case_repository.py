from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.case import Case, Evidence, CaseOperation
from app.repositories.base import BaseRepository
from app.schemas.case import CaseQueryParams
from app.schemas.common import PaginationParams


class CaseRepository(BaseRepository[Case]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Case)
        self.evidence_repo = BaseRepository(db, Evidence)
        self.operation_repo = BaseRepository(db, CaseOperation)

    async def generate_case_number(self) -> str:
        date_str = datetime.utcnow().strftime("%Y%m%d")
        prefix = f"TX{date_str}"

        query = select(func.max(Case.case_number)).where(Case.case_number.like(f"{prefix}%"))
        result = await self.db.execute(query)
        max_num = result.scalar_one_or_none()

        if max_num:
            sequence = int(max_num[-5:]) + 1
        else:
            sequence = 1

        return f"{prefix}{sequence:05d}"

    async def get_by_case_number(self, case_number: str) -> Optional[Case]:
        query = select(Case).where(Case.case_number == case_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def query_cases(
        self,
        params: CaseQueryParams,
        current_user_id: int = None
    ) -> Tuple[List[Case], int]:
        filters = []

        if params.status:
            filters.append(Case.status == params.status)
        if params.priority:
            filters.append(Case.priority == params.priority)
        if params.severity_level:
            filters.append(Case.severity_level == params.severity_level)
        if params.source_type:
            filters.append(Case.source_type == params.source_type)
        if params.plate_number:
            filters.append(Case.plate_number.ilike(f"%{params.plate_number}%"))
        if params.district:
            filters.append(Case.district == params.district)
        if params.road_name:
            filters.append(Case.road_name.ilike(f"%{params.road_name}%"))
        if params.near_school is not None:
            filters.append(Case.near_school == params.near_school)
        if params.near_hospital is not None:
            filters.append(Case.near_hospital == params.near_hospital)
        if params.in_peak_hour is not None:
            filters.append(Case.in_peak_hour == params.in_peak_hour)
        if params.violation_time_start:
            filters.append(Case.violation_time >= params.violation_time_start)
        if params.violation_time_end:
            filters.append(Case.violation_time <= params.violation_time_end)
        if params.assigned_to_me and current_user_id:
            filters.append(Case.assigned_to == current_user_id)
        if params.is_affecting_traffic is not None:
            filters.append(Case.is_affecting_traffic == params.is_affecting_traffic)

        query = select(Case)
        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.options(
            selectinload(Case.evidence),
            selectinload(Case.vehicle),
            selectinload(Case.road_segment)
        )

        if params.order_by == "priority":
            priority_order = func.array_position(
                func.cast(["critical", "high", "medium", "normal", "low"], func.array(Case.priority.type)),
                Case.priority
            )
            query = query.order_by(priority_order.asc(), Case.created_at.desc())
        else:
            query = query.order_by(
                func.array_position(
                    func.cast(["critical", "high", "medium", "normal", "low"], func.array(Case.priority.type)),
                    Case.priority
                ).asc(),
                Case.created_at.asc()
            )

        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        result = await self.db.execute(query)
        cases = list(result.scalars().all())

        return cases, total

    async def get_pending_cards(
        self,
        inspector_id: int,
        params: PaginationParams
    ) -> Tuple[List[Case], int]:
        filters = [
            Case.status == "pending_review",
            or_(Case.assigned_to == inspector_id, Case.assigned_to.is_(None))
        ]
        return await self.paginate(params, filters, ["evidence", "vehicle", "road_segment"])

    async def count_repeat_offenses(self, plate_number: str, exclude_case_id: int = None) -> int:
        if not plate_number:
            return 0
        filters = [
            Case.plate_number == plate_number,
            Case.status != "dismissed"
        ]
        if exclude_case_id:
            filters.append(Case.id != exclude_case_id)
        return await self.count(filters)

    async def count_same_location(
        self,
        location_lng: float,
        location_lat: float,
        radius_meters: float = 100,
        exclude_case_id: int = None,
        days: int = 30
    ) -> int:
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint

        point = func.ST_SetSRID(func.ST_MakePoint(location_lng, location_lat), 4326)

        query = select(func.count(Case.id)).where(
            and_(
                func.ST_DWithin(
                    func.ST_Transform(Case.location, 3857),
                    func.ST_Transform(point, 3857),
                    radius_meters
                ),
                Case.created_at >= datetime.utcnow() - timedelta(days=days),
                Case.status != "dismissed"
            )
        )
        if exclude_case_id:
            query = query.where(Case.id != exclude_case_id)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def add_evidence(self, case_id: int, **kwargs) -> Evidence:
        kwargs["case_id"] = case_id
        evidence = Evidence(**kwargs)
        self.db.add(evidence)
        await self.db.flush()
        await self.db.refresh(evidence)
        return evidence

    async def add_operation(self, case_id: int, operator_id: int, **kwargs) -> CaseOperation:
        kwargs["case_id"] = case_id
        kwargs["operator_id"] = operator_id
        operation = CaseOperation(**kwargs)
        self.db.add(operation)
        await self.db.flush()
        await self.db.refresh(operation)
        return operation

    async def get_case_operations(self, case_id: int) -> List[CaseOperation]:
        query = select(CaseOperation).where(
            CaseOperation.case_id == case_id
        ).order_by(CaseOperation.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_case_evidence(self, case_id: int) -> List[Evidence]:
        query = select(Evidence).where(
            Evidence.case_id == case_id
        ).order_by(Evidence.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_daily_stats(self, date: datetime) -> dict:
        start_of_day = datetime(date.year, date.month, date.day)
        end_of_day = start_of_day + timedelta(days=1)

        received = await self.count([Case.created_at >= start_of_day, Case.created_at < end_of_day])
        handled = await self.count([Case.handled_at >= start_of_day, Case.handled_at < end_of_day])
        closed = await self.count([Case.closed_at >= start_of_day, Case.closed_at < end_of_day])
        pending = await self.count([Case.status.notin_(["closed", "dismissed"])])

        query_avg = select(func.avg(
            func.extract('epoch', Case.handled_at) - func.extract('epoch', Case.created_at)
        )).where(
            Case.handled_at >= start_of_day,
            Case.handled_at < end_of_day,
            Case.handled_at.isnot(None)
        )
        result = await self.db.execute(query_avg)
        avg_seconds = result.scalar_one() or 0

        closure_rate = (closed / received * 100) if received > 0 else 0

        return {
            "date": date.date(),
            "total_received": received,
            "total_handled": handled,
            "total_closed": closed,
            "closure_rate": round(closure_rate, 2),
            "average_handling_time_minutes": round(avg_seconds / 60, 2),
            "pending_count": pending
        }

    async def get_hot_spot_segments(self, limit: int = 20, days: int = 7) -> List[dict]:
        query = select(
            Case.road_segment_id,
            Case.road_name,
            Case.district,
            func.count(Case.id).label("violation_count"),
            func.avg(Case.traffic_impact_score).label("avg_impact")
        ).where(
            Case.created_at >= datetime.utcnow() - timedelta(days=days),
            Case.road_segment_id.isnot(None),
            Case.status != "dismissed"
        ).group_by(
            Case.road_segment_id,
            Case.road_name,
            Case.district
        ).order_by(
            desc("violation_count"),
            desc("avg_impact")
        ).limit(limit)

        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def get_night_hotspots(self, days: int = 30) -> List[dict]:
        hour_col = func.extract('hour', Case.violation_time)
        night_condition = or_(hour_col >= 20, hour_col <= 5)

        query = select(
            Case.location,
            Case.location_text,
            Case.road_name,
            func.count(Case.id).label("violation_count"),
            func.mode().within_group(
                func.to_char(Case.violation_time, 'HH24')
            ).label("peak_hour"),
            func.mode().within_group(Case.violation_type).label("most_common_violation")
        ).where(
            Case.created_at >= datetime.utcnow() - timedelta(days=days),
            night_condition,
            Case.status != "dismissed"
        ).group_by(
            Case.location,
            Case.location_text,
            Case.road_name
        ).order_by(
            desc("violation_count")
        ).limit(50)

        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]

    async def get_shift_handover(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Case]:
        query = select(Case).where(
            or_(
                and_(Case.created_at >= start_time, Case.created_at < end_time),
                and_(Case.updated_at >= start_time, Case.updated_at < end_time, Case.status != "closed"),
                Case.status.notin_(["closed", "dismissed"])
            )
        ).order_by(
            func.array_position(
                func.cast(["critical", "high", "medium", "normal", "low"], func.array(Case.priority.type)),
                Case.priority
            ).asc(),
            Case.created_at.asc()
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())
