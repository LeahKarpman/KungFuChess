import unittest
from unittest.mock import MagicMock
from kungfu_chess.controller.controller import Controller, ControllerResult
from kungfu_chess.io.board_mapper import BoardMapper
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.engine.rule_engine import RuleEngine
from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.model.position import Position


def _setup(lines):
    board = parse_board(lines)
    engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
    mapper = BoardMapper(board.width, board.height)
    controller = Controller(mapper, engine)
    return controller, engine


class TestController(unittest.TestCase):
    def test_first_click_on_piece_selects(self):
        controller, _ = _setup(['wR . .'])
        result = controller.click(50, 50)
        self.assertEqual(result.action, 'selected')
        self.assertEqual(controller.selected, Position(0, 0))

    def test_first_click_on_empty_ignored(self):
        controller, _ = _setup(['wR . .'])
        result = controller.click(150, 50)
        self.assertEqual(result.action, 'ignored')
        self.assertIsNone(controller.selected)

    def test_outside_click_no_selection_ignored(self):
        controller, _ = _setup(['wR . .'])
        result = controller.click(9999, 9999)
        self.assertEqual(result.action, 'ignored')

    def test_outside_click_with_selection_cancels(self):
        controller, _ = _setup(['wR . .'])
        controller.click(50, 50)
        result = controller.click(9999, 9999)
        self.assertEqual(result.action, 'cancelled')
        self.assertIsNone(controller.selected)

    def test_second_inboard_click_sends_move_and_clears_selection(self):
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, mock_engine)
        controller.click(50, 50)   # בחירה
        result = controller.click(150, 50)  # יעד
        self.assertEqual(result.action, 'move_requested')
        mock_engine.request_move.assert_called_once_with(Position(0, 0), Position(0, 1))
        self.assertIsNone(controller.selected)

    def test_selection_cleared_after_second_click_regardless_of_validity(self):
        controller, _ = _setup(['wR . .'])
        controller.click(50, 50)
        controller.click(150, 50)  # מהלך (חוקי או לא — selection מתנקה)
        self.assertIsNone(controller.selected)
