# Author: Aaron William Tabor
# This file contains utility functions for the pipeline.

import pathlib
import dateutil.parser
import pandas as pd

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
