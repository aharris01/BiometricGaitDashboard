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
db.py | Defines the model (SwipeEvent) and utilizes the SQLAlchemy engine, now including a session factory and context-managed helper for automatic session handling.
accessfunctions.py | Provides functions for fetching participants, dates, directions, and events. Each function now manages its own session internally.

---

## Database Model — SwipeEvent

Represents a single gait-trial event stored in the database.

Column | Type | Description
---------|------|-------------
event_id | String (PK) | Unique event identifier, e.g. "001_2025-01-01_in_1_ready".
participant | Integer | Participant ID.
date | Date | The date of the swipe event.
direction | String | Direction ("in" or "out").
event_number | Integer | Event number.
state | String | Trial state.
trial_npz_uri | Text | Path to trial file.
trial_p100_npz_uri | Text | Path to P100 file.
trial_grf_npz_uri | Text | Path to GRF file.
created_at | TIMESTAMP | Automatically filled on record creation using now() (Postgres) or CURRENT_TIMESTAMP (SQLite).

---

## Access Functions

These functions (defined in accessfunctions.py) provide a consistent and session-independent way to query the database.  
Each function internally opens and closes its own session, so no manual session handling is needed by the caller.

Function | Parameters | Returns | Description
-----------|-------------|----------|--------------
getParticipants() | — | list[int] | All participant IDs.
getDates(participant) | participant: int | list[date] | Dates of events.
getDirections(participant, date) | participant: int, date: date | list[str] | Directions ("in" / "out") for that date.
getEvents(participant, date, direction) | participant: int, date: date, direction: str | list[int] | Event numbers for that participant/date/direction.
getSwipeEventId(participant, date, event, direction) | participant: int, date: date, event: int, direction: str | str or None | Returns the unique event ID string if it exists.
getBothDirectionEvents(participant, date) | participant: int, date: date | list[list[int]] | Returns both "in" and "out" direction event lists for the given participant and date. If only one direction exists, returns just that one list.

---

## Example Usage

import backend.storage_access_layer.accessfunctions as db

participants = db.getParticipants()
dates = db.getDates(participants[0])
directions = db.getDirections(participants[0], dates[0])
events = db.getEvents(participants[0], dates[0], directions[0])
both_events = db.getBothDirectionEvents(participants[0], dates[0])

swipe_event_id = db.getSwipeEventId(
    participants[0],
    dates[0],
    events[0],
    directions[0],
)

print("Swipe Event ID:", swipe_event_id)
print("Both Direction Events:", both_events)

---
