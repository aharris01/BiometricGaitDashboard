import argparse
import cProfile
import contextlib
import functools
import io
import logging
import pstats
import shutil
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this benchmark as a module from the repository root:\n"
        "python3 -m backend.scripts.benchmark_sal_footsteps_mutations --event-id <event_id>"
    )

from flask import Flask

from backend.src.routes.footsteps import CreateFootstepRequestPayload
from backend.storage_access_layer.helpers import sal_footsteps as sal_footsteps_module
from backend.storage_access_layer.pipeline import (
    footstep_edits as footstep_edits_module,
)
from backend.storage_access_layer.db.db import LOCAL_DB_PATH
from backend.storage_access_layer.sal import SAL
from backend.storage_access_layer.utils import uri_to_path


@dataclass(frozen=True)
class EventFiles:
    metadata_csv: Path
    steps_npz: Path
    steps_raw_npz: Path


@dataclass
class BenchmarkRun:
    elapsed_ms: float
    phase_timings_ms: dict[str, float]


class PhaseRecorder:
    def __init__(self):
        self.timings_ms: dict[str, list[float]] = defaultdict(list)
        self._patches: list[tuple[object, str, object]] = []
        self._call_counts: dict[str, int] = defaultdict(int)

    def patch(self, owner: object, attr_name: str, label: str | None = None) -> None:
        original = getattr(owner, attr_name)
        patch_key = f"{id(owner)}:{attr_name}"

        @functools.wraps(original)
        def wrapped(*args, **kwargs):
            call_index = self._call_counts[patch_key]
            self._call_counts[patch_key] += 1
            resolved_label = label or attr_name
            if "{n}" in resolved_label:
                resolved_label = resolved_label.format(n=call_index + 1)

            started = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000
                self.timings_ms[resolved_label].append(elapsed_ms)

        setattr(owner, attr_name, wrapped)
        self._patches.append((owner, attr_name, original))

    def totals(self) -> dict[str, float]:
        return {label: sum(values) for label, values in self.timings_ms.items()}

    def restore(self) -> None:
        for owner, attr_name, original in reversed(self._patches):
            setattr(owner, attr_name, original)
        self._patches.clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark SALFootsteps mutation methods without starting the main app."
        )
    )
    parser.add_argument(
        "--event-id",
        required=True,
        help="Event ID to benchmark against.",
    )
    parser.add_argument(
        "--footstep-id",
        type=int,
        default=None,
        help="Existing footstep ID to use for save/create templates. Defaults to 0.",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=["save", "create", "delete", "all"],
        default=["all"],
        help="Mutation methods to benchmark.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Timed iterations per method.",
    )
    parser.add_argument(
        "--warmups",
        type=int,
        default=1,
        help="Untimed warmup runs per method.",
    )
    parser.add_argument(
        "--keep-label",
        default="benchmark-keep",
        help="Label used when benchmarking save_footstep_review.",
    )
    parser.add_argument(
        "--create-label",
        default="benchmark-create",
        help="Label used when benchmarking create_footstep.",
    )
    parser.add_argument(
        "--profile-top",
        type=int,
        default=20,
        help=(
            "Run one extra cProfile pass per method and print the top functions by "
            "cumulative time. Use 0 to disable."
        ),
    )
    return parser.parse_args()


def normalize_methods(raw_methods: list[str]) -> list[str]:
    if "all" in raw_methods:
        return ["save", "create", "delete"]
    return raw_methods


def get_event_files(sal: SAL, event_id: str) -> EventFiles:
    event, err = sal.common._require_event(event_id)
    if err or event is None:
        raise ValueError(f"Unable to load event {event_id}: {err}")

    event_dir = uri_to_path(event.trial_npz_uri).parent
    return EventFiles(
        metadata_csv=event_dir / "metadata.csv",
        steps_npz=event_dir / "steps.npz",
        steps_raw_npz=event_dir / "steps.raw.npz",
    )


