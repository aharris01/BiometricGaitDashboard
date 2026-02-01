import csv
from pathlib import Path
from sqlalchemy import select
from ..storage_access_layer.db.db import DB
from ..storage_access_layer.db.schema import LocalSwipeEvent
from urllib.parse import urlparse

db = DB()
local_events = db.get_local_event_ids()

output_file = Path("metrics.csv")

with output_file.open("w", newline="") as out_f:
    writer = csv.writer(out_f)
    writer.writerow(["event_id", "avg_bbox_size", "step_count"])

    for local_event in local_events:
        with db._get_session() as session:
            query = select(LocalSwipeEvent.event_id, LocalSwipeEvent.root_path).where(
                LocalSwipeEvent.event_id == local_event
            )
            result = session.execute(query).first()
            if result is not None:
                event_id, root_path = result
            else:
                print("No data found for the given event ID.")

        parsed = urlparse(root_path)
        root_path = Path(parsed.path.lstrip("/"))
        file = Path(root_path) / "metadata.csv"
        try:
            with file.open(newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            print(f"{file}: Error occurred while opening file: {e}")
            continue

        box_sizes = []
        box_sizes_sum = 0

        for row in rows:
            try:
                x_min = int(float(row["XMin"]))
                x_max = int(float(row["XMax"]))
                y_min = int(float(row["YMin"]))
                y_max = int(float(row["YMax"]))
            except Exception:
                print(
                    "SAL.get_swipe_event_summary_plot_data(): Missing data, skipping this footstep..."
                )
                continue

            bounding_box_size = abs(x_max - x_min) * abs(y_max - y_min)
            box_sizes.append(bounding_box_size)
            box_sizes_sum += bounding_box_size

        if not box_sizes:
            continue

        avg_box_size = box_sizes_sum / len(box_sizes)
        footstep_count = len(box_sizes)
        writer.writerow([event_id, avg_box_size, footstep_count])
