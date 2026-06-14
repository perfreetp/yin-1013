from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import BaseResponse, DataResponse, ListResponse, LocationPoint


class HotSpotSegment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    road_segment_id: int = Field(..., description="路段ID")
    road_name: str = Field(..., description="路段名称")
    district: Optional[str] = Field(None, description="行政区")
    violation_count: int = Field(..., description="违章次数")
    hot_spot_score: float = Field(..., description="热点评分")
    priority_level: str = Field(..., description="优先级")
    center_point: Optional[LocationPoint] = Field(None, description="中心点坐标")
    trend: str = Field("stable", description="趋势: up/down/stable")


class ShiftHandoverItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Field(..., description="案件ID")
    case_number: str = Field(..., description="案件编号")
    plate_number: Optional[str] = Field(None, description="车牌号")
    violation_type: Optional[str] = Field(None, description="违章类型")
    location_text: Optional[str] = Field(None, description="位置描述")
    priority: str = Field(..., description="优先级")
    severity_level: str = Field(..., description="严重等级")
    status: str = Field(..., description="状态")
    handler_name: Optional[str] = Field(None, description="处理人")
    latest_operation_time: Optional[datetime] = Field(None, description="最后操作时间")
    waiting_minutes: int = Field(..., description="等待时长(分钟)")
    urgent_notes: Optional[str] = Field(None, description="紧急备注")


class NightHotspotPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location: LocationPoint = Field(..., description="位置坐标")
    location_text: str = Field(..., description="位置描述")
    road_name: Optional[str] = Field(None, description="路段名称")
    violation_count: int = Field(..., description="违章次数")
    peak_hour: str = Field(..., description="高发时段")
    most_common_violation: str = Field(..., description="最常见违章类型")
    heat_level: int = Field(..., description="热度等级 1-5")


class DailyClosureStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date = Field(..., description="日期")
    total_received: int = Field(..., description="当日接收")
    total_handled: int = Field(..., description="当日处理")
    total_closed: int = Field(..., description="当日闭环")
    closure_rate: float = Field(..., description="闭环率")
    average_handling_time_minutes: float = Field(..., description="平均处理时长(分钟)")
    pending_count: int = Field(..., description="待处理数量")


class DashboardOverview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    today_received: int = Field(..., description="今日接收")
    today_handled: int = Field(..., description="今日处理")
    today_closed: int = Field(..., description="今日闭环")
    today_closure_rate: float = Field(..., description="今日闭环率")
    pending_review: int = Field(..., description="待审核")
    pending_handling: int = Field(..., description="待处理")
    pending_closure: int = Field(..., description="待闭环")
    total_violations_week: int = Field(..., description="本周总违章")
    total_violations_month: int = Field(..., description="本月总违章")
    hot_spot_count: int = Field(..., description="热点路段数")
    high_priority_count: int = Field(..., description="高优先级案件数")


class ShiftHandoverResponse(DataResponse[List[ShiftHandoverItem]]):
    shift_start_time: datetime = Field(..., description="交班开始时间")
    shift_end_time: datetime = Field(..., description="交班结束时间")
    total_items: int = Field(..., description="总交接项数")
    urgent_count: int = Field(..., description="紧急项数")


class NightMapResponse(DataResponse[List[NightHotspotPoint]]):
    date_range: str = Field(..., description="统计日期范围")
    total_night_violations: int = Field(..., description="夜间违章总数")
    peak_night_hour: str = Field(..., description="夜间最高峰时段")


class HotSpotsResponse(ListResponse[HotSpotSegment]):
    pass


class DailyStatsResponse(DataResponse[DailyClosureStats]):
    pass


class DashboardResponse(DataResponse[DashboardOverview]):
    hot_spots: List[HotSpotSegment] = Field(..., description="Top热点路段")
    recent_cases: List[Dict[str, Any]] = Field(..., description="近期案件")


class OnboardingStep(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: int = Field(..., description="步骤ID")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤描述")
    icon: str = Field(..., description="图标")
    is_completed: bool = Field(..., description="是否已完成")
    is_current: bool = Field(..., description="是否当前步骤")
    action_hint: str = Field(..., description="操作提示")
    estimated_time_minutes: int = Field(..., description="预计时长(分钟)")


class OnboardingGuide(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="用户ID")
    is_new_user: bool = Field(..., description="是否新用户")
    current_step: int = Field(..., description="当前步骤")
    total_steps: int = Field(..., description="总步骤数")
    progress_percent: float = Field(..., description="完成进度百分比")
    steps: List[OnboardingStep] = Field(..., description="步骤列表")
    first_case_available: bool = Field(..., description="是否可以开始首单")
    encouragement_message: str = Field(..., description="鼓励语")


class OnboardingResponse(DataResponse[OnboardingGuide]):
    pass
