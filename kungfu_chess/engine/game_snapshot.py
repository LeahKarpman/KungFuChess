from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from ..model.piece import PieceState
from ..model.position import Position


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


@dataclass(frozen=True)
class GameSnapshot:
    """Provide an immutable view of the complete observable game state."""

    pieces: tuple[PieceSnapshot, ...]
    motions: tuple[MotionSnapshot, ...]
    selected: Position | None
    game_over: bool
    width: int
    height: int
