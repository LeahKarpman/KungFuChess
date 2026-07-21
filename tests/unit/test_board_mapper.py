import unittest
from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.position import Position


class TestBoardMapper(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = BoardMapper(width=8, height=8)

    def test_default_zero_origin_behavior_is_unchanged(self) -> None:
        self.assertEqual(self.mapper.pixel_to_cell(0, 0), Position(0, 0))
        self.assertEqual(self.mapper.pixel_to_cell(799, 799), Position(7, 7))

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

    def test_maps_first_cell_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        self.assertEqual(mapper.pixel_to_cell(10, 20), Position(0, 0))
        self.assertEqual(mapper.pixel_to_cell(109, 119), Position(0, 0))
        self.assertEqual(mapper.pixel_to_cell(110, 20), Position(0, 1))

    def test_maps_another_row_and_column_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        self.assertEqual(mapper.pixel_to_cell(210, 320), Position(3, 2))

    def test_pixel_immediately_before_origin_x_is_outside(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        self.assertIsNone(mapper.pixel_to_cell(9, 20))

    def test_pixel_immediately_before_origin_y_is_outside(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        self.assertIsNone(mapper.pixel_to_cell(10, 19))

    def test_final_board_pixel_is_valid_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        self.assertEqual(mapper.pixel_to_cell(809, 819), Position(7, 7))

    def test_first_pixel_after_board_is_invalid_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        for x, y in ((810, 20), (10, 820)):
            with self.subTest(x=x, y=y):
                self.assertIsNone(mapper.pixel_to_cell(x, y))

    def test_rejects_non_positive_cell_size(self) -> None:
        """Reject mapper configurations that cannot represent board cells."""
        for cell_size in (0, -100):
            with self.subTest(cell_size=cell_size):
                with self.assertRaisesRegex(ValueError, "^invalid_cell_size$"):
                    BoardMapper(width=8, height=8, cell_size=cell_size)
