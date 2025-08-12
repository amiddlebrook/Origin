import os
import sys
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator, Generator

# Ensure project root is on sys.path so `import app` works in tests
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

# Import database models first to avoid circular imports
from app.database import Base, get_db

# Use in-memory SQLite for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine and session
engine = create_async_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,  # Enable SQL query logging for tests
)

TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Override the get_db dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Fixture to create test database tables
@pytest.fixture(scope="function")
def test_app() -> Generator[FastAPI, None, None]:
    # Import here to avoid circular imports
    from app.main import create_app
    
    # Create a new FastAPI app for testing
    app = create_app()
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Clear overrides after test
    app.dependency_overrides.clear()

# Fixture to get a test database session
@pytest.fixture(scope="function")
async def db_session(test_app: FastAPI) -> AsyncGenerator[AsyncSession, None]:
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Dispose the engine
    await engine.dispose()

# Fixture to get a test client with overridden database
@pytest.fixture(scope="function")
def test_client(test_app: FastAPI) -> TestClient:
    with TestClient(test_app) as client:
        # Set default headers
        client.headers.update({"Content-Type": "application/json"})
        yield client

# Fixture for authenticated client
@pytest.fixture(scope="function")
def auth_client(test_client: TestClient) -> TestClient:
    import uuid
    
    # Register a test user
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    
    # Register
    response = test_client.post(
        "/auth/register",
        json={"email": email, "password": password}
    )
    assert response.status_code in (200, 201), f"Failed to register test user: {response.text}"
    
    # Login to get token
    form_data = {
        "username": email,
        "password": password,
    }
    
    response = test_client.post(
        "/auth/token",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Failed to login test user: {response.text}"
    
    # Extract token
    token_data = response.json()
    token = token_data.get("access_token")
    assert token is not None, "No access token in response"
    
    # Update client headers with auth token
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    
    return test_client
