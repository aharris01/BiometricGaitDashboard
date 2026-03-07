# backend/scripts/backfill_manifest_footsteps.py

import argparse
import csv
import os
import sqlite3
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
    s = str(uri)

    if "://" in s and not s.startswith("file://"):
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    if not s.startswith("file://"):
        return Path(s)

    parsed = urlparse(s)
    path = unquote(parsed.path)

    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return Path(path)


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def find_metadata_file(event_dir: Path) -> Path | None:
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
        if len(parts) == 3 and parts[0] == "metadata" and parts[2] == "csv":
            try:
                numeric_candidates.append((int(parts[1]), path))
            except ValueError:
                pass

    if numeric_candidates:
        numeric_candidates.sort(key=lambda item: item[0])
        return numeric_candidates[-1][1]

    return fallback_candidates[-1]


def read_metadata_rows(metadata_path: Path) -> list[dict[str, str]]:
    with metadata_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_footsteps_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS footsteps (
            event_id TEXT NOT NULL,
            footstep_id INTEGER NOT NULL,
            start_frame INTEGER NOT NULL,
            end_frame INTEGER NOT NULL,
            x_min INTEGER NOT NULL,
            x_max INTEGER NOT NULL,
            y_min INTEGER NOT NULL,
            y_max INTEGER NOT NULL,
            PRIMARY KEY (event_id, footstep_id)
        )
        """
    )


def extract_footsteps(
    rows: list[dict[str, str]],
) -> list[tuple[int, int, int, int, int, int, int]]:
    """
    Return rows as:
        (footstep_id, start_frame, end_frame, x_min, x_max, y_min, y_max)

    We keep all extracted footsteps from metadata.csv for now.
    """
    by_id: dict[int, tuple[int, int, int, int, int, int, int]] = {}

    for row in rows:
        footstep_id = parse_int(row.get("FootstepID"))
        start_frame = parse_int(row.get("StartFrame"))
        end_frame = parse_int(row.get("EndFrame"))
        x_min = parse_int(row.get("XMin"))
        x_max = parse_int(row.get("XMax"))
        y_min = parse_int(row.get("YMin"))
        y_max = parse_int(row.get("YMax"))

        if (
            footstep_id is None
            or start_frame is None
            or end_frame is None
            or x_min is None
            or x_max is None
            or y_min is None
            or y_max is None
        ):
            continue

        by_id[footstep_id] = (
            footstep_id,
            start_frame,
            end_frame,
            x_min,
            x_max,
            y_min,
            y_max,
        )

    return [by_id[key] for key in sorted(by_id.keys())]


def replace_event_footsteps(
    conn: sqlite3.Connection,
    event_id: str,
    footsteps: list[tuple[int, int, int, int, int, int, int]],
) -> None:
    conn.execute("DELETE FROM footsteps WHERE event_id = ?", (event_id,))

    if not footsteps:
        return

    conn.executemany(
        """
        INSERT INTO footsteps (
            event_id,
            footstep_id,
            start_frame,
            end_frame,
            x_min,
            x_max,
            y_min,
            y_max
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                event_id,
                footstep_id,
                start_frame,
                end_frame,
                x_min,
                x_max,
                y_min,
                y_max,
            )
            for (
                footstep_id,
                start_frame,
                end_frame,
                x_min,
                x_max,
                y_min,
                y_max,
            ) in footsteps
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate manifest.db footsteps table from metadata.csv files"
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
        help="Print what would be inserted without writing to manifest.db",
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

    conn = sqlite3.connect(MANIFEST_PATH)
    try:
        ensure_footsteps_table(conn)

        for swipe in iter_swipes(DATAROOT):
            event_id = swipe["event_id"]
            event_dir = uri_to_path(swipe["root_path"])

            metadata_path = find_metadata_file(event_dir)
            if metadata_path is None:
                skipped_missing_metadata += 1
                print(
                    f"[skip] no metadata file found for event {event_id}: {event_dir}"
                )
                continue

            rows = read_metadata_rows(metadata_path)
            footsteps = extract_footsteps(rows)

            processed += 1

            if args.dry_run:
                print(
                    f"[event_id={event_id}] using {metadata_path.name} -> {len(footsteps)} footsteps"
                )
            else:
                replace_event_footsteps(conn, event_id, footsteps)
                updated += 1

                if updated % 250 == 0:
                    conn.commit()
                    print(f"[progress] committed {updated} events")

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


if __name__ == "__main__":
    main()
