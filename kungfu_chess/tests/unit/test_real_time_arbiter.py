import unittest

from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


class TestRealTimeArbiter(unittest.TestCase):
    """Verify deterministic scheduling and completion of timed actions."""

    def setUp(self) -> None:
        self.arbiter = RealTimeArbiter()
        self.src = Position(0, 0)
        self.dst = Position(0, 1)
        self.piece = Piece("wR_0_0", "w", "R", self.src)

    def test_no_active_motion_initially(self) -> None:
        self.assertFalse(self.arbiter.has_active_motion())

    def test_start_motion_activates(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)
        self.assertTrue(self.arbiter.has_active_motion())

    def test_before_arrival_no_event(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(999)

        self.assertEqual(events, [])
        self.assertTrue(self.arbiter.has_active_motion())

    def test_arrival_at_1000ms(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        events = self.arbiter.advance_time(1000)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].destination, self.dst)
        self.assertFalse(self.arbiter.has_active_motion())

    def test_partial_then_remaining_wait(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        self.assertEqual(self.arbiter.advance_time(500), [])
        events = self.arbiter.advance_time(500)

        self.assertEqual(len(events), 1)

    def test_two_cell_move_takes_2000ms(self) -> None:
        self.arbiter.start_motion(
            self.piece,
            Position(0, 0),
            Position(0, 2),
        )

        self.assertEqual(self.arbiter.advance_time(1999), [])
        events = self.arbiter.advance_time(1)

        self.assertEqual(len(events), 1)

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
            [event.piece_id for event in events],
            ["wR_0_0", "bR_2_0"],
        )
        self.assertFalse(self.arbiter.has_active_motion())

    def test_active_motions_are_immutable_copies(self) -> None:
        self.arbiter.start_motion(self.piece, self.src, self.dst)

        motions = self.arbiter.active_motions()

        self.assertEqual(len(motions), 1)
        self.assertEqual(motions[0].piece_id, "wR_0_0")
        self.assertEqual(motions[0].piece_color, "w")
        self.assertFalse(hasattr(motions[0], "piece"))

        with self.assertRaises(AttributeError):
            setattr(motions[0], "elapsed_ms", 500)

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

    def test_jump_is_scheduled_without_becoming_active_motion(self) -> None:
        landing = Position(1, 1)
        jumper = Piece("wK_1_1", "w", "K", landing)

        self.arbiter.start_jump(jumper, landing)

        self.assertTrue(self.arbiter.is_piece_busy("wK_1_1"))
        self.assertFalse(self.arbiter.has_active_motion())
        self.assertEqual(self.arbiter.active_motions(), ())

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
        self.assertEqual(event.piece_id, self.piece.id)

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
