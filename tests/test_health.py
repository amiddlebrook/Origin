from fastapi.testclient import TestClient
from app.main import app


def test_healthz():
    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


def test_readyz_smoke():
    with TestClient(app) as client:
        r = client.get("/readyz")
        assert r.status_code == 200
        assert "details" in r.json()
