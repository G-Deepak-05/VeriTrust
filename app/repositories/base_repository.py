"""
Generic async base repository — provides CRUD operations for any SQLAlchemy model.
"""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository[ModelType: Base]:
    """
    Generic async CRUD repository.

    Subclass and set `model` class attribute to use.
    """

    model: type[ModelType]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: UUID) -> ModelType | None:
        """Get a single record by primary key."""
        model_any: Any = self.model
        result = await self.db.execute(select(self.model).where(model_any.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        filters: list | None = None,
        offset: int = 0,
        limit: int = 20,
        order_by=None,
    ) -> tuple[list[ModelType], int]:
        """
        Get paginated list of records.

        Returns:
            (items, total_count)
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        if order_by is not None:
            query = query.order_by(order_by)
        else:
            model_any: Any = self.model
            query = query.order_by(model_any.created_at.desc())

        total = await self.db.scalar(count_query) or 0
        result = await self.db.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def create(self, **kwargs: Any) -> ModelType:
        """Create and persist a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """Update fields on an existing record."""
        for key, value in kwargs.items():
            setattr(instance, key, value)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        await self.db.delete(instance)
        await self.db.flush()

    async def count(self, *filters) -> int:
        """Count records matching filters."""
        query = select(func.count()).select_from(self.model)
        for f in filters:
            query = query.where(f)
        return await self.db.scalar(query) or 0
