"""
Service for handling bulk operations on data.
"""
import logging
from typing import List, Dict, Any, Optional, Union, Type, TypeVar, Generic
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload
from pydantic import BaseModel, ValidationError

from app.database import get_db
from app.models import Research
from app.models_story import NameStory, OralHistory
from app.models_collaboration import WorkspaceResource, WorkspaceMember
from app.auth.utils import get_password_hash
from app.core.config import settings

logger = logging.getLogger(__name__)

# Type variables for generic operations
T = TypeVar('T')
P = TypeVar('P', bound=BaseModel)

class BulkOperationError(Exception):
    """Exception raised for errors in bulk operations."""
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None):
        self.message = message
        self.errors = errors or {}
        super().__init__(self.message)

class BulkOperationsService:
    """Service for handling bulk operations on data."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the bulk operations service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    # Generic bulk create method
    async def bulk_create(
        self,
        model: Type[T],
        items: List[Dict[str, Any]],
        user_id: int,
        skip_duplicates: bool = False,
        unique_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Bulk create items of a given model.
        
        Args:
            model: SQLAlchemy model class
            items: List of dictionaries with item data
            user_id: ID of the user performing the operation
            skip_duplicates: Whether to skip duplicate items
            unique_fields: List of field names that should be unique
            
        Returns:
            Dictionary with operation results
        """
        created = 0
        skipped = 0
        errors = []
        
        for index, item_data in enumerate(items):
            try:
                # Set created_by and updated_at fields if they exist
                if hasattr(model, 'created_by_id'):
                    item_data['created_by_id'] = user_id
                if hasattr(model, 'updated_at'):
                    item_data['updated_at'] = datetime.utcnow()
                
                # Check for duplicates if requested
                if skip_duplicates and unique_fields:
                    filters = []
                    for field in unique_fields:
                        if field in item_data:
                            filters.append(getattr(model, field) == item_data[field])
                    
                    if filters:
                        existing = await self.db.execute(
                            select(func.count()).select_from(model).where(and_(*filters))
                        )
                        if existing.scalar() > 0:
                            skipped += 1
                            continue
                
                # Create the item
                item = model(**item_data)
                self.db.add(item)
                created += 1
                
                # Commit periodically to avoid large transactions
                if created % 100 == 0:
                    await self.db.commit()
                    await self.db.refresh(item)
            
            except Exception as e:
                errors.append({
                    'index': index,
                    'error': str(e),
                    'item': item_data
                })
                logger.error(f"Error creating item at index {index}: {str(e)}")
        
        # Final commit
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise BulkOperationError("Error committing bulk create operation", {"detail": str(e)})
        
        return {
            'total': len(items),
            'created': created,
            'skipped': skipped,
            'errors': errors
        }
    
    # Generic bulk update method
    async def bulk_update(
        self,
        model: Type[T],
        items: List[Dict[str, Any]],
        user_id: int,
        id_field: str = 'id',
        update_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Bulk update items of a given model.
        
        Args:
            model: SQLAlchemy model class
            items: List of dictionaries with item data, must include the ID field
            user_id: ID of the user performing the operation
            id_field: Name of the ID field (default: 'id')
            update_fields: List of fields that can be updated (None means all fields)
            
        Returns:
            Dictionary with operation results
        """
        updated = 0
        not_found = 0
        errors = []
        
        for index, item_data in enumerate(items):
            if id_field not in item_data:
                errors.append({
                    'index': index,
                    'error': f"Missing required field: {id_field}",
                    'item': item_data
                })
                continue
            
            try:
                # Get the item ID
                item_id = item_data[id_field]
                
                # Build update data
                update_data = {}
                for field, value in item_data.items():
                    if field == id_field:
                        continue
                    if update_fields is None or field in update_fields:
                        update_data[field] = value
                
                # Add updated_at if the model has it
                if hasattr(model, 'updated_at'):
                    update_data['updated_at'] = datetime.utcnow()
                
                # Perform the update
                result = await self.db.execute(
                    update(model)
                    .where(getattr(model, id_field) == item_id)
                    .values(**update_data)
                )
                
                if result.rowcount > 0:
                    updated += 1
                else:
                    not_found += 1
                
                # Commit periodically to avoid large transactions
                if (updated + not_found) % 100 == 0:
                    await self.db.commit()
            
            except Exception as e:
                errors.append({
                    'index': index,
                    'error': str(e),
                    'item': item_data
                })
                logger.error(f"Error updating item at index {index}: {str(e)}")
        
        # Final commit
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise BulkOperationError("Error committing bulk update operation", {"detail": str(e)})
        
        return {
            'total': len(items),
            'updated': updated,
            'not_found': not_found,
            'errors': errors
        }
    
    # Generic bulk delete method
    async def bulk_delete(
        self,
        model: Type[T],
        item_ids: List[Any],
        user_id: int,
        id_field: str = 'id'
    ) -> Dict[str, Any]:
        """Bulk delete items of a given model.
        
        Args:
            model: SQLAlchemy model class
            item_ids: List of item IDs to delete
            user_id: ID of the user performing the operation
            id_field: Name of the ID field (default: 'id')
            
        Returns:
            Dictionary with operation results
        """
        deleted = 0
        not_found = 0
        errors = []
        
        # Delete in batches to avoid large transactions
        batch_size = 100
        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i:i + batch_size]
            
            try:
                # Build the delete query
                query = delete(model).where(getattr(model, id_field).in_(batch))
                
                # Execute the delete
                result = await self.db.execute(query)
                deleted += result.rowcount
                not_found += len(batch) - result.rowcount
                
                # Commit the batch
                await self.db.commit()
                
            except Exception as e:
                await self.db.rollback()
                errors.extend([{
                    'id': item_id,
                    'error': str(e)
                } for item_id in batch])
                logger.error(f"Error deleting batch {i//batch_size + 1}: {str(e)}")
        
        return {
            'total': len(item_ids),
            'deleted': deleted,
            'not_found': not_found,
            'errors': errors
        }
    
    # Specific bulk operations for research
    async def bulk_create_research(
        self,
        items: List[Dict[str, Any]],
        user_id: int,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """Bulk create research items."""
        return await self.bulk_create(
            model=Research,
            items=items,
            user_id=user_id,
            skip_duplicates=skip_duplicates,
            unique_fields=['title', 'created_by_id']
        )
    
    async def bulk_update_research(
        self,
        items: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk update research items."""
        return await self.bulk_update(
            model=Research,
            items=items,
            user_id=user_id,
            update_fields=[
                'title', 'description', 'content', 'is_public', 
                'tags', 'metadata', 'status', 'updated_at'
            ]
        )
    
    async def bulk_delete_research(
        self,
        research_ids: List[int],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk delete research items."""
        return await self.bulk_delete(
            model=Research,
            item_ids=research_ids,
            user_id=user_id
        )
    
    # Specific bulk operations for stories
    async def bulk_create_stories(
        self,
        items: List[Dict[str, Any]],
        user_id: int,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """Bulk create name stories."""
        return await self.bulk_create(
            model=NameStory,
            items=items,
            user_id=user_id,
            skip_duplicates=skip_duplicates,
            unique_fields=['title', 'name', 'created_by_id']
        )
    
    async def bulk_update_stories(
        self,
        items: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk update name stories."""
        return await self.bulk_update(
            model=NameStory,
            items=items,
            user_id=user_id,
            update_fields=[
                'title', 'name', 'content', 'is_public', 
                'tags', 'metadata', 'status', 'updated_at'
            ]
        )
    
    async def bulk_delete_stories(
        self,
        story_ids: List[int],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk delete name stories."""
        return await self.bulk_delete(
            model=NameStory,
            item_ids=story_ids,
            user_id=user_id
        )
    
    # Specific bulk operations for oral histories
    async def bulk_create_oral_histories(
        self,
        items: List[Dict[str, Any]],
        user_id: int,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """Bulk create oral histories."""
        return await self.bulk_create(
            model=OralHistory,
            items=items,
            user_id=user_id,
            skip_duplicates=skip_duplicates,
            unique_fields=['title', 'interviewee_name', 'created_by_id']
        )
    
    async def bulk_update_oral_histories(
        self,
        items: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk update oral histories."""
        return await self.bulk_update(
            model=OralHistory,
            items=items,
            user_id=user_id,
            update_fields=[
                'title', 'interviewee_name', 'content', 'is_public',
                'tags', 'metadata', 'status', 'transcript', 'audio_url',
                'video_url', 'duration_seconds', 'recorded_date', 'updated_at'
            ]
        )
    
    async def bulk_delete_oral_histories(
        self,
        oral_history_ids: List[int],
        user_id: int
    ) -> Dict[str, Any]:
        """Bulk delete oral histories."""
        return await self.bulk_delete(
            model=OralHistory,
            item_ids=oral_history_ids,
            user_id=user_id
        )
    
    # Bulk operations for workspace resources
    async def bulk_add_to_workspace(
        self,
        workspace_id: int,
        resources: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Bulk add resources to a workspace.
        
        Args:
            workspace_id: ID of the workspace
            resources: List of resources to add, each with 'resource_type' and 'resource_id'
            user_id: ID of the user performing the operation
            
        Returns:
            Dictionary with operation results
        """
        added = 0
        skipped = 0
        errors = []
        
        # Check if user has permission to add to workspace
        member = await self.db.execute(
            select(WorkspaceMember)
            .where(
                (WorkspaceMember.workspace_id == workspace_id) &
                (WorkspaceMember.user_id == user_id)
            )
        )
        member = member.scalars().first()
        
        if not member or member.role not in ['owner', 'admin', 'member']:
            raise BulkOperationError("You don't have permission to add resources to this workspace")
        
        for index, resource in enumerate(resources):
            try:
                resource_type = resource.get('resource_type')
                resource_id = resource.get('resource_id')
                
                if not resource_type or resource_id is None:
                    raise ValueError("Both resource_type and resource_id are required")
                
                # Check if the resource is already in the workspace
                existing = await self.db.execute(
                    select(WorkspaceResource)
                    .where(
                        (WorkspaceResource.workspace_id == workspace_id) &
                        (WorkspaceResource.resource_type == resource_type) &
                        (WorkspaceResource.resource_id == resource_id)
                    )
                )
                
                if existing.scalars().first():
                    skipped += 1
                    continue
                
                # Add the resource to the workspace
                workspace_resource = WorkspaceResource(
                    workspace_id=workspace_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    added_by_id=user_id
                )
                
                self.db.add(workspace_resource)
                added += 1
                
                # Commit periodically to avoid large transactions
                if (added + skipped) % 100 == 0:
                    await self.db.commit()
            
            except Exception as e:
                errors.append({
                    'index': index,
                    'error': str(e),
                    'resource': resource
                })
                logger.error(f"Error adding resource at index {index}: {str(e)}")
        
        # Final commit
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise BulkOperationError("Error committing bulk add to workspace operation", {"detail": str(e)})
        
        return {
            'total': len(resources),
            'added': added,
            'skipped': skipped,
            'errors': errors
        }
    
    async def bulk_remove_from_workspace(
        self,
        workspace_id: int,
        resource_ids: List[Dict[str, Any]],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Bulk remove resources from a workspace.
        
        Args:
            workspace_id: ID of the workspace
            resource_ids: List of resource identifiers, each with 'resource_type' and 'resource_id'
            user_id: ID of the user performing the operation
            
        Returns:
            Dictionary with operation results
        """
        removed = 0
        not_found = 0
        errors = []
        
        # Check if user has permission to remove from workspace
        member = await self.db.execute(
            select(WorkspaceMember)
            .where(
                (WorkspaceMember.workspace_id == workspace_id) &
                (WorkspaceMember.user_id == user_id) &
                (WorkspaceMember.role.in_(['owner', 'admin']))
            )
        )
        member = member.scalars().first()
        
        if not member:
            raise BulkOperationError("You don't have permission to remove resources from this workspace")
        
        # Remove in batches to avoid large transactions
        batch_size = 100
        for i in range(0, len(resource_ids), batch_size):
            batch = resource_ids[i:i + batch_size]
            
            try:
                # Build the delete conditions
                conditions = [
                    and_(
                        WorkspaceResource.workspace_id == workspace_id,
                        WorkspaceResource.resource_type == r['resource_type'],
                        WorkspaceResource.resource_id == r['resource_id']
                    )
                    for r in batch
                ]
                
                # Execute the delete
                result = await self.db.execute(
                    delete(WorkspaceResource)
                    .where(or_(*conditions))
                )
                
                removed += result.rowcount
                not_found += len(batch) - result.rowcount
                
                # Commit the batch
                await self.db.commit()
                
            except Exception as e:
                await self.db.rollback()
                errors.extend([{
                    'resource': r,
                    'error': str(e)
                } for r in batch])
                logger.error(f"Error removing batch {i//batch_size + 1}: {str(e)}")
        
        return {
            'total': len(resource_ids),
            'removed': removed,
            'not_found': not_found,
            'errors': errors
        }

from fastapi import Depends
# Helper function to get the bulk operations service
def get_bulk_operations_service(db: AsyncSession = Depends(get_db)):
    return BulkOperationsService(db)
