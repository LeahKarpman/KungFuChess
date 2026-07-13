from __future__ import annotations
from dataclasses import dataclass
from ..model.position import Position


@dataclass(frozen=True)
class PieceSnapshot:
    id: str
    color: str
    kind: str
    cell: Position
    state: str


@dataclass(frozen=True)
class MotionSnapshot:
    piece_id: str
    source: Position
    destination: Position
    elapsed_ms: int
    duration_ms: int


@dataclass(frozen=True)
class GameSnapshot:
    pieces: tuple[PieceSnapshot, ...]
    motions: tuple[MotionSnapshot, ...]
    selected: Position | None
    game_over: bool
    width: int
    height: int
