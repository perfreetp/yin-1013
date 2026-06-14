from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import Vehicle
from app.models.company import Company
from app.repositories.base import BaseRepository


class VehicleRepository(BaseRepository[Vehicle]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Vehicle)

    async def get_by_plate(self, plate_number: str) -> Optional[Vehicle]:
        query = select(Vehicle).where(Vehicle.plate_number == plate_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_or_update(self, plate_number: str, **kwargs) -> Vehicle:
        vehicle = await self.get_by_plate(plate_number)
        if vehicle:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(vehicle, key, value)
            await self.db.flush()
            await self.db.refresh(vehicle)
        else:
            kwargs["plate_number"] = plate_number
            vehicle = await self.create(**kwargs)
        return vehicle

    async def increment_violation_count(self, vehicle_id: int) -> None:
        vehicle = await self.get_by_id(vehicle_id)
        if vehicle:
            vehicle.total_violations = (vehicle.total_violations or 0) + 1
            await self.db.flush()

    async def get_vehicle_history(self, plate_number: str, limit: int = 20) -> List[dict]:
        from app.models.case import Case
        query = select(
            Case.id,
            Case.case_number,
            Case.violation_type,
            Case.violation_time,
            Case.status,
            Case.severity_level,
            Case.road_name,
            Case.location_text
        ).where(
            Case.plate_number == plate_number
        ).order_by(
            Case.violation_time.desc()
        ).limit(limit)

        result = await self.db.execute(query)
        return [dict(row) for row in result.mappings().all()]


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Company)

    async def get_by_name(self, name: str) -> Optional[Company]:
        query = select(Company).where(Company.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_uscc(self, unified_social_credit: str) -> Optional[Company]:
        query = select(Company).where(Company.unified_social_credit == unified_social_credit)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def increment_violation_count(self, company_id: int) -> None:
        company = await self.get_by_id(company_id)
        if company:
            company.total_violations = (company.total_violations or 0) + 1
            await self.db.flush()

    async def get_company_vehicles(self, company_id: int) -> List[Vehicle]:
        query = select(Vehicle).where(Vehicle.company_id == company_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
