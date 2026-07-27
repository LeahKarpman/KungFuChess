"""Immutable events describing what happened during a game update.

Each event is a minimal, explicit fact about a state transition — never a
command, a UI concern, or mutable internal state. GameEngine is the sole
producer; everything else only observes the stream through
GameEngine.consume_events().
"""
from __future__ import annotations

from dataclasses import dataclass

from .position import Position


@dataclass(frozen=True)
class MoveStarted:
    """A move was scheduled and its piece began moving."""

    piece_id: str
    source: Position
    destination: Position


@dataclass(frozen=True)
class MoveCompleted:
    """A move's piece arrived and settled at its destination.

    piece_kind reflects the piece before any promotion this same arrival
    triggers; a promoting pawn still reads "P" here — PiecePromoted carries
    the resulting kind separately.
    """

    piece_id: str
    piece_kind: str
    piece_color: str
    source: Position
    destination: Position


@dataclass(frozen=True)
class JumpStarted:
    """A jump was scheduled and its piece began jumping."""

    piece_id: str
    source: Position
    destination: Position


@dataclass(frozen=True)
class JumpCompleted:
    """A jump's piece landed and settled at its destination."""

    piece_id: str
    piece_kind: str
    piece_color: str
    source: Position
    destination: Position


@dataclass(frozen=True)
class PieceCaptured:
    """One piece removed another piece from the board.

    Captured kind/color and capturing color are read from the live pieces at
    the moment of capture, not derived from either id — a promoted pawn keeps
    its original id but reports its current kind (e.g. "Q").
    """

    captured_piece_id: str
    captured_piece_kind: str
    captured_piece_color: str
    by_piece_id: str
    by_piece_color: str
    position: Position


@dataclass(frozen=True)
class PiecePromoted:
    """A pawn reached its last row and changed kind."""

    piece_id: str
    new_kind: str


@dataclass(frozen=True)
class RestStarted:
    """A piece began its post-action cooldown."""

    piece_id: str
    rest_kind: str
    duration_ms: int


@dataclass(frozen=True)
class RestCompleted:
    """A piece's cooldown finished and it returned to idle."""

    piece_id: str


@dataclass(frozen=True)
class GameOver:
    """A king was captured and the game ended."""

    winner_color: str


GameEvent = (
    MoveStarted
    | MoveCompleted
    | JumpStarted
    | JumpCompleted
    | PieceCaptured
    | PiecePromoted
    | RestStarted
    | RestCompleted
    | GameOver
)
