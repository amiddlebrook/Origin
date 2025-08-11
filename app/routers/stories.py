from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db
from app.auth.router import get_current_user
from app import models
from app.models_story import NameStory
from app.schemas_story import NameStoryCreate, NameStoryOut
from tasks.story_tasks import generate_name_story
import asyncio

router = APIRouter()

@router.post("/", response_model=NameStoryOut, status_code=status.HTTP_201_CREATED)
async def create_story(payload: NameStoryCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not payload.title:
        raise HTTPException(status_code=400, detail="Title is required")
    story = NameStory(user_id=user.id, title=payload.title, status="pending", research_id=payload.research_id)
    db.add(story)
    await db.commit()
    await db.refresh(story)

    # Dispatch celery task; fallback to background if celery unavailable
    try:
        generate_name_story.delay(story.id, payload.seed_name)
    except Exception:
        asyncio.create_task(_fallback_generate(story.id, payload.seed_name))

    return story

async def _fallback_generate(story_id: int, seed_name: str | None):
    from app.tasks.story_worker import run_process_in_background
    await run_process_in_background(story_id, seed_name)

@router.get("/{story_id}", response_model=NameStoryOut)
async def get_story(story_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(NameStory).where(NameStory.id == story_id).where(NameStory.user_id == user.id))
    story = q.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Not found")
    return story

@router.get("/", response_model=list[NameStoryOut])
async def list_stories(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = await db.execute(select(NameStory).where(NameStory.user_id == user.id).order_by(NameStory.created_at.desc()))
    return [row for row in q.scalars().all()]
