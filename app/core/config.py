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
    ARTIFACTS_DIR: str = "data/artifacts"
    MEDIA_DIR: str = "data/media"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
settings = Settings()
