import datetime as dt

import pytest


class FakeSAL:
    def __init__(self):
        self.calls = []

    def search_footsteps(
        self,
        event_ids=None,
        participants=None,
        date_from=None,
        date_to=None,
        width_min=None,
        width_max=None,
        height_min=None,
        height_max=None,
        size_min=None,
        size_max=None,
        offset=0,
        limit=60,
    ):
        self.calls.append(
            {
                "event_ids": event_ids,
                "participants": participants,
                "date_from": date_from,
                "date_to": date_to,
                "width_min": width_min,
                "width_max": width_max,
                "height_min": height_min,
                "height_max": height_max,
                "size_min": size_min,
                "size_max": size_max,
                "offset": offset,
                "limit": limit,
            }
        )
        return {
            "items": [
                {
                    "event_id": "evt-1",
                    "footstep_id": 1,
                    "bbox_area": 123,
                }
            ],
            "total": 1,
        }


class ErrorSAL:
    def search_footsteps(
        self,
        event_ids=None,
        participants=None,
        date_from=None,
        date_to=None,
        width_min=None,
        width_max=None,
        height_min=None,
        height_max=None,
        size_min=None,
        size_max=None,
        offset=0,
        limit=60,
    ):
        raise RuntimeError("boom")


@pytest.fixture
def fake_sal():
    return FakeSAL()


@pytest.fixture
def client(app_factory, fake_sal):
    app = app_factory(fake_sal)
    with app.test_client() as c:
        yield c


@pytest.mark.unit
def test_search_footsteps_ok_returns_payload_and_passes_filters(client, fake_sal):
    resp = client.get(
        "/api/footsteps/search"
        "?participants=11111,22222"
        "&date_from=2025-01-01"
        "&date_to=2025-01-31"
        "&width_min=10"
        "&width_max=20"
        "&height_min=15"
        "&height_max=30"
        "&size_min=100"
        "&size_max=500"
        "&offset=10"
        "&limit=25"
    )

    assert resp.status_code == 200
    assert resp.get_json() == {
        "items": [
            {
                "event_id": "evt-1",
                "footstep_id": 1,
                "bbox_area": 123,
            }
        ],
        "total": 1,
    }

    assert fake_sal.calls == [
        {
            "event_ids": None,
            "participants": [11111, 22222],
            "date_from": dt.date(2025, 1, 1),
            "date_to": dt.date(2025, 1, 31),
            "width_min": 10,
            "width_max": 20,
            "height_min": 15,
            "height_max": 30,
            "size_min": 100,
            "size_max": 500,
            "offset": 10,
            "limit": 25,
        }
    ]


@pytest.mark.unit
def test_search_footsteps_parses_and_dedupes_event_ids_and_participants(
    client, fake_sal
):
    resp = client.get(
        "/api/footsteps/search"
        "?event_ids=evt1, evt2,evt1,,evt3,evt2"
        "&participants=11111, 22222,11111,bad,33333"
    )

    assert resp.status_code == 200
    assert fake_sal.calls == [
        {
            "event_ids": ["evt1", "evt2", "evt3"],
            "participants": [11111, 22222, 33333],
            "date_from": None,
            "date_to": None,
            "width_min": None,
            "width_max": None,
            "height_min": None,
            "height_max": None,
            "size_min": None,
            "size_max": None,
            "offset": 0,
            "limit": 60,
        }
    ]


@pytest.mark.unit
def test_search_footsteps_normalizes_offset_and_limit(client, fake_sal):
    resp = client.get("/api/footsteps/search?offset=-5&limit=999")

    assert resp.status_code == 200
    assert fake_sal.calls == [
        {
            "event_ids": None,
            "participants": None,
            "date_from": None,
            "date_to": None,
            "width_min": None,
            "width_max": None,
            "height_min": None,
            "height_max": None,
            "size_min": None,
            "size_max": None,
            "offset": 0,
            "limit": 200,
        }
    ]


@pytest.mark.unit
def test_search_footsteps_invalid_date_format_returns_400(client, fake_sal):
    resp = client.get("/api/footsteps/search?date_from=2025-99-99")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert "Invalid date format" in data["message"]
    assert fake_sal.calls == []


