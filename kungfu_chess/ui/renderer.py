from __future__ import annotations

from pathlib import Path

from ..model.game_state import GameSnapshot
from ..model.position import Position
from .img import Img
from .layout import BoardLayout
from .sprite_loader import SpriteLoader

SELECTION_BORDER_COLOR = (0, 255, 255, 255)  # BGRA yellow, opaque: visible on light and dark cells
SELECTION_BORDER_THICKNESS = 3


class BoardRenderer:
    """Compose one static frame from a GameSnapshot using a supplied board image.

    The supplied board image is a fixed picture of a standard board, so it can
    only represent snapshots of the exact dimensions it was drawn for.
    """

    def __init__(
        self,
        board_image_path: Path,
        sprite_loader: SpriteLoader,
        layout: BoardLayout,
        expected_width: int = 8,
        expected_height: int = 8,
    ) -> None:
        self._board_image_path = Path(board_image_path)
        self._sprite_loader = sprite_loader
        self._layout = layout
        self._expected_width = expected_width
        self._expected_height = expected_height
        self._prepared_board: Img | None = None

    def _get_prepared_board(self) -> Img:
        """Load and resize the board image once, then reuse it for every frame."""
        if self._prepared_board is None:
            pixel_size = self._layout.board_pixel_size(
                self._expected_width, self._expected_height
            )
            self._prepared_board = Img().read(self._board_image_path, size=pixel_size)
        return self._prepared_board

    def render(self, snapshot: GameSnapshot, selected: Position | None = None) -> Img:
        """Return a new Img with the board, every snapshot piece, and an optional selection border.

        The selection border is drawn last so it stays visible on top of a piece
        occupying the selected cell.
        """
        if snapshot.width != self._expected_width or snapshot.height != self._expected_height:
            raise ValueError(
                "Unsupported board dimensions for the supplied board image: "
                f"expected {self._expected_width}x{self._expected_height}, "
                f"got {snapshot.width}x{snapshot.height}"
            )

        canvas = self._get_prepared_board().copy()

        for piece in snapshot.pieces:
            sprite = self._sprite_loader.load_idle_sprite(piece.kind, piece.color)
            sprite_height, sprite_width = sprite.img.shape[:2]
            x, y = self._layout.centered_top_left(piece.cell, sprite_width, sprite_height)
            sprite.draw_on(canvas, x, y)

        if selected is not None:
            if not (0 <= selected.row < snapshot.height and 0 <= selected.col < snapshot.width):
                raise ValueError(
                    f"Selected position {selected} is outside the "
                    f"{snapshot.width}x{snapshot.height} board."
                )
            self._draw_selection_border(canvas, selected)

        return canvas

    def _draw_selection_border(self, canvas: Img, selected: Position) -> None:
        """Draw a border around selected that stays fully inside the cell."""
        left, top = self._layout.cell_top_left(selected)
        right, bottom = left + self._layout.cell_size, top + self._layout.cell_size
        inset = SELECTION_BORDER_THICKNESS
        canvas.draw_rectangle(
            (left + inset, top + inset),
            (right - inset, bottom - inset),
            SELECTION_BORDER_COLOR,
            SELECTION_BORDER_THICKNESS,
        )
