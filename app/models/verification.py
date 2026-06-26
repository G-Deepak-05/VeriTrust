"""
Verification Request and Result models.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSONB_TYPE, Base
from app.models.mixins import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class VerificationRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "verification_requests"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Input fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    # Relationship to result
    result: Mapped["VerificationResult | None"] = relationship(
        "VerificationResult", back_populates="request", uselist=False, lazy="select"
    )

    def __repr__(self) -> str:
        return f"<VerificationRequest id={self.id} email={self.email} status={self.status}>"


class VerificationResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "verification_results"

    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reasons: Mapped[list] = mapped_column(JSONB_TYPE, default=list, nullable=False)
    processing_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_breakdown: Mapped[dict] = mapped_column(JSONB_TYPE, default=dict, nullable=False)

    # Relationship back to request
    request: Mapped["VerificationRequest"] = relationship(
        "VerificationRequest", back_populates="result", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<VerificationResult id={self.id} score={self.risk_score} decision={self.decision}>"
