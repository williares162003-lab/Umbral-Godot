from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import numpy as np


SIZE = 2048
WORLD_SIZE_METERS = 10_000
SEED = 162003
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "terrain" / "heightmaps"


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def gaussian(
    x: np.ndarray,
    z: np.ndarray,
    center_x: float,
    center_z: float,
    width_x: float,
    width_z: float,
) -> np.ndarray:
    dx = (x - center_x) / width_x
    dz = (z - center_z) / width_z
    return np.exp(-(dx * dx + dz * dz) * 0.5)


def oriented_gaussian(
    x: np.ndarray,
    z: np.ndarray,
    center_x: float,
    center_z: float,
    long_width: float,
    short_width: float,
    angle_degrees: float,
) -> np.ndarray:
    angle = np.deg2rad(angle_degrees)
    dx = x - center_x
    dz = z - center_z
    along = dx * np.cos(angle) + dz * np.sin(angle)
    across = -dx * np.sin(angle) + dz * np.cos(angle)
    return np.exp(
        -0.5
        * (
            np.square(along / long_width)
            + np.square(across / short_width)
        )
    )


def mesa(
    x: np.ndarray,
    z: np.ndarray,
    center_x: float,
    center_z: float,
    width_x: float,
    width_z: float,
    edge_start: float = 0.82,
    phase: float = 0.0,
    distortion: np.ndarray | None = None,
) -> np.ndarray:
    local_x = (x - center_x) / width_x
    local_z = (z - center_z) / width_z
    angle = np.arctan2(local_z, local_x)
    distance = np.sqrt(
        np.square((x - center_x) / width_x)
        + np.square((z - center_z) / width_z)
    )
    outline = (
        1.0
        + 0.090 * np.sin(angle * 3.0 + phase)
        + 0.050 * np.sin(angle * 7.0 - phase * 0.7)
        + 0.025 * np.sin(angle * 11.0 + phase * 1.3)
    )
    if distortion is not None:
        outline += np.clip(distortion, -1.8, 1.8) * 0.035
    distance *= outline
    return 1.0 - smoothstep(edge_start, 1.0, distance)


def distance_to_segment(
    x: np.ndarray,
    z: np.ndarray,
    start: tuple[float, float],
    end: tuple[float, float],
) -> np.ndarray:
    ax, az = start
    bx, bz = end
    vx = bx - ax
    vz = bz - az
    length_squared = vx * vx + vz * vz
    projection = np.clip(
        ((x - ax) * vx + (z - az) * vz) / length_squared,
        0.0,
        1.0,
    )
    closest_x = ax + projection * vx
    closest_z = az + projection * vz
    return np.sqrt(np.square(x - closest_x) + np.square(z - closest_z))


def smooth_noise(rng: np.random.Generator, grid_size: int) -> np.ndarray:
    source = rng.random((grid_size, grid_size), dtype=np.float32)
    coordinates = np.linspace(0.0, grid_size - 1, SIZE, dtype=np.float32)
    lower = np.floor(coordinates).astype(np.int32)
    upper = np.minimum(lower + 1, grid_size - 1)
    blend = coordinates - lower
    horizontal = (
        source[:, lower] * (1.0 - blend)[None, :]
        + source[:, upper] * blend[None, :]
    )
    result = (
        horizontal[lower, :] * (1.0 - blend)[:, None]
        + horizontal[upper, :] * blend[:, None]
    ).astype(np.float32)
    return (result - result.mean()) / max(result.std(), 1e-6)


