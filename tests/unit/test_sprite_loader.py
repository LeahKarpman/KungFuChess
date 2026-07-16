from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kungfu_chess.ui import sprite_loader as sprite_loader_module
from kungfu_chess.ui.img import cv2 as img_cv2
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


class TestSpriteLoader(unittest.TestCase):
    def test_all_valid_kind_color_combinations_load(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        for kind, color, directory in ALL_KIND_COLOR_DIRECTORIES:
            with self.subTest(kind=kind, color=color, directory=directory):
                sprite = loader.load_idle_sprite(kind, color)
                self.assertIsNotNone(sprite.img)
                height, width, channels = sprite.img.shape
                self.assertEqual((width, height), (64, 64))
                self.assertEqual(channels, 4)  # RGBA: transparency must be preserved

    def test_caching_returns_same_instance(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        first = loader.load_idle_sprite("Q", "w")
        second = loader.load_idle_sprite("Q", "w")
        self.assertIs(first, second)

    def test_invalid_kind_raises(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        with self.assertRaisesRegex(ValueError, "Invalid piece kind"):
            loader.load_idle_sprite("Z", "w")

    def test_invalid_color_raises(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        with self.assertRaisesRegex(ValueError, "Invalid piece color"):
            loader.load_idle_sprite("Q", "x")

    def test_missing_sprite_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = SpriteLoader(Path(tmp_dir))
            with self.assertRaises(FileNotFoundError):
                loader.load_idle_sprite("Q", "w")

    def test_paths_independent_of_current_working_directory(self) -> None:
        loader = SpriteLoader(REAL_PIECES_ROOT)
        previous_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                sprite = loader.load_idle_sprite("K", "b")
                self.assertIsNotNone(sprite.img)
            finally:
                os.chdir(previous_cwd)


class TestSpriteLoaderSortedFramePaths(unittest.TestCase):
    def test_sorted_frame_paths_orders_numerically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sprites_dir = Path(tmp_dir)
            for name in ("1.png", "2.png", "10.png"):
                (sprites_dir / name).write_bytes(b"")

            paths = SpriteLoader._sorted_frame_paths(sprites_dir)

            self.assertEqual([path.name for path in paths], ["1.png", "2.png", "10.png"])


class TestSpriteLoaderAnimation(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.root = Path(self._tmp_dir.name)

    def _write_state(
        self,
        kind_color: str,
        state: str,
        frame_numbers: list[int],
        frames_per_sec: float = 12,
        is_loop: bool = True,
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

        self.assertIsNotNone(frame.img)

    def test_config_json_not_reparsed_for_every_frame(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        with patch(
            "kungfu_chess.ui.sprite_loader.json.loads", wraps=json.loads
        ) as mocked_loads:
            loader.get_animation_frame("P", "w", "move", 0)
            loader.get_animation_frame("P", "w", "move", 100)
            loader.get_animation_frame("P", "w", "move", 200)

        self.assertEqual(mocked_loads.call_count, 1)

    def test_already_loaded_frame_is_reused(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        first = loader.get_animation_frame("P", "w", "move", 0)
        second = loader.get_animation_frame("P", "w", "move", 0)

        self.assertIs(first, second)

    def test_png_not_reloaded_for_a_cached_frame(self) -> None:
        self._write_state("PW", "move", [1, 2, 3], frames_per_sec=1, is_loop=False)
        loader = SpriteLoader(self.root)

        with patch.object(img_cv2, "imread", wraps=img_cv2.imread) as mocked_imread:
            loader.get_animation_frame("P", "w", "move", 0)
            loader.get_animation_frame("P", "w", "move", 0)
            loader.get_animation_frame("P", "w", "move", 0)

        frame_reads = [
            call for call in mocked_imread.call_args_list if "1.png" in call.args[0]
        ]
        self.assertEqual(len(frame_reads), 1)

    def test_move_and_jump_use_separate_cache_entries(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        self._write_state("PW", "jump", [1, 2, 3])
        loader = SpriteLoader(self.root)

        move_frame = loader.get_animation_frame("P", "w", "move", 0)
        jump_frame = loader.get_animation_frame("P", "w", "jump", 0)

        self.assertIsNot(move_frame, jump_frame)

    def test_different_kind_and_color_use_separate_cache_entries(self) -> None:
        self._write_state("PW", "move", [1, 2, 3])
        self._write_state("PB", "move", [1, 2, 3])
        loader = SpriteLoader(self.root)

        white_frame = loader.get_animation_frame("P", "w", "move", 0)
        black_frame = loader.get_animation_frame("P", "b", "move", 0)

        self.assertIsNot(white_frame, black_frame)

    def test_malformed_json_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        (state_dir / "sprites").mkdir(parents=True)
        (state_dir / "config.json").write_text("{not valid json", encoding="utf-8")
        loader = SpriteLoader(self.root)

        with self.assertRaisesRegex(ValueError, "[Mm]alformed"):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_missing_graphics_metadata_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        (state_dir / "sprites").mkdir(parents=True)
        (state_dir / "config.json").write_text(
            json.dumps({"physics": {}}), encoding="utf-8"
        )
        loader = SpriteLoader(self.root)

        with self.assertRaisesRegex(ValueError, "graphics"):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_non_positive_frames_per_sec_raises_clear_error(self) -> None:
        self._write_state("PW", "move", [1], frames_per_sec=0)
        loader = SpriteLoader(self.root)

        with self.assertRaisesRegex(ValueError, "frames_per_sec"):
            loader.get_animation_frame("P", "w", "move", 0)

    def test_missing_sprite_frames_raises_clear_error(self) -> None:
        state_dir = self.root / "PW" / "states" / "move"
        state_dir.mkdir(parents=True)
        config = {"graphics": {"frames_per_sec": 12, "is_loop": True}}
        (state_dir / "config.json").write_text(json.dumps(config), encoding="utf-8")
        loader = SpriteLoader(self.root)

        with self.assertRaises(FileNotFoundError):
            loader.get_animation_frame("P", "w", "move", 0)


if __name__ == "__main__":
    unittest.main()
