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


cc_root = pathlib.Path("data")
tile_boundaries = [(i * 120, (i + 1) * 120) for i in range(6)]

metadata_configs = []
_vals = "20 25 30 35 40".split()
for x in _vals:
    for y in _vals:
        metadata_configs += [f"{x}{y}"]


def parse_identifying_components_from_path(data_filename):
    f = pathlib.Path(data_filename)

    swipe_n = int(f.parent.name)
    direction = f.parent.parent.name
    date = f.parent.parent.parent.name
    participant = int(f.parent.parent.parent.parent.name)

    return participant, date, direction, swipe_n


def load_all_metadata():
    metadata_filepaths = cc_root.glob("**/metadata.csv")

    dfs = []
    for f in metadata_filepaths:
        df = pd.read_csv(f)
        dfs.append(df)

    return pd.concat(dfs)


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

    if True:
        print("Anchor Identification:")
        for i, (f, l) in enumerate(zip(metadata.FootstepID, loss)):
            if i == min_idx:
                print(f"{f}: {l:.02f} *")
            else:
                print(f"{f}: {l:.02f}")
