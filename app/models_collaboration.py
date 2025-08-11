"""
Database models for collaboration features.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class Workspace(Base):
    """A shared workspace for collaboration."""
    __tablename__ = "workspaces"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="created_workspaces")
    members: Mapped[List["WorkspaceMember"]] = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    resources: Mapped[List["WorkspaceResource"]] = relationship("WorkspaceResource", back_populates="workspace", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by_id": self.created_by_id,
            "member_count": len(self.members)
        }

class WorkspaceMember(Base):
    """Association table for workspace members and their roles."""
    __tablename__ = "workspace_members"
    
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")  # 'owner', 'admin', 'member', 'viewer'
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="workspace_memberships")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "user": {
                "id": self.user.id,
                "email": self.user.email,
                "full_name": getattr(self.user, 'full_name', None)
            }
        }

class WorkspaceResource(Base):
    """Resources (research, stories, etc.) associated with a workspace."""
    __tablename__ = "workspace_resources"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'research', 'story', 'oral_history', etc.
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    added_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="resources")
    added_by: Mapped["User"] = relationship("User")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "added_at": self.added_at.isoformat(),
            "added_by_id": self.added_by_id
        }

class Comment(Base):
    """Comments on resources."""
    __tablename__ = "comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'research', 'story', 'oral_history', etc.
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_comment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("comments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    created_by: Mapped["User"] = relationship("User")
    parent_comment: Mapped[Optional["Comment"]] = relationship("Comment", remote_side=[id], back_populates="replies")
    replies: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_comment", cascade="all, delete-orphan")
    
    def to_dict(self, include_replies: bool = True) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "content": self.content,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "parent_comment_id": self.parent_comment_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": {
                "id": self.created_by.id,
                "email": self.created_by.email,
                "full_name": getattr(self.created_by, 'full_name', None)
            },
            "is_deleted": self.is_deleted
        }
        
        if include_replies and self.replies:
            result["replies"] = [reply.to_dict() for reply in self.replies]
            
        return result

class Annotation(Base):
    """Annotations on resources (e.g., highlights, notes on text)."""
    __tablename__ = "annotations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'research', 'story', 'oral_history', etc.
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    annotation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'highlight', 'note', 'comment', etc.
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)  # For storing position, color, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    created_by: Mapped["User"] = relationship("User")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "annotation_type": self.annotation_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": {
                "id": self.created_by.id,
                "email": self.created_by.email,
                "full_name": getattr(self.created_by, 'full_name', None)
            },
            "is_private": self.is_private
        }

class VersionHistory(Base):
    """Version history for resources."""
    __tablename__ = "version_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'research', 'story', 'oral_history', etc.
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    changes: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)  # What changed
    snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Full snapshot of the resource at this version
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by: Mapped["User"] = relationship("User")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "version_number": self.version_number,
            "changes": self.changes,
            "created_at": self.created_at.isoformat(),
            "created_by": {
                "id": self.created_by.id,
                "email": self.created_by.email,
                "full_name": getattr(self.created_by, 'full_name', None)
            }
        }
