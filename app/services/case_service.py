from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point

from app.models.case import Case, Evidence
from app.models.user import User
from app.models.road_segment import RoadSegment
from app.repositories.case_repository import CaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.analysis_engine import ViolationAnalysisEngine
from app.services.enrichment_service import DataEnrichmentService
from app.schemas.case import CaseCard, CaseDetail, EvidenceInfo, VehicleEnrichment, CaseOperationInfo
from app.schemas.ingestion import RoadsideCaptureRequest, VehicleVideoRequest, PublicReportRequest
from app.core.logger import logger
from app.core.exception_handler import BusinessException, NotFoundException, BadRequestException


class CaseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_repo = CaseRepository(db)
        self.user_repo = UserRepository(db)
        self.vehicle_repo = VehicleRepository(db)
        self.analysis_engine = ViolationAnalysisEngine(db)
        self.enrichment_service = DataEnrichmentService(db)

    async def create_from_roadside_capture(self, request: RoadsideCaptureRequest) -> Case:
        case_number = await self.case_repo.generate_case_number()

        location = None
        if request.location:
            point = Point(request.location.lng, request.location.lat)
            location = from_shape(point, srid=4326)

        case = await self.case_repo.create(
            case_number=case_number,
            source_type="roadside_camera",
            source_id=request.camera_code,
            status="pending_review",
            priority="normal",
            severity_level="trivial",
            plate_number=request.plate_number,
            plate_confidence=request.plate_confidence,
            location=location,
            location_text=request.extra_data.get("location_text") if request.extra_data else None,
            violation_time=request.capture_time,
            violation_type="占道停车",
            extra_data=request.extra_data or {}
        )

        if request.image_url:
            await self.case_repo.add_evidence(
                case_id=case.id,
                type="image",
                file_type="image/jpeg",
                file_url=request.image_url,
                capture_time=request.capture_time,
                capture_device=request.camera_code
            )

        if request.video_url:
            await self.case_repo.add_evidence(
                case_id=case.id,
                type="video",
                file_type="video/mp4",
                file_url=request.video_url,
                capture_time=request.capture_time,
                capture_device=request.camera_code
            )

        await self._analyze_and_enrich_case(case)

        logger.info(f"Case created from roadside capture: {case_number}")
        return case

    async def create_from_vehicle_video(self, request: VehicleVideoRequest) -> Case:
        case_number = await self.case_repo.generate_case_number()

        location = None
        if request.location:
            point = Point(request.location.lng, request.location.lat)
            location = from_shape(point, srid=4326)

        duration = int((request.record_end_time - request.record_start_time).total_seconds())

        case = await self.case_repo.create(
            case_number=case_number,
            source_type="vehicle_video",
            source_id=request.device_id,
            status="pending_review",
            priority="normal",
            severity_level="trivial",
            plate_number=request.vehicle_plate,
            location=location,
            location_text=request.extra_data.get("location_text") if request.extra_data else None,
            violation_time=request.record_start_time,
            violation_duration=duration,
            violation_type="占道停车",
            extra_data=request.extra_data or {}
        )

        await self.case_repo.add_evidence(
            case_id=case.id,
            type="video",
            file_type="video/mp4",
            file_url=request.video_url,
            thumbnail_url=request.thumbnail_url,
            duration=duration,
            capture_time=request.record_start_time,
            capture_device=request.device_id
        )

        await self._analyze_and_enrich_case(case)

        logger.info(f"Case created from vehicle video: {case_number}")
        return case

    async def create_from_public_report(self, request: PublicReportRequest) -> Case:
        case_number = await self.case_repo.generate_case_number()

        point = Point(request.location.lng, request.location.lat)
        location = from_shape(point, srid=4326)

        extra_data = request.extra_data or {}
        extra_data.update({
            "reporter_phone": request.reporter_phone,
            "reporter_name": request.reporter_name,
            "report_description": request.description
        })

        case = await self.case_repo.create(
            case_number=case_number,
            source_type="public_report",
            status="pending_review",
            priority="normal",
            severity_level="trivial",
            plate_number=request.plate_number,
            location=location,
            location_text=request.location_text,
            violation_time=request.report_time,
            violation_type="占道停车",
            extra_data=extra_data
        )

        if request.evidence_images:
            for idx, img_url in enumerate(request.evidence_images):
                await self.case_repo.add_evidence(
                    case_id=case.id,
                    type="image",
                    file_type="image/jpeg",
                    file_url=img_url,
                    file_name=f"report_image_{idx + 1}.jpg",
                    capture_time=request.report_time,
                    capture_device="public_report"
                )

        if request.evidence_video:
            await self.case_repo.add_evidence(
                case_id=case.id,
                type="video",
                file_type="video/mp4",
                file_url=request.evidence_video,
                file_name="report_video.mp4",
                capture_time=request.report_time,
                capture_device="public_report"
            )

        await self._analyze_and_enrich_case(case)

        logger.info(f"Case created from public report: {case_number}")
        return case

    async def _analyze_and_enrich_case(self, case: Case) -> Case:
        road_segment = None
        if case.location:
            from app.models.road_segment import RoadSegment
            from geoalchemy2.functions import ST_DWithin, ST_Transform

            query = func.ST_DWithin(
                ST_Transform(RoadSegment.geometry, 3857),
                ST_Transform(case.location, 3857),
                50
            ).label("is_near")

            road_query = RoadSegment.__table__.select().where(query == True).order_by(
                func.ST_Distance(
                    ST_Transform(RoadSegment.geometry, 3857),
                    ST_Transform(case.location, 3857)
                ).asc()
            ).limit(1)

            result = await self.db.execute(road_query)
            road_row = result.mappings().first()
            if road_row:
                road_segment = RoadSegment(**dict(road_row))
                case.road_segment_id = road_segment.id
                case.road_name = road_segment.name
                case.district = road_segment.district
                case.area = road_segment.area

        case = await self.analysis_engine.enrich_case_data(case, road_segment)

        case = await self.enrichment_service.enrich_case(case.id)

        priority = self.analysis_engine.determine_priority(
            severity_level=case.severity_level,
            near_school=case.near_school,
            near_hospital=case.near_hospital,
            in_peak_hour=case.in_peak_hour,
            repeat_count=case.repeat_offense_count,
            same_location_count=case.same_location_count
        )
        case.priority = priority

        if road_segment:
            violation_code, violation_desc = self.analysis_engine.determine_violation_type(
                is_no_parking=road_segment.is_no_parking,
                is_affecting=case.is_affecting_traffic or False,
                lane_count=road_segment.lane_count or 2
            )
            case.violation_code = violation_code
            case.violation_type = violation_desc

            penalty = self.analysis_engine.generate_penalty_suggestion(
                violation_code=violation_code,
                severity_level=case.severity_level,
                is_affecting=case.is_affecting_traffic or False,
                repeat_count=case.repeat_offense_count
            )
            case.penalty_suggestion = penalty

        dissuasion = self.analysis_engine.generate_dissuasion_template(
            severity_level=case.severity_level,
            near_school=case.near_school,
            near_hospital=case.near_hospital,
            in_peak_hour=case.in_peak_hour,
            plate_number=case.plate_number or "该车辆",
            location_text=case.location_text or "此处"
        )
        case.dissuasion_template = dissuasion

        await self.db.flush()
        await self.db.refresh(case)

        return case

    async def review_case(
        self,
        case_id: int,
        action: str,
        operator_id: int,
        remark: Optional[str] = None,
        supplement_evidence: Optional[List[str]] = None
    ) -> Case:
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise NotFoundException(message="案件不存在")

        if case.status != "pending_review":
            raise BadRequestException(message="案件状态不允许此操作")

        now = datetime.utcnow()
        old_status = case.status

        if action == "dismiss":
            case.status = "dismissed"
            case.review_result = "dismissed"
            case.review_remark = remark
            case.closed_at = now
            case.handled_by = operator_id
            case.handled_at = now
        elif action == "file":
            case.status = "filed"
            case.review_result = "filed"
            case.review_remark = remark
            case.handled_by = operator_id
            case.handled_at = now
        elif action == "supplement":
            case.status = "pending_supplement"
            case.review_remark = remark
            case.reviewed_at = now

            if supplement_evidence:
                for url in supplement_evidence:
                    await self.case_repo.add_evidence(
                        case_id=case.id,
                        type="image",
                        file_url=url,
                        capture_time=now,
                        capture_device="inspector_app"
                    )
        else:
            raise BadRequestException(message=f"不支持的操作: {action}")

        case.reviewed_at = now

        await self.case_repo.add_operation(
            case_id=case.id,
            operator_id=operator_id,
            operation_type=f"review_{action}",
            from_status=old_status,
            to_status=case.status,
            remark=remark
        )

        if action != "supplement":
            await self.user_repo.increment_cases_handled(operator_id)

        await self.db.flush()
        await self.db.refresh(case)

        logger.info(f"Case {case.case_number} reviewed: {action} by user {operator_id}")
        return case

    async def get_case_list(
        self,
        params,
        current_user_id: int
    ) -> Tuple[List[CaseCard], int]:
        cases, total = await self.case_repo.query_cases(params, current_user_id)
        cards = [await self._to_case_card(case) for case in cases]
        return cards, total

    async def get_case_detail(self, case_id: int, current_user: User) -> CaseDetail:
        case = await self.case_repo.get_by_id(case_id, ["evidence", "vehicle", "road_segment"])
        if not case:
            raise NotFoundException(message="案件不存在")

        card = await self._to_case_card(case)
        evidence_list = [self._to_evidence_info(e) for e in case.evidence]

        operations = await self.case_repo.get_case_operations(case_id)
        operation_history = []
        for op in operations:
            operator = await self.user_repo.get_by_id(op.operator_id)
            operation_history.append(CaseOperationInfo(
                id=op.id,
                operation_type=op.operation_type,
                operator_id=op.operator_id,
                operator_name=operator.real_name if operator else None,
                from_status=op.from_status,
                to_status=op.to_status,
                remark=op.remark,
                created_at=op.created_at
            ))

        appeal_info = None
        if case.appeal_status != "none":
            from app.schemas.case import AppealInfo
            appeal_info = AppealInfo(
                appeal_status=case.appeal_status,
                appeal_requested_at=case.appeal_requested_at,
                appeal_reviewed_at=case.appeal_reviewed_at,
                appeal_result=case.appeal_result,
                appeal_remark=case.appeal_remark
            )

        return CaseDetail(
            **card.model_dump(),
            evidence_list=evidence_list,
            operation_history=operation_history,
            appeal_info=appeal_info,
            evidence_package_url=case.evidence_package_url,
            evidence_package_hash=case.evidence_package_hash
        )

    async def _to_case_card(self, case: Case) -> CaseCard:
        location = None
        if case.location:
            try:
                point = to_shape(case.location)
                location = {"lng": point.x, "lat": point.y}
            except Exception:
                pass

        vehicle_info = None
        if case.vehicle:
            vehicle_info = self.enrichment_service.get_vehicle_enrichment_data(case.vehicle)

        primary_evidence = None
        if case.evidence:
            primary = next((e for e in case.evidence if e.type == "image"), case.evidence[0])
            primary_evidence = self._to_evidence_info(primary)

        waiting_time = 0
        if case.status == "pending_review" and case.created_at:
            waiting_time = int((datetime.utcnow() - case.created_at).total_seconds())

        return CaseCard(
            id=case.id,
            case_number=case.case_number,
            source_type=case.source_type,
            status=case.status,
            priority=case.priority,
            severity_level=case.severity_level,
            plate_number=case.plate_number,
            plate_confidence=case.plate_confidence,
            vehicle_info=vehicle_info,
            location=location,
            location_text=case.location_text,
            road_name=case.road_name,
            district=case.district,
            violation_type=case.violation_type,
            violation_time=case.violation_time,
            violation_duration=case.violation_duration,
            is_affecting_traffic=case.is_affecting_traffic,
            traffic_impact_score=case.traffic_impact_score or 0,
            congestion_index=case.congestion_index or 0,
            near_school=case.near_school or False,
            near_hospital=case.near_hospital or False,
            in_peak_hour=case.in_peak_hour or False,
            repeat_offense_count=case.repeat_offense_count or 0,
            same_location_count=case.same_location_count or 0,
            primary_evidence=primary_evidence,
            evidence_count=len(case.evidence) if case.evidence else 0,
            penalty_suggestion=case.penalty_suggestion,
            dissuasion_template=case.dissuasion_template,
            assigned_to=case.assigned_to,
            assigned_at=case.assigned_at,
            created_at=case.created_at,
            waiting_time_seconds=waiting_time
        )

    def _to_evidence_info(self, evidence: Evidence) -> EvidenceInfo:
        return EvidenceInfo(
            id=evidence.id,
            type=evidence.type,
            file_type=evidence.file_type,
            file_url=evidence.file_url,
            thumbnail_url=evidence.thumbnail_url,
            file_size=evidence.file_size,
            capture_time=evidence.capture_time,
            is_verified=evidence.is_verified or False
        )
