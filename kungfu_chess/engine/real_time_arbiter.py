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
    sequence: int = 0


@dataclass(frozen=True)
class ActiveMotion:
    piece_id: str
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int


@dataclass(frozen=True)
class ArrivalEvent:
    piece_id: str
    source: Position
    destination: Position


class RealTimeArbiter:
    def __init__(self) -> None:
        self._motions: dict[str, _Motion] = {}
        self._next_sequence = 0

    def has_active_motion(self) -> bool:
        return bool(self._motions)

    def is_piece_busy(self, piece_id: str) -> bool:
        return piece_id in self._motions

    def start_motion(
        self,
        piece_id: str,
        source: Position,
        destination: Position,
    ) -> None:
        if self.is_piece_busy(piece_id):
            raise ValueError('piece_busy')

        self._motions[piece_id] = _Motion(
            piece_id=piece_id,
            source=source,
            destination=destination,
            duration_ms=_travel_time(source, destination),
            sequence=self._next_sequence,
        )
        self._next_sequence += 1

    def advance_time(self, ms: int) -> list[ArrivalEvent]:
        completed: list[tuple[int, int, ArrivalEvent]] = []

        for piece_id, motion in tuple(self._motions.items()):
            remaining_ms = max(
                motion.duration_ms - motion.elapsed_ms,
                0,
            )
            motion.elapsed_ms += ms

            if motion.elapsed_ms < motion.duration_ms:
                continue

            completed.append((
                remaining_ms,
                motion.sequence,
                ArrivalEvent(
                    piece_id=motion.piece_id,
                    source=motion.source,
                    destination=motion.destination,
                ),
            ))
            del self._motions[piece_id]

        completed.sort(key=lambda item: (item[0], item[1]))
        return [event for _, _, event in completed]

    def active_motions(self) -> tuple[ActiveMotion, ...]:
        return tuple(
            ActiveMotion(
                piece_id=motion.piece_id,
                source=motion.source,
                destination=motion.destination,
                duration_ms=motion.duration_ms,
                elapsed_ms=motion.elapsed_ms,
            )
            for motion in self._motions.values()
        )