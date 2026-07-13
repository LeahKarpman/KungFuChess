from __future__ import annotations

VALID_COLORS = {'w', 'b'}
VALID_KINDS = {'K', 'Q', 'R', 'B', 'N', 'P'}


class Piece:
    def __init__(self, id: str, color: str, kind: str, cell, state: str = 'idle'):
        self.id = id
        self.color = color
        self.kind = kind
        self.cell = cell
        self.state = state
