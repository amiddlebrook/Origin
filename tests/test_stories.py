import uuid
from fastapi.testclient import TestClient
from app.main import app


def _unique_email():
    return f"stories+{uuid.uuid4().hex[:8]}@example.com"


def _auth_headers(client: TestClient):
    email = _unique_email()
    password = "Passw0rd!"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201)
    t = client.post("/auth/token", data={"username": email, "password": password})
    assert t.status_code == 200
    token = t.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_stories_requires_auth():
    client = TestClient(app)
    resp = client.get("/stories")
    assert resp.status_code in (401, 403)


def test_create_story_with_seed_name():
    client = TestClient(app)
    headers = _auth_headers(client)
    payload = {"title": "Test Story", "seed_name": "Avery"}
    resp = client.post("/stories", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("id") is not None
    assert data.get("status") in ("pending", "done")