def write_png(path: Path, pixels: np.ndarray) -> None:
    if pixels.ndim == 2 and pixels.dtype == np.uint16:
        color_type = 0
        bit_depth = 16
        row_data = pixels.astype(">u2", copy=False)
    elif pixels.ndim == 3 and pixels.shape[2] == 3 and pixels.dtype == np.uint8:
        color_type = 2
        bit_depth = 8
        row_data = pixels
    else:
        raise ValueError("PNG supports uint16 grayscale or uint8 RGB arrays")

    height, width = pixels.shape[:2]
    raw_rows = b"".join(b"\x00" + row.tobytes() for row in row_data)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0),
    )
    png += chunk(b"IDAT", zlib.compress(raw_rows, level=6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def soften_heightmap(height: np.ndarray, passes: int = 1) -> np.ndarray:
    result = height
    for _ in range(passes):
        padded = np.pad(result, 1, mode="edge")
        result = (
            padded[:-2, :-2]
            + 2.0 * padded[:-2, 1:-1]
            + padded[:-2, 2:]
            + 2.0 * padded[1:-1, :-2]
            + 4.0 * padded[1:-1, 1:-1]
            + 2.0 * padded[1:-1, 2:]
            + padded[2:, :-2]
            + 2.0 * padded[2:, 1:-1]
            + padded[2:, 2:]
        ) / 16.0
    return result


def carve_route(
    height: np.ndarray,
    x: np.ndarray,
    z: np.ndarray,
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    target_height: float,
) -> np.ndarray:
    distance = distance_to_segment(x, z, start, end)
    blend = 1.0 - smoothstep(width * 0.35, width, distance)
    target = np.minimum(height, target_height + distance * 0.32)
    return height * (1.0 - blend) + target * blend


def build_heightmap() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    rng = np.random.default_rng(SEED)
    axis = np.linspace(-1.0, 1.0, SIZE, dtype=np.float32)
    x, z = np.meshgrid(axis, axis)

    broad_shape_noise = smooth_noise(rng, 20)
    broad_noise = broad_shape_noise * 0.014
    medium_noise = smooth_noise(rng, 64) * 0.0055
    fine_noise = smooth_noise(rng, 160) * 0.0013

    height = np.full((SIZE, SIZE), 0.245, dtype=np.float32)
    height += broad_noise + medium_noise + fine_noise
    height += oriented_gaussian(x, z, -0.18, 0.05, 0.88, 0.30, 12.0) * 0.026
    height += oriented_gaussian(x, z, 0.16, 0.42, 0.72, 0.22, -18.0) * 0.018

    # Northwest: a connected cliff country with broad grassy tops.
    west_plateau = np.maximum(
        mesa(
            x, z, -0.70, -0.30, 0.32, 0.49,
            0.84, 0.7, broad_shape_noise,
        ),
        mesa(
            x, z, -0.45, -0.50, 0.27, 0.30,
            0.83, 2.2, broad_shape_noise,
        ) * 0.86,
    )
    west_crown = mesa(
        x, z, -0.68, -0.51, 0.21, 0.24,
        0.84, 1.4, broad_shape_noise,
    )
    height += west_plateau * 0.255
    height += west_crown * 0.175
    height += oriented_gaussian(x, z, -0.73, -0.70, 0.25, 0.080, 18.0) * 0.17
    height += gaussian(x, z, -0.56, -0.76, 0.085, 0.13) * 0.19

    # Northern skyline: distinct peaks separated by readable passes.
    height += oriented_gaussian(x, z, -0.02, -0.88, 0.52, 0.12, 2.0) * 0.26
    height += gaussian(x, z, 0.22, -0.79, 0.12, 0.17) * 0.27
    height += gaussian(x, z, -0.31, -0.82, 0.14, 0.18) * 0.23
    height += gaussian(x, z, 0.48, -0.83, 0.10, 0.15) * 0.18
    height -= gaussian(x, z, -0.03, -0.82, 0.070, 0.14) * 0.15
    height -= gaussian(x, z, 0.38, -0.78, 0.065, 0.12) * 0.11

    # East: long irregular escarpments and two broad elevation levels.
    east_plateau = np.maximum(
        mesa(
            x, z, 0.68, -0.16, 0.31, 0.52,
            0.84, 2.8, broad_shape_noise,
        ),
        mesa(
            x, z, 0.55, 0.20, 0.25, 0.32,
            0.83, 4.1, broad_shape_noise,
        ) * 0.82,
    )
    east_upper = mesa(
        x, z, 0.71, -0.26, 0.21, 0.32,
        0.85, 0.3, broad_shape_noise,
    )
    east_crown = mesa(
        x, z, 0.75, -0.42, 0.13, 0.17,
        0.84, 5.2, broad_shape_noise,
    )
    height += east_plateau * 0.215
    height += east_upper * 0.145
    height += east_crown * 0.105
    height += oriented_gaussian(x, z, 0.70, 0.38, 0.34, 0.085, -18.0) * 0.10

    # Interior landmarks break the basin into layered, explorable subregions.
    central_shelf = mesa(
        x, z, -0.31, 0.06, 0.19, 0.24,
        0.83, 3.6, broad_shape_noise,
    )
    central_crown = mesa(
        x, z, -0.35, -0.01, 0.105, 0.14,
        0.84, 1.7, broad_shape_noise,
    )
    eastern_step = mesa(
        x, z, 0.29, 0.14, 0.18, 0.15,
        0.85, 4.8, broad_shape_noise,
    )
    height += central_shelf * 0.175
    height += central_crown * 0.095
    height += eastern_step * 0.095

    southeast_shelf = mesa(
        x, z, 0.66, 0.62, 0.22, 0.19,
        0.84, 2.1, broad_shape_noise,
    )
    southwest_shelf = mesa(
        x, z, -0.60, 0.60, 0.20, 0.17,
        0.84, 5.5, broad_shape_noise,
    )
    height += southeast_shelf * 0.13
    height += southwest_shelf * 0.11

    # Southwest: broken ridges frame a future forest and wetland.
    height += oriented_gaussian(x, z, -0.69, 0.54, 0.38, 0.12, 55.0) * 0.17
    height += oriented_gaussian(x, z, -0.45, 0.80, 0.32, 0.10, 16.0) * 0.13
    height -= gaussian(x, z, -0.53, 0.57, 0.24, 0.22) * 0.08

    # The central basin keeps long sight lines between the major landmarks.
    central_basin = gaussian(x, z, -0.02, 0.04, 0.56, 0.55)
    height -= central_basin * 0.052

    # A broad southern lake basin. Water is not rendered yet; this is geography.
    lake_local_x = (x + 0.09) / 0.30
    lake_local_z = (z - 0.58) / 0.17
    lake_angle = np.arctan2(lake_local_z, lake_local_x)
    lake_distance = np.sqrt(lake_local_x * lake_local_x + lake_local_z * lake_local_z)
    lake_outline = (
        1.0
        + 0.13 * np.sin(lake_angle * 3.0 + 0.4)
        + 0.06 * np.sin(lake_angle * 7.0 - 1.1)
        + np.clip(broad_shape_noise, -1.6, 1.6) * 0.035
    )
    lake_mask = 1.0 - smoothstep(0.68, 1.0, lake_distance * lake_outline)
    lake_floor = 0.105 + broad_noise * 0.08
    height = height * (1.0 - lake_mask) + np.minimum(height, lake_floor) * lake_mask

    # A winding river descends from the northern pass into the lake basin.
    river_center = (
        -0.025
        + 0.11 * np.sin((z + 0.83) * 3.8)
        + 0.035 * np.sin((z + 0.40) * 8.2)
    )
    river_distance = np.abs(x - river_center)
    river_gate = smoothstep(-0.94, -0.76, z) * (1.0 - smoothstep(0.52, 0.68, z))
    river_t = smoothstep(-0.84, 0.58, z)
    river_floor = 0.215 * (1.0 - river_t) + 0.108 * river_t
    river_target = river_floor + smoothstep(0.0, 0.125, river_distance) * 0.085
    river_corridor = (
        (1.0 - smoothstep(0.024, 0.125, river_distance))
        * river_gate
    )
    river_water_mask = (
        (1.0 - smoothstep(0.009, 0.021, river_distance))
        * river_gate
    )
    height = (
        height * (1.0 - river_corridor)
        + np.minimum(height, river_target) * river_corridor
    )

    # Broad natural passes connect the basin without looking excavated.
    height -= oriented_gaussian(
        x, z, 0.28, 0.02, 0.42, 0.075, -34.0
    ) * 0.045
    height -= oriented_gaussian(
        x, z, -0.30, -0.02, 0.36, 0.080, 31.0
    ) * 0.042
    height -= oriented_gaussian(
        x, z, 0.08, -0.37, 0.35, 0.070, 87.0
    ) * 0.040

    # A calm southeastern meadow acts as the initial scale-check area.
    spawn_x, spawn_z = 0.32, 0.66
    spawn_distance = np.sqrt(
        np.square(x - spawn_x) + np.square(z - spawn_z)
    )
    spawn_blend = 1.0 - smoothstep(0.080, 0.19, spawn_distance)
    spawn_height = 0.185 + broad_noise * 0.025
    height = height * (1.0 - spawn_blend) + spawn_height * spawn_blend

    # Keep the world edge elevated in separated masses, not a circular wall.
    height += gaussian(x, z, -0.92, -0.02, 0.12, 0.34) * 0.18
    height += gaussian(x, z, 0.93, 0.55, 0.12, 0.28) * 0.15
    height += gaussian(x, z, 0.18, 0.96, 0.42, 0.10) * 0.11

    height = np.clip(soften_heightmap(height), 0.025, 0.97)
    masks = {
        "lake": lake_mask,
        "river": river_water_mask,
        "spawn": spawn_blend,
    }
    return height, masks


def build_preview(
    height: np.ndarray,
    masks: dict[str, np.ndarray],
) -> np.ndarray:
    grad_z, grad_x = np.gradient(height)
    slope = np.sqrt(grad_x * grad_x + grad_z * grad_z)

    deep_water = np.array([28, 93, 135], dtype=np.float32)
    shallow_water = np.array([50, 137, 158], dtype=np.float32)
    lowland = np.array([70, 132, 82], dtype=np.float32)
    meadow = np.array([105, 161, 82], dtype=np.float32)
    highland = np.array([133, 164, 83], dtype=np.float32)
    cliff = np.array([117, 112, 105], dtype=np.float32)
    peak = np.array([178, 177, 166], dtype=np.float32)

    preview = np.empty((SIZE, SIZE, 3), dtype=np.float32)
    preview[:] = lowland

    meadow_mix = smoothstep(0.14, 0.30, height)[..., None]
    preview = preview * (1.0 - meadow_mix) + meadow * meadow_mix

    high_mix = smoothstep(0.34, 0.60, height)[..., None]
    preview = preview * (1.0 - high_mix) + highland * high_mix

    cliff_mix = np.maximum(
        smoothstep(0.0035, 0.014, slope),
        smoothstep(0.68, 0.86, height),
    )
    preview = (
        preview * (1.0 - cliff_mix[..., None])
        + cliff * cliff_mix[..., None]
    )

    peak_mix = smoothstep(0.82, 0.96, height)[..., None]
    preview = preview * (1.0 - peak_mix) + peak * peak_mix

    water_mask = np.maximum(masks["lake"], masks["river"])
    water_color = (
        shallow_water[None, None, :] * (1.0 - masks["lake"][..., None])
        + deep_water[None, None, :] * masks["lake"][..., None]
    )
    preview = (
        preview * (1.0 - water_mask[..., None])
        + water_color * water_mask[..., None]
    )

    shade = np.clip(1.0 - grad_x * 20.0 - grad_z * 14.0, 0.68, 1.20)
    preview *= shade[..., None]
    return np.clip(preview, 0, 255).astype(np.uint8)


def normalized_to_world(value: float) -> int:
    return round((value + 1.0) * 0.5 * WORLD_SIZE_METERS)


def write_layout_metadata() -> None:
    layout = {
        "world_size_meters": WORLD_SIZE_METERS,
        "heightmap_resolution": SIZE,
        "meters_per_vertex": WORLD_SIZE_METERS / SIZE,
        "seed": SEED,
        "landmarks": {
            "northwest_cliffs": [
                normalized_to_world(-0.68),
                normalized_to_world(-0.30),
            ],
            "northern_crown": [
                normalized_to_world(-0.06),
                normalized_to_world(-0.86),
            ],
            "eastern_mesetas": [
                normalized_to_world(0.64),
                normalized_to_world(-0.12),
            ],
            "southern_lake_basin": [
                normalized_to_world(-0.08),
                normalized_to_world(0.56),
            ],
            "spawn_meadow": [
                normalized_to_world(0.29),
                normalized_to_world(0.59),
            ],
        },
    }
    (OUTPUT_DIR / "umbral_world_layout.json").write_text(
        json.dumps(layout, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    height, masks = build_heightmap()

    height_u16 = np.round(height * 65535.0).astype(np.uint16)
    height_u16.astype("<u2").tofile(
        OUTPUT_DIR / "umbral_world_heightmap.r16"
    )
    write_png(OUTPUT_DIR / "umbral_world_heightmap.png", height_u16)
    write_png(
        OUTPUT_DIR / "umbral_world_preview.png",
        build_preview(height, masks),
    )
    write_layout_metadata()

    print(f"World size: {WORLD_SIZE_METERS} x {WORLD_SIZE_METERS} m")
    print(f"Resolution: {SIZE} x {SIZE}")
    print(f"Meters per vertex: {WORLD_SIZE_METERS / SIZE:.6f}")
    print(f"Heightmap: {height.min():.4f} .. {height.max():.4f}")
    print(f"Written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
