#!/usr/bin/env python3
"""Render a spherical planet icon from an equirectangular texture."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

# Source planetary mosaics are often very large GeoTIFFs.
Image.MAX_IMAGE_PIXELS = None


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm <= 1e-9:
        return vec
    return vec / norm


def _bilinear_sample(texture: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Sample RGB texture with bilinear filtering; wraps U and clamps V."""
    height, width, _ = texture.shape

    x = (u % 1.0) * (width - 1)
    y = np.clip(v, 0.0, 1.0) * (height - 1)

    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = (x0 + 1) % width
    y1 = np.clip(y0 + 1, 0, height - 1)

    wx = x - x0
    wy = y - y0

    c00 = texture[y0, x0]
    c10 = texture[y0, x1]
    c01 = texture[y1, x0]
    c11 = texture[y1, x1]

    top = c00 * (1.0 - wx[..., None]) + c10 * wx[..., None]
    bottom = c01 * (1.0 - wx[..., None]) + c11 * wx[..., None]
    return top * (1.0 - wy[..., None]) + bottom * wy[..., None]


def render_planet_icon(
    texture_path: Path,
    output_path: Path,
    size: int,
    rotation_deg: float,
    finish: str,
) -> None:
    texture_image = Image.open(texture_path).convert("RGB")
    texture = np.asarray(texture_image, dtype=np.float32)

    output = np.zeros((size, size, 4), dtype=np.uint8)
    cx = (size - 1) * 0.5
    cy = (size - 1) * 0.5
    # Edge-to-edge fit: use nearly half-canvas radius so the sphere touches image bounds.
    radius = (size - 1) * 0.5

    yy, xx = np.meshgrid(
        np.arange(size, dtype=np.float32), np.arange(size, dtype=np.float32), indexing="ij"
    )
    nx = (xx - cx) / radius
    ny = (cy - yy) / radius
    r2 = nx * nx + ny * ny
    mask = r2 <= 1.0

    nz = np.zeros_like(nx)
    nz[mask] = np.sqrt(1.0 - r2[mask])

    # Camera looks at +Z, longitude 0 in the middle. Apply user rotation.
    rotation = math.radians(rotation_deg)
    lon = np.arctan2(nx, nz) + rotation
    lat = np.arcsin(np.clip(ny, -1.0, 1.0))

    u = (lon / (2.0 * math.pi) + 0.5) % 1.0
    v = 0.5 - (lat / math.pi)
    tex_color = _bilinear_sample(texture, u, v)

    normal = np.stack([nx, ny, nz], axis=-1)
    light_dir = _normalize(np.array([-0.42, 0.32, 0.85], dtype=np.float32))
    view_dir = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    n_dot_l = np.clip(np.sum(normal * light_dir, axis=-1), 0.0, 1.0)

    finish_name = str(finish).strip().lower()
    if finish_name == "matte":
        ambient = 0.34
        diffuse = 0.66 * n_dot_l
        shade = ambient + diffuse
        specular = np.zeros_like(n_dot_l)
        rim = np.power(np.clip(1.0 - nz, 0.0, 1.0), 2.3) * 0.03
    elif finish_name == "none":
        ambient = 0.28
        diffuse = 0.72 * n_dot_l
        shade = ambient + diffuse
        specular = np.zeros_like(n_dot_l)
        rim = np.zeros_like(n_dot_l)
    elif finish_name == "glossy":
        ambient = 0.22
        diffuse = 0.70 * n_dot_l
        shade = ambient + diffuse
        half_vec = _normalize(light_dir + view_dir)
        n_dot_h = np.clip(np.sum(normal * half_vec, axis=-1), 0.0, 1.0)
        specular = np.power(n_dot_h, 64.0) * 0.42
        rim = np.power(np.clip(1.0 - nz, 0.0, 1.0), 2.0) * 0.13
    else:
        # balanced
        ambient = 0.26
        diffuse = 0.74 * n_dot_l
        shade = ambient + diffuse
        half_vec = _normalize(light_dir + view_dir)
        n_dot_h = np.clip(np.sum(normal * half_vec, axis=-1), 0.0, 1.0)
        specular = np.power(n_dot_h, 48.0) * 0.32
        rim = np.power(np.clip(1.0 - nz, 0.0, 1.0), 2.1) * 0.11

    lit_rgb = tex_color * shade[..., None] + (specular[..., None] * 255.0) + (rim[..., None] * 28.0)
    lit_rgb = np.clip(lit_rgb, 0.0, 255.0)

    # Anti-aliased edge alpha.
    edge_softness = 0.018
    edge_alpha = np.clip((1.0 - np.sqrt(np.clip(r2, 0.0, 1.0))) / edge_softness, 0.0, 1.0)
    alpha = np.where(mask, edge_alpha, 0.0)

    output[..., :3] = lit_rgb.astype(np.uint8)
    output[..., 3] = (alpha * 255.0).astype(np.uint8)

    rendered = Image.fromarray(output, mode="RGBA")
    alpha_channel = rendered.split()[-1]
    bbox = alpha_channel.getbbox()
    if bbox:
        # Slight overfit removes any 1px transparent halo while preserving soft edges.
        cropped = rendered.crop(bbox)
        grown = cropped.resize((size + 2, size + 2), Image.Resampling.LANCZOS)
        rendered = grown.crop((1, 1, 1 + size, 1 + size))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a spherical icon from an equirectangular planet texture."
    )
    parser.add_argument(
        "--texture", required=True, type=Path, help="Input equirectangular texture path."
    )
    parser.add_argument("--output", required=True, type=Path, help="Output icon PNG path.")
    parser.add_argument("--size", default=512, type=int, help="Output icon size in pixels.")
    parser.add_argument(
        "--rotation-deg",
        default=-24.0,
        type=float,
        help="Longitude rotation in degrees (negative rotates map left).",
    )
    parser.add_argument(
        "--finish",
        default="balanced",
        choices=["matte", "balanced", "glossy", "none"],
        help="Surface shading finish.",
    )
    args = parser.parse_args()

    if args.size < 64:
        raise SystemExit("size must be >= 64")
    if not args.texture.exists():
        raise SystemExit(f"texture does not exist: {args.texture}")

    render_planet_icon(
        texture_path=args.texture,
        output_path=args.output,
        size=args.size,
        rotation_deg=args.rotation_deg,
        finish=args.finish,
    )


if __name__ == "__main__":
    main()
