"""
Story-related Pydantic models for request and response validation.
"""
from datetime import datetime
from typing import Any, Optional, List
from pydantic import Field, HttpUrl

from ..base import BaseSchema

class StoryBase(BaseSchema):
    """Base schema for story data."""
    title: str
    name: str
    content: str
    is_public: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class StoryCreate(StoryBase):
    """Schema for creating a new story."""
    research_id: Optional[int] = None

class StoryUpdate(BaseSchema):
    """Schema for updating an existing story."""
    title: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None

class StoryOut(StoryBase):
    """Schema for story output."""
    id: int
    research_id: Optional[int] = None
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "draft"
    
    # Relationships
    media_urls: List[HttpUrl] = Field(default_factory=list)
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class StoryList(BaseSchema):
    """Schema for a list of stories with pagination."""
    items: List[StoryOut]
    total: int
    page: int
    size: int
    pages: int
