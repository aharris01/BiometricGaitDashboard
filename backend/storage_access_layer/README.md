# Storage Access Layer

## Overview

The Storage Access Layer is the component responsible for database management and access within the Biometric Gait Dashboard backend.  
It defines the ORM schema, establishes the database engine connection, and exposes functions to safely query stored Swipe Event data.

This layer now automatically manages its own database sessions internally.  
Consumers (such as Flask endpoints or backend services) can import the module directly and call its functions without manually creating or passing a session object.

This design keeps the storage layer isolated so the rest of the project layers don't have to worry about changes in data storage or session management.

---

## Modules

File | Description
------|--------------
db.py | Defines the SwipeEvent ORM model, SQLAlchemy engine, session factory, and internal session helpers.
accessfunctions.py | Provides user-facing query functions that internally manage their own database session.
SAL.py | Provides the SAL class wrapper around DB, with validation automatically enforced.
validators.py | Defines validation rules for all access functions, ensuring input and output types remain correct.

---

## Database Model — SwipeEvent

Represents a single gait‑trial event stored in the database.

Column | Type | Description
---------|------|-------------
event_id | String (PK) | Unique event identifier.
participant | Integer | Participant ID.
date | Date | The date of the swipe event.
direction | String | Direction ("in" or "out").
event_number | Integer | Event number.
state | String | State ("ready", "complete", etc.)
trial_npz_uri | Text | Path to trial file.
trial_p100_npz_uri | Text | Path to P100 file.
trial_grf_npz_uri | Text | Path to GRF file.
created_at | TIMESTAMP | Automatically set to CURRENT_TIMESTAMP.

---

## Access Functions (accessfunctions.py)

Each function internally manages its own session using `with get_session()`:

Function | Parameters | Returns | Description
-----------|-------------|----------|--------------
getParticipants() | — | list[int] | Returns all participant IDs.
getDates(participant) | participant: int | list[date] | Returns all dates for the given participant.
getDirections(participant, date) | participant: int, date: date | list[str] | Returns directions for that participant/date.
getEvents(participant, date, direction) | (int, date, str) | list[int] | Returns event numbers for a given swipe context.
getSwipeEventId(participant, date, event, direction) | (...) | str or None | Returns the matching event ID, or None.
getBothDirectionEvents(participant, date) | (int, date) | list[list[int]] | Returns two lists: “in” events and “out” events.

---

## SAL Wrapper (SAL.py)

SAL wraps the DB class and accessfunctions in a validation layer:

```python
class SAL:
    def getParticipants(): validates output
    def getDates(): validates input + output
    def getDirections(): validates input + output
    def getEvents(): validates input + output
    def getSwipeEventId(): validates input + output
    def getBothDirectionEvents(): validates input + output
```

It ensures the DB layer is never allowed to return malformed data.

---

## Validators (validators.py)

The validator module ensures:

### Input Validation
- participant must be `int`
- date must be `datetime.date`
- direction must be `"in"` or `"out"`
- event must be `int`

### Output Validation
Function | Output Must Be | Validation Notes
----------|-------------------|----------------
getParticipants_check | list[int] | No duplicates allowed.
getDates_check | list[date] | All items must be `datetime.date`.
getDirections_check | list[str] | Must only contain "in" / "out".
getEvents_check | list[int] | Must only contain integers.
getSwipeEventId_check | str \| None | If returned, must be a string.
getBothDirectionEvents_check | list[list[int]] | Must be a list of event-number lists.

If validation fails, `ValueError` is raised — this is expected, and is covered by test_sal.py and test_validators.py.

---

## Example Usage

```python
import backend.storage_access_layer.accessfunctions as db

participants = db.getParticipants()
dates = db.getDates(participants[0])
directions = db.getDirections(participants[0], dates[0])
events = db.getEvents(participants[0], dates[0], directions[0])
both = db.getBothDirectionEvents(participants[0], dates[0])

swipe_event_id = db.getSwipeEventId(
    participants[0],
    dates[0],
    events[0],
    directions[0],
)
```

---

## Testing Notes

- The Storage Access Layer uses **real SQLite tables** during tests.
- `tests/backend/conftest.py` overrides the engine so **our database is not touched**.
- The server tests mock `_load_swipe()` to avoid db usage entirely.
- All validation tests ensure incorrect types raise `ValueError` to avoid null elements.

---

## Summary

The Storage Access Layer:
- Defines the SwipeEvent ORM model
- Provides safe, validated access to all gait‑trial event data
- Manages all SQLAlchemy sessions internally
- Ensures the rest of the project never has to deal with DB operations directly
- Is fully covered by unit tests (≥80% coverage target)