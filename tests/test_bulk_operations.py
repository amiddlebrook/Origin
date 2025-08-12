"""
Tests for bulk operations endpoints and services.
"""
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models_user import User
from app.models import Research
from app.models_story import NameStory, OralHistory

# Test data for creation
TEST_RESEARCH_CREATE = [{"name": f"New Research {i}", "content": f"Content {i}"} for i in range(5)]
TEST_STORIES_CREATE = [{"name": f"New Story {i}", "narrative": f"Narrative {i}"} for i in range(5)]
TEST_ORAL_HISTORIES_CREATE = [{"name": f"New Oral History {i}", "summary": f"Summary {i}"} for i in range(5)]

import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def initial_data(db_session: AsyncSession, test_user: User):
    """Helper to create initial data for update/delete tests."""
    research_items = [Research(name=f"Initial Research {i}", created_by_id=test_user.id) for i in range(2)]
    db_session.add_all(research_items)

    story_items = [NameStory(name=f"Initial Story {i}", created_by_id=test_user.id) for i in range(2)]
    db_session.add_all(story_items)

    oral_history_items = [OralHistory(name=f"Initial Oral History {i}", created_by_id=test_user.id) for i in range(2)]
    db_session.add_all(oral_history_items)

    await db_session.commit()

    # Refresh items to get IDs
    for item in research_items:
        await db_session.refresh(item)
    for item in story_items:
        await db_session.refresh(item)
    for item in oral_history_items:
        await db_session.refresh(item)

    return {
        "research": research_items,
        "stories": story_items,
        "oral_histories": oral_history_items,
        "research_ids": [item.id for item in research_items],
        "story_ids": [item.id for item in story_items],
        "oral_history_ids": [item.id for item in oral_history_items],
    }

@pytest.mark.asyncio
class TestBulkResearchOperations:
    async def test_bulk_create_research(self, client: TestClient, auth_headers: dict):
        response = client.post("/bulk/research/create", json={"items": TEST_RESEARCH_CREATE}, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["total"] == len(TEST_RESEARCH_CREATE)
        assert data["created"] == len(TEST_RESEARCH_CREATE)

    async def test_bulk_update_research(self, client: TestClient, auth_headers: dict, initial_data: dict):
        research_ids = initial_data["research_ids"]
        updates = [
            {"id": research_ids[0], "name": "Updated Research Title"},
            {"id": 99999, "name": "Non-existent Research"}
        ]
        response = client.put("/bulk/research/update", json={"items": updates}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated"] == 1
        assert data["not_found"] == 1

    async def test_bulk_delete_research(self, client: TestClient, auth_headers: dict, initial_data: dict):
        research_ids = initial_data["research_ids"]
        ids_to_delete = research_ids + [99999]
        response = client.post("/bulk/research/delete", json={"research_ids": ids_to_delete}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted"] == len(research_ids)
        assert data["not_found"] == 1

@pytest.mark.asyncio
class TestBulkStoryOperations:
    async def test_bulk_create_stories(self, client: TestClient, auth_headers: dict):
        response = client.post("/bulk/stories/create", json={"items": TEST_STORIES_CREATE}, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created"] == len(TEST_STORIES_CREATE)

    async def test_bulk_update_stories(self, client: TestClient, auth_headers: dict, initial_data: dict):
        story_ids = initial_data["story_ids"]
        updates = [{"id": story_ids[0], "name": "Updated Story Title"}]
        response = client.put("/bulk/stories/update", json={"items": updates}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["updated"] == 1

@pytest.mark.asyncio
class TestBulkOralHistoryOperations:
    async def test_bulk_create_oral_histories(self, client: TestClient, auth_headers: dict):
        response = client.post("/bulk/oral-histories/create", json={"items": TEST_ORAL_HISTORIES_CREATE}, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["created"] == len(TEST_ORAL_HISTORIES_CREATE)

    async def test_bulk_update_oral_histories(self, client: TestClient, auth_headers: dict, initial_data: dict):
        oral_history_ids = initial_data["oral_history_ids"]
        updates = [{"id": oral_history_ids[0], "name": "Updated Oral History Title"}]
        response = client.put("/bulk/oral-histories/update", json={"items": updates}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["updated"] == 1
