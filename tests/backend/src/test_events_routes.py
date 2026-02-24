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


class FakeSALMissingEvent:
    def get_event_summary(self, event_id: str):
        return None


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


@pytest.mark.unit
def test_event_full_missing_event_returns_404():
    app = create_app(sal=FakeSALMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/missing/full")
        assert resp.status_code == 404


class FakeSALFootstepMissingEvent(FakeSAL):
    def get_all_footstep_p100(self, event_id: str):
        return (None, "missing_event")


@pytest.mark.unit
def test_event_footsteps_p100s_missing_event_returns_404():
    app = create_app(sal=FakeSALFootstepMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/footsteps/p100s")
        assert resp.status_code == 404


class FakeSALFootstepMissingFile(FakeSAL):
    def get_all_footstep_p100(self, event_id: str):
        return (None, "missing_file")


@pytest.mark.unit
def test_event_footsteps_p100s_missing_file_returns_empty_list():
    app = create_app(sal=FakeSALFootstepMissingFile())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/footsteps/p100s")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []


class FakeSALFootstepDetail(FakeSAL):
    def get_footstep_data(self, event_id: str, step_id: int):
        return ([1, 2], [0.1, 0.2], None)


@pytest.mark.unit
def test_event_footstep_detail_ok():
    app = create_app(sal=FakeSALFootstepDetail())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "p100" in data
        assert "grf" in data


class FakeSALFootstepDetailMissingEvent(FakeSAL):
    def get_footstep_data(self, event_id: str, step_id: int):
        return (None, None, "missing_event")


@pytest.mark.unit
def test_event_footstep_detail_missing_event():
    app = create_app(sal=FakeSALFootstepDetailMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 404


class FakeSALFootstepDetailMissingFile(FakeSAL):
    def get_footstep_data(self, event_id: str, step_id: int):
        return (None, None, "missing_file")


@pytest.mark.unit
def test_event_footstep_detail_missing_file():
    app = create_app(sal=FakeSALFootstepDetailMissingFile())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 404


class FakeSALSummaryPlot(FakeSAL):
    def get_swipe_event_summary_plot_data(self, x, y, filters):
        return [{"x": 1, "y": 2}]


@pytest.mark.unit
def test_summary_plot_ok():
    app = create_app(sal=FakeSALSummaryPlot())
    with app.test_client() as client:
        resp = client.get("/api/events/summaryplot?x=a&y=b")
        assert resp.status_code == 200


@pytest.mark.unit
def test_summary_plot_missing_metrics():
    app = create_app(sal=FakeSALSummaryPlot())
    with app.test_client() as client:
        resp = client.get("/api/events/summaryplot?x=a")
        assert resp.status_code == 400


class FakeSALDates(FakeSAL):
    def get_distinct_date_part(self, part, filters):
        return [2024]


@pytest.mark.unit
def test_years_endpoint_ok():
    app = create_app(sal=FakeSALDates())
    with app.test_client() as client:
        resp = client.get("/api/events/years")
        assert resp.status_code == 200


class FakeSALGrfMissingEvent(FakeSAL):
    def get_grf(self, event_id: str):
        return (None, "missing_event")


@pytest.mark.unit
def test_event_full_grf_missing_event_returns_404():
    app = create_app(sal=FakeSALGrfMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALFootstepsMissingEvent(FakeSAL):
    def get_footsteps(self, event_id: str):
        return (None, "missing_event")


@pytest.mark.unit
def test_event_full_footsteps_missing_event_returns_404():
    app = create_app(sal=FakeSALFootstepsMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALFootstepsMissingFile(FakeSAL):
    def get_footsteps(self, event_id: str):
        return (None, "missing_file")


@pytest.mark.unit
def test_event_full_footsteps_missing_file_returns_empty_list():
    app = create_app(sal=FakeSALFootstepsMissingFile())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/full")
        assert resp.status_code == 200
        assert resp.get_json()["footsteps"] == []


class FakeSALDetailsMissingEvent(FakeSAL):
    def get_all_footstep_details(self, event_id: str):
        return (None, "missing_event")


@pytest.mark.unit
def test_event_full_details_missing_event_returns_404():
    app = create_app(sal=FakeSALDetailsMissingEvent())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALDetailsMissingFile(FakeSAL):
    def get_all_footstep_details(self, event_id: str):
        return (None, "missing_file")


@pytest.mark.unit
def test_event_full_details_missing_file_returns_empty_list():
    app = create_app(sal=FakeSALDetailsMissingFile())
    with app.test_client() as client:
        resp = client.get("/api/events/evt-1/full")
        assert resp.status_code == 200
        assert resp.get_json()["footstep_details"] == []
