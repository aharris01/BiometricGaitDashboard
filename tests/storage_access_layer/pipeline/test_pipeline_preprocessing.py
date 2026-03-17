import warnings

import numpy as np
import pandas as pd
import pytest

import backend.storage_access_layer.pipeline.utils.preprocess_footsteps as preprocess_module
from backend.storage_access_layer.pipeline.utils.preprocess_footsteps import (
    _spatial_crop,
    _temporal_crop,
    classify_side,
    crop_image,
    preprocess_footsteps,
    spatial_flip,
    spatial_rotation,
    spatial_translation,
    spatial_zeropad,
    temporal_interpolation,
)

pytestmark = pytest.mark.unit


def _make_block_footstep(
    *,
    frames=4,
    height=8,
    width=8,
    frame_slice=slice(1, 3),
    row_slice=slice(2, 5),
    col_slice=slice(3, 6),
    value=20.0,
):
    footstep = np.zeros((frames, height, width), dtype=float)
    footstep[frame_slice, row_slice, col_slice] = value
    return footstep


def _active_bbox_center(img, thresh=10):
    rows, cols = np.where(img > thresh)
    return rows.mean(), cols.mean()


class TestCroppingHelpers:
    def test_spatial_crop_reduces_to_active_bbox(self):
        footstep = _make_block_footstep(
            frames=3,
            height=7,
            width=9,
            frame_slice=slice(0, 3),
            row_slice=slice(2, 5),
            col_slice=slice(4, 8),
        )

        cropped = _spatial_crop(footstep)

        assert cropped.shape == (3, 3, 4)
        assert np.all(cropped == 20)

    def test_temporal_crop_removes_inactive_frames_at_both_ends(self):
        footstep = _make_block_footstep(
            frames=6,
            height=5,
            width=5,
            frame_slice=slice(2, 4),
            row_slice=slice(1, 4),
            col_slice=slice(1, 4),
        )

        cropped = _temporal_crop(footstep)

        assert cropped.shape == (2, 5, 5)
        assert np.all(cropped.max(axis=(1, 2)) == 20)

    def test_crop_image_reduces_2d_image_to_active_region(self):
        img = np.zeros((6, 7), dtype=float)
        img[1:4, 2:6] = 1

        cropped = crop_image(img)

        assert cropped.shape == (3, 4)
        assert np.all(cropped == 1)


class TestSpatialFlip:
    def test_spatial_flip_handles_zero_sum_frames_without_runtime_warning(self):
        footstep = np.zeros((4, 5, 4), dtype=float)
        footstep[1:3, 4, 1:3] = 20
        footstep[2:4, 0, 1:3] = 20

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            flipped, orientation = spatial_flip(footstep)

        assert caught == []
        assert flipped.shape == footstep.shape
        assert isinstance(orientation, bool)

    def test_spatial_flip_rotates_when_later_frames_have_lower_contact(self):
        footstep = np.zeros((4, 5, 4), dtype=float)
        footstep[0:2, 0, 1:3] = 20
        footstep[2:4, 4, 1:3] = 20

        flipped, orientation = spatial_flip(footstep)

        assert orientation is True
        assert np.array_equal(flipped, np.flip(footstep, axis=(1, 2)))

    def test_spatial_flip_leaves_upright_footstep_unchanged(self):
        footstep = np.zeros((4, 5, 4), dtype=float)
        footstep[0:2, 4, 1:3] = 20
        footstep[2:4, 0, 1:3] = 20

        flipped, orientation = spatial_flip(footstep)

        assert orientation is False
        assert np.array_equal(flipped, footstep)


class TestSpatialRotation:
    def test_spatial_rotation_uses_pca_angle_and_preserves_nonzero_data(
        self, monkeypatch
    ):
        class DummyPCA:
            def __init__(self, n_components):
                assert n_components == 2
                self.components_ = np.array([[0.0, 1.0], [1.0, 0.0]])

        monkeypatch.setattr(preprocess_module, "PCA", DummyPCA)

        footstep = _make_block_footstep(
            frames=3,
            height=7,
            width=5,
            frame_slice=slice(0, 3),
            row_slice=slice(2, 5),
            col_slice=slice(1, 4),
        )

        rotated, angle = spatial_rotation(footstep)

        assert angle == pytest.approx(-90.0)
        assert rotated.shape[0] == footstep.shape[0]
        assert np.count_nonzero(rotated) > 0


