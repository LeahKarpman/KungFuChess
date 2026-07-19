import unittest

from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


class TestRealTimeArbiter(unittest.TestCase):
    """Verify deterministic scheduling and completion of timed actions."""

    def setUp(self) -> None:
        self.arbiter = RealTimeArbiter()
        self.src = Position(0, 0)
        self.dst = Position(0, 1)
        self.piece = Piece("wR_0_0", "w", "R", self.src)

    def test_no_active_actions_initially(self) -> None:
        self.assertEqual(self.arbiter.active_actions(), ())

    def test_start_motion_marks_piece_busy(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.assertTrue(self.arbiter.is_piece_busy(self.piece.id))

    def test_before_arrival_no_event(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(999)

        self.assertEqual(events, [])
        self.assertTrue(self.arbiter.is_piece_busy(self.piece.id))

    def test_arrival_at_1000ms(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1000)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].destination, self.dst)
        self.assertFalse(self.arbiter.is_piece_busy(self.piece.id))

    def test_partial_then_remaining_wait(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.assertEqual(self.arbiter.advance_time(500), [])
        events = self.arbiter.advance_time(500)

        self.assertEqual(len(events), 1)

    def test_negative_time_does_not_rewind_active_action(self) -> None:
        """Keep simulated time monotonic when given a negative duration."""
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.assertEqual(self.arbiter.advance_time(500), [])
        self.assertEqual(self.arbiter.advance_time(-250), [])
        events = self.arbiter.advance_time(500)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].piece.id, self.piece.id)

    def test_two_cell_move_takes_2000ms(self) -> None:
        self.arbiter.start_motion(
            self.piece,
            Position(0, 0),
            Position(0, 2),
        )

        self.assertEqual(self.arbiter.advance_time(1999), [])
        events = self.arbiter.advance_time(1)

        self.assertEqual(len(events), 1)

    def test_knight_move_takes_3000ms(self) -> None:
        """Measure a knight's L-shaped route as three cell transitions."""
        source = Position(0, 0)
        destination = Position(2, 1)
        knight = Piece("wN_0_0", "w", "N", source)
        self.arbiter.start_motion(knight, source, destination)

        self.assertEqual(self.arbiter.advance_time(2999), [])
        events = self.arbiter.advance_time(1)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].piece.id, knight.id)

    def test_multiple_waits_accumulate(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        for _ in range(9):
            self.assertEqual(self.arbiter.advance_time(100), [])

        events = self.arbiter.advance_time(100)

        self.assertEqual(len(events), 1)

    def test_tracks_two_pieces_independently(self) -> None:
        second_source = Position(2, 0)
        second_destination = Position(2, 2)
        second_piece = Piece("bR_2_0", "b", "R", second_source)

        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_motion(
            second_piece,
            second_source,
            second_destination,
        )

        self.assertTrue(self.arbiter.is_piece_busy("wR_0_0"))
        self.assertTrue(self.arbiter.is_piece_busy("bR_2_0"))
        self.assertFalse(self.arbiter.is_piece_busy("wK_1_1"))

    def test_rejects_second_motion_for_same_piece(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        with self.assertRaisesRegex(ValueError, "^piece_busy$"):
            self.arbiter.start_motion(
                self.piece,
                self.src,
                Position(0, 2),
            )

    def test_cancel_action_stops_motion_without_changing_piece_state(
        self,
    ) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.piece.state = "captured"

        self.arbiter.cancel_action(self.piece.id)

        self.assertFalse(self.arbiter.is_piece_busy(self.piece.id))
        self.assertEqual(self.arbiter.advance_time(1000), [])
        self.assertEqual(self.piece.state, "captured")

    def test_advance_time_returns_every_completed_motion(self) -> None:
        second_source = Position(2, 0)
        second_piece = Piece("bR_2_0", "b", "R", second_source)

        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_motion(
            second_piece,
            second_source,
            Position(2, 1),
        )

        events = self.arbiter.advance_time(1000)

        self.assertEqual(
            [event.piece.id for event in events],
            ["wR_0_0", "bR_2_0"],
        )
        self.assertEqual(self.arbiter.active_actions(), ())

    def test_active_actions_are_immutable_copies(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        actions = self.arbiter.active_actions()

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].piece_id, "wR_0_0")
        self.assertEqual(actions[0].piece_color, "w")
        self.assertFalse(hasattr(actions[0], "piece"))

        with self.assertRaises(AttributeError):
            setattr(actions[0], "elapsed_ms", 500)

    def test_active_actions_include_moves_and_jumps(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.start_jump(jumper, landing)

        actions = self.arbiter.active_actions()

        self.assertEqual(
            {action.action_kind for action in actions},
            {"move", "jump"},
        )
        self.assertEqual(
            {action.piece_kind for action in actions},
            {"R", "K"},
        )
        self.assertTrue(all(not hasattr(action, "piece") for action in actions))

    def test_active_jump_can_be_found_by_landing_cell(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_jump(jumper, landing)

        jump = self.arbiter.active_jump_at(landing)

        self.assertIsNotNone(jump)
        self.assertEqual(jump.piece_id, "wK_1_1")

    def test_jump_completes_after_one_cell_duration(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        self.arbiter.start_jump(jumper, landing)

        self.assertEqual(self.arbiter.advance_time(999), [])
        events = self.arbiter.advance_time(1)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action_kind, "jump")
        self.assertEqual(events[0].destination, landing)
        self.assertFalse(self.arbiter.is_piece_busy("wK_1_1"))

    def test_move_completion_precedes_jump_at_same_time(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)
        source = Position(1, 2)
        mover = Piece("bR_1_2", "b", "R", source)

        self.arbiter.start_jump(jumper, landing)
        self.arbiter.start_motion(mover, source, landing)

        events = self.arbiter.advance_time(1000)

        self.assertEqual(
            [event.action_kind for event in events],
            ["move", "jump"],
        )

    def test_arrival_event_preserves_piece_identity(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        event = self.arbiter.advance_time(1000)[0]

        self.assertIs(event.piece, self.piece)
        self.assertEqual(event.piece.id, self.piece.id)

    def test_motion_updates_piece_lifecycle(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.assertEqual(self.piece.state, "moving")
        self.assertEqual(self.arbiter.advance_time(999), [])
        self.assertEqual(self.piece.state, "moving")

        self.arbiter.advance_time(1)

        self.assertEqual(self.piece.state, "idle")

    def test_jump_updates_piece_lifecycle(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)

        self.arbiter.start_jump(jumper, landing)
        self.assertEqual(jumper.state, "moving")

        self.arbiter.advance_time(1000)

        self.assertEqual(jumper.state, "idle")

    def test_completion_does_not_revive_captured_piece(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.piece.state = "captured"

        self.arbiter.advance_time(1000)

        self.assertEqual(self.piece.state, "captured")

    def test_advance_time_reports_leftover_time_past_arrival(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1500)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].leftover_ms, 500)

    def test_advance_time_reports_zero_leftover_at_exact_arrival(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1000)

        self.assertEqual(events[0].leftover_ms, 0)

    def test_cooldown_ms_properties_expose_configured_durations(self) -> None:
        arbiter = RealTimeArbiter(short_cooldown_ms=1500, long_cooldown_ms=9000)

        self.assertEqual(arbiter.short_cooldown_ms, 1500)
        self.assertEqual(arbiter.long_cooldown_ms, 9000)

    def test_consume_completed_rest_piece_ids_reports_and_clears(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        self.assertEqual(self.arbiter.consume_completed_rest_piece_ids(), ())

        self.arbiter.advance_time(2000)

        self.assertEqual(self.arbiter.consume_completed_rest_piece_ids(), (self.piece.id,))
        self.assertEqual(self.arbiter.consume_completed_rest_piece_ids(), ())

    def test_next_boundary_ms_is_none_when_nothing_scheduled(self) -> None:
        self.assertIsNone(self.arbiter.next_boundary_ms())

    def test_next_boundary_ms_reports_nearest_motion(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.assertEqual(self.arbiter.next_boundary_ms(), 1000)

        self.arbiter.advance_time(400)

        self.assertEqual(self.arbiter.next_boundary_ms(), 600)

    def test_next_boundary_ms_is_minimum_across_motions_and_rests(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")  # 2000ms remaining

        second_source = Position(2, 0)
        second_piece = Piece("bR_2_0", "b", "R", second_source)
        self.arbiter.start_motion(second_piece, second_source, Position(2, 1))  # 1000ms remaining

        self.assertEqual(self.arbiter.next_boundary_ms(), 1000)

    def test_next_boundary_ms_ignores_cancelled_actions(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.arbiter.cancel_action(self.piece.id)

        self.assertIsNone(self.arbiter.next_boundary_ms())


class TestRealTimeArbiterCooldown(unittest.TestCase):
    """Verify per-piece rest scheduling, busy semantics, and time carry-over."""

    def setUp(self) -> None:
        self.arbiter = RealTimeArbiter(short_cooldown_ms=2000, long_cooldown_ms=10000)
        self.piece = Piece("wP_1_0", "w", "P", Position(1, 0))

    def test_default_cooldown_durations_are_2000_and_10000(self) -> None:
        arbiter = RealTimeArbiter()
        arbiter.start_rest(self.piece, "short_rest")
        self.assertEqual(arbiter.active_rests()[0].duration_ms, 2000)

        other = Piece("wQ_0_0", "w", "Q", Position(0, 0))
        arbiter.start_rest(other, "long_rest")
        rests_by_id = {rest.piece_id: rest for rest in arbiter.active_rests()}
        self.assertEqual(rests_by_id["wQ_0_0"].duration_ms, 10000)

    def test_start_rest_marks_piece_busy_and_sets_state(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.assertTrue(self.arbiter.is_piece_busy(self.piece.id))
        self.assertEqual(self.piece.state, "long_rest")

    def test_long_rest_completes_exactly_after_10000ms(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.advance_time(9999)
        self.assertEqual(self.piece.state, "long_rest")
        self.assertTrue(self.arbiter.is_piece_busy(self.piece.id))

        self.arbiter.advance_time(1)
        self.assertEqual(self.piece.state, "idle")
        self.assertFalse(self.arbiter.is_piece_busy(self.piece.id))

    def test_short_rest_completes_exactly_after_2000ms(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        self.arbiter.advance_time(1999)
        self.assertEqual(self.piece.state, "short_rest")

        self.arbiter.advance_time(1)
        self.assertEqual(self.piece.state, "idle")

    def test_partial_rest_remains_active(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.advance_time(4000)

        active = self.arbiter.active_rests()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].elapsed_ms, 4000)
        self.assertEqual(active[0].duration_ms, 10000)

    def test_excessive_wait_returns_piece_to_idle(self) -> None:
        self.arbiter.start_rest(self.piece, "short_rest")

        self.arbiter.advance_time(50000)

        self.assertEqual(self.piece.state, "idle")
        self.assertEqual(self.arbiter.active_rests(), ())

    def test_start_rest_with_zero_elapsed_begins_at_zero(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=0)

        active = self.arbiter.active_rests()
        self.assertEqual(active[0].elapsed_ms, 0)
        self.assertEqual(self.piece.state, "long_rest")

    def test_start_rest_with_leftover_applies_remaining_time(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=4000)

        active = self.arbiter.active_rests()
        self.assertEqual(active[0].elapsed_ms, 4000)
        self.assertEqual(self.piece.state, "long_rest")

    def test_start_rest_with_leftover_crossing_full_cooldown_ends_idle(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest", elapsed_ms=10000)

        self.assertEqual(self.piece.state, "idle")
        self.assertEqual(self.arbiter.active_rests(), ())

    def test_cancel_action_removes_active_rest(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")

        self.arbiter.cancel_action(self.piece.id)

        self.assertFalse(self.arbiter.is_piece_busy(self.piece.id))
        self.assertEqual(self.arbiter.active_rests(), ())

    def test_cancelled_rest_does_not_resurface_later(self) -> None:
        self.arbiter.start_rest(self.piece, "long_rest")
        self.piece.state = "captured"

        self.arbiter.cancel_action(self.piece.id)
        self.arbiter.advance_time(50000)

        self.assertEqual(self.piece.state, "captured")

    def test_start_rest_rejects_already_busy_piece(self) -> None:
        self.arbiter.start_motion(self.piece, Position(1, 0), Position(1, 1))

        with self.assertRaisesRegex(ValueError, "^piece_busy$"):
            self.arbiter.start_rest(self.piece, "long_rest")

    def test_two_pieces_rest_concurrently_with_independent_elapsed_time(self) -> None:
        other = Piece("bP_6_0", "b", "P", Position(6, 0))
        self.arbiter.start_rest(self.piece, "long_rest")
        self.arbiter.start_rest(other, "short_rest")

        self.arbiter.advance_time(2000)

        self.assertEqual(other.state, "idle")
        self.assertEqual(self.piece.state, "long_rest")
        remaining = self.arbiter.active_rests()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].piece_id, self.piece.id)

    def test_one_piece_rests_while_another_moves(self) -> None:
        mover = Piece("bR_2_0", "b", "R", Position(2, 0))
        self.arbiter.start_rest(self.piece, "short_rest")
        self.arbiter.start_motion(mover, Position(2, 0), Position(2, 1))

        events = self.arbiter.advance_time(2000)

        self.assertEqual(len(events), 1)
        self.assertEqual(self.piece.state, "idle")
        self.assertFalse(self.arbiter.is_piece_busy(mover.id))
