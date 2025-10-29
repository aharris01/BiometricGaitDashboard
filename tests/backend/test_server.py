import pytest
from backend.server.app import server


@pytest.fixture
def client():
    server.config["Testing"] = True
    with server.test_client() as client:
        yield client


def test_health(client):
    rv = client.get("/api/health")
    assert rv.status_code == 200
    assert rv.json == {"status": "ok"}
