from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __repr__(self):
        return f"Position({self.row}, {self.col})"
