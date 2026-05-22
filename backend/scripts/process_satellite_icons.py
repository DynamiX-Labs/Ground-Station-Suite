#!/usr/bin/env python3
"""Batch-generate transparent satellite icon masters and 64/128/256 presets."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class Component:
    """Connected foreground component metadata."""

    label: int
    area: int
    min_x: int
    min_y: int
    max_x: int
    max_y: int
    centroid_x: float
    centroid_y: float
    touches_border: bool

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.min_x, self.min_y, self.max_x + 1, self.max_y + 1)


@dataclass(frozen=True)
class ProcessResult:
    norad: str
    source: Path
    master: Path
    preset_paths: tuple[Path, ...]
    source_size: tuple[int, int]
    master_size: tuple[int, int]
    component_count: int
    selected_components: int
    foreground_ratio: float
    note: str


def iter_source_images(source_dir: Path) -> Iterable[Path]:
    for candidate in sorted(source_dir.iterdir()):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in VALID_EXTENSIONS:
            continue
        if not candidate.stem.isdigit():
            continue
        yield candidate


def _flood_fill_edge_connected(mask: np.ndarray) -> np.ndarray:
    """Return edge-connected region from a candidate background mask."""
    h, w = mask.shape
    connected = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    for x in range(w):
        if mask[0, x]:
            connected[0, x] = True
            q.append((x, 0))
        if mask[h - 1, x] and not connected[h - 1, x]:
            connected[h - 1, x] = True
            q.append((x, h - 1))

    for y in range(h):
        if mask[y, 0] and not connected[y, 0]:
            connected[y, 0] = True
            q.append((0, y))
        if mask[y, w - 1] and not connected[y, w - 1]:
            connected[y, w - 1] = True
            q.append((w - 1, y))

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not connected[ny, nx]:
                connected[ny, nx] = True
                q.append((nx, ny))

    return connected


def _background_mask_from_border(rgb: np.ndarray) -> np.ndarray:
    """Estimate likely background colors from image border statistics."""
    h, w, _ = rgb.shape
    border = np.vstack([rgb[0, :, :], rgb[h - 1, :, :], rgb[:, 0, :], rgb[:, w - 1, :]]).astype(
        np.float32
    )
    border_median = np.median(border, axis=0)

    dist = np.linalg.norm(rgb.astype(np.float32) - border_median[None, None, :], axis=2)
    border_dist = np.linalg.norm(border - border_median[None, :], axis=1)

    p90 = float(np.percentile(border_dist, 90))
    p95 = float(np.percentile(border_dist, 95))
    color_threshold = min(92.0, max(18.0, (p95 * 1.35), (p90 * 1.6)))
    background = dist <= color_threshold

    # Star-field sources have bright speckles on black; add a near-black mask.
    if float(border_median.max()) < 36.0:
        border_value = border.max(axis=1)
        dark_threshold = min(72.0, max(24.0, float(np.percentile(border_value, 99)) + 6.0))
        background |= rgb.max(axis=2).astype(np.float32) <= dark_threshold

    return background


def _background_mask_from_side_rows(rgb: np.ndarray) -> np.ndarray:
    """Estimate background from per-row side-strip colors (good for studio photos)."""
    h, w, _ = rgb.shape
    strip_w = max(6, min(48, w // 50))

    side_pixels = np.concatenate([rgb[:, :strip_w, :], rgb[:, w - strip_w :, :]], axis=1).astype(
        np.float32
    )
    row_background = np.median(side_pixels, axis=1)

    # Smooth row model to avoid hard seams from local side-strip noise.
    smooth_window = max(11, (h // 32) | 1)  # keep odd
    pad = smooth_window // 2
    padded = np.pad(row_background, ((pad, pad), (0, 0)), mode="edge")
    smoothed = np.zeros_like(row_background)
    for y in range(h):
        smoothed[y] = np.mean(padded[y : y + smooth_window], axis=0)
    row_background = smoothed

    row_dist = np.linalg.norm(rgb.astype(np.float32) - row_background[:, None, :], axis=2)
    border_dist = np.concatenate(
        [
            row_dist[:, :strip_w].reshape(-1),
            row_dist[:, w - strip_w :].reshape(-1),
            row_dist[:3, :].reshape(-1),
            row_dist[h - 3 :, :].reshape(-1),
        ]
    )
    p95 = float(np.percentile(border_dist, 95))
    p99 = float(np.percentile(border_dist, 99))
    threshold = min(128.0, max(20.0, p99 * 1.5 + 6.0, p95 * 1.8 + 4.0))
    return row_dist <= threshold


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, list[Component]]:
    """Label connected components in a boolean foreground mask."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    visited = np.zeros((h, w), dtype=bool)
    components: list[Component] = []
    label_id = 0

    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue

            label_id += 1
            q: deque[tuple[int, int]] = deque([(x, y)])
            visited[y, x] = True
            labels[y, x] = label_id

            area = 0
            min_x = max_x = x
            min_y = max_y = y
            sum_x = 0.0
            sum_y = 0.0
            touches_border = x in (0, w - 1) or y in (0, h - 1)

            while q:
                cx, cy = q.popleft()
                area += 1
                sum_x += cx
                sum_y += cy
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                if cx in (0, w - 1) or cy in (0, h - 1):
                    touches_border = True

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        labels[ny, nx] = label_id
                        q.append((nx, ny))

            components.append(
                Component(
                    label=label_id,
                    area=area,
                    min_x=min_x,
                    min_y=min_y,
                    max_x=max_x,
                    max_y=max_y,
                    centroid_x=sum_x / area,
                    centroid_y=sum_y / area,
                    touches_border=touches_border,
                )
            )

    return labels, components


