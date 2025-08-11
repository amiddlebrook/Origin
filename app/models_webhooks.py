"""
Database models for webhooks.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class WebhookEventType(str, Enum):
    """Types of events that can trigger webhooks."""
    RESEARCH_CREATED = "research.created"
    RESEARCH_UPDATED = "research.updated"
    RESEARCH_DELETED = "research.deleted"
    STORY_CREATED = "story.created"
    STORY_UPDATED = "story.updated"
    STORY_DELETED = "story.deleted"
    ORAL_HISTORY_CREATED = "oral_history.created"
    ORAL_HISTORY_UPDATED = "oral_history.updated"
    ORAL_HISTORY_DELETED = "oral_history.deleted"
    COMMENT_CREATED = "comment.created"
    COMMENT_UPDATED = "comment.updated"
    COMMENT_DELETED = "comment.deleted"
    ANNOTATION_CREATED = "annotation.created"
    ANNOTATION_UPDATED = "annotation.updated"
    ANNOTATION_DELETED = "annotation.deleted"
    WORKSPACE_CREATED = "workspace.created"
    WORKSPACE_UPDATED = "workspace.updated"
    WORKSPACE_DELETED = "workspace.deleted"
    MEMBER_ADDED = "member.added"
    MEMBER_REMOVED = "member.removed"
    MEMBER_UPDATED = "member.updated"

class WebhookStatus(str, Enum):
    """Status of a webhook delivery."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"

class Webhook(Base):
    """Webhook configuration for receiving events."""
    __tablename__ = "webhooks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=True)  # For HMAC signature
    events: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # List of WebhookEventType values
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by: Mapped["User"] = relationship("User")
    deliveries: Mapped[List["WebhookDelivery"]] = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by_id": self.created_by_id
        }

class WebhookDelivery(Base):
    """Record of a webhook delivery attempt."""
    __tablename__ = "webhook_deliveries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    webhook_id: Mapped[int] = mapped_column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False)  # WebhookEventType value
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(SQLEnum(WebhookStatus), default=WebhookStatus.PENDING, nullable=False)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    webhook: Mapped[Webhook] = relationship("Webhook", back_populates="deliveries")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event": self.event,
            "status": self.status,
            "response_status": self.response_status,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None
        }
