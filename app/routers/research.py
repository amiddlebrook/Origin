from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app import models, schemas
from sqlalchemy import select
from tasks.research_tasks import run_name_research
from app.auth.router import get_current_user
import asyncio

router = APIRouter()

@router.post("/", response_model=schemas.ResearchOut, status_code=status.HTTP_201_CREATED)
async def create_research(payload: schemas.ResearchCreate, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    new = models.Research(name=payload.name, status="pending", user_id=user.id)
    db.add(new)
    await db.commit()
    await db.refresh(new)
    try:
        run_name_research.delay(new.id, payload.name)
    except Exception:
        asyncio.create_task(__fallback_background(new.id, payload.name))
    return new

async def __fallback_background(research_id: int, name: str):
    from app.tasks.research_worker import run_process_in_background
    await run_process_in_background(research_id, name)

@router.get("/{research_id}", response_model=schemas.ResearchOut)
async def get_research(research_id: int, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    q = await db.execute(select(models.Research).where(models.Research.id == research_id).where(models.Research.user_id == user.id))
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res
