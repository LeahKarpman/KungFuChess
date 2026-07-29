from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..model.game_state import GameSnapshot, MotionSnapshot, PieceSnapshot, RestSnapshot
from ..model.position import Position
from .animation import clamp_progress, lerp_point
from .img import Img
from .layout import BoardLayout
from .presentation import GamePresentationSnapshot, MoveLogEntry
from .sprite_loader import SpriteLoader

SELECTION_BORDER_COLOR = (
    0,
    255,
    255,
    255,
)  # BGRA yellow, opaque: visible on light and dark cells
SELECTION_BORDER_THICKNESS = 3
GAME_OVER_TEXT = "GAME OVER"
GAME_OVER_FONT_SIZE = 2.0
GAME_OVER_OUTLINE_COLOR = (0, 0, 0, 255)
GAME_OVER_TEXT_COLOR = (255, 255, 255, 255)
GAME_OVER_OUTLINE_THICKNESS = 8
GAME_OVER_TEXT_THICKNESS = 3
SUPPORTED_ACTION_KINDS = frozenset({"move", "jump"})
FRAME_WIDTH = 1096
FRAME_HEIGHT = 636
PANEL_WIDTH = 220
PANEL_HEIGHT = 576
PANEL_Y = 30
LEFT_PANEL_X = 20
RIGHT_PANEL_X = 856
PANEL_PADDING = 16
PANEL_HEADING_BASELINE = 42
PANEL_NAME_BASELINE = 74
PANEL_SCORE_BASELINE = 106
PANEL_MOVES_BASELINE = 146
PANEL_FIRST_ENTRY_BASELINE = 184
PANEL_ENTRY_LINE_HEIGHT = 32
PANEL_BOTTOM_PADDING = 20
HUD_BACKGROUND_COLOR = (28, 31, 36, 255)
PANEL_BACKGROUND_COLOR = (42, 47, 54, 255)
PANEL_BORDER_COLOR = (82, 91, 102, 255)
HUD_TEXT_COLOR = (245, 245, 245, 255)
HUD_HEADING_COLOR = (120, 210, 255, 255)
HUD_FONT_SIZE = 0.65
HUD_HEADING_FONT_SIZE = 0.82


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

    @property
    def layout(self) -> BoardLayout:
        """Return the board geometry shared with rendering and input."""
        return self._layout

    def _get_prepared_board(self) -> Img:
        """Load and resize the board image once, then reuse it for every frame."""
        if self._prepared_board is None:
            pixel_size = self._layout.board_pixel_size(
                self._expected_width, self._expected_height
            )
            self._prepared_board = self._image_factory().read(self._board_image_path)
            self._prepared_board.resize(*pixel_size)
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

        board_width, board_height = self._layout.board_pixel_size(
            self._expected_width,
            self._expected_height,
        )
        canvas = self._image_factory().create(
            self._layout.origin_x + board_width,
            self._layout.origin_y + board_height,
            (0, 0, 0, 0),
        )
        self.render_on(canvas, snapshot, selected)
        return canvas

    def render_on(
        self,
        canvas: Img,
        snapshot: GameSnapshot,
        selected: Position | None = None,
    ) -> None:
        """Render board content onto an existing composed frame."""
        if (
            snapshot.width != self._expected_width
            or snapshot.height != self._expected_height
        ):
            raise ValueError(
                "Unsupported board dimensions for the supplied board image: "
                f"expected {self._expected_width}x{self._expected_height}, "
                f"got {snapshot.width}x{snapshot.height}"
            )

        self._get_prepared_board().draw_on(
            canvas,
            self._layout.origin_x,
            self._layout.origin_y,
        )
        motions_by_piece_id, rests_by_piece_id = self._index_motions_and_rests(snapshot)

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

    def _draw_game_over_message(self, canvas: Img) -> None:
        board_width, board_height = self._layout.board_pixel_size(
            self._expected_width,
            self._expected_height,
        )
        x = self._layout.origin_x + round(board_width * 0.275)
        y = self._layout.origin_y + round(board_height * 0.5275)
        scale = self._layout.cell_size / 100
        canvas.put_text(
            GAME_OVER_TEXT,
            x,
            y,
            GAME_OVER_FONT_SIZE * scale,
            color=GAME_OVER_OUTLINE_COLOR,
            thickness=GAME_OVER_OUTLINE_THICKNESS,
        )
        canvas.put_text(
            GAME_OVER_TEXT,
            x,
            y,
            GAME_OVER_FONT_SIZE * scale,
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
    """Compose a compact dashboard with side panels around the centered board."""

    def __init__(
        self,
        board_renderer: BoardRenderer,
        image_factory: Callable[[], Img] = Img,
    ) -> None:
        self._board_renderer = board_renderer
        self._image_factory = image_factory

    @property
    def layout(self) -> BoardLayout:
        """Return the exact board geometry used by the composed renderer."""
        return self._board_renderer.layout

    def render(
        self,
        snapshot: GameSnapshot,
        selected: Position | None,
        presentation: GamePresentationSnapshot,
    ) -> Img:
        """Return the complete board, scores, and recent-moves dashboard."""
        canvas = self._image_factory().create(
            FRAME_WIDTH,
            FRAME_HEIGHT,
            HUD_BACKGROUND_COLOR,
        )
        self._draw_panel_background(canvas, LEFT_PANEL_X)
        self._draw_panel_background(canvas, RIGHT_PANEL_X)
        self._board_renderer.render_on(canvas, snapshot, selected)
        self._draw_panel(
            canvas,
            LEFT_PANEL_X,
            "Black",
            presentation.black_name,
            presentation.black_score,
            presentation.black_actions,
        )
        self._draw_panel(
            canvas,
            RIGHT_PANEL_X,
            "White",
            presentation.white_name,
            presentation.white_score,
            presentation.white_actions,
        )
        return canvas

    def _draw_panel_background(self, canvas: Img, panel_x: int) -> None:
        panel = self._image_factory().create(
            PANEL_WIDTH,
            PANEL_HEIGHT,
            PANEL_BACKGROUND_COLOR,
        )
        panel.draw_rectangle(
            (1, 1),
            (PANEL_WIDTH - 2, PANEL_HEIGHT - 2),
            PANEL_BORDER_COLOR,
            2,
        )
        panel.draw_on(canvas, panel_x, PANEL_Y)

    @staticmethod
    def _draw_panel(
        canvas: Img,
        panel_x: int,
        color_name: str,
        player_name: str,
        score: int,
        actions: tuple[MoveLogEntry, ...],
    ) -> None:
        text_x = panel_x + PANEL_PADDING
        canvas.put_text(
            color_name.upper(),
            text_x,
            PANEL_Y + PANEL_HEADING_BASELINE,
            HUD_HEADING_FONT_SIZE,
            color=HUD_HEADING_COLOR,
            thickness=2,
        )
        canvas.put_text(
            player_name,
            text_x,
            PANEL_Y + PANEL_NAME_BASELINE,
            HUD_FONT_SIZE,
            color=HUD_TEXT_COLOR,
            thickness=1,
        )
        canvas.put_text(
            f"Score: {score}",
            text_x,
            PANEL_Y + PANEL_SCORE_BASELINE,
            HUD_HEADING_FONT_SIZE,
            color=HUD_TEXT_COLOR,
            thickness=2,
        )
        canvas.put_text(
            "Moves",
            text_x,
            PANEL_Y + PANEL_MOVES_BASELINE,
            HUD_FONT_SIZE,
            color=HUD_TEXT_COLOR,
            thickness=1,
        )
        available_baseline_height = (
            PANEL_HEIGHT - PANEL_BOTTOM_PADDING - PANEL_FIRST_ENTRY_BASELINE
        )
        visible_count = max(
            0,
            available_baseline_height // PANEL_ENTRY_LINE_HEIGHT + 1,
        )
        visible_actions = actions[-visible_count:] if visible_count else ()
        for index, entry in enumerate(visible_actions):
            canvas.put_text(
                entry.notation,
                text_x,
                PANEL_Y
                + PANEL_FIRST_ENTRY_BASELINE
                + index * PANEL_ENTRY_LINE_HEIGHT,
                HUD_FONT_SIZE,
                color=HUD_TEXT_COLOR,
                thickness=1,
            )
