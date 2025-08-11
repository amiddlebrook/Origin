"""
Search API endpoints for full-text search across the application.
Supports both PostgreSQL (TSVECTOR) and SQLite (FTS5) backends.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any, Union, Type
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, Base
from app.auth.router import get_current_user
from app.models_user import User
from app.models_story import NameStory, OralHistory
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchResultType,
    SearchSuggestionsResponse,
    SearchSuggestionItem
)
from app.services.search_service import SearchService
from app.schemas.base import PaginatedResponse

router = APIRouter(prefix="/search", tags=["search"])

def _get_model_class(model_type: str) -> Type[Base]:
    """Get the SQLAlchemy model class for the given model type."""
    if model_type == 'stories':
        return NameStory
    elif model_type == 'oral_histories':
        return OralHistory
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model type: {model_type}"
        )

@router.post("", response_model=SearchResponse)
async def search(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search across all content types with full-text search capabilities.
    
    This endpoint allows searching across stories and oral histories with advanced filtering,
    sorting, and pagination. Works with both PostgreSQL (TSVECTOR) and SQLite (FTS5) backends.
    """
    search_service = SearchService(db, current_user)
    
    # Determine which model types to include in the search
    model_types = []
    if search_request.include:
        if SearchResultType.STORY in search_request.include:
            model_types.append(NameStory)
        if SearchResultType.ORAL_HISTORY in search_request.include:
            model_types.append(OralHistory)
    else:
        # Default to searching all types if none specified
        model_types = [NameStory, OralHistory]
    
    # Prepare filters for each model type
    filters = {}
    
    # Apply global filters
    if search_request.filters:
        # Status filter
        if 'status' in search_request.filters:
            filters['status'] = search_request.filters['status']
        
        # Date range filters
        if 'date_from' in search_request.filters:
            filters['created_at__gte'] = search_request.filters['date_from']
        if 'date_to' in search_request.filters:
            filters['created_at__lte'] = search_request.filters['date_to']
    
    # Map sort_by to model fields if needed
    sort_by = search_request.sort_by
    if sort_by == 'relevance':
        sort_by = None  # Let the search service handle relevance sorting
    
    # Execute search across all requested model types
    results = await search_service.search_all(
        query=search_request.query,
        page=search_request.page,
        page_size=search_request.page_size,
        model_types=model_types,
        **filters  # Pass filters directly, let the service handle model-specific filtering
    )
    
    # Combine and sort results if needed
    all_results = []
    
    # Process story results
    if 'stories' in results:
        story_results = results['stories']
        for item in story_results.items:
            all_results.append(SearchResultItem(
                id=item.id,
                type=SearchResultType.STORY,
                title=item.title,
                created_at=item.created_at,
                updated_at=getattr(item, 'updated_at', None),
                metadata={
                    'status': item.status,
                    'has_audio': len(getattr(item, 'oral_histories', [])) > 0
                }
            ))
    
    # Process oral history results
    if 'oral_histories' in results:
        oral_results = results['oral_histories']
        for item in oral_results.items:
            all_results.append(SearchResultItem(
                id=item.id,
                type=SearchResultType.ORAL_HISTORY,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
                metadata={
                    'status': item.status,
                    'duration_seconds': item.duration_seconds,
                    'mime_type': item.mime_type,
                    'has_transcript': bool(item.transcript)
                }
            ))
    
    # Sort combined results if not sorting by relevance
    if search_request.sort_by and search_request.sort_by != 'relevance':
        reverse = search_request.sort_order.lower() == 'desc'
        all_results.sort(
            key=lambda x: getattr(x, search_request.sort_by, x.created_at) or '',
            reverse=reverse
        )
    
    # Apply pagination to combined results
    total_results = len(all_results)
    total_pages = (total_results + search_request.page_size - 1) // search_request.page_size if search_request.page_size > 0 else 1
    
    # Ensure page is within bounds
    page = min(search_request.page, total_pages) if total_pages > 0 else 1
    start_idx = (page - 1) * search_request.page_size
    end_idx = start_idx + search_request.page_size
    
    paginated_results = all_results[start_idx:end_idx]
    
    return SearchResponse(
        query=search_request.query,
        total_results=total_results,
        page=page,
        page_size=search_request.page_size,
        total_pages=total_pages,
        results=paginated_results
    )

@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Search query for suggestions"),
    limit: int = Query(5, ge=1, le=10, description="Maximum number of suggestions per type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get search suggestions for the given query.
    
    This endpoint provides type-ahead search suggestions as the user types,
    with results from both stories and oral histories. Works with both PostgreSQL
    and SQLite backends.
    """
    if not q or len(q.strip()) < 1:
        return SearchSuggestionsResponse(query=q)
    
    search_service = SearchService(db, current_user)
    
    # Get suggestions from stories
    story_results = await search_service.search_stories(
        query=q,
        page=1,
        page_size=limit,
        sort_by='created_at',
        sort_order='desc'
    )
    
    # Get suggestions from oral histories
    oral_history_results = await search_service.search_oral_histories(
        query=q,
        page=1,
        page_size=limit,
        sort_by='created_at',
        sort_order='desc'
    )
    
    # Format suggestions
    suggestions = []
    
    # Add story suggestions
    for item in story_results.items[:limit]:
        suggestions.append(SearchSuggestionItem(
            id=item.id,
            type=SearchResultType.STORY,
            title=item.title,
            preview=getattr(item, 'narrative', '')[:100] + '...' if getattr(item, 'narrative', None) else ''
        ))
    
    # Add oral history suggestions
    for item in oral_history_results.items[:limit]:
        preview = getattr(item, 'summary', '')[:100] + '...' if getattr(item, 'summary', None) else ''
        if not preview:
            preview = getattr(item, 'transcript', '')[:100] + '...' if getattr(item, 'transcript', None) else ''
            
        suggestions.append(SearchSuggestionItem(
            id=item.id,
            type=SearchResultType.ORAL_HISTORY,
            title=item.title,
            preview=preview
        ))
    
    return SearchSuggestionsResponse(suggestions=suggestions)

@router.get("/models/{model_type}", response_model=PaginatedResponse)
async def search_model(
    model_type: str,
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of results per page"),
    status: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search within a specific model type.
    
    This endpoint allows searching within a specific content type (stories or oral_histories)
    with model-specific filtering and sorting options. Works with both PostgreSQL and SQLite backends.
    """
    search_service = SearchService(db, current_user)
    
    # Map model_type to the appropriate search method and model class
    if model_type == 'stories':
        model_class = NameStory
        search_method = search_service.search_stories
    elif model_type == 'oral_histories':
        model_class = OralHistory
        search_method = search_service.search_oral_histories
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model type: {model_type}. Must be 'stories' or 'oral_histories'."
        )
    
    # Prepare filters
    filters = {}
    if status:
        filters['status'] = status
    
    # Map sort_by to model fields if needed
    if sort_by == 'relevance':
        sort_by = None  # Let the search service handle relevance sorting
    
    # Execute the search
    result = await search_method(
        query=q,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        **filters
    )
    
    return result
