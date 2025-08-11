from typing import Optional, Any, List
from pydantic import BaseModel, ConfigDict

# Name Story Schemas
class NameStoryCreate(BaseModel):
    title: str
    research_id: Optional[int] = None
    seed_name: Optional[str] = None  # if provided, we will run research then compose

class NameStoryOut(BaseModel):
    id: int
    user_id: int
    research_id: Optional[int]
    title: str
    narrative: Optional[str]
    sources: Optional[Any]
    illustration_url: Optional[str]
    status: str

    model_config = ConfigDict(from_attributes=True)

# Oral History Schemas
class OralHistoryCreate(BaseModel):
    title: str
    story_id: Optional[int] = None

class OralHistoryOut(BaseModel):
    id: int
    user_id: int
    story_id: Optional[int]
    title: str
    file_path: str
    duration_seconds: Optional[int]
    transcript: Optional[str]

    model_config = ConfigDict(from_attributes=True)
