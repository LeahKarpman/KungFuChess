from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..model.game_state import GameSnapshot, MotionSnapshot, PieceSnapshot, RestSnapshot
from ..model.position import Position
from .animation import clamp_progress, lerp_point
from .img import Img
from .layout import BoardLayout
from .presentation import GamePresentationSnapshot
from .sprite_loader import SpriteLoader

SELECTION_BORDER_COLOR = (
    0,
    255,
    255,
    255,
)  # BGRA yellow, opaque: visible on light and dark cells
SELECTION_BORDER_THICKNESS = 3
GAME_OVER_TEXT = "GAME OVER"
GAME_OVER_TEXT_ORIGIN = (220, 422)
GAME_OVER_FONT_SIZE = 2.0
GAME_OVER_OUTLINE_COLOR = (0, 0, 0, 255)
GAME_OVER_TEXT_COLOR = (255, 255, 255, 255)
GAME_OVER_OUTLINE_THICKNESS = 8
GAME_OVER_TEXT_THICKNESS = 3
SUPPORTED_ACTION_KINDS = frozenset({"move", "jump"})
HUD_HEIGHT = 210
HUD_BACKGROUND_COLOR = (34, 34, 34, 255)
HUD_TEXT_COLOR = (245, 245, 245, 255)
HUD_HEADING_COLOR = (120, 210, 255, 255)
HUD_MARGIN_X = 20
HUD_COLUMN_GAP = 20
HUD_SCORE_BASELINE = 32
HUD_ACTIONS_BASELINE = 62
HUD_FIRST_ENTRY_BASELINE = 91
HUD_ENTRY_LINE_HEIGHT = 24
HUD_FONT_SIZE = 0.65
HUD_HEADING_FONT_SIZE = 0.72


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
        image_factory: Callable[[], Img] = Img,
    ) -> None:
        self._board_image_path = Path(board_image_path)
        self._sprite_loader = sprite_loader
        self._layout = layout
        self._expected_width = expected_width
        self._expected_height = expected_height
        self._image_factory = image_factory
        self._prepared_board: Img | None = None

    def _get_prepared_board(self) -> Img:
        """Load and resize the board image once, then reuse it for every frame."""
        if self._prepared_board is None:
            pixel_size = self._layout.board_pixel_size(
                self._expected_width, self._expected_height
            )
            self._prepared_board = self._image_factory().read(
                self._board_image_path, size=pixel_size
            )
        return self._prepared_board

    def render(self, snapshot: GameSnapshot, selected: Position | None = None) -> Img:
        """Return a new Img with the board, every snapshot piece, and an optional selection border.

        Render order is: base board, stationary idle pieces, resting pieces,
        moving pieces, the game-over message, then the selection border, so
        selection remains visible on top. A piece with an active motion or
        rest is never also drawn idle.
        """
        if (
            snapshot.width != self._expected_width
            or snapshot.height != self._expected_height
        ):
            raise ValueError(
                "Unsupported board dimensions for the supplied board image: "
                f"expected {self._expected_width}x{self._expected_height}, "
                f"got {snapshot.width}x{snapshot.height}"
            )

        motions_by_piece_id, rests_by_piece_id = self._index_motions_and_rests(snapshot)

        canvas = self._get_prepared_board().copy()

        for piece in snapshot.pieces:
            if (
                piece.id not in motions_by_piece_id
                and piece.id not in rests_by_piece_id
            ):
                self._draw_stationary_piece(canvas, piece)

        for piece in snapshot.pieces:
            rest = rests_by_piece_id.get(piece.id)
            if rest is not None:
                self._draw_resting_piece(canvas, piece, rest)

        for piece in snapshot.pieces:
            motion = motions_by_piece_id.get(piece.id)
            if motion is not None:
                self._draw_moving_piece(canvas, piece, motion)

        if snapshot.game_over:
            self._draw_game_over_message(canvas)

        if selected is not None:
            if not (
                0 <= selected.row < snapshot.height
                and 0 <= selected.col < snapshot.width
            ):
                raise ValueError(
                    f"Selected position {selected} is outside the "
                    f"{snapshot.width}x{snapshot.height} board."
                )
            self._draw_selection_border(canvas, selected)

        return canvas

    @staticmethod
    def _index_motions_and_rests(
        snapshot: GameSnapshot,
    ) -> tuple[dict[str, MotionSnapshot], dict[str, RestSnapshot]]:
        """Map each piece_id to its motion/rest, validating references and exclusivity."""
        piece_ids = {piece.id for piece in snapshot.pieces}

        motions_by_piece_id: dict[str, MotionSnapshot] = {}
        for motion in snapshot.motions:
            if motion.piece_id not in piece_ids:
                raise ValueError(
                    f"Motion references unknown piece_id: {motion.piece_id!r}"
                )
            if motion.piece_id in motions_by_piece_id:
                raise ValueError(f"Duplicate motion for piece_id: {motion.piece_id!r}")
            motions_by_piece_id[motion.piece_id] = motion

        rests_by_piece_id: dict[str, RestSnapshot] = {}
        for rest in snapshot.rests:
            if rest.piece_id not in piece_ids:
                raise ValueError(f"Rest references unknown piece_id: {rest.piece_id!r}")
            if rest.piece_id in rests_by_piece_id:
                raise ValueError(f"Duplicate rest for piece_id: {rest.piece_id!r}")
            if rest.piece_id in motions_by_piece_id:
                raise ValueError(
                    f"piece_id {rest.piece_id!r} has both an active motion and an active rest"
                )
            rests_by_piece_id[rest.piece_id] = rest

        return motions_by_piece_id, rests_by_piece_id

    def _draw_stationary_piece(self, canvas: Img, piece: PieceSnapshot) -> None:
        sprite = self._sprite_loader.load_idle_sprite(piece.kind, piece.color)
        self._draw_sprite_centered_in_cell(canvas, sprite, piece.cell)

    def _draw_resting_piece(
        self, canvas: Img, piece: PieceSnapshot, rest: RestSnapshot
    ) -> None:
        sprite = self._sprite_loader.get_animation_frame(
            piece.kind, piece.color, rest.rest_kind, rest.elapsed_ms
        )
        self._draw_sprite_centered_in_cell(canvas, sprite, piece.cell)

    def _draw_sprite_centered_in_cell(
        self, canvas: Img, sprite: Img, cell: Position
    ) -> None:
        sprite_height, sprite_width = sprite.pixels.shape[:2]
        x, y = self._layout.centered_top_left(cell, sprite_width, sprite_height)
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
            piece.kind,
            piece.color,
            motion.action_kind,
            (
                motion.elapsed_ms
                if motion.action_elapsed_ms is None
                else motion.action_elapsed_ms
            ),
        )
        sprite_height, sprite_width = sprite.pixels.shape[:2]
        x, y = self._layout.centered_top_left_at_point(
            point, sprite_width, sprite_height
        )
        sprite.draw_on(canvas, x, y)

    @staticmethod
    def _draw_game_over_message(canvas: Img) -> None:
        x, y = GAME_OVER_TEXT_ORIGIN
        canvas.put_text(
            GAME_OVER_TEXT,
            x,
            y,
            GAME_OVER_FONT_SIZE,
            color=GAME_OVER_OUTLINE_COLOR,
            thickness=GAME_OVER_OUTLINE_THICKNESS,
        )
        canvas.put_text(
            GAME_OVER_TEXT,
            x,
            y,
            GAME_OVER_FONT_SIZE,
            color=GAME_OVER_TEXT_COLOR,
            thickness=GAME_OVER_TEXT_THICKNESS,
        )

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


