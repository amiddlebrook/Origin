"""
Direct tests for the search service functionality.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

from app.models_user import User
from app.models_story import NameStory, OralHistory
from app.services.search_service import SearchService

# Test data
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

@pytest_asyncio.fixture
async def setup_search_service_test_data(db_session: AsyncSession, test_user_session: User):
    """Set up test data for search service tests."""
    story = NameStory(
        title=TEST_STORY["title"],
        narrative=TEST_STORY["narrative"],
        status=TEST_STORY["status"],
        user_id=test_user_session.id
    )
    db_session.add(story)
    await db_session.commit()
    await db_session.refresh(story)

    oral_history = OralHistory(
        title=TEST_ORAL_HISTORY["title"],
        summary=TEST_ORAL_HISTORY["summary"],
        transcript=TEST_ORAL_HISTORY["transcript"],
        status=TEST_ORAL_HISTORY["status"],
        user_id=test_user_session.id,
        story_id=story.id
    )
    db_session.add(oral_history)
    await db_session.commit()

@pytest.mark.asyncio
async def test_search_stories(db_session: AsyncSession, test_user_session: User, setup_search_service_test_data):
    """Test searching stories directly through the search service."""
    search_service = SearchService(db_session, test_user_session)
    
    results = await search_service.search_stories(
        query="family history",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert len(results.items) > 0
    assert any(story.title == TEST_STORY["title"] for story in results.items)

@pytest.mark.asyncio
async def test_search_oral_histories(db_session: AsyncSession, test_user_session: User, setup_search_service_test_data):
    """Test searching oral histories directly through the search service."""
    search_service = SearchService(db_session, test_user_session)
    
    results = await search_service.search_oral_histories(
        query="family journey",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert len(results.items) > 0
    assert any(oh.title == TEST_ORAL_HISTORY["title"] for oh in results.items)

@pytest.mark.asyncio
async def test_search_all(db_session: AsyncSession, test_user_session: User, setup_search_service_test_data):
    """Test searching across all content types."""
    search_service = SearchService(db_session, test_user_session)
    
    results = await search_service.search_all(
        query="family",
        page=1,
        page_size=10
    )
    
    assert results is not None
    assert "stories" in results
    assert "oral_histories" in results
    
    assert len(results["stories"].items) > 0
    assert len(results["oral_histories"].items) > 0
