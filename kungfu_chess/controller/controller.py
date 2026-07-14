from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from ..engine.game_engine import GameEngine
from ..io.board_mapper import BoardMapper
from ..model.position import Position

ControllerAction = Literal[
    "ignored",
    "cancelled",
    "selected",
    "move_requested",
]


@dataclass(frozen=True)
class ControllerResult:
    """Describe how the controller interpreted a click."""

    action: ControllerAction
    position: Position | None = None


class Controller:
    """Translate pixel clicks into selection and move requests."""

    def __init__(self, mapper: BoardMapper, engine: GameEngine) -> None:
        self._mapper = mapper
        self._engine = engine
        self._selected: Position | None = None

    @property
    def selected(self) -> Position | None:
        """Return the currently selected logical board cell, if any."""
        return self._selected

    def click(self, x: int, y: int) -> ControllerResult:
        """Interpret one pixel click without deciding move legality."""
        pos = self._mapper.pixel_to_cell(x, y)

        if pos is None:
            if self._selected is not None:
                self._selected = None
                return ControllerResult(action="cancelled")
            return ControllerResult(action="ignored")

        pieces = self._engine.snapshot().pieces
        piece_at_pos = next((p for p in pieces if p.cell == pos), None)

        if piece_at_pos is not None and piece_at_pos.state == "moving":
            return ControllerResult(action="ignored")

        if self._selected is None:
            if piece_at_pos is None:
                return ControllerResult(action="ignored")
            self._selected = pos
            return ControllerResult(action="selected", position=pos)

        selected_piece = next(
            (p for p in pieces if p.cell == self._selected),
            None,
        )
        if (
            piece_at_pos is not None
            and selected_piece is not None
            and piece_at_pos.color == selected_piece.color
        ):
            self._selected = pos
            return ControllerResult(action="selected", position=pos)

        src = self._selected
        self._selected = None
        self._engine.request_move(src, pos)
        return ControllerResult(action="move_requested", position=pos)
