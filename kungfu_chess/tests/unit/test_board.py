import unittest
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def _make_piece(
    row: int,
    col: int,
    color: str = 'w',
    kind: str = 'K',
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

    def test_duplicate_raises(self):
        b = Board(4, 4)
        b.add_piece(_make_piece(0, 0))
        with self.assertRaises(ValueError):
            b.add_piece(_make_piece(0, 0, color='b'))

    def test_remove_piece(self):
        b = Board(4, 4)
        b.add_piece(_make_piece(0, 0))
        b.remove_piece(Position(0, 0))
        self.assertIsNone(b.get_piece(Position(0, 0)))
