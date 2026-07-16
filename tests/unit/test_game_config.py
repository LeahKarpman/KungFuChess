from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import kungfu_chess
from kungfu_chess.game_config import GameConfig, load_game_config

PRODUCTION_CONFIG_PATH = (
    Path(kungfu_chess.__file__).resolve().parent / "resources" / "game_config.json"
)


class TestGameConfigDefaults(unittest.TestCase):
    def test_default_values_are_2000_and_10000_ms(self) -> None:
        config = GameConfig()
        self.assertEqual(config.short_cooldown_ms, 2000)
        self.assertEqual(config.long_cooldown_ms, 10000)


class TestProductionGameConfigFile(unittest.TestCase):
    def test_production_config_file_has_default_values(self) -> None:
        config = load_game_config(PRODUCTION_CONFIG_PATH)
        self.assertEqual(config.short_cooldown_ms, 2000)
        self.assertEqual(config.long_cooldown_ms, 10000)


class TestLoadGameConfig(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.path = Path(self._tmp_dir.name) / "game_config.json"

    def _write(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")

    def test_valid_json_loads_correctly(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": 1500, "long_cooldown_ms": 9000}))

        config = load_game_config(self.path)

        self.assertEqual(config.short_cooldown_ms, 1500)
        self.assertEqual(config.long_cooldown_ms, 9000)

    def test_missing_field_raises_clear_error(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": 1500}))

        with self.assertRaisesRegex(ValueError, "long_cooldown_ms"):
            load_game_config(self.path)

    def test_malformed_json_raises_clear_error(self) -> None:
        self._write("{not valid json")

        with self.assertRaisesRegex(ValueError, "[Mm]alformed"):
            load_game_config(self.path)

    def test_zero_value_is_rejected(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": 0, "long_cooldown_ms": 10000}))

        with self.assertRaisesRegex(ValueError, "short_cooldown_ms"):
            load_game_config(self.path)

    def test_negative_value_is_rejected(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": 2000, "long_cooldown_ms": -10000}))

        with self.assertRaisesRegex(ValueError, "long_cooldown_ms"):
            load_game_config(self.path)

    def test_non_integer_value_is_rejected(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": 2000.5, "long_cooldown_ms": 10000}))

        with self.assertRaisesRegex(ValueError, "short_cooldown_ms"):
            load_game_config(self.path)

    def test_boolean_value_is_rejected(self) -> None:
        self._write(json.dumps({"short_cooldown_ms": True, "long_cooldown_ms": 10000}))

        with self.assertRaisesRegex(ValueError, "short_cooldown_ms"):
            load_game_config(self.path)

    def test_missing_file_raises_clear_error(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_game_config(self.path)


if __name__ == "__main__":
    unittest.main()
