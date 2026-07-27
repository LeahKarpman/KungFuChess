"""Arbitration policy for scheduling and resolving timed piece actions."""
from __future__ import annotations

from ..model.piece import Piece
from ..model.position import Position
from .motion import (
    MS_PER_CELL,
    ActionKind,
    ActiveAction,
    ArrivalEvent,
    Motion,
    travel_duration_ms,
)
from .rest import (
    DEFAULT_LONG_COOLDOWN_MS,
    DEFAULT_SHORT_COOLDOWN_MS,
    ActiveRest,
    Rest,
    RestKind,
)


def _completion_priority(action_kind: ActionKind) -> int:
    """Resolve a move before a jump when both complete simultaneously."""
    return 0 if action_kind == "move" else 1


class RealTimeArbiter:
    """Schedule timed piece actions and emit deterministic arrival events.

    Tracks at most one active Motion per piece, advances simulated time
    on request, and resolves completions in a deterministic order. Never
    touches the Board, validates chess rules, or applies capture,
    promotion, or game-over logic — those are GameEngine's job.
    """

    def __init__(
        self,
        short_cooldown_ms: int = DEFAULT_SHORT_COOLDOWN_MS,
        long_cooldown_ms: int = DEFAULT_LONG_COOLDOWN_MS,
    ) -> None:
        self._motions: dict[str, Motion] = {}
        self._rests: dict[str, Rest] = {}
        self._next_sequence = 0
        self._short_cooldown_ms = short_cooldown_ms
        self._long_cooldown_ms = long_cooldown_ms
        self._completed_rest_piece_ids: list[str] = []

    @property
    def short_cooldown_ms(self) -> int:
        """Return the configured short_rest cooldown duration."""
        return self._short_cooldown_ms

    @property
    def long_cooldown_ms(self) -> int:
        """Return the configured long_rest cooldown duration."""
        return self._long_cooldown_ms

    def is_piece_busy(self, piece_id: str) -> bool:
        """Return whether the piece already has a scheduled action or active rest."""
        return piece_id in self._motions or piece_id in self._rests

    def cancel_action(self, piece_id: str) -> None:
        """Stop a scheduled action or active rest without changing the piece lifecycle."""
        self._motions.pop(piece_id, None)
        self._rests.pop(piece_id, None)

    def start_motion(
        self,
        piece: Piece,
        source: Position,
        destination: Position,
    ) -> None:
        """Schedule a regular move for a currently idle piece."""
        self._start_action(
            piece=piece,
            action_kind="move",
            source=source,
            destination=destination,
            duration_ms=travel_duration_ms(piece.kind, source, destination),
        )

    def start_jump(self, piece: Piece, landing: Position) -> None:
        """Schedule a jump that lands on its source cell after one second."""
        self._start_action(
            piece=piece,
            action_kind="jump",
            source=landing,
            destination=landing,
            duration_ms=MS_PER_CELL,
        )

    def next_boundary_ms(self) -> int | None:
        """Return the simulated time until the nearest motion or rest completion.

        Returns None when nothing is left to advance toward. A completed
        motion still awaiting resolve_arrival has nothing left to count
        down — it is excluded so it can never manufacture a zero-length
        boundary; only strictly positive remaining times are considered.
        GameEngine advances time in steps of at most this size so that an
        arrival's side effects (a capture cancelling a rest, a new rest
        starting) are always resolved before a completion that happens
        later in simulated time, never after it.
        """
        remaining = [motion.remaining_ms() for motion in self._motions.values()]
        remaining.extend(rest.remaining_ms() for rest in self._rests.values())
        positive = [value for value in remaining if value > 0]
        return min(positive) if positive else None

    def advance_time(self, ms: int) -> list[ArrivalEvent]:
        """Advance every action and rest, returning arrival events in resolution order.

        A motion that reaches completion is reported here but left in place
        — still busy, still returned by active_actions — until the caller
        acknowledges it via resolve_arrival. This lets a caller that cannot
        yet apply a given arrival (GameOver was decided by an earlier
        arrival in the same batch) leave it validly represented instead of
        finalizing it and then discarding the outcome.

        A motion already complete when this call starts is skipped
        entirely — inert until resolve_arrival is called. Otherwise it
        would keep accumulating elapsed_ms past its own duration and keep
        re-emitting the same ArrivalEvent on every subsequent call.
        """
        if ms <= 0:
            return []

        self._advance_rests(ms)

        completed: list[tuple[int, int, int, ArrivalEvent]] = []

        for motion in self._motions.values():
            if motion.is_complete():
                continue

            remaining_ms = motion.remaining_ms()
            motion.advance(ms)

            if not motion.is_complete():
                continue

            completed.append(
                (
                    remaining_ms,
                    _completion_priority(motion.action_kind),
                    motion.sequence,
                    ArrivalEvent(
                        piece=motion.piece,
                        source=motion.source,
                        destination=motion.destination,
                        action_kind=motion.action_kind,
                        leftover_ms=ms - remaining_ms,
                    ),
                )
            )

        completed.sort(key=lambda item: item[:3])
        return [event for _, _, _, event in completed]

    def resolve_arrival(self, piece_id: str) -> None:
        """Finalize a motion whose completion the caller has fully handled.

        Removes it from scheduling and returns its piece to idle. A no-op
        for an unknown piece_id or a motion that has not yet completed, so
        callers can call it unconditionally once they decide an arrival's
        outcome.
        """
        motion = self._motions.get(piece_id)
        if motion is None or not motion.is_complete():
            return

        if motion.piece.state == "moving":
            motion.piece.state = "idle"

        del self._motions[piece_id]

    def _advance_rests(self, ms: int) -> None:
        """Advance every active cooldown, returning completed pieces to idle.

        A rest completing here has no board effect (unlike arrival), so the
        piece returns to idle directly; the piece_id is recorded so
        GameEngine can still report a RestCompleted event for it.
        """
        for piece_id, rest in tuple(self._rests.items()):
            rest.advance(ms)
            if not rest.is_complete():
                continue
            if rest.piece.state == rest.rest_kind:
                rest.piece.state = "idle"
            del self._rests[piece_id]
            self._completed_rest_piece_ids.append(piece_id)

    def consume_completed_rest_piece_ids(self) -> tuple[str, ...]:
        """Return and clear piece_ids whose rest finished during the last advance_time call."""
        piece_ids = tuple(self._completed_rest_piece_ids)
        self._completed_rest_piece_ids.clear()
        return piece_ids

    def start_rest(self, piece: Piece, rest_kind: RestKind, elapsed_ms: int = 0) -> None:
        """Begin cooldown for a piece that just completed an action.

        elapsed_ms seeds the rest with simulated time left over from the same
        wait() call that produced the arrival, so time is never lost crossing
        the motion-to-rest boundary.
        """
        if self.is_piece_busy(piece.id):
            raise ValueError("piece_busy")

        duration_ms = (
            self._long_cooldown_ms if rest_kind == "long_rest" else self._short_cooldown_ms
        )
        rest = Rest(piece=piece, rest_kind=rest_kind, duration_ms=duration_ms)
        piece.state = rest_kind
        rest.advance(elapsed_ms)

        if rest.is_complete():
            piece.state = "idle"
            return

        self._rests[piece.id] = rest

    def active_actions(self) -> tuple[ActiveAction, ...]:
        """Return immutable views of every currently scheduled action."""
        return tuple(
            self._to_active_action(motion) for motion in self._motions.values()
        )

    def active_rests(self) -> tuple[ActiveRest, ...]:
        """Return immutable views of every currently active cooldown."""
        return tuple(
            ActiveRest(
                piece_id=rest.piece.id,
                rest_kind=rest.rest_kind,
                duration_ms=rest.duration_ms,
                elapsed_ms=rest.elapsed_ms,
            )
            for rest in self._rests.values()
        )

    def active_jump_at(self, landing: Position) -> ActiveAction | None:
        """Return the jump scheduled to land on a cell, if one exists."""
        for motion in self._motions.values():
            if motion.action_kind == "jump" and motion.destination == landing:
                return self._to_active_action(motion)
        return None

    def _start_action(
        self,
        piece: Piece,
        action_kind: ActionKind,
        source: Position,
        destination: Position,
        duration_ms: int,
    ) -> None:
        """Register a new motion for an idle piece and mark it as moving."""
        if self.is_piece_busy(piece.id):
            raise ValueError("piece_busy")

        self._motions[piece.id] = Motion(
            piece=piece,
            action_kind=action_kind,
            source=source,
            destination=destination,
            duration_ms=duration_ms,
            sequence=self._next_sequence,
        )
        piece.state = "moving"
        self._next_sequence += 1

    @staticmethod
    def _to_active_action(motion: Motion) -> ActiveAction:
        """Convert an internal Motion into its immutable external view."""
        return ActiveAction(
            piece_id=motion.piece.id,
            piece_color=motion.piece.color,
            piece_kind=motion.piece.kind,
            action_kind=motion.action_kind,
            source=motion.source,
            destination=motion.destination,
            duration_ms=motion.duration_ms,
            elapsed_ms=motion.elapsed_ms,
        )
