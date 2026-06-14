from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        query = select(User).where(User.phone == phone)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_badge_number(self, badge_number: str) -> Optional[User]:
        query = select(User).where(User.badge_number == badge_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_role(self, role: str, params: PaginationParams) -> tuple[List[User], int]:
        filters = [User.role == role]
        return await self.paginate(params, filters)

    async def list_active_inspectors(self) -> List[User]:
        query = select(User).where(
            and_(
                User.role == "inspector",
                User.is_active == True
            )
        ).order_by(User.cases_handled.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_onboarding_step(self, user_id: int, step: int) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if user:
            user.onboarding_step = step
            if step >= 5:
                user.is_new_user = False
            await self.db.flush()
            await self.db.refresh(user)
        return user

    async def increment_cases_handled(self, user_id: int) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.cases_handled = (user.cases_handled or 0) + 1
            await self.db.flush()

    async def update_last_login(self, user_id: int) -> None:
        user = await self.get_by_id(user_id)
        if user:
            from datetime import datetime
            user.last_login_at = datetime.utcnow()
            await self.db.flush()
