SET search_path TO app,
    public;
CREATE TABLE swipe_event (
    event_id TEXT PRIMARY KEY,
    -- Human readable format ie. ('001_yyyy-mm-dd_(in|out)_event#_state')
    participant INT NOT NULL,
    date DATE NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    event_number INT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('building', 'ready', 'failed')),
    -- 'ready' can be read, 'building' being used by another process, 'failed' corrupted or unusable
    trial_npz_uri TEXT NOT NULL,
    -- URI for the file destination
    trial_p100_npz_uri TEXT NOT NULL,
    -- URI for the p100 destination
    trial_GRF_npz_uri TEXT NOT NULL,
    -- URI for the GRF destination
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (participant, date, direction, event_number) -- Can be used for ~O(1) lookup with an index
);