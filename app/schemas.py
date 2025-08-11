from pydantic import BaseModel
from typing import Optional, Any

class ResearchCreate(BaseModel):
    name: str

class ResearchOut(BaseModel):
    id: int
    name: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

    class Config:
        orm_mode = True
