import unittest
from unittest.mock import MagicMock
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import MoveValidation, RuleEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def _engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board


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


class TestGameEngine(unittest.TestCase):
    """Verify move orchestration, arrivals, captures, and snapshots."""

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

    def test_missing_source_returns_rule_engine_reason(self) -> None:
        engine, _ = _engine([". ."])

        result = engine.request_move(Position(0, 0), Position(0, 1))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no_piece_at_source")

    def test_illegal_move_returns_reason(self) -> None:
        engine, _ = _engine([". . .", ". wR .", ". . ."])

        result = engine.request_move(
            Position(1, 1),
            Position(0, 2),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "illegal_move")

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

    def test_invalid_move_does_not_mutate_board(self) -> None:
        engine, board = _engine([". wR ."])

        engine.request_move(
            Position(0, 1),
            Position(1, 2),
        )

        self.assertIsNotNone(
            board.get_piece(Position(0, 1)),
        )

    def test_wait_delegates_to_arbiter(self) -> None:
        mock_arbiter = MagicMock(spec=RealTimeArbiter)
        mock_arbiter.advance_time.return_value = []
        board = parse_board([". wR ."])
        engine = GameEngine(
            board,
            RuleEngine(),
            mock_arbiter,
        )

        engine.wait(500)

        mock_arbiter.advance_time.assert_called_once_with(500)

    def test_arrival_moves_piece_on_board(self) -> None:
        engine, board = _engine([". wR . ."])
        engine.request_move(
            Position(0, 1),
            Position(0, 3),
        )

        engine.wait(2000)

        self.assertIsNone(
            board.get_piece(Position(0, 1)),
        )
        self.assertIsNotNone(
            board.get_piece(Position(0, 3)),
        )

    def test_king_capture_sets_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )

        engine.wait(2000)

        self.assertTrue(engine.game_over)

    def test_game_over_blocks_further_moves(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )
        engine.wait(2000)

        result = engine.request_move(
            Position(0, 2),
            Position(0, 0),
        )

        self.assertEqual(result.reason, "game_over")

    def test_snapshot_reads_pieces_through_board_public_api(self) -> None:
        board = MagicMock(spec=Board)
        board.width = 2
        board.height = 1
        piece = Piece(
            "wR_0_0",
            "w",
            "R",
            Position(0, 0),
        )
        board.all_pieces.return_value = (piece,)
        engine = GameEngine(
            board,
            RuleEngine(),
            RealTimeArbiter(),
        )

        snapshot = engine.snapshot()

        board.all_pieces.assert_called_once_with()
        self.assertEqual(snapshot.pieces[0].id, piece.id)

    def test_snapshot_reports_motion_lifecycle(self) -> None:
        engine, _ = _engine(["wR . ."])

        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )
        moving_snapshot = engine.snapshot()

        engine.wait(2000)
        arrived_snapshot = engine.snapshot()

        self.assertEqual(
            moving_snapshot.pieces[0].state,
            "moving",
        )
        self.assertEqual(
            moving_snapshot.pieces[0].cell,
            Position(0, 0),
        )
        self.assertEqual(len(moving_snapshot.motions), 1)
        self.assertEqual(
            arrived_snapshot.pieces[0].state,
            "long_rest",
        )
        self.assertEqual(
            arrived_snapshot.pieces[0].cell,
            Position(0, 2),
        )
        self.assertEqual(arrived_snapshot.motions, ())

    def test_snapshot_contains_each_piece_once_during_move_and_jump(
        self,
    ) -> None:
        """Avoid duplicate piece views when different actions are active."""
        engine, _ = _engine(
            [
                "wR . .",
                ". wK .",
                "bR . .",
            ]
        )
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.jump(Position(1, 1))

        snapshot = engine.snapshot()
        piece_ids = [piece.id for piece in snapshot.pieces]
        motion_ids = {motion.piece_id for motion in snapshot.motions}

        self.assertEqual(len(piece_ids), 3)
        self.assertEqual(len(piece_ids), len(set(piece_ids)))
        self.assertEqual(motion_ids, {"wR_0_0", "wK_1_1"})

    def test_snapshot_and_nested_piece_views_are_immutable(self) -> None:
        engine, _ = _engine(["wR . ."])
        snapshot = engine.snapshot()

        with self.assertRaises(AttributeError):
            setattr(snapshot, "game_over", True)

        with self.assertRaises(AttributeError):
            setattr(snapshot.pieces[0], "state", "captured")

    def test_captured_piece_keeps_captured_state(self) -> None:
        engine, board = _engine(["wR . bK"])
        captured_piece = board.get_piece(Position(0, 2))

        engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )
        engine.wait(2000)

        self.assertIsNotNone(captured_piece)
        self.assertEqual(captured_piece.state, "captured")


