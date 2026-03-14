# Author: Aaron William Tabor
# This file contains utility functions for the footstep extraction pipeline.
# Some of these functions were from a Jupyter notebook showing the process
# for footstep extraction and were moved here to be used in the footstep
# editing process as well.

import pathlib
import dateutil.parser
import pandas as pd
import numpy as np

import dateutil
from sklearn.decomposition import PCA

T_MIN = 50
T_MAX = 400

SHORT_DIMENSTION_MIN = 15
SHORT_DIMENSTION_MAX = 80
LONG_DIMENSION_MIN = 40
LONG_DIMENSION_MAX = 100


def parse_identifying_components_from_path(data_filename):
    f = pathlib.Path(data_filename)

    swipe_n = int(f.parent.name)
    direction = f.parent.parent.name
    date = f.parent.parent.parent.name
    participant = int(f.parent.parent.parent.parent.name)

    return participant, date, direction, swipe_n


def load_metadata(filepath):
    return pd.read_csv(
        filepath,
        converters={
            "Timestamp": dateutil.parser.parse,
        },
    )


MAX_DISTANCE = np.sqrt(220**2 + 660**2)


# The anchor footstep is used to trace the participant's path of travel.
# It is the closest (spatio-temporal) footstep to the swipe event for this trial
def identify_anchor_footstep(metadata):
    if metadata.Direction[0] == "out":
        # the anchor footstep should occur at a short delay following the swipe
        delay = 25
        temporal_loss = np.array([abs(delay - t) / (3000 - delay) for t in metadata.t])
    else:
        # we want the footstep that falls closest to 30-seconds
        temporal_loss = np.array([abs(3000 - t) / 3000 for t in metadata.t])

    y_target = 10
    gate = metadata.Gate[0]
    x_target = 60 if gate in [3, 4] else 220

    delta_y = np.abs(metadata.y - y_target)
    delta_x = np.abs(metadata.x - x_target)

    distance_from_target = np.sqrt(delta_x**2 + delta_y**2)
    distance_loss = distance_from_target / MAX_DISTANCE

    loss = (np.sqrt(temporal_loss) + np.sqrt(distance_loss)) / 2

    """
  # Invalid footsteps cannot be the anchor.
  loss[metadata.valid == False] = 1.0
  """

    min_idx = loss.argmin()

    metadata.loc[min_idx, "path_order"] = 0
    return


def get_heading(row, trial_p100: np.ndarray):
    bb = row["XMin XMax YMin YMax".split()]
    p100 = trial_p100[bb.YMin : bb.YMax, bb.XMin : bb.XMax]

    c, r = np.where(p100 > 0)
    X = np.array([c, r]).T

    pca = PCA(n_components=2)
    reducer = pca.fit(X)
    angle_needed_to_upright = np.arctan2(pca.components_[0, 1], pca.components_[0, 0])

    heading_angle = angle_needed_to_upright + 0.5 * np.pi

    tau = 2 * np.pi
    if heading_angle > tau:
        heading_angle -= tau

    if heading_angle < 0:
        heading_angle += tau

    return heading_angle


def _is_within_expected_bb_size(row):
    x_length = row.XMax - row.XMin
    y_length = row.YMax - row.YMin

    short_length = min(x_length, y_length)
    long_length = max(x_length, y_length)

    return (SHORT_DIMENSTION_MIN < short_length < SHORT_DIMENSTION_MAX) and (
        LONG_DIMENSION_MIN < long_length < LONG_DIMENSION_MAX
    )


def _is_within_expect_duration(row):
    duration = row.EndFrame - row.StartFrame
    return T_MIN < duration < T_MAX


def _get_angle_between(f1, f2):
    dx = f2.x - f1.x
    dy = f2.y - f1.y
    a = np.arctan2(-dy, dx)

    if a < 0:
        a += 2 * np.pi

    return a


