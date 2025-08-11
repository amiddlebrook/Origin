"""
Research-related Pydantic models for request and response validation.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import Field

from ..base import BaseSchema

class ResearchBase(BaseSchema):
    """Base schema for research data."""
    title: str
    description: Optional[str] = None
    content: Optional[Any] = None
    is_public: bool = False
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchCreate(ResearchBase):
    """Schema for creating a new research item."""
    pass

class ResearchUpdate(BaseSchema):
    """Schema for updating an existing research item."""
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Any] = None
    is_public: Optional[bool] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None

class ResearchOut(ResearchBase):
    """Schema for research item output."""
    id: int
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "pending"

class ResearchList(BaseSchema):
    """Schema for a list of research items with pagination."""
    items: list[ResearchOut]
    total: int
    page: int
    size: int
    pages: int
