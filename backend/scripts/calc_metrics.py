from pathlib import Path
from typing import Any, cast

import pandas as pd
from pandas.api.types import is_scalar
from flask import current_app


def _column(event_metadata: pd.DataFrame, column_name: str) -> pd.Series:
    return cast(pd.Series, event_metadata[column_name])


def _is_missing_scalar(value: Any) -> bool:
    if value is None:
        return True
    if not is_scalar(value):
        return False
    return bool(pd.isna(value))


def _avg_bbox_size(event_metadata: pd.DataFrame):
    return (
        (_column(event_metadata, "XMax") - _column(event_metadata, "XMin"))
        * (_column(event_metadata, "YMax") - _column(event_metadata, "YMin"))
    ).mean()


def _step_count_all(event_metadata: pd.DataFrame):
    return len(event_metadata)


def _total_trial_area(event_metadata: pd.DataFrame):
    return int(cast(Any, _column(event_metadata, "Trial_Area").max()))


def _steps_on_path(event_metadata: pd.DataFrame):
    return len(event_metadata.query("path_order >= 0"))


def _active_trial_duration(event_metadata: pd.DataFrame):
    # Trial duration for every step found
    all_step_min = _column(event_metadata, "StartFrame").min()
    all_step_max = _column(event_metadata, "EndFrame").max()
    all_step_duration = int(all_step_max - all_step_min)

    # Trial duration for steps on path
    path_step_min = _column(event_metadata.query("path_order >= 0"), "StartFrame").min()
    path_step_max = _column(event_metadata.query("path_order >= 0"), "EndFrame").max()
    path_step_duration = int(path_step_max - path_step_min)

    return all_step_duration, path_step_duration


def _bbox_area_std(event_metadata: pd.DataFrame, event_id):
    footstep_areas = abs(
        _column(event_metadata, "YMax") - _column(event_metadata, "YMin")
    ) * abs(_column(event_metadata, "XMax") - _column(event_metadata, "XMin"))
    area_std = footstep_areas.std()
    if _is_missing_scalar(area_std):
        print(f"Sample too small to calculate bounding box area std for {event_id}")
        area_std = float(0)
    return area_std


def _bbox_area_variance(event_metadata: pd.DataFrame, event_id):
    footstep_areas = abs(
        _column(event_metadata, "YMax") - _column(event_metadata, "YMin")
    ) * abs(_column(event_metadata, "XMax") - _column(event_metadata, "XMin"))
    area_variance = footstep_areas.var()
    if _is_missing_scalar(area_variance):
        print(
            f"Sample size too small to calculate variance of bounding box area for {event_id}"
        )
        area_variance = float(0)
    return area_variance


def _mean_dimensions(event_metadata: pd.DataFrame):
    mean_width = (
        abs(_column(event_metadata, "XMax") - _column(event_metadata, "XMin"))
    ).mean()
    mean_height = (
        abs(_column(event_metadata, "YMax") - _column(event_metadata, "YMin"))
    ).mean()
    return mean_height, mean_width


def _dimensions_variance(event_metadata: pd.DataFrame, event_id):
    height_variance = (
        abs(_column(event_metadata, "YMax") - _column(event_metadata, "XMin"))
    ).var()
    width_variance = (
        abs(_column(event_metadata, "XMax") - _column(event_metadata, "XMin"))
    ).var()
    if _is_missing_scalar(height_variance) or _is_missing_scalar(width_variance):
        print(f"Sample size too small to calculate dimension variance for {event_id}")
        if _is_missing_scalar(height_variance):
            height_variance = float(0)
        if _is_missing_scalar(width_variance):
            width_variance = float(0)
    return height_variance, width_variance


def _longest_footstep_duration(event_metadata: pd.DataFrame):
    return (
        _column(event_metadata, "EndFrame") - _column(event_metadata, "StartFrame")
    ).max()


def _mean_distance_between_consecutive_steps(event_metadata: pd.DataFrame):
    distance = (
        (_column(event_metadata, "x") - _column(event_metadata, "x").shift(-1)).pow(2)
    ) + ((_column(event_metadata, "y") - _column(event_metadata, "y").shift(-1)).pow(2))
    event_metadata["Distance"] = distance.pow(0.5)
    return _column(event_metadata, "Distance").mean()


def _variance_distance_between_consecutive_steps(
    event_metadata: pd.DataFrame, event_id
):
    distance_variation = _column(event_metadata, "Distance").var()
    if _is_missing_scalar(distance_variation):
        print(f"Sample size too small to calculate distance variance for {event_id}")
        distance_variation = float(0)
    return distance_variation


def _mean_footstep_angle(event_metadata: pd.DataFrame):
    return _column(event_metadata, "heading_angle").mean()


def _std_footstep_angle(event_metadata: pd.DataFrame, event_id):
    std_angle = _column(event_metadata, "heading_angle").std()
    if _is_missing_scalar(std_angle):
        print(
            f"Sample size too small to calculate standard deviation of heading angle for {event_id}"
        )
        std_angle = float(0)
    return std_angle


def _variance_footstep_angle(event_metadata: pd.DataFrame, event_id):
    angle_variance = _column(event_metadata, "heading_angle").mean()
    if _is_missing_scalar(angle_variance):
        print(
            f"Sample size too small to calculate heading angle variance for {event_id}"
        )
        angle_variance = float(0)
    return angle_variance