class GameRenderer:
    """Compose the unchanged board frame with a score-and-actions HUD below it."""

    def __init__(
        self,
        board_renderer: BoardRenderer,
        image_factory: Callable[[], Img] = Img,
    ) -> None:
        self._board_renderer = board_renderer
        self._image_factory = image_factory

    def render(
        self,
        snapshot: GameSnapshot,
        selected: Position | None,
        presentation: GamePresentationSnapshot,
    ) -> Img:
        """Return the board at (0, 0) followed by a visible two-column HUD."""
        board_frame = self._board_renderer.render(snapshot, selected)
        board_height, board_width = board_frame.pixels.shape[:2]
        canvas = self._image_factory().create(
            board_width,
            board_height + HUD_HEIGHT,
            HUD_BACKGROUND_COLOR,
        )
        board_frame.draw_on(canvas, 0, 0)
        self._draw_hud(canvas, board_width, board_height, presentation)
        return canvas

    @staticmethod
    def _draw_hud(
        canvas: Img,
        board_width: int,
        board_height: int,
        presentation: GamePresentationSnapshot,
    ) -> None:
        column_width = (board_width - HUD_COLUMN_GAP) // 2
        columns = (
            (
                HUD_MARGIN_X,
                "White",
                presentation.white_score,
                presentation.white_actions,
            ),
            (
                column_width + HUD_COLUMN_GAP,
                "Black",
                presentation.black_score,
                presentation.black_actions,
            ),
        )
        for x, color_name, score, actions in columns:
            canvas.put_text(
                f"{color_name} score: {score}",
                x,
                board_height + HUD_SCORE_BASELINE,
                HUD_HEADING_FONT_SIZE,
                color=HUD_HEADING_COLOR,
                thickness=2,
            )
            canvas.put_text(
                f"Recent {color_name} actions:",
                x,
                board_height + HUD_ACTIONS_BASELINE,
                HUD_FONT_SIZE,
                color=HUD_TEXT_COLOR,
                thickness=1,
            )
            for index, entry in enumerate(actions):
                canvas.put_text(
                    entry.notation,
                    x,
                    board_height
                    + HUD_FIRST_ENTRY_BASELINE
                    + index * HUD_ENTRY_LINE_HEIGHT,
                    HUD_FONT_SIZE,
                    color=HUD_TEXT_COLOR,
                    thickness=1,
                )
