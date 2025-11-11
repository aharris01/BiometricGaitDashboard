# Select Swipe Event

This feature lets users select a single swipe event for analysis by choosing a participant, date, direction, and event. The Dash frontend populates dropdowns from the backend and, on submit, requests the specific swipe. The backend (Flask) delegates to the SAL and returns the swipe identifier for use across the dashboard.

**What’s Implemented**
- Dropdown-driven selection (participant, date, direction, event) with initial load.
- Backend-integrated flow: Dash → Flask API → SAL → Flask API → Dash.
- On submit, returns `{ "id": event_id }` and stores it for downstream views.
- Basic error messaging surfaced in the UI.