## assumes that path order is populated for all steps currently on the path
def _find_next_footstep(metadata, current_footstep_id):
    current_footstep = metadata.loc[current_footstep_id]
    remaining_candidates = metadata.query("path_order < 0")

    if current_footstep.Direction == "in":
        # We are tracing backward through time. Next step must occur in some sane window of time before the current one
        remaining_candidates = remaining_candidates.query(
            "@current_footstep.t-150 < t < @current_footstep.t-10"
        )
    else:
        # We are tracing forward through time. Next step must occur in some sane window of time after the current one
        remaining_candidates = remaining_candidates.query(
            "@current_footstep.t+150 > t > @current_footstep.t+10"
        )

    ## TODO: Something funny is going on here...
    distance_to_candidates = np.sqrt(
        (remaining_candidates.x - current_footstep.x) ** 2
        + (remaining_candidates.y - current_footstep.y) ** 2
    )

    remaining_candidates = remaining_candidates[distance_to_candidates < 250]

    if len(remaining_candidates) == 0:
        return {}

    def normalize_range(a):
        # This allows is to still pass the stop criteria threshold and be added to the path
        if len(a) == 1:
            return np.array([0.1])

        return (a - np.min(a)) / (np.max(a) - np.min(a))

    dys = np.abs(remaining_candidates.y.to_numpy() - current_footstep.y)
    dxs = np.abs(remaining_candidates.x.to_numpy() - current_footstep.x)

    d_loss = np.sqrt(dxs**2 + dys**2)
    d_loss = normalize_range(d_loss)

    t_loss = np.abs(remaining_candidates.t.to_numpy() - current_footstep.t)
    t_loss = normalize_range(t_loss)

    """
  # in addition to favoring more temporally proximate candidates,
  # candidates exceedinging a certain absoulte duration threshold should be heavily penalized
  delta_t = np.abs(remaining_candidates.t.to_numpy() - current_footstep.t)
  t_absolute_loss = (delta_t / 1000).clip(max=1)
  """

    angle_btwn = np.array(
        [
            _get_angle_between(current_footstep, candidate)
            for _, candidate in remaining_candidates.iterrows()
        ]
    )

    desired_angle = (current_footstep.heading_angle + np.pi) % (2 * np.pi)

    a_loss = np.abs(angle_btwn - desired_angle)
    a_loss = normalize_range(a_loss)

    loss = (np.sqrt(d_loss) + np.sqrt(t_loss) + np.sqrt(a_loss)) / 3

    loss_dict = {f: l for f, l in zip(remaining_candidates.FootstepID, loss)}
    return loss_dict


def trace_path(metadata):
    # Start from the anchor footstep
    current_footstep_id = metadata.query("path_order == 0").FootstepID.iloc[0]

    next_path_order = 1
    while next_path_order < len(metadata):
        loss_dict = _find_next_footstep(metadata, current_footstep_id)

        min_loss = 1
        min_footstep_id = -1
        for f, l in loss_dict.items():
            if l <= min_loss:
                min_loss = l
                min_footstep_id = f

        next_footstep_id, next_loss = min_footstep_id, min_loss

        # for k, v in loss_dict.items():
        #     if k == next_footstep_id:
        #         pass
        #         # print(f"\t{k}: {v:.2f} *")
        #     else:
        #         pass
        #         # print(f"\t{k}: {v:.2f}")

        # Path termination. Evidence suggesting that we have reached the end of the path:
        # a) current footstep is near edge of grid
        # b) current headings points off of grid.
        # c) all next-step candidates are improbable
        current_footstep = metadata.loc[current_footstep_id]

        x = current_footstep.x
        y = current_footstep.y

        px_from_x_edge = min(x, 480 - x)
        x_loss = px_from_x_edge / 480

        px_from_y_edge = min(y, 720 - y)
        y_loss = px_from_y_edge / 720

        edge_loss = min(x_loss, y_loss)

        trajectory_angle = (current_footstep.heading_angle + np.pi) % (2 * np.pi)
        angle_to_grid_center = np.arctan2(-(360 - y), (240 - x))
        angle_difference = (trajectory_angle - angle_to_grid_center) % (2 * np.pi)
        angle_deviation = min(angle_difference, 2 * np.pi - angle_difference)
        a_loss = 1 - (angle_deviation / np.pi)

        improbable_loss = 1 - next_loss

        # print([f"{l:.2f}" for l in [x_loss, y_loss, a_loss, improbable_loss]])

        stop_loss = (
            np.sqrt(edge_loss) + np.sqrt(a_loss) + np.sqrt(improbable_loss)
        ) / 3
        # print(f"\tstop loss: {stop_loss:.2f}")

        if (len(loss_dict) == 0) or stop_loss < 0.2:
            break

        metadata.loc[next_footstep_id, "path_order"] = next_path_order

        current_footstep_id = next_footstep_id
        next_path_order += 1


# reset all path nodes EXCEPT for the
def reset_path_order(row):
    if row.path_order == 0:
        return 0
    else:
        return -1
