from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.ui.game_window import run_loop
from kungfu_chess.ui.img import Img
from kungfu_chess.ui.renderer import BoardRenderer


def _make_engine_and_renderer() -> tuple[MagicMock, MagicMock]:
    engine = MagicMock(spec=GameEngine)
    renderer = MagicMock(spec=BoardRenderer)
    renderer.render.return_value = MagicMock()
    return engine, renderer


class TestRunLoop(unittest.TestCase):
    """Exercise the persistent window loop without opening a real OpenCV window."""

    def test_advances_engine_with_elapsed_milliseconds(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        clock_values = iter([0.0, 0.5, 1.2])
        poll_key = MagicMock(side_effect=[-1, 27])

        with patch.object(Img, "close_all_windows"):
            run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        engine.wait.assert_any_call(500)
        engine.wait.assert_any_call(700)

    def test_exits_on_escape_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        with patch.object(Img, "close_all_windows"):
            run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        self.assertEqual(renderer.render.call_count, 1)

    def test_exits_on_q_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[ord("q")])

        with patch.object(Img, "close_all_windows"):
            run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        self.assertEqual(renderer.render.call_count, 1)

    def test_ignores_unrelated_keys_and_keeps_looping(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = MagicMock(side_effect=[-1, ord("a"), 27])

        with patch.object(Img, "close_all_windows"):
            run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        self.assertEqual(renderer.render.call_count, 3)

    def test_cleanup_runs_even_if_render_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        renderer.render.side_effect = RuntimeError("boom")
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock()

        with patch.object(Img, "close_all_windows") as mocked_close:
            with self.assertRaises(RuntimeError):
                run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        mocked_close.assert_called_once()

    def test_does_not_open_a_real_window(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        with patch.object(Img, "close_all_windows"):
            run_loop(engine, renderer, clock=lambda: next(clock_values), poll_key=poll_key)

        renderer.render.return_value.show_frame.assert_called_once()


if __name__ == "__main__":
    unittest.main()
