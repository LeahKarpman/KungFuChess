from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __repr__(self) -> str:
        return f"Position({self.row}, {self.col})"