@pytest.mark.unit
def test_search_footsteps_invalid_date_range_returns_400(client, fake_sal):
    resp = client.get("/api/footsteps/search?date_from=2025-02-01&date_to=2025-01-01")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert data["message"] == "date_from must be <= date_to"
    assert fake_sal.calls == []


@pytest.mark.unit
def test_search_footsteps_invalid_width_range_returns_400(client, fake_sal):
    resp = client.get("/api/footsteps/search?width_min=50&width_max=10")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert data["message"] == "width_min must be <= width_max"
    assert fake_sal.calls == []


@pytest.mark.unit
def test_search_footsteps_invalid_height_range_returns_400(client, fake_sal):
    resp = client.get("/api/footsteps/search?height_min=50&height_max=10")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert data["message"] == "height_min must be <= height_max"
    assert fake_sal.calls == []


@pytest.mark.unit
def test_search_footsteps_invalid_size_range_returns_400(client, fake_sal):
    resp = client.get("/api/footsteps/search?size_min=500&size_max=100")

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert data["message"] == "size_min must be <= size_max"
    assert fake_sal.calls == []


@pytest.mark.unit
def test_search_footsteps_defaults_limit_to_60(client, fake_sal):
    resp = client.get("/api/footsteps/search")

    assert resp.status_code == 200
    assert fake_sal.calls == [
        {
            "event_ids": None,
            "participants": None,
            "date_from": None,
            "date_to": None,
            "width_min": None,
            "width_max": None,
            "height_min": None,
            "height_max": None,
            "size_min": None,
            "size_max": None,
            "offset": 0,
            "limit": 60,
        }
    ]


@pytest.mark.unit
def test_search_footsteps_internal_error_returns_500(app_factory):
    app = app_factory(ErrorSAL())

    with app.test_client() as client_:
        resp = client_.get("/api/footsteps/search?size_min=10&size_max=20")

    assert resp.status_code == 500
    data = resp.get_json()
    assert data["code"] == "internal_error"
    assert data["message"] == "unexpected error"
    assert "boom" in data["details"]


class ReviewCreateDeleteSAL:
    def __init__(self):
        self.calls = []

    def get_footstep_review_context(self, event_id, footstep_id):
        self.calls.append(("get_review", event_id, footstep_id))
        return (
            {
                "item": {"event_id": event_id, "footstep_id": footstep_id},
                "bbox": {"x_min": 1, "x_max": 2, "y_min": 3, "y_max": 4},
                "event_p100": [[1.0]],
                "image_width": 1,
                "image_height": 1,
                "changes": [],
            },
            None,
        )

    def save_footstep_review(self, event_id, footstep_id, **kwargs):
        self.calls.append(("save_review", event_id, footstep_id, kwargs))
        return (
            {
                "item": {"event_id": event_id, "footstep_id": footstep_id},
                "bbox": {
                    "x_min": kwargs["x_min"],
                    "x_max": kwargs["x_max"],
                    "y_min": kwargs["y_min"],
                    "y_max": kwargs["y_max"],
                },
                "event_p100": [[1.0]],
                "image_width": 1,
                "image_height": 1,
                "changes": [],
            },
            None,
        )

    def create_footstep(self, event_id, **kwargs):
        self.calls.append(("create_footstep", event_id, kwargs))
        return (
            {
                "item": {"event_id": event_id, "footstep_id": 99},
                "bbox": {
                    "x_min": kwargs["x_min"],
                    "x_max": kwargs["x_max"],
                    "y_min": kwargs["y_min"],
                    "y_max": kwargs["y_max"],
                },
                "event_p100": [[1.0]],
                "image_width": 1,
                "image_height": 1,
                "changes": [],
            },
            None,
        )

    def delete_footstep(self, event_id, footstep_id):
        self.calls.append(("delete_footstep", event_id, footstep_id))
        return (
            {
                "ok": True,
                "event_id": event_id,
                "footstep_id": footstep_id,
            },
            None,
        )


@pytest.fixture
def review_client(app_factory):
    fake_sal = ReviewCreateDeleteSAL()
    app = app_factory(fake_sal)
    with app.test_client() as c:
        yield c, fake_sal


@pytest.mark.unit
def test_get_footstep_review_ok(review_client):
    client, fake_sal = review_client

    resp = client.get("/api/footsteps/evt-1/7/review")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["item"]["event_id"] == "evt-1"
    assert data["item"]["footstep_id"] == 7
    assert fake_sal.calls == [("get_review", "evt-1", 7)]


