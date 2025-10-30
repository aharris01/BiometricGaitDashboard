-- Used for fast lookup of a swipe event
CREATE INDEX swipe_event_lookup_idx ON swipe_event (participant, date, direction, event_number)
WHERE state = 'ready';