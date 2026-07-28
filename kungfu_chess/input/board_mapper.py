from __future__ import annotations

from ..model.position import Position
from ..ui.layout import BoardLayout

DEFAULT_CELL_SIZE = 100


class BoardMapper:
    def __init__(
        self,
        width: int,
        height: int,
        layout: BoardLayout | None = None,
        *,
        cell_size: int = DEFAULT_CELL_SIZE,
        origin_x: int = 0,
        origin_y: int = 0,
    ) -> None:
        self._width = width
        self._height = height
        self._layout = layout or BoardLayout(
            cell_size=cell_size,
            origin_x=origin_x,
            origin_y=origin_y,
        )

    @property
    def layout(self) -> BoardLayout:
        """Return the shared geometry used for pixel mapping."""
        return self._layout

    def pixel_to_cell(self, x: int, y: int) -> Position | None:
        relative_x = x - self._layout.origin_x
        relative_y = y - self._layout.origin_y
        if relative_x < 0 or relative_y < 0:
            return None

        col = relative_x // self._layout.cell_size
        row = relative_y // self._layout.cell_size
        if 0 <= row < self._height and 0 <= col < self._width:
            return Position(row, col)
        return None
