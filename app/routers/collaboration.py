"""
API endpoints for collaboration features.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.services.collaboration_service import CollaborationService, get_collaboration_service
from app.core.config import settings

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# Workspace endpoints
@router.post("/workspaces/", status_code=status.HTTP_201_CREATED)
async def create_workspace(
    name: str,
    description: Optional[str] = None,
    is_public: bool = False,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Create a new workspace.
    
    - **name**: Name of the workspace
    - **description**: Optional description
    - **is_public**: Whether the workspace is public
    """
    workspace = await service.create_workspace(
        name=name,
        user=current_user,
        description=description,
        is_public=is_public
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create workspace"
        )
    
    return workspace

@router.get("/workspaces/", response_model=List[Dict[str, Any]])
async def list_workspaces(
    is_public: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    List workspaces accessible to the current user.
    
    - **is_public**: Filter by public/private status
    - **limit**: Maximum number of results to return (1-1000)
    - **offset**: Number of results to skip for pagination
    """
    workspaces = await service.list_workspaces(
        user=current_user,
        is_public=is_public,
        limit=limit,
        offset=offset
    )
    
    return workspaces

@router.get("/workspaces/{workspace_id}", response_model=Dict[str, Any])
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Get a workspace by ID.
    
    - **workspace_id**: ID of the workspace to retrieve
    """
    workspace = await service.get_workspace(workspace_id, current_user)
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    
    return workspace

@router.patch("/workspaces/{workspace_id}", response_model=Dict[str, Any])
async def update_workspace(
    workspace_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Update a workspace.
    
    - **workspace_id**: ID of the workspace to update
    - **name**: New name for the workspace
    - **description**: New description
    - **is_public**: Whether the workspace is public
    """
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if is_public is not None:
        updates["is_public"] = is_public
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    workspace = await service.update_workspace(
        workspace_id=workspace_id,
        user=current_user,
        **updates
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    
    return workspace

@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Delete a workspace.
    
    - **workspace_id**: ID of the workspace to delete
    """
    success = await service.delete_workspace(workspace_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    
    return None

# Workspace member endpoints
@router.post("/workspaces/{workspace_id}/members/{user_id}", response_model=Dict[str, Any])
async def add_workspace_member(
    workspace_id: int,
    user_id: int,
    role: str = Query("member", regex="^(owner|admin|member|viewer)$"),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Add a member to a workspace.
    
    - **workspace_id**: ID of the workspace
    - **user_id**: ID of the user to add
    - **role**: Role for the new member (owner, admin, member, viewer)
    """
    member = await service.add_workspace_member(workspace_id, user_id, role)
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add member to workspace"
        )
    
    return member

@router.patch("/workspaces/{workspace_id}/members/{user_id}", response_model=Dict[str, Any])
async def update_workspace_member_role(
    workspace_id: int,
    user_id: int,
    role: str = Query(..., regex="^(owner|admin|member|viewer)$"),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Update a workspace member's role.
    
    - **workspace_id**: ID of the workspace
    - **user_id**: ID of the user whose role to update
    - **role**: New role (owner, admin, member, viewer)
    """
    member = await service.update_workspace_member_role(
        workspace_id=workspace_id,
        user_id=user_id,
        new_role=role,
        current_user=current_user
    )
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update member role"
        )
    
    return member

@router.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Remove a member from a workspace.
    
    - **workspace_id**: ID of the workspace
    - **user_id**: ID of the user to remove
    """
    success = await service.remove_workspace_member(
        workspace_id=workspace_id,
        user_id=user_id,
        current_user=current_user
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove member from workspace"
        )
    
    return None

# Resource endpoints
@router.post("/workspaces/{workspace_id}/resources/", response_model=Dict[str, Any])
async def add_workspace_resource(
    workspace_id: int,
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Add a resource to a workspace.
    
    - **workspace_id**: ID of the workspace
    - **resource_type**: Type of resource (research, story, oral_history)
    - **resource_id**: ID of the resource
    """
    resource = await service.add_resource_to_workspace(
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        user=current_user
    )
    
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add resource to workspace"
        )
    
    return resource

@router.delete("/workspaces/{workspace_id}/resources/{resource_type}/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_resource(
    workspace_id: int,
    resource_type: str,
    resource_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Remove a resource from a workspace.
    
    - **workspace_id**: ID of the workspace
    - **resource_type**: Type of resource
    - **resource_id**: ID of the resource
    """
    success = await service.remove_resource_from_workspace(
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
        user=current_user
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove resource from workspace"
        )
    
    return None

# Comment endpoints
@router.post("/comments/", status_code=status.HTTP_201_CREATED)
async def create_comment(
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    content: str = Query(..., min_length=1, max_length=2000),
    parent_comment_id: Optional[int] = Query(None, ge=1),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Add a comment to a resource.
    
    - **resource_type**: Type of resource being commented on
    - **resource_id**: ID of the resource
    - **content**: Comment content (1-2000 characters)
    - **parent_comment_id**: ID of the parent comment (for replies)
    """
    comment = await service.add_comment(
        resource_type=resource_type,
        resource_id=resource_id,
        content=content,
        user=current_user,
        parent_comment_id=parent_comment_id
    )
    
    return comment

@router.get("/comments/", response_model=List[Dict[str, Any]])
async def get_comments(
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    include_replies: bool = Query(True, description="Include replies to comments"),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Get comments for a resource.
    
    - **resource_type**: Type of resource
    - **resource_id**: ID of the resource
    - **include_replies**: Whether to include replies to comments
    """
    comments = await service.get_comments(
        resource_type=resource_type,
        resource_id=resource_id,
        include_replies=include_replies
    )
    
    return comments

@router.patch("/comments/{comment_id}", response_model=Dict[str, Any])
async def update_comment(
    comment_id: int,
    content: str = Query(..., min_length=1, max_length=2000),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Update a comment.
    
    - **comment_id**: ID of the comment to update
    - **content**: New comment content (1-2000 characters)
    """
    comment = await service.update_comment(
        comment_id=comment_id,
        content=content,
        user=current_user
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or access denied"
        )
    
    return comment

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Delete a comment.
    
    - **comment_id**: ID of the comment to delete
    """
    success = await service.delete_comment(comment_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or access denied"
        )
    
    return None

# Annotation endpoints
@router.post("/annotations/", status_code=status.HTTP_201_CREATED)
async def create_annotation(
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    annotation_type: str = Query(..., regex="^(highlight|note|comment)$"),
    content: Optional[str] = Query(None, max_length=2000),
    is_private: bool = Query(False),
    metadata: dict = {},
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Add an annotation to a resource.
    
    - **resource_type**: Type of resource being annotated
    - **resource_id**: ID of the resource
    - **annotation_type**: Type of annotation (highlight, note, comment)
    - **content**: Annotation content (optional, max 2000 chars)
    - **is_private**: Whether the annotation is private
    - **metadata**: Additional metadata (position, color, etc.)
    """
    annotation = await service.add_annotation(
        resource_type=resource_type,
        resource_id=resource_id,
        annotation_type=annotation_type,
        content=content,
        metadata=metadata,
        user=current_user,
        is_private=is_private
    )
    
    return annotation

@router.get("/annotations/", response_model=List[Dict[str, Any]])
async def get_annotations(
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    annotation_type: Optional[str] = Query(None, regex="^(highlight|note|comment)$"),
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Get annotations for a resource.
    
    - **resource_type**: Type of resource
    - **resource_id**: ID of the resource
    - **annotation_type**: Filter by annotation type
    """
    annotations = await service.get_annotations(
        resource_type=resource_type,
        resource_id=resource_id,
        user=current_user,
        annotation_type=annotation_type
    )
    
    return annotations

@router.patch("/annotations/{annotation_id}", response_model=Dict[str, Any])
async def update_annotation(
    annotation_id: int,
    content: Optional[str] = Query(None, max_length=2000),
    is_private: Optional[bool] = None,
    metadata: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Update an annotation.
    
    - **annotation_id**: ID of the annotation to update
    - **content**: New annotation content (optional, max 2000 chars)
    - **is_private**: New privacy setting
    - **metadata**: Updated metadata (position, color, etc.)
    """
    updates = {}
    if content is not None:
        updates["content"] = content
    if is_private is not None:
        updates["is_private"] = is_private
    if metadata is not None:
        updates["metadata"] = metadata
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    annotation = await service.update_annotation(
        annotation_id=annotation_id,
        user=current_user,
        **updates
    )
    
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found or access denied"
        )
    
    return annotation

@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation(
    annotation_id: int,
    current_user: User = Depends(get_current_user),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Delete an annotation.
    
    - **annotation_id**: ID of the annotation to delete
    """
    success = await service.delete_annotation(annotation_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotation not found or access denied"
        )
    
    return None

# Version history endpoints
@router.get("/versions/", response_model=List[Dict[str, Any]])
async def get_version_history(
    resource_type: str = Query(..., regex="^(research|story|oral_history)$"),
    resource_id: int = Query(..., ge=1),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Get version history for a resource.
    
    - **resource_type**: Type of resource
    - **resource_id**: ID of the resource
    - **limit**: Maximum number of versions to return (1-1000)
    - **offset**: Number of results to skip for pagination
    """
    versions = await service.get_version_history(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
        offset=offset
    )
    
    return versions

@router.get("/versions/{version_id}", response_model=Dict[str, Any])
async def get_version(
    resource_type: str,
    resource_id: int,
    version_number: int,
    service: CollaborationService = Depends(get_collaboration_service)
):
    """
    Get a specific version of a resource.
    
    - **resource_type**: Type of resource
    - **resource_id**: ID of the resource
    - **version_number**: Version number to retrieve
    """
    version = await service.get_version(
        resource_type=resource_type,
        resource_id=resource_id,
        version_number=version_number
    )
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )
    
    return version
