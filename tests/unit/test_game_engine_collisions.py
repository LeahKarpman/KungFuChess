# pyright: reportOptionalMemberAccess=false

import unittest

from kungfu_chess.model.events import MoveCompleted, PieceCaptured, RestStarted
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

        self.assertIsNotNone(board.get_piece(Position(0, 1)))
        self.assertIsNotNone(board.get_piece(Position(2, 1)))

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
        self.assertIs(board.get_piece(Position(1, 2)), second_piece)
        self.assertEqual(first_piece.state, "long_rest")
        self.assertEqual(second_piece.state, "long_rest")

    def test_piece_captured_at_source_does_not_arrive_later(self) -> None:
        engine, board = _engine(
            [
                "wR . . .",
                "bR . . .",
            ]
        )
        captured_mover = board.get_piece(Position(0, 0))

        first_result = engine.request_move(
            Position(1, 0),
            Position(0, 0),
        )
        second_result = engine.request_move(
            Position(0, 0),
            Position(0, 3),
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


class TestPerCellCrossingCollisions(unittest.TestCase):
    """Verify collisions at internal route cells and same-time ordering."""

    def test_friendly_crossing_stops_later_rook_in_previous_cell(self) -> None:
        engine, board = _engine(
            [
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                "wQ . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . wR . . .",
            ]
        )
        queen = board.get_piece(Position(4, 0))
        rook = board.get_piece(Position(7, 4))

        self.assertTrue(
            engine.request_move(Position(4, 0), Position(4, 7)).ok
        )
        engine.wait(1000)
        self.assertTrue(
            engine.request_move(Position(7, 4), Position(0, 4)).ok
        )
        engine.consume_events()

        engine.wait(3000)

        self.assertIs(board.get_piece(Position(4, 4)), queen)
        self.assertIs(board.get_piece(Position(5, 4)), rook)
        self.assertEqual(queen.state, "moving")
        self.assertEqual(rook.state, "long_rest")
        self.assertEqual(
            engine.consume_events(),
            (
                MoveCompleted(
                    piece_id=rook.id,
                    piece_kind="R",
                    piece_color="w",
                    source=Position(7, 4),
                    destination=Position(5, 4),
                ),
                RestStarted(
                    piece_id=rook.id,
                    rest_kind="long_rest",
                    duration_ms=10000,
                ),
            ),
        )

        engine.wait(3000)

        self.assertIs(board.get_piece(Position(4, 7)), queen)
        self.assertEqual(queen.state, "long_rest")
        self.assertNotEqual(rook.state, "captured")

    def test_enemy_crossing_later_rook_captures_and_continues(self) -> None:
        engine, board = _engine(
            [
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                "wQ . . . . . . .",
                ". . . . . . . .",
                ". . . . . . . .",
                ". . . . bR . . .",
            ]
        )
        queen = board.get_piece(Position(4, 0))
        rook = board.get_piece(Position(7, 4))

        engine.request_move(Position(4, 0), Position(4, 7))
        engine.wait(1000)
        engine.request_move(Position(7, 4), Position(0, 4))
        engine.consume_events()

        engine.wait(3000)

        self.assertEqual(queen.state, "captured")
        self.assertIs(board.get_piece(Position(4, 4)), rook)
        self.assertEqual(rook.state, "moving")
        self.assertEqual(
            engine.consume_events(),
            (
                PieceCaptured(
                    captured_piece_id=queen.id,
                    captured_piece_kind="Q",
                    captured_piece_color="w",
                    by_piece_id=rook.id,
                    position=Position(4, 4),
                ),
            ),
        )

        engine.wait(4000)

        self.assertIs(board.get_piece(Position(0, 4)), rook)
        self.assertEqual(rook.state, "long_rest")
        self.assertNotIn(
            queen.id,
            {motion.piece_id for motion in engine.snapshot().motions},
        )

    def test_same_color_simultaneous_arrivals_leave_later_piece_behind(self) -> None:
        engine, board = _engine(
            [
                "wR . .",
                ". wR .",
            ]
        )
        first = board.get_piece(Position(0, 0))
        second = board.get_piece(Position(1, 1))

        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(1, 1), Position(0, 1))
        engine.wait(1000)

        self.assertIs(board.get_piece(Position(0, 1)), first)
        self.assertIs(board.get_piece(Position(1, 1)), second)
        self.assertEqual(first.state, "long_rest")
        self.assertEqual(second.state, "long_rest")

    def test_enemy_simultaneous_arrivals_let_later_piece_capture_first(self) -> None:
        engine, board = _engine(
            [
                "wR . .",
                ". bR .",
            ]
        )
        first = board.get_piece(Position(0, 0))
        second = board.get_piece(Position(1, 1))

        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(1, 1), Position(0, 1))
        engine.wait(1000)

        self.assertEqual(first.state, "captured")
        self.assertIs(board.get_piece(Position(0, 1)), second)
        self.assertEqual(second.state, "long_rest")


class TestKnightDestinationCollisions(unittest.TestCase):
    """Verify that only a knight's final route boundary resolves on the board."""

    def test_friendly_destination_occupant_keeps_knight_at_original_cell(
        self,
    ) -> None:
        engine, board = _engine(
            [
                "wN . .",
                ". . .",
                ". . wR",
            ]
        )
        knight = board.get_piece(Position(0, 0))
        rook = board.get_piece(Position(2, 2))
        engine.request_move(Position(0, 0), Position(2, 1))
        engine.request_move(Position(2, 2), Position(2, 1))

        engine.wait(1000)
        engine.consume_events()
        engine.wait(2000)

        self.assertIs(board.get_piece(Position(0, 0)), knight)
        self.assertIs(board.get_piece(Position(2, 1)), rook)
        self.assertEqual(knight.state, "long_rest")
        self.assertEqual(
            engine.consume_events(),
            (
                MoveCompleted(
                    piece_id=knight.id,
                    piece_kind="N",
                    piece_color="w",
                    source=Position(0, 0),
                    destination=Position(0, 0),
                ),
                RestStarted(
                    piece_id=knight.id,
                    rest_kind="long_rest",
                    duration_ms=10000,
                ),
            ),
        )

    def test_enemy_at_final_destination_is_captured(self) -> None:
        engine, board = _engine(
            [
                "wN .",
                ". .",
                ". bR",
            ]
        )
        knight = board.get_piece(Position(0, 0))
        enemy = board.get_piece(Position(2, 1))
        engine.request_move(Position(0, 0), Position(2, 1))
        engine.consume_events()

        engine.wait(3000)
        events = engine.consume_events()

        self.assertEqual(enemy.state, "captured")
        self.assertIs(board.get_piece(Position(2, 1)), knight)
        self.assertIn(
            PieceCaptured(
                captured_piece_id=enemy.id,
                captured_piece_kind="R",
                captured_piece_color="b",
                by_piece_id=knight.id,
                position=Position(2, 1),
            ),
            events,
        )
        self.assertEqual(knight.state, "long_rest")
