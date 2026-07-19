from __future__ import annotations

import unittest

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.events import (
    GameOver,
    JumpCompleted,
    JumpStarted,
    MoveCompleted,
    MoveStarted,
    PieceCaptured,
    PiecePromoted,
    RestCompleted,
    RestStarted,
)
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.rules.rule_engine import RuleEngine


def _engine(lines: list[str]) -> tuple[GameEngine, Board]:
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter()), board


class TestEventCreation(unittest.TestCase):
    def test_move_produces_move_started_and_move_completed(self) -> None:
        engine, _ = _engine(["wR . ."])

        engine.request_move(Position(0, 0), Position(0, 1))
        started_events = engine.consume_events()

        engine.wait(1000)
        completed_events = engine.consume_events()

        self.assertEqual(
            started_events, (MoveStarted("wR_0_0", Position(0, 0), Position(0, 1)),)
        )
        self.assertIn(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            ),
            completed_events,
        )

    def test_jump_produces_jump_started_and_jump_completed(self) -> None:
        engine, _ = _engine([". wK ."])

        engine.jump(Position(0, 1))
        started_events = engine.consume_events()

        engine.wait(1000)
        completed_events = engine.consume_events()

        self.assertEqual(
            started_events, (JumpStarted("wK_0_1", Position(0, 1), Position(0, 1)),)
        )
        self.assertIn(
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            ),
            completed_events,
        )

    def test_capture_produces_piece_captured(self) -> None:
        """Also covers: normal PieceCaptured exposes id/kind/color/attacker/position."""
        engine, _ = _engine(["wR . bR"])

        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        events = engine.consume_events()
        self.assertIn(
            PieceCaptured(
                captured_piece_id="bR_0_2",
                captured_piece_kind="R",
                captured_piece_color="b",
                by_piece_id="wR_0_0",
                position=Position(0, 2),
            ),
            events,
        )

    def test_promotion_produces_piece_promoted(self) -> None:
        engine, _ = _engine([".", "wP"])

        engine.request_move(Position(1, 0), Position(0, 0))
        engine.wait(1000)

        events = engine.consume_events()
        self.assertIn(PiecePromoted(piece_id="wP_1_0", new_kind="Q"), events)

    def test_move_produces_rest_started(self) -> None:
        engine, _ = _engine(["wR . ."])

        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)

        events = engine.consume_events()
        self.assertIn(
            RestStarted(piece_id="wR_0_0", rest_kind="long_rest", duration_ms=10000), events
        )

    def test_rest_completion_produces_rest_completed(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.wait(1000)
        engine.consume_events()

        engine.wait(10000)
        events = engine.consume_events()

        self.assertIn(RestCompleted(piece_id="wR_0_0"), events)

    def test_king_capture_produces_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])

        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)

        events = engine.consume_events()
        self.assertIn(GameOver(winner_color="w"), events)


