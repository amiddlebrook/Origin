"""
Schemas package for the application.

This package contains all the Pydantic models used for request/response validation
and serialization in the API.
"""

# Base schemas
from .base import (
    BaseSchema,
    PaginatedResponse,
    Message,
    ErrorResponse
)

# Research schemas
from .research import (
    ResearchBase,
    ResearchCreate,
    ResearchUpdate,
    ResearchOut,
    ResearchList
)

# Story and Oral History schemas
from .stories import (
    StoryBase,
    StoryCreate,
    StoryUpdate,
    StoryOut,
    StoryList,
    OralHistoryBase,
    OralHistoryCreate,
    OralHistoryUpdate,
    OralHistoryOut,
    OralHistoryList
)

# Analytics schemas
from .analytics import (
    AnalyticsTimeRange,
    AnalyticsMetric,
    AnalyticsFilter,
    AnalyticsDataPoint,
    AnalyticsSeries,
    AnalyticsSummary,
    AnalyticsResponse,
    UserActivityData,
    ContentViewsData,
    ContentCreationData,
    SearchAnalyticsData,
    ApiUsageData,
    StorageUsageData
)

# Search schemas
from .search import (
    SearchResultType,
    SearchResultItem,
    SearchResponse,
    SearchSuggestionItem,
    SearchSuggestionsResponse,
    SearchRequest
)

# Re-export all schemas
__all__ = [
    # Base
    'BaseSchema',
    'PaginatedResponse',
    'Message',
    'ErrorResponse',
    
    # Research
    'ResearchBase',
    'ResearchCreate',
    'ResearchUpdate',
    'ResearchOut',
    'ResearchList',
    
    # Stories
    'StoryBase',
    'StoryCreate',
    'StoryUpdate',
    'StoryOut',
    'StoryList',
    
    # Oral Histories
    'OralHistoryBase',
    'OralHistoryCreate',
    'OralHistoryUpdate',
    'OralHistoryOut',
    'OralHistoryList',
    
    # Analytics
    'AnalyticsTimeRange',
    'AnalyticsMetric',
    'AnalyticsFilter',
    'AnalyticsDataPoint',
    'AnalyticsSeries',
    'AnalyticsSummary',
    'AnalyticsResponse',
    'UserActivityData',
    'ContentViewsData',
    'ContentCreationData',
    'SearchAnalyticsData',
    'ApiUsageData',
    'StorageUsageData',
    
    # Search
    'SearchResultType',
    'SearchResultItem',
    'SearchResponse',
    'SearchSuggestionItem',
    'SearchSuggestionsResponse',
    'SearchRequest'
]

# Import other schemas from the root schemas.py
