"""
Tests for the stories API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

def test_stories_requires_auth(client: TestClient):
    """Test that listing stories requires authentication."""
    resp = client.get("/stories")
    assert resp.status_code in (401, 403)


def test_create_story_with_seed_name(client: TestClient, auth_headers: dict):
    """Test creating a new story with a seed name."""
    payload = {"title": "Test Story", "seed_name": "Avery"}
    resp = client.post("/stories", json=payload, headers=auth_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("id") is not None
    assert data.get("status") in ("pending", "done")