class TestConcurrentMotions(unittest.TestCase):
    """Verify independent motions and deterministic arrival collisions."""

    def test_two_distinct_pieces_move_concurrently(self) -> None:
        engine, board = _engine(
            [
                "wR . .",
                ". . .",
                "bR . .",
            ]
        )

        first_result = engine.request_move(
            Position(0, 0),
            Position(0, 2),
        )
        second_result = engine.request_move(
            Position(2, 0),
            Position(2, 2),
        )

        self.assertTrue(first_result.ok)
        self.assertTrue(second_result.ok)

        engine.wait(1000)

        self.assertIsNotNone(board.get_piece(Position(0, 0)))
        self.assertIsNotNone(board.get_piece(Position(2, 0)))

        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 2)).color, "w")
        self.assertEqual(board.get_piece(Position(2, 2)).color, "b")

    def test_snapshot_reports_every_active_motion(self) -> None:
        engine, _ = _engine(
            [
                "wR . .",
                ". . .",
                "bR . .",
            ]
        )
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.request_move(Position(2, 0), Position(2, 2))

        snapshot = engine.snapshot()

        self.assertEqual(len(snapshot.motions), 2)
        self.assertEqual(
            {motion.piece_id for motion in snapshot.motions},
            {"wR_0_0", "bR_2_0"},
        )

    def test_later_enemy_arrival_captures_earlier_arrival(self) -> None:
        engine, board = _engine(
            [
                ". wR .",
                ". . .",
                ". . bR",
            ]
        )
        white_piece = board.get_piece(Position(0, 1))

        first_result = engine.request_move(
            Position(0, 1),
            Position(0, 2),
        )
        second_result = engine.request_move(
            Position(2, 2),
            Position(0, 2),
        )

        self.assertTrue(first_result.ok)
        self.assertTrue(second_result.ok)

        engine.wait(1000)

        self.assertIs(board.get_piece(Position(0, 2)), white_piece)

        engine.wait(1000)

        winner = board.get_piece(Position(0, 2))
        self.assertIsNotNone(winner)
        self.assertEqual(winner.color, "b")
        self.assertEqual(white_piece.state, "captured")

    def test_friendly_arrival_is_cancelled_if_destination_became_occupied(
        self,
    ) -> None:
        engine, board = _engine(
            [
                ". wR .",
                ". . .",
                ". . wR",
            ]
        )
        first_piece = board.get_piece(Position(0, 1))
        second_piece = board.get_piece(Position(2, 2))

        first_result = engine.request_move(
            Position(0, 1),
            Position(0, 2),
        )
        second_result = engine.request_move(
            Position(2, 2),
            Position(0, 2),
        )

        self.assertTrue(first_result.ok)
        self.assertTrue(second_result.ok)
        engine.wait(2000)

        self.assertIs(board.get_piece(Position(0, 2)), first_piece)
        self.assertIs(board.get_piece(Position(2, 2)), second_piece)
        self.assertEqual(first_piece.state, "long_rest")
        self.assertEqual(second_piece.state, "idle")

    def test_piece_captured_at_source_does_not_arrive_later(self) -> None:
        engine, board = _engine(
            [
                "wR . . .",
                "bR . . .",
            ]
        )
        captured_mover = board.get_piece(Position(0, 0))

        first_result = engine.request_move(
            Position(0, 0),
            Position(0, 3),
        )
        second_result = engine.request_move(
            Position(1, 0),
            Position(0, 0),
        )

        self.assertTrue(first_result.ok)
        self.assertTrue(second_result.ok)

        engine.wait(1000)

        self.assertEqual(captured_mover.state, "captured")
        self.assertEqual(board.get_piece(Position(0, 0)).color, "b")
        self.assertNotIn(
            captured_mover.id,
            {motion.piece_id for motion in engine.snapshot().motions},
        )

        engine.wait(2000)

        self.assertIsNone(board.get_piece(Position(0, 3)))
        self.assertEqual(captured_mover.state, "captured")


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
        engine.jump(Position(1, 0))
        engine.request_move(
            Position(1, 1),
            Position(1, 0),
        )

        engine.wait(1000)

        jumper = board.get_piece(Position(1, 0))
        self.assertIsNotNone(jumper)
        self.assertEqual(jumper.color, "w")
        self.assertIsNone(
            board.get_piece(Position(1, 1)),
        )

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
        piece = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        self.assertIsNotNone(piece)
        self.assertEqual(piece.state, "moving")

        engine.wait(1000)

        self.assertEqual(piece.state, "short_rest")

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


