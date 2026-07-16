from __future__ import annotations

from dataclasses import dataclass

from ..model.position import Position


@dataclass(frozen=True)
class BoardLayout:
    """Compute pixel geometry for a board grid, independent of any input mapping."""

    cell_size: int
    origin_x: int = 0
    origin_y: int = 0

    def __post_init__(self) -> None:
        if self.cell_size <= 0:
            raise ValueError("invalid_cell_size")

    def board_pixel_size(self, width: int, height: int) -> tuple[int, int]:
        """Return the pixel (width, height) of a board grid of the given cell dimensions."""
        return (width * self.cell_size, height * self.cell_size)

    def cell_top_left(self, position: Position) -> tuple[int, int]:
        """Return the pixel (x, y) of the top-left corner of a logical cell."""
        x = self.origin_x + position.col * self.cell_size
        y = self.origin_y + position.row * self.cell_size
        return (x, y)

    def centered_top_left(
        self, position: Position, content_width: int, content_height: int
    ) -> tuple[int, int]:
        """Return the pixel (x, y) that centers content of the given size within a cell."""
        cell_x, cell_y = self.cell_top_left(position)
        x = cell_x + (self.cell_size - content_width) // 2
        y = cell_y + (self.cell_size - content_height) // 2
        return (x, y)

    def cell_center(self, position: Position) -> tuple[float, float]:
        """Return the unrounded pixel (x, y) center of a logical cell."""
        left, top = self.cell_top_left(position)
        half = self.cell_size / 2
        return (left + half, top + half)

    def centered_top_left_at_point(
        self, point: tuple[float, float], content_width: int, content_height: int
    ) -> tuple[int, int]:
        """Return the integer pixel (x, y) that centers content at an arbitrary point.

        Rounding happens here only, at the final drawing-coordinate boundary.
        """
        x, y = point
        return (round(x - content_width / 2), round(y - content_height / 2))
