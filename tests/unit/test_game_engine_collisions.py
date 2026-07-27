# pyright: reportOptionalMemberAccess=false

import unittest

from kungfu_chess.model.position import Position
from tests.unit.game_engine_test_support import make_engine as _engine


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