def backup_paths(tmp_dir: Path, event_files: EventFiles) -> dict[Path, Path | None]:
    backups: dict[Path, Path | None] = {}
    paths = [LOCAL_DB_PATH, *event_files.__dict__.values()]

    for path in paths:
        if path.exists():
            backup_path = tmp_dir / path.name
            shutil.copy2(path, backup_path)
            backups[path] = backup_path
        else:
            backups[path] = None

    return backups


def restore_paths(backups: dict[Path, Path | None]) -> None:
    for original, backup in backups.items():
        if backup is None:
            if original.exists():
                original.unlink()
            continue

        shutil.copy2(backup, original)


def get_reference_footstep(
    sal: SAL, event_id: str, footstep_id: int | None
) -> tuple[int, dict]:
    steps, err = sal.get_footsteps(event_id)
    if err or not steps:
        raise ValueError(f"Unable to load footsteps for {event_id}: {err}")

    if footstep_id is None:
        return int(steps[0]["id"]), steps[0]

    for step in steps:
        if int(step["id"]) == footstep_id:
            return footstep_id, step

    raise ValueError(f"Footstep {footstep_id} was not found in event {event_id}.")


def build_save_payload(step: dict, label: str) -> dict:
    return {
        "x_min": int(step["x_min"]),
        "x_max": int(step["x_max"]),
        "y_min": int(step["y_min"]),
        "y_max": int(step["y_max"]),
        "start_frame": int(step["start_frame"]),
        "end_frame": int(step["end_frame"]),
        "label": label,
    }


def build_create_payload(step: dict, label: str) -> CreateFootstepRequestPayload:
    return CreateFootstepRequestPayload(
        start_frame=int(step["start_frame"]),
        end_frame=int(step["end_frame"]),
        x_min=int(step["x_min"]),
        x_max=int(step["x_max"]),
        y_min=int(step["y_min"]),
        y_max=int(step["y_max"]),
        label=label,
    )


def time_call(callable_obj) -> tuple[float, tuple[object, object]]:
    started = time.perf_counter()
    result = callable_obj()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms, result


def require_success(result: tuple[object, object], context: str) -> object:
    payload, err = result
    if err is not None:
        raise RuntimeError(f"{context} failed with error: {err}")
    return payload


@contextlib.contextmanager
def instrument_method(active_sal: SAL, method: str):
    recorder = PhaseRecorder()
    helper = active_sal.footsteps
    editor = helper.editor

    if method == "save":
        recorder.patch(
            helper,
            "get_footstep_review_context",
            "get_footstep_review_context.{n}",
        )
        recorder.patch(
            sal_footsteps_module,
            "_validate_bounding_box",
            "_validate_bounding_box",
        )
        recorder.patch(editor, "edit_footstep", "editor.edit_footstep")
        recorder.patch(
            active_sal.db,
            "update_local_footstep",
            "db.update_local_footstep",
        )
        recorder.patch(
            sal_footsteps_module,
            "calculate_all_metrics",
            "calculate_all_metrics",
        )
        recorder.patch(
            active_sal.db,
            "update_event_metrics",
            "db.update_event_metrics",
        )
    elif method == "create":
        recorder.patch(
            sal_footsteps_module,
            "_validate_bounding_box",
            "_validate_bounding_box",
        )
        recorder.patch(
            active_sal.db,
            "create_local_footstep",
            "db.create_local_footstep",
        )
        recorder.patch(
            helper,
            "get_footstep_review_context",
            "get_footstep_review_context",
        )
    elif method == "delete":
        recorder.patch(
            active_sal.db,
            "get_single_footstep",
            "db.get_single_footstep",
        )
        recorder.patch(editor, "delete_footstep", "editor.delete_footstep")
        recorder.patch(
            active_sal.db,
            "delete_local_footstep",
            "db.delete_local_footstep",
        )
        recorder.patch(
            sal_footsteps_module,
            "calculate_all_metrics",
            "calculate_all_metrics",
        )
        recorder.patch(
            active_sal.db,
            "update_event_metrics",
            "db.update_event_metrics",
        )
    else:
        raise ValueError(f"Unknown method for instrumentation: {method}")

    if method in {"save", "delete"}:
        recorder.patch(footstep_edits_module, "load_metadata", "editor.load_metadata")
        recorder.patch(
            footstep_edits_module,
            "identify_anchor_footstep",
            "editor.identify_anchor_footstep",
        )
        recorder.patch(
            footstep_edits_module,
            "trace_path",
            "editor.trace_path",
        )
        recorder.patch(
            footstep_edits_module,
            "preprocess_footsteps",
            "editor.preprocess_footsteps",
        )
        recorder.patch(
            footstep_edits_module.np,
            "savez_compressed",
            "editor.np.savez_compressed",
        )
        recorder.patch(
            footstep_edits_module.np,
            "savez",
            "editor.np.savez",
        )
        recorder.patch(footstep_edits_module, "_update_csv", "editor._update_csv")

    try:
        yield recorder
    finally:
        recorder.restore()


