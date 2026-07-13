import unittest
from kungfu_chess.io.board_mapper import BoardMapper
from kungfu_chess.model.position import Position


class TestBoardMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = BoardMapper(width=8, height=8)

    def test_x_0_to_99_maps_col_0(self):
        self.assertEqual(self.mapper.pixel_to_cell(0, 0), Position(0, 0))
        self.assertEqual(self.mapper.pixel_to_cell(99, 0), Position(0, 0))

    def test_x_100_to_199_maps_col_1(self):
        self.assertEqual(self.mapper.pixel_to_cell(100, 0), Position(0, 1))
        self.assertEqual(self.mapper.pixel_to_cell(199, 0), Position(0, 1))

    def test_y_100_to_199_maps_row_1(self):
        self.assertEqual(self.mapper.pixel_to_cell(0, 100), Position(1, 0))
        self.assertEqual(self.mapper.pixel_to_cell(0, 199), Position(1, 0))

    def test_outside_returns_none(self):
        self.assertIsNone(self.mapper.pixel_to_cell(800, 0))
        self.assertIsNone(self.mapper.pixel_to_cell(0, 800))
        self.assertIsNone(self.mapper.pixel_to_cell(-1, 0))
