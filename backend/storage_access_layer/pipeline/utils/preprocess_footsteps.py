# Author: Aaron William Tabor
# This file contains utility functions for preprocessing footsteps.

import collections
from typing import Any
import numpy as np
import cv2
from sklearn.decomposition import PCA
from scipy.interpolate import interp1d


# spatially crop to non-zero area
def _spatial_crop(footstep, thresh=10):
    img_peak = footstep.max(0)

    arr_w = np.sum(img_peak, axis=0)
    arr_h = np.sum(img_peak, axis=1)

    h_start = np.where(arr_h > thresh)[0][0]
    h_end = np.where(arr_h > thresh)[0][-1]
    w_start = np.where(arr_w > thresh)[0][0]
    w_end = np.where(arr_w > thresh)[0][-1]

    return footstep[:, h_start : h_end + 1, w_start : w_end + 1]


# temporally crop to non-zero frames
def _temporal_crop(footstep, thresh=10):
    max_activation = footstep.max((1, 2))

    t_start = np.where(max_activation > thresh)[0][0]
    t_end = np.where(max_activation > thresh)[0][-1]

    return footstep[t_start : t_end + 1, :, :]


def crop_image(img):
    arr_w = np.sum(img, axis=0)
    arr_h = np.sum(img, axis=1)

    h_start = np.where(arr_h > 0)[0][0]
    h_end = np.where(arr_h > 0)[0][-1]
    w_start = np.where(arr_w > 0)[0][0]
    w_end = np.where(arr_w > 0)[0][-1]

    return img[h_start : h_end + 1, w_start : w_end + 1]


