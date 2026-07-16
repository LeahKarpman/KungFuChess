from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from kungfu_chess.model.game_state import GameSnapshot, PieceSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui import game_window
from kungfu_chess.ui.img import cv2 as img_cv2
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.renderer import BoardRenderer
from kungfu_chess.ui.sprite_loader import SpriteLoader

ASSETS_ROOT = Path(game_window.__file__).resolve().parent / "assets"
BOARD_IMAGE_PATH = ASSETS_ROOT / "board.png"
PIECES_ROOT = ASSETS_ROOT / "pieces2"


def _snapshot(pieces, width: int = 8, height: int = 8) -> GameSnapshot:
    return GameSnapshot(
        pieces=tuple(pieces), motions=(), game_over=False, width=width, height=height
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

    def test_single_piece_rendered_at_expected_cell(self) -> None:
        piece = PieceSnapshot(id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle")
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
            PieceSnapshot(id="wK_7_4", color="w", kind="K", cell=Position(7, 4), state="idle"),
            PieceSnapshot(id="bK_0_4", color="b", kind="K", cell=Position(0, 4), state="idle"),
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
        piece = PieceSnapshot(id="wQ_0_0", color="w", kind="Q", cell=Position(0, 0), state="idle")
        snapshot = _snapshot([piece])

        self.renderer.render(snapshot)

        self.assertEqual(snapshot.pieces, (piece,))
        self.assertEqual((snapshot.width, snapshot.height), (8, 8))

    def test_board_asset_is_not_reloaded_for_every_frame(self) -> None:
        with patch.object(img_cv2, "imread", wraps=img_cv2.imread) as mocked_imread:
            self.renderer.render(_snapshot([]))
            self.renderer.render(_snapshot([]))
            self.renderer.render(_snapshot([]))

        board_reads = [
            call for call in mocked_imread.call_args_list if call.args[0] == str(BOARD_IMAGE_PATH)
        ]
        self.assertEqual(len(board_reads), 1)

    def test_repeated_renders_do_not_accumulate_previous_pieces(self) -> None:
        piece = PieceSnapshot(id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle")

        self.renderer.render(_snapshot([piece]))
        second_frame = self.renderer.render(_snapshot([]))
        baseline_frame = self.renderer.render(_snapshot([]))

        # The piece drawn in the first render must not leak into a later, empty frame.
        self.assertTrue(
            (second_frame.img[50, 50] == baseline_frame.img[50, 50]).all()
        )

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
        piece = PieceSnapshot(id="wK_0_0", color="w", kind="K", cell=Position(0, 0), state="idle")
        frame_with_piece_only = self.renderer.render(_snapshot([piece]))
        frame_with_piece_and_selection = self.renderer.render(
            _snapshot([piece]), selected=Position(0, 0)
        )

        self.assertFalse(
            (frame_with_piece_only.img[3, 50] == frame_with_piece_and_selection.img[3, 50]).all()
        )

    def test_render_does_not_mutate_selected_position(self) -> None:
        selected = Position(0, 0)

        self.renderer.render(_snapshot([]), selected=selected)

        self.assertEqual(selected, Position(0, 0))

    def test_out_of_board_selected_position_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside"):
            self.renderer.render(_snapshot([]), selected=Position(8, 0))


if __name__ == "__main__":
    unittest.main()
