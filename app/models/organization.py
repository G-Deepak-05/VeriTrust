"""
Organization model.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.user import User


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", lazy="select"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="organization", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug}>"
