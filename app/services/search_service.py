"""
Search service for full-text search across the application.
Supports both PostgreSQL (using TSVECTOR) and SQLite (using FTS5).
"""
from typing import List, Dict, Any, Optional, Type, TypeVar, Tuple
from datetime import datetime
from sqlalchemy import select, and_, func, text, ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models_story import NameStory, OralHistory
from app.models_user import User
from app.schemas_story import NameStoryOut, OralHistoryOut
from app.schemas.base import PaginatedResponse
from app.database import Base

# Type aliases
ModelType = TypeVar('ModelType', bound=Base)  # Base is the SQLAlchemy declarative base

T = TypeVar('T')

class SearchService:
    """Service for searching across different models with full-text search capabilities."""
    
    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.current_user = current_user
        # Check database type
        self.is_sqlite = 'sqlite' in str(db.bind.url.drivername)
        
    def _get_search_condition(self, model: Type[ModelType], query: str) -> ColumnElement:
        """
        Generate the appropriate search condition based on the database type.
        
        Args:
            model: The SQLAlchemy model class
            query: The search query string
            
        Returns:
            A SQLAlchemy condition for the search
        """
        if not query:
            return True  # No search filter if query is empty
            
        if self.is_sqlite:
            # For SQLite, use FTS5 syntax
            fts_table = f"{model.__tablename__}_fts"
            search_terms = ' OR '.join([f"{term}*" for term in query.split()])
            return text(f"{fts_table} MATCH :search_terms").bindparams(search_terms=search_terms)
        else:
            # For PostgreSQL, use TSVECTOR
            return model.search_vector.op('@@')(func.websearch_to_tsquery('english', query))
    
    async def _get_sort_expression(
        self, 
        model: Type[ModelType], 
        sort_by: Optional[str] = None, 
        sort_order: str = 'desc'
    ) -> Tuple[Optional[ColumnElement], List[ColumnElement]]:
        """
        Generate the sort expression for the query.
        
        Args:
            model: The SQLAlchemy model class
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            A tuple of (sort_expression, group_by_columns)
        """
        sort_expr = None
        group_by_columns = []
        
        # Handle sorting
        if sort_by:
            sort_column = getattr(model, sort_by, None)
            if sort_column is not None:
                sort_direction = func.desc if sort_order.lower() == 'desc' else func.asc
                sort_expr = sort_direction(sort_column)
                group_by_columns.append(sort_column)
        
        # For SQLite FTS, we need to include the rank in the order by
        if self.is_sqlite and hasattr(model, 'search_vector'):
            fts_table = f"{model.__tablename__}_fts"
            rank_expr = text(f"rank(matchinfo({fts_table}))")
            sort_expr = rank_expr.desc() if sort_order.lower() == 'desc' else rank_expr.asc()
        
        return sort_expr, group_by_columns

    async def search(
        self,
        query: str,
        model_type: Type[ModelType],
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> PaginatedResponse:
        """
        Generic search method that can search across any model with full-text search support.
        
        Args:
            query: Search query string
            model_type: The SQLAlchemy model class to search in
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Additional filters to apply {field: value}
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            PaginatedResponse with search results and metadata
        """
        # Initialize query
        stmt = select(model_type).where(
            model_type.user_id == self.current_user.id
        )
        
        # Apply search condition
        search_condition = self._get_search_condition(model_type, query)
        if search_condition is not True:  # Only add if we have a search condition
            stmt = stmt.where(search_condition)
        
        # Apply additional filters
        if filters:
            filter_conditions = []
            for field, value in filters.items():
                if value is not None:
                    column = getattr(model_type, field, None)
                    if column is not None:
                        if isinstance(value, (list, tuple)):
                            filter_conditions.append(column.in_(value))
                        else:
                            filter_conditions.append(column == value)
            if filter_conditions:
                stmt = stmt.where(and_(*filter_conditions))
        
        # Get total count for pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()
        
        # Handle sorting
        sort_expr, group_by_columns = await self._get_sort_expression(model_type, sort_by, sort_order)
        if sort_expr is not None:
            stmt = stmt.order_by(sort_expr)
        
        # Add group by columns if needed (for SQLite FTS)
        if group_by_columns:
            stmt = stmt.group_by(*group_by_columns)
        
        # Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        # Convert to output schema
        if model_type == NameStory:
            items_out = [NameStoryOut.from_orm(item) for item in items]
        elif model_type == OralHistory:
            items_out = [OralHistoryOut.from_orm(item) for item in items]
        else:
            items_out = items
        
        return PaginatedResponse(
            items=items_out,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0
        )
    
    async def search_stories(
        self,
        query: str,
        status: Optional[str] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> PaginatedResponse:
        """
        Search name stories with additional filters specific to stories.
        
        Args:
            query: Search query string
            status: Filter by status (e.g., 'draft', 'published')
            min_date: Filter by minimum creation date
            max_date: Filter by maximum creation date
            page: Page number (1-based)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            PaginatedResponse with search results and metadata
        """
        # Build filters
        filters = {}
        if status:
            filters['status'] = status
        
        # For SQLite FTS, we need to join with the FTS virtual table
        if self.is_sqlite and query:
            fts_table = f"{NameStory.__tablename__}_fts"
            stmt = select(NameStory).join(
                text(f"{fts_table} ON {NameStory.__tablename__}.id = {fts_table}.rowid"),
                isouter=False
            ).where(
                NameStory.user_id == self.current_user.id
            )
            
            # Apply search condition for SQLite
            search_condition = self._get_search_condition(NameStory, query)
            if search_condition is not True:
                stmt = stmt.where(search_condition)
        else:
            # Standard query for PostgreSQL or when there's no search query
            stmt = select(NameStory).where(
                NameStory.user_id == self.current_user.id
            )
            
            # Apply search condition for PostgreSQL
            if query:
                search_condition = self._get_search_condition(NameStory, query)
                if search_condition is not True:
                    stmt = stmt.where(search_condition)
        
        # Apply filters
        if filters:
            stmt = stmt.filter_by(**filters)
        
        # Apply date filters
        date_filters = []
        if min_date:
            date_filters.append(NameStory.created_at >= min_date)
        if max_date:
            date_filters.append(NameStory.created_at <= max_date)
        if date_filters:
            stmt = stmt.where(and_(*date_filters))
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()
        
        # Handle sorting
        sort_expr, group_by_columns = await self._get_sort_expression(NameStory, sort_by, sort_order)
        if sort_expr is not None:
            stmt = stmt.order_by(sort_expr)
        
        # Add group by columns if needed (for SQLite FTS)
        if group_by_columns:
            stmt = stmt.group_by(*group_by_columns)
        
        # Apply pagination
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return PaginatedResponse(
            items=[NameStoryOut.from_orm(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0
        )
    
    async def search_oral_histories(
        self,
        query: str,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> PaginatedResponse:
        """Search oral histories with additional audio-specific filtering."""
        filters = {}
        if status:
            filters['status'] = status
        if mime_type:
            filters['mime_type'] = mime_type
            
        # Apply duration filters
        if min_duration is not None or max_duration is not None:
            if min_duration is not None and max_duration is not None:
                filters['duration_seconds'] = and_(
                    OralHistory.duration_seconds >= min_duration,
                    OralHistory.duration_seconds <= max_duration
                )
            elif min_duration is not None:
                filters['duration_seconds'] = OralHistory.duration_seconds >= min_duration
            elif max_duration is not None:
                filters['duration_seconds'] = OralHistory.duration_seconds <= max_duration
        
        return await self.search(
            query=query,
            model_type=OralHistory,
            page=page,
            page_size=page_size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    async def search_all(
        self,
        query: str,
        model_types: Optional[List[Type[ModelType]]] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Search across multiple model types and combine results.
        
        Args:
            query: Search query string
            model_types: List of model types to search in (defaults to [NameStory, OralHistory])
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dictionary with search results from each model type
        """
        if model_types is None:
            model_types = [NameStory, OralHistory]
            
        results = {}
        
        # For SQLite, we need to be more careful with the query
        if self.is_sqlite and query:
            # For SQLite, we'll use a UNION ALL approach to search across all models at once
            # This is more efficient than separate queries for each model type
            
            # Build a list of all the queries we need to union
            union_queries = []
            
            # Track the model type for each query so we can map results back
            model_mapping = {}
            
            for model_type in model_types:
                if model_type == NameStory:
                    fts_table = f"{NameStory.__tablename__}_fts"
                    table_name = NameStory.__tablename__
                    model_mapping[table_name] = 'stories'
                    
                    # Build the query for this model type
                    query_parts = [
                        f"SELECT id, '{table_name}' as model_type, title, created_at, "
                        f"rank(matchinfo({fts_table})) as rank_score"
                        f" FROM {table_name} "
                        f"JOIN {fts_table} ON {table_name}.id = {fts_table}.rowid "
                        f"WHERE {fts_table} MATCH :search_terms"
                        f" AND user_id = :user_id"
                    ]
                    
                    union_queries.append(" ".join(query_parts))
                    
                elif model_type == OralHistory:
                    fts_table = f"{OralHistory.__tablename__}_fts"
                    table_name = OralHistory.__tablename__
                    model_mapping[table_name] = 'oral_histories'
                    
                    # Build the query for this model type
                    query_parts = [
                        f"SELECT id, '{table_name}' as model_type, title, created_at, "
                        f"rank(matchinfo({fts_table})) as rank_score"
                        f" FROM {table_name} "
                        f"JOIN {fts_table} ON {table_name}.id = {fts_table}.rowid "
                        f"WHERE {fts_table} MATCH :search_terms"
                        f" AND user_id = :user_id"
                    ]
                    
                    union_queries.append(" ".join(query_parts))
            
            if not union_queries:
                return {}
            
            # Combine all queries with UNION ALL
            full_query = " UNION ALL ".join(union_queries)
            
            # Add ordering and pagination
            full_query += " ORDER BY rank_score DESC LIMIT :limit OFFSET :offset"
            
            # Execute the query
            offset = (page - 1) * page_size
            params = {
                'search_terms': ' OR '.join([f"{term}*" for term in query.split()]),
                'user_id': self.current_user.id,
                'limit': page_size,
                'offset': offset
            }
            
            result = await self.db.execute(text(full_query), params)
            rows = result.fetchall()
            
            # Group results by model type
            grouped_results = {model_key: [] for model_key in model_mapping.values()}
            
            for row in rows:
                model_key = model_mapping.get(row[1])
                if model_key:
                    grouped_results[model_key].append(row)
            
            # Now fetch the full objects for each result
            for model_type in model_types:
                if model_type == NameStory:
                    model_key = 'stories'
                    model_class = NameStory
                    out_class = NameStoryOut
                elif model_type == OralHistory:
                    model_key = 'oral_histories'
                    model_class = OralHistory
                    out_class = OralHistoryOut
                else:
                    continue
                
                ids = [row[0] for row in grouped_results.get(model_key, [])]
                if not ids:
                    results[model_key] = PaginatedResponse(
                        items=[],
                        total=0,
                        page=page,
                        page_size=page_size,
                        total_pages=0
                    )
                    continue
                
                # Fetch the full objects
                stmt = select(model_class).where(
                    model_class.id.in_(ids)
                )
                
                # For oral histories, load the story relationship
                if model_class == OralHistory:
                    stmt = stmt.options(selectinload(OralHistory.story))
                
                result = await self.db.execute(stmt)
                items = result.scalars().all()
                
                # Convert to output schema
                items_out = [out_class.from_orm(item) for item in items]
                
                # Get total count for this model type
                count_stmt = select(func.count()).select_from(
                    select(model_class).where(
                        model_class.user_id == self.current_user.id
                    ).subquery()
                )
                total = (await self.db.execute(count_stmt)).scalar()
                
                results[model_key] = PaginatedResponse(
                    items=items_out,
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0
                )
        else:
            # For PostgreSQL or when there's no search query, use the original approach
            for model_type in model_types:
                if model_type == NameStory:
                    results['stories'] = await self.search_stories(
                        query=query,
                        page=page,
                        page_size=page_size
                    )
                elif model_type == OralHistory:
                    results['oral_histories'] = await self.search_oral_histories(
                        query=query,
                        page=page,
                        page_size=page_size
                    )
        
        return results
    
    def _prepare_tsquery(self, query: str):
        """Prepare a search query for PostgreSQL full-text search."""
        # Clean and prepare the query for tsquery
        query = query.strip()
        
        # Replace spaces with & for AND search
        terms = [term for term in query.split() if term]
        tsquery = ' & '.join(f"{term}:*" for term in terms)
        
        # Create a tsquery expression
        return func.to_tsquery('english', tsquery)
    
    async def get_search_suggestions(self, query: str, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get search suggestions for the given query.
        
        Returns suggestions from different models that match the query.
        """
        if not query or len(query.strip()) < 2:
            return {
                'stories': [],
                'oral_histories': []
            }
            
        results = {}
        
        # Get story suggestions
        stmt = (
            select(
                NameStory.id,
                NameStory.title,
                func.ts_headline('english', NameStory.narrative, 
                               func.to_tsquery('english', self._prepare_tsquery(query)),
                               'MaxFragments=2, MaxWords=20, MinWords=5, StartSel=**, StopSel=**').label('snippet')
            )
            .where(
                and_(
                    NameStory.user_id == self.current_user.id,
                    NameStory.search_vector.op('@@')(self._prepare_tsquery(query))
                )
            )
            .order_by(
                func.ts_rank(
                    NameStory.search_vector,
                    self._prepare_tsquery(query)
                ).desc()
            )
            .limit(limit)
        )
        
        story_results = await self.db.execute(stmt)
        results['stories'] = [
            {"id": r.id, "title": r.title, "snippet": r.snippet, "type": "story"} 
            for r in story_results
        ]
        
        # Get oral history suggestions
        stmt = (
            select(
                OralHistory.id,
                OralHistory.title,
                func.ts_headline('english', OralHistory.transcript, 
                               func.to_tsquery('english', self._prepare_tsquery(query)),
                               'MaxFragments=2, MaxWords=20, MinWords=5, StartSel=**, StopSel=**').label('snippet')
            )
            .where(
                and_(
                    OralHistory.user_id == self.current_user.id,
                    OralHistory.search_vector.op('@@')(self._prepare_tsquery(query))
                )
            )
            .order_by(
                func.ts_rank(
                    OralHistory.search_vector,
                    self._prepare_tsquery(query)
                ).desc()
            )
            .limit(limit)
        )
        
        oral_history_results = await self.db.execute(stmt)
        results['oral_histories'] = [
            {"id": r.id, "title": r.title, "snippet": r.snippet, "type": "oral_history"}
            for r in oral_history_results
        ]
        
        return results
