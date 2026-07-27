from __future__ import annotations

from ..model.board import Board
from ..model.piece import Piece
from ..model.position import Position

EMPTY = "."


def parse_board(lines: list[str]) -> Board:
    if not lines:
        return Board(0, 0)

    width = len(lines[0].split())
    for line in lines:
        if len(line.split()) != width:
            raise ValueError("ROW_WIDTH_MISMATCH")

    height = len(lines)
    board = Board(width, height)

    for row, line in enumerate(lines):
        for col, token in enumerate(line.split()):
            if token == EMPTY:
                continue
            if len(token) != 2:
                raise ValueError("UNKNOWN_TOKEN")
            pos = Position(row, col)
            try:
                piece = Piece(
                    id=f"{token}_{row}_{col}",
                    color=token[0],
                    kind=token[1],
                    cell=pos,
                )
            except ValueError:
                raise ValueError("UNKNOWN_TOKEN") from None
            board.add_piece(piece)

    return board
