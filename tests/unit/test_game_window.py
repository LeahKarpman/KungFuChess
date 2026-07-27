from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.input.board_mapper import DEFAULT_CELL_SIZE
from kungfu_chess.input.controller import Controller
from kungfu_chess.model.position import Position
from kungfu_chess.ui.game_window import main, run_loop
from kungfu_chess.ui.img import Img
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.renderer import BoardRenderer


def _make_engine_and_renderer() -> tuple[MagicMock, MagicMock]:
    engine = MagicMock(spec=GameEngine)
    renderer = MagicMock(spec=BoardRenderer)
    renderer.render.return_value = MagicMock()
    return engine, renderer


def _make_controller(selected: Position | None = None) -> MagicMock:
    controller = MagicMock(spec=Controller)
    controller.selected = selected
    return controller


class TestRunLoop(unittest.TestCase):
    """Exercise the persistent window loop without opening a real OpenCV window."""

    def setUp(self) -> None:
        close_patcher = patch.object(Img, "close_all_windows")
        callback_patcher = patch.object(Img, "set_mouse_callbacks")
        window_open_patcher = patch.object(Img, "is_window_open", return_value=True)
        self.mock_close_all_windows = close_patcher.start()
        self.mock_set_mouse_callbacks = callback_patcher.start()
        self.mock_is_window_open = window_open_patcher.start()
        self.addCleanup(close_patcher.stop)
        self.addCleanup(callback_patcher.stop)
        self.addCleanup(window_open_patcher.stop)

    def test_advances_engine_with_elapsed_milliseconds(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.5, 1.2])
        poll_key = MagicMock(side_effect=[-1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(
            [call.args[0] for call in engine.wait.call_args_list],
            [500, 700],
        )

    def test_accumulates_fractional_milliseconds_across_frames(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.0004, 0.0008, 0.0012])
        poll_key = MagicMock(side_effect=[-1, -1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(
            [call.args[0] for call in engine.wait.call_args_list],
            [0, 0, 1],
        )

    def test_total_delivered_time_matches_total_elapsed_time(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = [0.0, 1 / 60, 2 / 60, 3 / 60, 4 / 60]
        clock = iter(clock_values)
        poll_key = MagicMock(side_effect=[-1, -1, -1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock),
            poll_key=poll_key,
        )

        delivered_ms = sum(call.args[0] for call in engine.wait.call_args_list)
        total_elapsed_ms = int((clock_values[-1] - clock_values[0]) * 1000)
        self.assertEqual(delivered_ms, total_elapsed_ms)

    def test_fractional_milliseconds_are_not_double_counted(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.0006, 0.0012, 0.0018, 0.0024])
        poll_key = MagicMock(side_effect=[-1, -1, -1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(
            [call.args[0] for call in engine.wait.call_args_list],
            [0, 1, 0, 1],
        )

    def test_consumes_events_once_per_completed_iteration(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = MagicMock(side_effect=[-1, -1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(engine.consume_events.call_count, 3)

    def test_consumes_events_after_mouse_input_is_polled(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])

        def poll_key(delay_ms: int) -> int:
            _, on_left_click, _ = self.mock_set_mouse_callbacks.call_args.args
            on_left_click(123, 456)
            return 27

        def consume_events() -> tuple[object, ...]:
            controller.click.assert_called_once_with(123, 456)
            return ()

        engine.consume_events.side_effect = consume_events

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        engine.consume_events.assert_called_once_with()

    def test_exits_on_escape_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 1)
        engine.consume_events.assert_called_once_with()
        self.mock_close_all_windows.assert_called_once()

    def test_exits_on_q_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[ord("q")])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 1)
        engine.consume_events.assert_called_once_with()
        self.mock_close_all_windows.assert_called_once()

    def test_exits_on_uppercase_q_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[ord("Q")])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 1)
        engine.consume_events.assert_called_once_with()
        self.mock_close_all_windows.assert_called_once()

    def test_visible_window_keeps_loop_running(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = MagicMock(side_effect=[-1, 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 2)
        self.mock_is_window_open.assert_called_once_with("Kung-Fu Chess")

    def test_game_over_frame_remains_visible_until_exit_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        game_over_snapshot = MagicMock(game_over=True)
        engine.snapshot.return_value = game_over_snapshot
        controller = _make_controller(selected=None)
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = MagicMock(side_effect=[-1, ord("q")])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 2)
        renderer.render.assert_called_with(game_over_snapshot, None)
        self.mock_is_window_open.assert_called_once_with("Kung-Fu Chess")
        self.mock_close_all_windows.assert_called_once()

    def test_exits_when_window_is_closed_with_x(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = MagicMock(side_effect=[-1, -1])
        self.mock_is_window_open.side_effect = [True, False]

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 2)
        self.assertEqual(engine.consume_events.call_count, 2)
        self.assertEqual(self.mock_is_window_open.call_count, 2)
        self.mock_close_all_windows.assert_called_once()

    def test_ignores_unrelated_keys_and_keeps_looping(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = MagicMock(side_effect=[-1, ord("a"), 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(renderer.render.call_count, 3)

    def test_cleanup_runs_even_if_render_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        renderer.render.side_effect = RuntimeError("boom")
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock()

        with self.assertRaises(RuntimeError):
            run_loop(
                engine,
                renderer,
                controller,
                clock=lambda: next(clock_values),
                poll_key=poll_key,
            )

        self.mock_close_all_windows.assert_called_once()

    def test_cleanup_runs_if_mouse_callback_setup_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        error = RuntimeError("callback setup failed")
        self.mock_set_mouse_callbacks.side_effect = error
        clock = MagicMock()
        poll_key = MagicMock()

        with self.assertRaises(RuntimeError) as raised:
            run_loop(
                engine,
                renderer,
                controller,
                clock=clock,
                poll_key=poll_key,
            )

        self.assertIs(raised.exception, error)
        self.mock_close_all_windows.assert_called_once()
        engine.wait.assert_not_called()
        engine.snapshot.assert_not_called()
        renderer.render.assert_not_called()
        poll_key.assert_not_called()

    def test_cleanup_runs_if_initial_clock_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        error = RuntimeError("initial clock failed")
        clock = MagicMock(side_effect=error)
        poll_key = MagicMock()

        with self.assertRaises(RuntimeError) as raised:
            run_loop(
                engine,
                renderer,
                controller,
                clock=clock,
                poll_key=poll_key,
            )

        self.assertIs(raised.exception, error)
        self.mock_close_all_windows.assert_called_once()
        engine.wait.assert_not_called()
        renderer.render.assert_not_called()

    def test_does_not_open_a_real_window(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        renderer.render.return_value.show_frame.assert_called_once()

    def test_mouse_callback_installed_exactly_once(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = MagicMock(side_effect=[-1, ord("a"), 27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        self.assertEqual(self.mock_set_mouse_callbacks.call_count, 1)

    def test_installed_callback_delegates_exact_coordinates_to_controller_click(
        self,
    ) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        _window_name, on_left_click, _on_right_click = (
            self.mock_set_mouse_callbacks.call_args.args
        )
        on_left_click(123, 456)

        controller.click.assert_called_once_with(123, 456)

    def test_installed_callback_delegates_exact_coordinates_to_controller_jump(
        self,
    ) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        _window_name, _on_left_click, on_right_click = (
            self.mock_set_mouse_callbacks.call_args.args
        )
        on_right_click(123, 456)

        controller.jump.assert_called_once_with(123, 456)

    def test_rendering_receives_current_controller_selected(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        selected = Position(2, 3)
        controller = _make_controller(selected=selected)
        clock_values = iter([0.0, 0.1])
        poll_key = MagicMock(side_effect=[27])

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        renderer.render.assert_called_once_with(engine.snapshot.return_value, selected)

    def test_next_frame_reflects_selection_change_from_a_click(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller(selected=None)
        clock_values = iter([0.0, 0.1, 0.2])

        def poll_key(delay_ms: int) -> int:
            if renderer.render.call_count == 1:
                controller.selected = Position(
                    0, 0
                )  # simulate a click landing this frame
                return -1
            return 27

        run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        first_selected = renderer.render.call_args_list[0].args[1]
        second_selected = renderer.render.call_args_list[1].args[1]
        self.assertIsNone(first_selected)
        self.assertEqual(second_selected, Position(0, 0))


class TestMainComposition(unittest.TestCase):
    def test_renderer_and_mapper_receive_the_same_board_geometry(self) -> None:
        layout = BoardLayout(cell_size=73, origin_x=11, origin_y=17)

        with (
            patch(
                "kungfu_chess.ui.game_window.BoardLayout", return_value=layout
            ) as layout_type,
            patch("kungfu_chess.ui.game_window.SpriteLoader"),
            patch("kungfu_chess.ui.game_window.BoardRenderer") as renderer_type,
            patch("kungfu_chess.ui.game_window.BoardMapper") as mapper_type,
            patch("kungfu_chess.ui.game_window.Controller"),
            patch("kungfu_chess.ui.game_window.run_loop"),
        ):
            main()

        layout_type.assert_called_once_with(cell_size=DEFAULT_CELL_SIZE)
        self.assertIs(renderer_type.call_args.args[2], layout)
        mapper_type.assert_called_once_with(
            8,
            8,
            cell_size=layout.cell_size,
            origin_x=layout.origin_x,
            origin_y=layout.origin_y,
        )


if __name__ == "__main__":
    unittest.main()
