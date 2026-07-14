"""Arbitration policy for scheduling and resolving timed piece actions."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

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

    def __init__(self) -> None:
        self._motions: Dict[str, Motion] = {}
        self._next_sequence = 0

    def is_piece_busy(self, piece_id: str) -> bool:
        """Return whether the piece already has any scheduled action."""
        return piece_id in self._motions

    def cancel_action(self, piece_id: str) -> None:
        """Stop a scheduled action without changing the piece lifecycle."""
        self._motions.pop(piece_id, None)

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

    def advance_time(self, ms: int) -> List[ArrivalEvent]:
        """Advance every action and return events in resolution order."""
        if ms <= 0:
            return []

        completed: List[Tuple[int, int, int, ArrivalEvent]] = []

        for piece_id, motion in tuple(self._motions.items()):
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
                    ),
                )
            )

            if motion.piece.state == "moving":
                motion.piece.state = "idle"

            del self._motions[piece_id]

        completed.sort(key=lambda item: item[:3])
        return [event for _, _, _, event in completed]

    def active_actions(self) -> Tuple[ActiveAction, ...]:
        """Return immutable views of every currently scheduled action."""
        return tuple(
            self._to_active_action(motion) for motion in self._motions.values()
        )

    def active_jump_at(self, landing: Position) -> Optional[ActiveAction]:
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