def profile_call(callable_obj, top_n: int) -> tuple[BenchmarkRun, str]:
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        result = callable_obj()
    finally:
        profiler.disable()

    output = io.StringIO()
    stats = pstats.Stats(profiler, stream=output)
    stats.strip_dirs().sort_stats("cumulative").print_stats(top_n)
    return result, output.getvalue().strip()


def summarize_phases(
    phase_runs: list[dict[str, float]],
    mean_total_ms: float,
) -> list[str]:
    totals_by_phase: dict[str, list[float]] = defaultdict(list)
    for run in phase_runs:
        for label, elapsed_ms in run.items():
            totals_by_phase[label].append(elapsed_ms)

    lines: list[str] = []
    ranked = sorted(
        totals_by_phase.items(),
        key=lambda item: statistics.mean(item[1]),
        reverse=True,
    )
    for label, values in ranked:
        mean_ms = statistics.mean(values)
        percent = (mean_ms / mean_total_ms * 100) if mean_total_ms > 0 else 0.0
        lines.append(f"  {label}: mean={mean_ms:.2f} ms ({percent:.1f}% of total)")

    return lines


def benchmark_save(
    sal: SAL,
    event_id: str,
    footstep_id: int,
    step: dict,
    label: str,
) -> BenchmarkRun:
    payload = build_save_payload(step, label)
    with instrument_method(sal, "save") as recorder:
        elapsed_ms, result = time_call(
            lambda: sal.save_footstep_review(event_id, footstep_id, payload)
        )
    require_success(result, "save_footstep_review")
    return BenchmarkRun(elapsed_ms=elapsed_ms, phase_timings_ms=recorder.totals())


def benchmark_create(
    sal: SAL,
    event_id: str,
    step: dict,
    label: str,
) -> BenchmarkRun:
    payload = build_create_payload(step, label)
    with instrument_method(sal, "create") as recorder:
        elapsed_ms, result = time_call(lambda: sal.create_footstep(event_id, payload))
    require_success(result, "create_footstep")
    return BenchmarkRun(elapsed_ms=elapsed_ms, phase_timings_ms=recorder.totals())


def benchmark_delete(
    sal: SAL,
    event_id: str,
    step: dict,
    label: str,
) -> BenchmarkRun:
    create_payload = build_create_payload(step, label)
    created = require_success(
        sal.create_footstep(event_id, create_payload),
        "delete setup create_footstep",
    )
    if not isinstance(created, dict):
        raise RuntimeError("Non dict object returned from create")
    created_item = created.get("item") or {}
    created_footstep_id = created_item.get("footstep_id")
    if created_footstep_id is None:
        raise RuntimeError("delete setup could not determine created footstep_id")

    with instrument_method(sal, "delete") as recorder:
        elapsed_ms, result = time_call(
            lambda: sal.delete_footstep(event_id, int(created_footstep_id))
        )
    require_success(result, "delete_footstep")
    return BenchmarkRun(elapsed_ms=elapsed_ms, phase_timings_ms=recorder.totals())


