from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.statistics import OnboardingResponse, DataResponse
from app.schemas.common import BaseResponse
from app.services.onboarding_service import OnboardingService
from app.core.security import get_current_active_user

router = APIRouter()


@router.get("/guide", response_model=OnboardingResponse)
async def get_onboarding_guide(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    onboarding_service = OnboardingService(db)
    guide = onboarding_service.get_guide(current_user)

    return OnboardingResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=guide
    )


@router.post("/advance", response_model=OnboardingResponse)
async def advance_onboarding_step(
    request: Request,
    to_step: int = Query(..., ge=1, le=5, description="目标步骤"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    onboarding_service = OnboardingService(db)
    guide = await onboarding_service.advance_step(current_user.id, to_step)

    return OnboardingResponse(
        code=200,
        message=f"已推进到第{to_step}步",
        request_id=getattr(request.state, "request_id", None),
        data=guide
    )


@router.get("/step-hints/{step_id}", response_model=DataResponse)
async def get_step_hints(
    request: Request,
    step_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    onboarding_service = OnboardingService(db)
    hints = onboarding_service.get_step_hints(step_id)

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=hints
    )


@router.get("/processing-helper", response_model=DataResponse)
async def get_processing_helper(
    request: Request,
    case_priority: str = Query(..., description="案件优先级"),
    case_severity: str = Query(..., description="案件严重等级"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    onboarding_service = OnboardingService(db)
    helper = onboarding_service.get_processing_helper(case_priority, case_severity)

    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=helper
    )


@router.post("/complete", response_model=BaseResponse)
async def complete_onboarding(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    await user_repo.update_onboarding_step(current_user.id, 5)

    return BaseResponse(
        code=200,
        message="新手引导已完成，恭喜您！",
        request_id=getattr(request.state, "request_id", None)
    )


@router.post("/skip", response_model=BaseResponse)
async def skip_onboarding(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.update(current_user.id, is_new_user=False, onboarding_step=5)

    return BaseResponse(
        code=200,
        message="已跳过新手引导，可随时在帮助中心重新学习",
        request_id=getattr(request.state, "request_id", None)
    )
