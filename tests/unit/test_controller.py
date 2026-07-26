from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from kungfu_chess.input.controller import Controller
from kungfu_chess.engine.game_engine import GameEngine, JumpResult, MoveResult
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.game_state import PieceSnapshot
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

    def test_clicking_selected_piece_cancels_selection(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.click(50, 50)

        self.assertEqual(result.action, "cancelled")
        self.assertEqual(result.position, Position(0, 0))
        self.assertIsNone(controller.selected)

    def test_clicking_selected_piece_does_not_request_move(self) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=(
                PieceSnapshot(
                    id="piece-a",
                    color="w",
                    kind="R",
                    cell=Position(0, 0),
                    state="idle",
                ),
            )
        )
        controller = Controller(BoardMapper(3, 1), mock_engine)
        controller.click(50, 50)

        result = controller.click(50, 50)

        self.assertEqual(result.action, "cancelled")
        mock_engine.request_move.assert_not_called()

    def test_clicking_selected_piece_leaves_engine_state_unchanged(self) -> None:
        controller, engine = _setup(["wR . ."])
        controller.click(50, 50)
        snapshot_before = engine.snapshot()

        controller.click(50, 50)

        self.assertEqual(engine.snapshot(), snapshot_before)
        self.assertEqual(engine.consume_events(), ())

    def test_clicking_different_friendly_piece_replaces_selection(self) -> None:
        controller, _ = _setup(["wR wN ."])
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.click(150, 50)

        self.assertEqual(result.action, "selected")
        self.assertEqual(result.position, Position(0, 1))
        self.assertEqual(controller.selected, Position(0, 1))

    def test_second_inboard_click_sends_move_and_clears_selection(self) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mock_engine.request_move.return_value = MoveResult(ok=True, reason="ok")
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

    def test_rejected_move_preserves_selection(self) -> None:
        """A move rejected by the engine must not clear the current selection.

        Selection is cleared only when the requested action is accepted and
        actually starts; this supersedes the old expectation that selection
        was cleared regardless of validity.
        """
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mock_engine.request_move.return_value = MoveResult(
            ok=False,
            reason="illegal_piece_move",
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, mock_engine)
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.click(150, 50)

        self.assertEqual(result.action, "move_requested")
        self.assertEqual(controller.selected, Position(0, 0))

    def test_rejected_move_via_real_engine_preserves_selection(self) -> None:
        """Same rule, exercised through the real engine and rule engine.

        A knight on a single-row board has no legal destination, so the
        engine rejects the move with 'illegal_piece_move' and selection survives.
        """
        controller, _ = _setup(["wN . ."])
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.click(150, 50)

        self.assertEqual(result.action, "move_requested")
        self.assertEqual(controller.selected, Position(0, 0))

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
        mock_engine.jump.return_value = JumpResult(ok=True, reason="ok")
        controller = Controller(BoardMapper(3, 3), mock_engine)

        result = controller.jump(150, 250)

        self.assertEqual(result.action, "jump_requested")
        self.assertEqual(result.position, Position(2, 1))
        mock_engine.jump.assert_called_once_with(Position(2, 1))

    def test_jump_does_not_call_snapshot_to_decide_legality(self) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.jump.return_value = JumpResult(ok=True, reason="ok")
        controller = Controller(BoardMapper(3, 3), mock_engine)

        controller.jump(150, 250)

        mock_engine.snapshot.assert_not_called()

    def test_jump_outside_board_is_ignored(self) -> None:
        """Reject an out-of-board jump before it reaches the game engine."""
        mock_engine = MagicMock(spec=GameEngine)
        controller = Controller(BoardMapper(3, 3), mock_engine)

        result = controller.jump(-1, 50)

        self.assertEqual(result.action, "ignored")
        mock_engine.jump.assert_not_called()

    def test_right_click_outside_board_preserves_selection_and_does_not_call_engine(
        self,
    ) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, mock_engine)
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.jump(-1, 50)

        self.assertEqual(result.action, "ignored")
        self.assertEqual(controller.selected, Position(0, 0))
        mock_engine.jump.assert_not_called()

    def test_valid_jump_clears_current_selection(self) -> None:
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.jump(50, 50)

        self.assertEqual(result.action, "jump_requested")
        self.assertIsNone(controller.selected)

    def test_valid_jump_by_piece_b_clears_selection_belonging_to_piece_a(self) -> None:
        """An accepted jump clears the selection even for an unrelated piece."""
        controller, _ = _setup(["wR . wN"])
        controller.click(50, 50)  # select piece A (wR) at (0, 0)
        self.assertEqual(controller.selected, Position(0, 0))

        controller.jump(250, 50)  # piece B (wN) at (0, 2) jumps

        self.assertIsNone(controller.selected)

    def test_rejected_jump_preserves_current_selection(self) -> None:
        mock_engine = MagicMock(spec=GameEngine)
        mock_engine.snapshot.return_value = MagicMock(
            pieces=[MagicMock(cell=Position(0, 0))]
        )
        mock_engine.jump.return_value = JumpResult(ok=False, reason="no_piece_at_position")
        mapper = BoardMapper(3, 1)
        controller = Controller(mapper, mock_engine)
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.jump(150, 50)

        self.assertEqual(result.action, "jump_requested")
        self.assertEqual(controller.selected, Position(0, 0))

    def test_jump_on_empty_cell_preserves_current_selection(self) -> None:
        """Let the engine and rules reject an in-board jump onto an empty cell."""
        controller, _ = _setup(["wR . ."])
        controller.click(50, 50)
        self.assertEqual(controller.selected, Position(0, 0))

        result = controller.jump(150, 50)  # (0, 1) is empty

        self.assertEqual(result.action, "jump_requested")
        self.assertEqual(controller.selected, Position(0, 0))

    def test_busy_piece_jump_rejection_preserves_current_selection(self) -> None:
        controller, engine = _setup(["wR . wN"])
        controller.click(250, 50)  # select wN at (0, 2)
        self.assertEqual(controller.selected, Position(0, 2))
        engine.request_move(Position(0, 0), Position(0, 1))  # wR busy, still on board

        result = controller.jump(50, 50)  # attempt to jump the busy wR

        self.assertEqual(result.action, "jump_requested")
        self.assertEqual(controller.selected, Position(0, 2))


