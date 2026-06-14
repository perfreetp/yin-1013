from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import LocationPoint, BaseResponse, DataResponse, ListResponse, PaginationParams


class RoadsideCaptureRequest(BaseModel):
    camera_code: str = Field(..., description="摄像头编号")
    capture_time: datetime = Field(..., description="抓拍时间")
    image_url: Optional[str] = Field(None, description="图片URL")
    video_url: Optional[str] = Field(None, description="视频URL")
    plate_number: Optional[str] = Field(None, description="识别车牌号")
    plate_confidence: Optional[float] = Field(None, description="车牌识别置信度")
    location: Optional[LocationPoint] = Field(None, description="位置坐标")
    vehicle_type: Optional[str] = Field(None, description="车辆类型")
    vehicle_color: Optional[str] = Field(None, description="车辆颜色")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class VehicleVideoRequest(BaseModel):
    device_id: str = Field(..., description="车载设备ID")
    vehicle_plate: str = Field(..., description="车牌号")
    record_start_time: datetime = Field(..., description="录像开始时间")
    record_end_time: datetime = Field(..., description="录像结束时间")
    video_url: str = Field(..., description="视频URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    location: Optional[LocationPoint] = Field(None, description="位置坐标")
    location_trace: Optional[List[LocationPoint]] = Field(None, description="行驶轨迹")
    speed: Optional[float] = Field(None, description="车速(km/h)")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class PublicReportRequest(BaseModel):
    reporter_phone: str = Field(..., description="举报人电话")
    reporter_name: Optional[str] = Field(None, description="举报人姓名")
    report_time: datetime = Field(..., description="举报时间")
    description: str = Field(..., description="举报描述", min_length=10)
    location: LocationPoint = Field(..., description="位置坐标")
    location_text: Optional[str] = Field(None, description="位置描述")
    plate_number: Optional[str] = Field(None, description="车牌号")
    evidence_images: Optional[List[str]] = Field(None, description="证据图片URL列表")
    evidence_video: Optional[str] = Field(None, description="证据视频URL")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class IngestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Field(..., description="案件ID")
    case_number: str = Field(..., description="案件编号")
    status: str = Field(..., description="状态")
    priority: str = Field(..., description="优先级")
    severity_level: str = Field(..., description="严重等级")
    created_at: datetime = Field(..., description="创建时间")


class IngestionDataResponse(DataResponse[IngestionResponse]):
    pass
