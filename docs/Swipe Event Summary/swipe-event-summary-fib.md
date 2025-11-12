# Feature Interface - Swipe Event Summary

**Version:** 1.0
**Owner:** Aidan Harrison
**Date:** 2025-11-11

---

## 1. Overview

**Goal:**
The user should be able to see a summary of their currently selected swipe event. The summary view should include the P100 image, GRF graph, and the P100 images of the footsteps if they are available.

**User Action:**
After selecting a swipe event, a summary view should appear

**System Output:**
Summary view as previously described

---

## 2. Boundaries

### 2.1 Backend Endpoints: Sarun

**Purpose**

Send swipe event data to the frontend. Requests for the P100, GRF, and footstep data, if available, for the selected swipe event

| Action | Method / Path | Request | Response | Notes |
|---------|----------------|----------|-----------|--------|
| Get summary metadata | `GET /api/events/{event_id}/summary` | `event_id` | `{ "event": {"id": event_id, "participant": participant, "date": yyyy-mm-dd, "direction": in/out, "event_number": ###}, "availability": {"p100": true/false, "grf": true/false, "footsteps": true/false}}` | This should be called before any other call. Only calls for available assets should be made. Unavailable assets should be displayed within their respective containers |
| Get P100 | `GET /api/events/{event_id}/p100` | `event_id` | `{ "p100" : [JSON 2d array data]}` | event_id should be stored somewhere on the frontend and should be used for this call |
| Get GRF | `GET /api/events/{event_id}/grf` | `event_id` | `{ "grf" : [JSON 1d array data] }` | See above |
| Get footsteps data | `GET /api/events/{event_id}/footsteps/data`| `event_id` | `[{"footstep_id": id, "p100": [2d array data], "grf": [1d array data]}]` | |

**Error Propogation**

Backend errors should be handled gracefully and a descriptive error should be displayed to the user

### 2.2 SAL functions: Jonathan

**Purpose**
The backend makes request for swipe event data, without being responsible for data manipulation, conversion, etc. The backend is responsible for converting data into a format that can be sent as a response to the frontend.

| Function | Input | Output | Notes |
| --- | --- | --- | --- |
| `getEventSummary` | `event_id` | {event:{id: string, participant: int, date: datetime, direction: [in/out], event_number: int}, availability: {p100: boolean, grf: boolean, footsteps: boolean}} | The metadata db should be queried for event_id and use the identifier columns for metadata. The metadata db should be updated to include a new column in the swipe_event table or create a swipe_asset table |
| `getP100` | `event_id` | 2d numpy array with p100 data loaded from `trial.p100.npz` | The array should be rotated 90 degrees so it can be displayed horizontally on the frontend |
| `getGRF` | `event_id` | 1d numpy array with GRF data loaded from `trial.GRF.npz` | None |
| `getFootsteps` | `event_id` | [{footstep_id: int, p100: [2d numpy array], grf: [1d numpy array]}] | If a metadata####.csv file exists, open `trial.npz` and extract the footstep data into numpy arrays |