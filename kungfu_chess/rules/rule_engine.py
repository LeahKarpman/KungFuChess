"""Move-legality orchestration built on top of the piece movement rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Set

from ..model.board import Board
from ..model.position import Position
from .piece_rules import destination_rule_for


@dataclass(frozen=True)
class MoveValidation:
    """Immutable outcome of validating a single move request."""

    ok: bool
    reason: str


class RuleEngine:
    """Answer move-legality queries by delegating to piece_rules; never mutates state."""

    def legal_destinations(self, board: Board, src: Position) -> Set[Position]:
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
        if not board.get_piece(src):
            return MoveValidation(ok=False, reason="no_piece_at_source")
        if dst not in self.legal_destinations(board, src):
            return MoveValidation(ok=False, reason="illegal_move")
        return MoveValidation(ok=True, reason="ok")
