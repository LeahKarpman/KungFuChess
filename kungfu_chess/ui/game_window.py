from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from ..engine.game_engine import GameEngine
from ..game_config import GameConfig, load_game_config
from ..input.board_mapper import BoardMapper
from ..input.controller import Controller
from ..io.board_parser import parse_board
from ..realtime.real_time_arbiter import RealTimeArbiter
from ..rules.rule_engine import RuleEngine
from .img import Img
from .layout import BoardLayout
from .presentation import GamePresentation
from .renderer import BoardRenderer, GameRenderer
from .sprite_loader import SpriteLoader

WINDOW_TITLE = "Kung-Fu Chess"
POLL_DELAY_MS = 30
_EXIT_KEYS = frozenset({27, ord("q"), ord("Q")})  # Escape, q, Q

_UI_ROOT = Path(__file__).resolve().parent
_PACKAGE_ROOT = _UI_ROOT.parent
_ASSETS_ROOT = _UI_ROOT / "assets"
_STANDARD_BOARD_PATH = _PACKAGE_ROOT / "resources" / "boards" / "standard_board.txt"
_GAME_CONFIG_PATH = _PACKAGE_ROOT / "resources" / "game_config.json"
GAME_BOARD_LAYOUT = BoardLayout(cell_size=72, origin_x=260, origin_y=30)
SPRITE_SIZE = round(GAME_BOARD_LAYOUT.cell_size * 0.64)


class WindowOperations(Protocol):
    def set_mouse_callbacks(
        self,
        window_name: str,
        on_left_click: Callable[[int, int], object],
        on_right_click: Callable[[int, int], object],
    ) -> None: ...

    def is_window_open(self, window_name: str) -> bool: ...

    def close_all_windows(self) -> None: ...


def _build_standard_engine(config: GameConfig) -> GameEngine:
    """Construct a GameEngine for the standard starting position via the existing parser."""
    text = _STANDARD_BOARD_PATH.read_text(encoding="utf-8")
    lines = text.strip("\n").splitlines()
    board = parse_board(lines)
    arbiter = RealTimeArbiter(
        short_cooldown_ms=config.short_cooldown_ms,
        long_cooldown_ms=config.long_cooldown_ms,
    )
    return GameEngine(board, RuleEngine(), arbiter)


def _build_renderer(layout: BoardLayout) -> GameRenderer:
    sprite_size = round(layout.cell_size * 0.64)
    sprite_loader = SpriteLoader(_ASSETS_ROOT / "pieces2", sprite_size=sprite_size)
    board_renderer = BoardRenderer(_ASSETS_ROOT / "board.png", sprite_loader, layout)
    return GameRenderer(board_renderer)


def run_loop(
    engine: GameEngine,
    renderer: GameRenderer,
    controller: Controller,
    presentation: GamePresentation,
    clock: Callable[[], float] = time.perf_counter,
    poll_key: Callable[[int], int] = Img.poll_key,
    window: WindowOperations = Img(),
) -> None:
    """Advance and render until the window closes or an exit key is pressed.

    clock and poll_key are injectable so the loop can be exercised deterministically
    in tests; the real UI always calls this with their default implementations.
    """
    try:
        window.set_mouse_callbacks(WINDOW_TITLE, controller.click, controller.jump)

        last_time = clock()
        fractional_elapsed_ms = 0.0

        while True:
            now = clock()
            total_elapsed_ms = (now - last_time) * 1000 + fractional_elapsed_ms
            elapsed_ms = int(total_elapsed_ms)
            fractional_elapsed_ms = total_elapsed_ms - elapsed_ms
            last_time = now

            engine.wait(elapsed_ms)
            events = engine.consume_events()
            presentation.apply(events)
            snapshot = engine.snapshot()
            frame = renderer.render(
                snapshot,
                controller.selected,
                presentation.snapshot(),
            )
            frame.show_frame(WINDOW_TITLE)

            key = poll_key(POLL_DELAY_MS)
            if key in _EXIT_KEYS or not window.is_window_open(WINDOW_TITLE):
                break
    finally:
        window.close_all_windows()


def run_game(
    engine: GameEngine,
    renderer: GameRenderer,
    layout: BoardLayout,
    presentation: GamePresentation,
    controller_factory: Callable[[BoardMapper, GameEngine], Controller] = Controller,
    loop: Callable[
        [GameEngine, GameRenderer, Controller, GamePresentation], None
    ] = run_loop,
) -> None:
    """Wire input geometry to an existing game and run its persistent window."""
    snapshot = engine.snapshot()
    mapper = BoardMapper(snapshot.width, snapshot.height, layout)
    controller = controller_factory(mapper, engine)
    loop(engine, renderer, controller, presentation)


def main() -> None:
    """Run the persistent real-time window until the user closes it."""
    config = load_game_config(_GAME_CONFIG_PATH)
    engine = _build_standard_engine(config)
    layout = GAME_BOARD_LAYOUT
    renderer = _build_renderer(layout)
    presentation = GamePresentation(
        piece_values=config.piece_values,
        board_height=engine.snapshot().height,
    )
    run_game(engine, renderer, layout, presentation)
