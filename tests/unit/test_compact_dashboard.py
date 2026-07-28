from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.game_state import GameSnapshot, MotionSnapshot, PieceSnapshot
from kungfu_chess.model.position import Position
from kungfu_chess.ui import game_window
from kungfu_chess.ui.game_window import GAME_BOARD_LAYOUT, SPRITE_SIZE, _build_renderer
from kungfu_chess.ui.img import Img
from kungfu_chess.ui.presentation import GamePresentationSnapshot
from kungfu_chess.ui.renderer import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    HUD_BACKGROUND_COLOR,
    LEFT_PANEL_X,
    PANEL_WIDTH,
    RIGHT_PANEL_X,
    BoardRenderer,
)

ASSETS_ROOT = Path(game_window.__file__).resolve().parent / "assets"
BOARD_IMAGE_PATH = ASSETS_ROOT / "board.png"


def _snapshot(
    pieces: tuple[PieceSnapshot, ...] = (),
    motions: tuple[MotionSnapshot, ...] = (),
) -> GameSnapshot:
    return GameSnapshot(
        pieces=pieces,
        motions=motions,
        rests=(),
        game_over=False,
        width=8,
        height=8,
    )


class RecordingSprite(Img):
    def __init__(self, size: int = SPRITE_SIZE) -> None:
        super().__init__()
        self.img = np.zeros((size, size, 4), dtype=np.uint8)
        self.draw_calls: list[tuple[Img, int, int]] = []

    def draw_on(self, other_img: Img, x: int, y: int) -> None:
        self.draw_calls.append((other_img, x, y))


class RecordingSpriteLoader:
    def __init__(self, sprite: RecordingSprite) -> None:
        self.sprite = sprite
        self.animation_calls: list[tuple[str, str, str, int]] = []

    def load_idle_sprite(self, kind: str, color: str) -> Img:
        return self.sprite

    def get_animation_frame(
        self,
        kind: str,
        color: str,
        state: str,
        elapsed_ms: int,
    ) -> Img:
        self.animation_calls.append((kind, color, state, elapsed_ms))
        return self.sprite


class RecordingCanvas(Img):
    def __init__(self) -> None:
        super().__init__()
        self.create(FRAME_WIDTH, FRAME_HEIGHT, HUD_BACKGROUND_COLOR)
        self.rectangle_calls: list[tuple[object, ...]] = []

    def draw_rectangle(
        self,
        top_left: tuple[int, int],
        bottom_right: tuple[int, int],
        color: tuple[int, ...],
        thickness: int,
    ) -> None:
        self.rectangle_calls.append((top_left, bottom_right, color, thickness))
        super().draw_rectangle(top_left, bottom_right, color, thickness)


def test_standard_renderer_and_mapper_share_the_exact_layout_instance() -> None:
    renderer = _build_renderer(GAME_BOARD_LAYOUT)
    mapper = BoardMapper(8, 8, GAME_BOARD_LAYOUT)

    assert renderer.layout is GAME_BOARD_LAYOUT
    assert mapper.layout is GAME_BOARD_LAYOUT


def test_board_is_drawn_at_layout_origin_inside_the_compact_frame() -> None:
    renderer = _build_renderer(GAME_BOARD_LAYOUT)
    frame = renderer.render(
        _snapshot(),
        None,
        GamePresentationSnapshot(0, 0, (), ()),
    )
    origin_x = GAME_BOARD_LAYOUT.origin_x
    origin_y = GAME_BOARD_LAYOUT.origin_y

    assert frame.pixels.shape == (FRAME_HEIGHT, FRAME_WIDTH, 4)
    assert tuple(frame.pixels[origin_y - 1, origin_x]) == HUD_BACKGROUND_COLOR
    assert tuple(frame.pixels[origin_y, origin_x]) != HUD_BACKGROUND_COLOR


def test_selection_border_uses_scaled_cell_geometry() -> None:
    sprite = RecordingSprite()
    renderer = BoardRenderer(
        BOARD_IMAGE_PATH,
        RecordingSpriteLoader(sprite),
        GAME_BOARD_LAYOUT,
    )
    canvas = RecordingCanvas()

    renderer.render_on(canvas, _snapshot(), selected=Position(7, 7))

    cell_left, cell_top = GAME_BOARD_LAYOUT.cell_top_left(Position(7, 7))
    assert canvas.rectangle_calls[-1][0] == (cell_left + 3, cell_top + 3)
    assert canvas.rectangle_calls[-1][1] == (
        cell_left + GAME_BOARD_LAYOUT.cell_size - 3,
        cell_top + GAME_BOARD_LAYOUT.cell_size - 3,
    )


