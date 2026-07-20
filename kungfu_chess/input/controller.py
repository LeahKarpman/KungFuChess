from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..engine.game_engine import GameEngine
from .board_mapper import BoardMapper
from ..model.piece import RESTING_STATES
from ..model.position import Position


ControllerAction = Literal[
    "ignored",
    "cancelled",
    "selected",
    "move_requested",
    "jump_requested",
]


@dataclass(frozen=True)
class ControllerResult:
    """Describe how the controller interpreted one input action."""

    action: ControllerAction
    position: Position | None = None


class Controller:
    """Translate pixel input into selection and game-engine requests."""

    def __init__(self, mapper: BoardMapper, engine: GameEngine) -> None:
        self._mapper = mapper
        self._engine = engine
        self._selected: Position | None = None

    @property
    def selected(self) -> Position | None:
        """Return the currently selected logical board cell, if any."""
        return self._selected

    def jump(self, x: int, y: int) -> ControllerResult:
        """Map a jump command to a board cell and delegate it to the engine.

        Selection is cleared only when the engine accepts the jump, even if
        the jumping piece is not the one currently selected.
        """
        pos = self._mapper.pixel_to_cell(x, y)
        if pos is None:
            return ControllerResult(action="ignored")

        result = self._engine.jump(pos)
        if result.ok:
            self._selected = None
        return ControllerResult(action="jump_requested", position=pos)

    def click(self, x: int, y: int) -> ControllerResult:
        """Interpret one pixel click without deciding move legality."""
        pos = self._mapper.pixel_to_cell(x, y)

        if pos is None:
            if self._selected is not None:
                self._selected = None
                return ControllerResult(action="cancelled")
            return ControllerResult(action="ignored")

        pieces_by_cell = {piece.cell: piece for piece in self._engine.snapshot().pieces}
        piece_at_pos = pieces_by_cell.get(pos)

        if self._selected is None:
            if (
                piece_at_pos is None
                or piece_at_pos.state == "moving"
                or piece_at_pos.state in RESTING_STATES
            ):
                return ControllerResult(action="ignored")
            self._selected = pos
            return ControllerResult(action="selected", position=pos)

        selected_piece = pieces_by_cell.get(self._selected)
        if (
            piece_at_pos is not None
            and piece_at_pos.state != "moving"
            and piece_at_pos.state not in RESTING_STATES
            and selected_piece is not None
            and piece_at_pos.color == selected_piece.color
        ):
            self._selected = pos
            return ControllerResult(action="selected", position=pos)

        if (
            piece_at_pos is not None
            and piece_at_pos.state in RESTING_STATES
            and selected_piece is not None
            and piece_at_pos.color == selected_piece.color
        ):
            # A friendly resting piece cannot become the new selection; leave
            # the existing selection untouched instead of requesting a move.
            return ControllerResult(action="ignored")

        src = self._selected
        result = self._engine.request_move(src, pos)
        if result.ok:
            self._selected = None
        return ControllerResult(action="move_requested", position=pos)
