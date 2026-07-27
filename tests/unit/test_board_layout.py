import pytest

from kungfu_chess.model.position import Position
from kungfu_chess.ui.layout import BoardLayout


class TestBoardLayout:
    def test_board_pixel_size(self) -> None:
        layout = BoardLayout(cell_size=100)
        assert layout.board_pixel_size(8, 8) == (800, 800)
        assert layout.board_pixel_size(3, 1) == (300, 100)

    def test_cell_top_left_at_origin(self) -> None:
        layout = BoardLayout(cell_size=100)
        assert layout.cell_top_left(Position(0, 0)) == (0, 0)
        assert layout.cell_top_left(Position(1, 2)) == (200, 100)
        assert layout.cell_top_left(Position(7, 7)) == (700, 700)

    def test_cell_top_left_with_non_zero_origin(self) -> None:
        layout = BoardLayout(cell_size=100, origin_x=10, origin_y=20)
        assert layout.cell_top_left(Position(0, 0)) == (10, 20)
        assert layout.cell_top_left(Position(1, 2)) == (210, 120)

    def test_centered_top_left_centers_smaller_content(self) -> None:
        layout = BoardLayout(cell_size=100)
        # A 64x64 sprite inside a 100x100 cell is offset by 18px on each side.
        assert layout.centered_top_left(Position(0, 0), 64, 64) == (18, 18)
        assert layout.centered_top_left(Position(1, 2), 64, 64) == (218, 118)

    def test_centered_top_left_with_non_zero_origin(self) -> None:
        layout = BoardLayout(cell_size=100, origin_x=10, origin_y=20)
        assert layout.centered_top_left(Position(0, 0), 64, 64) == (28, 38)

    @pytest.mark.parametrize("cell_size", [0, -100])
    def test_rejects_non_positive_cell_size(self, cell_size: int) -> None:
        with pytest.raises(ValueError, match="^invalid_cell_size$"):
            BoardLayout(cell_size=cell_size)

    def test_cell_center(self) -> None:
        layout = BoardLayout(cell_size=100)
        assert layout.cell_center(Position(0, 0)) == (50.0, 50.0)
        assert layout.cell_center(Position(1, 2)) == (250.0, 150.0)

    def test_cell_center_with_non_zero_origin(self) -> None:
        layout = BoardLayout(cell_size=100, origin_x=10, origin_y=20)
        assert layout.cell_center(Position(0, 0)) == (60.0, 70.0)

    def test_centered_top_left_at_point_matches_integer_cell_case(self) -> None:
        layout = BoardLayout(cell_size=100)
        assert layout.centered_top_left_at_point(
            (50.0, 50.0), 64, 64
        ) == layout.centered_top_left(
            Position(0, 0), 64, 64
        )

    def test_centered_top_left_at_point_rounds_final_coordinates(self) -> None:
        layout = BoardLayout(cell_size=100)
        assert layout.centered_top_left_at_point((50.2, 50.8), 64, 64) == (18, 19)
