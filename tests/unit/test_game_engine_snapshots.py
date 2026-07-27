import unittest
from unittest.mock import MagicMock

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine
from tests.unit.game_engine_test_support import make_engine as _engine


class TestGameEngineSnapshots(unittest.TestCase):
    """Verify snapshots use public board state and remain consistent and immutable."""

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

    def test_snapshot_exposes_current_segment_and_total_action_elapsed(self) -> None:
        engine, _ = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 3))

        engine.wait(1500)
        snapshot = engine.snapshot()
        piece = snapshot.pieces[0]
        motion = snapshot.motions[0]

        self.assertEqual(piece.cell, Position(0, 1))
        self.assertEqual(motion.source, Position(0, 1))
        self.assertEqual(motion.destination, Position(0, 2))
        self.assertEqual(motion.elapsed_ms, 500)
        self.assertEqual(motion.duration_ms, 1000)
        self.assertEqual(motion.action_elapsed_ms, 1500)

    def test_knight_snapshot_exposes_one_direct_visual_segment(self) -> None:
        engine, board = _engine(
            [
                "wN .",
                "wP .",
                "bP .",
            ]
        )
        knight = board.get_piece(Position(0, 0))
        friendly_blocker = board.get_piece(Position(1, 0))
        enemy_blocker = board.get_piece(Position(2, 0))
        engine.request_move(Position(0, 0), Position(2, 1))

        engine.wait(1500)
        snapshot = engine.snapshot()
        motion = snapshot.motions[0]

        self.assertIs(board.get_piece(Position(0, 0)), knight)
        self.assertIs(board.get_piece(Position(1, 0)), friendly_blocker)
        self.assertIs(board.get_piece(Position(2, 0)), enemy_blocker)
        self.assertEqual(motion.source, Position(0, 0))
        self.assertEqual(motion.destination, Position(2, 1))
        self.assertEqual(motion.elapsed_ms, 1500)
        self.assertEqual(motion.duration_ms, 3000)

        engine.wait(1500)

        self.assertIs(board.get_piece(Position(2, 1)), knight)
        self.assertIs(board.get_piece(Position(1, 0)), friendly_blocker)
        self.assertIs(board.get_piece(Position(2, 0)), enemy_blocker)

    def test_snapshot_and_nested_piece_views_are_immutable(self) -> None:
        engine, _ = _engine(["wR . ."])
        snapshot = engine.snapshot()

        with self.assertRaises(AttributeError):
            setattr(snapshot, "game_over", True)  # noqa: B010

        with self.assertRaises(AttributeError):
            setattr(snapshot.pieces[0], "state", "captured")  # noqa: B010
