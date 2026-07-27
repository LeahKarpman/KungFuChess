from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .piece import PieceState
from .position import Position


@dataclass(frozen=True)
class PieceSnapshot:
    """Describe one piece without exposing its mutable model object."""

    id: str
    color: str
    kind: str
    cell: Position
    state: PieceState


@dataclass(frozen=True)
class MotionSnapshot:
    """Describe one active timed action for rendering and inspection."""

    piece_id: str
    source: Position
    destination: Position
    elapsed_ms: int
    duration_ms: int
    action_kind: Literal["move", "jump"] = "move"
    action_elapsed_ms: int | None = None


@dataclass(frozen=True)
class RestSnapshot:
    """Describe one active cooldown for rendering and inspection."""

    piece_id: str
    rest_kind: Literal["short_rest", "long_rest"]
    elapsed_ms: int
    duration_ms: int


@dataclass(frozen=True)
class GameSnapshot:
    """Provide an immutable view of the complete observable game state."""

    pieces: tuple[PieceSnapshot, ...]
    motions: tuple[MotionSnapshot, ...]
    game_over: bool
    width: int
    height: int
    rests: tuple[RestSnapshot, ...] = ()
