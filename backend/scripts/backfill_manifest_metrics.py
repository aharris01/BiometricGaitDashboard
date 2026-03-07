# backend/scripts/backfill_manifest_metrics.py

import argparse
import csv
import math
import os
import sqlite3
import statistics
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv

from backend.scripts.ingest import iter_swipes


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATAROOT = Path(os.environ.get("DATAROOT", ".")).resolve()
MANIFEST_PATH = ROOT / "manifest.db"


def uri_to_path(uri: str | Path) -> Path:
    """
    Convert either:
    - a normal filesystem path
    - or a file:// URI

    into a usable Path object.

    This is required because iter_swipes() currently returns:
        root_path = event_dir.resolve().as_uri()
    """
    s = str(uri)

    if "://" in s and not s.startswith("file://"):
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    if not s.startswith("file://"):
        return Path(s)

    parsed = urlparse(s)
    path = unquote(parsed.path)

    # Windows: "/E:/folder/..." -> "E:/folder/..."
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return Path(path)


def parse_float(value: Any) -> float | None:
    if value is None:
        return None

    s = str(value).strip()
    if s == "":
        return None

    try:
        parsed = float(s)
    except ValueError:
        return None

    if math.isnan(parsed) or math.isinf(parsed):
        return None

    return parsed


def parse_int(value: Any) -> int | None:
    parsed = parse_float(value)
    if parsed is None:
        return None
    return int(parsed)


def read_metadata_rows(metadata_path: Path) -> list[dict[str, str]]:
    with metadata_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_metadata_file(event_dir: Path) -> Path | None:
    """
    Preferred order:
    1. metadata.csv
    2. highest-numbered metadata.<n>.csv
    3. any metadata.*.csv if numbering is weird
    """
    canonical = event_dir / "metadata.csv"
    if canonical.exists():
        return canonical

    candidates = sorted(event_dir.glob("metadata.*.csv"))
    if not candidates:
        return None

    numeric_candidates: list[tuple[int, Path]] = []
    fallback_candidates: list[Path] = []

    for path in candidates:
        fallback_candidates.append(path)

        parts = path.name.split(".")
        # Expecting metadata.<number>.csv
        if len(parts) == 3 and parts[0] == "metadata" and parts[2] == "csv":
            try:
                numeric_candidates.append((int(parts[1]), path))
            except ValueError:
                pass

    if numeric_candidates:
        numeric_candidates.sort(key=lambda item: item[0])
        return numeric_candidates[-1][1]

    return fallback_candidates[-1]


def is_path_step(row: dict[str, str]) -> bool:
    """
    A path step must:
    - be marked valid
    - have a non-negative path_order

    Based on your sample metadata:
    - path_order >= 0 means on-path
    - path_order == -1 appears to mean off-path
    """
    valid = parse_int(row.get("valid"))
    path_order = parse_int(row.get("path_order"))
    return valid == 1 and path_order is not None and path_order >= 0


def compute_event_metrics(rows: list[dict[str, str]]) -> dict[str, float | int | None]:
    if not rows:
        return {
            "total_trial_area": None,
            "mean_step_distance": None,
            "footstep_count_on_path": 0,
            "active_trial_duration_all": None,
            "active_trial_duration_path": None,
            "std_dev_bounding_box_area": None,
            "max_footstep_duration_frames": None,
        }

    total_trial_area: float | None = None
    bbox_areas: list[float] = []
    durations_all: list[int] = []
    start_frames_all: list[int] = []
    end_frames_all: list[int] = []

    path_steps: list[dict[str, Any]] = []

    for row in rows:
        # ---------------------------------------------------------
        # total_trial_area
        # ---------------------------------------------------------
        if total_trial_area is None:
            trial_area = parse_float(row.get("Trial_Area"))
            if trial_area is not None:
                total_trial_area = trial_area

        # ---------------------------------------------------------
        # bounding box area
        # ---------------------------------------------------------
        x_min = parse_int(row.get("XMin"))
        x_max = parse_int(row.get("XMax"))
        y_min = parse_int(row.get("YMin"))
        y_max = parse_int(row.get("YMax"))

        if (
            x_min is not None
            and x_max is not None
            and y_min is not None
            and y_max is not None
        ):
            area = float((x_max - x_min) * (y_max - y_min))
            bbox_areas.append(area)

        # ---------------------------------------------------------
        # step duration and overall active span
        # ---------------------------------------------------------
        start_frame = parse_int(row.get("StartFrame"))
        end_frame = parse_int(row.get("EndFrame"))

        if (
            start_frame is not None
            and end_frame is not None
            and end_frame >= start_frame
        ):
            duration = end_frame - start_frame
            durations_all.append(duration)
            start_frames_all.append(start_frame)
            end_frames_all.append(end_frame)

        # ---------------------------------------------------------
        # path step collection
        # ---------------------------------------------------------
        if is_path_step(row):
            path_order = parse_int(row.get("path_order"))
            x_coord = parse_float(row.get("x"))
            y_coord = parse_float(row.get("y"))
            footstep_id = parse_int(row.get("FootstepID"))

            path_steps.append(
                {
                    "path_order": path_order,
                    "x_coord": x_coord,
                    "y_coord": y_coord,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "footstep_id": footstep_id,
                }
            )

    # -------------------------------------------------------------
    # std_dev_bounding_box_area
    # -------------------------------------------------------------
    if bbox_areas:
        std_dev_bounding_box_area = float(statistics.pstdev(bbox_areas))
    else:
        std_dev_bounding_box_area = None

    # -------------------------------------------------------------
    # max_footstep_duration_frames
    # -------------------------------------------------------------
    if durations_all:
        max_footstep_duration_frames = max(durations_all)
    else:
        max_footstep_duration_frames = None

    # -------------------------------------------------------------
    # active_trial_duration_all
    # -------------------------------------------------------------
    if start_frames_all and end_frames_all:
        active_trial_duration_all = max(end_frames_all) - min(start_frames_all)
    else:
        active_trial_duration_all = None

    # -------------------------------------------------------------
    # path-based metrics
    # -------------------------------------------------------------
    footstep_count_on_path = len(path_steps)

    path_steps_sorted = sorted(
        path_steps,
        key=lambda step: (
            step["path_order"] if step["path_order"] is not None else 10**9,
            step["start_frame"] if step["start_frame"] is not None else 10**9,
            step["footstep_id"] if step["footstep_id"] is not None else 10**9,
        ),
    )

    path_start_frames = [
        step["start_frame"]
        for step in path_steps_sorted
        if step["start_frame"] is not None
    ]
    path_end_frames = [
        step["end_frame"] for step in path_steps_sorted if step["end_frame"] is not None
    ]

    if path_start_frames and path_end_frames:
        active_trial_duration_path = max(path_end_frames) - min(path_start_frames)
    else:
        active_trial_duration_path = None

    # -------------------------------------------------------------
    # mean_step_distance
    # -------------------------------------------------------------
    ordered_points = [
        (step["x_coord"], step["y_coord"])
        for step in path_steps_sorted
        if step["x_coord"] is not None and step["y_coord"] is not None
    ]

    distances: list[float] = []
    for i in range(1, len(ordered_points)):
        x1, y1 = ordered_points[i - 1]
        x2, y2 = ordered_points[i]
        distances.append(math.hypot(x2 - x1, y2 - y1))

    if distances:
        mean_step_distance = float(sum(distances) / len(distances))
    else:
        mean_step_distance = 0.0

    return {
        "total_trial_area": total_trial_area,
        "mean_step_distance": mean_step_distance,
        "footstep_count_on_path": footstep_count_on_path,
        "active_trial_duration_all": active_trial_duration_all,
        "active_trial_duration_path": active_trial_duration_path,
        "std_dev_bounding_box_area": std_dev_bounding_box_area,
        "max_footstep_duration_frames": max_footstep_duration_frames,
    }


