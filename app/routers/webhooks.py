"""
API endpoints for managing webhooks.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.router import get_current_user
from app.models_user import User
from app.models_webhooks import WebhookEventType
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Dependency to get webhook service
def get_webhook_service_dep(db: AsyncSession = Depends(get_db)) -> WebhookService:
    return WebhookService(db)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    url: str = Body(..., embed=True),
    events: List[str] = Body(..., embed=True),
    secret: Optional[str] = Body(None, embed=True),
    is_active: bool = Body(True, embed=True),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    Create a new webhook.
    
    - **url**: The URL to send webhook events to
    - **events**: List of events to subscribe to (e.g., ["research.created", "story.updated"])
    - **secret**: Optional secret for signing webhook payloads
    - **is_active**: Whether the webhook is active
    """
    # Validate events
    valid_events = [e.value for e in WebhookEventType]
    for event in events:
        if event != "*" and event not in valid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {event}"
            )
    
    webhook = await service.create_webhook(
        url=url,
        events=events,
        user_id=current_user.id,
        secret=secret,
        is_active=is_active
    )
    
    return webhook

@router.get("/", response_model=List[dict])
async def list_webhooks(
    is_active: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    List webhooks for the current user.
    
    - **is_active**: Filter by active status
    - **limit**: Maximum number of results to return (1-1000)
    - **offset**: Number of results to skip for pagination
    """
    webhooks = await service.list_webhooks(
        user_id=current_user.id,
        is_active=is_active,
        limit=limit,
        offset=offset
    )
    
    return webhooks

@router.get("/{webhook_id}", response_model=dict)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    Get a webhook by ID.
    
    - **webhook_id**: ID of the webhook to retrieve
    """
    webhook = await service.get_webhook(webhook_id, current_user.id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or access denied"
        )
    
    return webhook

@router.patch("/{webhook_id}", response_model=dict)
async def update_webhook(
    webhook_id: int,
    url: Optional[str] = Body(None, embed=True),
    events: Optional[List[str]] = Body(None, embed=True),
    secret: Optional[str] = Body(None, embed=True),
    is_active: Optional[bool] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    Update a webhook.
    
    - **webhook_id**: ID of the webhook to update
    - **url**: New URL for the webhook
    - **events**: New list of events to subscribe to
    - **secret**: New secret for signing webhook payloads
    - **is_active**: Whether the webhook is active
    """
    updates = {}
    
    if url is not None:
        updates["url"] = url
    
    if events is not None:
        # Validate events
        valid_events = [e.value for e in WebhookEventType]
        for event in events:
            if event != "*" and event not in valid_events:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event}"
                )
        updates["events"] = events
    
    if secret is not None:
        updates["secret"] = secret
    
    if is_active is not None:
        updates["is_active"] = is_active
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    webhook = await service.update_webhook(
        webhook_id=webhook_id,
        user_id=current_user.id,
        **updates
    )
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or access denied"
        )
    
    return webhook

@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    Delete a webhook.
    
    - **webhook_id**: ID of the webhook to delete
    """
    success = await service.delete_webhook(webhook_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or access denied"
        )
    
    return None

@router.get("/events/", response_model=List[str])
async def list_webhook_events():
    """
    List all available webhook event types.
    """
    return [e.value for e in WebhookEventType]

@router.post("/test/{webhook_id}", status_code=status.HTTP_200_OK)
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service_dep)
):
    """
    Test a webhook by sending a test event.
    
    - **webhook_id**: ID of the webhook to test
    """
    # Get the webhook to verify it exists and the user has access
    webhook = await service.get_webhook(webhook_id, current_user.id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found or access denied"
        )
    
    # Trigger a test event
    test_data = {
        "message": "This is a test webhook event",
        "webhook_id": webhook_id,
        "user_id": current_user.id,
        "timestamp": "2023-01-01T00:00:00Z"
    }
    
    deliveries = await service.trigger_webhook_event(
        event="test",
        data=test_data,
        user_id=current_user.id
    )
    
    return {"status": "test_event_triggered", "delivery_ids": [d["id"] for d in deliveries]}
