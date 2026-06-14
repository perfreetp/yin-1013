from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.common import DataResponse, BaseResponse
from app.services.evidence_service import EvidenceService
from app.core.security import get_current_active_user, require_role
from app.core.exception_handler import NotFoundException
from app.core.logger import logger

router = APIRouter()


@router.post("/{case_id}/package", response_model=DataResponse)
async def generate_evidence_package(
    request: Request,
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"User {current_user.id} generating evidence package for case {case_id}")

    evidence_service = EvidenceService(db)
    result = await evidence_service.generate_evidence_package(case_id)

    return DataResponse(
        code=200,
        message="证据包生成成功",
        request_id=getattr(request.state, "request_id", None),
        data={
            "package_url": result["package_url"],
            "package_hash": result["package_hash"],
            "file_size": result["file_size"],
            "evidence_count": result["evidence_count"],
            "generated_at": result["generated_at"].isoformat()
        }
    )


@router.get("/{case_id}/appeal-review", response_model=DataResponse)
async def get_appeal_review_data(
    request: Request,
    case_id: int,
    current_user: User = Depends(require_role("admin", "supervisor", "reviewer")),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository

    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id, ["evidence"])

    if not case:
        raise NotFoundException(message="案件不存在")

    evidence_service = EvidenceService(db)
    review_data = evidence_service.get_appeal_review_data(case)

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=review_data
    )


@router.post("/{case_id}/appeal", response_model=BaseResponse)
async def request_appeal(
    request: Request,
    case_id: int,
    appeal_remark: str,
    current_user: User = Depends(require_role("admin", "inspector")),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"User {current_user.id} requesting appeal for case {case_id}")

    evidence_service = EvidenceService(db)
    await evidence_service.request_appeal(case_id, appeal_remark)

    return BaseResponse(
        code=200,
        message="申诉已提交，等待审核",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/{case_id}/appeal/review", response_model=BaseResponse)
async def review_appeal(
    request: Request,
    case_id: int,
    approved: bool,
    review_remark: str,
    current_user: User = Depends(require_role("admin", "supervisor", "reviewer")),
    db: AsyncSession = Depends(get_db)
):
    logger.info(
        f"User {current_user.id} reviewing appeal for case {case_id}: "
        f"approved={approved}"
    )

    evidence_service = EvidenceService(db)
    await evidence_service.review_appeal(case_id, approved, review_remark)

    result_msg = "申诉已通过，案件将重新处理" if approved else "申诉已驳回"

    return BaseResponse(
        code=200,
        message=result_msg,
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/{case_id}/verify", response_model=BaseResponse)
async def verify_evidence(
    request: Request,
    case_id: int,
    evidence_id: int,
    is_verified: bool,
    verify_remark: Optional[str] = None,
    current_user: User = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.case_repository import CaseRepository
    from datetime import datetime

    case_repo = CaseRepository(db)
    evidence = await case_repo.evidence_repo.get_by_id(evidence_id)

    if not evidence:
        raise NotFoundException(message="证据不存在")

    if evidence.case_id != case_id:
        from app.core.exception_handler import BadRequestException
        raise BadRequestException(message="证据不属于该案件")

    evidence.is_verified = is_verified
    evidence.verified_at = datetime.utcnow()
    evidence.verified_by = current_user.id
    evidence.remark = verify_remark

    await case_repo.add_operation(
        case_id=case_id,
        operator_id=current_user.id,
        operation_type=f"evidence_verify_{'pass' if is_verified else 'reject'}",
        remark=f"证据{evidence_id}核验{'通过' if is_verified else '不通过'}: {verify_remark or ''}"
    )

    await db.flush()

    return BaseResponse(
        code=200,
        message=f"证据核验{'通过' if is_verified else '不通过'}",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/{case_id}/timeline", response_model=DataResponse)
async def get_case_timeline(
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

    evidence_service = EvidenceService(db)
    timeline = evidence_service._build_timeline(case)

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=timeline
    )
