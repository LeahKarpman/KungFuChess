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
        self.arbiter.start_motion('wR_0_0', self.src, self.dst)
        self.assertTrue(self.arbiter.has_active_motion())

    def test_before_arrival_no_event(self):
        self.arbiter.start_motion('wR_0_0', self.src, self.dst)
        events = self.arbiter.advance_time(999)
        self.assertEqual(events, [])
        self.assertTrue(self.arbiter.has_active_motion())

    def test_arrival_at_1000ms(self):
        self.arbiter.start_motion('wR_0_0', self.src, self.dst)
        events = self.arbiter.advance_time(1000)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].destination, self.dst)
        self.assertFalse(self.arbiter.has_active_motion())

    def test_partial_then_remaining_wait(self):
        self.arbiter.start_motion('wR_0_0', self.src, self.dst)
        self.assertEqual(self.arbiter.advance_time(500), [])
        events = self.arbiter.advance_time(500)
        self.assertEqual(len(events), 1)

    def test_two_cell_move_takes_2000ms(self):
        self.arbiter.start_motion('wR_0_0', Position(0, 0), Position(0, 2))
        self.assertEqual(self.arbiter.advance_time(1999), [])
        events = self.arbiter.advance_time(1)
        self.assertEqual(len(events), 1)

    def test_multiple_waits_accumulate(self):
        self.arbiter.start_motion('wR_0_0', self.src, self.dst)
        for _ in range(9):
            self.assertEqual(self.arbiter.advance_time(100), [])
        events = self.arbiter.advance_time(100)
        self.assertEqual(len(events), 1)
