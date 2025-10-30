import psycopg2
import os
import datetime
from dotenv import load_dotenv


load_dotenv()

dsn = os.environ.get("DATABASE_URL")

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO swipe_event(event_id, participant, date, direction, event_number, state, trial_npz_uri, trial_p100_npz_uri, trial_GRF_npz_uri) 
            VALUES (%(event_id)s, %(part)s, %(date)s, %(direction)s, %(event)s, %(state)s, %(reg_uri)s, %(p100_uri)s, %(GRF_uri)s)""",
            {
                "event_id": "example_event_id2",
                "part": 1,
                "date": datetime.date(2023, 11, 18),
                "direction": "in",
                "event": 3,
                "state": "ready",
                "reg_uri": "uri",
                "p100_uri": "uri",
                "GRF_uri": "uri",
            },
        )
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM swipe_event")
        rows = cur.fetchall()
        print(type(rows[0]))
