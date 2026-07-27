import unittest

from kungfu_chess.model.position import Position


class TestPosition(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(Position(1, 2), Position(1, 2))

    def test_inequality(self):
        self.assertNotEqual(Position(1, 2), Position(2, 1))

    def test_repr(self):
        self.assertEqual(repr(Position(3, 4)), "Position(3, 4)")

    def test_hashable(self):
        s = {Position(0, 0), Position(0, 0)}
        self.assertEqual(len(s), 1)
