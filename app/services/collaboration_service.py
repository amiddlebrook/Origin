"""
Service for handling collaboration features like workspaces, comments, and annotations.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from app.database import get_db
from app.models_user import User
from app.models_collaboration import (
    Workspace, WorkspaceMember, WorkspaceResource, 
    Comment, Annotation, VersionHistory
)
from app.core.config import settings

logger = logging.getLogger(__name__)

class CollaborationService:
    """Service for handling collaboration features."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the collaboration service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    # Workspace methods
    async def create_workspace(
        self, 
        name: str, 
        user: User, 
        description: str = None, 
        is_public: bool = False
    ) -> Dict[str, Any]:
        """Create a new workspace.
        
        Args:
            name: Name of the workspace
            user: User creating the workspace
            description: Optional description
            is_public: Whether the workspace is public
            
        Returns:
            Dictionary with the created workspace data
        """
        workspace = Workspace(
            name=name,
            description=description,
            is_public=is_public,
            created_by=user
        )
        
        self.db.add(workspace)
        await self.db.flush()
        
        # Add the creator as an owner
        await self.add_workspace_member(workspace.id, user.id, "owner")
        
        await self.db.commit()
        await self.db.refresh(workspace)
        
        return workspace.to_dict()
    
    async def get_workspace(self, workspace_id: int, user: User = None) -> Optional[Dict[str, Any]]:
        """Get a workspace by ID with access control.
        
        Args:
            workspace_id: ID of the workspace to retrieve
            user: User requesting the workspace (for access control)
            
        Returns:
            Workspace data if found and accessible, None otherwise
        """
        query = select(Workspace).where(Workspace.id == workspace_id)
        
        # If user is provided, check access
        if user:
            query = query.join(
                WorkspaceMember,
                and_(
                    WorkspaceMember.workspace_id == Workspace.id,
                    WorkspaceMember.user_id == user.id
                )
            )
        else:
            # Only public workspaces if no user
            query = query.where(Workspace.is_public == True)
        
        result = await self.db.execute(query)
        workspace = result.scalars().first()
        
        return workspace.to_dict() if workspace else None
    
    async def list_workspaces(
        self, 
        user: User, 
        is_public: bool = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List workspaces accessible to a user.
        
        Args:
            user: User requesting the list
            is_public: Filter by public/private status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of workspace dictionaries
        """
        query = select(Workspace).join(
            WorkspaceMember,
            and_(
                WorkspaceMember.workspace_id == Workspace.id,
                WorkspaceMember.user_id == user.id
            )
        )
        
        if is_public is not None:
            query = query.where(Workspace.is_public == is_public)
            
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        workspaces = result.scalars().all()
        
        return [w.to_dict() for w in workspaces]
    
    async def update_workspace(
        self, 
        workspace_id: int, 
        user: User, 
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update a workspace.
        
        Args:
            workspace_id: ID of the workspace to update
            user: User making the update (must be workspace owner or admin)
            **updates: Fields to update
            
        Returns:
            Updated workspace data if successful, None otherwise
        """
        # Check if user has permission to update
        member = await self.get_workspace_member(workspace_id, user.id)
        if not member or member.role not in ["owner", "admin"]:
            return None
        
        # Update workspace
        result = await self.db.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(**updates, updated_at=datetime.utcnow())
            .returning(Workspace)
        )
        
        workspace = result.scalars().first()
        if workspace:
            await self.db.commit()
            await self.db.refresh(workspace)
            return workspace.to_dict()
        
        return None
    
    async def delete_workspace(self, workspace_id: int, user: User) -> bool:
        """Delete a workspace.
        
        Args:
            workspace_id: ID of the workspace to delete
            user: User requesting the deletion (must be workspace owner)
            
        Returns:
            True if deleted, False otherwise
        """
        # Check if user has permission to delete
        member = await self.get_workspace_member(workspace_id, user.id)
        if not member or member.role != "owner":
            return False
        
        # Delete the workspace (cascades to members and resources)
        result = await self.db.execute(
            delete(Workspace).where(Workspace.id == workspace_id)
        )
        
        if result.rowcount > 0:
            await self.db.commit()
            return True
        
        return False
    
    # Workspace member methods
    async def add_workspace_member(
        self, 
        workspace_id: int, 
        user_id: int, 
        role: str = "member"
    ) -> Optional[Dict[str, Any]]:
        """Add a member to a workspace.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user to add
            role: Role of the new member (owner, admin, member, viewer)
            
        Returns:
            Member data if added, None otherwise
        """
        # Check if user is already a member
        existing = await self.get_workspace_member(workspace_id, user_id)
        if existing:
            return existing.to_dict()
        
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role
        )
        
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        
        return member.to_dict()
    
    async def get_workspace_member(
        self, 
        workspace_id: int, 
        user_id: int
    ) -> Optional[WorkspaceMember]:
        """Get a workspace member.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user
            
        Returns:
            WorkspaceMember if found, None otherwise
        """
        result = await self.db.execute(
            select(WorkspaceMember)
            .where(
                (WorkspaceMember.workspace_id == workspace_id) &
                (WorkspaceMember.user_id == user_id)
            )
        )
        
        return result.scalars().first()
    
    async def update_workspace_member_role(
        self, 
        workspace_id: int, 
        user_id: int, 
        new_role: str,
        current_user: User
    ) -> Optional[Dict[str, Any]]:
        """Update a workspace member's role.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user whose role to update
            new_role: New role (owner, admin, member, viewer)
            current_user: User making the change (must be owner or admin)
            
        Returns:
            Updated member data if successful, None otherwise
        """
        # Check if current user has permission
        current_member = await self.get_workspace_member(workspace_id, current_user.id)
        if not current_member or current_member.role not in ["owner", "admin"]:
            return None
        
        # Prevent non-owners from changing owner role
        if new_role == "owner" and current_member.role != "owner":
            return None
        
        # Get the member to update
        member = await self.get_workspace_member(workspace_id, user_id)
        if not member:
            return None
        
        # Update the role
        member.role = new_role
        await self.db.commit()
        await self.db.refresh(member)
        
        return member.to_dict()
    
    async def remove_workspace_member(
        self, 
        workspace_id: int, 
        user_id: int,
        current_user: User
    ) -> bool:
        """Remove a member from a workspace.
        
        Args:
            workspace_id: ID of the workspace
            user_id: ID of the user to remove
            current_user: User making the request (must be owner or admin, or the user themselves)
            
        Returns:
            True if removed, False otherwise
        """
        # Check if current user has permission
        current_member = await self.get_workspace_member(workspace_id, current_user.id)
        if not current_member:
            return False
        
        # Allow users to remove themselves, or owners/admins to remove others
        if current_user.id != user_id and current_member.role not in ["owner", "admin"]:
            return False
        
        # Prevent removing the last owner
        if current_user.id == user_id and current_member.role == "owner":
            # Check if there are other owners
            result = await self.db.execute(
                select(func.count())
                .where(
                    (WorkspaceMember.workspace_id == workspace_id) &
                    (WorkspaceMember.role == "owner") &
                    (WorkspaceMember.user_id != user_id)
                )
            )
            other_owners = result.scalar()
            
            if other_owners == 0:
                return False
        
        # Remove the member
        result = await self.db.execute(
            delete(WorkspaceMember)
            .where(
                (WorkspaceMember.workspace_id == workspace_id) &
                (WorkspaceMember.user_id == user_id)
            )
        )
        
        if result.rowcount > 0:
            await self.db.commit()
            return True
        
        return False
    
    # Resource methods
    async def add_resource_to_workspace(
        self,
        workspace_id: int,
        resource_type: str,
        resource_id: int,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """Add a resource to a workspace.
        
        Args:
            workspace_id: ID of the workspace
            resource_type: Type of resource (research, story, etc.)
            resource_id: ID of the resource
            user: User adding the resource
            
        Returns:
            Resource data if added, None otherwise
        """
        # Check if user has permission to add resources
        member = await self.get_workspace_member(workspace_id, user.id)
        if not member or member.role not in ["owner", "admin", "member"]:
            return None
        
        # Check if resource is already in the workspace
        result = await self.db.execute(
            select(WorkspaceResource)
            .where(
                (WorkspaceResource.workspace_id == workspace_id) &
                (WorkspaceResource.resource_type == resource_type) &
                (WorkspaceResource.resource_id == resource_id)
            )
        )
        
        if result.scalars().first():
            return None  # Already exists
        
        # Add the resource
        resource = WorkspaceResource(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_id=resource_id,
            added_by=user
        )
        
        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)
        
        return resource.to_dict()
    
    async def remove_resource_from_workspace(
        self,
        workspace_id: int,
        resource_type: str,
        resource_id: int,
        user: User
    ) -> bool:
        """Remove a resource from a workspace.
        
        Args:
            workspace_id: ID of the workspace
            resource_type: Type of resource
            resource_id: ID of the resource
            user: User removing the resource
            
        Returns:
            True if removed, False otherwise
        """
        # Check if user has permission to remove resources
        member = await self.get_workspace_member(workspace_id, user.id)
        if not member or member.role not in ["owner", "admin"]:
            return False
        
        # Remove the resource
        result = await self.db.execute(
            delete(WorkspaceResource)
            .where(
                (WorkspaceResource.workspace_id == workspace_id) &
                (WorkspaceResource.resource_type == resource_type) &
                (WorkspaceResource.resource_id == resource_id)
            )
        )
        
        if result.rowcount > 0:
            await self.db.commit()
            return True
        
        return False
    
    # Comment methods
    async def add_comment(
        self,
        resource_type: str,
        resource_id: int,
        content: str,
        user: User,
        parent_comment_id: int = None
    ) -> Dict[str, Any]:
        """Add a comment to a resource.
        
        Args:
            resource_type: Type of resource being commented on
            resource_id: ID of the resource
            content: Comment content
            user: User adding the comment
            parent_comment_id: ID of the parent comment (for replies)
            
        Returns:
            Dictionary with the created comment data
        """
        comment = Comment(
            content=content,
            resource_type=resource_type,
            resource_id=resource_id,
            parent_comment_id=parent_comment_id,
            created_by=user
        )
        
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        
        return comment.to_dict()
    
    async def get_comments(
        self,
        resource_type: str,
        resource_id: int,
        include_replies: bool = True
    ) -> List[Dict[str, Any]]:
        """Get comments for a resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            include_replies: Whether to include replies to comments
            
        Returns:
            List of comment dictionaries
        """
        query = select(Comment).where(
            (Comment.resource_type == resource_type) &
            (Comment.resource_id == resource_id) &
            (Comment.parent_comment_id.is_(None) if include_replies else True) &
            (Comment.is_deleted == False)
        ).order_by(Comment.created_at.asc())
        
        if include_replies:
            query = query.options(
                selectinload(Comment.replies)
                .selectinload(Comment.created_by)
            )
        
        result = await self.db.execute(query)
        comments = result.scalars().all()
        
        return [c.to_dict(include_replies=include_replies) for c in comments]
    
    async def update_comment(
        self,
        comment_id: int,
        content: str,
        user: User
    ) -> Optional[Dict[str, Any]]:
        """Update a comment.
        
        Args:
            comment_id: ID of the comment to update
            content: New comment content
            user: User updating the comment
            
        Returns:
            Updated comment data if successful, None otherwise
        """
        result = await self.db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .options(selectinload(Comment.created_by))
        )
        comment = result.scalars().first()
        
        if not comment or comment.created_by_id != user.id:
            return None
        
        comment.content = content
        await self.db.commit()
        await self.db.refresh(comment)
        
        return comment.to_dict()
    
    async def delete_comment(self, comment_id: int, user: User) -> bool:
        """Delete a comment (soft delete).
        
        Args:
            comment_id: ID of the comment to delete
            user: User deleting the comment
            
        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            select(Comment)
            .where(Comment.id == comment_id)
            .with_for_update()
        )
        comment = result.scalars().first()
        
        if not comment:
            return False
        
        # Only allow the comment author or an admin to delete
        if comment.created_by_id != user.id:
            # Check if user is an admin for the workspace
            # This would require additional logic to check workspace permissions
            return False
        
        # Soft delete the comment
        comment.is_deleted = True
        await self.db.commit()
        
        return True
    
    # Annotation methods
    async def add_annotation(
        self,
        resource_type: str,
        resource_id: int,
        annotation_type: str,
        metadata: Dict[str, Any],
        user: User,
        content: str = None,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """Add an annotation to a resource.
        
        Args:
            resource_type: Type of resource being annotated
            resource_id: ID of the resource
            annotation_type: Type of annotation (highlight, note, etc.)
            metadata: Annotation metadata (position, color, etc.)
            user: User adding the annotation
            content: Optional annotation content
            is_private: Whether the annotation is private
            
        Returns:
            Dictionary with the created annotation data
        """
        annotation = Annotation(
            resource_type=resource_type,
            resource_id=resource_id,
            annotation_type=annotation_type,
            content=content,
            metadata=metadata,
            created_by=user,
            is_private=is_private
        )
        
        self.db.add(annotation)
        await self.db.commit()
        await self.db.refresh(annotation)
        
        return annotation.to_dict()
    
    async def get_annotations(
        self,
        resource_type: str,
        resource_id: int,
        user: User = None,
        annotation_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get annotations for a resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            user: User requesting the annotations (for access control)
            annotation_type: Filter by annotation type
            
        Returns:
            List of annotation dictionaries
        """
        query = select(Annotation).where(
            (Annotation.resource_type == resource_type) &
            (Annotation.resource_id == resource_id)
        )
        
        # Filter by type if specified
        if annotation_type:
            query = query.where(Annotation.annotation_type == annotation_type)
        
        # Apply privacy filter
        if user:
            query = query.where(
                (Annotation.is_private == False) |
                (Annotation.created_by_id == user.id)
            )
        else:
            query = query.where(Annotation.is_private == False)
        
        result = await self.db.execute(
            query.options(selectinload(Annotation.created_by))
        )
        annotations = result.scalars().all()
        
        return [a.to_dict() for a in annotations]
    
    async def update_annotation(
        self,
        annotation_id: int,
        user: User,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update an annotation.
        
        Args:
            annotation_id: ID of the annotation to update
            user: User updating the annotation
            **updates: Fields to update
            
        Returns:
            Updated annotation data if successful, None otherwise
        """
        result = await self.db.execute(
            select(Annotation)
            .where(Annotation.id == annotation_id)
            .options(selectinload(Annotation.created_by))
            .with_for_update()
        )
        annotation = result.scalars().first()
        
        if not annotation or annotation.created_by_id != user.id:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(annotation, key):
                setattr(annotation, key, value)
        
        annotation.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(annotation)
        
        return annotation.to_dict()
    
    async def delete_annotation(self, annotation_id: int, user: User) -> bool:
        """Delete an annotation.
        
        Args:
            annotation_id: ID of the annotation to delete
            user: User deleting the annotation
            
        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(
            select(Annotation)
            .where(Annotation.id == annotation_id)
            .with_for_update()
        )
        annotation = result.scalars().first()
        
        if not annotation or annotation.created_by_id != user.id:
            return False
        
        await self.db.delete(annotation)
        await self.db.commit()
        
        return True
    
    # Version history methods
    async def create_version(
        self,
        resource_type: str,
        resource_id: int,
        changes: Dict[str, Any],
        user: User,
        snapshot: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new version of a resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            changes: Dictionary describing the changes in this version
            user: User creating the version
            snapshot: Optional full snapshot of the resource
            
        Returns:
            Dictionary with the created version data
        """
        # Get the current version number
        result = await self.db.execute(
            select(func.max(VersionHistory.version_number))
            .where(
                (VersionHistory.resource_type == resource_type) &
                (VersionHistory.resource_id == resource_id)
            )
        )
        
        current_version = result.scalar() or 0
        new_version = current_version + 1
        
        version = VersionHistory(
            resource_type=resource_type,
            resource_id=resource_id,
            version_number=new_version,
            changes=changes,
            snapshot=snapshot,
            created_by=user
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        
        return version.to_dict()
    
    async def get_version_history(
        self,
        resource_type: str,
        resource_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get version history for a resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            limit: Maximum number of versions to return
            offset: Offset for pagination
            
        Returns:
            List of version dictionaries
        """
        result = await self.db.execute(
            select(VersionHistory)
            .where(
                (VersionHistory.resource_type == resource_type) &
                (VersionHistory.resource_id == resource_id)
            )
            .order_by(VersionHistory.version_number.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(VersionHistory.created_by))
        )
        
        versions = result.scalars().all()
        return [v.to_dict() for v in versions]
    
    async def get_version(
        self,
        resource_type: str,
        resource_id: int,
        version_number: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific version of a resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of the resource
            version_number: Version number to retrieve
            
        Returns:
            Version data if found, None otherwise
        """
        result = await self.db.execute(
            select(VersionHistory)
            .where(
                (VersionHistory.resource_type == resource_type) &
                (VersionHistory.resource_id == resource_id) &
                (VersionHistory.version_number == version_number)
            )
            .options(selectinload(VersionHistory.created_by))
        )
        
        version = result.scalars().first()
        return version.to_dict() if version else None

# Helper function to get the collaboration service
def get_collaboration_service(db: AsyncSession = Depends(get_db)):
    return CollaborationService(db)
