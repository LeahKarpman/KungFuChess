"""Event-driven presentation state for scores and completed action history."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ..model.events import (
    GameEvent,
    GameOver,
    JumpCompleted,
    MoveCompleted,
    PieceCaptured,
    PiecePromoted,
)
from ..model.position import Position

_COLORS = frozenset({"w", "b"})


@dataclass(frozen=True)
class MoveLogEntry:
    """One formatted, completed action attributed to a piece and color."""

    piece_id: str
    piece_color: str
    notation: str


@dataclass(frozen=True)
class GamePresentationSnapshot:
    """Immutable score and complete action history consumed by the HUD renderer."""

    white_score: int
    black_score: int
    white_actions: tuple[MoveLogEntry, ...]
    black_actions: tuple[MoveLogEntry, ...]


class GamePresentation:
    """Project engine events into display-only score and full move-log state."""

    def __init__(self, piece_values: Mapping[str, int], board_height: int) -> None:
        if board_height <= 0:
            raise ValueError("board_height must be positive")
        self._piece_values = dict(piece_values)
        self._board_height = board_height
        self._scores = {"w": 0, "b": 0}
        self._actions: dict[str, list[MoveLogEntry]] = {"w": [], "b": []}
        self._capturing_piece_ids: set[str] = set()
        self._scored_piece_ids: set[str] = set()

    def apply(self, events: Iterable[GameEvent]) -> None:
        """Apply consumed engine events in their existing deterministic order."""
        for event in events:
            if isinstance(event, PieceCaptured):
                self._apply_capture(event)
            elif isinstance(event, MoveCompleted):
                self._append_completed_action(event, is_jump=False)
            elif isinstance(event, JumpCompleted):
                self._append_completed_action(event, is_jump=True)
            elif isinstance(event, PiecePromoted):
                self._append_promotion(event)
            elif isinstance(event, GameOver):
                self._capturing_piece_ids.clear()

    def snapshot(self) -> GamePresentationSnapshot:
        """Return an immutable presentation snapshot for the next frame."""
        return GamePresentationSnapshot(
            white_score=self._scores["w"],
            black_score=self._scores["b"],
            white_actions=tuple(self._actions["w"]),
            black_actions=tuple(self._actions["b"]),
        )

    def _apply_capture(self, event: PieceCaptured) -> None:
        if event.by_piece_color not in _COLORS:
            raise ValueError(
                f"Unsupported capturing piece color: {event.by_piece_color!r}"
            )
        try:
            value = self._piece_values[event.captured_piece_kind]
        except KeyError:
            raise ValueError(
                f"Missing configured value for piece kind "
                f"{event.captured_piece_kind!r}"
            ) from None

        if event.captured_piece_id not in self._scored_piece_ids:
            self._scores[event.by_piece_color] += value
            self._scored_piece_ids.add(event.captured_piece_id)
        self._capturing_piece_ids.add(event.by_piece_id)
        self._capturing_piece_ids.discard(event.captured_piece_id)

    def _append_completed_action(
        self, event: MoveCompleted | JumpCompleted, is_jump: bool
    ) -> None:
        captured = event.piece_id in self._capturing_piece_ids
        self._capturing_piece_ids.discard(event.piece_id)
        separator = "x" if captured else "-"
        source = self._coordinate(event.source)
        destination = self._coordinate(event.destination)
        if is_jump:
            action = f"{source}x{destination}" if captured else source
            notation = f"{event.piece_kind} {action} (jump)"
        else:
            notation = f"{event.piece_kind} {source}{separator}{destination}"

        self._actions[event.piece_color].append(
            MoveLogEntry(
                piece_id=event.piece_id,
                piece_color=event.piece_color,
                notation=notation,
            )
        )

    def _append_promotion(self, event: PiecePromoted) -> None:
        for actions in self._actions.values():
            for index in range(len(actions) - 1, -1, -1):
                entry = actions[index]
                if entry.piece_id == event.piece_id:
                    actions[index] = MoveLogEntry(
                        piece_id=entry.piece_id,
                        piece_color=entry.piece_color,
                        notation=f"{entry.notation}={event.new_kind}",
                    )
                    return

    def _coordinate(self, position: Position) -> str:
        file_name = chr(ord("a") + position.col)
        rank = self._board_height - position.row
        return f"{file_name}{rank}"
