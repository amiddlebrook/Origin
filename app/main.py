import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging
from app.routers import research
from app.auth import router as auth_router
from app.routers.health import router as health_router
import logging
from app.database import engine, Base
import os
# Ensure models are imported so metadata contains all tables
from app import models  # noqa: F401
from app import models_user  # noqa: F401
from app import models_story  # noqa: F401
configure_logging(settings.DEBUG)
logger = logging.getLogger(__name__)
def create_app():
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
    app.include_router(auth_router, prefix='/auth', tags=['auth'])
    app.include_router(research.router, prefix='/research', tags=['research'])
    app.include_router(health_router, tags=['health'])
    # Lazy import to avoid circulars
    from app.routers.stories import router as stories_router
    app.include_router(stories_router, prefix='/stories', tags=['stories'])
    @app.on_event('startup')
    async def startup():
        logger.info('Ensuring DB tables exist')
        # Ensure data dirs exist
        os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)
        os.makedirs(settings.MEDIA_DIR, exist_ok=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    return app
app = create_app()
if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=settings.DEBUG)
