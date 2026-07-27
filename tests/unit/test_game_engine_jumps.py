# pyright: reportOptionalMemberAccess=false

import unittest

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.events import JumpStarted
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import JumpValidation, RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class _RecordingJumpRules:
    def __init__(self, result: JumpValidation | None = None) -> None:
        self.result = result
        self.calls: list[tuple[object, Position]] = []

    def validate_jump(self, board, pos: Position) -> JumpValidation:
        self.calls.append((board, pos))
        if self.result is None:
            raise AssertionError("validate_jump must not be called")
        return self.result


class TestLandingReservation(unittest.TestCase):
    """Verify landing-cell behavior during a jump."""

    def test_enemy_may_move_to_landing_cell(self) -> None:
        lines = [". . .", "wP bR .", ". . ."]
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))

        result = engine.request_move(
            Position(1, 1),
            Position(1, 0),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "ok")

    def test_friendly_piece_blocked_from_landing_cell(self) -> None:
        lines = [". . .", "wP . wR", ". . ."]
        engine, _ = _engine(lines)
        engine.jump(Position(1, 0))

        result = engine.request_move(
            Position(1, 2),
            Position(1, 0),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "landing_reserved")

    def test_enemy_arrives_then_jumper_lands_captures_enemy(
        self,
    ) -> None:
        lines = [". . .", "wP bR .", ". . ."]
        engine, board = _engine(lines)
        landing = Position(1, 0)
        enemy_source = Position(1, 1)
        jumping_piece = board.get_piece(landing)
        captured_piece = board.get_piece(enemy_source)
        engine.jump(landing)
        engine.request_move(
            enemy_source,
            landing,
        )

        engine.wait(1000)

        self.assertIsNotNone(jumping_piece)
        self.assertIsNotNone(captured_piece)
        self.assertIs(board.get_piece(landing), jumping_piece)
        self.assertIsNone(board.get_piece(enemy_source))
        self.assertEqual(jumping_piece.cell, landing)
        self.assertEqual(captured_piece.cell, landing)
        self.assertEqual(captured_piece.state, "captured")
        snapshot_piece = next(
            piece for piece in engine.snapshot().pieces if piece.id == jumping_piece.id
        )
        self.assertEqual(snapshot_piece.cell, landing)

    def test_jump_capture_of_enemy_king_sets_game_over(self) -> None:
        """Apply the king-capture rule through the jump arrival path."""
        engine, board = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        result = engine.request_move(Position(1, 1), Position(1, 0))

        self.assertTrue(result.ok)
        engine.wait(1000)

        winner = board.get_piece(Position(1, 0))
        self.assertIsNotNone(winner)
        self.assertEqual(winner.color, "w")
        self.assertTrue(engine.game_over)


