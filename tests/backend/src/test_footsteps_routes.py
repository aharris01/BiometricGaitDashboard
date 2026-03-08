import pytest


class FakeSAL:
    def __init__(self):
        self.calls = []

    def search_footsteps(
        self,
        event_ids=None,
        size_min=None,
        size_max=None,
        offset=0,
        limit=60,
    ):
        self.calls.append(
            {
                "event_ids": event_ids,
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
        "/api/footsteps/search?size_min=100&size_max=500&offset=10&limit=25"
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
            "size_min": 100,
            "size_max": 500,
            "offset": 10,
            "limit": 25,
        }
    ]


@pytest.mark.unit
def test_search_footsteps_parses_and_dedupes_event_ids(client, fake_sal):
    resp = client.get("/api/footsteps/search?event_ids=evt1, evt2,evt1,,evt3,evt2")

    assert resp.status_code == 200
    assert fake_sal.calls == [
        {
            "event_ids": ["evt1", "evt2", "evt3"],
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
            "size_min": None,
            "size_max": None,
            "offset": 0,
            "limit": 200,
        }
    ]


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
