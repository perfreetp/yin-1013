from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.db.session import get_db
from app.models.user import User
from app.schemas.ingestion import (
    RoadsideCaptureRequest, VehicleVideoRequest, PublicReportRequest,
    IngestionResponse, IngestionDataResponse,
    BatchIngestionResult, BatchIngestionResponse, BatchIngestionDataResponse
)
from app.schemas.common import BaseResponse
from app.services.case_service import CaseService
from app.core.security import get_current_active_user, require_role
from app.core.logger import logger
from app.core.exception_handler import BadRequestException

router = APIRouter()

SUPPORTED_SOURCES = ["roadside_camera", "vehicle_video", "public_report"]


@router.post("/roadside-capture", response_model=IngestionDataResponse)
async def receive_roadside_capture(
    request: Request,
    capture_data: RoadsideCaptureRequest,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received roadside capture from camera: {capture_data.camera_code}")

    case_service = CaseService(db)
    case = await case_service.create_from_roadside_capture(capture_data)

    return IngestionDataResponse(
        code=200,
        message="路侧抓拍数据接收成功",
        request_id=getattr(request.state, "request_id", None),
        data=IngestionResponse(
            case_id=case.id,
            case_number=case.case_number,
            status=case.status,
            priority=case.priority,
            severity_level=case.severity_level,
            created_at=case.created_at
        )
    )


@router.post("/vehicle-video", response_model=IngestionDataResponse)
async def receive_vehicle_video(
    request: Request,
    video_data: VehicleVideoRequest,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received vehicle video from device: {video_data.device_id}, plate: {video_data.vehicle_plate}")

    case_service = CaseService(db)
    case = await case_service.create_from_vehicle_video(video_data)

    return IngestionDataResponse(
        code=200,
        message="车载视频数据接收成功",
        request_id=getattr(request.state, "request_id", None),
        data=IngestionResponse(
            case_id=case.id,
            case_number=case.case_number,
            status=case.status,
            priority=case.priority,
            severity_level=case.severity_level,
            created_at=case.created_at
        )
    )


@router.post("/public-report", response_model=IngestionDataResponse)
async def receive_public_report(
    request: Request,
    report_data: PublicReportRequest,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Received public report from: {report_data.reporter_phone}")

    case_service = CaseService(db)
    case = await case_service.create_from_public_report(report_data)

    return IngestionDataResponse(
        code=200,
        message="群众举报接收成功，感谢您的参与",
        request_id=getattr(request.state, "request_id", None),
        data=IngestionResponse(
            case_id=case.id,
            case_number=case.case_number,
            status=case.status,
            priority=case.priority,
            severity_level=case.severity_level,
            created_at=case.created_at
        )
    )


@router.post("/batch-ingestion", response_model=BatchIngestionDataResponse)
async def batch_ingestion(
    request: Request,
    items: list[dict],
    current_user: User = Depends(require_role("admin", "inspector")),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Batch ingestion requested by user {current_user.id}, count: {len(items)}")

    case_service = CaseService(db)
    results = []
    success_count = 0
    failed_count = 0

    for idx, item in enumerate(items):
        source_type = item.get("source_type")
        result = BatchIngestionResult(
            index=idx,
            source_type=source_type,
            success=False,
            error_reason=None
        )

        try:
            if source_type not in SUPPORTED_SOURCES:
                result.error_reason = f"不支持的来源类型: {source_type}，支持的类型: {', '.join(SUPPORTED_SOURCES)}"
                failed_count += 1
                results.append(result)
                continue

            try:
                if source_type == "roadside_camera":
                    req = RoadsideCaptureRequest(**item)
                    case = await case_service.create_from_roadside_capture(req)
                elif source_type == "vehicle_video":
                    req = VehicleVideoRequest(**item)
                    case = await case_service.create_from_vehicle_video(req)
                elif source_type == "public_report":
                    req = PublicReportRequest(**item)
                    case = await case_service.create_from_public_report(req)

                if case and case.id:
                    result.success = True
                    result.case_id = case.id
                    result.case_number = case.case_number
                    result.error_reason = None
                    success_count += 1
                else:
                    result.error_reason = "案件创建失败，未生成有效ID"
                    failed_count += 1

            except ValidationError as e:
                error_msgs = []
                for err in e.errors():
                    field = ".".join(str(loc) for loc in err["loc"])
                    error_msgs.append(f"{field}: {err['msg']}")
                result.error_reason = "数据验证失败: " + "; ".join(error_msgs)
                failed_count += 1

            except BadRequestException as e:
                result.error_reason = f"业务校验失败: {e.message}"
                failed_count += 1

        except Exception as e:
            result.error_reason = f"系统异常: {str(e)}"
            failed_count += 1
            logger.error(f"Batch ingestion failed for item {idx}: {e}")

        results.append(result)

    response_data = BatchIngestionResponse(
        total_count=len(items),
        success_count=success_count,
        failed_count=failed_count,
        results=results
    )

    return BatchIngestionDataResponse(
        code=200,
        message=f"批量接入完成：成功{success_count}条，失败{failed_count}条",
        request_id=getattr(request.state, "request_id", None),
        data=response_data
    )
