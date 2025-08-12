"""
Tests for bulk operations endpoints and services.
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict

from app.main import app
from app.database import get_db, Base, async_session_maker
from app.models_user import User, UserCreate
from app.models_research import Research
from app.models_stories import NameStory
from app.models_oral_history import OralHistory
from app.services.auth import get_password_hash

# Test client
client = TestClient(app)

# Test data
TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
}

TEST_RESEARCH = [
    {"title": f"Research {i}", "content": f"Content {i}", "is_public": True}
    for i in range(1, 6)
]

TEST_STORIES = [
    {"title": f"Story {i}", "name": f"Name {i}", "content": f"Content {i}", "is_public": True}
    for i in range(1, 6)
]

TEST_ORAL_HISTORIES = [
    {"title": f"Oral History {i}", "interviewee_name": f"Interviewee {i}", "content": f"Content {i}"}
    for i in range(1, 6)
]

# Fixtures
@pytest.fixture(scope="module")
async def db():
    # Create all tables
    async with async_session_maker() as session:
        async with session.begin():
            await session.run_sync(Base.metadata.create_all)
        yield session
        # Clean up
        async with session.begin():
            await session.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="module")
async def test_user(db: AsyncSession):
    user_data = UserCreate(**TEST_USER)
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.fixture(scope="module")
def auth_headers(test_user: User):
    # Get auth token
    response = client.post(
        "/auth/token",
        data={"username": TEST_USER["email"], "password": TEST_USER["password"]}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Helper functions
async def create_test_data(db: AsyncSession, user_id: int):
    """Create test research, stories, and oral histories."""
    # Create test research
    research_items = [
        Research(**{**item, "created_by_id": user_id, "updated_at": None})
        for item in TEST_RESEARCH
    ]
    db.add_all(research_items)
    
    # Create test stories
    stories = [
        NameStory(**{**item, "created_by_id": user_id, "updated_at": None})
        for item in TEST_STORIES
    ]
    db.add_all(stories)
    
    # Create test oral histories
    oral_histories = [
        OralHistory(**{**item, "created_by_id": user_id, "updated_at": None})
        for item in TEST_ORAL_HISTORIES
    ]
    db.add_all(oral_histories)
    
    await db.commit()
    
    # Get IDs
    research_ids = [item.id for item in research_items]
    story_ids = [item.id for item in stories]
    oral_history_ids = [item.id for item in oral_histories]
    
    return {
        "research_ids": research_ids,
        "story_ids": story_ids,
        "oral_history_ids": oral_history_ids
    }

# Tests
class TestBulkResearchOperations:
    async def test_bulk_create_research(self, auth_headers: Dict[str, str]):
        """Test bulk creating research items."""
        response = client.post(
            "/bulk/research/create",
            headers=auth_headers,
            json=TEST_RESEARCH
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total"] == len(TEST_RESEARCH)
        assert data["created"] == len(TEST_RESEARCH)
        assert data["skipped"] == 0
        assert len(data["errors"]) == 0
        
        # Verify items were created
        response = client.get("/research/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        items = response.json()
        assert len(items) >= len(TEST_RESEARCH)
    
    async def test_bulk_update_research(self, auth_headers: Dict[str, str], test_user: User):
        """Test bulk updating research items."""
        # First create test data
        test_data = await create_test_data(get_db(), test_user.id)
        research_ids = test_data["research_ids"]
        
        # Prepare updates
        updates = [
            {"id": research_ids[0], "title": "Updated Title 1"},
            {"id": research_ids[1], "is_public": False},
            {"id": 999999, "title": "Non-existent"}  # Should be not found
        ]
        
        response = client.put(
            "/bulk/research/update",
            headers=auth_headers,
            json=updates
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["updated"] == 2
        assert data["not_found"] == 1
        assert len(data["errors"]) == 0
        
        # Verify updates
        response = client.get(f"/research/{research_ids[0]}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Title 1"
    
    async def test_bulk_delete_research(self, auth_headers: Dict[str, str], test_user: User):
        """Test bulk deleting research items."""
        # First create test data
        test_data = await create_test_data(get_db(), test_user.id)
        research_ids = test_data["research_ids"]
        
        # Try to delete some items (including one non-existent ID)
        ids_to_delete = research_ids[:2] + [999999]  # First 2 items + non-existent
        
        response = client.post(
            "/bulk/research/delete",
            headers=auth_headers,
            json=ids_to_delete
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["deleted"] == 2
        assert data["not_found"] == 1
        assert len(data["errors"]) == 0
        
        # Verify items were deleted
        for item_id in research_ids[:2]:
            response = client.get(f"/research/{item_id}", headers=auth_headers)
            assert response.status_code == status.HTTP_404_NOT_FOUND

class TestBulkStoryOperations:
    async def test_bulk_create_stories(self, auth_headers: Dict[str, str]):
        """Test bulk creating name stories."""
        response = client.post(
            "/bulk/stories/create",
            headers=auth_headers,
            json=TEST_STORIES
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total"] == len(TEST_STORIES)
        assert data["created"] == len(TEST_STORIES)
        assert data["skipped"] == 0
        assert len(data["errors"]) == 0
    
    async def test_bulk_update_stories(self, auth_headers: Dict[str, str], test_user: User):
        """Test bulk updating name stories."""
        # First create test data
        test_data = await create_test_data(get_db(), test_user.id)
        story_ids = test_data["story_ids"]
        
        # Prepare updates
        updates = [
            {"id": story_ids[0], "title": "Updated Story 1"},
            {"id": story_ids[1], "is_public": False}
        ]
        
        response = client.put(
            "/bulk/stories/update",
            headers=auth_headers,
            json=updates
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["updated"] == 2
        
        # Verify updates
        response = client.get(f"/stories/{story_ids[0]}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Story 1"

class TestBulkOralHistoryOperations:
    async def test_bulk_create_oral_histories(self, auth_headers: Dict[str, str]):
        """Test bulk creating oral histories."""
        response = client.post(
            "/bulk/oral-histories/create",
            headers=auth_headers,
            json=TEST_ORAL_HISTORIES
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total"] == len(TEST_ORAL_HISTORIES)
        assert data["created"] == len(TEST_ORAL_HISTORIES)
        assert data["skipped"] == 0
        assert len(data["errors"]) == 0
    
    async def test_bulk_update_oral_histories(self, auth_headers: Dict[str, str], test_user: User):
        """Test bulk updating oral histories."""
        # First create test data
        test_data = await create_test_data(get_db(), test_user.id)
        oral_history_ids = test_data["oral_history_ids"]
        
        # Prepare updates
        updates = [
            {"id": oral_history_ids[0], "title": "Updated Oral History 1"},
            {"id": oral_history_ids[1], "interviewee_name": "Updated Interviewee"}
        ]
        
        response = client.put(
            "/bulk/oral-histories/update",
            headers=auth_headers,
            json=updates
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2
        assert data["updated"] == 2
        
        # Verify updates
        response = client.get(f"/oral-histories/{oral_history_ids[0]}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "Updated Oral History 1"

class TestRateLimiting:
    async def test_rate_limiting(self, auth_headers: Dict[str, str]):
        """Test that rate limiting is working."""
        # Make requests until rate limited
        endpoint = "/research/"
        responses = []
        
        # Make enough requests to hit the rate limit (default is 60/min)
        for _ in range(65):
            response = client.get(endpoint, headers=auth_headers)
            responses.append(response.status_code)
        
        # Should have some 429 responses
        assert status.HTTP_429_TOO_MANY_REQUESTS in responses
        
        # Check rate limit headers
        response = client.get(endpoint, headers=auth_headers)
        if response.status_code == status.HTTP_200_OK:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
        else:
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Retry-After" in response.headers
