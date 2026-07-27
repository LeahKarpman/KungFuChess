from __future__ import annotations

from dataclasses import dataclass

from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.events import MoveCompleted
from kungfu_chess.model.game_state import GameSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui.game_window import run_game, run_loop
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.presentation import (
    GamePresentationSnapshot,
    MoveLogEntry,
)
from kungfu_chess.ui.renderer import HUD_HEIGHT, GameRenderer


class FakeFrame:
    def __init__(self) -> None:
        self.show_calls: list[str] = []

    def show_frame(self, window_name: str) -> None:
        self.show_calls.append(window_name)


class OrderedEngine:
    def __init__(self, order: list[str], event: MoveCompleted) -> None:
        self.order = order
        self.event = event
        self.snapshot_value = object()

    def wait(self, elapsed_ms: int) -> None:
        self.order.append("wait")

    def consume_events(self):
        self.order.append("consume")
        return (self.event,)

    def snapshot(self):
        self.order.append("engine_snapshot")
        return self.snapshot_value


class OrderedPresentation:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.received: tuple[object, ...] = ()
        self.snapshot_value = object()

    def apply(self, events) -> None:
        self.order.append("apply")
        self.received = tuple(events)

    def snapshot(self):
        self.order.append("presentation_snapshot")
        return self.snapshot_value


class OrderedRenderer:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.frame = FakeFrame()
        self.arguments = None

    def render(self, snapshot, selected, presentation):
        self.order.append("render")
        self.arguments = (snapshot, selected, presentation)
        return self.frame


class FakeController:
    selected = Position(2, 3)

    def click(self, x: int, y: int) -> None:
        pass

    def jump(self, x: int, y: int) -> None:
        pass


class FakeWindow:
    def set_mouse_callbacks(self, window_name, on_left_click, on_right_click) -> None:
        pass

    def is_window_open(self, window_name: str) -> bool:
        return True

    def close_all_windows(self) -> None:
        pass


def test_window_forwards_consumed_events_before_rendering_updated_hud() -> None:
    order: list[str] = []
    event = MoveCompleted(
        piece_id="white_rook",
        piece_kind="R",
        piece_color="w",
        source=Position(7, 4),
        destination=Position(4, 4),
    )
    engine = OrderedEngine(order, event)
    presentation = OrderedPresentation(order)
    renderer = OrderedRenderer(order)
    clock_values = iter((0.0, 0.1))

    run_loop(
        engine,
        renderer,
        FakeController(),
        presentation,
        clock=lambda: next(clock_values),
        poll_key=lambda delay_ms: 27,
        window=FakeWindow(),
    )

    assert order == [
        "wait",
        "consume",
        "apply",
        "engine_snapshot",
        "presentation_snapshot",
        "render",
    ]
    assert presentation.received == (event,)
    assert renderer.arguments == (
        engine.snapshot_value,
        Position(2, 3),
        presentation.snapshot_value,
    )


@dataclass
class FakePixels:
    shape: tuple[int, int, int]


class RecordingImage:
    def __init__(self, width: int = 0, height: int = 0) -> None:
        self.pixels = FakePixels((height, width, 4))
        self.create_call = None
        self.draw_call = None
        self.text_calls: list[tuple[str, int, int]] = []

    def create(self, width: int, height: int, color):
        self.pixels = FakePixels((height, width, len(color)))
        self.create_call = (width, height, color)
        return self

    def draw_on(self, other, x: int, y: int) -> None:
        self.draw_call = (other, x, y)

    def put_text(
        self,
        text: str,
        x: int,
        y: int,
        font_size: float,
        color,
        thickness: int,
    ) -> None:
        self.text_calls.append((text, x, y))


class FakeBoardRenderer:
    def __init__(self, board_frame: RecordingImage) -> None:
        self.board_frame = board_frame
        self.calls = []

    def render(self, snapshot, selected):
        self.calls.append((snapshot, selected))
        return self.board_frame


def test_final_frame_contains_unchanged_board_and_visible_scores_and_logs() -> None:
    board_frame = RecordingImage(width=800, height=800)
    board_renderer = FakeBoardRenderer(board_frame)
    created_images: list[RecordingImage] = []

    def image_factory() -> RecordingImage:
        image = RecordingImage()
        created_images.append(image)
        return image

    renderer = GameRenderer(board_renderer, image_factory=image_factory)
    snapshot = object()
    presentation = GamePresentationSnapshot(
        white_score=5,
        black_score=3,
        white_actions=(MoveLogEntry("wR", "w", "R a1xa8"),),
        black_actions=(MoveLogEntry("bN", "b", "N e4 (jump)"),),
    )

    frame = renderer.render(snapshot, Position(0, 0), presentation)

    assert frame is created_images[0]
    assert frame.pixels.shape == (800 + HUD_HEIGHT, 800, 4)
    assert board_frame.draw_call == (frame, 0, 0)
    rendered_text = {call[0] for call in frame.text_calls}
    assert "White score: 5" in rendered_text
    assert "Black score: 3" in rendered_text
    assert "R a1xa8" in rendered_text
    assert "N e4 (jump)" in rendered_text


class GeometryEngine:
    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            pieces=(),
            motions=(),
            rests=(),
            game_over=False,
            width=8,
            height=8,
        )


def test_board_input_geometry_remains_at_configured_origin_and_size() -> None:
    layout = BoardLayout(cell_size=100, origin_x=0, origin_y=0)
    captured_mapper: list[BoardMapper] = []

    def controller_factory(mapper, engine):
        captured_mapper.append(mapper)
        return FakeController()

    def loop(engine, renderer, controller, presentation) -> None:
        pass

    run_game(
        GeometryEngine(),
        object(),
        layout,
        object(),
        controller_factory=controller_factory,
        loop=loop,
    )

    mapper = captured_mapper[0]
    assert mapper.pixel_to_cell(0, 0) == Position(0, 0)
    assert mapper.pixel_to_cell(799, 799) == Position(7, 7)
    assert mapper.pixel_to_cell(800, 799) is None
    assert mapper.pixel_to_cell(20, 820) is None
