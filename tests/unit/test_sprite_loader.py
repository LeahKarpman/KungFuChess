# pyright: reportOptionalMemberAccess=false

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from kungfu_chess.ui import sprite_loader as sprite_loader_module
from kungfu_chess.ui.animation import select_frame_index
from kungfu_chess.ui.img import Img
from kungfu_chess.ui.sprite_loader import SpriteLoader

REAL_PIECES_ROOT = Path(sprite_loader_module.__file__).resolve().parent / "assets" / "pieces2"
STUB_SPRITE_SOURCE = REAL_PIECES_ROOT / "PW" / "states" / "idle" / "sprites" / "1.png"

ALL_KIND_COLOR_DIRECTORIES = [
    ("K", "w", "KW"),
    ("K", "b", "KB"),
    ("Q", "w", "QW"),
    ("Q", "b", "QB"),
    ("R", "w", "RW"),
    ("R", "b", "RB"),
    ("B", "w", "BW"),
    ("B", "b", "BB"),
    ("N", "w", "NW"),
    ("N", "b", "NB"),
    ("P", "w", "PW"),
    ("P", "b", "PB"),
]


class RecordingImageFactory:
    def __init__(self) -> None:
        self.created_images: list[Img] = []

    def __call__(self) -> Img:
        image = Img()
        self.created_images.append(image)
        return image


class RecordingFrameSelector:
    def __init__(self) -> None:
        self.calls: list[tuple[int, float, int, bool]] = []

    def __call__(
        self, elapsed_ms: int, frames_per_sec: float, frame_count: int, is_loop: bool
    ) -> int:
        self.calls.append((elapsed_ms, frames_per_sec, frame_count, is_loop))
        return select_frame_index(elapsed_ms, frames_per_sec, frame_count, is_loop)


