from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.common import LocationPoint, BaseResponse, DataResponse, ListResponse, PaginationParams


class EvidenceInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="证据ID")
    type: str = Field(..., description="证据类型: image/video/audio")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_url: str = Field(..., description="文件URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    file_size: Optional[int] = Field(None, description="文件大小(bytes)")
    capture_time: Optional[datetime] = Field(None, description="拍摄时间")
    is_verified: bool = Field(..., description="是否已核验")


class VehicleEnrichment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plate_number: str = Field(..., description="车牌号")
    plate_color: Optional[str] = Field(None, description="车牌颜色")
    vehicle_type: Optional[str] = Field(None, description="车辆类型")
    vehicle_brand: Optional[str] = Field(None, description="车辆品牌")
    vehicle_model: Optional[str] = Field(None, description="车辆型号")
    vehicle_color: Optional[str] = Field(None, description="车身颜色")
    owner_name: Optional[str] = Field(None, description="车主姓名")
    owner_phone: Optional[str] = Field(None, description="车主电话")
    company_id: Optional[int] = Field(None, description="所属公司ID")
    company_name: Optional[str] = Field(None, description="所属公司名称")
    total_violations: int = Field(0, description="总违章次数")
    total_penalties: int = Field(0, description="总处罚次数")


class CaseCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="案件ID")
    case_number: str = Field(..., description="案件编号")
    source_type: str = Field(..., description="来源类型: roadside_camera/vehicle_video/public_report")
    status: str = Field(..., description="状态")
    priority: str = Field(..., description="优先级")
    severity_level: str = Field(..., description="严重等级")

    plate_number: Optional[str] = Field(None, description="车牌号")
    plate_confidence: Optional[float] = Field(None, description="车牌识别置信度")
    vehicle_info: Optional[VehicleEnrichment] = Field(None, description="车辆补充信息")

    location: Optional[LocationPoint] = Field(None, description="位置坐标")
    location_text: Optional[str] = Field(None, description="位置描述")
    road_name: Optional[str] = Field(None, description="路段名称")
    district: Optional[str] = Field(None, description="行政区")

    violation_type: Optional[str] = Field(None, description="违章类型")
    violation_time: datetime = Field(..., description="违章时间")
    violation_duration: Optional[int] = Field(None, description="违章时长(秒)")

    is_affecting_traffic: Optional[bool] = Field(None, description="是否影响通行")
    traffic_impact_score: float = Field(0, description="交通影响分数")
    congestion_index: float = Field(0, description="附近拥堵指数")
    near_school: bool = Field(False, description="是否靠近学校")
    near_hospital: bool = Field(False, description="是否靠近医院")
    in_peak_hour: bool = Field(False, description="是否在高峰期")

    repeat_offense_count: int = Field(0, description="历史告警次数")
    same_location_count: int = Field(0, description="同点位复犯次数")

    primary_evidence: Optional[EvidenceInfo] = Field(None, description="主要证据")
    evidence_count: int = Field(0, description="证据数量")

    penalty_suggestion: Optional[Dict[str, Any]] = Field(None, description="处罚建议")
    dissuasion_template: Optional[str] = Field(None, description="劝离模板")

    assigned_to: Optional[int] = Field(None, description="分配给")
    assigned_at: Optional[datetime] = Field(None, description="分配时间")

    created_at: datetime = Field(..., description="创建时间")
    waiting_time_seconds: int = Field(0, description="等待时长(秒)")


class CaseCardListResponse(ListResponse[CaseCard]):
    pass


class CaseDetail(CaseCard):
    evidence_list: List[EvidenceInfo] = Field(default_factory=list, description="证据列表")
    operation_history: List["CaseOperationInfo"] = Field(default_factory=list, description="操作历史")
    appeal_info: Optional["AppealInfo"] = Field(None, description="申诉信息")
    evidence_package_url: Optional[str] = Field(None, description="证据包下载URL")
    evidence_package_hash: Optional[str] = Field(None, description="证据包哈希")


class CaseDetailResponse(DataResponse[CaseDetail]):
    pass


class CaseOperationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="操作ID")
    operation_type: str = Field(..., description="操作类型")
    operator_id: int = Field(..., description="操作人ID")
    operator_name: Optional[str] = Field(None, description="操作人姓名")
    from_status: Optional[str] = Field(None, description="原状态")
    to_status: Optional[str] = Field(None, description="目标状态")
    remark: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(..., description="操作时间")


class AppealInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appeal_status: str = Field(..., description="申诉状态")
    appeal_requested_at: Optional[datetime] = Field(None, description="申诉申请时间")
    appeal_reviewed_at: Optional[datetime] = Field(None, description="申诉审核时间")
    appeal_result: Optional[str] = Field(None, description="申诉结果")
    appeal_remark: Optional[str] = Field(None, description="申诉备注")


class CaseReviewRequest(BaseModel):
    case_id: int = Field(..., description="案件ID")
    action: str = Field(..., description="操作: dismiss(排除)/file(立案)/supplement(补证)")
    remark: Optional[str] = Field(None, description="备注")
    supplement_evidence: Optional[List[str]] = Field(None, description="补充证据URL列表")


class CaseReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: int = Field(..., description="案件ID")
    status: str = Field(..., description="新状态")
    action: str = Field(..., description="执行的操作")
    handled_at: datetime = Field(..., description="处理时间")


class CaseQueryParams(PaginationParams):
    status: Optional[str] = Field(None, description="案件状态")
    priority: Optional[str] = Field(None, description="优先级")
    severity_level: Optional[str] = Field(None, description="严重等级")
    source_type: Optional[str] = Field(None, description="来源类型")
    plate_number: Optional[str] = Field(None, description="车牌号")
    district: Optional[str] = Field(None, description="行政区")
    road_name: Optional[str] = Field(None, description="路段名称")
    near_school: Optional[bool] = Field(None, description="是否靠近学校")
    near_hospital: Optional[bool] = Field(None, description="是否靠近医院")
    in_peak_hour: Optional[bool] = Field(None, description="是否高峰期")
    violation_time_start: Optional[datetime] = Field(None, description="违章开始时间")
    violation_time_end: Optional[datetime] = Field(None, description="违章结束时间")
    assigned_to_me: Optional[bool] = Field(None, description="仅看分配给我的")
    is_affecting_traffic: Optional[bool] = Field(None, description="是否影响交通")


class PenaltySuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    violation_code: str = Field(..., description="违章代码")
    violation_name: str = Field(..., description="违章名称")
    penalty_type: str = Field(..., description="处罚类型: fine/points/both")
    fine_amount: Optional[int] = Field(None, description="罚款金额(元)")
    points: Optional[int] = Field(None, description="扣分")
    description: str = Field(..., description="处罚说明")
    legal_basis: str = Field(..., description="法律依据")


class DissuasionTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: str = Field(..., description="模板ID")
    title: str = Field(..., description="模板标题")
    content: str = Field(..., description="劝离话术内容")
    scenario: str = Field(..., description="适用场景")
    severity_level: str = Field(..., description="适用严重等级")


CaseDetail.model_rebuild()