def update_manifest_metrics(
    conn: sqlite3.Connection,
    event_id: str,
    metrics: dict[str, float | int | None],
) -> None:
    conn.execute(
        """
        UPDATE global_metrics
        SET
            total_trial_area = ?,
            mean_step_distance = ?,
            footstep_count_on_path = ?,
            active_trial_duration_all = ?,
            active_trial_duration_path = ?,
            std_dev_bounding_box_area = ?,
            max_footstep_duration_frames = ?
        WHERE event_id = ?
        """,
        (
            metrics["total_trial_area"],
            metrics["mean_step_distance"],
            metrics["footstep_count_on_path"],
            metrics["active_trial_duration_all"],
            metrics["active_trial_duration_path"],
            metrics["std_dev_bounding_box_area"],
            metrics["max_footstep_duration_frames"],
            event_id,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill missing summary metrics into manifest.db"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N events (useful for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print metrics without writing to manifest.db",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"manifest.db not found at: {MANIFEST_PATH}")

    print(f"Using DATAROOT: {DATAROOT}")
    print(f"Using manifest DB: {MANIFEST_PATH}")
    if args.dry_run:
        print("Running in DRY RUN mode (no DB writes).")

    processed = 0
    updated = 0
    skipped_missing_metadata = 0
    skipped_no_manifest_row = 0

    conn = sqlite3.connect(MANIFEST_PATH)
    try:
        for swipe in iter_swipes(DATAROOT):
            event_id = swipe["event_id"]

            # iter_swipes() returns root_path as a file:// URI
            event_dir = uri_to_path(swipe["root_path"])

            metadata_path = find_metadata_file(event_dir)
            if metadata_path is None:
                skipped_missing_metadata += 1
                print(
                    f"[skip] no metadata file found for event {event_id}: {event_dir}"
                )
                continue

            rows = read_metadata_rows(metadata_path)
            metrics = compute_event_metrics(rows)

            processed += 1

            if args.dry_run:
                print(f"\n[event_id={event_id}] using {metadata_path.name}")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
            else:
                cur = conn.execute(
                    "SELECT 1 FROM global_metrics WHERE event_id = ?",
                    (event_id,),
                )
                if cur.fetchone() is None:
                    skipped_no_manifest_row += 1
                    print(f"[skip] event_id not found in global_metrics: {event_id}")
                    continue

                update_manifest_metrics(conn, event_id, metrics)
                updated += 1

                if updated % 250 == 0:
                    conn.commit()
                    print(f"[progress] committed {updated} updated events")

            if args.limit is not None and processed >= args.limit:
                break

        if not args.dry_run:
            conn.commit()

    finally:
        conn.close()

    print("\nDone.")
    print(f"Processed events: {processed}")
    print(f"Updated events:   {updated}")
    print(f"Skipped (no metadata file): {skipped_missing_metadata}")
    print(f"Skipped (missing manifest row): {skipped_no_manifest_row}")


if __name__ == "__main__":
    main()
