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
        self.place_piece(piece, piece.cell)

    def place_piece(self, piece: Piece, position: Position) -> None:
        """Place a settled piece and synchronize its logical cell."""
        if not self.in_bounds(position):
            raise ValueError("piece_out_of_bounds")
        if position in self._cells:
            raise ValueError(f"Cell {position} is already occupied")
        if any(existing.id == piece.id for existing in self._cells.values()):
            raise ValueError("duplicate_piece_id")
        piece._set_cell(position)
        self._cells[position] = piece

    def move_piece(self, source: Position, destination: Position) -> Piece:
        """Move one settled piece between unoccupied in-bounds cells."""
        if not self.in_bounds(source):
            raise ValueError("source_out_of_bounds")
        if not self.in_bounds(destination):
            raise ValueError("destination_out_of_bounds")

        piece = self._cells.get(source)
        if piece is None:
            raise ValueError("no_piece_at_source")
        if destination in self._cells:
            raise ValueError("destination_occupied")

        del self._cells[source]
        piece._set_cell(destination)
        self._cells[destination] = piece
        return piece

    def remove_piece(self, pos: Position) -> None:
        self._cells.pop(pos, None)

    def get_piece(self, pos: Position) -> Piece | None:
        return self._cells.get(pos)

    def all_pieces(self) -> tuple[Piece, ...]:
        """Return the pieces currently occupying board cells."""
        return tuple(self._cells.values())
