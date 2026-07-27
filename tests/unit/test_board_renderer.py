# pyright: reportOptionalMemberAccess=false, reportOptionalSubscript=false

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from kungfu_chess.model.game_state import (
    GameSnapshot,
    MotionSnapshot,
    PieceSnapshot,
    RestSnapshot,
)
from kungfu_chess.model.position import Position
from kungfu_chess.ui import game_window
from kungfu_chess.ui.img import Img
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.renderer import BoardRenderer
from kungfu_chess.ui.sprite_loader import SpriteLoader

ASSETS_ROOT = Path(game_window.__file__).resolve().parent / "assets"
BOARD_IMAGE_PATH = ASSETS_ROOT / "board.png"
PIECES_ROOT = ASSETS_ROOT / "pieces2"


class RecordingImage(Img):
    def __init__(self, read_paths: list[Path]) -> None:
        super().__init__()
        self._read_paths = read_paths
        self.text_calls: list[tuple[object, ...]] = []

    def read(self, path, *args, **kwargs):
        self._read_paths.append(Path(path))
        return super().read(path, *args, **kwargs)

    def copy(self) -> RecordingImage:
        duplicate = RecordingImage(self._read_paths)
        if self.img is not None:
            duplicate.img = self.img.copy()
        return duplicate

    def put_text(
        self,
        txt,
        x,
        y,
        font_size,
        color=(255, 255, 255, 255),
        thickness=1,
    ):
        self.text_calls.append((txt, x, y, font_size, color, thickness))
        super().put_text(txt, x, y, font_size, color=color, thickness=thickness)


class RecordingImageFactory:
    def __init__(self) -> None:
        self.read_paths: list[Path] = []

    def __call__(self) -> RecordingImage:
        return RecordingImage(self.read_paths)


