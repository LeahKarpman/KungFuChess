from __future__ import annotations

import math


def clamp_progress(elapsed_ms: int, duration_ms: int) -> float:
    """Return elapsed_ms / duration_ms clamped to [0.0, 1.0]."""
    if duration_ms <= 0:
        raise ValueError(f"duration_ms must be positive, got {duration_ms}")

    progress = elapsed_ms / duration_ms
    return min(max(progress, 0.0), 1.0)


def lerp_point(
    source: tuple[float, float], destination: tuple[float, float], progress: float
) -> tuple[float, float]:
    """Linearly interpolate between two pixel points at the given progress."""
    source_x, source_y = source
    destination_x, destination_y = destination
    return (
        source_x + (destination_x - source_x) * progress,
        source_y + (destination_y - source_y) * progress,
    )


def select_frame_index(
    elapsed_ms: int, frames_per_sec: float, frame_count: int, is_loop: bool
) -> int:
    """Select a zero-based animation frame index from elapsed time."""
    if frames_per_sec <= 0:
        raise ValueError(f"frames_per_sec must be positive, got {frames_per_sec}")
    if frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")

    index = math.floor((elapsed_ms / 1000) * frames_per_sec)
    index = max(index, 0)

    if is_loop:
        return index % frame_count
    return min(index, frame_count - 1)