class TestPromotion(unittest.TestCase):
    """Verify that pawn promotion is applied only when a move arrives."""

    def test_white_pawn_promotes_to_queen_on_top_row(self) -> None:
        engine, board = _engine([".", "wP"])

        result = engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(0, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(promoted)
        self.assertEqual(promoted.kind, "Q")
        self.assertEqual(engine.snapshot().pieces[0].kind, "Q")

    def test_black_pawn_promotes_to_queen_on_bottom_row(self) -> None:
        engine, board = _engine(["bP", "."])

        result = engine.request_move(Position(0, 0), Position(1, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(1, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(promoted)
        self.assertEqual(promoted.kind, "Q")

    def test_pawn_is_not_promoted_before_arrival(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn = board.get_piece(Position(1, 0))

        result = engine.request_move(Position(1, 0), Position(0, 0))

        self.assertTrue(result.ok)
        self.assertIs(board.get_piece(Position(1, 0)), pawn)
        self.assertEqual(pawn.kind, "P")
        self.assertEqual(engine.snapshot().pieces[0].kind, "P")

    def test_non_pawn_keeps_its_kind_on_last_row(self) -> None:
        engine, board = _engine([".", "wR"])

        result = engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        rook = board.get_piece(Position(0, 0))
        self.assertTrue(result.ok)
        self.assertIsNotNone(rook)
        self.assertEqual(rook.kind, "R")


class TestCooldownStateTransitions(unittest.TestCase):
    """Verify move/jump arrival transitions into short_rest/long_rest and back to idle."""

    def test_move_starts_in_moving_state(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        self.assertEqual(board.get_piece(Position(0, 0)).state, "moving")

    def test_jump_starts_in_moving_state(self) -> None:
        engine, board = _engine([". wK ."])
        piece = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        self.assertEqual(piece.state, "moving")

    def test_move_arrival_transitions_to_long_rest(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "long_rest")

    def test_jump_arrival_transitions_to_short_rest(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))

        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "short_rest")

    def test_long_rest_completes_exactly_after_10000ms(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        piece = board.get_piece(Position(0, 1))

        engine.wait(9999)
        self.assertEqual(piece.state, "long_rest")

        engine.wait(1)
        self.assertEqual(piece.state, "idle")

    def test_short_rest_completes_exactly_after_2000ms(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        piece = board.get_piece(Position(0, 1))

        engine.wait(1999)
        self.assertEqual(piece.state, "short_rest")

        engine.wait(1)
        self.assertEqual(piece.state, "idle")

    def test_partial_rest_remains_active(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        engine.wait(4000)

        rests = engine.snapshot().rests
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].elapsed_ms, 4000)
        self.assertEqual(rests[0].duration_ms, 10000)

    def test_excessive_wait_returns_piece_to_idle(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))

        engine.wait(50000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "idle")
        self.assertEqual(engine.snapshot().rests, ())

    def test_cooldown_does_not_start_before_arrival(self) -> None:
        engine, board = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 3))

        engine.wait(500)

        self.assertEqual(engine.snapshot().rests, ())
        self.assertEqual(board.get_piece(Position(0, 0)).state, "moving")

    def test_wait_exactly_ending_at_arrival_begins_rest_with_zero_elapsed(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1000)

        rests = engine.snapshot().rests
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].elapsed_ms, 0)
        self.assertEqual(rests[0].rest_kind, "long_rest")

    def test_wait_crossing_arrival_applies_remaining_time_to_rest(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(1500)

        rests = engine.snapshot().rests
        self.assertEqual(rests[0].elapsed_ms, 500)

    def test_wait_crossing_full_cooldown_returns_piece_to_idle(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(11000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "idle")
        self.assertEqual(engine.snapshot().rests, ())

    def test_single_large_wait_handles_motion_and_partial_cooldown(self) -> None:
        """The prompt's own example: 1000ms motion + 10000ms long cooldown."""
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(5000)

        piece = board.get_piece(Position(0, 1))
        self.assertEqual(piece.state, "long_rest")
        self.assertEqual(engine.snapshot().rests[0].elapsed_ms, 4000)

    def test_single_large_wait_handles_motion_and_full_cooldown(self) -> None:
        """The prompt's own example: wait(11000) must leave the piece idle."""
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        engine.wait(11000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "idle")


class TestCooldownConcurrency(unittest.TestCase):
    def test_two_pieces_rest_concurrently(self) -> None:
        engine, board = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(2, 0), Position(2, 1))

        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "long_rest")
        self.assertEqual(board.get_piece(Position(2, 1)).state, "long_rest")
        self.assertEqual(len(engine.snapshot().rests), 2)

    def test_one_piece_moves_while_another_rests(self) -> None:
        engine, board = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        engine.request_move(Position(2, 0), Position(2, 1))

        self.assertEqual(board.get_piece(Position(0, 1)).state, "long_rest")
        self.assertEqual(board.get_piece(Position(2, 0)).state, "moving")

    def test_different_rest_durations_advance_independently(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.jump(Position(1, 1))

        engine.wait(1000)

        mover = board.get_piece(Position(0, 1))
        jumper = board.get_piece(Position(1, 1))
        self.assertEqual(mover.state, "long_rest")
        self.assertEqual(jumper.state, "short_rest")

        engine.wait(2000)

        self.assertEqual(jumper.state, "idle")
        self.assertEqual(mover.state, "long_rest")

    def test_multiple_arrivals_in_one_wait_start_correct_rest_types(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.jump(Position(1, 1))

        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 1)).state, "long_rest")
        self.assertEqual(board.get_piece(Position(1, 1)).state, "short_rest")

    def test_one_large_wait_handles_several_independent_phase_boundaries(self) -> None:
        engine, board = _engine(["wR . .", ". wK ."])
        engine.request_move(Position(0, 0), Position(0, 1))  # 1000ms motion, then 10000ms rest
        engine.jump(Position(1, 1))  # 1000ms motion, then 2000ms rest

        engine.wait(3000)  # both arrive at 1000ms; jumper's rest completes at 1000+2000

        mover = board.get_piece(Position(0, 1))
        jumper = board.get_piece(Position(1, 1))
        self.assertEqual(jumper.state, "idle")
        self.assertEqual(mover.state, "long_rest")
        rests = engine.snapshot().rests
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].piece_id, mover.id)
        self.assertEqual(rests[0].elapsed_ms, 2000)


