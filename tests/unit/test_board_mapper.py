import pytest

from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.position import Position


@pytest.fixture
def mapper() -> BoardMapper:
    return BoardMapper(width=8, height=8)


class TestBoardMapper:
    def test_default_zero_origin_behavior_is_unchanged(
        self, mapper: BoardMapper
    ) -> None:
        assert mapper.pixel_to_cell(0, 0) == Position(0, 0)
        assert mapper.pixel_to_cell(799, 799) == Position(7, 7)

    def test_x_0_to_99_maps_col_0(self, mapper: BoardMapper):
        assert mapper.pixel_to_cell(0, 0) == Position(0, 0)
        assert mapper.pixel_to_cell(99, 0) == Position(0, 0)

    def test_x_100_to_199_maps_col_1(self, mapper: BoardMapper):
        assert mapper.pixel_to_cell(100, 0) == Position(0, 1)
        assert mapper.pixel_to_cell(199, 0) == Position(0, 1)

    def test_y_100_to_199_maps_row_1(self, mapper: BoardMapper):
        assert mapper.pixel_to_cell(0, 100) == Position(1, 0)
        assert mapper.pixel_to_cell(0, 199) == Position(1, 0)

    def test_outside_returns_none(self, mapper: BoardMapper):
        assert mapper.pixel_to_cell(800, 0) is None
        assert mapper.pixel_to_cell(0, 800) is None
        assert mapper.pixel_to_cell(-1, 0) is None

    def test_maps_first_cell_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(10, 20) == Position(0, 0)
        assert mapper.pixel_to_cell(109, 119) == Position(0, 0)
        assert mapper.pixel_to_cell(110, 20) == Position(0, 1)

    def test_maps_another_row_and_column_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(210, 320) == Position(3, 2)

    def test_pixel_immediately_before_origin_x_is_outside(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(9, 20) is None

    def test_pixel_immediately_before_origin_y_is_outside(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(10, 19) is None

    def test_final_board_pixel_is_valid_with_non_zero_origin(self) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(809, 819) == Position(7, 7)

    @pytest.mark.parametrize(("x", "y"), [(810, 20), (10, 820)])
    def test_first_pixel_after_board_is_invalid_with_non_zero_origin(
        self, x: int, y: int
    ) -> None:
        mapper = BoardMapper(width=8, height=8, origin_x=10, origin_y=20)

        assert mapper.pixel_to_cell(x, y) is None

    @pytest.mark.parametrize("cell_size", [0, -100])
    def test_rejects_non_positive_cell_size(self, cell_size: int) -> None:
        """Reject mapper configurations that cannot represent board cells."""
        with pytest.raises(ValueError, match="^invalid_cell_size$"):
            BoardMapper(width=8, height=8, cell_size=cell_size)
