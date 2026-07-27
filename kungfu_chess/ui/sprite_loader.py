from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..model.piece import VALID_COLORS, VALID_KINDS
from .animation import select_frame_index
from .img import Img

IDLE_SPRITE_RELATIVE_PATH = Path("states") / "idle" / "sprites" / "1.png"
STATES_DIRECTORY_NAME = "states"
SPRITES_DIRECTORY_NAME = "sprites"
CONFIG_FILE_NAME = "config.json"


@dataclass(frozen=True)
class _AnimationConfig:
    """Cached graphical metadata and numerically sorted frame paths for one state."""

    frames_per_sec: float
    is_loop: bool
    frame_paths: tuple[Path, ...]


class SpriteLoader:
    """Load and cache idle and animated sprites for piece kind/color combinations."""

    def __init__(
        self,
        assets_root: Path,
        image_factory: Callable[[], Img] = Img,
        frame_selector: Callable[[int, float, int, bool], int] = select_frame_index,
    ) -> None:
        self._assets_root = Path(assets_root)
        self._image_factory = image_factory
        self._frame_selector = frame_selector
        self._idle_cache: dict[tuple[str, str], Img] = {}
        self._animation_config_cache: dict[tuple[str, str, str], _AnimationConfig] = {}
        self._animation_frame_cache: dict[tuple[str, str, str, int], Img] = {}

    def load_idle_sprite(self, kind: str, color: str) -> Img:
        """Return the cached idle sprite for a piece kind/color, loading it on first use."""
        self._validate_kind_and_color(kind, color)

        key = (kind, color)
        cached = self._idle_cache.get(key)
        if cached is not None:
            return cached

        sprite_path = self._piece_directory(kind, color) / IDLE_SPRITE_RELATIVE_PATH
        sprite = self._image_factory().read(sprite_path)
        self._idle_cache[key] = sprite
        return sprite

    def get_animation_frame(self, kind: str, color: str, state: str, elapsed_ms: int) -> Img:
        """Return the cached animation frame of kind/color/state for elapsed_ms."""
        self._validate_kind_and_color(kind, color)

        config = self._get_animation_config(kind, color, state)
        frame_index = self._frame_selector(
            elapsed_ms, config.frames_per_sec, len(config.frame_paths), config.is_loop
        )

        cache_key = (kind, color, state, frame_index)
        cached = self._animation_frame_cache.get(cache_key)
        if cached is not None:
            return cached

        frame = self._image_factory().read(config.frame_paths[frame_index])
        self._animation_frame_cache[cache_key] = frame
        return frame

    @staticmethod
    def _validate_kind_and_color(kind: str, color: str) -> None:
        if kind not in VALID_KINDS:
            raise ValueError(f"Invalid piece kind: {kind!r}")
        if color not in VALID_COLORS:
            raise ValueError(f"Invalid piece color: {color!r}")

    def _piece_directory(self, kind: str, color: str) -> Path:
        return self._assets_root / f"{kind}{color.upper()}"

    def _get_animation_config(self, kind: str, color: str, state: str) -> _AnimationConfig:
        cache_key = (kind, color, state)
        cached = self._animation_config_cache.get(cache_key)
        if cached is not None:
            return cached

        state_dir = self._piece_directory(kind, color) / STATES_DIRECTORY_NAME / state
        config = self._load_animation_config(state_dir)
        self._animation_config_cache[cache_key] = config
        return config

    @staticmethod
    def _load_animation_config(state_dir: Path) -> _AnimationConfig:
        config_path = state_dir / CONFIG_FILE_NAME
        try:
            raw_text = config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Missing animation config file: {config_path}"
            ) from None

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Malformed animation config JSON in {config_path}: {error}"
            ) from error

        graphics = data.get("graphics") if isinstance(data, dict) else None
        if not isinstance(graphics, dict) or "frames_per_sec" not in graphics or "is_loop" not in graphics:
            raise ValueError(f"Missing 'graphics' metadata in {config_path}")

        frames_per_sec = graphics["frames_per_sec"]
        if (
            isinstance(frames_per_sec, bool)
            or not isinstance(frames_per_sec, (int, float))
            or (
                isinstance(frames_per_sec, float)
                and not math.isfinite(frames_per_sec)
            )
            or frames_per_sec <= 0
        ):
            raise ValueError(
                f"'frames_per_sec' must be a positive number in {config_path}, "
                f"got {frames_per_sec!r}"
            )

        is_loop = graphics["is_loop"]
        if not isinstance(is_loop, bool):
            raise TypeError(
                f"'is_loop' must be a boolean in {config_path}, got {is_loop!r}"
            )

        sprites_dir = state_dir / SPRITES_DIRECTORY_NAME
        frame_paths = SpriteLoader._sorted_frame_paths(sprites_dir)
        if not frame_paths:
            raise FileNotFoundError(f"No sprite frames found in {sprites_dir}")

        return _AnimationConfig(
            frames_per_sec=frames_per_sec, is_loop=is_loop, frame_paths=frame_paths
        )

    @staticmethod
    def _sorted_frame_paths(sprites_dir: Path) -> tuple[Path, ...]:
        """Return sprite frame paths sorted by their numeric filename stem."""
        paths = list(sprites_dir.glob("*.png"))
        return tuple(sorted(paths, key=lambda path: int(path.stem)))
