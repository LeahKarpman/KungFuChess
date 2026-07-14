from __future__ import annotations
from ..model.position import Position

CELL_SIZE = 100


class BoardMapper:
    def __init__(self, width: int, height: int, cell_size: int = CELL_SIZE) -> None:
        if cell_size <= 0:
            raise ValueError("invalid_cell_size")
        self._width = width
        self._height = height
        self._cell_size = cell_size

    def pixel_to_cell(self, x: int, y: int) -> Position | None:
        col = x // self._cell_size
        row = y // self._cell_size
        if 0 <= row < self._height and 0 <= col < self._width:
            return Position(row, col)
        return None
