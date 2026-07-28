import pytest

from kungfu_chess.model.board import Board
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def _make_piece(
    row: int,
    col: int,
    color: str = "w",
    kind: str = "K",
) -> Piece:
    pos = Position(row, col)
    return Piece(id=f"{color}{kind}_{row}_{col}", color=color, kind=kind, cell=pos)


def _assert_board_invariant(
    board: Board,
    positions: list[Position],
) -> None:
    for position in positions:
        occupant = board.get_piece(position)
        if occupant is not None:
            assert occupant.cell == position


class TestBoard:
    def test_dimensions(self):
        b = Board(8, 8)
        assert b.width == 8
        assert b.height == 8

    def test_in_bounds(self):
        b = Board(4, 4)
        assert b.in_bounds(Position(0, 0))
        assert not b.in_bounds(Position(4, 0))
        assert not b.in_bounds(Position(0, 4))

    def test_empty_cell_returns_none(self):
        b = Board(4, 4)
        assert b.get_piece(Position(0, 0)) is None

    def test_add_and_get_piece(self):
        b = Board(4, 4)
        p = _make_piece(1, 2)
        b.add_piece(p)
        assert b.get_piece(Position(1, 2)) is p
        assert p.cell == Position(1, 2)
        _assert_board_invariant(b, [Position(1, 2)])

    def test_place_piece_uses_explicit_position_without_touching_other_cell(self):
        board = Board(3, 3)
        original_position = Position(0, 0)
        destination = Position(2, 2)
        existing = Piece("existing", "w", "R", original_position)
        incoming = Piece("incoming", "b", "B", original_position)
        board.add_piece(existing)

        board.place_piece(incoming, destination)

        assert board.get_piece(original_position) is existing
        assert board.get_piece(destination) is incoming
        assert incoming.cell == destination
        _assert_board_invariant(board, [original_position, destination])

    def test_move_piece_preserves_piece_identity_and_attributes(self):
        board = Board(3, 3)
        source = Position(0, 1)
        destination = Position(2, 1)
        piece = Piece("moving", "b", "N", source, "short_rest")
        board.add_piece(piece)

        moved = board.move_piece(source, destination)

        assert moved is piece
        assert board.get_piece(source) is None
        assert board.get_piece(destination) is piece
        assert piece.cell == destination
        assert piece.id == "moving"
        assert piece.color == "b"
        assert piece.kind == "N"
        assert piece.state == "short_rest"
        _assert_board_invariant(board, [source, destination])

    @pytest.mark.parametrize(
        "position",
        [
            Position(-1, 0),
            Position(0, -1),
            Position(2, 0),
            Position(0, 2),
        ],
    )
    def test_add_piece_rejects_out_of_bounds_position(self, position: Position):
        """Keep every stored piece inside the board dimensions."""
        board = Board(2, 2)
        piece = Piece("wK_outside", "w", "K", position)

        with pytest.raises(ValueError, match="^piece_out_of_bounds$"):
            board.add_piece(piece)

    def test_duplicate_raises(self):
        b = Board(4, 4)
        b.add_piece(_make_piece(0, 0))
        with pytest.raises(ValueError):
            b.add_piece(_make_piece(0, 0, color="b"))

    def test_duplicate_piece_id_raises(self) -> None:
        """Reject two board occupants that share one stable identity."""
        board = Board(2, 2)
        first = Piece("shared_id", "w", "K", Position(0, 0))
        second = Piece("shared_id", "b", "K", Position(1, 1))
        board.add_piece(first)

        with pytest.raises(ValueError, match="^duplicate_piece_id$"):
            board.add_piece(second)

    def test_failed_place_piece_out_of_bounds_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(0, 0))
        incoming = Piece("incoming", "b", "K", Position(1, 1))
        board.add_piece(existing)

        with pytest.raises(ValueError, match="^piece_out_of_bounds$"):
            board.place_piece(incoming, Position(2, 1))

        assert board.get_piece(Position(0, 0)) is existing
        assert board.get_piece(Position(1, 1)) is None
        assert incoming.cell == Position(1, 1)
        _assert_board_invariant(board, [Position(0, 0), Position(1, 1)])

    def test_failed_place_piece_occupied_is_atomic(self) -> None:
        board = Board(2, 2)
        destination = Position(0, 0)
        existing = Piece("existing", "w", "K", destination)
        incoming = Piece("incoming", "b", "K", Position(1, 1))
        board.add_piece(existing)

        with pytest.raises(ValueError, match="already occupied"):
            board.place_piece(incoming, destination)

        assert board.get_piece(destination) is existing
        assert board.get_piece(Position(1, 1)) is None
        assert incoming.cell == Position(1, 1)
        _assert_board_invariant(board, [destination, Position(1, 1)])

    def test_failed_place_piece_duplicate_id_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("shared_id", "w", "K", Position(0, 0))
        incoming = Piece("shared_id", "b", "K", Position(1, 0))
        board.add_piece(existing)

        with pytest.raises(ValueError, match="^duplicate_piece_id$"):
            board.place_piece(incoming, Position(1, 1))

        assert board.get_piece(Position(0, 0)) is existing
        assert board.get_piece(Position(1, 0)) is None
        assert board.get_piece(Position(1, 1)) is None
        assert incoming.cell == Position(1, 0)
        _assert_board_invariant(
            board,
            [Position(0, 0), Position(1, 0), Position(1, 1)],
        )

    def test_failed_move_missing_source_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(1, 1))
        board.add_piece(existing)

        with pytest.raises(ValueError, match="^no_piece_at_source$"):
            board.move_piece(Position(0, 0), Position(0, 1))

        assert board.get_piece(Position(1, 1)) is existing
        assert existing.cell == Position(1, 1)
        _assert_board_invariant(board, [Position(0, 0), Position(1, 1)])

    def test_failed_move_out_of_bounds_source_is_atomic(self) -> None:
        board = Board(2, 2)
        existing = Piece("existing", "w", "K", Position(0, 0))
        board.add_piece(existing)

        with pytest.raises(ValueError, match="^source_out_of_bounds$"):
            board.move_piece(Position(-1, 0), Position(1, 1))

        assert board.get_piece(Position(0, 0)) is existing
        assert existing.cell == Position(0, 0)
        _assert_board_invariant(board, [Position(0, 0), Position(1, 1)])

    def test_failed_move_out_of_bounds_destination_is_atomic(self) -> None:
        board = Board(2, 2)
        source = Position(0, 0)
        existing = Piece("existing", "w", "K", source)
        board.add_piece(existing)

        with pytest.raises(ValueError, match="^destination_out_of_bounds$"):
            board.move_piece(source, Position(0, 2))

        assert board.get_piece(source) is existing
        assert existing.cell == source
        _assert_board_invariant(board, [source, Position(1, 1)])

    def test_failed_move_occupied_destination_is_atomic(self) -> None:
        board = Board(2, 2)
        source = Position(0, 0)
        destination = Position(1, 1)
        moving = Piece("moving", "w", "K", source)
        blocker = Piece("blocker", "b", "K", destination)
        board.add_piece(moving)
        board.add_piece(blocker)

        with pytest.raises(ValueError, match="^destination_occupied$"):
            board.move_piece(source, destination)

        assert board.get_piece(source) is moving
        assert board.get_piece(destination) is blocker
        assert moving.cell == source
        assert blocker.cell == destination
        _assert_board_invariant(board, [source, destination])

    def test_remove_piece(self):
        b = Board(4, 4)
        piece = _make_piece(0, 0)
        b.add_piece(piece)
        b.remove_piece(Position(0, 0))
        assert b.get_piece(Position(0, 0)) is None
        assert piece.cell == Position(0, 0)

    def test_all_pieces_returns_current_occupants(self):
        b = Board(2, 2)
        first = _make_piece(0, 0)
        second = _make_piece(1, 1, color="b")
        b.add_piece(first)
        b.add_piece(second)

        assert b.all_pieces() == (first, second)
