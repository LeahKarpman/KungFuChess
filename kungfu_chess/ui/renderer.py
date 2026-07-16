from __future__ import annotations

from pathlib import Path

from ..model.game_state import GameSnapshot, MotionSnapshot, PieceSnapshot
from ..model.position import Position
from .animation import clamp_progress, lerp_point
from .img import Img
from .layout import BoardLayout
from .sprite_loader import SpriteLoader

SELECTION_BORDER_COLOR = (0, 255, 255, 255)  # BGRA yellow, opaque: visible on light and dark cells
SELECTION_BORDER_THICKNESS = 3
SUPPORTED_ACTION_KINDS = frozenset({"move", "jump"})


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

        Render order is: base board, stationary pieces, moving pieces, then the
        selection border, so the border always stays visible on top and a moving
        piece is never also drawn at its logical (source) cell.
        """
        if snapshot.width != self._expected_width or snapshot.height != self._expected_height:
            raise ValueError(
                "Unsupported board dimensions for the supplied board image: "
                f"expected {self._expected_width}x{self._expected_height}, "
                f"got {snapshot.width}x{snapshot.height}"
            )

        motions_by_piece_id = self._index_motions(snapshot)

        canvas = self._get_prepared_board().copy()

        for piece in snapshot.pieces:
            if piece.id not in motions_by_piece_id:
                self._draw_stationary_piece(canvas, piece)

        for piece in snapshot.pieces:
            motion = motions_by_piece_id.get(piece.id)
            if motion is not None:
                self._draw_moving_piece(canvas, piece, motion)

        if selected is not None:
            if not (0 <= selected.row < snapshot.height and 0 <= selected.col < snapshot.width):
                raise ValueError(
                    f"Selected position {selected} is outside the "
                    f"{snapshot.width}x{snapshot.height} board."
                )
            self._draw_selection_border(canvas, selected)

        return canvas

    @staticmethod
    def _index_motions(snapshot: GameSnapshot) -> dict[str, MotionSnapshot]:
        """Map each piece_id to its motion, validating references and uniqueness."""
        piece_ids = {piece.id for piece in snapshot.pieces}
        motions_by_piece_id: dict[str, MotionSnapshot] = {}
        for motion in snapshot.motions:
            if motion.piece_id not in piece_ids:
                raise ValueError(
                    f"Motion references unknown piece_id: {motion.piece_id!r}"
                )
            if motion.piece_id in motions_by_piece_id:
                raise ValueError(
                    f"Duplicate motion for piece_id: {motion.piece_id!r}"
                )
            motions_by_piece_id[motion.piece_id] = motion
        return motions_by_piece_id

    def _draw_stationary_piece(self, canvas: Img, piece: PieceSnapshot) -> None:
        sprite = self._sprite_loader.load_idle_sprite(piece.kind, piece.color)
        sprite_height, sprite_width = sprite.img.shape[:2]
        x, y = self._layout.centered_top_left(piece.cell, sprite_width, sprite_height)
        sprite.draw_on(canvas, x, y)

    def _draw_moving_piece(
        self, canvas: Img, piece: PieceSnapshot, motion: MotionSnapshot
    ) -> None:
        if motion.action_kind not in SUPPORTED_ACTION_KINDS:
            raise ValueError(f"Unsupported action kind: {motion.action_kind!r}")

        progress = clamp_progress(motion.elapsed_ms, motion.duration_ms)
        source_center = self._layout.cell_center(motion.source)
        destination_center = self._layout.cell_center(motion.destination)
        point = lerp_point(source_center, destination_center, progress)

        sprite = self._sprite_loader.get_animation_frame(
            piece.kind, piece.color, motion.action_kind, motion.elapsed_ms
        )
        sprite_height, sprite_width = sprite.img.shape[:2]
        x, y = self._layout.centered_top_left_at_point(point, sprite_width, sprite_height)
        sprite.draw_on(canvas, x, y)

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
