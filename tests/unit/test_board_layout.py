import unittest

from kungfu_chess.model.position import Position
from kungfu_chess.ui.layout import BoardLayout


class TestBoardLayout(unittest.TestCase):
    def test_board_pixel_size(self) -> None:
        layout = BoardLayout(cell_size=100)
        self.assertEqual(layout.board_pixel_size(8, 8), (800, 800))
        self.assertEqual(layout.board_pixel_size(3, 1), (300, 100))

    def test_cell_top_left_at_origin(self) -> None:
        layout = BoardLayout(cell_size=100)
        self.assertEqual(layout.cell_top_left(Position(0, 0)), (0, 0))
        self.assertEqual(layout.cell_top_left(Position(1, 2)), (200, 100))
        self.assertEqual(layout.cell_top_left(Position(7, 7)), (700, 700))

    def test_cell_top_left_with_non_zero_origin(self) -> None:
        layout = BoardLayout(cell_size=100, origin_x=10, origin_y=20)
        self.assertEqual(layout.cell_top_left(Position(0, 0)), (10, 20))
        self.assertEqual(layout.cell_top_left(Position(1, 2)), (210, 120))

    def test_centered_top_left_centers_smaller_content(self) -> None:
        layout = BoardLayout(cell_size=100)
        # A 64x64 sprite inside a 100x100 cell is offset by 18px on each side.
        self.assertEqual(
            layout.centered_top_left(Position(0, 0), 64, 64),
            (18, 18),
        )
        self.assertEqual(
            layout.centered_top_left(Position(1, 2), 64, 64),
            (218, 118),
        )

    def test_centered_top_left_with_non_zero_origin(self) -> None:
        layout = BoardLayout(cell_size=100, origin_x=10, origin_y=20)
        self.assertEqual(
            layout.centered_top_left(Position(0, 0), 64, 64),
            (28, 38),
        )

    def test_rejects_non_positive_cell_size(self) -> None:
        for cell_size in (0, -100):
            with self.subTest(cell_size=cell_size):
                with self.assertRaisesRegex(ValueError, "^invalid_cell_size$"):
                    BoardLayout(cell_size=cell_size)


if __name__ == "__main__":
    unittest.main()