class RecordingSprite(Img):
    def __init__(
        self,
        width: int = 64,
        height: int = 64,
        label: str = "sprite",
        draw_order: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.img = np.zeros((height, width, 4), dtype=np.uint8)
        self.label = label
        self.draw_order = draw_order
        self.draw_calls: list[tuple[Img, int, int]] = []

    def draw_on(self, other_img, x, y):
        self.draw_calls.append((other_img, x, y))
        if self.draw_order is not None:
            self.draw_order.append(self.label)


class RecordingSpriteLoader:
    def __init__(
        self,
        delegate: SpriteLoader | None = None,
        idle_sprite: Img | None = None,
        animation_sprite: Img | None = None,
    ) -> None:
        self.delegate = delegate
        self.idle_sprite = idle_sprite
        self.animation_sprite = animation_sprite
        self.idle_calls: list[tuple[str, str]] = []
        self.animation_calls: list[tuple[str, str, str, int]] = []

    def load_idle_sprite(self, kind: str, color: str) -> Img:
        self.idle_calls.append((kind, color))
        if self.idle_sprite is not None:
            return self.idle_sprite
        assert self.delegate is not None
        return self.delegate.load_idle_sprite(kind, color)

    def get_animation_frame(
        self, kind: str, color: str, state: str, elapsed_ms: int
    ) -> Img:
        self.animation_calls.append((kind, color, state, elapsed_ms))
        if self.animation_sprite is not None:
            return self.animation_sprite
        assert self.delegate is not None
        return self.delegate.get_animation_frame(kind, color, state, elapsed_ms)


def _snapshot(
    pieces,
    motions=(),
    rests=(),
    game_over: bool = False,
    width: int = 8,
    height: int = 8,
) -> GameSnapshot:
    return GameSnapshot(
        pieces=tuple(pieces),
        motions=tuple(motions),
        rests=tuple(rests),
        game_over=game_over,
        width=width,
        height=height,
    )


class TestBoardRenderer(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = BoardLayout(cell_size=100)
        self.sprite_loader = SpriteLoader(PIECES_ROOT)
        self.renderer = BoardRenderer(BOARD_IMAGE_PATH, self.sprite_loader, self.layout)

    def test_output_dimensions_match_expected_board_pixel_size(self) -> None:
        frame = self.renderer.render(_snapshot([]))
        height, width = frame.img.shape[:2]
        self.assertEqual((width, height), (800, 800))

    def test_game_over_message_drawn_when_snapshot_is_game_over(self) -> None:
        image_factory = RecordingImageFactory()
        renderer = BoardRenderer(
            BOARD_IMAGE_PATH,
            self.sprite_loader,
            self.layout,
            image_factory=image_factory,
        )

        frame = renderer.render(_snapshot([], game_over=True))

        self.assertEqual(
            frame.text_calls,
            [
                (
                    "GAME OVER",
                    220,
                    422,
                    2.0,
                    (0, 0, 0, 255),
                    8,
                ),
                (
                    "GAME OVER",
                    220,
                    422,
                    2.0,
                    (255, 255, 255, 255),
                    3,
                ),
            ],
        )

    def test_game_over_message_not_drawn_when_game_is_active(self) -> None:
        image_factory = RecordingImageFactory()
        renderer = BoardRenderer(
            BOARD_IMAGE_PATH,
            self.sprite_loader,
            self.layout,
            image_factory=image_factory,
        )

        frame = renderer.render(_snapshot([], game_over=False))

        self.assertEqual(frame.text_calls, [])

    def test_single_piece_rendered_at_expected_cell(self) -> None:
        piece = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )
        occupied_frame = self.renderer.render(_snapshot([piece]))
        empty_frame = self.renderer.render(_snapshot([]))

        cell_center = occupied_frame.img[50, 50]
        empty_cell_center = empty_frame.img[50, 50]
        self.assertFalse((cell_center == empty_cell_center).all())

        far_cell = occupied_frame.img[750, 750]
        empty_far_cell = empty_frame.img[750, 750]
        self.assertTrue((far_cell == empty_far_cell).all())

    def test_multiple_pieces_rendered_at_different_positions(self) -> None:
        pieces = [
            PieceSnapshot(
                id="wK_7_4", color="w", kind="K", cell=Position(7, 4), state="idle"
            ),
            PieceSnapshot(
                id="bK_0_4", color="b", kind="K", cell=Position(0, 4), state="idle"
            ),
        ]
        occupied_frame = self.renderer.render(_snapshot(pieces))
        empty_frame = self.renderer.render(_snapshot([]))

        white_king_cell = occupied_frame.img[750, 450]
        black_king_cell = occupied_frame.img[50, 450]
        empty_at_white_cell = empty_frame.img[750, 450]
        empty_at_black_cell = empty_frame.img[50, 450]

        self.assertFalse((white_king_cell == empty_at_white_cell).all())
        self.assertFalse((black_king_cell == empty_at_black_cell).all())

    def test_unsupported_board_dimensions_raise_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported board dimensions"):
            self.renderer.render(_snapshot([], width=3, height=3))

    def test_renderer_does_not_mutate_snapshot(self) -> None:
        piece = PieceSnapshot(
            id="wQ_0_0", color="w", kind="Q", cell=Position(0, 0), state="idle"
        )
        snapshot = _snapshot([piece])

        self.renderer.render(snapshot)

        self.assertEqual(snapshot.pieces, (piece,))
        self.assertEqual((snapshot.width, snapshot.height), (8, 8))

    def test_board_asset_is_not_reloaded_for_every_frame(self) -> None:
        image_factory = RecordingImageFactory()
        renderer = BoardRenderer(
            BOARD_IMAGE_PATH,
            self.sprite_loader,
            self.layout,
            image_factory=image_factory,
        )

        renderer.render(_snapshot([]))
        renderer.render(_snapshot([]))
        renderer.render(_snapshot([]))

        self.assertEqual(image_factory.read_paths, [BOARD_IMAGE_PATH])

    def test_repeated_renders_do_not_accumulate_previous_pieces(self) -> None:
        piece = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )

        self.renderer.render(_snapshot([piece]))
        second_frame = self.renderer.render(_snapshot([]))
        baseline_frame = self.renderer.render(_snapshot([]))

        # The piece drawn in the first render must not leak into a later, empty frame.
        self.assertTrue((second_frame.img[50, 50] == baseline_frame.img[50, 50]).all())

    def test_selected_none_draws_no_border(self) -> None:
        implicit_frame = self.renderer.render(_snapshot([]))
        explicit_none_frame = self.renderer.render(_snapshot([]), selected=None)

        self.assertTrue((implicit_frame.img == explicit_none_frame.img).all())

    def test_selected_position_draws_border_in_correct_cell(self) -> None:
        baseline = self.renderer.render(_snapshot([]))
        selected_frame = self.renderer.render(_snapshot([]), selected=Position(0, 0))

        # A point along the top edge of cell (0, 0), just inside its border.
        self.assertFalse((selected_frame.img[3, 50] == baseline.img[3, 50]).all())

    def test_selection_in_one_cell_does_not_alter_another_cell(self) -> None:
        baseline = self.renderer.render(_snapshot([]))
        selected_frame = self.renderer.render(_snapshot([]), selected=Position(0, 0))

        far_cell_pixel = selected_frame.img[750, 750]
        baseline_far_cell_pixel = baseline.img[750, 750]
        self.assertTrue((far_cell_pixel == baseline_far_cell_pixel).all())

    def test_selection_border_visible_after_piece_rendering(self) -> None:
        piece = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )
        frame_with_piece_only = self.renderer.render(_snapshot([piece]))
        frame_with_piece_and_selection = self.renderer.render(
            _snapshot([piece]), selected=Position(0, 0)
        )

        self.assertFalse(
            (
                frame_with_piece_only.img[3, 50]
                == frame_with_piece_and_selection.img[3, 50]
            ).all()
        )

    def test_render_does_not_mutate_selected_position(self) -> None:
        selected = Position(0, 0)

        self.renderer.render(_snapshot([]), selected=selected)

        self.assertEqual(selected, Position(0, 0))

    def test_out_of_board_selected_position_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside"):
            self.renderer.render(_snapshot([]), selected=Position(8, 0))


