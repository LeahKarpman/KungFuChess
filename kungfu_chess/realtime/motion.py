"""Data and pure calculations describing a single timed piece action.

This module owns the shape of one in-flight action (a move or a jump)
and how long it takes to travel. It has no knowledge of the board, chess
legality, capture, promotion, game-over state, controllers, pixels,
commands, or rendering — those belong to higher layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..model.piece import Piece
from ..model.position import Position

MS_PER_CELL = 1000
ActionKind = Literal["move", "jump"]


def calculate_route(
    piece_kind: str,
    source: Position,
    destination: Position,
) -> tuple[Position, ...]:
    """Return the ordered visual waypoints for one legal move.

    This function describes timing geometry only. The rules layer remains
    responsible for deciding whether the requested move is legal, and Motion
    separately decides which waypoint boundaries require board resolution.
    """
    dr = destination.row - source.row
    dc = destination.col - source.col

    if piece_kind == "N":
        route: list[Position] = []
        row, col = source.row, source.col
        row_step = _sign(dr)
        col_step = _sign(dc)
        if abs(dr) == 2:
            for _ in range(2):
                row += row_step
                route.append(Position(row, col))
            col += col_step
            route.append(Position(row, col))
        else:
            for _ in range(2):
                col += col_step
                route.append(Position(row, col))
            row += row_step
            route.append(Position(row, col))
        return tuple(route)

    if piece_kind == "K":
        return (destination,)

    distance = max(abs(dr), abs(dc))
    row_step = _sign(dr)
    col_step = _sign(dc)
    return tuple(
        Position(source.row + row_step * step, source.col + col_step * step)
        for step in range(1, distance + 1)
    )


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def travel_duration_ms(
    piece_kind: str,
    source: Position,
    destination: Position,
) -> int:
    """Calculate movement duration from the piece's board-cell route.

    Every route cell takes exactly one cell-duration to reach.
    """
    return len(calculate_route(piece_kind, source, destination)) * MS_PER_CELL


@dataclass
class Motion:
    """Mutable state of one piece action currently in progress.

    Instances are owned and mutated only by RealTimeArbiter; nothing
    outside the realtime package should hold or mutate a Motion.
    """

    piece: Piece
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int = 0
    sequence: int = 0
    route: tuple[Position, ...] = ()
    current_cell: Position | None = None
    current_waypoint: Position | None = None
    route_index: int = 0
    segment_elapsed_ms: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, int):
            raise TypeError(
                f"Motion duration_ms must be an int, got {self.duration_ms!r}"
            )
        if self.duration_ms <= 0:
            raise ValueError(
                f"Motion duration_ms must be positive, got {self.duration_ms!r}"
            )
        if not self.route:
            self.route = (
                (self.destination,)
                if self.action_kind == "jump"
                else calculate_route(self.piece.kind, self.source, self.destination)
            )
        if not self.route:
            raise ValueError("Motion route must contain at least one cell")
        if self.current_cell is None:
            self.current_cell = self.source
        if self.current_waypoint is None:
            self.current_waypoint = self.source

    @property
    def origin(self) -> Position:
        """Return the immutable source of the whole requested action."""
        return self.source

    @property
    def requested_destination(self) -> Position:
        """Return the immutable destination of the whole requested action."""
        return self.destination

    @property
    def next_cell(self) -> Position:
        """Backward-compatible alias for the next visual waypoint."""
        return self.next_waypoint

    @property
    def next_waypoint(self) -> Position:
        """Return the visual route point at the pending boundary."""
        return self.route[self.route_index]

    def segment_duration_ms(self) -> int:
        """Return the duration of the current render/timing segment."""
        return self.duration_ms if self.action_kind == "jump" else MS_PER_CELL

    def advance(self, ms: int) -> None:
        """Advance toward, but never beyond, the pending cell boundary."""
        applied_ms = min(ms, self.remaining_ms())
        self.elapsed_ms += applied_ms
        self.segment_elapsed_ms += applied_ms

    def remaining_ms(self) -> int:
        """Return simulated time left before the next cell boundary."""
        return max(self.segment_duration_ms() - self.segment_elapsed_ms, 0)

    def is_waiting_at_boundary(self) -> bool:
        """Return whether GameEngine must decide the pending cell arrival."""
        return self.segment_elapsed_ms >= self.segment_duration_ms()

    def is_complete(self) -> bool:
        """Return whether the pending boundary is the requested destination."""
        return self.is_waiting_at_boundary() and self.is_final_boundary()

    def is_final_boundary(self) -> bool:
        return self.route_index == len(self.route) - 1

    def requires_board_resolution(self) -> bool:
        """Return whether the pending visual boundary can change board occupancy."""
        return (
            self.action_kind != "move"
            or self.piece.kind != "N"
            or self.is_final_boundary()
        )

    def accept_boundary(self, update_occupied_cell: bool = True) -> bool:
        """Commit progress at the pending visual boundary.

        Sliding-piece and pawn boundaries update both the visual waypoint and
        occupied cell after GameEngine resolves the board step. Knight transit
        boundaries update only the visual waypoint. Returns True at the final
        route point; otherwise prepares the next visual segment.
        """
        if not self.is_waiting_at_boundary():
            return False

        self.current_waypoint = self.next_waypoint
        if update_occupied_cell:
            self.current_cell = self.next_waypoint
        if self.is_final_boundary():
            return True

        self.route_index += 1
        self.segment_elapsed_ms = 0
        return False


@dataclass(frozen=True)
class ActiveAction:
    """Immutable external view of a currently scheduled action.

    Exposes only plain data (no Piece reference) so callers outside the
    realtime package cannot mutate the piece through this view.
    """

    piece_id: str
    piece_color: str
    piece_kind: str
    action_kind: ActionKind
    source: Position
    destination: Position
    duration_ms: int
    elapsed_ms: int
    action_elapsed_ms: int | None = None


@dataclass(frozen=True)
class ArrivalEvent:
    """Immutable event describing a timed action at one cell boundary."""

    piece: Piece
    source: Position
    destination: Position
    action_kind: ActionKind = "move"
    leftover_ms: int = 0
    original_source: Position | None = None
    requested_destination: Position | None = None
    is_final: bool = True
