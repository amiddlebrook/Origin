from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class ResearchCreate(BaseModel):
    name: str

class ResearchOut(BaseModel):
    id: int
    name: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
