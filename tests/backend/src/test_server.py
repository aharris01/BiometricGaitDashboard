# tests/backend/src/test_server.py
from __future__ import annotations
import importlib
from dataclasses import dataclass
from pathlib import Path
from datetime import date

import numpy as np
import pytest


@pytest.fixture
def server_mod(monkeypatch):
    # Disable auth for tests
    monkeypatch.setenv("ENABLE_AUTH", "false")
    monkeypatch.setenv("ALLOWED_ORIGIN", "http://127.0.0.1:8050")
    from backend.src import server as mod
    importlib.reload(mod)
    return mod


# def _make_npzs(tmp: Path):
#     p100 = tmp / "trial.p100.npz"
#     grf  = tmp / "trial.grf.npz"
#     trial= tmp / "trial.npz"
#     a = np.arange(12).reshape(3, 4)            # for rotation check
#     g = np.linspace(0, 1, 10)
#     np.savez(p100, p100=a)
#     np.savez(grf,  grf=g)
#     np.savez(trial, footstep_0_p100=np.ones((2,2)), footstep_0_grf=np.arange(5))
#     return p100, grf, trial, a, g


# @dataclass
# class FakeRow:
#     event_id: str
#     participant: int
#     date: date
#     direction: str
#     event_number: int
#     state: str
#     trial_npz_uri: str
#     trial_p100_npz_uri: str
#     trial_grf_npz_uri: str


# @pytest.fixture
# def client_with_fake_event(server_mod, tmp_path, monkeypatch):
#     p100, grf, trial, a, g = _make_npzs(tmp_path)
#     ev_id = "001_2025-01-01_in_1_ready"
#     row = FakeRow(
#         event_id=ev_id,
#         participant=1,
#         date=date(2025,1,1),
#         direction="in",
#         event_number=1,
#         state="ready",
#         trial_npz_uri=trial.resolve().as_uri(),
#         trial_p100_npz_uri=p100.resolve().as_uri(),
#         trial_grf_npz_uri=grf.resolve().as_uri(),
#     )

#     # Mock the DB fetch so we don't touch the real DB
#     monkeypatch.setattr(server_mod, "_load_swipe", lambda eid: row if eid == ev_id else None, raising=True)

#     server_mod.server.config["TESTING"] = True
#     with server_mod.server.test_client() as c:
#         yield c, ev_id, a, g


def test_health(server_mod):
    server_mod.server.config["TESTING"] = True
    with server_mod.server.test_client() as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.get_json() == {"status": "ok"}


# def test_summary(client_with_fake_event):
#     c, ev_id, *_ = client_with_fake_event
#     r = c.get(f"/api/events/{ev_id}/summary")
#     assert r.status_code == 200
#     js = r.get_json()
#     assert js["event"]["id"] == ev_id
#     assert js["availability"] == {"p100": True, "grf": True, "footsteps": True}


# def test_p100_rotated(client_with_fake_event):
#     c, ev_id, a, _ = client_with_fake_event
#     r = c.get(f"/api/events/{ev_id}/p100")
#     assert r.status_code == 200
#     arr = np.array(r.get_json()["p100"])
#     np.testing.assert_array_equal(arr, np.rot90(a, 1))
#     assert arr.shape == (4, 3)


# def test_grf(client_with_fake_event):
#     c, ev_id, _, g = client_with_fake_event
#     r = c.get(f"/api/events/{ev_id}/grf")
#     assert r.status_code == 200
#     arr = np.array(r.get_json()["grf"])
#     assert arr.ndim == 1 and arr.size == g.size
#     np.testing.assert_allclose(arr, g)


# def test_footsteps(client_with_fake_event):
#     c, ev_id, *_ = client_with_fake_event
#     r = c.get(f"/api/events/{ev_id}/footsteps/data")
#     assert r.status_code == 200
#     steps = r.get_json()
#     assert isinstance(steps, list) and len(steps) == 1
#     assert steps[0]["footstep_id"] == 0
#     a = np.array(steps[0]["p100"])
#     assert a.shape == (2, 2)


# def test_missing_event(server_mod, monkeypatch):
#     # Pretend DB lookup returns nothing; avoids hitting real DB/tables
#     monkeypatch.setattr(server_mod, "_load_swipe", lambda eid: None, raising=True)

#     server_mod.server.config["TESTING"] = True
#     with server_mod.server.test_client() as c:
#         r = c.get("/api/events/NOPE/summary")
#         assert r.status_code == 404
#         assert r.get_json()["error"] == "event not found"

