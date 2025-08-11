"""
Tests for the search functionality with both PostgreSQL and SQLite backends.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from datetime import datetime, timezone

from app.main import app
from app.database import Base, get_db, engine, SQLALCHEMY_DATABASE_URL
from app.models_user import User
from app.models_story import NameStory, OralHistory
# Import search schemas from the correct module path
from app.schemas.search import (
    SearchResultType, 
    SearchRequest, 
    SearchResponse,
    SearchSuggestionItem,
    SearchSuggestionsResponse
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
def test_app():
    """Create a test client with overridden dependencies."""
    # Setup test database
    Base.metadata.create_all(bind=engine)
    
    # Create test data
    with Session(engine) as session:
        # Create test user
        user = User(email=TEST_USER["email"])
        user.set_password(TEST_USER["password"])
        session.add(user)
        session.commit()
        
        # Create test story
        story = NameStory(
            title=TEST_STORY["title"],
            narrative=TEST_STORY["narrative"],
            status=TEST_STORY["status"],
            user_id=user.id
        )
        session.add(story)
        
        # Create test oral history
        oral_history = OralHistory(
            title=TEST_ORAL_HISTORY["title"],
            summary=TEST_ORAL_HISTORY["summary"],
            transcript=TEST_ORAL_HISTORY["transcript"],
            status=TEST_ORAL_HISTORY["status"],
            user_id=user.id
        )
        session.add(oral_history)
        session.commit()
    
    # Create test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def auth_headers(test_app):
    """Get authentication headers."""
    # Login to get access token
    response = test_app.post(
        "/auth/token",
        data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_search_stories(test_app, auth_headers):
    """Test searching stories."""
    search_request = {
        "query": "family history",
        "include": [SearchResultType.STORY],
        "page": 1,
        "page_size": 10
    }
    
    response = test_app.post(
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

def test_search_oral_histories(test_app, auth_headers):
    """Test searching oral histories."""
    search_request = {
        "query": "family journey",
        "include": [SearchResultType.ORAL_HISTORY],
        "page": 1,
        "page_size": 10
    }
    
    response = test_app.post(
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

def test_search_suggestions(test_app, auth_headers):
    """Test search suggestions."""
    response = test_app.get(
        "/search/suggestions",
        params={"q": "family"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "family"
    assert "stories" in data or "oral_histories" in data

def test_search_with_filters(test_app, auth_headers):
    """Test search with filters."""
    search_request = {
        "query": "test",
        "filters": {
            "status": "published"
        },
        "page": 1,
        "page_size": 10
    }
    
    response = test_app.post(
        "/search",
        json=search_request,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["page"] == 1
    assert data["page_size"] == 10

def test_search_model_endpoint(test_app, auth_headers):
    """Test the model-specific search endpoint."""
    response = test_app.get(
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
