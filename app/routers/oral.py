from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.router import get_current_user
from app.models_story import OralHistory, NameStory
from app.schemas_story import OralHistoryCreate, OralHistoryOut
from app.services.storage import save_upload

router = APIRouter()

@router.post("/upload", response_model=OralHistoryOut, status_code=status.HTTP_201_CREATED)
async def upload_oral_history(
    title: str = Form(...),
    story_id: int | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    if story_id is not None:
        q = await db.execute(select(NameStory).where(NameStory.id == story_id).where(NameStory.user_id == user.id))
        story = q.scalar_one_or_none()
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
    # Save file
    _, rel_path = save_upload(file, subdir="audio")
    item = OralHistory(user_id=user.id, story_id=story_id, title=title, file_path=rel_path)
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