@pytest.mark.unit
def test_save_footstep_review_ok(review_client):
    client, fake_sal = review_client

    resp = client.post(
        "/api/footsteps/evt-1/7/review",
        json={
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
            "y_max": 40,
            "label": "left",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["bbox"] == {
        "x_min": 10,
        "x_max": 20,
        "y_min": 30,
        "y_max": 40,
    }
    assert fake_sal.calls == [
        (
            "save_review",
            "evt-1",
            7,
            {
                "x_min": 10,
                "x_max": 20,
                "y_min": 30,
                "y_max": 40,
                "label": "left",
            },
        )
    ]


@pytest.mark.unit
def test_save_footstep_review_bad_payload_returns_400(review_client):
    client, fake_sal = review_client

    resp = client.post(
        "/api/footsteps/evt-1/7/review",
        json={
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert "Missing required field" in data["message"]
    assert fake_sal.calls == []


@pytest.mark.unit
def test_create_footstep_ok(review_client):
    client, fake_sal = review_client

    resp = client.post(
        "/api/footsteps/evt-1/create",
        json={
            "start_frame": 1,
            "end_frame": 2,
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
            "y_max": 40,
            "label": "new step",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["item"]["event_id"] == "evt-1"
    assert data["item"]["footstep_id"] == 99
    assert fake_sal.calls == [
        (
            "create_footstep",
            "evt-1",
            {
                "start_frame": 1,
                "end_frame": 2,
                "x_min": 10,
                "x_max": 20,
                "y_min": 30,
                "y_max": 40,
                "label": "new step",
            },
        )
    ]


@pytest.mark.unit
def test_create_footstep_bad_payload_returns_400(review_client):
    client, fake_sal = review_client

    resp = client.post(
        "/api/footsteps/evt-1/create",
        json={
            "start_frame": 1,
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
            "y_max": 40,
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert "Missing required field" in data["message"]
    assert fake_sal.calls == []


@pytest.mark.unit
def test_delete_footstep_ok(review_client):
    client, fake_sal = review_client

    resp = client.post("/api/footsteps/evt-1/7/delete")

    assert resp.status_code == 200
    assert resp.get_json() == {
        "ok": True,
        "event_id": "evt-1",
        "footstep_id": 7,
    }
    assert fake_sal.calls == [("delete_footstep", "evt-1", 7)]


class ReviewErrorSAL:
    def get_footstep_review_context(self, event_id, footstep_id):
        return None, "missing_event"

    def save_footstep_review(self, event_id, footstep_id, **kwargs):
        return None, "invalid_bbox"

    def create_footstep(self, event_id, **kwargs):
        return None, "invalid_frame"

    def delete_footstep(self, event_id, footstep_id):
        return None, "missing_file"


@pytest.fixture
def review_error_client(app_factory):
    app = app_factory(ReviewErrorSAL())
    with app.test_client() as c:
        yield c


@pytest.mark.unit
def test_get_footstep_review_missing_event_returns_404(review_error_client):
    resp = review_error_client.get("/api/footsteps/evt-1/7/review")

    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"
    assert data["message"] == "event not found"


@pytest.mark.unit
def test_save_footstep_review_invalid_bbox_returns_400(review_error_client):
    resp = review_error_client.post(
        "/api/footsteps/evt-1/7/review",
        json={
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
            "y_max": 40,
            "label": "left",
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert "bbox must stay inside the full event image" in data["message"]


@pytest.mark.unit
def test_create_footstep_invalid_frame_returns_400(review_error_client):
    resp = review_error_client.post(
        "/api/footsteps/evt-1/create",
        json={
            "start_frame": 1,
            "end_frame": 2,
            "x_min": 10,
            "x_max": 20,
            "y_min": 30,
            "y_max": 40,
            "label": "new step",
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "bad_request"
    assert "start_frame and end_frame must be inside the trial" in data["message"]


@pytest.mark.unit
def test_delete_footstep_missing_file_returns_404(review_error_client):
    resp = review_error_client.post("/api/footsteps/evt-1/7/delete")

    assert resp.status_code == 404
    data = resp.get_json()
    assert data["code"] == "not_found"
    assert data["message"] == "footstep not found"
