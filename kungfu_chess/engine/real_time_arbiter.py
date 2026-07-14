from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..model.piece import Piece
from ..model.position import Position


MS_PER_CELL = 1000
ActionKind = Literal["move", "jump"]


def _travel_time(
    piece_kind: str,
    source: Position,
    destination: Position,
) -> int:
    """Calculate movement duration from the piece's board-cell route."""
    dr = abs(destination.row - source.row)
    dc = abs(destination.col - source.col)
    distance = dr + dc if piece_kind == "N" else max(dr, dc)
    return distance * MS_PER_CELL


def _completion_priority(action_kind: ActionKind) -> int:
    """Resolve a move before a jump when both complete simultaneously."""
    return 0 if action_kind == "move" else 1


@dataclass
class _ScheduledAction:
    piece: Piece
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int = 0
    sequence: int = 0


@dataclass(frozen=True)
class ActiveAction:
    """Provide an immutable view of a currently scheduled action."""

    piece_id: str
    piece_color: str
    piece_kind: str
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int


@dataclass(frozen=True)
class ArrivalEvent:
    """Describe a timed action that has reached its destination."""

    piece: Piece
    source: Position
    destination: Position
    action_kind: ActionKind = "move"

    @property
    def piece_id(self) -> str:
        """Return the stable identifier of the arriving piece."""
        return self.piece.id


class RealTimeArbiter:
    """Schedule timed piece actions and emit deterministic arrival events."""

    def __init__(self) -> None:
        self._actions: dict[str, _ScheduledAction] = {}
        self._next_sequence = 0

    def has_active_motion(self) -> bool:
        """Return whether at least one regular move is active."""
        return any(action.action_kind == "move" for action in self._actions.values())

    def is_piece_busy(self, piece_id: str) -> bool:
        """Return whether the piece already has any scheduled action."""
        return piece_id in self._actions

    def cancel_action(self, piece_id: str) -> None:
        """Stop a scheduled action without changing the piece lifecycle."""
        self._actions.pop(piece_id, None)

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
            duration_ms=_travel_time(piece.kind, source, destination),
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

    def advance_time(self, ms: int) -> list[ArrivalEvent]:
        """Advance every action and return events in resolution order."""
        if ms <= 0:
            return []

        completed: list[tuple[int, int, int, ArrivalEvent]] = []

        for piece_id, action in tuple(self._actions.items()):
            remaining_ms = max(
                action.duration_ms - action.elapsed_ms,
                0,
            )
            action.elapsed_ms += ms

            if action.elapsed_ms < action.duration_ms:
                continue

            completed.append(
                (
                    remaining_ms,
                    _completion_priority(action.action_kind),
                    action.sequence,
                    ArrivalEvent(
                        piece=action.piece,
                        source=action.source,
                        destination=action.destination,
                        action_kind=action.action_kind,
                    ),
                )
            )

            if action.piece.state == "moving":
                action.piece.state = "idle"

            del self._actions[piece_id]

        completed.sort(key=lambda item: item[:3])
        return [event for _, _, _, event in completed]

    def active_motions(self) -> tuple[ActiveAction, ...]:
        """Return immutable views of active regular moves."""
        return tuple(
            action for action in self.active_actions() if action.action_kind == "move"
        )

    def active_actions(self) -> tuple[ActiveAction, ...]:
        """Return immutable views of every currently scheduled action."""
        return tuple(
            self._to_active_action(action) for action in self._actions.values()
        )

    def active_jump_at(self, landing: Position) -> ActiveAction | None:
        """Return the jump scheduled to land on a cell, if one exists."""
        for action in self._actions.values():
            if action.action_kind == "jump" and action.destination == landing:
                return self._to_active_action(action)
        return None

    def _start_action(
        self,
        piece: Piece,
        action_kind: ActionKind,
        source: Position,
        destination: Position,
        duration_ms: int,
    ) -> None:
        if self.is_piece_busy(piece.id):
            raise ValueError("piece_busy")

        self._actions[piece.id] = _ScheduledAction(
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
    def _to_active_action(action: _ScheduledAction) -> ActiveAction:
        return ActiveAction(
            piece_id=action.piece.id,
            piece_color=action.piece.color,
            piece_kind=action.piece.kind,
            action_kind=action.action_kind,
            source=action.source,
            destination=action.destination,
            duration_ms=action.duration_ms,
            elapsed_ms=action.elapsed_ms,
        )
