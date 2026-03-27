from dataclasses import dataclass
import datetime


# A dataclass the represents the previous SwipeEvent ORM object
@dataclass(frozen=True)
class SwipeEvent:
    event_id: str
    participant: int
    date: datetime.date
    direction: str
    event_number: int

    trial_npz_uri: str
    trial_p100_npz_uri: str
    trial_grf_npz_uri: str
    trial_folder: str
