# tests/backend/src/test_api.py
import pytest

from backend.src.server import create_app


class FakeSAL:
    # ✅ match new routes (snake_case)
    def get_participants(self):
        return [1]


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    with app.test_client() as client:
        yield client


@pytest.mark.integration
def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


@pytest.mark.integration
def test_participants(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    assert resp.get_json() == {"items": [1]}
