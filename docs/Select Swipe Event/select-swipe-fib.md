# Feature Interface — Select Swipe Event

**Version:** 1.0  
**Date:** 2025-11-18  
**Owner:** Aidan Harrison

---

## 1. Overview

**Goal:**  
The user selects a swipe event for exploration. Request runs from frontend, backend, and SAL, and returns the swipe event metadata.

**User Action:**  
User selects participant, date, direction, and event.

**System Output:**  
Returns `event_id`.

---

## 2. Boundaries

### 2.1 Frontend ↔ Backend

**Purpose:**  
Dynamically populate dropdown menus with available swipe event data and make requests for a swipe event.

| Action | Method / Path | Request | Response | Notes |
|---------|----------------|----------|-----------|--------|
| Get participants | `GET /api/participants` | None | `{ "items": [participant] }` | N/A |
| Get dates | `GET /api/participants/{participant}/dates` | `participant` | `{ "items": [date] }` | N/A |
| Get directions | `GET /api/participants/{participant}/dates/{date}/directions` | `participant`, `date` | `{ "items": ["in", "out"]}` | The response should be used in the subsequent get events call |
| Get events | `GET /api/participants/{participant}/dates/{date}/directions/{direction}/events` | `participant`, `date` | `{ "items": [1, 2, 3, etc.]}` | Should be called after receiving a response from get directions |
| Get events by direction | `GET /api/participants/{participant}/dates/{date}/eventsByDirection` | `{ "in": [1, 2, 3, …], "out": [4, 5, 6, …] }` | This is in place to populate the last two dropdowns without the frontend handling the logic to build the dictionary |
| Get swipe | `GET /api/swipe/{participant}/{date}/{direction}/{event}` | `participant`, `date`, `direction`, `event` | `{ "id": event_id }` | This should be cached somewhere in the frontend to be used in subsequent api calls. Look at dcc.Store |

#### Error Model and Status Codes

All errors should have the same body format:

```json
{
  "code": "invalid_argument",
  "message": "direction must be 'in' or 'out'",
  "details": null
}
```

| HTTP Code | Meaning | Client Action |
|------------|----------|----------------|
| **200** | Success | - |
| **400** | `invalid_argument` — Bad query parameter | Fix request |
| **404** | `not_found` — Requested data doesn’t exist | Refresh options |
| **500** | `internal_error` — Unexpected error | Retry later |
| **503** | `unavailable` — Backend down | Retry later |

---

### 2.2 Backend ↔ SAL

**Purpose:**  
The Flask backend will call the SAL to get participants, dates, directions, events, and swipe metadata when requested by the frontend.

| Function | Input | Output | Notes |
|-----------|--------|---------|--------|
| `getParticipants` | None | `[participant]` | None |
| `getDates` | `participant` | `[date]` | None |
| `getDirections` | `participant`, `date` | `[in, out]` | None |
| `getEvents` | `participant`, `date`, `direction` | `{ "items": [1, 2, 3, …] }` | None |
| `getEventsByDirection` | `participant`, `date` | `{ "in": [1, 2, 3, …], "out": [4, 5, 6, …] }` | This is an extra function that can be used if desired. Backend can use it in Get events by direction call |
| `getSwipeEventId` | `participant`, `date`, `direction`, `event` | `event_id` | None |