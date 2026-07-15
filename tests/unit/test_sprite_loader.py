from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from kungfu_chess.ui import sprite_loader as sprite_loader_module
from kungfu_chess.ui.sprite_loader import SpriteLoader

REAL_PIECES_ROOT = Path(sprite_loader_module.__file__).resolve().parent / "assets" / "pieces2"

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


if __name__ == "__main__":
    unittest.main()