class TestJumpScheduling(unittest.TestCase):
    """Verify that jump timing is delegated to the real-time arbiter."""

    def test_jump_on_empty_cell_leaves_game_unchanged(self) -> None:
        """Ignore a valid board position that does not contain a piece."""
        engine, _ = _engine([". ."])
        before = engine.snapshot()

        engine.jump(Position(0, 0))

        self.assertEqual(engine.snapshot(), before)

    def test_jump_after_game_over_leaves_game_unchanged(self) -> None:
        """Reject new jump actions after a king has been captured."""
        engine, _ = _engine(["wR . bK", ". . wP"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        before = engine.snapshot()

        engine.jump(Position(1, 2))

        self.assertTrue(engine.game_over)
        self.assertEqual(engine.snapshot(), before)

    def test_snapshot_includes_airborne_piece_and_jump_action(self) -> None:
        engine, _ = _engine([". wK ."])
        landing = Position(0, 1)

        engine.jump(landing)
        snapshot = engine.snapshot()

        self.assertEqual(len(snapshot.pieces), 1)
        self.assertEqual(snapshot.pieces[0].id, "wK_0_1")
        self.assertEqual(snapshot.pieces[0].cell, landing)
        self.assertEqual(snapshot.pieces[0].state, "moving")
        self.assertEqual(len(snapshot.motions), 1)
        self.assertEqual(snapshot.motions[0].piece_id, "wK_0_1")
        self.assertEqual(snapshot.motions[0].action_kind, "jump")

    def test_jump_marks_piece_busy_in_arbiter(self) -> None:
        board = parse_board([". wK ."])
        arbiter = RealTimeArbiter()
        engine = GameEngine(
            board,
            RuleEngine(),
            arbiter,
        )

        engine.jump(Position(0, 1))

        self.assertTrue(arbiter.is_piece_busy("wK_0_1"))

    def test_jump_updates_piece_lifecycle(self) -> None:
        engine, board = _engine([". wK ."])
        landing = Position(0, 1)
        piece = board.get_piece(landing)

        engine.jump(landing)

        self.assertIsNotNone(piece)
        self.assertIsNone(board.get_piece(landing))
        self.assertEqual(piece.cell, landing)
        self.assertEqual(piece.state, "moving")

        engine.wait(1000)

        self.assertIs(board.get_piece(landing), piece)
        self.assertEqual(piece.cell, landing)
        self.assertEqual(piece.state, "short_rest")
        snapshot_piece = next(p for p in engine.snapshot().pieces if p.id == piece.id)
        self.assertEqual(snapshot_piece.cell, landing)

    def test_game_engine_does_not_store_airborne_pieces(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))

        self.assertFalse(hasattr(engine, "_airborne"))

    def test_black_piece_can_jump(self) -> None:
        engine, board = _engine([". bK ."])

        engine.jump(Position(0, 1))
        engine.wait(1000)

        piece = board.get_piece(Position(0, 1))
        self.assertIsNotNone(piece)
        self.assertEqual(piece.color, "b")

    def test_two_pieces_can_jump_concurrently(self) -> None:
        engine, board = _engine(["wK . bK"])

        engine.jump(Position(0, 0))
        engine.jump(Position(0, 2))
        engine.wait(1000)

        first_piece = board.get_piece(Position(0, 0))
        second_piece = board.get_piece(Position(0, 2))

        self.assertIsNotNone(first_piece)
        self.assertIsNotNone(second_piece)
        self.assertEqual(first_piece.id, "wK_0_0")
        self.assertEqual(second_piece.id, "bK_0_2")

    def test_moving_piece_cannot_start_jump(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )

        engine.jump(Position(0, 0))
        engine.wait(2000)

        arrived_piece = board.get_piece(Position(0, 2))

        self.assertIsNone(
            board.get_piece(Position(0, 0)),
        )
        self.assertIsNotNone(arrived_piece)
        self.assertEqual(arrived_piece.id, "wR_0_0")


class TestJumpResult(unittest.TestCase):
    """Verify the explicit JumpResult returned by GameEngine.jump()."""

    def test_valid_jump_returns_ok(self) -> None:
        engine, _ = _engine([". wK ."])

        result = engine.jump(Position(0, 1))

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "ok")

    def test_empty_position_returns_no_piece_at_position(self) -> None:
        engine, _ = _engine([". ."])

        result = engine.jump(Position(0, 0))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_piece_at_position")

    def test_busy_piece_returns_piece_busy(self) -> None:
        """A piece still on the board but scheduled elsewhere cannot also jump."""
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 2))

        result = engine.jump(Position(0, 0))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "piece_busy")

    def test_game_over_returns_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        self.assertTrue(engine.game_over)

        result = engine.jump(Position(0, 2))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "game_over")

    def test_game_over_checked_before_rule_engine(self) -> None:
        rules = _RecordingJumpRules()
        board = parse_board([". wK ."])
        engine = GameEngine(board, rules, RealTimeArbiter())
        engine._game_over = True

        result = engine.jump(Position(0, 1))

        self.assertEqual(result.reason, "game_over")
        self.assertEqual(rules.calls, [])

    def test_rejected_jump_does_not_mutate_board(self) -> None:
        engine, board = _engine([". ."])

        engine.jump(Position(0, 0))

        self.assertIsNone(board.get_piece(Position(0, 0)))

    def test_rejected_jump_emits_no_jump_started(self) -> None:
        engine, _ = _engine([". ."])

        engine.jump(Position(0, 0))

        self.assertEqual(engine.consume_events(), ())

    def test_accepted_jump_starts_through_arbiter(self) -> None:
        board = parse_board([". wK ."])
        arbiter = RealTimeArbiter()
        engine = GameEngine(board, RuleEngine(), arbiter)

        engine.jump(Position(0, 1))

        self.assertTrue(arbiter.is_piece_busy("wK_0_1"))

    def test_accepted_jump_emits_exactly_one_jump_started(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))

        events = engine.consume_events()
        jump_started_events = [event for event in events if isinstance(event, JumpStarted)]
        self.assertEqual(len(jump_started_events), 1)

    def test_jump_validation_is_delegated_to_rule_engine(self) -> None:
        rules = _RecordingJumpRules(
            JumpValidation(ok=False, reason="injected_reason")
        )
        board = parse_board([". wK ."])
        engine = GameEngine(board, rules, RealTimeArbiter())

        result = engine.jump(Position(0, 1))

        self.assertEqual(rules.calls, [(board, Position(0, 1))])
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "injected_reason")

    def test_jump_rejects_gracefully_when_rule_engine_disagrees_with_board(self) -> None:
        """A RuleEngine that (incorrectly) approves a jump with no piece there
        must not crash GameEngine.jump(); it must reject cleanly instead.
        """
        rules = _RecordingJumpRules(JumpValidation(ok=True, reason="ok"))
        board = parse_board([". ."])
        engine = GameEngine(board, rules, RealTimeArbiter())

        result = engine.jump(Position(0, 0))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_piece_at_position")

    def test_all_piece_kinds_can_request_jump(self) -> None:
        for kind in ["K", "Q", "R", "B", "N", "P"]:
            with self.subTest(kind=kind):
                engine, _ = _engine([f"w{kind}"])

                result = engine.jump(Position(0, 0))

                self.assertTrue(result.ok)

    def test_both_colors_can_request_jump(self) -> None:
        for color in ["w", "b"]:
            with self.subTest(color=color):
                engine, _ = _engine([f"{color}K"])

                result = engine.jump(Position(0, 0))

                self.assertTrue(result.ok)
