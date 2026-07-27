# pyright: reportOptionalMemberAccess=false

from __future__ import annotations

from pathlib import Path

import kungfu_chess
import pytest
from kungfu_chess.io.board_parser import parse_board
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position

STANDARD_BOARD_PATH = (
    Path(kungfu_chess.__file__).resolve().parent / "resources" / "boards" / "standard_board.txt"
)


@pytest.fixture
def board() -> Board:
    text = STANDARD_BOARD_PATH.read_text(encoding="utf-8")
    lines = text.strip("\n").splitlines()
    return parse_board(lines)


class TestStandardBoardResource:
    """Guard the game-data file loaded by the UI entry point, not just the parser."""

    def test_dimensions_are_standard_8x8(self, board: Board) -> None:
        assert (board.width, board.height) == (8, 8)

    def test_total_piece_count_is_32(self, board: Board) -> None:
        assert len(board.all_pieces()) == 32

    @pytest.mark.parametrize("col", range(8))
    def test_white_pawns_face_row_zero_matching_pawn_rules(
        self, board: Board, col: int
    ) -> None:
        # piece_rules.pawn_destinations moves white toward row 0, from start_row = height - 2.
        piece = board.get_piece(Position(6, col))
        assert piece is not None
        assert (piece.color, piece.kind) == ("w", "P")

    @pytest.mark.parametrize("col", range(8))
    def test_black_pawns_face_row_seven_matching_pawn_rules(
        self, board: Board, col: int
    ) -> None:
        piece = board.get_piece(Position(1, col))
        assert piece is not None
        assert (piece.color, piece.kind) == ("b", "P")

    def test_kings_on_expected_cells(self, board: Board) -> None:
        white_king = board.get_piece(Position(7, 4))
        black_king = board.get_piece(Position(0, 4))
        assert (white_king.color, white_king.kind) == ("w", "K")
        assert (black_king.color, black_king.kind) == ("b", "K")
