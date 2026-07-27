from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from ..engine.game_engine import GameEngine
from ..game_config import load_game_config
from ..input.board_mapper import BoardMapper, DEFAULT_CELL_SIZE
from ..input.controller import Controller
from ..io.board_parser import parse_board
from ..realtime.real_time_arbiter import RealTimeArbiter
from ..rules.rule_engine import RuleEngine
from .img import Img
from .layout import BoardLayout
from .renderer import BoardRenderer
from .sprite_loader import SpriteLoader

WINDOW_TITLE = "Kung-Fu Chess"
POLL_DELAY_MS = 30
_EXIT_KEYS = frozenset({27, ord("q"), ord("Q")})  # Escape, q, Q

_UI_ROOT = Path(__file__).resolve().parent
_PACKAGE_ROOT = _UI_ROOT.parent
_ASSETS_ROOT = _UI_ROOT / "assets"
_STANDARD_BOARD_PATH = _PACKAGE_ROOT / "resources" / "boards" / "standard_board.txt"
_GAME_CONFIG_PATH = _PACKAGE_ROOT / "resources" / "game_config.json"


def _build_standard_engine() -> GameEngine:
    """Construct a GameEngine for the standard starting position via the existing parser."""
    text = _STANDARD_BOARD_PATH.read_text(encoding="utf-8")
    lines = text.strip("\n").splitlines()
    board = parse_board(lines)
    config = load_game_config(_GAME_CONFIG_PATH)
    arbiter = RealTimeArbiter(
        short_cooldown_ms=config.short_cooldown_ms,
        long_cooldown_ms=config.long_cooldown_ms,
    )
    return GameEngine(board, RuleEngine(), arbiter)


def _build_renderer(layout: BoardLayout) -> BoardRenderer:
    sprite_loader = SpriteLoader(_ASSETS_ROOT / "pieces2")
    return BoardRenderer(_ASSETS_ROOT / "board.png", sprite_loader, layout)


def run_loop(
    engine: GameEngine,
    renderer: BoardRenderer,
    controller: Controller,
    clock: Callable[[], float] = time.perf_counter,
    poll_key: Callable[[int], int] = Img.poll_key,
) -> None:
    """Advance and render until the window closes or an exit key is pressed.

    clock and poll_key are injectable so the loop can be exercised deterministically
    in tests; the real UI always calls this with their default implementations.
    """
    try:
        Img.set_mouse_callbacks(WINDOW_TITLE, controller.click, controller.jump)

        last_time = clock()
        fractional_elapsed_ms = 0.0

        while True:
            now = clock()
            total_elapsed_ms = (now - last_time) * 1000 + fractional_elapsed_ms
            elapsed_ms = int(total_elapsed_ms)
            fractional_elapsed_ms = total_elapsed_ms - elapsed_ms
            last_time = now

            engine.wait(elapsed_ms)
            snapshot = engine.snapshot()
            frame = renderer.render(snapshot, controller.selected)
            frame.show_frame(WINDOW_TITLE)

            key = poll_key(POLL_DELAY_MS)
            _ = engine.consume_events()
            if key in _EXIT_KEYS or not Img.is_window_open(WINDOW_TITLE):
                break
    finally:
        Img.close_all_windows()


def main() -> None:
    """Run the persistent real-time window until the user closes it."""
    engine = _build_standard_engine()
    layout = BoardLayout(cell_size=DEFAULT_CELL_SIZE)
    renderer = _build_renderer(layout)
    snapshot = engine.snapshot()
    mapper = BoardMapper(
        snapshot.width,
        snapshot.height,
        cell_size=layout.cell_size,
        origin_x=layout.origin_x,
        origin_y=layout.origin_y,
    )
    controller = Controller(mapper, engine)
    run_loop(engine, renderer, controller)
