from __future__ import annotations
from .piece import Piece
from .position import Position


class Board:
    """Store settled pieces within fixed logical board dimensions."""

    width: int
    height: int
    _cells: dict[Position, Piece]

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._cells = {}

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.height and 0 <= pos.col < self.width

    def add_piece(self, piece: Piece) -> None:
        """Place a piece in an unoccupied in-bounds cell."""
        if not self.in_bounds(piece.cell):
            raise ValueError("piece_out_of_bounds")
        if piece.cell in self._cells:
            raise ValueError(f"Cell {piece.cell} is already occupied")
        if any(existing.id == piece.id for existing in self._cells.values()):
            raise ValueError("duplicate_piece_id")
        self._cells[piece.cell] = piece

    def remove_piece(self, pos: Position) -> None:
        self._cells.pop(pos, None)

    def get_piece(self, pos: Position) -> Piece | None:
        return self._cells.get(pos)

    def all_pieces(self) -> tuple[Piece, ...]:
        """Return the pieces currently occupying board cells."""
        return tuple(self._cells.values())
