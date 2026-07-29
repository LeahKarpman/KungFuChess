from __future__ import annotations

from functools import partial

import pytest

from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.input.controller import Controller
from kungfu_chess.model.game_state import GameSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui.game_window import _build_renderer, run_game, run_loop
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.presentation import GamePresentationSnapshot
from kungfu_chess.ui.renderer import BoardRenderer


class FakeFrame:
    def __init__(self) -> None:
        self.show_frame_calls: list[str] = []

    def show_frame(self, window_name: str) -> None:
        self.show_frame_calls.append(window_name)


class FakeEngine:
    def __init__(self, snapshot: object | None = None) -> None:
        self.snapshot_value = snapshot if snapshot is not None else object()
        self.wait_calls: list[int] = []
        self.snapshot_calls = 0
        self.consume_events_calls = 0
        self.consume_events_hook = None

    def wait(self, elapsed_ms: int) -> None:
        self.wait_calls.append(elapsed_ms)

    def snapshot(self):
        self.snapshot_calls += 1
        return self.snapshot_value

    def consume_events(self):
        self.consume_events_calls += 1
        if self.consume_events_hook is not None:
            return self.consume_events_hook()
        return ()


class FakeRenderer:
    def __init__(self) -> None:
        self.frame = FakeFrame()
        self.render_calls: list[tuple[object, Position | None, object]] = []
        self.render_error: Exception | None = None

    def render(self, snapshot, selected, presentation):
        self.render_calls.append((snapshot, selected, presentation))
        if self.render_error is not None:
            raise self.render_error
        return self.frame


class FakeController:
    def __init__(self, selected: Position | None = None) -> None:
        self.selected = selected
        self.click_calls: list[tuple[int, int]] = []
        self.jump_calls: list[tuple[int, int]] = []

    def click(self, x: int, y: int) -> None:
        self.click_calls.append((x, y))

    def jump(self, x: int, y: int) -> None:
        self.jump_calls.append((x, y))


class FakePresentation:
    def __init__(self) -> None:
        self.apply_calls: list[tuple[object, ...]] = []
        self.snapshot_value = object()

    def apply(self, events) -> None:
        self.apply_calls.append(tuple(events))

    def snapshot(self):
        return self.snapshot_value


class SequencePollKey:
    def __init__(self, values=()) -> None:
        self._values = iter(values)
        self.calls: list[int] = []

    def __call__(self, delay_ms: int) -> int:
        self.calls.append(delay_ms)
        return next(self._values)


def _make_engine_and_renderer() -> tuple[FakeEngine, FakeRenderer]:
    return FakeEngine(), FakeRenderer()


def _make_controller(selected: Position | None = None) -> FakeController:
    return FakeController(selected)


class FakeWindow:
    def __init__(self) -> None:
        self.callback_calls: list[tuple[str, object, object]] = []
        self.is_open_calls: list[str] = []
        self.open_results: list[bool] = []
        self.close_calls = 0
        self.callback_error: Exception | None = None

    def set_mouse_callbacks(self, window_name, on_left_click, on_right_click) -> None:
        if self.callback_error is not None:
            raise self.callback_error
        self.callback_calls.append((window_name, on_left_click, on_right_click))

    def is_window_open(self, window_name: str) -> bool:
        self.is_open_calls.append(window_name)
        if self.open_results:
            return self.open_results.pop(0)
        return True

    def close_all_windows(self) -> None:
        self.close_calls += 1


