"""
API endpoints for bulk operations.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.services.bulk_operations import BulkOperationsService, BulkOperationError, get_bulk_operations_service
from app.core.config import settings

router = APIRouter(prefix="/bulk", tags=["bulk"])

# Research bulk operations
@router.post("/research/create", status_code=status.HTTP_201_CREATED)
async def bulk_create_research(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    skip_duplicates: bool = Query(True, description="Skip duplicate items"),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk create research items.
    
    - **items**: List of research items to create
    - **skip_duplicates**: Whether to skip duplicate items (based on title and creator)
    """
    try:
        result = await service.bulk_create_research(
            items=items,
            user_id=current_user.id,
            skip_duplicates=skip_duplicates
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/research/update", status_code=status.HTTP_200_OK)
async def bulk_update_research(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk update research items.
    
    - **items**: List of research items to update (must include 'id' field)
    """
    try:
        result = await service.bulk_update_research(
            items=items,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/research/delete", status_code=status.HTTP_200_OK)
async def bulk_delete_research(
    research_ids: List[int] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk delete research items.
    
    - **research_ids**: List of research item IDs to delete
    """
    try:
        result = await service.bulk_delete_research(
            research_ids=research_ids,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Stories bulk operations
@router.post("/stories/create", status_code=status.HTTP_201_CREATED)
async def bulk_create_stories(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    skip_duplicates: bool = Query(True, description="Skip duplicate items"),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk create name stories.
    
    - **items**: List of name stories to create
    - **skip_duplicates**: Whether to skip duplicate items (based on title, name, and creator)
    """
    try:
        result = await service.bulk_create_stories(
            items=items,
            user_id=current_user.id,
            skip_duplicates=skip_duplicates
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/stories/update", status_code=status.HTTP_200_OK)
async def bulk_update_stories(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk update name stories.
    
    - **items**: List of name stories to update (must include 'id' field)
    """
    try:
        result = await service.bulk_update_stories(
            items=items,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/stories/delete", status_code=status.HTTP_200_OK)
async def bulk_delete_stories(
    story_ids: List[int] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk delete name stories.
    
    - **story_ids**: List of story IDs to delete
    """
    try:
        result = await service.bulk_delete_stories(
            story_ids=story_ids,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Oral histories bulk operations
@router.post("/oral-histories/create", status_code=status.HTTP_201_CREATED)
async def bulk_create_oral_histories(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    skip_duplicates: bool = Query(True, description="Skip duplicate items"),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk create oral histories.
    
    - **items**: List of oral histories to create
    - **skip_duplicates**: Whether to skip duplicate items (based on title, interviewee, and creator)
    """
    try:
        result = await service.bulk_create_oral_histories(
            items=items,
            user_id=current_user.id,
            skip_duplicates=skip_duplicates
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/oral-histories/update", status_code=status.HTTP_200_OK)
async def bulk_update_oral_histories(
    items: List[Dict[str, Any]] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk update oral histories.
    
    - **items**: List of oral histories to update (must include 'id' field)
    """
    try:
        result = await service.bulk_update_oral_histories(
            items=items,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/oral-histories/delete", status_code=status.HTTP_200_OK)
async def bulk_delete_oral_histories(
    oral_history_ids: List[int] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk delete oral histories.
    
    - **oral_history_ids**: List of oral history IDs to delete
    """
    try:
        result = await service.bulk_delete_oral_histories(
            oral_history_ids=oral_history_ids,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Workspace bulk operations
@router.post("/workspaces/{workspace_id}/resources/add", status_code=status.HTTP_200_OK)
async def bulk_add_to_workspace(
    workspace_id: int,
    resources: List[Dict[str, Any]] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk add resources to a workspace.
    
    - **resources**: List of resources to add, each with 'resource_type' and 'resource_id'
    """
    try:
        result = await service.bulk_add_to_workspace(
            workspace_id=workspace_id,
            resources=resources,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/workspaces/{workspace_id}/resources/remove", status_code=status.HTTP_200_OK)
async def bulk_remove_from_workspace(
    workspace_id: int,
    resource_ids: List[Dict[str, Any]] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    service: BulkOperationsService = Depends(get_bulk_operations_service)
) -> Dict[str, Any]:
    """
    Bulk remove resources from a workspace.
    
    - **resource_ids**: List of resource identifiers, each with 'resource_type' and 'resource_id'
    """
    try:
        result = await service.bulk_remove_from_workspace(
            workspace_id=workspace_id,
            resource_ids=resource_ids,
            user_id=current_user.id
        )
        return result
    except BulkOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