def _bbox_intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (ax0 < bx1) and (bx0 < ax1) and (ay0 < by1) and (by0 < ay1)


def _select_satellite_components(components: list[Component], width: int, height: int) -> set[int]:
    """Select the probable satellite component and nearby detached parts."""
    if not components:
        return set()

    components_sorted = sorted(components, key=lambda c: c.area, reverse=True)
    primary = components_sorted[0]
    image_area = width * height

    # If the largest region looks like a big border-touching body (e.g. Earth),
    # prefer a substantial non-border object as the actual satellite.
    if primary.touches_border and (primary.area / image_area) >= 0.12:
        non_border = [
            c
            for c in components_sorted
            if not c.touches_border and c.area >= max(800, int(0.02 * image_area))
        ]
        if non_border:
            primary = non_border[0]

    margin = max(8, int(0.04 * max(width, height)))
    px0, py0, px1, py1 = primary.bbox
    expanded = (
        max(0, px0 - margin),
        max(0, py0 - margin),
        min(width, px1 + margin),
        min(height, py1 + margin),
    )
    min_fragment_area = max(48, int(primary.area * 0.001))

    selected: set[int] = {primary.label}
    for component in components_sorted[1:]:
        if component.area < min_fragment_area:
            continue
        if component.area > int(primary.area * 1.6):
            continue
        if (
            component.touches_border
            and not primary.touches_border
            and component.area > int(primary.area * 0.5)
        ):
            continue
        if _bbox_intersects(component.bbox, expanded):
            selected.add(component.label)

    return selected


