from __future__ import annotations
from ..model.position import Position

DEFAULT_CELL_SIZE = 100


class BoardMapper:
    def __init__(
        self,
        width: int,
        height: int,
        cell_size: int = DEFAULT_CELL_SIZE,
        origin_x: int = 0,
        origin_y: int = 0,
    ) -> None:
        if cell_size <= 0:
            raise ValueError("invalid_cell_size")
        self._width = width
        self._height = height
        self._cell_size = cell_size
        self._origin_x = origin_x
        self._origin_y = origin_y

    def pixel_to_cell(self, x: int, y: int) -> Position | None:
        relative_x = x - self._origin_x
        relative_y = y - self._origin_y
        if relative_x < 0 or relative_y < 0:
            return None

        col = relative_x // self._cell_size
        row = relative_y // self._cell_size
        if 0 <= row < self._height and 0 <= col < self._width:
            return Position(row, col)
        return None
