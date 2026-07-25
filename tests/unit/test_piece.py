import unittest

from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


class TestPiece(unittest.TestCase):
    """Verify construction of valid piece model objects."""

    def test_constructor_initializes_readable_cell(self) -> None:
        cell = Position(2, 3)

        piece = Piece("piece", "w", "K", cell)

        self.assertEqual(piece.cell, cell)

    def test_cell_rejects_external_assignment(self) -> None:
        piece = Piece("piece", "w", "K", Position(0, 0))

        with self.assertRaises(AttributeError):
            piece.cell = Position(1, 1)

    def test_rejects_invalid_color(self) -> None:
        with self.assertRaisesRegex(ValueError, "^invalid_piece_color$"):
            Piece("piece", "green", "K", Position(0, 0))

    def test_rejects_invalid_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "^invalid_piece_kind$"):
            Piece("piece", "w", "X", Position(0, 0))

    def test_rejects_invalid_lifecycle_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "^invalid_piece_state$"):
            Piece("piece", "w", "K", Position(0, 0), "flying")


if __name__ == "__main__":
    unittest.main()
