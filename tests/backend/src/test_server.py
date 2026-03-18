import json
import datetime as dt

import pytest

pytestmark = pytest.mark.unit


class FakeSAL:
    """
    Minimal fake SAL that lives entirely in memory.

    Routes use snake_case, but we also provide camelCase wrappers for compatibility.
    IMPORTANT: Do NOT redefine snake_case methods twice (will overwrite + can recurse).
    """

    def __init__(self):
        self._participants = [1001]
        self._dates = {1001: [dt.date(2024, 10, 1)]}
        self._directions = {
            (1001, dt.date(2024, 10, 1)): ["in", "out"],
        }
        self._events = {
            (1001, dt.date(2024, 10, 1), "in"): [1, 2],
            (1001, dt.date(2024, 10, 1), "out"): [3],
        }
        self._swipe_ids = {
            (1001, dt.date(2024, 10, 1), 1, "in"): "evt-in-1",
            (1001, dt.date(2024, 10, 1), 2, "in"): "evt-in-2",
            (1001, dt.date(2024, 10, 1), 3, "out"): "evt-out-3",
        }

    # --------------------
    # snake_case API (used by routes)
    # --------------------

    def get_participants(self):
        return self._participants

    def get_dates(self, participant):
        return self._dates.get(participant, [])

    def get_directions(self, participant, dt_):
        return self._directions.get((participant, dt_), [])

    def get_events(self, participant, dt_, direction):
        return self._events.get((participant, dt_, direction), [])

    def get_swipe_event_id(self, participant, dt_, event, direction):
        return self._swipe_ids.get((participant, dt_, event, direction))

    def get_both_direction_events(self, participant, dt_):
        dirs = self.get_directions(participant, dt_)
        return {d: self.get_events(participant, dt_, d) for d in dirs}

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
        availability = {"p100": True, "grf": True, "metadata": True, "steps": True}
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
        steps = [
            {
                "id": 0,
                "start_frame": 0,
                "end_frame": 10,
                "x_min": 5,
                "x_max": 15,
                "y_min": 20,
                "y_max": 30,
            }
        ]
        return steps, None

    def get_footstep_data(self, event_id: str, step_id: int):
        if event_id == "missing":
            return None, None, "missing_event"
        if event_id == "nofile_stepdetail":
            return None, None, "missing_file"
        if step_id != 0:
            return None, None, "missing_file"
        return [[1.0, 2.0], [3.0, 4.0]], [0.5, 0.6, 0.7], None

    def get_all_footstep_details(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_steps":
            return None, "missing_file"
        # Must return: (items, None) on success
        return [{"id": 0, "p100": [[1.0]], "grf": [0.5, 0.6]}], None

    # --------------------
    # camelCase wrappers (compat)
    # --------------------

    def getParticipants(self):
        return self.get_participants()

    def getDates(self, participant):
        return self.get_dates(participant)

    def getDirections(self, participant, dt_):
        return self.get_directions(participant, dt_)

    def getEvents(self, participant, dt_, direction):
        return self.get_events(participant, dt_, direction)

    def getSwipeEventId(self, participant, dt_, event, direction):
        return self.get_swipe_event_id(participant, dt_, event, direction)

    def getBothDirectionEvents(self, participant, dt_):
        return self.get_both_direction_events(participant, dt_)

    def getEventSummary(self, event_id: str):
        return self.get_event_summary(event_id)

    def getP100(self, event_id: str):
        return self.get_p100(event_id)

    def getGRF(self, event_id: str):
        return self.get_grf(event_id)

    def getFootsteps(self, event_id: str):
        return self.get_footsteps(event_id)

    def getFootstepData(self, event_id: str, step_id: int):
        return self.get_footstep_data(event_id, step_id)

    def getAllFootstepDetails(self, event_id: str):
        return self.get_all_footstep_details(event_id)


@pytest.fixture
def client(app_factory):
    app = app_factory(FakeSAL())
    with app.test_client() as client_:
        yield client_


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == {"status": "ok"}


def test_get_participants_ok(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == [1001]


def test_get_dates_ok(client):
    resp = client.get("/api/participants/1001/dates")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == ["2024-10-01"]


def test_get_dates_not_found(client):
    resp = client.get("/api/participants/9999/dates")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


def test_get_directions_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == ["in", "out"]


def test_get_directions_invalid_date(client):
    resp = client.get("/api/participants/1001/dates/2024-13-40/directions")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["code"] == "invalid_argument"


def test_get_events_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions/in/events")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == [1, 2]


def test_get_events_invalid_direction(client):
    resp = client.get(
        "/api/participants/1001/dates/2024-10-01/directions/sideways/events"
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["code"] == "invalid_argument"


def test_get_events_by_direction_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/eventsByDirection")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["in"] == [1, 2]
    assert data["out"] == [3]
