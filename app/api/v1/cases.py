from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.case import (
    CaseCardListResponse, CaseDetailResponse, CaseReviewRequest,
    CaseReviewResponse, CaseQueryParams, PenaltySuggestion, DissuasionTemplate,
    DataResponse, ListResponse
)
from app.services.case_service import CaseService
from app.services.analysis_engine import ViolationAnalysisEngine
from app.core.security import get_current_active_user, require_role
from app.core.exception_handler import NotFoundException
from app.core.logger import logger

router = APIRouter()


@router.get("/cards", response_model=CaseCardListResponse)
async def get_case_cards(
    request: Request,
    params: CaseQueryParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    case_service = CaseService(db)
    cards, total = await case_service.get_case_list(params, current_user.id)

    return CaseCardListResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=cards,
        total=total,
        page=params.page,
        page_size=params.page_size
    )


@router.get("/pending", response_model=CaseCardListResponse)
async def get_pending_cases(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.schemas.common import PaginationParams
    params = PaginationParams(page=page, page_size=page_size, order_by="priority")

    case_service = CaseService(db)
    from app.repositories.case_repository import CaseRepository
    case_repo = CaseRepository(db)

    cases, total = await case_repo.get_pending_cards(current_user.id, params)
    cards = [await case_service._to_case_card(case) for case in cases]

    return CaseCardListResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=cards,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    request: Request,
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    case_service = CaseService(db)
    case_detail = await case_service.get_case_detail(case_id, current_user)

    return CaseDetailResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=case_detail
    )


@router.post("/review", response_model=DataResponse[CaseReviewResponse])
async def review_case(
    request: Request,
    review_data: CaseReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"User {current_user.id} reviewing case {review_data.case_id}: "
        f"action={review_data.action}"
    )

    case_service = CaseService(db)
    case = await case_service.review_case(
        case_id=review_data.case_id,
        action=review_data.action,
        operator_id=current_user.id,
        remark=review_data.remark,
        supplement_evidence=review_data.supplement_evidence
    )

    return DataResponse(
        code=200,
        message=f"案件{review_data.action}成功",
        request_id=getattr(request.state, "request_id", None),
        data=CaseReviewResponse(
            case_id=case.id,
            status=case.status,
            action=review_data.action,
            handled_at=case.handled_at or case.reviewed_at
        )
    )


@router.post("/{case_id}/dismiss", response_model=DataResponse[CaseReviewResponse])
async def dismiss_case(
    request: Request,
    case_id: int,
    remark: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"User {current_user.id} dismissing case {case_id}")

    case_service = CaseService(db)
    case = await case_service.review_case(
        case_id=case_id,
        action="dismiss",
        operator_id=current_user.id,
        remark=remark
    )

    return DataResponse(
        code=200,
        message="案件已排除",
        request_id=getattr(request.state, "request_id", None),
        data=CaseReviewResponse(
            case_id=case.id,
            status=case.status,
            action="dismiss",
            handled_at=case.handled_at
        )
    )


@router.post("/{case_id}/file", response_model=DataResponse[CaseReviewResponse])
async def file_case(
    request: Request,
    case_id: int,
    remark: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"User {current_user.id} filing case {case_id}")

    case_service = CaseService(db)
    case = await case_service.review_case(
        case_id=case_id,
        action="file",
        operator_id=current_user.id,
        remark=remark
    )

    return DataResponse(
        code=200,
        message="案件已立案",
        request_id=getattr(request.state, "request_id", None),
        data=CaseReviewResponse(
            case_id=case.id,
            status=case.status,
            action="file",
            handled_at=case.handled_at
        )
    )


@router.post("/{case_id}/supplement", response_model=DataResponse[CaseReviewResponse])
async def supplement_evidence(
    request: Request,
    case_id: int,
    evidence_urls: list[str],
    remark: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"User {current_user.id} supplementing evidence for case {case_id}")

    case_service = CaseService(db)
    case = await case_service.review_case(
        case_id=case_id,
        action="supplement",
        operator_id=current_user.id,
        remark=remark,
        supplement_evidence=evidence_urls
    )

    return DataResponse(
        code=200,
        message="证据补充成功",
        request_id=getattr(request.state, "request_id", None),
        data=CaseReviewResponse(
            case_id=case.id,
            status=case.status,
            action="supplement",
            handled_at=case.reviewed_at
        )
    )


@router.get("/{case_id}/penalty-suggestion", response_model=DataResponse[PenaltySuggestion])
async def get_penalty_suggestion(
    request: Request,
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)

    if not case:
        raise NotFoundException(message="案件不存在")

    if not case.penalty_suggestion:
        analysis_engine = ViolationAnalysisEngine(db)
        suggestion = analysis_engine.generate_penalty_suggestion(
            violation_code=case.violation_code or "violation_code_003",
            severity_level=case.severity_level,
            is_affecting=case.is_affecting_traffic or False,
            repeat_count=case.repeat_offense_count or 0
        )
    else:
        suggestion = case.penalty_suggestion

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=PenaltySuggestion(**suggestion)
    )


@router.get("/{case_id}/dissuasion-template", response_model=DataResponse[DissuasionTemplate])
async def get_dissuasion_template(
    request: Request,
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)

    if not case:
        raise NotFoundException(message="案件不存在")

    if not case.dissuasion_template:
        analysis_engine = ViolationAnalysisEngine(db)
        template_content = analysis_engine.generate_dissuasion_template(
            severity_level=case.severity_level,
            near_school=case.near_school or False,
            near_hospital=case.near_hospital or False,
            in_peak_hour=case.in_peak_hour or False,
            plate_number=case.plate_number or "该车辆",
            location_text=case.location_text or "此处"
        )
    else:
        template_content = case.dissuasion_template

    template = DissuasionTemplate(
        template_id=f"template_{case.severity_level}",
        title=f"{case.severity_level}级劝离模板",
        content=template_content,
        scenario="占道停车劝离",
        severity_level=case.severity_level
    )

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=template
    )


@router.post("/{case_id}/assign", response_model=DataResponse)
async def assign_case(
    request: Request,
    case_id: int,
    inspector_id: int,
    current_user: User = Depends(require_role("admin", "supervisor")),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository
    from datetime import datetime

    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)

    if not case:
        raise NotFoundException(message="案件不存在")

    case.assigned_to = inspector_id
    case.assigned_at = datetime.utcnow()
    case.status = "assigned"

    await case_repo.add_operation(
        case_id=case_id,
        operator_id=current_user.id,
        operation_type="assign",
        from_status=case.status,
        to_status="assigned",
        remark=f"分配给稽查员{inspector_id}"
    )

    await db.flush()

    return DataResponse(
        code=200,
        message="案件分配成功",
        request_id=getattr(request.state, "request_id", None),
        data={"case_id": case_id, "assigned_to": inspector_id}
    )
