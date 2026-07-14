import unittest
from unittest.mock import MagicMock
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.engine.rule_engine import RuleEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def _engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board


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
            arrived_snapshot.pieces[0].state,
            "idle",
        )

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
        self.assertEqual(first_piece.state, "idle")
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


class TestJumpScheduling(unittest.TestCase):
    """Verify that jump timing is delegated to the real-time arbiter."""

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

        self.assertEqual(piece.state, "idle")

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