class TestSpriteLoader:
    @pytest.mark.parametrize(
        ("kind", "color", "directory"),
        ALL_KIND_COLOR_DIRECTORIES,
    )
    def test_all_valid_kind_color_combinations_load(
        self, kind: str, color: str, directory: str
    ) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        sprite = loader.load_idle_sprite(kind, color)
        assert sprite.img is not None
        height, width, channels = sprite.img.shape
        assert (width, height) == (64, 64)
        assert channels == 4  # RGBA: transparency must be preserved

    def test_caching_returns_same_instance(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        first = loader.load_idle_sprite("Q", "w")
        second = loader.load_idle_sprite("Q", "w")
        assert first is second

    def test_invalid_kind_raises(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        with pytest.raises(ValueError, match='Invalid piece kind'):
            loader.load_idle_sprite("Z", "w")

    def test_invalid_color_raises(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        with pytest.raises(ValueError, match='Invalid piece color'):
            loader.load_idle_sprite("Q", "x")

    def test_missing_sprite_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = SpriteLoader(Path(tmp_dir))
            with pytest.raises(FileNotFoundError):
                loader.load_idle_sprite("Q", "w")

    def test_paths_independent_of_current_working_directory(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        previous_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                sprite = loader.load_idle_sprite("K", "b")
                assert sprite.img is not None
            finally:
                os.chdir(previous_cwd)


class TestSpriteLoaderSortedFramePaths:
    def test_sorted_frame_paths_orders_numerically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sprites_dir = Path(tmp_dir)
            for name in ("1.png", "2.png", "10.png"):
                (sprites_dir / name).write_bytes(b"")

            paths = SpriteLoader._sorted_frame_paths(sprites_dir)

            assert [path.name for path in paths] == ['1.png', '2.png', '10.png']


class TestSpriteLoaderAnimation:
    def setup_method(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp_dir.name)

    def teardown_method(self) -> None:
        self._tmp_dir.cleanup()

    def _write_state(
        self,
        kind_color: str,
        state: str,
        frame_numbers: list[int],
        frames_per_sec: object = 12,
        is_loop: object = True,
    ) -> None:
        state_dir = self.root / kind_color / "states" / state
        sprites_dir = state_dir / "sprites"
        sprites_dir.mkdir(parents=True)
        for number in frame_numbers:
            shutil.copy(STUB_SPRITE_SOURCE, sprites_dir / f"{number}.png")
        config = {"graphics": {"frames_per_sec": frames_per_sec, "is_loop": is_loop}}
        (state_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")

    def test_first_frame_at_zero_elapsed(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        frame = loader.get_animation_frame("P", "w", "move", 0)

        assert frame.img is not None

    def test_config_json_not_reparsed_for_every_frame(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        loader.get_animation_frame("P", "w", "move", 0)
        config_path = self.root / "PW" / "states" / "move" / "config.json"
        config_path.write_text("{now malformed", encoding="utf-8")
        loader.get_animation_frame("P", "w", "move", 100)
        loader.get_animation_frame("P", "w", "move", 200)

        assert loader.get_animation_frame('P', 'w', 'move', 0).pixels.shape[:2] == (64, 64)

    def test_already_loaded_frame_is_reused(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        first = loader.get_animation_frame("P", "w", "move", 0)
        second = loader.get_animation_frame("P", "w", "move", 0)

        assert first is second

    def test_png_not_reloaded_for_a_cached_frame(self) -> None:
        self._write_state("PW", "move", [1, 2, 3], frames_per_sec=1, is_loop=False)
        image_factory = RecordingImageFactory()
        loader = SpriteLoader(self.root, image_factory=image_factory)

        loader.get_animation_frame("P", "w", "move", 0)
        loader.get_animation_frame("P", "w", "move", 0)
        loader.get_animation_frame("P", "w", "move", 0)

        assert len(image_factory.created_images) == 1

    def test_move_and_jump_use_separate_cache_entries(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        self._write_state("PW", "jump", [1, 2, 3])
        loader = SpriteLoader(self.root)

        move_frame = loader.get_animation_frame("P", "w", "move", 0)
        jump_frame = loader.get_animation_frame("P", "w", "jump", 0)

        assert move_frame is not jump_frame

    def test_different_kind_and_color_use_separate_cache_entries(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        self._write_state("PB", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        white_frame = loader.get_animation_frame("P", "w", "move", 0)
        black_frame = loader.get_animation_frame("P", "b", "move", 0)

        assert white_frame is not black_frame

    def test_malformed_json_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        (state_dir / "sprites").mkdir(parents=True)
        (state_dir / "config.json").write_text("{not valid json", encoding="utf-8")
        loader = SpriteLoader(self.root)

        with pytest.raises(ValueError, match='[Mm]alformed'):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_missing_graphics_metadata_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        (state_dir / "sprites").mkdir(parents=True)
        (state_dir / "config.json").write_text(
            json.dumps({"physics": {}}), encoding="utf-8"
        )
        loader = SpriteLoader(self.root)

        with pytest.raises(ValueError, match='graphics'):
            loader.get_animation_frame("P", "w", "move", 0)

    @pytest.mark.parametrize(("index", "value"), tuple(enumerate((True, False))))
    def test_boolean_frames_per_sec_values_are_rejected(
        self, index: int, value: bool
    ) -> None:
        loader = SpriteLoader(self.root)

        state = f"boolean_fps_{index}"
        self._write_state("PW", state, [1], frames_per_sec=value)

        with pytest.raises(ValueError, match="'frames_per_sec' must be a positive number"):
            loader.get_animation_frame("P", "w", state, 0)

    @pytest.mark.parametrize(
        ("index", "value"), tuple(enumerate((None, "12", "fast", [], {})))
    )
    def test_non_numeric_frames_per_sec_values_are_rejected(
        self, index: int, value: object
    ) -> None:
        loader = SpriteLoader(self.root)

        state = f"non_numeric_fps_{index}"
        self._write_state("PW", state, [1], frames_per_sec=value)

        with pytest.raises(ValueError, match="'frames_per_sec' must be a positive number"):
            loader.get_animation_frame("P", "w", state, 0)

    @pytest.mark.parametrize(
        ("index", "value"),
        tuple(enumerate((float("nan"), float("inf"), float("-inf")))),
    )
    def test_non_finite_frames_per_sec_values_are_rejected(
        self, index: int, value: float
    ) -> None:
        loader = SpriteLoader(self.root)

        state = f"non_finite_fps_{index}"
        self._write_state("PW", state, [1], frames_per_sec=value)

        with pytest.raises(ValueError, match="'frames_per_sec' must be a positive number"):
            loader.get_animation_frame("P", "w", state, 0)

    def test_zero_frames_per_sec_is_rejected(self) -> None:
        self._write_state("PW", "move", [1], frames_per_sec=0)
        loader = SpriteLoader(self.root)

        with pytest.raises(ValueError, match="'frames_per_sec' must be a positive number"):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_negative_frames_per_sec_is_rejected(self) -> None:
        self._write_state("PW", "move", [1], frames_per_sec=-1)
        loader = SpriteLoader(self.root)

        with pytest.raises(ValueError, match="'frames_per_sec' must be a positive number"):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_positive_integer_frames_per_sec_remains_supported(self) -> None:
        self._write_state("PW", "move", [1], frames_per_sec=12)
        frame_selector = RecordingFrameSelector()
        loader = SpriteLoader(self.root, frame_selector=frame_selector)

        loader.get_animation_frame("P", "w", "move", 0)

        frames_per_sec = frame_selector.calls[0][1]
        assert type(frames_per_sec) is int
        assert frames_per_sec == 12

    def test_positive_float_frames_per_sec_remains_supported(self) -> None:
        self._write_state("PW", "move", [1], frames_per_sec=12.5)
        frame_selector = RecordingFrameSelector()
        loader = SpriteLoader(self.root, frame_selector=frame_selector)

        loader.get_animation_frame("P", "w", "move", 0)

        frames_per_sec = frame_selector.calls[0][1]
        assert type(frames_per_sec) is float
        assert frames_per_sec == 12.5

    @pytest.mark.parametrize(
        ("index", "value"),
        tuple(enumerate(("false", "true", 0, 1, None, [], {}))),
    )
    def test_non_boolean_is_loop_values_are_rejected(
        self, index: int, value: object
    ) -> None:
        loader = SpriteLoader(self.root)

        state = f"non_boolean_is_loop_{index}"
        self._write_state("PW", state, [1], is_loop=value)

        with pytest.raises(TypeError, match="'is_loop' must be a boolean"):
            loader.get_animation_frame("P", "w", state, 0)

    def test_true_is_loop_is_preserved_exactly(self) -> None:
        self._write_state("PW", "move", [1], is_loop=True)
        frame_selector = RecordingFrameSelector()
        loader = SpriteLoader(self.root, frame_selector=frame_selector)

        loader.get_animation_frame("P", "w", "move", 0)

        assert frame_selector.calls[0][3] is True

    def test_false_is_loop_is_preserved_exactly(self) -> None:
        self._write_state("PW", "move", [1], is_loop=False)
        frame_selector = RecordingFrameSelector()
        loader = SpriteLoader(self.root, frame_selector=frame_selector)

        loader.get_animation_frame("P", "w", "move", 0)

        assert frame_selector.calls[0][3] is False

    def test_missing_sprite_frames_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        state_dir.mkdir(parents=True)
        config = {"graphics": {"frames_per_sec": 12, "is_loop": True}}
        (state_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
        loader = SpriteLoader(self.root)

        with pytest.raises(FileNotFoundError):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_short_rest_state_loops_past_its_final_frame(self) -> None:
        self._write_state("PW", "short_rest", [1, 2], frames_per_sec=1, is_loop=True)
        loader = SpriteLoader(self.root)

        # 2 frames at 1fps: elapsed_ms=0 -> frame 0; elapsed_ms=2000 wraps back to frame 0.
        first = loader.get_animation_frame("P", "w", "short_rest", 0)
        wrapped = loader.get_animation_frame("P", "w", "short_rest", 2000)

        assert first is wrapped

    def test_long_rest_state_holds_its_final_frame_when_non_looping(self) -> None:
        self._write_state("PW", "long_rest", [1, 2], frames_per_sec=1, is_loop=False)
        loader = SpriteLoader(self.root)

        # 2 frames at 1fps: both elapsed_ms=1000 (last frame) and a far later
        # elapsed_ms clamp to the same final frame instead of raising or wrapping.
        last_frame = loader.get_animation_frame("P", "w", "long_rest", 1000)
        held_frame = loader.get_animation_frame("P", "w", "long_rest", 50000)

        assert last_frame is held_frame
