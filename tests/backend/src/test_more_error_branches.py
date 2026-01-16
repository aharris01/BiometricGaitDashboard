import pytest
from backend.src.server import create_app


class FakeSAL:
    # participants route
    def get_participants(self):
        raise RuntimeError("boom")

    # events routes
    def get_all_footstep_p100(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile":
            return None, "missing_file"
        return [{"id": 0, "p100": [[1]]}], None

    def get_footstep_data(self, event_id: str, step_id: int):
        if event_id == "missing":
            return None, None, "missing_event"
        if event_id == "nofile":
            return None, None, "missing_file"
        return [[1]], [0.1, 0.2], None


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    with app.test_client() as c:
        yield c


@pytest.mark.unit
def test_participants_internal_error_500(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["code"] == "internal_error"


@pytest.mark.unit
def test_event_footsteps_p100s_missing_event_404(client):
    resp = client.get("/api/events/missing/footsteps/p100s")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_footsteps_p100s_missing_file_returns_empty_list(client):
    resp = client.get("/api/events/nofile/footsteps/p100s")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["items"] == []


@pytest.mark.unit
def test_event_footstep_detail_missing_event_404(client):
    resp = client.get("/api/events/missing/footsteps/0")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_footstep_detail_missing_file_404(client):
    resp = client.get("/api/events/nofile/footsteps/0")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"
    assert data["message"] == "footstep data not found"