class TestBoardRendererMotion(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = BoardLayout(cell_size=100)
        self.sprite_loader = SpriteLoader(PIECES_ROOT)
        self.renderer = BoardRenderer(BOARD_IMAGE_PATH, self.sprite_loader, self.layout)

    def test_moving_piece_not_drawn_at_source_cell(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )
        frame = self.renderer.render(_snapshot([piece], motions=[motion]))
        baseline = self.renderer.render(_snapshot([]))

        # Cell (6, 0) center pixel: the interpolated sprite has moved to the
        # shared border with cell (5, 0) and no longer covers its own center.
        self.assertTrue((frame.img[650, 50] == baseline.img[650, 50]).all())

    def test_moving_piece_drawn_at_interpolated_position(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )
        frame = self.renderer.render(_snapshot([piece], motions=[motion]))
        baseline = self.renderer.render(_snapshot([]))

        # Halfway between row 6 (y=650) and row 5 (y=550) is y=600, at col 0 (x=50).
        self.assertFalse((frame.img[600, 50] == baseline.img[600, 50]).all())

    def test_knight_moves_directly_from_source_center_to_destination_center(
        self,
    ) -> None:
        piece = PieceSnapshot(
            id="wN_1_1", color="w", kind="N", cell=Position(1, 1), state="moving"
        )
        expected_centers = (
            (0, (150.0, 150.0)),
            (1500, (200.0, 250.0)),
            (3000, (250.0, 350.0)),
        )

        for elapsed_ms, expected_center in expected_centers:
            with self.subTest(elapsed_ms=elapsed_ms):
                motion = MotionSnapshot(
                    piece_id="wN_1_1",
                    source=Position(1, 1),
                    destination=Position(3, 2),
                    elapsed_ms=elapsed_ms,
                    duration_ms=3000,
                    action_kind="move",
                    action_elapsed_ms=elapsed_ms,
                )
                sprite = RecordingSprite()
                loader = RecordingSpriteLoader(animation_sprite=sprite)
                renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

                renderer.render(_snapshot([piece], motions=[motion]))

                expected_xy = self.layout.centered_top_left_at_point(
                    expected_center,
                    64,
                    64,
                )
                self.assertEqual(sprite.draw_calls[0][1:], expected_xy)

    def test_move_motion_uses_move_animation_state(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="move",
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], motions=[motion]))

        self.assertEqual(loader.animation_calls, [("P", "w", "move", 0)])

    def test_segment_interpolation_keeps_total_elapsed_for_animation(self) -> None:
        piece = PieceSnapshot(
            id="wR_0_1", color="w", kind="R", cell=Position(0, 1), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wR_0_1",
            source=Position(0, 1),
            destination=Position(0, 2),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
            action_elapsed_ms=1500,
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], motions=[motion]))

        self.assertEqual(loader.animation_calls, [("R", "w", "move", 1500)])

    def test_jump_motion_uses_jump_animation_state(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(6, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="jump",
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], motions=[motion]))

        self.assertEqual(loader.animation_calls, [("P", "w", "jump", 0)])

    def test_simultaneous_motions_rendered_independently(self) -> None:
        piece_a = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        piece_b = PieceSnapshot(
            id="bP_1_7", color="b", kind="P", cell=Position(1, 7), state="moving"
        )
        motion_a = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )
        motion_b = MotionSnapshot(
            piece_id="bP_1_7",
            source=Position(1, 7),
            destination=Position(2, 7),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )

        frame = self.renderer.render(
            _snapshot([piece_a, piece_b], motions=[motion_a, motion_b])
        )
        baseline = self.renderer.render(_snapshot([]))

        self.assertFalse((frame.img[600, 50] == baseline.img[600, 50]).all())
        self.assertFalse((frame.img[200, 750] == baseline.img[200, 750]).all())

    def test_moving_pieces_drawn_after_stationary_pieces(self) -> None:
        stationary = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )
        moving = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )
        draw_order: list[str] = []
        idle_sprite = RecordingSprite(label="stationary", draw_order=draw_order)
        moving_sprite = RecordingSprite(label="moving", draw_order=draw_order)
        loader = RecordingSpriteLoader(
            idle_sprite=idle_sprite,
            animation_sprite=moving_sprite,
        )
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([stationary, moving], motions=[motion]))

        stationary_xy = self.layout.centered_top_left(Position(0, 0), 64, 64)
        self.assertEqual(draw_order, ["stationary", "moving"])
        self.assertEqual(idle_sprite.draw_calls[0][1:], stationary_xy)
        self.assertNotEqual(moving_sprite.draw_calls[0][1:], stationary_xy)

    def test_selection_border_visible_above_moving_piece(self) -> None:
        moving = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="move",
        )
        frame_without_selection = self.renderer.render(
            _snapshot([moving], motions=[motion])
        )
        frame_with_selection = self.renderer.render(
            _snapshot([moving], motions=[motion]), selected=Position(6, 0)
        )

        # A point just inside the top edge of cell (6, 0), where the border is drawn.
        self.assertFalse(
            (
                frame_without_selection.img[603, 50]
                == frame_with_selection.img[603, 50]
            ).all()
        )

    def test_unknown_piece_id_in_motion_raises_clear_error(self) -> None:
        motion = MotionSnapshot(
            piece_id="ghost",
            source=Position(0, 0),
            destination=Position(1, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="move",
        )
        with self.assertRaisesRegex(ValueError, "unknown piece_id"):
            self.renderer.render(_snapshot([], motions=[motion]))

    def test_duplicate_motion_for_same_piece_raises_clear_error(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion_a = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="move",
        )
        motion_b = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=100,
            duration_ms=1000,
            action_kind="move",
        )
        with self.assertRaisesRegex(ValueError, "Duplicate motion"):
            self.renderer.render(_snapshot([piece], motions=[motion_a, motion_b]))

    def test_unsupported_action_kind_raises_clear_error(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="teleport",  # type: ignore[arg-type]
        )
        with self.assertRaisesRegex(ValueError, "Unsupported action kind"):
            self.renderer.render(_snapshot([piece], motions=[motion]))

    def test_render_does_not_mutate_snapshot_with_active_motion(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=300,
            duration_ms=1000,
            action_kind="move",
        )
        snapshot = _snapshot([piece], motions=[motion])

        self.renderer.render(snapshot)

        self.assertEqual(snapshot.pieces, (piece,))
        self.assertEqual(snapshot.motions, (motion,))

    def test_repeated_renders_do_not_accumulate_previous_motion_drawings(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )

        self.renderer.render(_snapshot([piece], motions=[motion]))
        second_frame = self.renderer.render(_snapshot([]))
        baseline_frame = self.renderer.render(_snapshot([]))

        self.assertTrue(
            (second_frame.img[600, 50] == baseline_frame.img[600, 50]).all()
        )


