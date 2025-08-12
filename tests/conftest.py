import os
import sys
import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, Dict
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import JSON, TEXT

# --- Custom Compilers for SQLite ---

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    """Compile JSONB as JSON for sqlite."""
    return compiler.visit_JSON(type_, **kw)

@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    """Compile TSVECTOR as TEXT for sqlite."""
    return compiler.visit_TEXT(type_, **kw)

# --- Path Setup ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from app.main import create_app
from app.database import Base, get_db
from app.core.config import settings
from app.models_user import User
from app.auth.utils import get_password_hash

# --- Test Database Setup ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override for getting a DB session."""
    async with TestingSessionLocal() as session:
        yield session

# --- Pytest Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the whole session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Create database tables for each test function, and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a new DB session for each test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> TestClient:
    """Provides a TestClient with the database dependency overridden for each test."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def test_user_session(db_session: AsyncSession) -> User:
    """Creates a test user for a test function."""
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user_session: User) -> Dict[str, str]:
    """Provides auth headers for a test function."""
    response = client.post(
        "/auth/token",
        data={"username": test_user_session.email, "password": "testpassword"},
    )
    if response.status_code != 200:
        # This will help debug if token generation fails
        print("Failed to get auth token:", response.text)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Creates a fresh test user for each test function."""
    user = User(
        email="testfuncuser@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
