# Storage Access Layer

## Overview

The **Storage Access Layer** is the component responsible for database management and access within the **Biometric Gait Dashboard** backend.  
It defines the ORM schema, establishes the database engine connection, and exposes functions to safely query stored Swipe Event data.

This layer is isolated so the rest of the project layers don't have to worry about changes in data storage format.

---

## Modules

| File | Description |
|------|--------------|
| **`db.py`** | Defines the model (`SwipeEvent`) and utilizes the SQLAlchemy engine. |
| **`accessfunctions.py`** | Provides functions for fetching participants, dates, directions, and events. |

---

## Database Model — `SwipeEvent`

Represents a single gait-trial event stored in the database.

| Column | Type | Description |
|---------|------|-------------|
| `event_id` | `String` (PK) | Unique event identifier, e.g. `"001_2025-01-01_in_1_ready"`. |
| `participant` | `Integer` | Participant |
| `date` | `Date` | The date of the swipe event. |
| `direction` | `String` | Direction (`"in"` or `"out"`) |
| `event_number` | `Integer` | Event number |
| `state` | `String` | Trial state |
| `trial_npz_uri` | `Text` | Path to trial |
| `trial_p100_npz_uri` | `Text` | Path to P100 |
| `trial_grf_npz_uri` | `Text` | Path to GRF |
| `created_at` | `TIMESTAMP` | Automatically filled on record creation using `now()` (Postgres) or `CURRENT_TIMESTAMP` (SQLite). |

---

## Access Functions

These functions (defined in `accessfunctions.py`) provide a consistent way to query the database.

| Function | Parameters | Returns | Description |
|-----------|-------------|----------|--------------|
| `getParticipants(session)` | — | `list[int]` | All participant IDs |
| `getDates(session, participant)` | `participant: int` | `list[date]` | Dates of events |
| `getDirections(session, participant, date)` | `participant: int`, `date: date` | `list[str]` |directions (`"in"` / `"out"`) for that date. |
| `getEvents(session, participant, date)` | `participant: int`, `date: date` | `list[int]` | Event numbers for that participant/date. |
| `getSwipeEventId(session, participant, date, event, direction)` | `participant, date, event, direction` | `str` or `None` | Returns the unique event ID string if it exists. |

---

## Example Usage

```python
from sqlalchemy.orm import Session
from backend.storage_access_layer.db import engine
from backend.storage_access_layer.accessfunctions import (
    getParticipants, getDates, getDirections, getEvents, getSwipeEventId
)

with Session(engine) as session:
    participants = getParticipants(session)
    dates = getDates(session, participants[0])
    directions = getDirections(session, participants[0], dates[0])
    events = getEvents(session, participants[0], dates[0])

    swipe_event_id = getSwipeEventId(
        session,
        participant=participants[0],
        date=dates[0],
        event=events[0],
        direction=directions[0],
    )

    print("Swipe Event ID:", swipe_event_id)
