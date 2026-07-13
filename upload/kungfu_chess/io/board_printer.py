from __future__ import annotations
from ..model.board import Board
from ..model.position import Position

EMPTY = '.'


def print_board(board: Board) -> str:
    rows = []
    for row in range(board.height):
        tokens = []
        for col in range(board.width):
            piece = board.get_piece(Position(row, col))
            tokens.append(f"{piece.color}{piece.kind}" if piece else EMPTY)
        rows.append(' '.join(tokens))
    return '\n'.join(rows)
