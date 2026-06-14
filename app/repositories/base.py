from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import Base
from app.schemas.common import PaginationParams

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int, with_relations: List[str] = None) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == id)
        if with_relations:
            for rel in with_relations:
                query = query.options(selectinload(getattr(self.model, rel)))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        query = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.rowcount > 0

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def paginate(
        self,
        params: PaginationParams,
        filters: Optional[List] = None,
        with_relations: List[str] = None
    ) -> tuple[List[ModelType], int]:
        query = select(self.model)

        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        if params.order_by:
            order_column = getattr(self.model, params.order_by, None)
            if order_column is not None:
                if params.order_dir and params.order_dir.lower() == "desc":
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column.asc())
        else:
            query = query.order_by(self.model.created_at.desc())

        if with_relations:
            for rel in with_relations:
                query = query.options(selectinload(getattr(self.model, rel)))

        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def count(self, filters: Optional[List] = None) -> int:
        query = select(func.count(self.model.id))
        if filters:
            query = query.where(and_(*filters))
        result = await self.db.execute(query)
        return result.scalar_one()

    async def exists(self, filters: List) -> bool:
        query = select(func.count(self.model.id)).where(and_(*filters))
        result = await self.db.execute(query)
        return result.scalar_one() > 0
