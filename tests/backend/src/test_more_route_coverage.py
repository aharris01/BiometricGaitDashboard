import datetime as dt
import pytest

from backend.src.server import create_app


class FakeSAL:
    # ---- swipe route needs this ----
    def getSwipeEventId(self, participant: int, date: dt.date, event: int, direction: str):
        # only one valid combo; everything else returns None
        if participant == 1001 and date == dt.date(2024, 10, 1) and event == 1 and direction == "in":
            return "evt-in-1"
        return None

    # ---- events/full route needs these ----
    def get_event_summary(self, event_id: str):
        if event_id == "missing":
            return None
        return (
            {
                "event_id": event_id,
                "participant": 1001,
                "date": "2024-10-01",
                "direction": "in",
                "event_number": 1,
                "state": "ready",
            },
            {"p100": True, "grf": True, "metadata": True, "steps": True},
        )

    def get_p100(self, event_id: str):
        return [[1, 2], [3, 4]]

    def get_grf(self, event_id: str):
        if event_id == "nofile_grf":
            return None, "missing_file"
        return [0.1, 0.2, 0.3], None

    def get_footsteps(self, event_id: str):
        if event_id == "nofile_steps":
            return None, "missing_file"
        return (
            [
                {
                    "id": 0,
                    "start_frame": 0,
                    "end_frame": 10,
                    "x_min": 1,
                    "x_max": 2,
                    "y_min": 3,
                    "y_max": 4,
                }
            ],
            None,
        )

    def get_all_footstep_details(self, event_id: str):
        if event_id == "nofile_details":
            return None, "missing_file"
        return ([{"id": 0, "p100": [[1]], "grf": [0.5, 0.6]}], None)


@pytest.fixture
def client():
    app = create_app(sal=FakeSAL())
    with app.test_client() as c:
        yield c


# -------------------------
# swipe.py route coverage
# -------------------------

@pytest.mark.unit
def test_swipe_invalid_date_returns_400(client):
    resp = client.get("/api/swipe/1001/2024-99-99/in/1")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "invalid_argument"


@pytest.mark.unit
def test_swipe_invalid_direction_returns_400(client):
    resp = client.get("/api/swipe/1001/2024-10-01/sideways/1")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "invalid_argument"


@pytest.mark.unit
def test_swipe_not_found_returns_404(client):
    resp = client.get("/api/swipe/9999/2024-10-01/in/1")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"


# -------------------------
# events.py route coverage
# -------------------------

@pytest.mark.unit
def test_event_full_missing_event_returns_404(client):
    resp = client.get("/api/events/missing/full")
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"


@pytest.mark.unit
def test_event_full_grf_missing_file_returns_empty_grf(client):
    resp = client.get("/api/events/nofile_grf/full")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["grf"] == []  # route converts missing_file to empty list


@pytest.mark.unit
def test_event_full_footsteps_missing_file_returns_empty_footsteps(client):
    resp = client.get("/api/events/nofile_steps/full")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["footsteps"] == []  # route converts missing_file to empty list


@pytest.mark.unit
def test_event_full_details_missing_file_returns_empty_details(client):
    resp = client.get("/api/events/nofile_details/full")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["footstep_details"] == []  # route converts missing_file to empty list
