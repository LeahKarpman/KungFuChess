import pytest

from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


class TestPiece:
    """Verify construction of valid piece model objects."""

    def test_constructor_initializes_readable_cell(self) -> None:
        cell = Position(2, 3)

        piece = Piece("piece", "w", "K", cell)

        assert piece.cell == cell

    def test_cell_rejects_external_assignment(self) -> None:
        piece = Piece("piece", "w", "K", Position(0, 0))

        with pytest.raises(AttributeError):
            setattr(piece, "cell", Position(1, 1))  # noqa: B010

    def test_rejects_invalid_color(self) -> None:
        with pytest.raises(ValueError, match="^invalid_piece_color$"):
            Piece("piece", "green", "K", Position(0, 0))

    def test_rejects_invalid_kind(self) -> None:
        with pytest.raises(ValueError, match="^invalid_piece_kind$"):
            Piece("piece", "w", "X", Position(0, 0))

    def test_rejects_invalid_lifecycle_state(self) -> None:
        with pytest.raises(ValueError, match="^invalid_piece_state$"):
            Piece(
                "piece",
                "w",
                "K",
                Position(0, 0),
                "flying",  # pyright: ignore[reportArgumentType]
            )