def summarize_timings(method: str, timings_ms: list[float]) -> str:
    if len(timings_ms) == 1:
        return f"{method}: {timings_ms[0]:.2f} ms"

    mean_ms = statistics.mean(timings_ms)
    median_ms = statistics.median(timings_ms)
    min_ms = min(timings_ms)
    max_ms = max(timings_ms)
    stdev_ms = statistics.stdev(timings_ms)
    return (
        f"{method}: mean={mean_ms:.2f} ms, median={median_ms:.2f} ms, "
        f"min={min_ms:.2f} ms, max={max_ms:.2f} ms, stdev={stdev_ms:.2f} ms"
    )


def run_profiled_method(
    method: str,
    runner,
    backups: dict[Path, Path | None],
    top_n: int,
) -> None:
    if top_n <= 0:
        return

    restore_paths(backups)
    profiled_sal = SAL()
    try:
        result, profile_output = profile_call(lambda: runner(profiled_sal), top_n)
    finally:
        profiled_sal._close_db()

    print(f"{method} cProfile top {top_n} cumulative functions:")
    print(profile_output)
    if result.phase_timings_ms:
        print("profiled phase breakdown:")
        for line in summarize_phases([result.phase_timings_ms], result.elapsed_ms):
            print(line)
    print()


def run_benchmark(args: argparse.Namespace) -> int:
    methods = normalize_methods(args.methods)
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    with app.app_context():
        sal = SAL()
        try:
            event_files = get_event_files(sal, args.event_id)
            footstep_id, step = get_reference_footstep(
                sal, args.event_id, args.footstep_id
            )
        finally:
            sal._close_db()

        print(f"Event ID: {args.event_id}")
        print(f"Reference footstep ID: {footstep_id}")
        print(f"Methods: {', '.join(methods)}")
        print(f"Warmups per method: {args.warmups}")
        print(f"Timed iterations per method: {args.iterations}")
        print()

        with TemporaryDirectory(prefix="sal-footsteps-benchmark-") as tmp_dir_name:
            tmp_dir = Path(tmp_dir_name)
            backups = backup_paths(tmp_dir, event_files)

            method_runners = {
                "save": lambda active_sal: benchmark_save(
                    active_sal,
                    args.event_id,
                    footstep_id,
                    step,
                    args.keep_label,
                ),
                "create": lambda active_sal: benchmark_create(
                    active_sal,
                    args.event_id,
                    step,
                    args.create_label,
                ),
                "delete": lambda active_sal: benchmark_delete(
                    active_sal,
                    args.event_id,
                    step,
                    args.create_label,
                ),
            }

            for method in methods:
                for _ in range(args.warmups):
                    restore_paths(backups)
                    warmup_sal = SAL()
                    try:
                        method_runners[method](warmup_sal)
                    finally:
                        warmup_sal._close_db()

                timings_ms: list[float] = []
                phase_runs: list[dict[str, float]] = []
                for iteration in range(1, args.iterations + 1):
                    restore_paths(backups)
                    iteration_sal = SAL()
                    try:
                        run = method_runners[method](iteration_sal)
                    finally:
                        iteration_sal._close_db()

                    timings_ms.append(run.elapsed_ms)
                    phase_runs.append(run.phase_timings_ms)
                    print(f"{method} iteration {iteration}: {run.elapsed_ms:.2f} ms")

                print(summarize_timings(method, timings_ms))
                if phase_runs:
                    print("phase breakdown:")
                    for line in summarize_phases(
                        phase_runs,
                        statistics.mean(timings_ms),
                    ):
                        print(line)
                print()

                run_profiled_method(
                    method,
                    method_runners[method],
                    backups,
                    args.profile_top,
                )

            restore_paths(backups)

    return 0


if __name__ == "__main__":
    raise SystemExit(run_benchmark(parse_args()))
