# tests/test_server.py
import datetime as dt
import json
import pytest

from backend.src.server import create_app


class FakeSAL:
    """
    Fake SAL for route tests.
    Mix camelCase + snake_case because routes currently use both.
    """

    def __init__(self):
        self._participants = [1001]
        self._dates = {1001: [dt.date(2024, 10, 1)]}
        self._directions = {(1001, dt.date(2024, 10, 1)): ["in", "out"]}
        self._events = {
            (1001, dt.date(2024, 10, 1), "in"): [1, 2],
            (1001, dt.date(2024, 10, 1), "out"): [3],
        }
        self._swipe_ids = {
            (1001, dt.date(2024, 10, 1), 1, "in"): "evt-in-1",
            (1001, dt.date(2024, 10, 1), 2, "in"): "evt-in-2",
            (1001, dt.date(2024, 10, 1), 3, "out"): "evt-out-3",
        }

    # ---------------- camelCase (participants/swipe routes) ----------------

    def getParticipants(self):
        return self._participants

    def getDates(self, participant):
        return self._dates.get(participant, [])

    def getDirections(self, participant, dt_):
        return self._directions.get((participant, dt_), [])

    def getEvents(self, participant, dt_, direction):
        return self._events.get((participant, dt_, direction), [])

    def getSwipeEventId(self, participant, dt_, event, direction):
        return self._swipe_ids.get((participant, dt_, event, direction))

    def getBothDirectionEvents(self, participant, dt_):
        dirs = self.getDirections(participant, dt_)
        return {d: self.getEvents(participant, dt_, d) for d in dirs}

    # ---------------- snake_case (events routes) ----------------

    def get_event_summary(self, event_id: str):
        if event_id == "missing":
            return None

        event = {
            "event_id": event_id,
            "participant": 1001,
            "date": "2024-10-01",
            "direction": "in",
            "event_number": 1,
            "state": "ready",
        }
        availability = {
            "p100": True,
            "grf": True,
            "metadata": True,
            "steps": True,
        }
        return event, availability

    def get_p100(self, event_id: str):
        if event_id in ("missing", "nofile_p100"):
            return None
        return [[1.0, 2.0], [3.0, 4.0]]

    def get_grf(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_grf":
            return None, "missing_file"
        return [0.1, 0.2, 0.3], None

    def get_footsteps(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_steps":
            return None, "missing_file"
        return (
            [
                {
                    "id": 0,
                    "start_frame": 0,
                    "end_frame": 10,
                    "x_min": 5,
                    "x_max": 15,
                    "y_min": 20,
                    "y_max": 30,
                }
            ],
            None,
        )

    def get_all_footstep_details(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_stepdetail":
            return None, "missing_file"
        return (
            [
                {"id": 0, "p100": [[1, 2], [3, 4]], "grf": [0.5, 0.6, 0.7]},
                {"id": 1, "p100": [[0, 0], [0, 0]], "grf": [0.1, 0.2]},
            ],
            None,
        )

    # Optional: per-step endpoint uses this in events.py
    def get_footstep_data(self, event_id: str, step_id: int):
        if event_id == "missing":
            return None, None, "missing_event"
        if event_id == "nofile_stepdetail":
            return None, None, "missing_file"
        if step_id != 0:
            return None, None, "missing_file"
        return [[1, 2], [3, 4]], [0.5, 0.6, 0.7], None


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    return app.test_client()


# -------------------- basic --------------------

@pytest.mark.unit
def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# -------------------- dropdown + swipe lookup --------------------

@pytest.mark.unit
def test_get_participants_ok(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    assert resp.get_json()["items"] == [1001]


@pytest.mark.unit
def test_get_dates_ok(client):
    resp = client.get("/api/participants/1001/dates")
    assert resp.status_code == 200
    assert resp.get_json()["items"] == ["2024-10-01"]


@pytest.mark.unit
def test_get_dates_not_found(client):
    resp = client.get("/api/participants/9999/dates")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "not_found"


@pytest.mark.unit
def test_get_directions_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions")
    assert resp.status_code == 200
    assert resp.get_json()["items"] == ["in", "out"]


@pytest.mark.unit
def test_get_directions_invalid_date(client):
    resp = client.get("/api/participants/1001/dates/2024-13-40/directions")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_argument"


@pytest.mark.unit
def test_get_events_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions/in/events")
    assert resp.status_code == 200
    assert resp.get_json()["items"] == [1, 2]


@pytest.mark.unit
def test_get_events_invalid_direction(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions/sideways/events")
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_argument"


@pytest.mark.unit
def test_get_events_by_direction_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/eventsByDirection")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["in"] == [1, 2]
    assert data["out"] == [3]


@pytest.mark.unit
def test_get_swipe_lookup_ok(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/1")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == "evt-in-1"


@pytest.mark.unit
def test_get_swipe_lookup_not_found(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/99")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "not_found"


# -------------------- event full --------------------

@pytest.mark.unit
def test_event_full_ok(client):
    resp = client.get("/api/events/evt-in-1/full")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "event" in data and "availability" in data
    assert "p100" in data and "grf" in data
    assert "footsteps" in data
    assert "footstep_details" in data

    assert data["event"]["event_id"] == "evt-in-1"
    assert isinstance(data["footstep_details"], list)
    assert data["footstep_details"][0]["id"] == 0


@pytest.mark.unit
def test_event_full_not_found(client):
    resp = client.get("/api/events/missing/full")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "not_found"


@pytest.mark.unit
def test_event_full_missing_grf_file_returns_empty_list(client):
    resp = client.get("/api/events/nofile_grf/full")
    assert resp.status_code == 200
    assert resp.get_json()["grf"] == []


@pytest.mark.unit
def test_event_full_missing_steps_file_returns_empty_lists(client):
    resp = client.get("/api/events/nofile_steps/full")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["footsteps"] == []


@pytest.mark.unit
def test_event_full_missing_stepdetail_file_returns_empty_list(client):
    resp = client.get("/api/events/nofile_stepdetail/full")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["footstep_details"] == []


# -------------------- per-footstep detail endpoint (still supported) --------------------

@pytest.mark.unit
def test_footstep_detail_ok(client):
    resp = client.get("/api/events/evt-in-1/footsteps/0")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "p100" in data and "grf" in data
    assert isinstance(data["p100"], list)
    assert isinstance(data["grf"], list)


@pytest.mark.unit
def test_footstep_detail_missing_event(client):
    resp = client.get("/api/events/missing/footsteps/0")
    assert resp.status_code == 404
    assert resp.get_json()["code"] == "not_found"