class TestCooldownBusyRejection(unittest.TestCase):
    def test_move_request_rejected_during_short_rest(self) -> None:
        engine, board = _engine([". wK . ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "piece_busy")

    def test_move_request_rejected_during_long_rest(self) -> None:
        engine, board = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "piece_busy")

    def test_jump_request_rejected_during_short_rest(self) -> None:
        engine, board = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        piece_before = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        self.assertIs(board.get_piece(Position(0, 1)), piece_before)
        self.assertEqual(piece_before.state, "short_rest")

    def test_jump_request_rejected_during_long_rest(self) -> None:
        engine, board = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        piece_before = board.get_piece(Position(0, 1))

        engine.jump(Position(0, 1))

        self.assertIs(board.get_piece(Position(0, 1)), piece_before)
        self.assertEqual(piece_before.state, "long_rest")

    def test_action_becomes_available_immediately_after_rest_completion(self) -> None:
        engine, board = _engine([". wK . ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)
        engine.wait(2000)

        result = engine.request_move(Position(0, 1), Position(0, 2))

        self.assertTrue(result.ok)


class TestCooldownCaptures(unittest.TestCase):
    def test_resting_piece_blocks_movement_paths(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        self.assertEqual(board.get_piece(Position(0, 2)).state, "long_rest")

        result = engine.request_move(Position(0, 3), Position(0, 0))

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "illegal_move")

    def test_resting_enemy_can_be_captured(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))
        self.assertEqual(resting_piece.state, "long_rest")

        result = engine.request_move(Position(0, 3), Position(0, 2))
        self.assertTrue(result.ok)

        engine.wait(1000)

        self.assertEqual(resting_piece.state, "captured")
        capturer = board.get_piece(Position(0, 2))
        self.assertIsNotNone(capturer)
        self.assertEqual(capturer.color, "b")

    def test_capturing_a_resting_piece_removes_its_rest_record(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))
        self.assertEqual(len(engine.snapshot().rests), 1)

        engine.request_move(Position(0, 3), Position(0, 2))
        engine.wait(1000)

        # The captured piece's own rest record is gone; the capturing piece
        # (which survives and now starts its own long_rest) is unaffected.
        self.assertNotIn(
            resting_piece.id, {rest.piece_id for rest in engine.snapshot().rests}
        )
        self.assertNotIn(resting_piece.id, {p.id for p in engine.snapshot().pieces})

    def test_captured_resting_piece_never_returns_to_idle(self) -> None:
        engine, board = _engine(["wR . . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        resting_piece = board.get_piece(Position(0, 2))

        engine.request_move(Position(0, 3), Position(0, 2))
        engine.wait(1000)
        self.assertEqual(resting_piece.state, "captured")

        engine.wait(50000)

        self.assertEqual(resting_piece.state, "captured")

    def test_moving_piece_captured_during_arrival_does_not_enter_rest(self) -> None:
        engine, board = _engine(["wR . . .", "bR . . ."])
        captured_mover = board.get_piece(Position(0, 0))

        engine.request_move(Position(0, 0), Position(0, 3))
        engine.request_move(Position(1, 0), Position(0, 0))

        engine.wait(1000)

        self.assertEqual(captured_mover.state, "captured")
        self.assertNotIn(
            captured_mover.id, {rest.piece_id for rest in engine.snapshot().rests}
        )

    def test_move_capture_causes_long_rest_for_surviving_mover(self) -> None:
        engine, board = _engine(["wR . bR"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        survivor = board.get_piece(Position(0, 2))
        self.assertEqual(survivor.color, "w")
        self.assertEqual(survivor.state, "long_rest")

    def test_jump_capture_causes_short_rest_for_surviving_jumper(self) -> None:
        engine, board = _engine([". . .", "wP bR .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))

        engine.wait(1000)

        jumper = board.get_piece(Position(1, 0))
        self.assertEqual(jumper.color, "w")
        self.assertEqual(jumper.state, "short_rest")


class TestCooldownPromotion(unittest.TestCase):
    def test_promoted_pawn_retains_its_identity(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn_id = board.get_piece(Position(1, 0)).id

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        self.assertEqual(board.get_piece(Position(0, 0)).id, pawn_id)

    def test_promoted_piece_enters_long_rest_after_move(self) -> None:
        engine, board = _engine([".", "wP"])

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        promoted = board.get_piece(Position(0, 0))
        self.assertEqual(promoted.kind, "Q")
        self.assertEqual(promoted.state, "long_rest")

    def test_rest_snapshot_references_the_promoted_piece(self) -> None:
        engine, board = _engine([".", "wP"])
        pawn_id = board.get_piece(Position(1, 0)).id

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        rests = engine.snapshot().rests
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].piece_id, pawn_id)


class TestCooldownGameOver(unittest.TestCase):
    def test_capturing_a_king_ends_the_game(self) -> None:
        engine, board = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        self.assertTrue(engine.game_over)

    def test_surviving_capturing_piece_receives_no_rest_record_after_game_over(self) -> None:
        engine, board = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))

        engine.wait(2000)

        survivor = board.get_piece(Position(0, 2))
        self.assertEqual(survivor.state, "idle")
        self.assertEqual(engine.snapshot().rests, ())

    def test_jump_capture_of_king_grants_no_rest_to_jumper(self) -> None:
        engine, board = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))

        engine.wait(1000)

        winner = board.get_piece(Position(1, 0))
        self.assertTrue(engine.game_over)
        self.assertEqual(winner.state, "idle")
        self.assertEqual(engine.snapshot().rests, ())
