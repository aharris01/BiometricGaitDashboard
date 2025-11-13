# Storage Access Layer (SAL)

## Overview

The **Storage Access Layer** is responsible for all database interaction
in the Biometric Gait Dashboard backend.\
It provides:

-   a SQLAlchemy ORM model (`SwipeEvent`)
-   an automatically configured database engine and session factory
-   validated access functions used throughout the backend
-   an optional `SAL` class wrapper for structured access

The key design principle is:\
\### **The rest of the application does not manage sessions.**\
All session handling is internal to the storage layer.

This ensures:

-   consistent lifetime & cleanup of DB sessions\
-   compatibility with unit tests (which inject a temporary DB)\
-   isolation from SQLAlchemy engine changes\
-   safety when the backend code runs in multiple environments

------------------------------------------------------------------------

# Module Breakdown

  -----------------------------------------------------------------------
  File                        Purpose
  --------------------------- -------------------------------------------
  **db.py**                   Database engine, session factory, ORM
                              model, low-level query functions.

  **accessfunctions.py**      Public API for storage access. Each
                              function internally manages its session.

  **validators.py**           Ensures inputs/outputs follow the expected
                              invariants.

  **SAL.py**                  Optional object-oriented wrapper around
                              accessfunctions (used by some parts of the
                              backend).
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Database Model --- `SwipeEvent`

The `SwipeEvent` ORM model represents a single gait-trial event stored
in SQLite.

  ------------------------------------------------------------------------------
  Field                  Type              Description
  ---------------------- ----------------- -------------------------------------
  `event_id`             String (PK)       Unique event identifier (composed
                                           participant/date/direction/event#).

  `participant`          Integer           Participant ID.

  `date`                 Date              Date of trial.

  `direction`            String            `"in"` or `"out"`.

  `event_number`         Integer           Trial number for the given
                                           participant/date/direction.

  `state`                String            Trial state (cannot be NULL).

  `trial_npz_uri`        Text              Path to `.npz` file.

  `trial_p100_npz_uri`   Text              Path to P100 file.

  `trial_grf_npz_uri`    Text              Path to GRF file.

  `created_at`           Timestamp         Automatically added when the event is
                                           stored.
  ------------------------------------------------------------------------------

------------------------------------------------------------------------

# Database Engine & Sessions

`db.py` now defines:

### A module-level SQLAlchemy engine

### A `SessionLocal = sessionmaker(bind=engine)` factory

### A `get_session()` context manager

This pattern guarantees:

-   automatic commit/rollback\
-   automatic cleanup\
-   no external session handling

------------------------------------------------------------------------

# Access Functions (Final Behavior)

All functions in `accessfunctions.py`:

-   create and manage their own sessions\
-   return plain Python types\
-   match strict validator requirements

  -------------------------------------------------------------------------------------------------------------
  Function                                      Input          Output              Description
  --------------------------------------------- -------------- ------------------- ----------------------------
  `getParticipants()`                           ---            `list[int]`         All participant IDs.

  `getDates(participant)`                       `int`          `list[date]`        All dates for that
                                                                                   participant.

  `getDirections(participant, date)`            ---            `list[str]`         `"in"` / `"out"`.

  `getEvents(participant, date, direction)`     ---            `list[int]`         Event numbers.

  `getSwipeEventId(...)`                        params         `str | None`        Unique event ID.

  `getBothDirectionEvents(participant, date)`   ---            `list[list[int]]`   `[in_events, out_events]`.
  -------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# SAL Class

The `SAL` class adds:

-   input validation\
-   output validation\
-   encapsulation of the `DB` object

All logic still delegates to accessfunctions but wraps them safely.

------------------------------------------------------------------------

# Example Usage

``` python
import backend.storage_access_layer.accessfunctions as af

participants = af.getParticipants()
dates = af.getDates(participants[0])
dirs = af.getDirections(participants[0], dates[0])
events = af.getEvents(participants[0], dates[0], dirs[0])

swipe_id = af.getSwipeEventId(
    participants[0],
    dates[0],
    events[0],
    dirs[0],
)
```

------------------------------------------------------------------------

# Test Behavior

-   Tests use a temporary SQLite DB defined in `conftest.py`
-   Real DB is not touched\
-   Fake `.npz` files are created for server routes\
-   All functions produce strictly validated output

------------------------------------------------------------------------


