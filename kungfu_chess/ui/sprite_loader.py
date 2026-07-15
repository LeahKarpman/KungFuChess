from __future__ import annotations

from pathlib import Path

from ..model.piece import VALID_COLORS, VALID_KINDS
from .img import Img

IDLE_SPRITE_RELATIVE_PATH = Path("states") / "idle" / "sprites" / "1.png"


class SpriteLoader:
    """Load and cache idle sprites for piece kind/color combinations."""

    def __init__(self, assets_root: Path) -> None:
        self._assets_root = Path(assets_root)
        self._cache: dict[tuple[str, str], Img] = {}

    def load_idle_sprite(self, kind: str, color: str) -> Img:
        """Return the cached idle sprite for a piece kind/color, loading it on first use."""
        if kind not in VALID_KINDS:
            raise ValueError(f"Invalid piece kind: {kind!r}")
        if color not in VALID_COLORS:
            raise ValueError(f"Invalid piece color: {color!r}")

        key = (kind, color)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        directory = f"{kind}{color.upper()}"
        sprite_path = self._assets_root / directory / IDLE_SPRITE_RELATIVE_PATH
        sprite = Img().read(sprite_path)
        self._cache[key] = sprite
        return sprite
