import unittest
from kungfu_chess.engine.rule_engine import RuleEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position


class TestRookRules(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = RuleEngine()

    def _board(self, lines: list[str]) -> Board:
        return parse_board(lines)

    def test_rook_legal_destinations_empty_board(self):
        board = self._board([
            '. . . . .',
            '. . . . .',
            '. . wR . .',
            '. . . . .',
            '. . . . .',
        ])
        src = Position(2, 2)
        dests = self.rules.legal_destinations(board, src)
        expected = (
            {Position(r, 2) for r in range(5) if r != 2} |
            {Position(2, c) for c in range(5) if c != 2}
        )
        self.assertEqual(dests, expected)

    def test_rook_blocked_by_friendly(self):
        # A friendly pawn directly above the rook blocks its path.
        board = self._board([
            '. . . . .',
            '. . wP . .',
            '. . wR . .',
            '. . . . .',
            '. . . . .',
        ])
        dests = self.rules.legal_destinations(board, Position(2, 2))
        self.assertNotIn(Position(1, 2), dests)  # The friendly square is unavailable.
        self.assertNotIn(Position(0, 2), dests)  # Squares beyond it are unavailable.

    def test_rook_includes_enemy_blocker(self):
        # An enemy pawn directly above the rook blocks its path.
        board = self._board([
            '. . . . .',
            '. . bP . .',
            '. . wR . .',
            '. . . . .',
            '. . . . .',
        ])
        dests = self.rules.legal_destinations(board, Position(2, 2))
        self.assertIn(Position(1, 2), dests)  # The enemy square is capturable.
        self.assertNotIn(Position(0, 2), dests)  # Squares beyond it are unavailable.

    def test_rook_cannot_pass_enemy_blocker(self):
        board = self._board([
            '. . . . .',
            '. . bP . .',
            '. . wR . .',
            '. . . . .',
            '. . . . .',
        ])
        dests = self.rules.legal_destinations(board, Position(2, 2))
        self.assertIn(Position(1, 2), dests)
        self.assertNotIn(Position(0, 2), dests)

    def test_rook_cannot_move_diagonally(self):
        board = self._board([
            '. . . . .',
            '. . . . .',
            '. . wR . .',
            '. . . . .',
            '. . . . .',
        ])
        dests = self.rules.legal_destinations(board, Position(2, 2))
        self.assertNotIn(Position(1, 1), dests)
        self.assertNotIn(Position(3, 3), dests)
