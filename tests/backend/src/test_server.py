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
        Return dict[str, list[int]] matching whatever getDirections() returns.
        """
        dirs = self.getDirections(participant, dt_)
        result = {}
        for d in dirs:
            result[d] = self.getEvents(participant, dt_, d)
        return result

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

    def getP100(self, event_id: str):
        """
        Match real SAL.getP100 semantics:
        - returns a 2D list on success
        - returns None if event/file is missing
        server.py turns None into {"p100": []} with status 200.
        """
        if event_id in ("missing", "nofile_p100"):
            return None
        return [[1.0, 2.0], [3.0, 4.0]]

    def getGRF(self, event_id: str):
        """
        Match real SAL.getGRF semantics:
        - returns (data_list, None) on success
        - returns (None, "missing_event" | "missing_file") on failure
        """
        if event_id == "missing":
            return None, "missing_event"
        if event_id == "nofile_grf":
            return None, "missing_file"
        return [0.1, 0.2, 0.3], None

    def getFootsteps(self, event_id: str):
        """
        Match real SAL.getFootsteps semantics:
        - returns (steps, None) where steps is a list of bounding-box dicts
        - returns (None, "missing_event" | "missing_file") on failure
        """
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

    def getFootstepData(self, event_id: str, step_id: int):
        """
        Match real SAL.getFootstepData semantics:
        - returns (step_p100, step_grf, None) on success
        - returns (..., ..., "missing_event" | "missing_file") on failure
        """
        if event_id == "missing":
            return None, None, "missing_event"
        if event_id == "nofile_stepdetail":
            return None, None, "missing_file"

        if step_id != 0:
            # treat unknown step as missing file for simplicity
            return None, None, "missing_file"

        step_p100 = [[1.0, 2.0], [3.0, 4.0]]
        step_grf = [0.5, 0.6, 0.7]
        return step_p100, step_grf, None

        # ---- snake_case API expected by server.py ----

    def get_participants(self):
        return self.getParticipants()

    def get_dates(self, participant):
        return self.getDates(participant)

    def get_directions(self, participant, dt_):
        return self.getDirections(participant, dt_)

    def get_events(self, participant, dt_, direction):
        return self.getEvents(participant, dt_, direction)

    def get_both_direction_events(self, participant, dt_):
        return self.getBothDirectionEvents(participant, dt_)

    def get_swipe_event_id(self, participant, dt_, event, direction):
        return self.getSwipeEventId(participant, dt_, event, direction)

    def get_event_summary(self, event_id):
        return self.getEventSummary(event_id)

    def get_p100(self, event_id):
        return self.getP100(event_id)

    def get_grf(self, event_id):
        return self.getGRF(event_id)

    def get_foot_steps(self, event_id):
        return self.getFootsteps(event_id)

    def get_footstep_data(self, event_id, step_id):
        return self.getFootstepData(event_id, step_id)


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


@pytest.mark.unit
def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == {"status": "ok"}


# -------------------- dropdown + swipe lookup --------------------


@pytest.mark.unit
def test_get_participants_ok(client):
    resp = client.get("/api/participants")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == [1001]


@pytest.mark.unit
def test_get_dates_ok(client):
    resp = client.get("/api/participants/1001/dates")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    # dates should be ISO strings
    assert data["items"] == ["2024-10-01"]


@pytest.mark.unit
def test_get_dates_not_found(client):
    # participant with no dates -> 404
    resp = client.get("/api/participants/9999/dates")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_get_directions_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == ["in", "out"]


@pytest.mark.unit
def test_get_directions_invalid_date(client):
    # bad date format should yield 400
    resp = client.get("/api/participants/1001/dates/2024-13-40/directions")
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["code"] == "invalid_argument"


@pytest.mark.unit
def test_get_events_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/directions/in/events")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["items"] == [1, 2]


@pytest.mark.unit
def test_get_events_invalid_direction(client):
    resp = client.get(
        "/api/participants/1001/dates/2024-10-01/directions/sideways/events"
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data["code"] == "invalid_argument"


@pytest.mark.unit
def test_get_events_by_direction_ok(client):
    resp = client.get("/api/participants/1001/dates/2024-10-01/eventsByDirection")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    # directions in FakeSAL: "in" -> [1,2], "out" -> [3]
    assert data["in"] == [1, 2]
    assert data["out"] == [3]


@pytest.mark.unit
def test_get_swipe_lookup_ok(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/1")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["id"] == "evt-in-1"


@pytest.mark.unit
def test_get_swipe_lookup_not_found(client):
    resp = client.get("/api/swipe/1001/2024-10-01/in/99")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


# -------------------- event summary + assets --------------------


@pytest.mark.unit
def test_event_summary_ok(client):
    resp = client.get("/api/events/evt-in-1/summary")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["event"]["id"] == "evt-in-1"
    assert "availability" in data
    assert data["availability"]["p100"] is True


@pytest.mark.unit
def test_event_summary_not_found(client):
    resp = client.get("/api/events/missing/summary")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_p100_ok(client):
    resp = client.get("/api/events/evt-in-1/p100")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "p100" in data
    assert isinstance(data["p100"], list)
    assert isinstance(data["p100"][0], list)


@pytest.mark.unit
def test_event_p100_missing_returns_empty_list(client):
    resp = client.get("/api/events/missing/p100")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["p100"] == []


@pytest.mark.unit
def test_event_p100_missing_file_returns_empty_list(client):
    resp = client.get("/api/events/nofile_p100/p100")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["p100"] == []


@pytest.mark.unit
def test_event_grf_ok(client):
    resp = client.get("/api/events/evt-in-1/grf")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "grf" in data
    assert isinstance(data["grf"], list)


@pytest.mark.unit
def test_event_grf_missing_event(client):
    resp = client.get("/api/events/missing/grf")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_grf_missing_file(client):
    resp = client.get("/api/events/nofile_grf/grf")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"
    assert "grf not available" in data["message"]


@pytest.mark.unit
def test_event_footsteps_ok(client):
    resp = client.get("/api/events/evt-in-1/footsteps/data")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    step = data[0]
    assert step["id"] == 0
    assert "x_min" in step and "x_max" in step
    assert "y_min" in step and "y_max" in step


@pytest.mark.unit
def test_event_footsteps_missing_event(client):
    resp = client.get("/api/events/missing/footsteps/data")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_footsteps_missing_file_returns_empty_list(client):
    # server.py returns [] (200) when err == "missing_file"
    resp = client.get("/api/events/nofile_steps/footsteps/data")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []


# -------------------- per-footstep detail --------------------


@pytest.mark.unit
def test_footstep_detail_ok(client):
    resp = client.get("/api/events/evt-in-1/footsteps/0")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "p100" in data
    assert "grf" in data
    assert isinstance(data["p100"], list)
    assert isinstance(data["grf"], list)


@pytest.mark.unit
def test_footstep_detail_missing_event(client):
    resp = client.get("/api/events/missing/footsteps/0")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_footstep_detail_missing_file(client):
    resp = client.get("/api/events/nofile_stepdetail/footsteps/0")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert data["code"] == "not_found"
    assert "footstep data not available" in data["message"]
