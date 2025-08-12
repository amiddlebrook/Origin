"""
Oral History related Pydantic models for request and response validation.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import Field, HttpUrl

from ..base import BaseSchema

class OralHistoryBase(BaseSchema):
    """Base schema for oral history data."""
    title: str
    interviewee_name: str
    description: Optional[str] = None
    recording_date: Optional[datetime] = None
    location: Optional[str] = None
    language: str = "en"
    is_public: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class OralHistoryCreate(OralHistoryBase):
    """Schema for creating a new oral history."""
    story_id: Optional[int] = None

class OralHistoryUpdate(BaseSchema):
    """Schema for updating an existing oral history."""
    title: Optional[str] = None
    interviewee_name: Optional[str] = None
    description: Optional[str] = None
    recording_date: Optional[datetime] = None
    location: Optional[str] = None
    language: Optional[str] = None
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[str] = None

class OralHistoryOut(OralHistoryBase):
    """Schema for oral history output."""
    id: int
    story_id: Optional[int] = None
    created_by_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = "pending"
    duration_seconds: Optional[int] = None
    audio_url: Optional[HttpUrl] = None
    video_url: Optional[HttpUrl] = None
    transcript: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class OralHistoryList(BaseSchema):
    """Schema for a list of oral histories with pagination."""
    items: List[OralHistoryOut]
    total: int
    page: int
    size: int
    pages: int