class TestRunLoop:
    """Exercise the persistent window loop without opening a real OpenCV window."""

    def setup_method(self) -> None:
        self.window = FakeWindow()
        self.presentation = FakePresentation()
        self.run_loop = partial(
            run_loop,
            presentation=self.presentation,
            window=self.window,
        )

    def test_advances_engine_with_elapsed_milliseconds(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.5, 1.2])
        poll_key = SequencePollKey([-1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert engine.wait_calls == [500, 700]

    def test_accumulates_fractional_milliseconds_across_frames(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.0004, 0.0008, 0.0012])
        poll_key = SequencePollKey([-1, -1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert engine.wait_calls == [0, 0, 1]

    def test_total_delivered_time_matches_total_elapsed_time(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = [0.0, 1 / 60, 2 / 60, 3 / 60, 4 / 60]
        clock = iter(clock_values)
        poll_key = SequencePollKey([-1, -1, -1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock),
            poll_key=poll_key,
        )

        delivered_ms = sum(engine.wait_calls)
        total_elapsed_ms = int((clock_values[-1] - clock_values[0]) * 1000)
        assert delivered_ms == total_elapsed_ms

    def test_fractional_milliseconds_are_not_double_counted(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.0006, 0.0012, 0.0018, 0.0024])
        poll_key = SequencePollKey([-1, -1, -1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert engine.wait_calls == [0, 1, 0, 1]

    def test_consumes_events_once_per_completed_iteration(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = SequencePollKey([-1, -1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert engine.consume_events_calls == 3

    def test_consumes_events_before_mouse_input_is_polled(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])

        def poll_key(delay_ms: int) -> int:
            _, on_left_click, _ = self.window.callback_calls[0]
            on_left_click(123, 456)
            return 27

        def consume_events() -> tuple[object, ...]:
            assert controller.click_calls == []
            return ()

        engine.consume_events_hook = consume_events

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert engine.consume_events_calls == 1
        assert controller.click_calls == [(123, 456)]

    def test_exits_on_escape_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 1
        assert engine.consume_events_calls == 1
        assert self.window.close_calls == 1

    def test_exits_on_q_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([ord("q")])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 1
        assert engine.consume_events_calls == 1
        assert self.window.close_calls == 1

    def test_exits_on_uppercase_q_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([ord("Q")])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 1
        assert engine.consume_events_calls == 1
        assert self.window.close_calls == 1

    def test_visible_window_keeps_loop_running(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = SequencePollKey([-1, 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 2
        assert self.window.is_open_calls == ['Kung-Fu Chess']

    def test_game_over_frame_remains_visible_until_exit_key(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        game_over_snapshot = GameSnapshot(
            pieces=(),
            motions=(),
            rests=(),
            game_over=True,
            width=8,
            height=8,
        )
        engine.snapshot_value = game_over_snapshot
        controller = _make_controller(selected=None)
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = SequencePollKey([-1, ord("q")])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 2
        assert renderer.render_calls[-1] == (game_over_snapshot, None, self.presentation.snapshot_value)
        assert self.window.is_open_calls == ['Kung-Fu Chess']
        assert self.window.close_calls == 1

    def test_exits_when_window_is_closed_with_x(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2])
        poll_key = SequencePollKey([-1, -1])
        self.window.open_results = [True, False]

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 2
        assert engine.consume_events_calls == 2
        assert self.window.is_open_calls == ['Kung-Fu Chess', 'Kung-Fu Chess']
        assert self.window.close_calls == 1

    def test_ignores_unrelated_keys_and_keeps_looping(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = SequencePollKey([-1, ord("a"), 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(renderer.render_calls) == 3

    def test_cleanup_runs_even_if_render_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        renderer.render_error = RuntimeError("boom")
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey()

        with pytest.raises(RuntimeError):
            self.run_loop(
                engine,
                renderer,
                controller,
                clock=lambda: next(clock_values),
                poll_key=poll_key,
            )

        assert self.window.close_calls == 1

    def test_cleanup_runs_if_mouse_callback_setup_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        error = RuntimeError("callback setup failed")
        self.window.callback_error = error
        clock_calls = 0

        def clock():
            nonlocal clock_calls
            clock_calls += 1
            return 0.0

        poll_key = SequencePollKey()

        with pytest.raises(RuntimeError) as raised:
            self.run_loop(
                engine,
                renderer,
                controller,
                clock=clock,
                poll_key=poll_key,
            )

        assert raised.value is error
        assert self.window.close_calls == 1
        assert clock_calls == 0
        assert engine.wait_calls == []
        assert engine.snapshot_calls == 0
        assert renderer.render_calls == []
        assert poll_key.calls == []

    def test_cleanup_runs_if_initial_clock_raises(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        error = RuntimeError("initial clock failed")

        def clock():
            raise error

        poll_key = SequencePollKey()

        with pytest.raises(RuntimeError) as raised:
            self.run_loop(
                engine,
                renderer,
                controller,
                clock=clock,
                poll_key=poll_key,
            )

        assert raised.value is error
        assert self.window.close_calls == 1
        assert engine.wait_calls == []
        assert renderer.render_calls == []

    def test_does_not_open_a_real_window(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert renderer.frame.show_frame_calls == ['Kung-Fu Chess']

    def test_mouse_callback_installed_exactly_once(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1, 0.2, 0.3])
        poll_key = SequencePollKey([-1, ord("a"), 27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert len(self.window.callback_calls) == 1

    def test_installed_callback_delegates_exact_coordinates_to_controller_click(
        self,
    ) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        _window_name, on_left_click, _on_right_click = self.window.callback_calls[0]
        on_left_click(123, 456)

        assert controller.click_calls == [(123, 456)]

    def test_installed_callback_delegates_exact_coordinates_to_controller_jump(
        self,
    ) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller()
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        _window_name, _on_left_click, on_right_click = self.window.callback_calls[0]
        on_right_click(123, 456)

        assert controller.jump_calls == [(123, 456)]

    def test_rendering_receives_current_controller_selected(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        selected = Position(2, 3)
        controller = _make_controller(selected=selected)
        clock_values = iter([0.0, 0.1])
        poll_key = SequencePollKey([27])

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        assert renderer.render_calls == [(engine.snapshot_value, selected, self.presentation.snapshot_value)]

    def test_next_frame_reflects_selection_change_from_a_click(self) -> None:
        engine, renderer = _make_engine_and_renderer()
        controller = _make_controller(selected=None)
        clock_values = iter([0.0, 0.1, 0.2])

        def poll_key(delay_ms: int) -> int:
            if len(renderer.render_calls) == 1:
                controller.selected = Position(
                    0, 0
                )  # simulate a click landing this frame
                return -1
            return 27

        self.run_loop(
            engine,
            renderer,
            controller,
            clock=lambda: next(clock_values),
            poll_key=poll_key,
        )

        first_selected = renderer.render_calls[0][1]
        second_selected = renderer.render_calls[1][1]
        assert first_selected is None
        assert second_selected == Position(0, 0)


class TestMainComposition:
    def test_renderer_and_mapper_receive_the_same_board_geometry(self) -> None:
        layout = BoardLayout(cell_size=73, origin_x=11, origin_y=17)
        snapshot = GameSnapshot(
            pieces=(),
            motions=(),
            rests=(),
            game_over=False,
            width=8,
            height=8,
        )
        engine = FakeEngine(snapshot)
        renderer = _build_renderer(layout)
        captured_mappers = []

        def controller_factory(mapper, controller_engine):
            captured_mappers.append(mapper)
            return Controller(mapper, controller_engine)

        loop_calls = []

        def loop(loop_engine, loop_renderer, controller, loop_presentation):
            loop_calls.append(
                (loop_engine, loop_renderer, controller, loop_presentation)
            )

        run_game(
            engine,
            renderer,
            layout,
            FakePresentation(),
            controller_factory=controller_factory,
            loop=loop,
        )

        mapper = captured_mappers[0]
        sample_x = layout.origin_x + layout.cell_size // 2
        sample_y = layout.origin_y + 3
        assert mapper.pixel_to_cell(sample_x, sample_y) == Position(0, 0)

        presentation = GamePresentationSnapshot(0, 0, (), ())
        baseline = renderer.render(snapshot, None, presentation)
        selected = renderer.render(snapshot, Position(0, 0), presentation)
        assert not (baseline.pixels[sample_y, sample_x] == selected.pixels[sample_y, sample_x]).all()
        assert loop_calls[0][0] is engine
        assert loop_calls[0][1] is renderer
