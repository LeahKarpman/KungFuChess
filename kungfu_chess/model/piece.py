from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .position import Position


VALID_COLORS = {"w", "b"}
VALID_KINDS = {"K", "Q", "R", "B", "N", "P"}
PieceState = Literal["idle", "moving", "short_rest", "long_rest", "captured"]
VALID_STATES = {"idle", "moving", "short_rest", "long_rest", "captured"}
RESTING_STATES = {"short_rest", "long_rest"}


class Piece:
    """Represent a chess piece and its logical lifecycle state."""

    id: str
    color: str
    kind: str
    _cell: Position
    state: PieceState

    def __init__(
        self,
        id: str,
        color: str,
        kind: str,
        cell: Position,
        state: PieceState = "idle",
    ) -> None:
        if color not in VALID_COLORS:
            raise ValueError("invalid_piece_color")
        if kind not in VALID_KINDS:
            raise ValueError("invalid_piece_kind")
        if state not in VALID_STATES:
            raise ValueError("invalid_piece_state")

        self.id = id
        self.color = color
        self.kind = kind
        self._cell = cell
        self.state = state

    @property
    def cell(self) -> Position:
        """Return the piece's logical cell."""
        return self._cell

    def _set_cell(self, cell: Position) -> None:
        """Update the logical cell through a model-owned board operation."""
        self._cell = cell
