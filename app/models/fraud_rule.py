"""
Fraud Rule model — configurable rules stored in the database.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONB_TYPE
from app.models.mixins import TimestampMixin, UUIDMixin


class FraudRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "fraud_rules"

    # NULL org_id = system-level global rule; non-null = org-specific override
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    score_impact: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Extensible rule config (thresholds, patterns, etc.)
    config: Mapped[dict] = mapped_column(JSONB_TYPE, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<FraudRule id={self.id} name={self.rule_name} impact={self.score_impact}>"
