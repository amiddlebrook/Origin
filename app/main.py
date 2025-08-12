import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.logging import configure_logging
from app.routers import research
from app.auth.router import router as auth_router
from app.routers.health import router as health_router
from app.services.rate_limiter import RateLimiter
import logging
from app.database import engine, Base
import os
# Ensure models are imported so metadata contains all tables
from app import models  # noqa: F401
from app import models_user  # noqa: F401
from app import models_story  # noqa: F401
configure_logging(settings.DEBUG)
logger = logging.getLogger(__name__)
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ensuring DB tables exist")
    # Ensure data dirs exist
    os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)
    # The media upload dir is created later, when the app is created.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app():
    app = FastAPI(
        title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Create media upload directory if it doesn't exist
    os.makedirs(settings.MEDIA_UPLOAD_DIR, exist_ok=True)
    # Mount static files for media uploads
    app.mount("/media", StaticFiles(directory=settings.MEDIA_UPLOAD_DIR), name="media")
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(research, prefix="/research", tags=["research"])
    app.include_router(health_router, tags=["health"])
    # Lazy import to avoid circulars
    from app.routers.stories import router as stories_router
    from app.routers.search import router as search_router
    from app.routers.analytics import router as analytics_router
    from app.routers.media import router as media_router
    from app.routers.export_import import router as export_import_router
    from app.routers.collaboration import router as collaboration_router

    app.include_router(stories_router, prefix="/stories", tags=["stories"])
    app.include_router(search_router, tags=["search"])
    app.include_router(analytics_router, tags=["analytics"])
    app.include_router(media_router, tags=["media"])
    app.include_router(export_import_router, tags=["export-import"])
    app.include_router(collaboration_router, tags=["collaboration"])
    
    # Import and include bulk operations router
    from app.routers.bulk_operations import router as bulk_operations_router
    app.include_router(bulk_operations_router, tags=["bulk"])
    
    # Add rate limiting middleware
    app.state.rate_limiter = RateLimiter(app)
    return app
app = create_app()
if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=settings.DEBUG)
