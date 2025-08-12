"""
Tests for the analytics API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.main import app
from app.database import get_db
from app.models_user import User
from app.models_analytics import UserActivity, SearchQuery, ContentInteraction
from app.auth.router import get_current_user

# Test client
client = TestClient(app)

# Test data
TEST_USER = {
    "email": "test_analytics@example.com",
    "password": "testpassword123"
}

# Fixture to override the get_db dependency
@pytest.fixture(scope="module")
async def db():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session

# Fixture to override the get_current_user dependency
def override_get_current_user():
    return User(
        id=1,
        email=TEST_USER["email"],
        hashed_password="",
        is_active=True
    )

# Apply the overrides
app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(autouse=True)
async def setup_test_data(db: AsyncSession):
    """Set up test data for analytics tests."""
    # Create a test user
    user = User(
        email=TEST_USER["email"],
        hashed_password="hashed_password",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test activities
    activities = [
        UserActivity(
            user_id=user.id,
            activity_type="login",
            activity_data={"ip": "127.0.0.1"},
            created_at=datetime.utcnow() - timedelta(days=i)
        ) for i in range(5)
    ]
    db.add_all(activities)
    
    # Create test search queries
    searches = [
        SearchQuery(
            user_id=user.id,
            query=f"test query {i}",
            result_count=i * 2,
            search_type="stories" if i % 2 == 0 else "all",
            is_advanced=i % 2 == 0,
            created_at=datetime.utcnow() - timedelta(days=i)
        ) for i in range(5)
    ]
    db.add_all(searches)
    
    # Create test content interactions
    interactions = [
        ContentInteraction(
            user_id=user.id,
            content_type="story",
            content_id=i,
            interaction_type="view",
            interaction_data={"duration": i * 10},
            created_at=datetime.utcnow() - timedelta(days=i)
        ) for i in range(1, 6)
    ]
    db.add_all(interactions)
    
    db.commit()
    
    yield
    
    # Clean up test data
    db.query(ContentInteraction).delete()
    db.query(SearchQuery).delete()
    db.query(UserActivity).delete()
    db.query(User).filter(User.email == TEST_USER["email"]).delete()
    db.commit()

def test_track_activity():
    """Test tracking a user activity."""
    response = client.post(
        "/analytics/track/activity",
        params={
            "activity_type": "test_activity",
            "ip_address": "192.168.1.1",
            "user_agent": "test_agent"
        },
        json={"key": "value"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_track_search():
    """Test tracking a search query."""
    response = client.post(
        "/analytics/track/search",
        params={
            "query": "test search",
            "result_count": 5,
            "search_type": "stories",
            "is_advanced": True
        },
        json={"filters": {"category": "history"}}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_track_interaction():
    """Test tracking a content interaction."""
    response = client.post(
        "/analytics/track/interaction",
        params={
            "content_type": "story",
            "content_id": 1,
            "interaction_type": "view"
        },
        json={"duration": 30}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_activity_analytics():
    """Test getting activity analytics."""
    response = client.get("/analytics/activity", params={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert "total_activities" in data
    assert "activity_types" in data
    assert "daily_activity" in data
    assert len(data["activity_types"]) > 0

def test_get_search_analytics():
    """Test getting search analytics."""
    response = client.get("/analytics/searches", params={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert "total_searches" in data
    assert "popular_searches" in data
    assert "search_types" in data
    assert "advanced_ratio" in data

def test_get_content_analytics():
    """Test getting content interaction analytics."""
    response = client.get("/analytics/content", params={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert "total_interactions" in data
    assert "interaction_types" in data
    assert "popular_content" in data
    assert len(data["interaction_types"]) > 0
