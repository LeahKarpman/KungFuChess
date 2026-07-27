"""Pure, read-only movement rules for each chess piece kind.

Every function here takes a Board and a source Position and returns the
set of legal destination Positions for the piece at that source. Nothing
in this module mutates the Board or any Piece, tracks simulated time or
game-over state, or knows about controllers, pixel coordinates, commands,
text parsing, or rendering.
"""
from __future__ import annotations

from collections.abc import Callable

from ..model.board import Board
from ..model.position import Position

DestinationRule = Callable[[Board, Position], set[Position]]
"""A function computing the legal destinations for a piece at a source cell."""

_KNIGHT_OFFSETS: tuple[tuple[int, int], ...] = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)
_KING_OFFSETS: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


def _sliding(
    board: Board, src: Position, directions: list[tuple[int, int]]
) -> set[Position]:
    """Walk each direction from src until off-board or blocked by a piece.

    A blocking enemy square is included (capturable) but nothing beyond it;
    a blocking friendly square is excluded and also stops the walk.
    """
    destinations: set[Position] = set()
    piece = board.get_piece(src)
    assert piece is not None

    for dr, dc in directions:
        r, c = src.row + dr, src.col + dc
        while board.in_bounds(Position(r, c)):
            pos = Position(r, c)
            blocker = board.get_piece(pos)
            if blocker:
                if blocker.color != piece.color:
                    destinations.add(pos)
                break
            destinations.add(pos)
            r += dr
            c += dc
    return destinations


def rook_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal rook destinations: orthogonal sliding stopped by blockers."""
    return _sliding(board, src, [(-1, 0), (1, 0), (0, -1), (0, 1)])


def bishop_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal bishop destinations: diagonal sliding stopped by blockers."""
    return _sliding(board, src, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


def queen_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal queen destinations: the union of rook and bishop movement."""
    return rook_destinations(board, src) | bishop_destinations(board, src)


def _offset_destinations(
    board: Board,
    src: Position,
    offsets: tuple[tuple[int, int], ...],
) -> set[Position]:
    """Return in-bounds offset destinations not occupied by a friendly piece.

    Shared by king and knight movement, which both jump to a fixed set of
    relative offsets rather than sliding through intermediate squares.
    """
    destinations: set[Position] = set()
    piece = board.get_piece(src)
    assert piece is not None

    for dr, dc in offsets:
        pos = Position(src.row + dr, src.col + dc)
        if not board.in_bounds(pos):
            continue

        blocker = board.get_piece(pos)
        if blocker is None or blocker.color != piece.color:
            destinations.add(pos)

    return destinations


def knight_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal knight destinations: fixed L-shaped jumps that ignore blockers along the way."""
    return _offset_destinations(board, src, _KNIGHT_OFFSETS)


def king_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal king destinations: one cell in any direction."""
    return _offset_destinations(board, src, _KING_OFFSETS)


def pawn_destinations(board: Board, src: Position) -> set[Position]:
    """Return legal pawn destinations for either color.

    Covers a single forward step, an initial double step, and diagonal
    captures of enemy pieces. Direction and the eligible start row are
    derived from the pawn's own color.
    """
    destinations: set[Position] = set()
    piece = board.get_piece(src)
    assert piece is not None

    direction = -1 if piece.color == "w" else 1
    start_row = board.height - 2 if piece.color == "w" else 1

    forward = Position(src.row + direction, src.col)
    if board.in_bounds(forward) and not board.get_piece(forward):
        destinations.add(forward)
        if src.row == start_row:
            double = Position(src.row + 2 * direction, src.col)
            if board.in_bounds(double) and not board.get_piece(double):
                destinations.add(double)

    for dc in [-1, 1]:
        diag = Position(src.row + direction, src.col + dc)
        if board.in_bounds(diag):
            target = board.get_piece(diag)
            if target and target.color != piece.color:
                destinations.add(diag)

    return destinations


_DESTINATION_RULES: dict[str, DestinationRule] = {
    "R": rook_destinations,
    "B": bishop_destinations,
    "Q": queen_destinations,
    "N": knight_destinations,
    "K": king_destinations,
    "P": pawn_destinations,
}


def destination_rule_for(kind: str) -> DestinationRule | None:
    """Return the destination rule registered for a piece kind, or None if unknown."""
    return _DESTINATION_RULES.get(kind)
