import uuid
from fastapi.testclient import TestClient
from app.main import app


def _unique_email():
    return f"tester+{uuid.uuid4().hex[:8]}@example.com"


def test_protected_endpoints_require_auth():
    client = TestClient(app)
    # stories list should require auth
    resp = client.get("/stories")
    assert resp.status_code in (401, 403)


def test_register_and_login_and_create_research():
    client = TestClient(app)

    email = _unique_email()
    password = "passw0rd!"

    # register
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201)

    # login
    t = client.post("/auth/token", data={"username": email, "password": password})
    assert t.status_code == 200, t.text
    token = t.json().get("access_token")
    assert token and isinstance(token, str)

    headers = {"Authorization": f"Bearer {token}"}

    # create research
    name = "Avery"
    rr = client.post("/research", json={"name": name}, headers=headers)
    assert rr.status_code in (200, 201)
    data = rr.json()
    assert isinstance(data, dict)
    # Accept id or research object with id
    rid = data.get("id") or data.get("research", {}).get("id")
    assert rid is not None
