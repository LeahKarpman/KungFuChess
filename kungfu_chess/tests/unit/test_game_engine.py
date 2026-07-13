import unittest
from unittest.mock import MagicMock
from kungfu_chess.engine.game_engine import GameEngine, MoveResult
from kungfu_chess.engine.rule_engine import RuleEngine, MoveValidation
from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position


def _engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board


class TestGameEngine(unittest.TestCase):
    def test_legal_move_returns_ok(self):
        engine, _ = _engine(['. . .', '. wR .', '. . .'])
        result = engine.request_move(Position(1, 1), Position(1, 2))
        self.assertTrue(result.ok)
        self.assertEqual(result.reason, 'ok')

    def test_illegal_move_returns_reason(self):
        engine, _ = _engine(['. . .', '. wR .', '. . .'])
        result = engine.request_move(Position(1, 1), Position(0, 2))
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, 'illegal_move')

    def test_game_over_checked_before_rule_engine(self):
        mock_rules = MagicMock(spec=RuleEngine)
        board = parse_board(['. wR .'])
        engine = GameEngine(board, mock_rules, RealTimeArbiter())
        engine._game_over = True
        result = engine.request_move(Position(0, 1), Position(0, 2))
        self.assertEqual(result.reason, 'game_over')
        mock_rules.validate_move.assert_not_called()

    def test_motion_in_progress_blocks_second_move(self):
        engine, _ = _engine(['. wR . . .'])
        engine.request_move(Position(0, 1), Position(0, 4))
        result = engine.request_move(Position(0, 1), Position(0, 0))
        self.assertEqual(result.reason, 'motion_in_progress')

    def test_invalid_move_does_not_mutate_board(self):
        engine, board = _engine(['. wR .'])
        engine.request_move(Position(0, 1), Position(1, 2))  # diagonal — illegal
        self.assertIsNotNone(board.get_piece(Position(0, 1)))

    def test_wait_delegates_to_arbiter(self):
        mock_arbiter = MagicMock(spec=RealTimeArbiter)
        mock_arbiter.has_active_motion.return_value = False
        mock_arbiter.advance_time.return_value = []
        board = parse_board(['. wR .'])
        engine = GameEngine(board, RuleEngine(), mock_arbiter)
        engine.wait(500)
        mock_arbiter.advance_time.assert_called_once_with(500)

    def test_arrival_moves_piece_on_board(self):
        engine, board = _engine(['. wR . .'])
        engine.request_move(Position(0, 1), Position(0, 3))
        engine.wait(2000)
        self.assertIsNone(board.get_piece(Position(0, 1)))
        self.assertIsNotNone(board.get_piece(Position(0, 3)))

    def test_king_capture_sets_game_over(self):
        engine, _ = _engine(['wR . bK'])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        self.assertTrue(engine.game_over)

    def test_game_over_blocks_further_moves(self):
        engine, _ = _engine(['wR . bK'])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        result = engine.request_move(Position(0, 2), Position(0, 0))
        self.assertEqual(result.reason, 'game_over')


class TestLandingReservation(unittest.TestCase):
    """Tests for landing-cell reservation during a jump."""

    def test_enemy_may_move_to_landing_cell(self):
        """An enemy piece must be accepted, not blocked by landing_reserved."""
        lines = ['. . .', 'wP bR .', '. . .']
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))
        result = engine.request_move(Position(1, 1), Position(1, 0))
        self.assertTrue(result.ok)
        self.assertEqual(result.reason, 'ok')

    def test_friendly_piece_blocked_from_landing_cell(self):
        """A friendly piece must be rejected with landing_reserved."""
        lines = ['. . .', 'wP . wR', '. . .']
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))
        result = engine.request_move(Position(1, 2), Position(1, 0))
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, 'landing_reserved')

    def test_enemy_arrives_then_jumper_lands_captures_enemy(self):
        """
        After the enemy moves to the landing cell and wait(1000) elapses,
        the enemy should be captured and the jumper should occupy the cell.
        """
        lines = ['. . .', 'wP bR .', '. . .']
        engine, board = _engine(lines)
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))
        engine.wait(1000)
        jumper = board.get_piece(Position(1, 0))
        self.assertIsNotNone(jumper, "Jumper must occupy landing cell")
        self.assertEqual(jumper.color, 'w')
        self.assertIsNone(board.get_piece(Position(1, 1)), "Enemy must have left (1,1)")