def _center_fit_square(icon: Image.Image, size: int, padding_ratio: float) -> Image.Image:
    pad = max(2, int(round(size * padding_ratio)))
    max_w = max(1, size - (2 * pad))
    max_h = max(1, size - (2 * pad))
    src_w, src_h = icon.size

    scale = min(max_w / src_w, max_h / src_h)
    out_w = max(1, int(round(src_w * scale)))
    out_h = max(1, int(round(src_h * scale)))

    resized = icon.resize((out_w, out_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - out_w) // 2, (size - out_h) // 2)
    canvas.paste(resized, offset, resized)
    return canvas


def _mask_touches_border(mask: np.ndarray) -> bool:
    h, w = mask.shape
    return (
        bool(np.any(mask[0, :]))
        or bool(np.any(mask[h - 1, :]))
        or bool(np.any(mask[:, 0]))
        or bool(np.any(mask[:, w - 1]))
    )


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if xs.size == 0 or ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _mask_quality(mask: np.ndarray) -> float:
    bbox = _mask_bbox(mask)
    if bbox is None:
        return -1e9
    h, w = mask.shape
    x0, y0, x1, y1 = bbox
    area_ratio = float(np.count_nonzero(mask)) / float(h * w)
    bbox_w = float(x1 - x0) / float(w)
    bbox_h = float(y1 - y0) / float(h)
    touches_border = _mask_touches_border(mask)

    score = 0.0
    score += 2.5 if not touches_border else -2.0
    score += 1.5 if 0.01 <= area_ratio <= 0.62 else -1.5
    score += 1.0 if (bbox_w < 0.98 and bbox_h < 0.98) else -1.0
    if area_ratio > 0.82:
        score -= 4.0
    return score


def _extract_selected_mask(
    background_candidate: np.ndarray, width: int, height: int
) -> tuple[np.ndarray, np.ndarray, list[Component], set[int]] | None:
    edge_background = _flood_fill_edge_connected(background_candidate)
    foreground = ~edge_background
    label_map, components = _label_components(foreground)
    selected_labels = _select_satellite_components(components, width, height)
    if not selected_labels:
        return None
    selected_mask = np.isin(label_map, list(selected_labels))
    if not np.any(selected_mask):
        return None
    return selected_mask, label_map, components, selected_labels


def process_satellite_image(
    source_path: Path,
    source_dir: Path,
    output_dir: Path,
    sizes: list[int],
    padding_ratio: float,
    apply_changes: bool,
) -> ProcessResult:
    norad = source_path.stem
    rgba = np.asarray(Image.open(source_path).convert("RGBA"), dtype=np.uint8)
    source_h, source_w, _ = rgba.shape
    source_alpha = rgba[:, :, 3]

    if np.all(source_alpha == 255):
        primary_result = _extract_selected_mask(
            _background_mask_from_border(rgba[:, :, :3]), source_w, source_h
        )
        if primary_result is None:
            raise RuntimeError(f"{norad}: no foreground components selected")
        selected_mask, label_map, components, selected_labels = primary_result
        note = "opaque source -> border-derived background extraction"

        # Retry with row-wise side-strip modeling when the primary mask is likely over-segmented.
        primary_bbox = _mask_bbox(selected_mask)
        primary_area_ratio = float(np.count_nonzero(selected_mask)) / float(source_w * source_h)
        if primary_bbox is not None:
            x0, y0, x1, y1 = primary_bbox
            bbox_w = float(x1 - x0) / float(source_w)
            bbox_h = float(y1 - y0) / float(source_h)
            suspicious_primary = _mask_touches_border(selected_mask) and (
                primary_area_ratio > 0.42 or bbox_w > 0.98 or bbox_h > 0.98
            )
        else:
            suspicious_primary = True

        if suspicious_primary:
            side_result = _extract_selected_mask(
                _background_mask_from_side_rows(rgba[:, :, :3]), source_w, source_h
            )
            if side_result is not None:
                (
                    side_mask,
                    side_label_map,
                    side_components,
                    side_selected_labels,
                ) = side_result
                if _mask_quality(side_mask) > _mask_quality(selected_mask) + 0.35:
                    selected_mask = side_mask
                    label_map = side_label_map
                    components = side_components
                    selected_labels = side_selected_labels
                    note = "opaque source -> side-row background extraction"
    else:
        note = "alpha source -> reuse existing transparency"
        label_map, components = _label_components(source_alpha > 0)
        # For already-transparent masters, keep all visible alpha regions.
        # This avoids dropping detached solar panels/antennas from prior cutouts.
        selected_labels = {component.label for component in components}
        if not selected_labels:
            raise RuntimeError(f"{norad}: no foreground components selected")
        selected_mask = np.isin(label_map, list(selected_labels))
    ys, xs = np.where(selected_mask)
    if xs.size == 0 or ys.size == 0:
        raise RuntimeError(f"{norad}: selected mask is empty")

    left = int(xs.min())
    right = int(xs.max()) + 1
    top = int(ys.min())
    bottom = int(ys.max()) + 1

    trimmed = rgba[top:bottom, left:right].copy()
    trimmed_mask = selected_mask[top:bottom, left:right]
    trimmed[:, :, 3] = np.where(trimmed_mask, 255, 0).astype(np.uint8)
    # Keep RGB black where transparent to avoid dark/bright fringes in compositing.
    trimmed[:, :, :3][trimmed[:, :, 3] == 0] = 0

    master_image = Image.fromarray(trimmed, mode="RGBA")
    master_path = source_dir / f"{norad}.png"
    preset_paths = tuple(output_dir / str(size) / f"{norad}.png" for size in sizes)

    if apply_changes:
        master_image.save(master_path)
        for size, preset_path in zip(sizes, preset_paths, strict=True):
            preset_path.parent.mkdir(parents=True, exist_ok=True)
            _center_fit_square(master_image, size, padding_ratio).save(preset_path)

    foreground_ratio = float(np.count_nonzero(trimmed[:, :, 3])) / float(
        trimmed.shape[0] * trimmed.shape[1]
    )
    return ProcessResult(
        norad=norad,
        source=source_path,
        master=master_path,
        preset_paths=preset_paths,
        source_size=(source_w, source_h),
        master_size=(trimmed.shape[1], trimmed.shape[0]),
        component_count=len(components),
        selected_components=len(selected_labels),
        foreground_ratio=foreground_ratio,
        note=note,
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_source_dir = repo_root / "images" / "satellites" / "full"
    default_output_dir = repo_root / "images" / "satellites"

    parser = argparse.ArgumentParser(
        description=(
            "Batch-process NORAD-named satellite source images into transparent masters "
            "and 64/128/256 icon presets."
        )
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=default_source_dir,
        help=(
            "Directory containing NORAD-named source images "
            "(default: backend/images/satellites/full)."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_output_dir,
        help=(
            "Directory where the normalized masters and 64/128/256 presets are written "
            "(default: backend/images/satellites)."
        ),
    )
    parser.add_argument(
        "--norad",
        nargs="*",
        default=[],
        help="Optional NORAD IDs to process (defaults to all numeric filenames in source dir).",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[64, 128, 256],
        help="Preset icon sizes to generate.",
    )
    parser.add_argument(
        "--padding-ratio",
        type=float,
        default=0.045,
        help="Inner padding ratio when center-fitting into square presets.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N images (0 = no limit). Useful for spot checks.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write output files. Without this flag, run in dry-run mode only.",
    )
    args = parser.parse_args()

    source_dir: Path = args.source_dir.resolve()
    if not source_dir.exists():
        raise SystemExit(f"source dir does not exist: {source_dir}")
    output_dir: Path = args.output_dir.resolve()
    if not output_dir.exists():
        if args.apply:
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            raise SystemExit(f"output dir does not exist: {output_dir}")
    if any(size < 16 for size in args.sizes):
        raise SystemExit("all --sizes must be >= 16")
    if not (0.0 <= args.padding_ratio <= 0.25):
        raise SystemExit("--padding-ratio must be in [0.0, 0.25]")

    allowed_norad = {item.strip() for item in args.norad if item.strip()} if args.norad else None
    candidates = [
        path
        for path in iter_source_images(source_dir)
        if allowed_norad is None or path.stem in allowed_norad
    ]
    if args.limit > 0:
        candidates = candidates[: args.limit]

    if not candidates:
        raise SystemExit("no matching NORAD source images found")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] processing {len(candidates)} images from {source_dir} -> {output_dir}")

    successes: list[ProcessResult] = []
    failures: list[tuple[str, str]] = []

    for source in candidates:
        try:
            result = process_satellite_image(
                source_path=source,
                source_dir=source_dir,
                output_dir=output_dir,
                sizes=args.sizes,
                padding_ratio=args.padding_ratio,
                apply_changes=args.apply,
            )
            successes.append(result)
            print(
                f"[ok] {result.norad} src={result.source_size[0]}x{result.source_size[1]} "
                f"master={result.master_size[0]}x{result.master_size[1]} "
                f"components={result.selected_components}/{result.component_count} "
                f"fg={result.foreground_ratio:.3f} note={result.note}"
            )
        except Exception as exc:  # noqa: BLE001 - batch mode should continue per-image.
            failures.append((source.stem, str(exc)))
            print(f"[fail] {source.stem} {exc}")

    print("")
    print(f"Done. ok={len(successes)} fail={len(failures)} mode={mode}")
    if not args.apply:
        print("Dry-run only: no files were written. Re-run with --apply to persist outputs.")

    if failures:
        print("Failures:")
        for norad, message in failures:
            print(f"  - {norad}: {message}")


if __name__ == "__main__":
    main()
