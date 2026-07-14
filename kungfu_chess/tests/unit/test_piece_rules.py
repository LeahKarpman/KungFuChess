from __future__ import annotations

import unittest
from kungfu_chess.rules import piece_rules
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position


class TestRookRules(unittest.TestCase):
    """Verify orthogonal sliding and blocker behavior for rooks."""

    def _board(self, lines: list[str]) -> Board:
        return parse_board(lines)

    def test_rook_legal_destinations_empty_board(self):
        board = self._board(
            [
                ". . . . .",
                ". . . . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        src = Position(2, 2)
        dests = piece_rules.rook_destinations(board, src)
        expected = {Position(r, 2) for r in range(5) if r != 2} | {
            Position(2, c) for c in range(5) if c != 2
        }
        self.assertEqual(dests, expected)

    def test_rook_blocked_by_friendly(self):
        # A friendly pawn directly above the rook blocks its path.
        board = self._board(
            [
                ". . . . .",
                ". . wP . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        self.assertNotIn(Position(1, 2), dests)  # The friendly square is unavailable.
        self.assertNotIn(Position(0, 2), dests)  # Squares beyond it are unavailable.

    def test_rook_includes_enemy_blocker(self):
        # An enemy pawn directly above the rook blocks its path.
        board = self._board(
            [
                ". . . . .",
                ". . bP . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        self.assertIn(Position(1, 2), dests)  # The enemy square is capturable.
        self.assertNotIn(Position(0, 2), dests)  # Squares beyond it are unavailable.

    def test_rook_cannot_pass_enemy_blocker(self):
        board = self._board(
            [
                ". . . . .",
                ". . bP . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        self.assertIn(Position(1, 2), dests)
        self.assertNotIn(Position(0, 2), dests)

    def test_rook_cannot_move_diagonally(self):
        board = self._board(
            [
                ". . . . .",
                ". . . . .",
                ". . wR . .",
                ". . . . .",
                ". . . . .",
            ]
        )
        dests = piece_rules.rook_destinations(board, Position(2, 2))
        self.assertNotIn(Position(1, 1), dests)
        self.assertNotIn(Position(3, 3), dests)


class TestOtherPieceRules(unittest.TestCase):
    """Verify movement rules that are independent of pawn direction."""

    def test_bishop_moves_diagonally_and_stops_at_enemy(self) -> None:
        board = parse_board(
            [
                "bP . . . .",
                ". . . . .",
                ". . wB . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.bishop_destinations(board, Position(2, 2))

        self.assertIn(Position(0, 0), destinations)
        self.assertNotIn(Position(2, 3), destinations)

    def test_bishop_cannot_pass_friendly_blocker(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". wP . . .",
                ". . wB . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.bishop_destinations(board, Position(2, 2))

        self.assertNotIn(Position(1, 1), destinations)
        self.assertNotIn(Position(0, 0), destinations)

    def test_queen_combines_rook_and_bishop_destinations(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". . . . .",
                ". . wQ . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.queen_destinations(board, Position(2, 2))

        self.assertIn(Position(2, 4), destinations)
        self.assertIn(Position(0, 0), destinations)
        self.assertNotIn(Position(0, 1), destinations)

    def test_king_moves_one_cell_and_cannot_land_on_friendly_piece(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". wK wP",
                ". . .",
            ]
        )

        destinations = piece_rules.king_destinations(board, Position(1, 1))

        self.assertIn(Position(0, 0), destinations)
        self.assertNotIn(Position(1, 2), destinations)

    def test_knight_jumps_over_adjacent_blockers(self) -> None:
        board = parse_board(
            [
                ". . . . .",
                ". wP wP wP .",
                ". wP wN wP .",
                ". wP wP wP .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.knight_destinations(board, Position(2, 2))

        self.assertIn(Position(0, 1), destinations)
        self.assertIn(Position(4, 3), destinations)

    def test_knight_cannot_land_on_friendly_piece(self) -> None:
        board = parse_board(
            [
                ". wP . . .",
                ". . . . .",
                ". . wN . .",
                ". . . . .",
                ". . . . .",
            ]
        )

        destinations = piece_rules.knight_destinations(board, Position(2, 2))

        self.assertNotIn(Position(0, 1), destinations)


class TestPawnRules(unittest.TestCase):
    """Verify direction, double steps, blockers, and pawn captures."""

    def test_white_pawn_moves_up_and_may_double_step_from_start(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". . .",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        self.assertIn(Position(1, 1), destinations)
        self.assertIn(Position(0, 1), destinations)

    def test_black_pawn_moves_down_and_may_double_step_from_start(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". bP .",
                ". . .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(1, 1))

        self.assertIn(Position(2, 1), destinations)
        self.assertIn(Position(3, 1), destinations)

    def test_pawn_captures_enemy_diagonally(self) -> None:
        board = parse_board(
            [
                ". . .",
                "bR . bN",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        self.assertIn(Position(1, 0), destinations)
        self.assertIn(Position(1, 2), destinations)

    def test_pawn_cannot_move_forward_into_occupied_cell(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". bR .",
                ". wP .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        self.assertNotIn(Position(1, 1), destinations)
        self.assertNotIn(Position(0, 1), destinations)

    def test_pawn_cannot_double_step_outside_start_row(self) -> None:
        board = parse_board(
            [
                ". . .",
                ". . .",
                ". wP .",
                ". . .",
                ". . .",
            ]
        )

        destinations = piece_rules.pawn_destinations(board, Position(2, 1))

        self.assertIn(Position(1, 1), destinations)
        self.assertNotIn(Position(0, 1), destinations)
