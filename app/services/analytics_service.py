"""
Analytics service for tracking and retrieving user activity and usage statistics.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from sqlalchemy import func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models_analytics import UserActivity, SearchQuery, ContentInteraction
from app.models_user import User

class AnalyticsService:
    """Service for handling analytics operations."""
    
    def __init__(self, db: AsyncSession, current_user: Optional[User] = None):
        self.db = db
        self.current_user = current_user
    
    async def track_activity(
        self,
        activity_type: str,
        activity_data: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserActivity:
        """
        Track a user activity.
        
        Args:
            activity_type: Type of activity (e.g., 'login', 'search', 'view_story')
            activity_data: Additional data about the activity
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            The created UserActivity record
        """
        if not self.current_user:
            raise ValueError("No current user provided for activity tracking")
            
        activity = UserActivity(
            user_id=self.current_user.id,
            activity_type=activity_type,
            activity_data=activity_data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity
    
    async def track_search(
        self,
        query: str,
        result_count: int,
        search_type: str = 'all',
        filters: Optional[Dict] = None,
        is_advanced: bool = False
    ) -> SearchQuery:
        """
        Track a search query.
        
        Args:
            query: The search query string
            result_count: Number of results returned
            search_type: Type of search ('stories', 'oral_histories', or 'all')
            filters: Any filters applied to the search
            is_advanced: Whether advanced search was used
            
        Returns:
            The created SearchQuery record
        """
        search_query = SearchQuery(
            user_id=self.current_user.id if self.current_user else None,
            query=query,
            result_count=result_count,
            search_type=search_type,
            filters=filters or {},
            is_advanced=is_advanced
        )
        
        self.db.add(search_query)
        await self.db.commit()
        await self.db.refresh(search_query)
        return search_query
    
    async def track_content_interaction(
        self,
        content_type: str,
        content_id: int,
        interaction_type: str,
        interaction_data: Optional[Dict] = None
    ) -> ContentInteraction:
        """
        Track a user interaction with content.
        
        Args:
            content_type: Type of content ('story', 'oral_history', etc.)
            content_id: ID of the content item
            interaction_type: Type of interaction ('view', 'download', 'share', etc.)
            interaction_data: Additional data about the interaction
            
        Returns:
            The created ContentInteraction record
        """
        interaction = ContentInteraction(
            user_id=self.current_user.id if self.current_user else None,
            content_type=content_type,
            content_id=content_id,
            interaction_type=interaction_type,
            interaction_data=interaction_data or {}
        )
        
        self.db.add(interaction)
        await self.db.commit()
        await self.db.refresh(interaction)
        return interaction
    
    async def get_activity_stats(
        self,
        days: int = 30,
        activity_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Get activity statistics.
        
        Args:
            days: Number of days to look back
            activity_type: Filter by activity type
            user_id: Filter by user ID
            
        Returns:
            Dictionary with activity statistics
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        query = select(UserActivity).where(UserActivity.created_at >= since_date)
        
        # Apply filters
        if activity_type:
            query = query.where(UserActivity.activity_type == activity_type)
        if user_id:
            query = query.where(UserActivity.user_id == user_id)
        elif self.current_user and not user_id:
            query = query.where(UserActivity.user_id == self.current_user.id)
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_query)).scalar()
        
        # Get activity type breakdown
        type_query = select(
            UserActivity.activity_type,
            func.count().label('count')
        ).where(UserActivity.created_at >= since_date)
        
        if user_id:
            type_query = type_query.where(UserActivity.user_id == user_id)
        
        type_query = type_query.group_by(UserActivity.activity_type)
        type_results = (await self.db.execute(type_query)).all()
        
        # Get daily activity
        daily_query = select(
            func.date(UserActivity.created_at).label('date'),
            func.count().label('count')
        ).where(UserActivity.created_at >= since_date)
        
        if user_id:
            daily_query = daily_query.where(UserActivity.user_id == user_id)
        if activity_type:
            daily_query = daily_query.where(UserActivity.activity_type == activity_type)
            
        daily_query = daily_query.group_by('date')
        daily_results = (await self.db.execute(daily_query)).all()
        
        # Ensure date is a datetime object before calling isoformat
        daily_activity_processed = []
        for r in daily_results:
            date_obj = r[0]
            if isinstance(date_obj, str):
                date_obj = datetime.fromisoformat(date_obj)
            daily_activity_processed.append({'date': date_obj.isoformat(), 'count': r[1]})

        return {
            'total_activities': total,
            'activity_types': [{'type': r[0], 'count': r[1]} for r in type_results],
            'daily_activity': daily_activity_processed
        }
    
    async def get_search_analytics(
        self,
        days: int = 30,
        search_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Get search analytics.
        
        Args:
            days: Number of days to look back
            search_type: Filter by search type
            user_id: Filter by user ID
            
        Returns:
            Dictionary with search analytics
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        query = select(SearchQuery).where(SearchQuery.created_at >= since_date)
        
        # Apply filters
        if search_type:
            query = query.where(SearchQuery.search_type == search_type)
        if user_id:
            query = query.where(SearchQuery.user_id == user_id)
        elif self.current_user and not user_id:
            query = query.where(SearchQuery.user_id == self.current_user.id)
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_query)).scalar()
        
        # Get popular searches
        popular_query = select(
            SearchQuery.query,
            func.count().label('count')
        ).where(SearchQuery.created_at >= since_date)
        
        if search_type:
            popular_query = popular_query.where(SearchQuery.search_type == search_type)
        if user_id:
            popular_query = popular_query.where(SearchQuery.user_id == user_id)
            
        popular_query = popular_query.group_by(SearchQuery.query)\
                                   .order_by(func.count().desc())\
                                   .limit(10)
        
        popular_results = (await self.db.execute(popular_query)).all()
        
        # Get search type breakdown
        type_query = select(
            SearchQuery.search_type,
            func.count().label('count')
        ).where(SearchQuery.created_at >= since_date)
        
        if user_id:
            type_query = type_query.where(SearchQuery.user_id == user_id)
            
        type_query = type_query.group_by(SearchQuery.search_type)
        type_results = (await self.db.execute(type_query)).all()
        
        # Get advanced vs basic search ratio
        advanced_query = select(
            SearchQuery.is_advanced,
            func.count().label('count')
        ).where(SearchQuery.created_at >= since_date)
        
        if user_id:
            advanced_query = advanced_query.where(SearchQuery.user_id == user_id)
            
        advanced_query = advanced_query.group_by(SearchQuery.is_advanced)
        advanced_results = (await self.db.execute(advanced_query)).all()
        
        return {
            'total_searches': total,
            'popular_searches': [{'query': r[0], 'count': r[1]} for r in popular_results],
            'search_types': [{'type': r[0], 'count': r[1]} for r in type_results],
            'advanced_ratio': {
                'advanced': next((r[1] for r in advanced_results if r[0]), 0),
                'basic': next((r[1] for r in advanced_results if not r[0]), 0)
            }
        }
    
    async def get_content_analytics(
        self,
        days: int = 30,
        content_type: Optional[str] = None,
        interaction_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Get content interaction analytics.
        
        Args:
            days: Number of days to look back
            content_type: Filter by content type
            interaction_type: Filter by interaction type
            user_id: Filter by user ID
            
        Returns:
            Dictionary with content interaction analytics
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        query = select(ContentInteraction).where(ContentInteraction.created_at >= since_date)
        
        # Apply filters
        if content_type:
            query = query.where(ContentInteraction.content_type == content_type)
        if interaction_type:
            query = query.where(ContentInteraction.interaction_type == interaction_type)
        if user_id:
            query = query.where(ContentInteraction.user_id == user_id)
        
        # Get total count
        total_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(total_query)).scalar()
        
        # Get interaction type breakdown
        type_query = select(
            ContentInteraction.interaction_type,
            func.count().label('count')
        ).where(ContentInteraction.created_at >= since_date)
        
        if content_type:
            type_query = type_query.where(ContentInteraction.content_type == content_type)
        if user_id:
            type_query = type_query.where(ContentInteraction.user_id == user_id)
            
        type_query = type_query.group_by(ContentInteraction.interaction_type)
        type_results = (await self.db.execute(type_query)).all()
        
        # Get popular content
        content_query = select(
            ContentInteraction.content_type,
            ContentInteraction.content_id,
            func.count().label('count')
        ).where(ContentInteraction.created_at >= since_date)
        
        if content_type:
            content_query = content_query.where(ContentInteraction.content_type == content_type)
        if interaction_type:
            content_query = content_query.where(ContentInteraction.interaction_type == interaction_type)
        if user_id:
            content_query = content_query.where(ContentInteraction.user_id == user_id)
            
        content_query = content_query.group_by(
            ContentInteraction.content_type,
            ContentInteraction.content_id
        ).order_by(func.count().desc()).limit(10)
        
        content_results = (await self.db.execute(content_query)).all()
        
        return {
            'total_interactions': total,
            'interaction_types': [{'type': r[0], 'count': r[1]} for r in type_results],
            'popular_content': [
                {
                    'content_type': r[0],
                    'content_id': r[1],
                    'count': r[2]
                } for r in content_results
            ]
        }
