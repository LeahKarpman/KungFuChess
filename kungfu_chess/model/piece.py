from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .position import Position


VALID_COLORS = {"w", "b"}
VALID_KINDS = {"K", "Q", "R", "B", "N", "P"}
PieceState = Literal["idle", "moving", "captured"]


class Piece:
    """Represent a chess piece and its logical lifecycle state."""

    id: str
    color: str
    kind: str
    cell: Position
    state: PieceState

    def __init__(
        self,
        id: str,
        color: str,
        kind: str,
        cell: Position,
        state: PieceState = "idle",
    ) -> None:
        self.id = id
        self.color = color
        self.kind = kind
        self.cell = cell
        self.state = state
