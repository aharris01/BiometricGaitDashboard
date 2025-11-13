# tests/backend/conftest.py
#The purpose of this fixture in conftest is to create a simulated environment in which SQLite scripts can be tested against 
import os
import datetime
import pytest
import numpy as np

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# DB imports
from backend.storage_access_layer.db import Base
from backend.storage_access_layer.db import SwipeEvent
from backend.storage_access_layer import db as db_module


@pytest.fixture(scope="module", autouse=True)
def setup_test_db(tmp_path_factory):

    # create temp npz files
    tmp = tmp_path_factory.mktemp("npzdata")

    p100_file = tmp / "trial.p100.npz"
    grf_file = tmp / "trial.grf.npz"
    trial_file = tmp / "trial.npz"

    a = np.arange(12).reshape(3, 4)
    g = np.linspace(0, 1, 10)

    np.savez(p100_file, p100=a)
    np.savez(grf_file, grf=g)
    np.savez(trial_file,
             footstep_0_p100=np.ones((2, 2)),
             footstep_0_grf=np.arange(5))

    # use filesystem paths, uri's break for some reason
    p100_path = str(p100_file.resolve())
    grf_path = str(grf_file.resolve())
    trial_path = str(trial_file.resolve())

    # setup SQLite test DB
    os.environ["DATABASE_URL"] = "sqlite:///test_temp.db"
    test_engine = create_engine("sqlite:///test_temp.db")

    db_module.engine.dispose()
    db_module.engine = test_engine
    db_module.SessionLocal.configure(bind=test_engine)

    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)

    # insert rows
    rows = [
        SwipeEvent(
            event_id="test_11111_2025-01-01_in_1_complete",
            participant=11111,
            date=datetime.date(2025, 1, 1),
            direction="in",
            event_number=1,
            state="complete",
            trial_npz_uri=trial_path,
            trial_p100_npz_uri=p100_path,
            trial_grf_npz_uri=grf_path,
        ),
        SwipeEvent(
            event_id="test_22222_2025-01-02_out_2_complete",
            participant=22222,
            date=datetime.date(2025, 1, 2),
            direction="out",
            event_number=2,
            state="complete",
            trial_npz_uri=trial_path,
            trial_p100_npz_uri=p100_path,
            trial_grf_npz_uri=grf_path,
        ),
        SwipeEvent(
            event_id="test_33333_2025-01-03_in_3_complete",
            participant=33333,
            date=datetime.date(2025, 1, 3),
            direction="in",
            event_number=3,
            state="complete",
            trial_npz_uri=trial_path,
            trial_p100_npz_uri=p100_path,
            trial_grf_npz_uri=grf_path,
        ),
    ]

    with Session(test_engine) as s:
        s.add_all(rows)
        s.commit()

    yield

    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
    if os.path.exists("test_temp.db"):
        os.remove("test_temp.db")