class TestBoardRendererRest(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = BoardLayout(cell_size=100)
        self.sprite_loader = SpriteLoader(PIECES_ROOT)
        self.renderer = BoardRenderer(BOARD_IMAGE_PATH, self.sprite_loader, self.layout)

    def test_idle_piece_uses_idle_sprite(self) -> None:
        piece = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece]))

        self.assertEqual(loader.idle_calls, [("K", "w")])

    def test_short_rest_piece_uses_short_rest_animation_state(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="short_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="short_rest", elapsed_ms=100, duration_ms=2000
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(
            loader.animation_calls, [("P", "w", "short_rest", 100)]
        )

    def test_long_rest_piece_uses_long_rest_animation_state(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=300, duration_ms=10000
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(
            loader.animation_calls, [("P", "w", "long_rest", 300)]
        )

    def test_idle_and_resting_pieces_use_same_cell_centering(self) -> None:
        cell = Position(6, 0)
        idle_piece = PieceSnapshot(
            id="wK_6_0", color="w", kind="K", cell=cell, state="idle"
        )
        resting_piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=cell, state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        idle_sprite = RecordingSprite(width=30, height=42)
        resting_sprite = RecordingSprite(width=30, height=42)
        loader = RecordingSpriteLoader(
            idle_sprite=idle_sprite,
            animation_sprite=resting_sprite,
        )
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([idle_piece, resting_piece], rests=[rest]))

        centered_xy = self.layout.centered_top_left(cell, 30, 42)
        self.assertEqual(idle_sprite.draw_calls[0][1:], centered_xy)
        self.assertEqual(resting_sprite.draw_calls[0][1:], centered_xy)
        self.assertEqual(loader.idle_calls, [("K", "w")])
        self.assertEqual(loader.animation_calls, [("P", "w", "long_rest", 0)])

    def test_resting_piece_not_also_rendered_with_idle_sprite(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(loader.idle_calls, [])

    def test_rest_frame_selection_uses_rest_elapsed_ms(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=750, duration_ms=10000
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(
            loader.animation_calls, [("P", "w", "long_rest", 750)]
        )

    def test_rest_config_and_images_are_cached_across_frames(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )

        image_factory = RecordingImageFactory()
        sprite_loader = SpriteLoader(
            PIECES_ROOT,
            image_factory=image_factory,
        )
        renderer = BoardRenderer(BOARD_IMAGE_PATH, sprite_loader, self.layout)

        for elapsed_ms in (0, 10, 20):
            rest = RestSnapshot(
                piece_id="wP_6_0",
                rest_kind="long_rest",
                elapsed_ms=elapsed_ms,
                duration_ms=10000,
            )
            renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(len(image_factory.read_paths), 1)
        self.assertIn("long_rest", image_factory.read_paths[0].parts)

    def test_moving_resting_and_idle_pieces_render_together(self) -> None:
        idle_piece = PieceSnapshot(
            id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle"
        )
        resting_piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        moving_piece = PieceSnapshot(
            id="bP_1_7", color="b", kind="P", cell=Position(1, 7), state="moving"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        motion = MotionSnapshot(
            piece_id="bP_1_7",
            source=Position(1, 7),
            destination=Position(2, 7),
            elapsed_ms=500,
            duration_ms=1000,
            action_kind="move",
        )

        frame = self.renderer.render(
            _snapshot(
                [idle_piece, resting_piece, moving_piece],
                motions=[motion],
                rests=[rest],
            )
        )
        baseline = self.renderer.render(_snapshot([]))

        self.assertFalse((frame.img[50, 50] == baseline.img[50, 50]).all())  # idle king
        self.assertFalse(
            (frame.img[650, 50] == baseline.img[650, 50]).all()
        )  # resting pawn
        self.assertFalse(
            (frame.img[200, 750] == baseline.img[200, 750]).all()
        )  # moving pawn midpoint

    def test_selection_border_visible_above_resting_piece(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )

        frame_without_selection = self.renderer.render(_snapshot([piece], rests=[rest]))
        frame_with_selection = self.renderer.render(
            _snapshot([piece], rests=[rest]), selected=Position(6, 0)
        )

        self.assertFalse(
            (
                frame_without_selection.img[603, 50]
                == frame_with_selection.img[603, 50]
            ).all()
        )

    def test_unknown_piece_id_in_rest_raises_clear_error(self) -> None:
        rest = RestSnapshot(
            piece_id="ghost", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )

        with self.assertRaisesRegex(ValueError, "unknown piece_id"):
            self.renderer.render(_snapshot([], rests=[rest]))

    def test_duplicate_rest_for_same_piece_raises_clear_error(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest_a = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        rest_b = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=50, duration_ms=10000
        )

        with self.assertRaisesRegex(ValueError, "Duplicate rest"):
            self.renderer.render(_snapshot([piece], rests=[rest_a, rest_b]))

    def test_piece_with_both_motion_and_rest_raises_clear_error(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="moving"
        )
        motion = MotionSnapshot(
            piece_id="wP_6_0",
            source=Position(6, 0),
            destination=Position(5, 0),
            elapsed_ms=0,
            duration_ms=1000,
            action_kind="move",
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )

        with self.assertRaisesRegex(
            ValueError, "both an active motion and an active rest"
        ):
            self.renderer.render(_snapshot([piece], motions=[motion], rests=[rest]))

    def test_promoted_piece_uses_promoted_kinds_long_rest_asset(self) -> None:
        """A promoted pawn's rest sprite must be looked up by its new kind, not 'P'."""
        piece = PieceSnapshot(
            id="wP_1_0", color="w", kind="Q", cell=Position(0, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_1_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )

        loader = RecordingSpriteLoader(delegate=self.sprite_loader)
        renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, self.layout)

        renderer.render(_snapshot([piece], rests=[rest]))

        self.assertEqual(loader.animation_calls, [("Q", "w", "long_rest", 0)])

    def test_render_does_not_mutate_snapshot_with_active_rest(self) -> None:
        piece = PieceSnapshot(
            id="wP_6_0", color="w", kind="P", cell=Position(6, 0), state="long_rest"
        )
        rest = RestSnapshot(
            piece_id="wP_6_0", rest_kind="long_rest", elapsed_ms=0, duration_ms=10000
        )
        snapshot = _snapshot([piece], rests=[rest])

        self.renderer.render(snapshot)

        self.assertEqual(snapshot.pieces, (piece,))
        self.assertEqual(snapshot.rests, (rest,))


if __name__ == "__main__":
    unittest.main()