class TestEventOrdering(unittest.TestCase):
    def test_move_completed_happens_before_rest_started(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
        )
        rest_started_index = next(
            index for index, event in enumerate(events) if isinstance(event, RestStarted)
        )
        self.assertLess(move_completed_index, rest_started_index)

    def test_rest_started_happens_before_rest_completed_on_immediate_completion(self) -> None:
        """The prompt's own example: motion completes, rest starts, rest completes — one wait()."""
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(11000)  # 1000ms motion + the full 10000ms long_rest in a single call
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            )
        )
        rest_started_index = events.index(
            RestStarted(piece_id="wR_0_0", rest_kind="long_rest", duration_ms=10000)
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wR_0_0"))

        self.assertLess(move_completed_index, rest_started_index)
        self.assertLess(rest_started_index, rest_completed_index)

    def test_events_emitted_in_correct_chronological_order(self) -> None:
        engine, _ = _engine([".", "wP"])
        engine.request_move(Position(1, 0), Position(0, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wP_1_0",
                piece_kind="P",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(0, 0),
            )
        )
        promoted_index = events.index(PiecePromoted(piece_id="wP_1_0", new_kind="Q"))
        rest_started_index = next(
            index for index, event in enumerate(events) if isinstance(event, RestStarted)
        )

        self.assertLess(move_completed_index, promoted_index)
        self.assertLess(promoted_index, rest_started_index)


class TestEventTiming(unittest.TestCase):
    def test_wait_crossing_motion_boundary_produces_correct_sequence(self) -> None:
        engine, _ = _engine(["wR . . ."])
        engine.request_move(Position(0, 0), Position(0, 3))  # 3-cell move, 3000ms
        engine.consume_events()

        engine.wait(1500)  # still mid-flight
        mid_flight_events = engine.consume_events()
        self.assertEqual(mid_flight_events, ())

        engine.wait(1500)  # now arrives at 3000ms total
        arrival_events = engine.consume_events()
        self.assertIn(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 3),
            ),
            arrival_events,
        )

    def test_wait_crossing_rest_boundary_produces_rest_completed(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.wait(1000)  # short_rest starts (2000ms)
        engine.consume_events()

        engine.wait(1000)  # rest still active
        mid_rest_events = engine.consume_events()
        self.assertEqual(mid_rest_events, ())

        engine.wait(1000)  # rest completes (total elapsed 2000ms)
        completed_events = engine.consume_events()
        self.assertIn(RestCompleted(piece_id="wK_0_1"), completed_events)


class TestEventConcurrency(unittest.TestCase):
    def test_multiple_pieces_produce_independent_events(self) -> None:
        engine, _ = _engine(["wR . .", ". . .", "bR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.request_move(Position(2, 0), Position(2, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        self.assertIn(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            ),
            events,
        )
        self.assertIn(
            MoveCompleted(
                piece_id="bR_2_0",
                piece_kind="R",
                piece_color="b",
                source=Position(2, 0),
                destination=Position(2, 1),
            ),
            events,
        )

    def test_event_order_is_deterministic_across_runs(self) -> None:
        def _run() -> tuple:
            engine, _ = _engine(["wR . .", ". . .", "bR . ."])
            engine.request_move(Position(0, 0), Position(0, 1))
            engine.request_move(Position(2, 0), Position(2, 1))
            engine.consume_events()
            engine.wait(1000)
            return engine.consume_events()

        self.assertEqual(_run(), _run())


class TestChronologicalBoundaryOrdering(unittest.TestCase):
    """A single wait() may cross several boundaries; each must resolve in
    simulated-time order, since an earlier arrival can cancel or start a
    later completion (e.g. a capture cancelling a resting piece's cooldown).
    """

    def test_motion_completing_before_existing_rest_orders_move_completed_first(self) -> None:
        engine, _ = _engine(["wK . . .", ". . . .", "wR . . .", ". . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(2, 0), Position(2, 1))  # 1-cell move, 1000ms
        engine.consume_events()

        engine.wait(2000)  # move arrives at 1000ms; king's rest completes at 2000ms
        events = engine.consume_events()

        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_2_0",
                piece_kind="R",
                piece_color="w",
                source=Position(2, 0),
                destination=Position(2, 1),
            )
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        self.assertLess(move_completed_index, rest_completed_index)

    def test_existing_rest_completing_before_motion_orders_rest_completed_first(self) -> None:
        engine, _ = _engine(["wK . . .", "wR . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(1, 3))  # 3-cell move, 3000ms
        engine.consume_events()

        engine.wait(3000)  # king's rest completes at 2000ms; move arrives at 3000ms
        events = engine.consume_events()

        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_1_0",
                piece_kind="R",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 3),
            )
        )
        self.assertLess(rest_completed_index, move_completed_index)

    def test_capturing_resting_piece_cancels_its_rest_without_rest_completed(self) -> None:
        engine, _ = _engine(["wR . .", "bR . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(0, 0))  # captures at 1000ms
        engine.consume_events()

        engine.wait(2000)  # spans the capture (1000ms) and the rest's original 2000ms deadline
        events = engine.consume_events()

        self.assertIn(
            PieceCaptured(
                captured_piece_id="wR_0_0",
                captured_piece_kind="R",
                captured_piece_color="w",
                by_piece_id="bR_1_0",
                position=Position(0, 0),
            ),
            events,
        )
        self.assertFalse(
            any(isinstance(event, RestCompleted) and event.piece_id == "wR_0_0" for event in events)
        )

        snapshot = engine.snapshot()
        self.assertFalse(any(rest.piece_id == "wR_0_0" for rest in snapshot.rests))
        self.assertFalse(any(piece.id == "wR_0_0" for piece in snapshot.pieces))

    def test_rest_and_motion_completing_at_same_millisecond_use_tie_rule(self) -> None:
        engine, _ = _engine(["wK . . .", "wR . . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(1, 2))  # 2-cell move, 2000ms
        engine.consume_events()

        engine.wait(2000)  # rest and move both complete at the same simulated millisecond
        events = engine.consume_events()

        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_completed_index = events.index(
            MoveCompleted(
                piece_id="wR_1_0",
                piece_kind="R",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 2),
            )
        )
        self.assertLess(rest_completed_index, move_completed_index)

    def test_two_motions_and_two_rests_completing_at_different_boundaries_stay_ordered(self) -> None:
        board = parse_board(["wK . . .", "wR . . .", "wR . . .", "wR . . ."])
        arbiter = RealTimeArbiter(short_cooldown_ms=500, long_cooldown_ms=4000)
        engine = GameEngine(board, RuleEngine(), arbiter)

        engine.jump(Position(0, 0))  # king: jump, then short_rest(500ms)
        engine.request_move(Position(1, 0), Position(1, 1))  # piece D: 1-cell, completes with the jump
        engine.consume_events()

        engine.wait(1000)  # jump + D's move complete; king's rest(500ms) and D's rest(4000ms) start
        engine.consume_events()

        engine.request_move(Position(2, 0), Position(2, 1))  # piece B: 1-cell, 1000ms from now
        engine.request_move(Position(3, 0), Position(3, 3))  # piece C: 3-cell, 3000ms from now
        engine.consume_events()

        engine.wait(4000)  # boundaries at 500 (king rest), 1000 (B), 3000 (C), 4000 (D rest)
        events = engine.consume_events()

        rest_a_index = events.index(RestCompleted(piece_id="wK_0_0"))
        move_b_index = events.index(
            MoveCompleted(
                piece_id="wR_2_0",
                piece_kind="R",
                piece_color="w",
                source=Position(2, 0),
                destination=Position(2, 1),
            )
        )
        move_c_index = events.index(
            MoveCompleted(
                piece_id="wR_3_0",
                piece_kind="R",
                piece_color="w",
                source=Position(3, 0),
                destination=Position(3, 3),
            )
        )
        rest_d_index = events.index(RestCompleted(piece_id="wR_1_0"))

        self.assertLess(rest_a_index, move_b_index)
        self.assertLess(move_b_index, move_c_index)
        self.assertLess(move_c_index, rest_d_index)

    def test_jump_arrival_starting_rest_that_completes_within_same_wait(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.consume_events()

        engine.wait(3000)  # 1000ms jump + the full 2000ms short_rest, in one call
        events = engine.consume_events()

        jump_completed_index = events.index(
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            )
        )
        rest_started_index = events.index(
            RestStarted(piece_id="wK_0_1", rest_kind="short_rest", duration_ms=2000)
        )
        rest_completed_index = events.index(RestCompleted(piece_id="wK_0_1"))

        self.assertLess(jump_completed_index, rest_started_index)
        self.assertLess(rest_started_index, rest_completed_index)

    def test_capturing_resting_king_produces_game_over_without_rest_completed(self) -> None:
        engine, _ = _engine(["bK . .", "wR . ."])
        engine.jump(Position(0, 0))
        engine.wait(1000)  # jump completes; short_rest(2000ms) starts, 2000ms remaining
        engine.consume_events()

        engine.request_move(Position(1, 0), Position(0, 0))  # captures at 1000ms
        engine.consume_events()

        engine.wait(2000)  # spans the capture (1000ms) and the rest's original 2000ms deadline
        events = engine.consume_events()

        self.assertIn(
            PieceCaptured(
                captured_piece_id="bK_0_0",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wR_1_0",
                position=Position(0, 0),
            ),
            events,
        )
        self.assertIn(GameOver(winner_color="w"), events)
        self.assertFalse(
            any(isinstance(event, RestCompleted) and event.piece_id == "bK_0_0" for event in events)
        )
        self.assertTrue(engine.game_over)


class TestApprovedCaptureEventOrder(unittest.TestCase):
    """Approved order: PieceCaptured, MoveCompleted/JumpCompleted, PiecePromoted
    (when relevant), GameOver (when relevant), RestStarted (unless game over
    prevents rest).
    """

    def test_move_king_capture_exact_order(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.consume_events()

        engine.wait(2000)
        events = engine.consume_events()

        self.assertEqual(
            events,
            (
                PieceCaptured(
                    captured_piece_id="bK_0_2",
                    captured_piece_kind="K",
                    captured_piece_color="b",
                    by_piece_id="wR_0_0",
                    position=Position(0, 2),
                ),
                MoveCompleted(
                    piece_id="wR_0_0",
                    piece_kind="R",
                    piece_color="w",
                    source=Position(0, 0),
                    destination=Position(0, 2),
                ),
                GameOver(winner_color="w"),
            ),
        )

    def test_jump_king_capture_exact_order(self) -> None:
        """A jump always lands back on its own source cell, so the only way it
        captures a king is if the king moves into that vacated cell while the
        jumper is airborne — the same landing-reservation mechanism already
        exercised by TestLandingReservation. The king's own (harmless) move
        into the empty cell therefore resolves first, ahead of the three
        events under test here.
        """
        engine, _ = _engine([". . .", "wP bK .", ". . ."])
        engine.jump(Position(1, 0))
        engine.request_move(Position(1, 1), Position(1, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        captured_index = events.index(
            PieceCaptured(
                captured_piece_id="bK_1_1",
                captured_piece_kind="K",
                captured_piece_color="b",
                by_piece_id="wP_1_0",
                position=Position(1, 0),
            )
        )
        jump_completed_index = events.index(
            JumpCompleted(
                piece_id="wP_1_0",
                piece_kind="P",
                piece_color="w",
                source=Position(1, 0),
                destination=Position(1, 0),
            )
        )
        game_over_index = events.index(GameOver(winner_color="w"))

        self.assertLess(captured_index, jump_completed_index)
        self.assertLess(jump_completed_index, game_over_index)
        self.assertFalse(
            any(
                isinstance(event, RestStarted) and event.piece_id == "wP_1_0"
                for event in events
            )
        )

    def test_capture_promotion_and_game_over_exact_order(self) -> None:
        engine, _ = _engine(["bK . .", ". wP ."])
        engine.request_move(Position(1, 1), Position(0, 0))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        self.assertEqual(
            events,
            (
                PieceCaptured(
                    captured_piece_id="bK_0_0",
                    captured_piece_kind="K",
                    captured_piece_color="b",
                    by_piece_id="wP_1_1",
                    position=Position(0, 0),
                ),
                MoveCompleted(
                    piece_id="wP_1_1",
                    piece_kind="P",
                    piece_color="w",
                    source=Position(1, 1),
                    destination=Position(0, 0),
                ),
                PiecePromoted(piece_id="wP_1_1", new_kind="Q"),
                GameOver(winner_color="w"),
            ),
        )

    def test_promoted_pawn_captured_later_reports_current_kind(self) -> None:
        engine, _ = _engine([". . .", "wP . .", "bR . ."])
        engine.request_move(Position(1, 0), Position(0, 0))  # promotes to Q
        engine.wait(1000)
        engine.consume_events()

        engine.request_move(Position(2, 0), Position(0, 0))  # rook captures the queen
        engine.consume_events()

        engine.wait(2000)
        events = engine.consume_events()

        self.assertIn(
            PieceCaptured(
                captured_piece_id="wP_1_0",
                captured_piece_kind="Q",
                captured_piece_color="w",
                by_piece_id="bR_2_0",
                position=Position(0, 0),
            ),
            events,
        )

    def test_move_completed_contains_full_payload(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        self.assertIn(
            MoveCompleted(
                piece_id="wR_0_0",
                piece_kind="R",
                piece_color="w",
                source=Position(0, 0),
                destination=Position(0, 1),
            ),
            events,
        )

    def test_jump_completed_contains_full_payload(self) -> None:
        engine, _ = _engine([". wK ."])
        engine.jump(Position(0, 1))
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        self.assertIn(
            JumpCompleted(
                piece_id="wK_0_1",
                piece_kind="K",
                piece_color="w",
                source=Position(0, 1),
                destination=Position(0, 1),
            ),
            events,
        )

    def test_simultaneous_king_captures_first_arrival_wins(self) -> None:
        """Both rooks capture the enemy king in one cell, arriving at the same
        simulated millisecond; only the sequence tie-break (white scheduled
        first) may decide the winner — see RealTimeArbiter's deterministic
        arrival ordering.
        """
        engine, board = _engine(["wK bR", "bK wR"])
        engine.request_move(Position(1, 1), Position(1, 0))  # white rook: scheduled first
        engine.request_move(Position(0, 1), Position(0, 0))  # black rook: scheduled second
        engine.consume_events()

        engine.wait(1000)
        events = engine.consume_events()

        self.assertEqual(
            events,
            (
                PieceCaptured(
                    captured_piece_id="bK_1_0",
                    captured_piece_kind="K",
                    captured_piece_color="b",
                    by_piece_id="wR_1_1",
                    position=Position(1, 0),
                ),
                MoveCompleted(
                    piece_id="wR_1_1",
                    piece_kind="R",
                    piece_color="w",
                    source=Position(1, 1),
                    destination=Position(1, 0),
                ),
                GameOver(winner_color="w"),
            ),
        )

        white_king = board.get_piece(Position(0, 0))
        self.assertIsNotNone(white_king)
        self.assertNotEqual(white_king.state, "captured")
        self.assertTrue(engine.game_over)

    def test_no_rest_started_emitted_after_game_over(self) -> None:
        engine, _ = _engine(["wR . bK"])
        engine.request_move(Position(0, 0), Position(0, 2))
        engine.wait(2000)
        events = engine.consume_events()

        game_over_index = events.index(GameOver(winner_color="w"))
        self.assertFalse(any(isinstance(event, RestStarted) for event in events))
        self.assertFalse(
            any(isinstance(event, RestStarted) for event in events[game_over_index:])
        )


class TestEventImmutability(unittest.TestCase):
    def test_events_are_immutable(self) -> None:
        event = MoveStarted(piece_id="wR_0_0", source=Position(0, 0), destination=Position(0, 1))

        with self.assertRaises(AttributeError):
            setattr(event, "piece_id", "changed")

    def test_consume_events_clears_internal_queue(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        first_call = engine.consume_events()
        second_call = engine.consume_events()

        self.assertGreater(len(first_call), 0)
        self.assertEqual(second_call, ())

    def test_returned_event_tuple_is_not_mutable(self) -> None:
        engine, _ = _engine(["wR . ."])
        engine.request_move(Position(0, 0), Position(0, 1))

        events = engine.consume_events()

        with self.assertRaises(AttributeError):
            events.append(MoveStarted("x", Position(0, 0), Position(0, 1)))


if __name__ == "__main__":
    unittest.main()
