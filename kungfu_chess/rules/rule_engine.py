"""Move-legality orchestration built on top of the piece movement rules."""
from __future__ import annotations

from dataclasses import dataclass

from ..model.board import Board
from ..model.position import Position
from .piece_rules import destination_rule_for


@dataclass(frozen=True)
class MoveValidation:
    """Immutable outcome of validating a single move request."""

    ok: bool
    reason: str


@dataclass(frozen=True)
class JumpValidation:
    """Immutable outcome of validating a single jump request."""

    ok: bool
    reason: str


class RuleEngine:
    """Answer move- and jump-legality queries; never mutates board or piece state."""

    def legal_destinations(self, board: Board, src: Position) -> set[Position]:
        """Return the legal destinations for the piece at src, or empty if there is none."""
        piece = board.get_piece(src)
        if not piece:
            return set()
        rule = destination_rule_for(piece.kind)
        return rule(board, src) if rule else set()

    def validate_move(
        self, board: Board, src: Position, dst: Position
    ) -> MoveValidation:
        """Validate a proposed move, reporting a reason string when it is rejected."""
        if not board.in_bounds(src) or not board.in_bounds(dst):
            return MoveValidation(ok=False, reason="outside_board")

        piece = board.get_piece(src)
        if piece is None:
            return MoveValidation(ok=False, reason="empty_source")

        destination_piece = board.get_piece(dst)
        if (
            destination_piece is not None
            and destination_piece.color == piece.color
        ):
            return MoveValidation(ok=False, reason="friendly_destination")

        if dst not in self.legal_destinations(board, src):
            return MoveValidation(ok=False, reason="illegal_piece_move")

        return MoveValidation(ok=True, reason="ok")

    def validate_jump(self, board: Board, pos: Position) -> JumpValidation:
        """Validate a proposed jump, reporting a reason string when it is rejected."""
        if not board.get_piece(pos):
            return JumpValidation(ok=False, reason="no_piece_at_position")
        return JumpValidation(ok=True, reason="ok")
