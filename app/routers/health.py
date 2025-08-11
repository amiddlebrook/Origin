from fastapi import APIRouter
from app.database import AsyncSessionLocal
from sqlalchemy import text
import os

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    details = {"db": "unknown", "redis": "skipped"}
    # DB check
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        details["db"] = "ok"
    except Exception as e:
        details["db"] = f"error: {e}"

    # Optional Redis check if REDIS_URL provided
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            r = redis.Redis.from_url(redis_url)
            pong = r.ping()
            details["redis"] = "ok" if pong else "error: no PONG"
        except Exception as e:
            details["redis"] = f"error: {e}"
    return {"status": ("ok" if details.get("db") == "ok" else "error"), "details": details}