# spatially rotate 180 degrees to make footstep upright
def spatial_flip(footstep: np.ndarray):
    # use COP in y direction to make steps upright
    frame_sums = footstep.sum((1, 2))
    cop_numerator = footstep.sum(2) * np.arange(0, footstep.shape[1])
    COP = np.divide(
        cop_numerator,
        frame_sums[:, np.newaxis],
        out=np.full(cop_numerator.shape, np.nan, dtype=float),
        where=frame_sums[:, np.newaxis] != 0,
    ).sum(1)

    if np.nanmean(COP[0 : COP.shape[0] // 2]) < np.nanmean(COP[COP.shape[0] // 2 :]):
        footstep_upright = np.flip(footstep, axis=(1, 2))
        orientation = True
    else:
        footstep_upright = footstep
        orientation = False

    return footstep_upright, orientation


# rotate centered footstep using direction of PC1
def spatial_rotation(footstep: np.ndarray):
    # get peak pressure image
    img_peak = footstep.max(0)

    # get angle of first principal component axis
    c, r = np.where(img_peak > 0)
    X = np.array([c, r]).T  # noqa: F841
    pca = PCA(n_components=2)
    # projected = pca.fit_transform(X)
    angle = np.arctan2(pca.components_[0, 1], pca.components_[0, 0])
    angle = np.degrees(angle)

    # rotate only within 90 degrees
    if abs(angle) > 90:
        angle = angle - 180 * np.sign(angle)

    rotation_angle = -angle

    # grow image to allow room for rotation
    max_sz = max(footstep.shape)
    footstep_rotated = np.zeros((footstep.shape[0], max_sz, max_sz))

    # rotate each frame and pad to desired shape
    for i, frame in enumerate(footstep):
        # rotate frame
        cX, cY = (frame.shape[1] // 2, frame.shape[0] // 2)
        M = cv2.getRotationMatrix2D((cX, cY), rotation_angle, 1)
        frame_rotated = cv2.warpAffine(
            frame, M, (max_sz, max_sz), flags=cv2.INTER_NEAREST
        )

        footstep_rotated[i] = frame_rotated

    # crop to footstep
    footstep_rotated = _spatial_crop(footstep_rotated)

    return footstep_rotated, rotation_angle


# center footstep based on center of mass, area, or extreme limits ('bbox') (alignment_method)
def spatial_translation(footstep: np.ndarray, alignment_method="mass", thresh=10):
    img_peak = footstep.max(0)
    w = img_peak.shape[1]
    l = img_peak.shape[0]  # noqa: E741

    if alignment_method == "mass":
        # get center of mass
        y_center = (
            (img_peak.sum(1) * np.arange(0, img_peak.shape[0])) / img_peak.sum((0, 1))
        ).sum(0)
        x_center = (
            (img_peak.sum(0) * np.arange(0, img_peak.shape[1])) / img_peak.sum((0, 1))
        ).sum(0)
    elif alignment_method == "area":
        # get center of area
        y_center = (
            ((img_peak > thresh).sum(1) * np.arange(0, img_peak.shape[0]))
            / (img_peak > thresh).sum((0, 1))
        ).sum(0)
        x_center = (
            ((img_peak > thresh).sum(0) * np.arange(0, img_peak.shape[1]))
            / (img_peak > thresh).sum((0, 1))
        ).sum(0)
    else:  # 'bbox': center bounding box in frame
        y_idx = np.where((img_peak > thresh))[0]
        x_idx = np.where((img_peak > thresh))[1]
        y_center = np.mean((y_idx.min(), y_idx.max()))
        x_center = np.mean((x_idx.min(), x_idx.max()))

    y_center = int(np.round(y_center))
    x_center = int(np.round(x_center))

    # avoid translating out of the frame
    arr_w = np.sum(img_peak, axis=0)
    arr_l = np.sum(img_peak, axis=1)
    max_y_shift = min(
        np.where(arr_l > thresh)[0][0], l - np.where(arr_l > thresh)[0][-1]
    )
    max_x_shift = min(
        np.where(arr_w > thresh)[0][0], w - np.where(arr_w > thresh)[0][-1]
    )

    x_shift = w // 2 - x_center
    y_shift = l // 2 - y_center
    x_shift = np.sign(x_shift) * np.min(np.abs((x_shift, max_x_shift)))
    y_shift = np.sign(y_shift) * np.min(np.abs((y_shift, max_y_shift)))

    # Modified from the original to satisfy pylance, which was complaining about the type of M. The original code was:
    # M = np.float32([[1, 0, x_shift], [0, 1, y_shift]])
    M = np.array(
        [[1.0, 0.0, float(x_shift)], [0.0, 1.0, float(y_shift)]], dtype=np.float32
    )
    footstep_centered = np.zeros(footstep.shape)

    for i, frame in enumerate(footstep):
        # Modified from the original to satisfy pylance, which was complaining about the type of frame_centered. The original code was:
        # dsize = (int(frame.shape[1]), int(frame.shape[0]))
        # frame_centered = cv2.warpAffine(
        #     frame, M, dsize, flags=cv2.INTER_NEAREST
        # )
        dsize = (int(frame.shape[1]), int(frame.shape[0]))
        frame_centered = cv2.warpAffine(frame, M, dsize, flags=cv2.INTER_NEAREST)
        footstep_centered[i] = frame_centered

    return footstep_centered


# pad footstep with zeros to specified height (h) and width (w)
def spatial_zeropad(footstep: np.ndarray, w=100, h=100):
    footstep_padded = np.zeros((footstep.shape[0], h, w))
    top = np.floor((h - footstep.shape[1]) / 2)
    bottom = np.ceil((h - footstep.shape[1]) / 2)
    left = np.floor((w - footstep.shape[2]) / 2)
    right = np.ceil((w - footstep.shape[2]) / 2)

    for i, frame in enumerate(footstep):
        frame_padded = cv2.copyMakeBorder(
            frame,
            int(top),
            int(bottom),
            int(left),
            int(right),
            cv2.BORDER_CONSTANT,
            value=(0, 0, 0),
        )
        footstep_padded[i] = frame_padded

    return footstep_padded


# classify left/right using P100 pixel counting
def classify_side(footstep: np.ndarray):
    P100 = footstep.max(0)
    P100 = crop_image(P100)
    P100_bin = (P100 > 0).astype(int)

    w = P100_bin.shape[1]
    h = P100_bin.shape[0]

    middle = int(w / 2)
    top_3rd = int(h / 3)
    mid_3rd = int(top_3rd * 2)

    A = np.sum(P100_bin[0:top_3rd, 0:middle])
    B = np.sum(P100_bin[0:top_3rd, middle:])
    C = np.sum(P100_bin[top_3rd:mid_3rd, 0:middle])
    D = np.sum(P100_bin[top_3rd:mid_3rd, middle:])

    left_sum = B + C
    right_sum = A + D

    return bool(left_sum > right_sum)  # True = left, False = right


# interpolate to specified number of frames (t) using a specified method (interp_method).
# Accepted values for interp_method: ‘linear’, ‘nearest’, ‘nearest-up’, ‘zero’, ‘slinear’,
# ‘quadratic’, ‘cubic’, ‘previous’, or ‘next’
def temporal_interpolation(footstep: np.ndarray, t=101, interp_method="nearest"):
    # crop-out inactivity at beginning and end of recording
    footstep = _temporal_crop(footstep)

    # interpolate to t frames
    f = interp1d(
        np.linspace(0, 1, footstep.shape[0]), footstep, axis=0, kind=interp_method
    )
    footstep_interp = f(np.linspace(0, 1, t))

    return footstep_interp


def preprocess_footsteps(footsteps: dict[Any, np.ndarray], metadata, h=75, w=40):
    preprocessed_footsteps = []
    new_metadata_dict = collections.defaultdict(list)

    for footstep in footsteps.values():
        # rotate according to first principal component axis
        footstep_rotated, rotation_angle = spatial_rotation(footstep)
        new_metadata_dict["RotationAngle"].append(rotation_angle)

        # rotate footsteps by 180 degrees to same orientation
        footstep_flipped, orientation = spatial_flip(footstep_rotated)
        new_metadata_dict["Orientation"].append(orientation)

        # zero-pad spatially to 75 x 40 pixels
        footstep_padded = spatial_zeropad(footstep_flipped, w=w, h=h)

        # center footstep based on its extreme limits (bounding box)
        footstep_translated = spatial_translation(
            footstep_padded, alignment_method="bbox", thresh=10
        )

        # interpolate temporally to 101 frames
        footstep_norm = temporal_interpolation(footstep_translated)

        # determine side (i.e., left vs. right)
        side = classify_side(footstep_norm)
        new_metadata_dict["Side"].append(side)

        preprocessed_footsteps.append(footstep_norm)

    preprocessed_footsteps = np.stack(preprocessed_footsteps, axis=0)

    new_metadata_df = metadata.copy()
    for k, v in new_metadata_dict.items():
        new_metadata_df[k] = v

    return preprocessed_footsteps, new_metadata_df
