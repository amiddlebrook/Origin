"""
Search-related schemas for the API.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class SearchResultType(str, Enum):
    """Types of search results."""
    STORY = "story"
    ORAL_HISTORY = "oral_history"

class SearchResultItem(BaseModel):
    """Single search result item."""
    id: int
    type: SearchResultType
    title: str
    snippet: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "type": "story",
                "title": "The Story of My Name",
                "snippet": "This is a **snippet** from the content that matches your search query.",
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z",
                "score": 0.85,
                "metadata": {
                    "status": "done",
                    "has_audio": False
                }
            }
        }
    }

class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    total_results: int
    page: int
    page_size: int
    total_pages: int
    results: List[SearchResultItem]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "family history",
                "total_results": 42,
                "page": 1,
                "page_size": 10,
                "total_pages": 5,
                "results": [
                    {
                        "id": 1,
                        "type": "story",
                        "title": "The Story of My Name",
                        "snippet": "This is a **snippet** from the content that matches your search query.",
                        "created_at": "2023-01-01T12:00:00Z",
                        "updated_at": "2023-01-01T12:00:00Z",
                        "score": 0.85,
                        "metadata": {
                            "status": "done"
                        }
                    }
                ]
            }
        }
    }

class SearchSuggestionItem(BaseModel):
    """Single search suggestion item."""
    id: int
    type: SearchResultType
    title: str
    snippet: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "type": "story",
                "title": "The Story of My Name",
                "snippet": "This is a **snippet** from the content that matches your search query."
            }
        }
    }

class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response model."""
    query: str
    stories: List[SearchSuggestionItem] = Field(default_factory=list)
    oral_histories: List[SearchSuggestionItem] = Field(default_factory=list)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "fam",
                "stories": [
                    {
                        "id": 1,
                        "type": "story",
                        "title": "Family History",
                        "snippet": "This story is about my **family** history..."
                    }
                ],
                "oral_histories": [
                    {
                        "id": 5,
                        "type": "oral_history",
                        "title": "Grandma's Stories",
                        "snippet": "My grandmother told me stories about our **family**..."
                    }
                ]
            }
        }
    }

class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=200, description="Search query string")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(10, ge=1, le=100, description="Number of results per page")
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional filters to apply to the search"
    )
    sort_by: Optional[str] = Field(
        None,
        description="Field to sort by (default: relevance)",
        examples=["relevance", "title", "created_at", "updated_at"]
    )
    sort_order: Literal["asc", "desc"] = Field(
        "desc",
        description="Sort order (asc or desc)"
    )
    include: Optional[List[SearchResultType]] = Field(
        None,
        description="Types of results to include in the search"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "family history",
                "page": 1,
                "page_size": 10,
                "filters": {
                    "status": "done"
                },
                "sort_by": "relevance",
                "sort_order": "desc",
                "include": ["story", "oral_history"]
            }
        }
    }
