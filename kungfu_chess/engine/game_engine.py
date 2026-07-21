from __future__ import annotations

from dataclasses import dataclass

from ..model.board import Board
from ..model.piece import Piece
from ..model.position import Position
from ..model.events import (
    GameEvent,
    GameOver,
    JumpCompleted,
    JumpStarted,
    MoveCompleted,
    MoveStarted,
    PieceCaptured,
    PiecePromoted,
    RestCompleted,
    RestStarted,
)
from ..model.game_state import GameSnapshot, MotionSnapshot, PieceSnapshot, RestSnapshot
from ..realtime.motion import ArrivalEvent
from ..realtime.real_time_arbiter import RealTimeArbiter
from ..realtime.rest import RestKind
from ..rules.rule_engine import RuleEngine


@dataclass(frozen=True)
class MoveResult:
    """Report whether a move request was accepted and why."""

    ok: bool
    reason: str


@dataclass(frozen=True)
class JumpResult:
    """Report whether a jump request was accepted and why."""

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
        self._events: list[GameEvent] = []

    @property
    def game_over(self) -> bool:
        """Return whether a king has been captured."""
        return self._game_over

    def consume_events(self) -> tuple[GameEvent, ...]:
        """Return every event produced since the last call, then clear the queue."""
        events = tuple(self._events)
        self._events.clear()
        return events

    def _emit(self, event: GameEvent) -> None:
        self._events.append(event)

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
        self._emit(MoveStarted(piece_id=piece.id, source=src, destination=dst))
        return MoveResult(ok=True, reason="ok")

    def jump(self, pos: Position) -> JumpResult:
        """Validate and schedule a jump through the real-time arbiter."""
        if self._game_over:
            return JumpResult(ok=False, reason="game_over")

        piece = self._board.get_piece(pos)
        if piece is not None and self._arbiter.is_piece_busy(piece.id):
            return JumpResult(ok=False, reason="piece_busy")

        validation = self._rules.validate_jump(self._board, pos)
        if not validation.ok:
            return JumpResult(ok=False, reason=validation.reason)

        if piece is None:
            # Defends against a RuleEngine implementation that disagrees with
            # the board about piece presence; the stock RuleEngine never
            # reaches this, since validate_jump already rejected it above.
            return JumpResult(ok=False, reason="no_piece_at_position")

        self._arbiter.start_jump(piece, pos)
        self._board.remove_piece(pos)
        self._emit(JumpStarted(piece_id=piece.id, source=pos, destination=pos))
        return JumpResult(ok=True, reason="ok")

    def wait(self, ms: int) -> None:
        """Advance simulated time in chronological steps, one boundary at a time.

        A single call may span several completions: an already-active rest,
        an arrival, another rest that arrival just started. Stepping only up
        to the nearest boundary each time guarantees an arrival's side
        effects (a capture cancelling a rest, a new rest starting) are
        applied before any later completion is resolved, never after — this
        is what makes a capture cancel a resting piece's cooldown before it
        ever completes, instead of racing it.

        Tie rule for completions landing on the exact same simulated
        millisecond: rest completion, then move arrival, then jump arrival,
        then (within the same kind) start-of-action order.

        Game over is terminal: the instant it is set (by a king capture
        inside a step this loop just took), stepping stops immediately and
        any unused milliseconds from this call are discarded rather than
        applied to another motion or rest. Checking at the top of the loop
        also makes a wait() call issued after the game already ended a
        complete no-op — it never advances the arbiter at all.
        """
        remaining_ms = ms
        while remaining_ms > 0:
            if self._game_over:
                break
            boundary_ms = self._arbiter.next_boundary_ms()
            step_ms = (
                remaining_ms if boundary_ms is None else min(boundary_ms, remaining_ms)
            )
            self._advance_step(step_ms)
            remaining_ms -= step_ms

    def _advance_step(self, ms: int) -> None:
        """Advance the arbiter by exactly one chronological step and apply results."""
        arrival_events = self._arbiter.advance_time(ms)

        for piece_id in self._arbiter.consume_completed_rest_piece_ids():
            self._emit(RestCompleted(piece_id=piece_id))

        for event in arrival_events:
            if event.action_kind == "jump":
                self._apply_jump_arrival(event)
            else:
                self._apply_arrival(event)

    def _apply_jump_arrival(self, event: ArrivalEvent) -> None:
        if self._game_over:
            return

        piece = event.piece
        # Finalize this motion now that we're committed to deciding its
        # outcome — the game_over guard above is what skips this for a
        # later arrival in the same batch, leaving it authoritative rather
        # than orphaning the piece (see RealTimeArbiter.resolve_arrival).
        self._arbiter.resolve_arrival(piece.id)
        target = self._board.get_piece(event.destination)

        winner_color = None
        if target and target.color != piece.color:
            winner_color = self._capture_piece(target, event.destination, piece)

        if not self._board.get_piece(event.destination):
            piece.cell = event.destination
            self._board.add_piece(piece)
            self._emit(
                JumpCompleted(
                    piece_id=piece.id,
                    piece_kind=piece.kind,
                    piece_color=piece.color,
                    source=event.source,
                    destination=event.destination,
                )
            )
            if winner_color is not None:
                self._emit(GameOver(winner_color=winner_color))
            self._start_rest_if_alive(piece, "short_rest", event.leftover_ms)

    def _apply_arrival(self, event: ArrivalEvent) -> None:
        if self._game_over:
            return

        piece = event.piece
        # See the matching comment in _apply_jump_arrival.
        self._arbiter.resolve_arrival(piece.id)

        if self._board.get_piece(event.source) is not piece:
            return

        target = self._board.get_piece(event.destination)
        if target is not None and target.color == piece.color:
            return

        self._board.remove_piece(event.source)

        winner_color = None
        if target:
            winner_color = self._capture_piece(target, event.destination, piece)

        piece.cell = event.destination
        self._board.add_piece(piece)
        self._emit(
            MoveCompleted(
                piece_id=piece.id,
                piece_kind=piece.kind,
                piece_color=piece.color,
                source=event.source,
                destination=event.destination,
            )
        )
        self._try_promote(piece)
        if winner_color is not None:
            self._emit(GameOver(winner_color=winner_color))
        self._start_rest_if_alive(piece, "long_rest", event.leftover_ms)

    def _start_rest_if_alive(
        self, piece: Piece, rest_kind: RestKind, leftover_ms: int
    ) -> None:
        """Begin the piece's cooldown, unless it was captured or the game just ended.

        Checked after capture and promotion resolve, so a piece removed from
        the game during this same arrival never starts a cooldown, and a
        capture that ends the game never grants the capturing piece a rest.
        """
        if piece.state == "captured" or self._game_over:
            return

        self._arbiter.start_rest(piece, rest_kind, elapsed_ms=leftover_ms)
        duration_ms = (
            self._arbiter.long_cooldown_ms
            if rest_kind == "long_rest"
            else self._arbiter.short_cooldown_ms
        )
        self._emit(
            RestStarted(piece_id=piece.id, rest_kind=rest_kind, duration_ms=duration_ms)
        )
        if piece.state == "idle":
            # leftover_ms already covered the full cooldown within this same wait().
            self._emit(RestCompleted(piece_id=piece.id))

    def _capture_piece(
        self, target: Piece, position: Position, capturing_piece: Piece
    ) -> str | None:
        """Apply the complete lifecycle transition for a captured piece.

        Sets self._game_over immediately when the captured piece is a king,
        so a second simultaneous king capture (guarded against at the top of
        _apply_arrival/_apply_jump_arrival) never runs. Returns the winning
        color instead of emitting GameOver itself, so the caller can place
        the event after the completion event, per the approved order.
        """
        target.state = "captured"
        self._arbiter.cancel_action(target.id)
        self._board.remove_piece(position)
        self._emit(
            PieceCaptured(
                captured_piece_id=target.id,
                captured_piece_kind=target.kind,
                captured_piece_color=target.color,
                by_piece_id=capturing_piece.id,
                position=position,
            )
        )
        if target.kind == "K":
            self._game_over = True
            return capturing_piece.color
        return None

    def _try_promote(self, piece: Piece) -> None:
        if piece.kind != "P":
            return

        promotion_row = 0 if piece.color == "w" else self._board.height - 1
        if piece.cell.row == promotion_row:
            piece.kind = "Q"
            self._emit(PiecePromoted(piece_id=piece.id, new_kind="Q"))

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
        rests = tuple(
            RestSnapshot(
                piece_id=rest.piece_id,
                rest_kind=rest.rest_kind,
                elapsed_ms=rest.elapsed_ms,
                duration_ms=rest.duration_ms,
            )
            for rest in self._arbiter.active_rests()
        )
        return GameSnapshot(
            pieces=tuple(pieces),
            motions=motions,
            rests=rests,
            game_over=self._game_over,
            width=self._board.width,
            height=self._board.height,
        )
