"""Data describing one piece's cooldown after a completed move or jump.

This module owns the shape of one in-progress rest and how long it lasts.
It has no knowledge of the board, chess legality, capture, promotion,
game-over state, controllers, pixels, commands, or rendering — those
belong to higher layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..model.piece import Piece

DEFAULT_SHORT_COOLDOWN_MS = 2000
DEFAULT_LONG_COOLDOWN_MS = 10000

RestKind = Literal["short_rest", "long_rest"]


@dataclass
class Rest:
    """Mutable state of one piece's cooldown currently in progress.

    Instances are owned and mutated only by RealTimeArbiter; nothing
    outside the realtime package should hold or mutate a Rest.
    """

    piece: Piece
    rest_kind: RestKind
    duration_ms: int
    elapsed_ms: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, int):
            raise ValueError(
                f"Rest duration_ms must be an int, got {self.duration_ms!r}"
            )
        if self.duration_ms <= 0:
            raise ValueError(
                f"Rest duration_ms must be positive, got {self.duration_ms!r}"
            )

    def advance(self, ms: int) -> None:
        """Add simulated time to this rest's elapsed duration."""
        self.elapsed_ms += ms

    def remaining_ms(self) -> int:
        """Return the simulated time left before completion, floored at zero."""
        return max(self.duration_ms - self.elapsed_ms, 0)

    def is_complete(self) -> bool:
        """Return whether this rest has reached or passed its full duration."""
        return self.elapsed_ms >= self.duration_ms


@dataclass(frozen=True)
class ActiveRest:
    """Immutable external view of a currently active cooldown.

    Exposes only plain data (no Piece reference) so callers outside the
    realtime package cannot mutate the piece through this view.
    """

    piece_id: str
    rest_kind: RestKind
    duration_ms: int
    elapsed_ms: int
