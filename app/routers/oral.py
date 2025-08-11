from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import os

from app.database import get_db
from app.auth.router import get_current_user
from app.models_story import OralHistory, NameStory
from app.schemas_story import OralHistoryOut, OralHistoryUpdate
from app.services.storage import save_upload
from app.tasks.oral_worker import run_oral_processing_in_background

router = APIRouter(prefix="/oral-histories", tags=["oral-histories"])

@router.post(
    "/upload", 
    response_model=OralHistoryOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Upload an oral history recording",
    description="Upload an audio file to be processed as an oral history. The file will be processed in the background."
)
async def upload_oral_history(
    background_tasks: BackgroundTasks,
    title: str = Form(..., description="Title for the oral history"),
    story_id: Optional[int] = Form(None, description="Optional ID of the story this oral history is associated with"),
    file: UploadFile = File(..., description="Audio file to upload"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Upload an oral history audio file. The file will be processed in the background.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only audio files are allowed"
        )

    # Check if story exists and belongs to user if provided
    if story_id is not None:
        q = await db.execute(
            select(NameStory)
            .where(NameStory.id == story_id)
            .where(NameStory.user_id == user.id)
        )
        story = q.scalar_one_or_none()
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied"
            )

    try:
        # Save the uploaded file
        _, rel_path = save_upload(file, subdir=f"users/{user.id}/oral-histories")
        
        # Create the oral history record
        item = OralHistory(
            user_id=user.id,
            story_id=story_id,
            title=title,
            file_path=rel_path,
            status="pending"
        )
        
    async with db.begin():
        db.add(item)
    await db.refresh(item)
    return item

@router.get("/", response_model=list[OralHistoryOut])
async def list_oral_histories(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(OralHistory).where(OralHistory.user_id == user.id).order_by(OralHistory.created_at.desc()))
    return [row for row in q.scalars().all()]

@router.get("/{oral_id}", response_model=OralHistoryOut)
async def get_oral_history(oral_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(OralHistory).where(OralHistory.id == oral_id).where(OralHistory.user_id == user.id))
    item = q.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item
