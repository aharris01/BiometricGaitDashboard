import pytest

pytestmark = pytest.mark.unit


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
def client(app_factory):
    app = app_factory(FakeSAL())
    with app.test_client() as c:
        yield c


def test_participants_internal_error_500(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["code"] == "internal_error"
