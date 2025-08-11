"""
Base schemas and configurations used throughout the application.
"""
from pydantic import BaseModel, ConfigDict
from typing import Any, TypeVar, Generic

# Generic type variable for pagination
T = TypeVar('T')

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)

class Message(BaseModel):
    """Standard message response schema."""
    message: str

class ErrorResponse(BaseModel):
    """Standard error response schema."""
    detail: str | dict[str, Any] | None = None
    error: str | None = None
    code: str | None = None
