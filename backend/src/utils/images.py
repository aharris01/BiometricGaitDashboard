from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import plotly.express as px
from PIL import Image


@dataclass(frozen=True)
class ImageBytes:
    data: bytes
    mimetype: str


def _normalize_to_0_1(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    mn = float(arr.min())
    mx = float(arr.max())
    if mx <= mn:
        return np.zeros_like(arr, dtype=np.float32)
    return (arr - mn) / (mx - mn)


def _plotly_color_to_rgb(color: str) -> np.ndarray:
    color = color.strip()
    if color.startswith("#"):
        h = color.lstrip("#")
        return np.array(
            [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)],
            dtype=np.float32,
        )
    if color.startswith("rgb"):
        nums = color[color.find("(") + 1 : color.find(")")]
        r, g, b = map(float, nums.split(","))
        return np.array([r, g, b], dtype=np.float32)
    raise ValueError(f"Unsupported color format: {color}")


def _build_jet_lut_256() -> np.ndarray:
    cmap = px.colors.sequential.Jet.copy()
    cmap[0] = "#000000"

    base = np.array([_plotly_color_to_rgb(c) for c in cmap], dtype=np.float32)

    x = np.linspace(0.0, 1.0, len(base))
    xi = np.linspace(0.0, 1.0, 256)

    lut = np.stack([np.interp(xi, x, base[:, ch]) for ch in range(3)], axis=1)
    return np.clip(lut, 0, 255).astype(np.uint8)


# Build once at import
JET_LUT_256 = _build_jet_lut_256()


def _p100_to_rgb(p100: np.ndarray) -> np.ndarray:
    norm = _normalize_to_0_1(p100)
    idx = np.clip((norm * 255.0).round(), 0, 255).astype(np.uint8)
    return JET_LUT_256[idx]


def create_image_bytes(
    p100: np.ndarray,
    *,
    thumb_scale: int = 6,
    webp_quality: int = 85,
) -> ImageBytes:
    """
    Always returns:
      - Thumbnail
      - WEBP format
      - Jet colormap with black at 0
    """

    if p100 is None:
        raise ValueError("p100 cannot be None")

    arr = np.asarray(p100, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"p100 must be 2D, got shape={arr.shape}")

    rgb = _p100_to_rgb(arr)

    img = Image.fromarray(rgb, mode="RGB")

    # Upscale thumbnail using NEAREST to avoid blur
    if thumb_scale > 1:
        img = img.resize(
            (img.width * thumb_scale, img.height * thumb_scale),
            resample=Image.Resampling.NEAREST,
        )

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=webp_quality, method=6)

    return ImageBytes(
        data=buf.getvalue(),
        mimetype="image/webp",
    )
