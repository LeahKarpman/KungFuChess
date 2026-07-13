from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerResult:
    action: str
    position: object = None


class Controller:
    def __init__(self, mapper, engine):
        self._mapper = mapper
        self._engine = engine
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def click(self, x, y):
        pos = self._mapper.pixel_to_cell(x, y)

        if pos is None:
            if self._selected is not None:
                self._selected = None
                return ControllerResult(action='cancelled')
            return ControllerResult(action='ignored')

        pieces = self._engine.snapshot().pieces
        piece_at_pos = next((p for p in pieces if p.cell == pos), None)

        if self._selected is None:
            if piece_at_pos is None:
                return ControllerResult(action='ignored')
            self._selected = pos
            return ControllerResult(action='selected', position=pos)

        selected_piece = next((p for p in pieces if p.cell == self._selected), None)
        if piece_at_pos is not None and selected_piece is not None and \
                piece_at_pos.color == selected_piece.color:
            self._selected = pos
            return ControllerResult(action='selected', position=pos)

        src = self._selected
        self._selected = None
        self._engine.request_move(src, pos)
        return ControllerResult(action='move_requested', position=pos)
