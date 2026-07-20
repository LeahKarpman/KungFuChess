"""Data and pure calculations describing a single timed piece action.

This module owns the shape of one in-flight action (a move or a jump)
and how long it takes to travel. It has no knowledge of the board, chess
legality, capture, promotion, game-over state, controllers, pixels,
commands, or rendering — those belong to higher layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..model.piece import Piece
from ..model.position import Position


MS_PER_CELL = 1000
ActionKind = Literal["move", "jump"]


def travel_duration_ms(
    piece_kind: str,
    source: Position,
    destination: Position,
) -> int:
    """Calculate movement duration from the piece's board-cell route.

    Knights travel their L-shaped route as the sum of the row and column
    deltas; every other piece travels the straight-line cell distance.
    """
    dr = abs(destination.row - source.row)
    dc = abs(destination.col - source.col)
    distance = dr + dc if piece_kind == "N" else max(dr, dc)
    return distance * MS_PER_CELL


@dataclass
class Motion:
    """Mutable state of one piece action currently in progress.

    Instances are owned and mutated only by RealTimeArbiter; nothing
    outside the realtime package should hold or mutate a Motion.
    """

    piece: Piece
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int = 0
    sequence: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, int):
            raise ValueError(
                f"Motion duration_ms must be an int, got {self.duration_ms!r}"
            )
        if self.duration_ms <= 0:
            raise ValueError(
                f"Motion duration_ms must be positive, got {self.duration_ms!r}"
            )

    def advance(self, ms: int) -> None:
        """Add simulated time to this motion's elapsed duration."""
        self.elapsed_ms += ms

    def remaining_ms(self) -> int:
        """Return the simulated time left before completion, floored at zero."""
        return max(self.duration_ms - self.elapsed_ms, 0)

    def is_complete(self) -> bool:
        """Return whether this motion has reached or passed its full duration."""
        return self.elapsed_ms >= self.duration_ms


@dataclass(frozen=True)
class ActiveAction:
    """Immutable external view of a currently scheduled action.

    Exposes only plain data (no Piece reference) so callers outside the
    realtime package cannot mutate the piece through this view.
    """

    piece_id: str
    piece_color: str
    piece_kind: str
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int


@dataclass(frozen=True)
class ArrivalEvent:
    """Immutable event describing a timed action that has reached its destination."""

    piece: Piece
    source: Position
    destination: Position
    action_kind: ActionKind = "move"
    leftover_ms: int = 0
