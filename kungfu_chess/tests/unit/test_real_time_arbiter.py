import unittest
from kungfu_chess.engine.real_time_arbiter import RealTimeArbiter
from kungfu_chess.model.position import Position


class TestRealTimeArbiter(unittest.TestCase):
    def setUp(self) -> None:
        self.arbiter = RealTimeArbiter()
        self.src = Position(0, 0)
        self.dst = Position(0, 1)  # A one-cell move takes 1000 ms.

    def test_no_active_motion_initially(self):
        self.assertFalse(self.arbiter.has_active_motion())

    def test_start_motion_activates(self):
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        self.assertTrue(self.arbiter.has_active_motion())

    def test_before_arrival_no_event(self):
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        events = self.arbiter.advance_time(999)
        self.assertEqual(events, [])
        self.assertTrue(self.arbiter.has_active_motion())

    def test_arrival_at_1000ms(self):
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        events = self.arbiter.advance_time(1000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].destination, self.dst)
        self.assertFalse(self.arbiter.has_active_motion())

    def test_partial_then_remaining_wait(self):
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        self.assertEqual(self.arbiter.advance_time(500), [])
        events = self.arbiter.advance_time(500)
        self.assertEqual(len(events), 1)

    def test_two_cell_move_takes_2000ms(self):
        self.arbiter.start_motion("wR_0_0", Position(0, 0), Position(0, 2))
        self.assertEqual(self.arbiter.advance_time(1999), [])
        events = self.arbiter.advance_time(1)
        self.assertEqual(len(events), 1)

    def test_multiple_waits_accumulate(self):
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        for _ in range(9):
            self.assertEqual(self.arbiter.advance_time(100), [])
        events = self.arbiter.advance_time(100)
        self.assertEqual(len(events), 1)

    def test_tracks_two_pieces_independently(self) -> None:
        second_source = Position(2, 0)
        second_destination = Position(2, 2)

        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        self.arbiter.start_motion(
            "bR_2_0",
            second_source,
            second_destination,
        )

        self.assertTrue(self.arbiter.is_piece_busy("wR_0_0"))
        self.assertTrue(self.arbiter.is_piece_busy("bR_2_0"))
        self.assertFalse(self.arbiter.is_piece_busy("wK_1_1"))

    def test_rejects_second_motion_for_same_piece(self) -> None:
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)

        with self.assertRaisesRegex(ValueError, "^piece_busy$"):
            self.arbiter.start_motion(
                "wR_0_0",
                self.src,
                Position(0, 2),
            )

    def test_advance_time_returns_every_completed_motion(self) -> None:
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)
        self.arbiter.start_motion(
            "bR_2_0",
            Position(2, 0),
            Position(2, 1),
        )

        events = self.arbiter.advance_time(1000)

        self.assertEqual(
            [event.piece_id for event in events],
            ["wR_0_0", "bR_2_0"],
        )
        self.assertFalse(self.arbiter.has_active_motion())

    def test_active_motions_are_immutable_copies(self) -> None:
        self.arbiter.start_motion("wR_0_0", self.src, self.dst)

        motions = self.arbiter.active_motions()

        self.assertEqual(len(motions), 1)
        self.assertEqual(motions[0].piece_id, "wR_0_0")

        with self.assertRaises(AttributeError):
            setattr(motions[0], "elapsed_ms", 500)

    def test_jump_is_scheduled_without_becoming_active_motion(self) -> None:
        self.arbiter.start_jump("wK_1_1", Position(1, 1))

        self.assertTrue(self.arbiter.is_piece_busy("wK_1_1"))
        self.assertFalse(self.arbiter.has_active_motion())
        self.assertEqual(self.arbiter.active_motions(), ())

    def test_active_jump_can_be_found_by_landing_cell(self) -> None:
        landing = Position(1, 1)
        self.arbiter.start_jump("wK_1_1", landing)

        jump = self.arbiter.active_jump_at(landing)

        self.assertIsNotNone(jump)
        self.assertEqual(jump.piece_id, "wK_1_1")

    def test_jump_completes_after_one_cell_duration(self) -> None:
        landing = Position(1, 1)
        self.arbiter.start_jump("wK_1_1", landing)

        self.assertEqual(self.arbiter.advance_time(999), [])
        events = self.arbiter.advance_time(1)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action_kind, "jump")
        self.assertEqual(events[0].destination, landing)
        self.assertFalse(self.arbiter.is_piece_busy("wK_1_1"))

    def test_move_completion_precedes_jump_at_same_time(self) -> None:
        landing = Position(1, 1)
        self.arbiter.start_jump("wK_1_1", landing)
        self.arbiter.start_motion(
            "bR_1_2",
            Position(1, 2),
            landing,
        )

        events = self.arbiter.advance_time(1000)

        self.assertEqual(
            [event.action_kind for event in events],
            ["move", "jump"],
        )