class TestSpatialTranslation:
    @pytest.mark.parametrize("alignment_method", ["mass", "area", "bbox"])
    def test_spatial_translation_preserves_shape_and_repositions_active_region(
        self, alignment_method
    ):
        footstep = _make_block_footstep(
            frames=2,
            height=12,
            width=12,
            frame_slice=slice(0, 2),
            row_slice=slice(3, 6),
            col_slice=slice(2, 5),
        )

        before_peak = footstep.max(axis=0)
        before_center = _active_bbox_center(before_peak)

        translated = spatial_translation(
            footstep, alignment_method=alignment_method, thresh=10
        )
        after_peak = translated.max(axis=0)
        after_center = _active_bbox_center(after_peak)

        assert translated.shape == footstep.shape
        assert np.count_nonzero(translated) == np.count_nonzero(footstep)
        assert after_center != before_center


class TestSpatialZeroPad:
    def test_spatial_zeropad_returns_requested_shape_with_centered_content(self):
        footstep = np.ones((2, 2, 3), dtype=float)

        padded = spatial_zeropad(footstep, h=6, w=7)

        expected = np.zeros((2, 6, 7), dtype=float)
        expected[:, 2:4, 2:5] = 1

        assert padded.shape == (2, 6, 7)
        assert np.array_equal(padded, expected)


class TestClassifySide:
    def test_classify_side_returns_true_for_left_pattern(self):
        footstep = np.zeros((3, 6, 6), dtype=float)
        footstep[:, 0:2, 3:6] = 20
        footstep[:, 2:6, 0:3] = 20

        assert classify_side(footstep) is True

    def test_classify_side_returns_false_for_right_pattern(self):
        footstep = np.zeros((3, 6, 6), dtype=float)
        footstep[:, 0:2, 0:3] = 20
        footstep[:, 2:6, 3:6] = 20

        assert classify_side(footstep) is False


class TestTemporalInterpolation:
    def test_temporal_interpolation_crops_inactive_frames_before_resampling(self):
        footstep = _make_block_footstep(
            frames=5,
            height=4,
            width=4,
            frame_slice=slice(1, 4),
            row_slice=slice(1, 3),
            col_slice=slice(1, 3),
        )

        interpolated = temporal_interpolation(footstep, t=7, interp_method="nearest")

        expected_frame = np.zeros((4, 4), dtype=float)
        expected_frame[1:3, 1:3] = 20

        assert interpolated.shape == (7, 4, 4)
        assert np.all(interpolated == expected_frame)


class TestPreprocessFootsteps:
    def test_preprocess_footsteps_returns_normalized_stack_and_augmented_metadata(
        self, monkeypatch
    ):
        def fake_spatial_rotation(footstep):
            return footstep, float(footstep.max())

        monkeypatch.setattr(
            preprocess_module, "spatial_rotation", fake_spatial_rotation
        )

        left_step = np.zeros((4, 8, 8), dtype=float)
        left_step[1:3, 1:3, 4:7] = 20
        left_step[1:3, 3:5, 1:4] = 20

        right_step = np.zeros((4, 8, 8), dtype=float)
        right_step[1:3, 1:3, 1:4] = 30
        right_step[1:3, 3:5, 4:7] = 30

        footsteps = {"left": left_step, "right": right_step}
        metadata = pd.DataFrame({"FootstepID": [10, 11], "Label": ["L", "R"]})

        processed, new_metadata = preprocess_footsteps(footsteps, metadata, h=12, w=10)

        assert processed.shape == (2, 101, 12, 10)
        assert list(new_metadata["FootstepID"]) == [10, 11]
        assert list(new_metadata["Label"]) == ["L", "R"]
        assert list(new_metadata["RotationAngle"]) == [20.0, 30.0]
        assert len(new_metadata["Orientation"]) == 2
        assert len(new_metadata["Side"]) == 2
        assert all(
            isinstance(value, (bool, np.bool_))
            for value in new_metadata["Orientation"].tolist()
        )
        assert all(
            isinstance(value, (bool, np.bool_))
            for value in new_metadata["Side"].tolist()
        )

        assert "RotationAngle" not in metadata.columns
        assert np.count_nonzero(processed[0]) > 0
        assert np.count_nonzero(processed[1]) > 0
