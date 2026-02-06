import datetime

import numpy as np
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from backend.storage_access_layer.db.schema import (
    LocalBase,
    ManifestBase,
    ManifestSwipeEvent,
    ManifestMetrics,
    LocalSwipeEvent,
)
from backend.storage_access_layer.db.db import DB


@pytest.fixture(scope="module")
def db_paths(tmp_path_factory):
    root = tmp_path_factory.mktemp("dbs")
    return {
        "local": root / "local.db",
        "manifest": root / "manifest.db",
        "dataroot": root / "data",
    }


@pytest.fixture(scope="module")
def engine(db_paths):
    local_uri = f"sqlite:///{db_paths['local'].as_posix()}"
    manifest_path = db_paths["manifest"].as_posix()

    engine = create_engine(local_uri, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _attach_manifest(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("ATTACH DATABASE ? AS manifest", (manifest_path,))
        cur.close()

    # ensure manifest is attached for metadata creation
    with engine.begin() as conn:
        ManifestBase.metadata.create_all(conn)
        LocalBase.metadata.create_all(conn)

    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def seeded_db(engine, db_paths):
    # build tiny data root with files for path checks
    event_root = db_paths["dataroot"] / "11111" / "2025-01-01" / "in" / "1"
    event_root.mkdir(parents=True)
    for name, arr in {
        "trial.npz": np.array([1, 2, 3]),
        "trial.p100.npz": np.array([4]),
        "trial.grf.npz": np.array([5]),
    }.items():
        np.savez(event_root / name, arr=arr)

    rows_manifest = [
        ManifestSwipeEvent(
            event_id="EV_PRESENT",
            participant=11111,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            local=1,
        ),
        ManifestSwipeEvent(
            event_id="EV_ABSENT",
            participant=22222,
            date=datetime.date(2025, 1, 2),
            direction="out",
            event_number=2,
            local=0,
        ),
    ]
    rows_local = [
        LocalSwipeEvent(
            event_id="EV_PRESENT",
            root_path=event_root.as_posix(),
            present=True,
            last_seen=datetime.datetime.now(),
        ),
    ]
    rows_metrics = [
        ManifestMetrics(event_id="EV_PRESENT", avg_bbox_size=3.14, step_count=7),
    ]

    with Session(engine) as s:
        s.add_all(rows_manifest)
        s.add_all(rows_local)
        s.add_all(rows_metrics)
        s.commit()

    db = DB(engine)
    yield db
    db.close()


@pytest.fixture
def empty_db(tmp_path):
    """Fresh isolated DB (local + manifest) for tests that need empties."""
    root = tmp_path / "empty"
    root.mkdir()
    local = root / "local.db"
    manifest = root / "manifest.db"
    manifest_path = manifest.as_posix()

    engine = create_engine(
        f"sqlite:///{local.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _attach_manifest(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("ATTACH DATABASE ? AS manifest", (manifest_path,))
        cur.close()

    with engine.begin() as conn:
        ManifestBase.metadata.create_all(conn)
        LocalBase.metadata.create_all(conn)

    db = DB(engine)
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
