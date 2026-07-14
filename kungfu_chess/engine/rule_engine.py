from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Set

from ..model.board import Board
from ..model.position import Position


DestinationRule = Callable[[Board, Position], Set[Position]]

_KNIGHT_OFFSETS = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)
_KING_OFFSETS = (
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
)


@dataclass(frozen=True)
class MoveValidation:
    ok: bool
    reason: str


def _sliding(
    board: Board, src: Position, directions: list[tuple[int, int]]
) -> set[Position]:
    destinations: set[Position] = set()
    piece = board.get_piece(src)
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


def _rook_destinations(board: Board, src: Position) -> set[Position]:
    return _sliding(board, src, [(-1, 0), (1, 0), (0, -1), (0, 1)])


def _bishop_destinations(board: Board, src: Position) -> set[Position]:
    return _sliding(board, src, [(-1, -1), (-1, 1), (1, -1), (1, 1)])


def _offset_destinations(
    board: Board,
    src: Position,
    offsets: tuple[tuple[int, int], ...],
) -> set[Position]:
    """Return in-bounds offset destinations not occupied by a friendly piece."""
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


def _knight_destinations(board: Board, src: Position) -> set[Position]:
    return _offset_destinations(board, src, _KNIGHT_OFFSETS)


def _king_destinations(board: Board, src: Position) -> set[Position]:
    return _offset_destinations(board, src, _KING_OFFSETS)


def _pawn_destinations(board: Board, src: Position) -> set[Position]:
    destinations: set[Position] = set()
    piece = board.get_piece(src)
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


_DESTINATIONS: dict[str, DestinationRule] = {
    "R": _rook_destinations,
    "B": _bishop_destinations,
    "Q": lambda b, s: _rook_destinations(b, s) | _bishop_destinations(b, s),
    "N": _knight_destinations,
    "K": _king_destinations,
    "P": _pawn_destinations,
}


class RuleEngine:
    def legal_destinations(self, board: Board, src: Position) -> set[Position]:
        piece = board.get_piece(src)
        if not piece:
            return set()
        fn = _DESTINATIONS.get(piece.kind)
        return fn(board, src) if fn else set()

    def validate_move(
        self, board: Board, src: Position, dst: Position
    ) -> MoveValidation:
        if not board.get_piece(src):
            return MoveValidation(ok=False, reason="no_piece_at_source")
        if dst not in self.legal_destinations(board, src):
            return MoveValidation(ok=False, reason="illegal_move")
        return MoveValidation(ok=True, reason="ok")
