from typing import List, Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NameStory Explorer"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/dev.db"
    USER_AGENT: Optional[str] = None
    MAX_CONCURRENT_REQUESTS: int = 4
    REQUEST_DELAY: float = 0.5
    ENABLE_PLAYWRIGHT: bool = False
    # Auth
    SECRET_KEY: str = "change-me-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60*24*7
    CORS_ORIGINS: List[str] = ["*"]
    # File storage
    ARTIFACTS_DIR: str = "data/artifacts"
    MEDIA_UPLOAD_DIR: str = "data/media"
    
    # Media processing
    MAX_IMAGE_SIZE_MB: int = 10  # 10MB max image size
    MAX_VIDEO_SIZE_MB: int = 100  # 100MB max video size
    THUMBNAIL_SIZE: tuple[int, int] = (300, 300)  # Width, Height in pixels
    
    # Allowed file types
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp"
    ]
    
    ALLOWED_VIDEO_TYPES: list[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-ms-wmv"
    ]

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
settings = Settings()
