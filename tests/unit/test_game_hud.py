from __future__ import annotations

from dataclasses import dataclass

from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.events import MoveCompleted
from kungfu_chess.model.game_state import GameSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui.game_window import GAME_BOARD_LAYOUT, run_game, run_loop
from kungfu_chess.ui.layout import BoardLayout
from kungfu_chess.ui.presentation import (
    GamePresentationSnapshot,
    MoveLogEntry,
)
from kungfu_chess.ui.renderer import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LEFT_PANEL_X,
    PANEL_WIDTH,
    RIGHT_PANEL_X,
    GameRenderer,
)


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
        self.draw_calls: list[tuple[object, int, int]] = []
        self.rectangle_calls: list[tuple[object, ...]] = []
        self.text_calls: list[tuple[str, int, int]] = []

    def create(self, width: int, height: int, color):
        self.pixels = FakePixels((height, width, len(color)))
        self.create_call = (width, height, color)
        return self

    def draw_on(self, other, x: int, y: int) -> None:
        self.draw_calls.append((other, x, y))

    def draw_rectangle(self, top_left, bottom_right, color, thickness) -> None:
        self.rectangle_calls.append((top_left, bottom_right, color, thickness))

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
    def __init__(self, layout: BoardLayout) -> None:
        self.layout = layout
        self.calls = []

    def render_on(self, canvas, snapshot, selected):
        self.calls.append((canvas, snapshot, selected))


def test_final_frame_contains_centered_board_and_side_scores_and_logs() -> None:
    board_renderer = FakeBoardRenderer(GAME_BOARD_LAYOUT)
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
    assert frame.pixels.shape == (FRAME_HEIGHT, FRAME_WIDTH, 4)
    assert board_renderer.calls == [(frame, snapshot, Position(0, 0))]
    text_by_value = {call[0]: call for call in frame.text_calls}
    assert text_by_value["BLACK"][1] == LEFT_PANEL_X + 16
    assert text_by_value["Score: 3"][1] == LEFT_PANEL_X + 16
    assert text_by_value["N e4 (jump)"][1] == LEFT_PANEL_X + 16
    assert text_by_value["WHITE"][1] == RIGHT_PANEL_X + 16
    assert text_by_value["Score: 5"][1] == RIGHT_PANEL_X + 16
    assert text_by_value["R a1xa8"][1] == RIGHT_PANEL_X + 16


def test_dashboard_geometry_fits_and_panels_are_outside_board() -> None:
    board_width, board_height = GAME_BOARD_LAYOUT.board_pixel_size(8, 8)

    assert FRAME_WIDTH <= 1200
    assert FRAME_HEIGHT <= 760
    assert (board_width, board_height) == (576, 576)
    assert board_width < 800
    assert LEFT_PANEL_X + PANEL_WIDTH <= GAME_BOARD_LAYOUT.origin_x
    assert GAME_BOARD_LAYOUT.origin_x + board_width <= RIGHT_PANEL_X
    assert GAME_BOARD_LAYOUT.origin_y + board_height <= FRAME_HEIGHT


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
    layout = GAME_BOARD_LAYOUT
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
    assert mapper.layout is layout
    board_width, board_height = layout.board_pixel_size(8, 8)
    assert mapper.pixel_to_cell(layout.origin_x, layout.origin_y) == Position(0, 0)
    assert mapper.pixel_to_cell(
        layout.origin_x + board_width - 1,
        layout.origin_y + board_height - 1,
    ) == Position(7, 7)
    assert mapper.pixel_to_cell(layout.origin_x - 1, layout.origin_y) is None
    assert mapper.pixel_to_cell(
        layout.origin_x + board_width,
        layout.origin_y + board_height - 1,
    ) is None
    assert mapper.pixel_to_cell(LEFT_PANEL_X + 10, 100) is None
    assert mapper.pixel_to_cell(RIGHT_PANEL_X + 10, 100) is None
