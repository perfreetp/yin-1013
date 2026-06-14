from datetime import timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse, TokenData, UserInfo,
    RefreshTokenRequest, ChangePasswordRequest
)
from app.schemas.common import DataResponse, BaseResponse
from app.repositories.user_repository import UserRepository
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    decode_token, get_current_active_user, hash_password
)
from app.core.exception_handler import (
    UnauthorizedException, BadRequestException, NotFoundException
)
from app.config import settings

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(login_data.username)

    if not user or not verify_password(login_data.password, user.password_hash):
        raise UnauthorizedException(message="用户名或密码错误")

    if not user.is_active:
        raise UnauthorizedException(message="账号已被禁用")

    await user_repo.update_last_login(user.id)

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )

    user_info = UserInfo.model_validate(user)

    return LoginResponse(
        code=200,
        message="登录成功",
        request_id=getattr(request.state, "request_id", None),
        data=TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
        user=user_info
    )


@router.post("/refresh", response_model=DataResponse[TokenData])
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    payload = decode_token(token_data.refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedException(message="无效的刷新令牌")

    user_id = int(payload.get("sub"))
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise UnauthorizedException(message="用户不存在或已被禁用")

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = create_refresh_token(
        subject=user.id,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return DataResponse(
        code=200,
        message="刷新成功",
        request_id=getattr(request.state, "request_id", None),
        data=TokenData(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise BadRequestException(message="原密码错误")

    user_repo = UserRepository(db)
    new_hash = hash_password(password_data.new_password)
    await user_repo.update(current_user.id, password_hash=new_hash)

    return BaseResponse(
        code=200,
        message="密码修改成功",
        request_id=getattr(request.state, "request_id", None)
    )


@router.get("/me", response_model=DataResponse[UserInfo])
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    user_info = UserInfo.model_validate(current_user)
    return DataResponse(
        code=200,
        message="获取成功",
        request_id=getattr(request.state, "request_id", None),
        data=user_info
    )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    return BaseResponse(
        code=200,
        message="登出成功",
        request_id=getattr(request.state, "request_id", None)
    )
