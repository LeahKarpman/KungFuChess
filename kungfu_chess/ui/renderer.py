from __future__ import annotations

from pathlib import Path

from ..model.game_state import GameSnapshot
from .img import Img
from .layout import BoardLayout
from .sprite_loader import SpriteLoader


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

    def render(self, snapshot: GameSnapshot) -> Img:
        """Return a new Img with the board and every snapshot piece drawn on it."""
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

        return canvas
