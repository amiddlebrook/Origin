"""
Analytics models for tracking user activity and usage statistics.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserActivity(Base):
    """Tracks user activities across the application."""
    __tablename__ = 'user_activities'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    activity_type = Column(String(100), nullable=False)  # e.g., 'login', 'search', 'view_story', etc.
    activity_data = Column(JSON, nullable=True)  # Additional JSON data about the activity
    ip_address = Column(String(45), nullable=True)  # IPv6 addresses can be up to 45 chars
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="activities")

class SearchQuery(Base):
    """Tracks search queries and their results for analytics."""
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Null for anonymous users
    query = Column(String(500), nullable=False)
    result_count = Column(Integer, nullable=False, default=0)
    filters = Column(JSON, nullable=True)  # Any filters applied to the search
    search_type = Column(String(50), nullable=False)  # 'stories', 'oral_histories', or 'all'
    is_advanced = Column(Boolean, default=False)  # Whether advanced search was used
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="search_queries")

class ContentInteraction(Base):
    """Tracks user interactions with content (views, downloads, shares, etc.)."""
    __tablename__ = 'content_interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # Null for anonymous users
    content_type = Column(String(50), nullable=False)  # 'story', 'oral_history', etc.
    content_id = Column(Integer, nullable=False)  # ID of the content item
    interaction_type = Column(String(50), nullable=False)  # 'view', 'download', 'share', etc.
    interaction_data = Column(JSON, nullable=True)  # Additional data about the interaction
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Index for faster lookups by content
    __table_args__ = (
        {'sqlite_autoindex': True},
    )
    
    # Relationships
    user = relationship("User", back_populates="content_interactions")
