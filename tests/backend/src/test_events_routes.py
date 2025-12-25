import pytest

from backend.src.server import create_app


class FakeSAL:
    def get_event_summary(self, event_id: str):
        # Must return (event_dict, availability_dict) or None
        return (
            {
                "event_id": event_id,
                "participant": 1,
                "date": "2025-01-01",
                "direction": "in",
                "event_number": 1,
                "state": "ready",
            },
            {
                "p100": True,
                "grf": True,
                "metadata": True,
                "steps": True,
            },
        )

    def get_p100(self, event_id: str):
        return [[1, 2], [3, 4]]

    def get_grf(self, event_id: str):
        return ([0.1, 0.2, 0.3], None)

    def get_footsteps(self, event_id: str):
        return (
            [
                {
                    "id": 0,
                    "start_frame": 0,
                    "end_frame": 10,
                    "x_min": 0,
                    "x_max": 10,
                    "y_min": 0,
                    "y_max": 10,
                }
            ],
            None,
        )

    def get_all_footstep_details(self, event_id: str):
        # New combined thumbnail + per-step grf payload
        return (
            [
                {"id": 0, "p100": [[1]], "grf": [0.0, 1.0]},
            ],
            None,
        )

    def get_all_footstep_p100(self, event_id: str):
        return ([{"id": 0, "p100": [[1]]}], None)


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    with app.test_client() as c:
        yield c


@pytest.mark.unit
def test_event_full_ok(client):
    resp = client.get("/api/events/evt-1/full")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "event" in data
    assert "availability" in data
    assert "p100" in data
    assert "grf" in data
    assert "footsteps" in data
    assert "footstep_details" in data


@pytest.mark.unit
def test_event_footsteps_p100s_ok(client):
    resp = client.get("/api/events/evt-1/footsteps/p100s")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["items"][0]["id"] == 0
