import json
import datetime as dt

import pytest

from backend.src.server import server


class FakeSAL:
    """
    Minimal fake SAL that lives entirely in memory.
    It implements all methods that server.py calls.
    """

    def __init__(self):
        # simple in-memory fixtures
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

    # ---------- metadata methods ----------

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
        """
        Return list[list[int]] matching whatever getDirections() returns.
        """
        dirs = self.getDirections(participant, dt_)
        return [self.getEvents(participant, dt_, d) for d in dirs]

    # ---------- high-level event helpers ----------

    def getEventSummary(self, event_id: str):
        """
        Return (event_dict, availability_dict) or None if missing.
        """
        if event_id == "missing":
            return None

        # simple fake event; real values don't matter much for route behavior
        event = {
            "id": event_id,
            "participant": 1001,
            "date": "2024-10-01",
            "direction": "in",
            "event_number": 1,
        }
        availability = {
            "p100": True,
            "grf": True,
            "footsteps": True,
        }
        return event, availability

    def getEventP100(self, event_id: str):
        """
        Return (data, err) where:
        - err is None, "missing_event", or "missing_file"
        """
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_p100":
            return None, "missing_file"
        return [[1.0, 2.0], [3.0, 4.0]], None

    def getEventGRF(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_grf":
            return None, "missing_file"
        return [0.1, 0.2, 0.3], None

    def getEventFootsteps(self, event_id: str):
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_steps":
            return None, "missing_file"
        return (
            [
                {
                    "footstep_id": 0,
                    "p100": [[1.0, 2.0]],
                    "grf": [0.5, 0.6],
                }
            ],
            None,
        )


@pytest.fixture
def client(monkeypatch):
    """
    Patch the global `sal` in server.py so get_sal() returns our FakeSAL,
    then yield a Flask test client.
    """
    from backend.src import server as server_module

    fake_sal = FakeSAL()
    # ensure get_sal() sees our fake instance
    monkeypatch.setattr(server_module, "sal", fake_sal)
    return server.test_client()


# -------------------- basic / health --------------------


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == {"status": "ok"}


# -------------------- dropdown + swipe lookup --------------------


def test_get_participants_ok(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == [1001]


def test_get_dates_ok(client):
    resp = client.get("/api/participants/1001/dates")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    # dates should be ISO strings
    assert data["items"] == ["2024-10-01"]


def test_get_dates_not_found(client):
    # participant with no dates -> 404
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
    # bad date format should yield 400
    resp = client.get("/api/participants/1001/dates/2024-13-40/directions")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["code"] == "invalid_argument"


def test_get_events_ok(client):
    resp = client.get(
        "/api/participants/1001/dates/2024-10-01/directions/in/events"
    )
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
    # directions in FakeSAL: "in" -> [1,2], "out" -> [3]
    assert data["in"] == [1, 2]
    assert data["out"] == [3]


def test_get_swipe_lookup_ok(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/1")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["id"] == "evt-in-1"


def test_get_swipe_lookup_not_found(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/99")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


# -------------------- event summary + assets --------------------


def test_event_summary_ok(client):
    resp = client.get("/api/events/evt-in-1/summary")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["event"]["id"] == "evt-in-1"
    assert "availability" in data
    assert data["availability"]["p100"] is True


def test_event_summary_not_found(client):
    resp = client.get("/api/events/missing/summary")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


def test_event_p100_ok(client):
    resp = client.get("/api/events/evt-in-1/p100")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "p100" in data
    assert isinstance(data["p100"], list)
    assert isinstance(data["p100"][0], list)


def test_event_p100_missing_event(client):
    resp = client.get("/api/events/missing/p100")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


def test_event_p100_missing_file(client):
    resp = client.get("/api/events/nofile_p100/p100")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"
    assert "p100 not available" in data["message"]


def test_event_grf_ok(client):
    resp = client.get("/api/events/evt-in-1/grf")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "grf" in data
    assert isinstance(data["grf"], list)


def test_event_grf_missing_event(client):
    resp = client.get("/api/events/missing/grf")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


def test_event_grf_missing_file(client):
    resp = client.get("/api/events/nofile_grf/grf")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"
    assert "grf not available" in data["message"]


def test_event_footsteps_ok(client):
    resp = client.get("/api/events/evt-in-1/footsteps/data")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert data[0]["footstep_id"] == 0
    assert "p100" in data[0]
    assert "grf" in data[0]


def test_event_footsteps_missing_event(client):
    resp = client.get("/api/events/missing/footsteps/data")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


def test_event_footsteps_missing_file_returns_empty_list(client):
    # server.py returns [] (200) when err == "missing_file"
    resp = client.get("/api/events/nofile_steps/footsteps/data")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []
