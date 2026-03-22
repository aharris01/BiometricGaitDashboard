import pytest

pytestmark = pytest.mark.unit

# -------------------------------------------------------------------
# Base Fake SALs
# -------------------------------------------------------------------


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

    def get_footstep_data(self, event_id: str, step_id: int):
        return ([1, 2], [0.1, 0.2], None)

    def get_available_metrics(self):
        return ["avg_bbox_size", "step_count"]

    def get_swipe_event_summary_plot_data(self, x: str, y: str, filters=None):
        return {"evt-1": {x: 1.0, y: 2.0}}

    def get_date_bounds(self, filters=None):
        return {"min_date": None, "max_date": None}

    def get_distinct_date_values(self, part: str, filters=None):
        return []


class FakeSALMissingEvent:
    def get_event_summary(self, event_id: str):
        return None


@pytest.fixture
def client(app_factory):
    app = app_factory(FakeSAL())
    with app.test_client() as c:
        yield c


# -------------------------------------------------------------------
# Existing tests (unchanged behavior)
# -------------------------------------------------------------------


def test_event_full_ok(client):
    resp = client.get("/api/events/evt-1/full")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "event" in data
    assert "availability" in data
    assert "p100" in data
    assert "grf" in data
    assert "footsteps" in data


def test_event_footsteps_p100s_ok(client):
    resp = client.get("/api/events/evt-1/footsteps/p100s")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["items"][0]["id"] == 0


