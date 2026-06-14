from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import BaseResponse, DataResponse


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=6, max_length=100)


class TokenData(BaseModel):
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    real_name: Optional[str] = Field(None, description="真实姓名")
    phone: Optional[str] = Field(None, description="手机号")
    badge_number: Optional[str] = Field(None, description="警号")
    role: str = Field(..., description="角色")
    department: Optional[str] = Field(None, description="部门")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    is_new_user: bool = Field(..., description="是否新用户")
    onboarding_step: int = Field(..., description="新手引导进度")
    cases_handled: int = Field(..., description="处理案件数")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")


class LoginResponse(DataResponse[TokenData]):
    user: UserInfo = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码", min_length=6)
    new_password: str = Field(..., description="新密码", min_length=6)
