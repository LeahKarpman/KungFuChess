"""Project-wide runtime configuration."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .realtime.rest import (
    DEFAULT_LONG_COOLDOWN_MS,
    DEFAULT_SHORT_COOLDOWN_MS,
)


@dataclass(frozen=True)
class GameConfig:
    """Immutable values shared by the engine and presentation layer."""

    piece_values: Mapping[str, int]
    short_cooldown_ms: int = DEFAULT_SHORT_COOLDOWN_MS
    long_cooldown_ms: int = DEFAULT_LONG_COOLDOWN_MS


def load_game_config(path: Path) -> GameConfig:
    """Load and validate cooldown durations from a project configuration file."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing game configuration file: {path}") from None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"Malformed game configuration JSON in {path}: {error}") from error

    if not isinstance(data, dict):
        raise TypeError(f"Game configuration in {path} must be a JSON object")

    return GameConfig(
        piece_values=_require_piece_values(data, path),
        short_cooldown_ms=_require_positive_int(data, "short_cooldown_ms", path),
        long_cooldown_ms=_require_positive_int(data, "long_cooldown_ms", path),
    )


def _require_piece_values(data: dict, path: Path) -> Mapping[str, int]:
    """Return all configured chess-piece values after strict validation."""
    field = "piece_values"
    if field not in data:
        raise ValueError(f"Missing required field {field!r} in {path}")

    values = data[field]
    if not isinstance(values, dict):
        raise TypeError(f"Field {field!r} in {path} must be a JSON object")

    required_kinds = frozenset({"P", "N", "B", "R", "Q", "K"})
    actual_kinds = set(values)
    if actual_kinds != required_kinds:
        missing = sorted(required_kinds - actual_kinds)
        extra = sorted(actual_kinds - required_kinds)
        raise ValueError(
            f"Field {field!r} in {path} must contain exactly "
            f"{sorted(required_kinds)!r}; missing={missing!r}, extra={extra!r}"
        )

    validated: dict[str, int] = {}
    for kind, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"Piece value {kind!r} in {path} must be an integer, got {value!r}"
            )
        if value < 0:
            raise ValueError(
                f"Piece value {kind!r} in {path} must be non-negative, got {value!r}"
            )
        validated[kind] = value

    return MappingProxyType(validated)


def _require_positive_int(data: dict, field: str, path: Path) -> int:
    """Return a validated positive integer field, raising a clear error otherwise."""
    if field not in data:
        raise ValueError(f"Missing required field {field!r} in {path}")

    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Field {field!r} in {path} must be an integer, got {value!r}")
    if value <= 0:
        raise ValueError(f"Field {field!r} in {path} must be positive, got {value!r}")

    return value
