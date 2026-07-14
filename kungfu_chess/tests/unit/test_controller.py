from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from kungfu_chess.controller.controller import Controller
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.engine.rule_engine import RuleEngine
from kungfu_chess.io.board_mapper import BoardMapper
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.position import Position


def _setup(lines: list[str]) -> tuple[Controller, GameEngine]:
    """Build a controller and its real engine for a small board."""
    board = parse_board(lines)
    engine = GameEngine(board, RuleEngine(), RealTimeArbiter())
    mapper = BoardMapper(board.width, board.height)
    controller = Controller(mapper, engine)
    return controller, engine


class TestController(unittest.TestCase):
    """Verify click interpretation and selection state."""

    def test_first_click_on_piece_selects(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(50, 50)

        self.assertEqual(result.action, "selected")
        self.assertEqual(controller.selected, Position(0, 0))

    def test_first_click_on_empty_ignored(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(150, 50)

        self.assertEqual(result.action, "ignored")
        self.assertIsNone(controller.selected)

    def test_outside_click_no_selection_ignored(self) -> None:
        controller, _ = _setup(["wR . ."])
        result = controller.click(9999, 9999)

        self.assertEqual(result.action, "ignored")

    def test_outside_click_with_selection_cancels(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)

        result = controller.click(9999, 9999)

        self.assertEqual(result.action, "cancelled")
        self.assertIsNone(controller.selected)

    def test_second_inboard_click_sends_move_and_clears_selection(self) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, mock_engine)
        controller.click(50, 50)

        result = controller.click(150, 50)

        self.assertEqual(result.action, "move_requested")
        mock_engine.request_move.assert_called_once_with(
            Position(0, 0),
            Position(0, 1),
        )
        self.assertIsNone(controller.selected)

    def test_selection_cleared_after_second_click_regardless_of_validity(
        self,
    ) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)

        controller.click(150, 50)

        self.assertIsNone(controller.selected)

    def test_moving_piece_cannot_be_selected(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 2))

        result = controller.click(50, 50)

        self.assertEqual(result.action, "ignored")
        self.assertIsNone(controller.selected)

    def test_selected_piece_can_target_moving_enemy(self) -> None:
        """Forward a moving enemy cell as the selected piece's destination."""
        controller, engine = _setup([". . .", "wK bR .", ". . ."])
        engine.jump(Position(1, 0))
        controller.click(150, 150)

        result = controller.click(50, 150)

        self.assertEqual(result.action, "move_requested")
        self.assertIsNone(controller.selected)

    def test_jump_maps_pixels_and_delegates_to_engine(self) -> None:
        """Forward an in-board jump request without applying game rules."""
        mock_engine = MagicMock(spec=GameEngine)
        controller = Controller(BoardMapper(3, 3), mock_engine)

        result = controller.jump(150, 250)

        self.assertEqual(result.action, "jump_requested")
        self.assertEqual(result.position, Position(2, 1))
        mock_engine.jump.assert_called_once_with(Position(2, 1))
        mock_engine.snapshot.assert_not_called()

    def test_jump_outside_board_is_ignored(self) -> None:
        """Reject an out-of-board jump before it reaches the game engine."""
        mock_engine = MagicMock(spec=GameEngine)
        controller = Controller(BoardMapper(3, 3), mock_engine)

        result = controller.jump(-1, 50)

        self.assertEqual(result.action, "ignored")
        mock_engine.jump.assert_not_called()
