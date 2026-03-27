from datetime import date, datetime
from typing import Optional, Tuple

from backend.storage_access_layer.helpers.common import CommonHelper

from ..db.db import DB
from ..utils import uri_to_path


class SalEvents:
    def __init__(self, db: DB, common: CommonHelper):
        self.db = db
        self.common = common

    def get_event_summary(self, event_id: str) -> Optional[Tuple[dict, dict]]:
        """
        Return (event_dict, availability_dict) or None if event missing.
        """
        event = self.db.get_swipe_event(event_id)
        if event is None:
            return None

        date_value = event.date
        if isinstance(date_value, (datetime, date)):
            date_value = date_value.isoformat()

        event_dict = {
            "event_id": event.event_id,
            "participant": event.participant,
            "date": date_value,
            "direction": event.direction,
            "event_number": event.event_number,
        }

        availability: dict = {}

        try:
            p100_path = uri_to_path(event.trial_p100_npz_uri)
            availability["p100"] = p100_path.exists()
        except Exception:
            availability["p100"] = False

        try:
            grf_path = uri_to_path(event.trial_grf_npz_uri)
            availability["grf"] = grf_path.exists()
        except Exception:
            availability["grf"] = False

        try:
            trial_path = uri_to_path(event.trial_npz_uri)
            availability["metadata"] = trial_path.with_name("metadata.csv").exists()
            availability["steps"] = trial_path.with_name("steps.npz").exists()
        except Exception:
            availability["metadata"] = False
            availability["steps"] = False

        return event_dict, availability

    def get_p100(self, event_id: str):
        event, err = self.common._require_event(event_id)
        if err or event is None:
            return None

        p100, err = self.common._get_p100(event)
        if err or p100 is None:
            return None

        try:
            return p100.tolist()
        except Exception as e:
            return f"unexpected error: {e}"
        return

    def get_grf(self, event_id: str):
        event, err = self.common._require_event(event_id)
        if err or event is None:
            return None, err

        array, arr_err = self.common._load_npz_from_uri(
            event.trial_grf_npz_uri,
            key="arr_0",
        )
        if arr_err or array is None:
            return None, arr_err

        try:
            return array.tolist(), None
        except Exception:
            return None, "missing_file"
