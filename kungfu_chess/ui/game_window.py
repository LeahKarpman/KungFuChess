from __future__ import annotations

from pathlib import Path

from ..engine.game_engine import GameEngine
from ..io.board_parser import parse_board
from ..realtime.real_time_arbiter import RealTimeArbiter
from ..rules.rule_engine import RuleEngine
from .layout import BoardLayout
from .renderer import BoardRenderer
from .sprite_loader import SpriteLoader

CELL_SIZE = 100

_UI_ROOT = Path(__file__).resolve().parent
_PACKAGE_ROOT = _UI_ROOT.parent
_ASSETS_ROOT = _UI_ROOT / "assets"
_STANDARD_BOARD_PATH = _PACKAGE_ROOT / "resources" / "boards" / "standard_board.txt"


def _build_standard_engine() -> GameEngine:
    """Construct a GameEngine for the standard starting position via the existing parser."""
    text = _STANDARD_BOARD_PATH.read_text(encoding="utf-8")
    lines = text.strip("\n").splitlines()
    board = parse_board(lines)
    return GameEngine(board, RuleEngine(), RealTimeArbiter())


def main() -> None:
    """Render the standard starting position once and display it in a window."""
    engine = _build_standard_engine()
    layout = BoardLayout(cell_size=CELL_SIZE)
    sprite_loader = SpriteLoader(_ASSETS_ROOT / "pieces2")
    renderer = BoardRenderer(_ASSETS_ROOT / "board.png", sprite_loader, layout)

    snapshot = engine.snapshot()
    frame = renderer.render(snapshot)
    frame.show()
