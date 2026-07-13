from __future__ import annotations
from dataclasses import dataclass
from ..model.position import Position

MS_PER_CELL = 1000


def _travel_time(source: Position, destination: Position) -> int:
    dr = abs(destination.row - source.row)
    dc = abs(destination.col - source.col)
    return max(dr, dc) * MS_PER_CELL


@dataclass
class _Motion:
    piece_id: str
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int = 0


@dataclass(frozen=True)
class ArrivalEvent:
    piece_id: str
    source: Position
    destination: Position


class RealTimeArbiter:
    def __init__(self) -> None:
        self._motion: _Motion | None = None

    def has_active_motion(self) -> bool:
        return self._motion is not None

    def start_motion(self, piece_id: str, source: Position, destination: Position) -> None:
        self._motion = _Motion(
            piece_id=piece_id,
            source=source,
            destination=destination,
            duration_ms=_travel_time(source, destination),
        )

    def advance_time(self, ms: int) -> list[ArrivalEvent]:
        if not self._motion:
            return []
        self._motion.elapsed_ms += ms
        if self._motion.elapsed_ms >= self._motion.duration_ms:
            event = ArrivalEvent(
                piece_id=self._motion.piece_id,
                source=self._motion.source,
                destination=self._motion.destination,
            )
            self._motion = None
            return [event]
        return []

    def current_motion(self) -> _Motion | None:
        return self._motion
