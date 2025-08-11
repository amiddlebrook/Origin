"""
Direct tests for the search service functionality.
These tests focus on the search service layer without going through the FastAPI app.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.database import Base
from app.core.config import settings
from app.models_user import User
from app.models_story import NameStory, OralHistory
from app.services.search_service import SearchService

# Use the test database URL from settings
TEST_DATABASE_URL = settings.ASYNC_DATABASE_URL

# Create async engine and session factory
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession
)

# Test data
TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword"
}

TEST_STORY = {
    "title": "Test Story",
    "narrative": "This is a test story about family history and genealogy.",
    "status": "published"
}

TEST_ORAL_HISTORY = {
    "title": "Test Oral History",
    "summary": "An interview about family history",
    "transcript": "This is a transcript about our family's journey and traditions.",
    "status": "published"
}

@pytest.fixture(scope="module")
async def db():
    """Create a test database and yield a session."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a new session for testing
    async with TestingSessionLocal() as session:
        # Create test user
        user = User(email=TEST_USER["email"])
        user.set_password(TEST_USER["password"])
        session.add(user)
        
        # Create test story
        story = NameStory(
            title=TEST_STORY["title"],
            narrative=TEST_STORY["narrative"],
            status=TEST_STORY["status"],
            user=user
        )
        session.add(story)
        
        # Create test oral history
        oral_history = OralHistory(
            title=TEST_ORAL_HISTORY["title"],
            summary=TEST_ORAL_HISTORY["summary"],
            transcript=TEST_ORAL_HISTORY["transcript"],
            status=TEST_ORAL_HISTORY["status"],
            user=user,
            story=story
        )
        session.add(oral_history)
        
        await session.commit()
        
        # Refresh objects to ensure we have the latest data
        await session.refresh(user)
        await session.refresh(story)
        await session.refresh(oral_history)
        
        yield session
        
        # Cleanup
        await session.rollback()
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def current_user(db):
    """Get the current test user."""
    result = await db.execute("SELECT * FROM users WHERE email = :email", {"email": TEST_USER["email"]})
    return result.scalar_one()

@pytest.mark.asyncio
async def test_search_stories(db, current_user):
    """Test searching stories directly through the search service."""
    search_service = SearchService(db, current_user)
    
    # Search for stories
    results = await search_service.search_stories(
        query="family history",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert len(results.items) > 0
    assert any(story.title == TEST_STORY["title"] for story in results.items)

@pytest.mark.asyncio
async def test_search_oral_histories(db, current_user):
    """Test searching oral histories directly through the search service."""
    search_service = SearchService(db, current_user)
    
    # Search for oral histories
    results = await search_service.search_oral_histories(
        query="family journey",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert len(results.items) > 0
    assert any(oh.title == TEST_ORAL_HISTORY["title"] for oh in results.items)

@pytest.mark.asyncio
async def test_search_all(db, current_user):
    """Test searching across all content types."""
    search_service = SearchService(db, current_user)
    
    # Search across all content types
    results = await search_service.search_all(
        query="family",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert "stories" in results
    assert "oral_histories" in results
    
    # Verify we got results for both types
    assert len(results["stories"].items) > 0
    assert len(results["oral_histories"].items) > 0
