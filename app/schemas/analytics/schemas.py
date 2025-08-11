"""
Analytics-related Pydantic models for request and response validation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import Field, HttpUrl

from ..base import BaseSchema

class AnalyticsTimeRange(str, Enum):
    """Time ranges for analytics queries."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"

class AnalyticsMetric(str, Enum):
    """Available analytics metrics."""
    USER_ACTIVITY = "user_activity"
    CONTENT_VIEWS = "content_views"
    CONTENT_CREATION = "content_creation"
    SEARCH_QUERIES = "search_queries"
    API_USAGE = "api_usage"
    STORAGE_USAGE = "storage_usage"

class AnalyticsFilter(BaseSchema):
    """Filters for analytics queries."""
    time_range: Optional[AnalyticsTimeRange] = AnalyticsTimeRange.LAST_30_DAYS
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_id: Optional[int] = None
    content_type: Optional[str] = None  # 'research', 'story', 'oral_history', etc.
    content_id: Optional[int] = None
    group_by: Optional[List[str]] = Field(default_factory=list)  # 'day', 'week', 'month', 'content_type', 'user', etc.

class AnalyticsDataPoint(BaseSchema):
    """A single data point in an analytics series."""
    timestamp: datetime
    value: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsSeries(BaseSchema):
    """A series of analytics data points."""
    name: str
    data: List[AnalyticsDataPoint]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsSummary(BaseSchema):
    """Summary statistics for analytics."""
    total: float
    average: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    change_percentage: Optional[float] = None  # Percentage change from previous period
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsResponse(BaseSchema):
    """Standard analytics API response."""
    metric: AnalyticsMetric
    filter: AnalyticsFilter
    series: List[AnalyticsSeries]
    summary: AnalyticsSummary
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Specific metric responses
class UserActivityData(AnalyticsResponse):
    """User activity analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.USER_ACTIVITY
    active_users: int
    new_users: int
    returning_users: int

class ContentViewsData(AnalyticsResponse):
    """Content views analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.CONTENT_VIEWS
    total_views: int
    unique_visitors: int
    views_by_content_type: Dict[str, int]
    top_content: List[Dict[str, Any]]

class ContentCreationData(AnalyticsResponse):
    """Content creation analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.CONTENT_CREATION
    total_created: int
    created_by_type: Dict[str, int]  # e.g., {'research': 5, 'story': 10}
    created_by_user: List[Dict[str, Any]]  # Top content creators

class SearchAnalyticsData(AnalyticsResponse):
    """Search analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.SEARCH_QUERIES
    total_searches: int
    top_queries: List[Dict[str, Any]]
    no_results_queries: List[Dict[str, Any]]
    search_conversion_rate: Optional[float]  # Percentage of searches that led to content views

class ApiUsageData(AnalyticsResponse):
    """API usage analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.API_USAGE
    total_requests: int
    requests_by_endpoint: Dict[str, int]
    error_rate: float
    average_response_time: float

class StorageUsageData(AnalyticsResponse):
    """Storage usage analytics data."""
    metric: AnalyticsMetric = AnalyticsMetric.STORAGE_USAGE
    total_used: int  # in bytes
    total_available: Optional[int] = None  # in bytes
    used_by_type: Dict[str, int]  # e.g., {'audio': 1024, 'images': 2048, 'documents': 512}
