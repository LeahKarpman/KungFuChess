# pyright: reportOptionalMemberAccess=false

import pytest

from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.position import Position


class TestBoardParser:
    def test_empty_input_creates_an_empty_board(self) -> None:
        board = parse_board([])

        assert board.width == 0
        assert board.height == 0
        assert board.all_pieces() == ()

    def test_valid_board(self):
        lines = [
            "wR wN wB wQ wK wB wN wR",
            "wP wP wP wP wP wP wP wP",
            ". . . . . . . .",
            ". . . . . . . .",
            ". . . . . . . .",
            ". . . . . . . .",
            "bP bP bP bP bP bP bP bP",
            "bR bN bB bQ bK bB bN bR",
        ]
        board = parse_board(lines)
        assert board.width == 8
        assert board.height == 8
        piece = board.get_piece(Position(0, 0))
        assert piece.color == "w"
        assert piece.kind == "R"

    def test_empty_cell(self):
        board = parse_board([". .", ". ."])
        assert board.get_piece(Position(0, 0)) is None

    def test_inconsistent_row_raises(self):
        with pytest.raises(ValueError):
            parse_board(["wK wQ", "bK"])

    @pytest.mark.parametrize("token", ["xK", "wX", "K", "wKK"])
    def test_invalid_token_raises(self, token: str):
        with pytest.raises(ValueError, match="^UNKNOWN_TOKEN$"):
            parse_board([f"wK {token}"])

    def test_piece_id_format(self):
        board = parse_board(["wK ."])
        piece = board.get_piece(Position(0, 0))
        assert piece.id == "wK_0_0"
