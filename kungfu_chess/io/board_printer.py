from __future__ import annotations

from ..engine.game_snapshot import GameSnapshot
from ..model.board import Board
from ..model.position import Position

EMPTY = "."


def print_board(board: Board) -> str:
    """Render the current logical board using canonical piece tokens."""
    tokens_by_cell = {
        piece.cell: f"{piece.color}{piece.kind}" for piece in board.all_pieces()
    }
    return _render_tokens(board.width, board.height, tokens_by_cell)


def print_snapshot(snapshot: GameSnapshot) -> str:
    """Render an immutable game snapshot without accessing live model state."""
    tokens_by_cell = {
        piece.cell: f"{piece.color}{piece.kind}" for piece in snapshot.pieces
    }
    return _render_tokens(snapshot.width, snapshot.height, tokens_by_cell)


def _render_tokens(
    width: int,
    height: int,
    tokens_by_cell: dict[Position, str],
) -> str:
    """Format positioned tokens as canonical rectangular board text."""
    rows = []
    for row in range(height):
        tokens = [tokens_by_cell.get(Position(row, col), EMPTY) for col in range(width)]
        rows.append(" ".join(tokens))
    return "\n".join(rows)
