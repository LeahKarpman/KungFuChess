from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .position import Position

VALID_COLORS = {'w', 'b'}
VALID_KINDS = {'K', 'Q', 'R', 'B', 'N', 'P'}


class Piece:
    id: str
    color: str
    kind: str
    cell: Position
    state: str

    def __init__(self, id: str, color: str, kind: str, cell: Position, state: str = 'idle') -> None:
        self.id = id
        self.color = color
        self.kind = kind
        self.cell = cell
        self.state = state
