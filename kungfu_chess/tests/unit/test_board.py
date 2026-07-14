import unittest
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def _make_piece(
    row: int,
    col: int,
    color: str = "w",
    kind: str = "K",
) -> Piece:
    pos = Position(row, col)
    return Piece(id=f"{color}{kind}_{row}_{col}", color=color, kind=kind, cell=pos)


class TestBoard(unittest.TestCase):
    def test_dimensions(self):
        b = Board(8, 8)
        self.assertEqual(b.width, 8)
        self.assertEqual(b.height, 8)

    def test_in_bounds(self):
        b = Board(4, 4)
        self.assertTrue(b.in_bounds(Position(0, 0)))
        self.assertFalse(b.in_bounds(Position(4, 0)))
        self.assertFalse(b.in_bounds(Position(0, 4)))

    def test_empty_cell_returns_none(self):
        b = Board(4, 4)
        self.assertIsNone(b.get_piece(Position(0, 0)))

    def test_add_and_get_piece(self):
        b = Board(4, 4)
        p = _make_piece(1, 2)
        b.add_piece(p)
        self.assertIs(b.get_piece(Position(1, 2)), p)

    def test_add_piece_rejects_out_of_bounds_position(self):
        """Keep every stored piece inside the board dimensions."""
        board = Board(2, 2)
        invalid_positions = [
            Position(-1, 0),
            Position(0, -1),
            Position(2, 0),
            Position(0, 2),
        ]

        for position in invalid_positions:
            with self.subTest(position=position):
                piece = Piece("wK_outside", "w", "K", position)
                with self.assertRaisesRegex(
                    ValueError,
                    "^piece_out_of_bounds$",
                ):
                    board.add_piece(piece)

    def test_duplicate_raises(self):
        b = Board(4, 4)
        b.add_piece(_make_piece(0, 0))
        with self.assertRaises(ValueError):
            b.add_piece(_make_piece(0, 0, color="b"))

    def test_remove_piece(self):
        b = Board(4, 4)
        b.add_piece(_make_piece(0, 0))
        b.remove_piece(Position(0, 0))
        self.assertIsNone(b.get_piece(Position(0, 0)))

    def test_all_pieces_returns_current_occupants(self):
        b = Board(2, 2)
        first = _make_piece(0, 0)
        second = _make_piece(1, 1, color="b")
        b.add_piece(first)
        b.add_piece(second)

        self.assertEqual(b.all_pieces(), (first, second))
