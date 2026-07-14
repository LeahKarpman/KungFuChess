from __future__ import annotations

from dataclasses import dataclass

from ..model.board import Board
from ..model.piece import Piece
from ..model.position import Position
from .game_snapshot import GameSnapshot, MotionSnapshot, PieceSnapshot
from .real_time_arbiter import ArrivalEvent, RealTimeArbiter
from ..rules.rule_engine import RuleEngine


@dataclass(frozen=True)
class MoveResult:
    """Report whether a move request was accepted and why."""

    ok: bool
    reason: str


class GameEngine:
    """Coordinate rules, timed actions, arrivals, and game state."""

    def __init__(
        self,
        board: Board,
        rule_engine: RuleEngine | None = None,
        arbiter: RealTimeArbiter | None = None,
    ) -> None:
        self._board = board
        self._rules = rule_engine if rule_engine is not None else RuleEngine()
        self._arbiter = arbiter if arbiter is not None else RealTimeArbiter()
        self._game_over = False

    @property
    def game_over(self) -> bool:
        """Return whether a king has been captured."""
        return self._game_over

    def request_move(self, src: Position, dst: Position) -> MoveResult:
        """Validate and schedule a move without mutating settled board cells."""
        if self._game_over:
            return MoveResult(ok=False, reason="game_over")

        piece = self._board.get_piece(src)
        if piece is not None and self._arbiter.is_piece_busy(piece.id):
            return MoveResult(ok=False, reason="piece_busy")

        jump = self._arbiter.active_jump_at(dst)
        if jump is not None:
            if piece is not None and piece.color == jump.piece_color:
                return MoveResult(ok=False, reason="landing_reserved")

        validation = self._rules.validate_move(self._board, src, dst)
        if not validation.ok:
            return MoveResult(ok=False, reason=validation.reason)

        assert piece is not None
        self._arbiter.start_motion(piece, src, dst)
        return MoveResult(ok=True, reason="ok")

    def jump(self, pos: Position) -> None:
        """Start a timed jump for an idle piece on the requested cell."""
        if self._game_over:
            return

        piece = self._board.get_piece(pos)
        if piece is None or self._arbiter.is_piece_busy(piece.id):
            return

        self._arbiter.start_jump(piece, pos)
        self._board.remove_piece(pos)

    def wait(self, ms: int) -> None:
        """Advance simulated time and apply every completed action."""
        for event in self._arbiter.advance_time(ms):
            if event.action_kind == "jump":
                self._apply_jump_arrival(event)
            else:
                self._apply_arrival(event)

    def _apply_jump_arrival(self, event: ArrivalEvent) -> None:
        piece = event.piece
        target = self._board.get_piece(event.destination)

        if target and target.color != piece.color:
            self._capture_piece(target, event.destination)

        if not self._board.get_piece(event.destination):
            piece.cell = event.destination
            self._board.add_piece(piece)

    def _apply_arrival(self, event: ArrivalEvent) -> None:
        piece = event.piece

        if self._board.get_piece(event.source) is not piece:
            return

        target = self._board.get_piece(event.destination)
        if target is not None and target.color == piece.color:
            return

        self._board.remove_piece(event.source)

        if target:
            self._capture_piece(target, event.destination)

        piece.cell = event.destination
        self._board.add_piece(piece)
        self._try_promote(piece)

    def _capture_piece(self, target: Piece, position: Position) -> None:
        """Apply the complete lifecycle transition for a captured piece."""
        target.state = "captured"
        self._arbiter.cancel_action(target.id)
        self._board.remove_piece(position)
        if target.kind == "K":
            self._game_over = True

    def _try_promote(self, piece: Piece) -> None:
        if piece.kind != "P":
            return

        promotion_row = 0 if piece.color == "w" else self._board.height - 1
        if piece.cell.row == promotion_row:
            piece.kind = "Q"

    def snapshot(self) -> GameSnapshot:
        """Return an immutable representation of the current game state."""
        active_actions = self._arbiter.active_actions()
        pieces = [
            PieceSnapshot(p.id, p.color, p.kind, p.cell, p.state)
            for p in self._board.all_pieces()
        ]
        visible_piece_ids = {piece.id for piece in pieces}

        pieces.extend(
            PieceSnapshot(
                action.piece_id,
                action.piece_color,
                action.piece_kind,
                action.source,
                "moving",
            )
            for action in active_actions
            if action.piece_id not in visible_piece_ids
        )
        motions = tuple(
            MotionSnapshot(
                piece_id=action.piece_id,
                source=action.source,
                destination=action.destination,
                elapsed_ms=action.elapsed_ms,
                duration_ms=action.duration_ms,
                action_kind=action.action_kind,
            )
            for action in active_actions
        )
        return GameSnapshot(
            pieces=tuple(pieces),
            motions=motions,
            game_over=self._game_over,
            width=self._board.width,
            height=self._board.height,
        )