def test_scaled_piece_sprite_is_centered_in_its_cell() -> None:
    sprite = RecordingSprite()
    renderer = BoardRenderer(
        BOARD_IMAGE_PATH,
        RecordingSpriteLoader(sprite),
        GAME_BOARD_LAYOUT,
    )
    canvas = RecordingCanvas()
    piece = PieceSnapshot("white_king", "w", "K", Position(3, 4), "idle")

    renderer.render_on(canvas, _snapshot((piece,)))

    assert sprite.pixels.shape == (SPRITE_SIZE, SPRITE_SIZE, 4)
    assert sprite.draw_calls[0][1:] == GAME_BOARD_LAYOUT.centered_top_left(
        piece.cell,
        SPRITE_SIZE,
        SPRITE_SIZE,
    )


@pytest.mark.parametrize("action_kind", ["move", "jump"])
def test_motion_coordinates_use_scaled_layout(action_kind: str) -> None:
    sprite = RecordingSprite()
    loader = RecordingSpriteLoader(sprite)
    renderer = BoardRenderer(BOARD_IMAGE_PATH, loader, GAME_BOARD_LAYOUT)
    canvas = RecordingCanvas()
    piece = PieceSnapshot("white_rook", "w", "R", Position(0, 0), "moving")
    motion = MotionSnapshot(
        piece_id=piece.id,
        source=Position(0, 0),
        destination=Position(0, 2),
        elapsed_ms=500,
        duration_ms=1000,
        action_kind=action_kind,
    )

    renderer.render_on(canvas, _snapshot((piece,), (motion,)))

    source = GAME_BOARD_LAYOUT.cell_center(motion.source)
    destination = GAME_BOARD_LAYOUT.cell_center(motion.destination)
    midpoint = (
        (source[0] + destination[0]) / 2,
        (source[1] + destination[1]) / 2,
    )
    assert sprite.draw_calls[0][1:] == (
        GAME_BOARD_LAYOUT.centered_top_left_at_point(
            midpoint,
            SPRITE_SIZE,
            SPRITE_SIZE,
        )
    )
    assert loader.animation_calls == [("R", "w", action_kind, 500)]


def test_mapper_accepts_corner_cells_and_rejects_both_panels() -> None:
    mapper = BoardMapper(8, 8, GAME_BOARD_LAYOUT)
    board_width, board_height = GAME_BOARD_LAYOUT.board_pixel_size(8, 8)

    assert mapper.pixel_to_cell(
        GAME_BOARD_LAYOUT.origin_x,
        GAME_BOARD_LAYOUT.origin_y,
    ) == Position(0, 0)
    assert mapper.pixel_to_cell(
        GAME_BOARD_LAYOUT.origin_x + board_width - 1,
        GAME_BOARD_LAYOUT.origin_y + board_height - 1,
    ) == Position(7, 7)
    assert mapper.pixel_to_cell(
        LEFT_PANEL_X + PANEL_WIDTH // 2,
        GAME_BOARD_LAYOUT.origin_y + board_height // 2,
    ) is None
    assert mapper.pixel_to_cell(
        RIGHT_PANEL_X + PANEL_WIDTH // 2,
        GAME_BOARD_LAYOUT.origin_y + board_height // 2,
    ) is None


def test_resize_preserves_sprite_transparency_channel() -> None:
    sprite = Img()
    sprite.img = np.zeros((2, 2, 4), dtype=np.uint8)
    sprite.img[0, 0] = (10, 20, 30, 0)
    sprite.img[1, 1] = (40, 50, 60, 255)

    result = sprite.resize(SPRITE_SIZE, SPRITE_SIZE)

    assert result is sprite
    assert sprite.pixels.shape == (SPRITE_SIZE, SPRITE_SIZE, 4)
    assert sprite.pixels[:, :, 3].min() == 0
    assert sprite.pixels[:, :, 3].max() == 255
