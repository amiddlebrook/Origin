from fastapi.testclient import TestClient
from app.main import app


def test_openapi_json_served():
    with TestClient(app) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "openapi" in data


def test_docs_route_available():
    with TestClient(app) as client:
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "").lower()
