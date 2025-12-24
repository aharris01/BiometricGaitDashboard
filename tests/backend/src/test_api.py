# tests/test_api.py
import pytest

from backend.src.server import create_app


class FakeSAL:
    # participants route expects list[int]
    def getParticipants(self):
        return [1, 2]


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
    assert resp.get_json() == {"items": [1, 2]}