class TestControllerCooldownSelection(unittest.TestCase):
    """Verify that resting pieces follow the same selection rules as moving ones."""

    def test_resting_piece_cannot_be_selected(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # wR now long_rest at (0, 1)

        result = controller.click(150, 50)

        self.assertEqual(result.action, "ignored")
        self.assertIsNone(controller.selected)

    def test_clicking_friendly_resting_piece_preserves_prior_selection(self) -> None:
        controller, engine = _setup(["wR . wN"])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # wR now long_rest at (0, 1); wN stays idle at (0, 2)

        select_result = controller.click(250, 50)
        self.assertEqual(select_result.action, "selected")
        self.assertEqual(controller.selected, Position(0, 2))

        result = controller.click(150, 50)

        self.assertEqual(result.action, "ignored")
        self.assertEqual(controller.selected, Position(0, 2))

    def test_enemy_resting_piece_remains_a_valid_destination(self) -> None:
        controller, engine = _setup(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)  # wR now long_rest at (0, 2)

        controller.click(350, 50)  # select bR at (0, 3)
        result = controller.click(250, 50)  # target the resting enemy at (0, 2)

        self.assertEqual(result.action, "move_requested")
        self.assertIsNone(controller.selected)


class TestControllerSelectionIdentity(unittest.TestCase):
    """Verify selection survives by piece identity, not by stale cell position.

    Selection must not silently keep pointing at a cell whose original
    occupant was captured in place by the opponent — otherwise a later
    click can be misattributed to whatever piece now sits on that cell.
    """

    def test_selected_property_self_heals_after_selected_piece_is_captured(
        self,
    ) -> None:
        controller, engine = _setup(["wR . bR"])
        controller.click(50, 50)  # select wR at (0, 0)
        self.assertEqual(controller.selected, Position(0, 0))

        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)

        self.assertIsNone(controller.selected)

    def test_clicking_another_friendly_piece_reselects_immediately_after_capture(
        self,
    ) -> None:
        """The stale selection must not hijack an unrelated piece's move.

        Before selection was tracked by piece id, this click fell through to
        the final branch and requested a move for the captured cell's new
        (enemy) occupant instead of reselecting the clicked friendly piece —
        and since that request was rejected, selection stayed stuck forever.
        """
        controller, engine = _setup(["wR . bR . wN"])
        controller.click(50, 50)  # select wR at (0, 0)
        self.assertEqual(controller.selected, Position(0, 0))

        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)  # bR now rests at (0, 0)

        result = controller.click(450, 50)  # click own knight at (0, 4)

        self.assertEqual(result.action, "selected")
        self.assertEqual(controller.selected, Position(0, 4))

    def test_reselection_after_capture_can_be_toggled_across_repeated_clicks(
        self,
    ) -> None:
        controller, engine = _setup(["wR . bR . wN"])
        controller.click(50, 50)  # select wR at (0, 0)
        engine.request_move(Position(0, 2), Position(0, 0))  # bR captures wR
        engine.wait(2000)

        first_result = controller.click(450, 50)  # select own knight at (0, 4)
        second_result = controller.click(450, 50)  # cancel that selection
        third_result = controller.click(450, 50)  # select it again

        self.assertEqual(first_result.action, "selected")
        self.assertEqual(second_result.action, "cancelled")
        self.assertEqual(third_result.action, "selected")
        self.assertEqual(controller.selected, Position(0, 4))

    def test_selection_works_immediately_after_rest_completion(self) -> None:
        controller, engine = _setup(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)  # long_rest starts
        engine.wait(10000)  # long_rest completes -> idle

        result = controller.click(150, 50)

        self.assertEqual(result.action, "selected")
        self.assertEqual(controller.selected, Position(0, 1))
