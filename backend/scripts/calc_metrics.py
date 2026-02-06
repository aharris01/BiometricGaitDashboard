import csv
from pathlib import Path
from sqlalchemy import select
from ..storage_access_layer.db.db import DB
from ..storage_access_layer.db.schema import LocalSwipeEvent
from urllib.parse import urlparse

db = DB()
local_events = db.get_local_event_ids()


def calc_first_metrics():
    output_file = Path("metrics.csv")
    with output_file.open("w", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["event_id", "avg_bbox_size", "step_count"])

        for local_event in local_events:
            with db._get_session() as session:
                query = select(
                    LocalSwipeEvent.event_id, LocalSwipeEvent.root_path
                ).where(LocalSwipeEvent.event_id == local_event)
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


def calc_swipe_duration():
    output_file = Path("metrics_duration.csv")
    with output_file.open("w", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["event_id", "duration"])

        for local_event in local_events:
            with db._get_session() as session:
                query = select(
                    LocalSwipeEvent.event_id, LocalSwipeEvent.root_path
                ).where(LocalSwipeEvent.event_id == local_event)
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

            if not rows:
                print(f"No rows found for {local_event}")
                continue

            try:
                start_frame = int(float(rows[0]["StartFrame"]))
                end_frame = int(float(rows[-1]["EndFrame"]))
            except (KeyError, ValueError):
                continue

            duration = end_frame - start_frame
            writer.writerow([event_id, duration])


def calc_one_duration(event_id):
    with db._get_session() as session:
        query = select(LocalSwipeEvent.event_id, LocalSwipeEvent.root_path).where(
            LocalSwipeEvent.event_id == event_id
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
        exit(1)

    if not rows:
        print(f"No rows found for {event_id}")
        exit(1)

    try:
        start_frame = int(float(rows[0]["StartFrame"]))
        end_frame = int(float(rows[-1]["EndFrame"]))
    except (KeyError, ValueError):
        print(f"Error occurred on event: {event_id}")
        exit(1)

    duration = end_frame - start_frame
    print(f"{event_id} duration: {duration}")


if __name__ == "__main__":
    print("Calculating durations...")
    calc_swipe_duration()
    print("Done calculating")