def test_event_full_missing_event_returns_404(app_factory):
    app = app_factory(FakeSALMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/missing/full")
        assert resp.status_code == 404


class FakeSALFootstepMissingEvent(FakeSAL):
    def get_all_footstep_p100(self, event_id: str):
        return (None, "missing_event")


def test_event_footsteps_p100s_missing_event_returns_404(app_factory):
    app = app_factory(FakeSALFootstepMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/footsteps/p100s")
        assert resp.status_code == 404


class FakeSALFootstepMissingFile(FakeSAL):
    def get_all_footstep_p100(self, event_id: str):
        return (None, "missing_file")


def test_event_footsteps_p100s_missing_file_returns_empty_list(app_factory):
    app = app_factory(FakeSALFootstepMissingFile())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/footsteps/p100s")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []


class FakeSALFootstepDetail(FakeSAL):
    def get_footstep_context_data(self, event_id: str, step_id: int):
        return (
            {
                "p100": [1, 2],
                "grf": [0.1, 0.2],
                "cop_x": [0.0, 1.0],
                "cop_y": [1.0, 0.0],
            },
            None,
        )


def test_event_footstep_detail_ok(app_factory):
    app = app_factory(FakeSALFootstepDetail())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "p100" in data
        assert "grf" in data
        assert "cop_x" in data
        assert "cop_y" in data


class FakeSALFootstepDetailMissingEvent(FakeSAL):
    def get_footstep_context_data(self, event_id: str, step_id: int):
        return (None, "missing_event")


def test_event_footstep_detail_missing_event(app_factory):
    app = app_factory(FakeSALFootstepDetailMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 404


class FakeSALFootstepDetailMissingFile(FakeSAL):
    def get_footstep_context_data(self, event_id: str, step_id: int):
        return (None, "missing_file")


def test_event_footstep_detail_missing_file(app_factory):
    app = app_factory(FakeSALFootstepDetailMissingFile())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/footsteps/0")
        assert resp.status_code == 404


# -------------------------------------------------------------------
# Summary plot tests (match current SAL-backed route behavior)
# -------------------------------------------------------------------


class FakeSALSummaryPlot(FakeSAL):
    def get_available_metrics(self):
        return ["avg_bbox_size", "step_count"]

    def get_swipe_event_summary_plot_data(self, x: str, y: str, filters=None):
        return {"evt-1": {x: 1.0, y: 2.0}}


def test_summary_plot_ok(app_factory):
    app = app_factory(FakeSALSummaryPlot())
    with app.test_client() as client_:
        resp = client_.get("/api/events/summaryplot?x=avg_bbox_size&y=step_count")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "evt-1" in data


def test_summary_plot_missing_metrics(app_factory):
    app = app_factory(FakeSALSummaryPlot())
    with app.test_client() as client_:
        resp = client_.get("/api/events/summaryplot?x=avg_bbox_size")
        assert resp.status_code == 400


def test_summaryplot_invalid_metric_returns_400(app_factory):
    app = app_factory(FakeSALSummaryPlot())
    with app.test_client() as client_:
        resp = client_.get("/api/events/summaryplot?x=not_a_metric&y=step_count")
        assert resp.status_code == 400


def test_summaryplot_bad_date_order_returns_400(app_factory):
    app = app_factory(FakeSALSummaryPlot())
    with app.test_client() as client_:
        resp = client_.get(
            "/api/events/summaryplot?x=avg_bbox_size&y=step_count&date_from=2025-02-01&date_to=2025-01-01"
        )
        assert resp.status_code == 400


# -------------------------------------------------------------------
# Date filter endpoint tests (match current SAL-backed route behavior)
# -------------------------------------------------------------------


class FakeSALDates(FakeSAL):
    def get_distinct_date_values(self, part: str, filters=None):
        if part == "year":
            return [2024, 2025]
        return []


def test_years_endpoint_ok(app_factory):
    app = app_factory(FakeSALDates())
    with app.test_client() as client_:
        resp = client_.get("/api/events/years")
        assert resp.status_code == 200
        assert resp.get_json() == [2024, 2025]


class FakeSALGrfMissingEvent(FakeSAL):
    def get_grf(self, event_id: str):
        return (None, "missing_event")


def test_event_full_grf_missing_event_returns_404(app_factory):
    app = app_factory(FakeSALGrfMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALFootstepsMissingEvent(FakeSAL):
    def get_footsteps(self, event_id: str):
        return (None, "missing_event")


def test_event_full_footsteps_missing_event_returns_404(app_factory):
    app = app_factory(FakeSALFootstepsMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALFootstepsMissingFile(FakeSAL):
    def get_footsteps(self, event_id: str):
        return (None, "missing_file")


def test_event_full_footsteps_missing_file_returns_empty_list(app_factory):
    app = app_factory(FakeSALFootstepsMissingFile())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/full")
        assert resp.status_code == 200
        assert resp.get_json()["footsteps"] == []


class FakeSALDetailsMissingEvent(FakeSAL):
    def get_all_footstep_details(self, event_id: str):
        return (None, "missing_event")


def test_event_full_details_missing_event_returns_404(app_factory):
    app = app_factory(FakeSALDetailsMissingEvent())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/full")
        assert resp.status_code == 404


class FakeSALDetailsMissingFile(FakeSAL):
    def get_all_footstep_details(self, event_id: str):
        return (None, "missing_file")


def test_event_full_details_missing_file_returns_empty_list(app_factory):
    app = app_factory(FakeSALDetailsMissingFile())
    with app.test_client() as client_:
        resp = client_.get("/api/events/evt-1/full")
        assert resp.status_code == 200
        assert resp.get_json()["footstep_details"] == []


# -------------------------------------------------------------------
# Additional events/date endpoint tests
# -------------------------------------------------------------------


def test_available_metrics_endpoint_ok(app_factory):
    app = app_factory(FakeSAL())
    with app.test_client() as client_:
        resp = client_.get("/api/events/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "avg_bbox_size" in data["items"]
        assert "step_count" in data["items"]


class FakeSALDateBoundsOk(FakeSAL):
    def get_date_bounds(self, filters=None):
        return {"min_date": "2024-01-01", "max_date": "2024-12-31"}


def test_date_bounds_ok_returns_iso_dates(app_factory):
    app = app_factory(FakeSALDateBoundsOk())
    with app.test_client() as client_:
        resp = client_.get("/api/events/date_bounds")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["min_date"] == "2024-01-01"
        assert data["max_date"] == "2024-12-31"


class FakeSALDateBoundsEmpty(FakeSAL):
    def get_date_bounds(self, filters=None):
        return {"min_date": None, "max_date": None}


def test_date_bounds_empty_returns_nulls(app_factory):
    app = app_factory(FakeSALDateBoundsEmpty())
    with app.test_client() as client_:
        resp = client_.get("/api/events/date_bounds")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["min_date"] is None
        assert data["max_date"] is None


class FakeSALMonths(FakeSAL):
    def get_distinct_date_values(self, part: str, filters=None):
        if part == "month":
            return [1, 2, 12]
        return []


def test_months_endpoint_ok_returns_sorted_unique(app_factory):
    app = app_factory(FakeSALMonths())
    with app.test_client() as client_:
        resp = client_.get("/api/events/months?year=2024&participants=1,2")
        assert resp.status_code == 200
        assert resp.get_json() == [1, 2, 12]


class FakeSALDays(FakeSAL):
    def get_distinct_date_values(self, part: str, filters=None):
        if part == "day":
            return [1, 15, 31]
        return []


def test_days_endpoint_ok_returns_sorted_unique(app_factory):
    app = app_factory(FakeSALDays())
    with app.test_client() as client_:
        resp = client_.get("/api/events/days?year=2024&month=1&participants=1")
        assert resp.status_code == 200
        assert resp.get_json() == [1, 15, 31]
