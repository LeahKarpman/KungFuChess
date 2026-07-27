# pyright: reportOptionalMemberAccess=false

import unittest
from unittest.mock import MagicMock

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.events import MoveCompleted, RestStarted
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import MoveValidation, RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class _FalseyRuleEngine(RuleEngine):
    """Expose whether a falsey injected validation service is actually used."""

    def __bool__(self) -> bool:
        return False

    def validate_move(
        self,
        board: Board,
        src: Position,
        dst: Position,
    ) -> MoveValidation:
        return MoveValidation(ok=False, reason="injected_rule_engine")


class _FalseyArbiter(RealTimeArbiter):
    """Expose whether a falsey injected scheduling service is actually used."""

    def __bool__(self) -> bool:
        return False

    def is_piece_busy(self, piece_id: str) -> bool:
        return True


class TestMoveRequests(unittest.TestCase):
    """Verify move requests, rejection, and scheduling delegation."""

    def test_legal_move_returns_ok(self) -> None:
        engine, _ = _engine([". . .", ". wR .", ". . ."])

        result = engine.request_move(
            Position(1, 1),
            Position(1, 2),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "ok")

    def test_uses_falsey_injected_rule_engine(self) -> None:
        board = parse_board(["wR ."])
        engine = GameEngine(
            board,
            rule_engine=_FalseyRuleEngine(),
            arbiter=RealTimeArbiter(),
        )

        result = engine.request_move(Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "injected_rule_engine")

    def test_uses_falsey_injected_arbiter(self) -> None:
        board = parse_board(["wR ."])
        engine = GameEngine(
            board,
            rule_engine=RuleEngine(),
            arbiter=_FalseyArbiter(),
        )

        result = engine.request_move(Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "piece_busy")

    def test_empty_source_reason_propagates_without_starting_motion(self) -> None:
        engine, _ = _engine([". ."])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "empty_source")
        self.assertEqual(engine.snapshot(), before)
        self.assertEqual(engine.consume_events(), ())

    def test_friendly_destination_reason_propagates_without_starting_motion(
        self,
    ) -> None:
        engine, _ = _engine(["wR wP"])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "friendly_destination")
        self.assertEqual(engine.snapshot(), before)
        self.assertEqual(engine.consume_events(), ())

    def test_illegal_piece_move_reason_propagates_without_starting_motion(
        self,
    ) -> None:
        engine, _ = _engine([". . .", ". wR .", ". . ."])
        before = engine.snapshot()

        result = engine.request_move(
            Position(1, 1),
            Position(0, 2),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "illegal_piece_move")
        self.assertEqual(engine.snapshot(), before)
        self.assertEqual(engine.consume_events(), ())

    def test_outside_board_reason_propagates_without_starting_motion(self) -> None:
        engine, _ = _engine(["wR ."])
        before = engine.snapshot()

        result = engine.request_move(Position(0, 0), Position(-1, 0))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "outside_board")
        self.assertEqual(engine.snapshot(), before)
        self.assertEqual(engine.consume_events(), ())

    def test_game_over_checked_before_rule_engine(self) -> None:
        mock_rules = MagicMock(spec=RuleEngine)
        board = parse_board([". wR ."])
        engine = GameEngine(
            board,
            mock_rules,
            RealTimeArbiter(),
        )
        engine._game_over = True

        result = engine.request_move(
            Position(0, 1),
            Position(0, 2),
        )

        self.assertEqual(result.reason, "game_over")
        mock_rules.validate_move.assert_not_called()

    def test_busy_piece_rejects_second_move(self) -> None:
        engine, _ = _engine([". wR . . ."])
        engine.request_move(
            Position(0, 1),
            Position(0, 4),
        )

        result = engine.request_move(
            Position(0, 1),
            Position(0, 0),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "piece_busy")

    def test_wait_delegates_to_arbiter(self) -> None:
        mock_arbiter = MagicMock(spec=RealTimeArbiter)
        mock_arbiter.advance_time.return_value = []
        mock_arbiter.next_boundary_ms.return_value = None
        board = parse_board([". wR ."])
        engine = GameEngine(
            board,
            RuleEngine(),
            mock_arbiter,
        )

        engine.wait(500)

        mock_arbiter.advance_time.assert_called_once_with(500)


class TestMoveCompletion(unittest.TestCase):
    """Verify completed moves update board and capture state."""

    def test_arrival_moves_piece_on_board(self) -> None:
        engine, board = _engine([". wR . ."])
        source = Position(0, 1)
        destination = Position(0, 3)
        piece = board.get_piece(source)
        engine.request_move(
            source,
            destination,
        )

        engine.wait(2000)

        self.assertIsNotNone(piece)
        self.assertIsNone(board.get_piece(source))
        self.assertIs(board.get_piece(destination), piece)
        self.assertEqual(piece.cell, destination)
        snapshot_piece = next(p for p in engine.snapshot().pieces if p.id == piece.id)
        self.assertEqual(snapshot_piece.cell, destination)

    def test_captured_piece_keeps_captured_state(self) -> None:
        engine, board = _engine(["wR . bK"])
        source = Position(0, 0)
        destination = Position(0, 2)
        moving_piece = board.get_piece(source)
        captured_piece = board.get_piece(destination)

        engine.request_move(
            source,
            destination,
        )
        engine.wait(2000)

        self.assertIsNotNone(moving_piece)
        self.assertIsNotNone(captured_piece)
        self.assertIsNone(board.get_piece(source))
        self.assertIs(board.get_piece(destination), moving_piece)
        self.assertEqual(moving_piece.cell, destination)
        self.assertEqual(captured_piece.state, "captured")
        self.assertEqual(captured_piece.cell, destination)
        snapshot_piece = next(
            piece for piece in engine.snapshot().pieces if piece.id == moving_piece.id
        )
        self.assertEqual(snapshot_piece.cell, destination)

    def test_intermediate_step_emits_no_completion_and_starts_no_rest(self) -> None:
        engine, board = _engine(["wR . . ."])
        piece = board.get_piece(Position(0, 0))
        engine.request_move(Position(0, 0), Position(0, 3))
        engine.consume_events()

        engine.wait(1000)

        self.assertIs(board.get_piece(Position(0, 1)), piece)
        self.assertEqual(piece.state, "moving")
        self.assertEqual(engine.consume_events(), ())
        self.assertEqual(engine.snapshot().rests, ())

    def test_large_wait_crosses_all_cell_boundaries_in_order(self) -> None:
        engine, board = _engine(["wR . . . ."])
        piece = board.get_piece(Position(0, 0))
        engine.request_move(Position(0, 0), Position(0, 4))
        engine.consume_events()

        engine.wait(4000)

        self.assertIs(board.get_piece(Position(0, 4)), piece)
        self.assertEqual(
            engine.consume_events(),
            (
                MoveCompleted(
                    piece_id=piece.id,
                    piece_kind="R",
                    piece_color="w",
                    source=Position(0, 0),
                    destination=Position(0, 4),
                ),
                RestStarted(
                    piece_id=piece.id,
                    rest_kind="long_rest",
                    duration_ms=10000,
                ),
            ),
        )
