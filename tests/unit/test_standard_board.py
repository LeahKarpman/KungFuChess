# pyright: reportOptionalMemberAccess=false

from __future__ import annotations

import unittest
from pathlib import Path

import kungfu_chess
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.position import Position

STANDARD_BOARD_PATH = (
    Path(kungfu_chess.__file__).resolve().parent / "resources" / "boards" / "standard_board.txt"
)


class TestStandardBoardResource(unittest.TestCase):
    """Guard the game-data file loaded by the UI entry point, not just the parser."""

    def setUp(self) -> None:
        text = STANDARD_BOARD_PATH.read_text(encoding="utf-8")
        lines = text.strip("\n").splitlines()
        self.board = parse_board(lines)

    def test_dimensions_are_standard_8x8(self) -> None:
        self.assertEqual((self.board.width, self.board.height), (8, 8))

    def test_total_piece_count_is_32(self) -> None:
        self.assertEqual(len(self.board.all_pieces()), 32)

    def test_white_pawns_face_row_zero_matching_pawn_rules(self) -> None:
        # piece_rules.pawn_destinations moves white toward row 0, from start_row = height - 2.
        for col in range(8):
            with self.subTest(col=col):
                piece = self.board.get_piece(Position(6, col))
                self.assertIsNotNone(piece)
                self.assertEqual((piece.color, piece.kind), ("w", "P"))

    def test_black_pawns_face_row_seven_matching_pawn_rules(self) -> None:
        for col in range(8):
            with self.subTest(col=col):
                piece = self.board.get_piece(Position(1, col))
                self.assertIsNotNone(piece)
                self.assertEqual((piece.color, piece.kind), ("b", "P"))

    def test_kings_on_expected_cells(self) -> None:
        white_king = self.board.get_piece(Position(7, 4))
        black_king = self.board.get_piece(Position(0, 4))
        self.assertEqual((white_king.color, white_king.kind), ("w", "K"))
        self.assertEqual((black_king.color, black_king.kind), ("b", "K"))


if __name__ == "__main__":
    unittest.main()