def _metric_is_missing(value):
    if value is None:
        return True
    if isinstance(value, tuple):
        return any(_metric_is_missing(item) for item in value)
    return _is_missing_scalar(value)


def _safe_metric(event_id: str, metric_name: str, metric_fn, default_value, *args):
    try:
        value = metric_fn(*args)
    except Exception as err:
        print(
            f"[{event_id}] Error calculating '{metric_name}': {err}. Using default {default_value}"
        )
        return default_value

    if _metric_is_missing(value):
        print(
            f"[{event_id}] Metric '{metric_name}' was missing/NaN. Using default {default_value}"
        )
        return default_value
    return value


def calculate_all_metrics(event_id: str, event_path: Path):
    event_metrics = {}
    event_metadata_file = None
    try:
        event_metadata_file = event_path.open()
        event_metadata = pd.read_csv(event_metadata_file)

        # avg_bbox_size
        avg_bbox = _safe_metric(
            event_id, "avg_bbox_size", _avg_bbox_size, 0, event_metadata
        )
        event_metrics["avg_bbox_size"] = avg_bbox

        # Standard deviation of bbox area
        area_std = _safe_metric(
            event_id,
            "std_dev_bounding_box_area",
            _bbox_area_std,
            0.0,
            event_metadata,
            event_id,
        )
        event_metrics["std_dev_bounding_box_area"] = area_std

        # Variance of bbox area
        area_variance = _safe_metric(
            event_id,
            "bbox_area_variance",
            _bbox_area_variance,
            0.0,
            event_metadata,
            event_id,
        )
        event_metrics["variance_bounding_box_area"] = area_variance

        # Mean bounding box height and width
        mean_height, mean_width = _safe_metric(
            event_id, "mean_dimensions", _mean_dimensions, (0.0, 0.0), event_metadata
        )
        event_metrics["mean_height"], event_metrics["mean_width"] = (
            mean_height,
            mean_width,
        )

        # Variance of bounding box height and width
        height_variance, width_variance = _safe_metric(
            event_id,
            "dimensions_variance",
            _dimensions_variance,
            (0.0, 0.0),
            event_metadata,
            event_id,
        )
        (
            event_metrics["variance_bounding_box_height"],
            event_metrics["variance_bounding_box_width"],
        ) = (
            height_variance,
            width_variance,
        )

        # step count
        step_count = _safe_metric(
            event_id, "step_count", _step_count_all, 0, event_metadata
        )
        event_metrics["step_count"] = step_count

        # Number of footsteps on path
        steps_on_path_count = _safe_metric(
            event_id, "step_count_on_path", _steps_on_path, 0, event_metadata
        )
        event_metrics["step_count_on_path"] = steps_on_path_count

        # Calculate total trial area
        total_area = _safe_metric(
            event_id, "trial_area", _total_trial_area, 0, event_metadata
        )
        event_metrics["total_trial_area"] = total_area

        # Mean distance between consecutive steps
        mean_distance = _safe_metric(
            event_id,
            "mean_step_distance",
            _mean_distance_between_consecutive_steps,
            0.0,
            event_metadata,
        )
        event_metrics["mean_step_distance"] = mean_distance

        # Variance of distance between consecutive steps
        distance_variance = _safe_metric(
            event_id,
            "variance_step_distance",
            _variance_distance_between_consecutive_steps,
            0.0,
            event_metadata,
            event_id,
        )
        event_metrics["variance_step_distance"] = distance_variance

        # Active trial duration (all, on path)
        total_duration, on_path_duration = _safe_metric(
            event_id,
            "active_trial_duration",
            _active_trial_duration,
            (0, 0),
            event_metadata,
        )
        (
            event_metrics["active_trial_duration_all"],
            event_metrics["active_trial_duration_path"],
        ) = (
            total_duration,
            on_path_duration,
        )

        # Longest duration footstep
        longest_duration = _safe_metric(
            event_id,
            "max_footstep_duration_frames",
            _longest_footstep_duration,
            0.0,
            event_metadata,
        )
        event_metrics["max_footstep_duration_frames"] = longest_duration

        # Average heading angle of footsteps
        mean_angle = _safe_metric(
            event_id,
            "mean_heading_angle",
            _mean_footstep_angle,
            0.0,
            event_metadata,
        )
        event_metrics["mean_heading_angle"] = mean_angle

        # Standard deviation of footstep heading angle
        std_angle = _safe_metric(
            event_id,
            "std_heading_angle",
            _std_footstep_angle,
            0.0,
            event_metadata,
            event_id,
        )
        event_metrics["std_heading_angle"] = std_angle

        # Variance of heading angle of footsteps
        variance_angle = _safe_metric(
            event_id,
            "variance_heading_angle",
            _variance_footstep_angle,
            0.0,
            event_metadata,
            event_id,
        )
        event_metrics["variance_heading_angle"] = variance_angle

        return event_metrics, None
    except IOError:
        return None, "missing_file"
    except Exception:
        current_app.logger.error("exception")
        return None, "unexpected_error"
    finally:
        if event_metadata_file is not None:
            event_metadata_file.close()
