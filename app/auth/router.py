from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models_user import User
from app.auth import utils
from app.auth import schemas as s
from app.core.config import settings
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
router = APIRouter()

@router.post("/register", response_model=dict)
async def register(payload: s.UserCreate, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == payload.email))
    existing = q.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = utils.get_password_hash(payload.password)
    user = User(email=payload.email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email}

@router.post("/token", response_model=s.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == form_data.username))
    user = q.scalar_one_or_none()
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = utils.create_access_token({"sub": user.email, "user_id": user.id}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = utils.decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    q = await db.execute(select(User).where(User.id == payload["user_id"]))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
