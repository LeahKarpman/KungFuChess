from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ..engine.game_engine import GameEngine
from ..input.board_mapper import BoardMapper
from ..input.controller import Controller
from ..io.board_parser import parse_board
from ..realtime.real_time_arbiter import RealTimeArbiter
from ..rules.rule_engine import RuleEngine
from .img import Img
from .layout import BoardLayout
from .renderer import BoardRenderer
from .sprite_loader import SpriteLoader

CELL_SIZE = 100
WINDOW_TITLE = "Kung-Fu Chess"
POLL_DELAY_MS = 30
_EXIT_KEYS = frozenset({27, ord("q")})  # Escape, q

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


def _build_renderer() -> BoardRenderer:
    layout = BoardLayout(cell_size=CELL_SIZE)
    sprite_loader = SpriteLoader(_ASSETS_ROOT / "pieces2")
    return BoardRenderer(_ASSETS_ROOT / "board.png", sprite_loader, layout)


def run_loop(
    engine: GameEngine,
    renderer: BoardRenderer,
    controller: Controller,
    clock: Callable[[], float] = time.perf_counter,
    poll_key: Callable[[int], int] = Img.poll_key,
) -> None:
    """Advance and render the engine every iteration until Escape or q is pressed.

    clock and poll_key are injectable so the loop can be exercised deterministically
    in tests; the real UI always calls this with their default implementations.
    """
    Img.set_left_click_callback(WINDOW_TITLE, controller.click)

    last_time = clock()
    try:
        while True:
            now = clock()
            elapsed_ms = int((now - last_time) * 1000)
            last_time = now

            engine.wait(elapsed_ms)
            snapshot = engine.snapshot()
            frame = renderer.render(snapshot, controller.selected)
            frame.show_frame(WINDOW_TITLE)

            key = poll_key(POLL_DELAY_MS)
            if key in _EXIT_KEYS:
                break
    finally:
        Img.close_all_windows()


def main() -> None:
    """Run the persistent real-time window until the user closes it."""
    engine = _build_standard_engine()
    renderer = _build_renderer()
    snapshot = engine.snapshot()
    mapper = BoardMapper(snapshot.width, snapshot.height, cell_size=CELL_SIZE)
    controller = Controller(mapper, engine)
    run_loop(engine, renderer, controller)
