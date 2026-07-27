from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..engine.game_engine import GameEngine
from .board_mapper import BoardMapper
from ..model.game_state import PieceSnapshot
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
        self._selected_piece_id: str | None = None

    @property
    def selected(self) -> Position | None:
        """Return the currently selected piece's board cell, if it still exists.

        Selection is tracked by piece identity rather than by cell, so a
        selected piece that gets captured in place no longer leaves behind a
        stale cell reference pointing at whatever piece now occupies it. A
        terminal game also clears the controller-owned selection immediately.
        """
        if self._clear_selection_if_game_over():
            return None
        piece = self._find_selected(self._engine.snapshot().pieces)
        return piece.cell if piece is not None else None

    def _clear_selection_if_game_over(self) -> bool:
        """Clear controller-owned selection when the engine reports game over."""
        if not self._engine.game_over:
            return False
        self._selected_piece_id = None
        return True

    def _find_selected(
        self, pieces: tuple[PieceSnapshot, ...]
    ) -> PieceSnapshot | None:
        """Look up the selected piece by id, self-healing a stale selection.

        If the previously selected piece is no longer present (captured),
        the stale id is dropped here so callers see a clean "no selection"
        state instead of one anchored to a cell that piece no longer owns.
        """
        if self._selected_piece_id is None:
            return None
        for piece in pieces:
            if piece.id == self._selected_piece_id:
                return piece
        self._selected_piece_id = None
        return None

    def _clear_selection_if_accepted(self, ok: bool) -> None:
        """Clear the selection only when the engine accepted the request."""
        if ok:
            self._selected_piece_id = None

    def jump(self, x: int, y: int) -> ControllerResult:
        """Map a jump command to a board cell and delegate it to the engine.

        During an active game, selection is cleared only when the engine
        accepts the jump, even if the jumping piece is not the one currently
        selected. Input is ignored once the game is over.
        """
        if self._clear_selection_if_game_over():
            return ControllerResult(action="ignored")

        pos = self._mapper.pixel_to_cell(x, y)
        if pos is None:
            return ControllerResult(action="ignored")

        result = self._engine.jump(pos)
        self._clear_selection_if_accepted(result.ok)
        return ControllerResult(action="jump_requested", position=pos)

    def click(self, x: int, y: int) -> ControllerResult:
        """Interpret one active-game pixel click without deciding move legality."""
        if self._clear_selection_if_game_over():
            return ControllerResult(action="ignored")

        pos = self._mapper.pixel_to_cell(x, y)

        if pos is None:
            if self._selected_piece_id is not None:
                self._selected_piece_id = None
                return ControllerResult(action="cancelled")
            return ControllerResult(action="ignored")

        pieces = self._engine.snapshot().pieces
        pieces_by_cell = {piece.cell: piece for piece in pieces}
        piece_at_pos = pieces_by_cell.get(pos)
        selected_piece = self._find_selected(pieces)

        if selected_piece is None:
            if (
                piece_at_pos is None
                or piece_at_pos.state == "moving"
                or piece_at_pos.state in RESTING_STATES
            ):
                return ControllerResult(action="ignored")
            self._selected_piece_id = piece_at_pos.id
            return ControllerResult(action="selected", position=pos)

        if piece_at_pos is not None and piece_at_pos.id == selected_piece.id:
            self._selected_piece_id = None
            return ControllerResult(action="cancelled", position=pos)

        if (
            piece_at_pos is not None
            and piece_at_pos.state != "moving"
            and piece_at_pos.state not in RESTING_STATES
            and piece_at_pos.color == selected_piece.color
        ):
            self._selected_piece_id = piece_at_pos.id
            return ControllerResult(action="selected", position=pos)

        if (
            piece_at_pos is not None
            and piece_at_pos.state in RESTING_STATES
            and piece_at_pos.color == selected_piece.color
        ):
            # A friendly resting piece cannot become the new selection; leave
            # the existing selection untouched instead of requesting a move.
            return ControllerResult(action="ignored")

        src = selected_piece.cell
        result = self._engine.request_move(src, pos)
        self._clear_selection_if_accepted(result.ok)
        return ControllerResult(action="move_requested", position=pos)
