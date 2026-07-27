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


def _assert_board_invariant(
    test_case: unittest.TestCase,
    board: Board,
    positions: list[Position],
) -> None:
    for position in positions:
        occupant = board.get_piece(position)
        if occupant is not None:
            test_case.assertEqual(occupant.cell, position)


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
        self.assertEqual(p.cell, Position(1, 2))
        _assert_board_invariant(self, b, [Position(1, 2)])

    def test_place_piece_uses_explicit_position_without_touching_other_cell(self):
        board = Board(3, 3)
        original_position = Position(0, 0)
        destination = Position(2, 2)
        existing = Piece("existing", "w", "R", original_position)
        incoming = Piece("incoming", "b", "B", original_position)
        board.add_piece(existing)

        board.place_piece(incoming, destination)

        self.assertIs(board.get_piece(original_position), existing)
        self.assertIs(board.get_piece(destination), incoming)
        self.assertEqual(incoming.cell, destination)
        _assert_board_invariant(self, board, [original_position, destination])

    def test_move_piece_preserves_piece_identity_and_attributes(self):
        board = Board(3, 3)
        source = Position(0, 1)
        destination = Position(2, 1)
        piece = Piece("moving", "b", "N", source, "short_rest")
        board.add_piece(piece)

        moved = board.move_piece(source, destination)

        self.assertIs(moved, piece)
        self.assertIsNone(board.get_piece(source))
        self.assertIs(board.get_piece(destination), piece)
        self.assertEqual(piece.cell, destination)
        self.assertEqual(piece.id, "moving")
        self.assertEqual(piece.color, "b")
        self.assertEqual(piece.kind, "N")
        self.assertEqual(piece.state, "short_rest")
        _assert_board_invariant(self, board, [source, destination])

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

    def test_duplicate_piece_id_raises(self) -> None:
        """Reject two board occupants that share one stable identity."""
        board = Board(2, 2)
        first = Piece("shared_id", "w", "K", Position(0, 0))
        second = Piece("shared_id", "b", "K", Position(1, 1))
        board.add_piece(first)

        with self.assertRaisesRegex(ValueError, "^duplicate_piece_id$"):
            board.add_piece(second)

    def test_failed_place_piece_out_of_bounds_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(0, 0))
        incoming = Piece("incoming", "b", "K", Position(1, 1))
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "^piece_out_of_bounds$"):
            board.place_piece(incoming, Position(2, 1))

        self.assertIs(board.get_piece(Position(0, 0)), existing)
        self.assertIsNone(board.get_piece(Position(1, 1)))
        self.assertEqual(incoming.cell, Position(1, 1))
        _assert_board_invariant(self, board, [Position(0, 0), Position(1, 1)])

    def test_failed_place_piece_occupied_is_atomic(self) -> None:
        board = Board(2, 2)
        destination = Position(0, 0)
        existing = Piece("existing", "w", "K", destination)
        incoming = Piece("incoming", "b", "K", Position(1, 1))
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "already occupied"):
            board.place_piece(incoming, destination)

        self.assertIs(board.get_piece(destination), existing)
        self.assertIsNone(board.get_piece(Position(1, 1)))
        self.assertEqual(incoming.cell, Position(1, 1))
        _assert_board_invariant(self, board, [destination, Position(1, 1)])

    def test_failed_place_piece_duplicate_id_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("shared_id", "w", "K", Position(0, 0))
        incoming = Piece("shared_id", "b", "K", Position(1, 0))
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "^duplicate_piece_id$"):
            board.place_piece(incoming, Position(1, 1))

        self.assertIs(board.get_piece(Position(0, 0)), existing)
        self.assertIsNone(board.get_piece(Position(1, 0)))
        self.assertIsNone(board.get_piece(Position(1, 1)))
        self.assertEqual(incoming.cell, Position(1, 0))
        _assert_board_invariant(
            self,
            board,
            [Position(0, 0), Position(1, 0), Position(1, 1)],
        )

    def test_failed_move_missing_source_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(1, 1))
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "^no_piece_at_source$"):
            board.move_piece(Position(0, 0), Position(0, 1))

        self.assertIs(board.get_piece(Position(1, 1)), existing)
        self.assertEqual(existing.cell, Position(1, 1))
        _assert_board_invariant(self, board, [Position(0, 0), Position(1, 1)])

    def test_failed_move_out_of_bounds_source_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(0, 0))
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "^source_out_of_bounds$"):
            board.move_piece(Position(-1, 0), Position(1, 1))

        self.assertIs(board.get_piece(Position(0, 0)), existing)
        self.assertEqual(existing.cell, Position(0, 0))
        _assert_board_invariant(self, board, [Position(0, 0), Position(1, 1)])

    def test_failed_move_out_of_bounds_destination_is_atomic(self) -> None:
        board = Board(2, 2)
        source = Position(0, 0)
        existing = Piece("existing", "w", "K", source)
        board.add_piece(existing)

        with self.assertRaisesRegex(ValueError, "^destination_out_of_bounds$"):
            board.move_piece(source, Position(0, 2))

        self.assertIs(board.get_piece(source), existing)
        self.assertEqual(existing.cell, source)
        _assert_board_invariant(self, board, [source, Position(1, 1)])

    def test_failed_move_occupied_destination_is_atomic(self) -> None:
        board = Board(2, 2)
        source = Position(0, 0)
        destination = Position(1, 1)
        moving = Piece("moving", "w", "K", source)
        blocker = Piece("blocker", "b", "K", destination)
        board.add_piece(moving)
        board.add_piece(blocker)

        with self.assertRaisesRegex(ValueError, "^destination_occupied$"):
            board.move_piece(source, destination)

        self.assertIs(board.get_piece(source), moving)
        self.assertIs(board.get_piece(destination), blocker)
        self.assertEqual(moving.cell, source)
        self.assertEqual(blocker.cell, destination)
        _assert_board_invariant(self, board, [source, destination])

    def test_remove_piece(self):
        b = Board(4, 4)
        piece = _make_piece(0, 0)
        b.add_piece(piece)
        b.remove_piece(Position(0, 0))
        self.assertIsNone(b.get_piece(Position(0, 0)))
        self.assertEqual(piece.cell, Position(0, 0))

    def test_all_pieces_returns_current_occupants(self):
        b = Board(2, 2)
        first = _make_piece(0, 0)
        second = _make_piece(1, 1, color="b")
        b.add_piece(first)
        b.add_piece(second)

        self.assertEqual(b.all_pieces(), (first, second))
