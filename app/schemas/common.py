"""
Common/shared Pydantic schemas.
"""

from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with shared config."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MessageResponse(BaseSchema):
    """Generic success message."""

    success: bool = True
    message: str


class ErrorDetail(BaseSchema):
    field: str
    message: str
    type: str


class ErrorResponse(BaseSchema):
    """Standard error envelope."""

    success: bool = False
    error: dict[str, Any]


class PaginationParams(BaseSchema):
    """Query params for paginated list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse[T](BaseSchema):
    """Wrapper for paginated list responses."""

    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseSchema):
    status: str
    version: str
    postgres: str
    redis: str
    environment: str
