"""Project-wide runtime configuration for cooldown durations."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SHORT_COOLDOWN_MS = 2000
DEFAULT_LONG_COOLDOWN_MS = 10000


@dataclass(frozen=True)
class GameConfig:
    """Immutable cooldown durations shared by the engine and its real-time arbiter."""

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
        raise ValueError(f"Game configuration in {path} must be a JSON object")

    return GameConfig(
        short_cooldown_ms=_require_positive_int(data, "short_cooldown_ms", path),
        long_cooldown_ms=_require_positive_int(data, "long_cooldown_ms", path),
    )


def _require_positive_int(data: dict, field: str, path: Path) -> int:
    """Return a validated positive integer field, raising a clear error otherwise."""
    if field not in data:
        raise ValueError(f"Missing required field {field!r} in {path}")

    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Field {field!r} in {path} must be an integer, got {value!r}")
    if value <= 0:
        raise ValueError(f"Field {field!r} in {path} must be positive, got {value!r}")

    return value
