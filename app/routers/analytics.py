"""
Analytics API endpoints for tracking and retrieving user activity and usage statistics.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.services.analytics_service import AnalyticsService
from app.core.config import settings

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/activity")
async def get_activity_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get activity analytics.
    
    Users can only see their own analytics unless they are admins.
    """
    if user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view other users' analytics"
        )
    
    analytics_service = AnalyticsService(db, current_user)
    return await analytics_service.get_activity_stats(
        days=days,
        activity_type=activity_type,
        user_id=user_id
    )

@router.get("/searches")
async def get_search_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    search_type: Optional[str] = Query(None, description="Filter by search type (stories, oral_histories, all)"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get search analytics.
    
    Users can only see their own analytics unless they are admins.
    """
    if user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view other users' analytics"
        )
    
    analytics_service = AnalyticsService(db, current_user)
    return await analytics_service.get_search_analytics(
        days=days,
        search_type=search_type,
        user_id=user_id
    )

@router.get("/content")
async def get_content_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    interaction_type: Optional[str] = Query(None, description="Filter by interaction type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID (admin only)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get content interaction analytics.
    
    Users can only see their own analytics unless they are admins.
    """
    if user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can view other users' analytics"
        )
    
    analytics_service = AnalyticsService(db, current_user)
    return await analytics_service.get_content_analytics(
        days=days,
        content_type=content_type,
        interaction_type=interaction_type,
        user_id=user_id
    )

@router.post("/track/activity")
async def track_activity(
    activity_type: str,
    activity_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Track a user activity.
    
    This endpoint is typically called from the frontend to track user actions.
    """
    analytics_service = AnalyticsService(db, current_user)
    
    try:
        await analytics_service.track_activity(
            activity_type=activity_type,
            activity_data=activity_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return {"status": "success", "message": "Activity tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/track/search")
async def track_search(
    query: str,
    result_count: int,
    search_type: str = 'all',
    filters: Optional[Dict[str, Any]] = None,
    is_advanced: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Track a search query.
    
    This endpoint is typically called from the frontend after a search is performed.
    """
    analytics_service = AnalyticsService(db, current_user)
    
    try:
        await analytics_service.track_search(
            query=query,
            result_count=result_count,
            search_type=search_type,
            filters=filters,
            is_advanced=is_advanced
        )
        return {"status": "success", "message": "Search tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/track/interaction")
async def track_interaction(
    content_type: str,
    content_id: int,
    interaction_type: str,
    interaction_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Track a user interaction with content.
    
    This endpoint is typically called from the frontend when a user interacts with content.
    """
    analytics_service = AnalyticsService(db, current_user)
    
    try:
        await analytics_service.track_content_interaction(
            content_type=content_type,
            content_id=content_id,
            interaction_type=interaction_type,
            interaction_data=interaction_data
        )
        return {"status": "success", "message": "Interaction tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
