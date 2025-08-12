"""
Tests for the search functionality.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

from app.models_user import User
from app.models_story import NameStory, OralHistory
from app.schemas.search import SearchResultType

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

@pytest_asyncio.fixture(scope="function")
async def setup_search_test_data(db_session: AsyncSession, test_user_session: User):
    """Set up test data for search tests."""
    # test_user_session is the user from conftest.
    # Create test story
    story = NameStory(
        title=TEST_STORY["title"],
        narrative=TEST_STORY["narrative"],
        status=TEST_STORY["status"],
        user_id=test_user_session.id
    )
    db_session.add(story)

    # Create test oral history
    oral_history = OralHistory(
        title=TEST_ORAL_HISTORY["title"],
        summary=TEST_ORAL_HISTORY["summary"],
        transcript=TEST_ORAL_HISTORY["transcript"],
        status=TEST_ORAL_HISTORY["status"],
        user_id=test_user_session.id
    )
    db_session.add(oral_history)
    await db_session.commit()


def test_search_stories(client: TestClient, auth_headers: dict, setup_search_test_data):
    """Test searching stories."""
    search_request = {
        "query": "family history",
        "include": [SearchResultType.STORY.value],
        "page": 1,
        "page_size": 10
    }
    
    response = client.post(
        "/search",
        json=search_request,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["query"] == "family history"
    assert len(data["results"]) > 0
    assert any(s["title"] == TEST_STORY["title"] for s in data["results"])

def test_search_oral_histories(client: TestClient, auth_headers: dict, setup_search_test_data):
    """Test searching oral histories."""
    search_request = {
        "query": "family journey",
        "include": [SearchResultType.ORAL_HISTORY.value],
        "page": 1,
        "page_size": 10
    }
    
    response = client.post(
        "/search",
        json=search_request,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["query"] == "family journey"
    assert len(data["results"]) > 0
    assert any(oh["title"] == TEST_ORAL_HISTORY["title"] for oh in data["results"])

def test_search_suggestions(client: TestClient, auth_headers: dict, setup_search_test_data):
    """Test search suggestions."""
    response = client.get(
        "/search/suggestions",
        params={"q": "family"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "family"
    assert "stories" in data or "oral_histories" in data

def test_search_with_filters(client: TestClient, auth_headers: dict, setup_search_test_data):
    """Test search with filters."""
    search_request = {
        "query": "test",
        "filters": {
            "status": "published"
        },
        "page": 1,
        "page_size": 10
    }
    
    response = client.post(
        "/search",
        json=search_request,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["page"] == 1
    assert data["page_size"] == 10

def test_search_model_endpoint(client: TestClient, auth_headers: dict, setup_search_test_data):
    """Test the model-specific search endpoint."""
    response = client.get(
        "/search/models/stories",
        params={"q": "family"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
