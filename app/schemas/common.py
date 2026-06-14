from typing import Generic, TypeVar, Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class BaseResponse(BaseModel):
    code: int = Field(200, description="响应状态码")
    message: str = Field("success", description="响应消息")
    request_id: Optional[str] = Field(None, description="请求ID")


class DataResponse(BaseResponse, Generic[T]):
    data: T = Field(..., description="响应数据")


class ListResponse(BaseResponse, Generic[T]):
    data: List[T] = Field(..., description="响应数据列表")
    total: int = Field(..., description="总条数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页条数")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")
    order_by: Optional[str] = Field(None, description="排序字段")
    order_dir: Optional[str] = Field("desc", description="排序方向: asc/desc")


class LocationPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")


class TimeRange(BaseModel):
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")


class AuditLog(BaseModel):
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
