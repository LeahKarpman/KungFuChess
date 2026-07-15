from __future__ import annotations

import unittest
from pathlib import Path

from kungfu_chess.model.game_state import GameSnapshot, PieceSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui import game_window
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


if __name__ == "__main__":
    unittest.main()
