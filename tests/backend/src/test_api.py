# tests/test_api.py
import pytest

from backend.src.server import create_app


class FakeSAL:
    def getParticipants(self):
        return [{"id": 1, "name": "Alice"}]


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_participants(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    assert resp.get_json() == {"items": [{"id": 1, "name": "Alice"}]}
