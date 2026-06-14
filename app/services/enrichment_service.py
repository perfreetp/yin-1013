from typing import Optional, Dict, Any
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.case import Case
from app.models.vehicle import Vehicle
from app.repositories.case_repository import CaseRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.core.logger import logger
from app.core.exception_handler import BusinessException


class DataEnrichmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_repo = CaseRepository(db)
        self.vehicle_repo = VehicleRepository(db)

    async def recognize_license_plate(self, image_url: str) -> Optional[str]:
        if not image_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.OCR_SERVICE_URL,
                    json={"image_url": image_url}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return data.get("plate_number")
        except Exception as e:
            logger.warning(f"OCR service failed: {e}")

        return None

    async def fetch_vehicle_info(self, plate_number: str) -> Optional[Dict[str, Any]]:
        if not plate_number:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.VEHICLE_INFO_API_URL}/vehicle/query",
                    params={"plate_number": plate_number}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        return data.get("data")
        except Exception as e:
            logger.warning(f"Vehicle info API failed: {e}")

        return None

    async def fetch_congestion_index(
        self,
        lng: float,
        lat: float
    ) -> float:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.CONGESTION_API_URL}/index",
                    params={"lng": lng, "lat": lat}
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("index", 0.0))
        except Exception as e:
            logger.warning(f"Congestion API failed: {e}")

        return 0.0

    async def enrich_case(self, case_id: int) -> Case:
        case = await self.case_repo.get_by_id(case_id, ["evidence", "vehicle"])
        if not case:
            raise BusinessException(message="案件不存在")

        plate_number = case.plate_number

        if not plate_number and case.evidence:
            evidence = next((e for e in case.evidence if e.type == "image"), None)
            if evidence and not plate_number:
                plate_number = await self.recognize_license_plate(evidence.file_url)
                if plate_number:
                    case.plate_number = plate_number
                    case.plate_confidence = 0.85

        if plate_number:
            vehicle = await self.vehicle_repo.get_by_plate(plate_number)
            if not vehicle:
                vehicle_info = await self.fetch_vehicle_info(plate_number)
                if vehicle_info:
                    vehicle = await self.vehicle_repo.create_or_update(
                        plate_number=plate_number,
                        **vehicle_info
                    )

            if vehicle:
                case.vehicle_id = vehicle.id
                case.plate_number = vehicle.plate_number

                repeat_count = await self.case_repo.count_repeat_offenses(
                    plate_number, exclude_case_id=case_id
                )
                case.repeat_offense_count = repeat_count

        if case.location:
            from geoalchemy2.shape import to_shape
            point = to_shape(case.location)
            congestion_index = await self.fetch_congestion_index(point.x, point.y)
            case.congestion_index = congestion_index

            same_location_count = await self.case_repo.count_same_location(
                location_lng=point.x,
                location_lat=point.y,
                exclude_case_id=case_id
            )
            case.same_location_count = same_location_count

        await self.db.flush()
        await self.db.refresh(case)

        logger.info(f"Case {case.case_number} enriched successfully")
        return case

    def get_vehicle_enrichment_data(self, vehicle: Optional[Vehicle]) -> Dict[str, Any]:
        if not vehicle:
            return None

        return {
            "plate_number": vehicle.plate_number,
            "plate_color": vehicle.plate_color,
            "vehicle_type": vehicle.vehicle_type,
            "vehicle_brand": vehicle.vehicle_brand,
            "vehicle_model": vehicle.vehicle_model,
            "vehicle_color": vehicle.vehicle_color,
            "owner_name": vehicle.owner_name,
            "owner_phone": vehicle.owner_phone,
            "company_id": vehicle.company_id,
            "company_name": vehicle.company_name,
            "total_violations": vehicle.total_violations or 0,
            "total_penalties": vehicle.total_penalties or 0,
        }
