from __future__ import annotations

import json
from pathlib import Path

import kungfu_chess
import pytest
from kungfu_chess.game_config import GameConfig, load_game_config
from kungfu_chess.realtime.rest import (
    DEFAULT_LONG_COOLDOWN_MS,
    DEFAULT_SHORT_COOLDOWN_MS,
)

PRODUCTION_CONFIG_PATH = (
    Path(kungfu_chess.__file__).resolve().parent / "resources" / "game_config.json"
)
PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "game_config.json"


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class TestGameConfigDefaults:
    def test_default_values_are_2000_and_10000_ms(self) -> None:
        config = GameConfig(piece_values=PIECE_VALUES)
        assert config.short_cooldown_ms == DEFAULT_SHORT_COOLDOWN_MS
        assert config.long_cooldown_ms == DEFAULT_LONG_COOLDOWN_MS
        assert dict(config.piece_values) == PIECE_VALUES
        assert DEFAULT_SHORT_COOLDOWN_MS == 2000
        assert DEFAULT_LONG_COOLDOWN_MS == 10000


class TestProductionGameConfigFile:
    def test_production_config_file_has_default_values(self) -> None:
        config = load_game_config(PRODUCTION_CONFIG_PATH)
        assert config.short_cooldown_ms == 2000
        assert config.long_cooldown_ms == 10000
        assert dict(config.piece_values) == PIECE_VALUES


class TestLoadGameConfig:
    def test_valid_json_loads_correctly(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps(
                {
                    "short_cooldown_ms": 1500,
                    "long_cooldown_ms": 9000,
                    "piece_values": PIECE_VALUES,
                }
            ),
        )

        config = load_game_config(config_path)

        assert config.short_cooldown_ms == 1500
        assert config.long_cooldown_ms == 9000

    def test_missing_field_raises_clear_error(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps({"short_cooldown_ms": 1500, "piece_values": PIECE_VALUES}),
        )

        with pytest.raises(ValueError, match="long_cooldown_ms"):
            load_game_config(config_path)

    def test_malformed_json_raises_clear_error(self, config_path: Path) -> None:
        _write(config_path, "{not valid json")

        with pytest.raises(ValueError, match="[Mm]alformed"):
            load_game_config(config_path)

    def test_zero_value_is_rejected(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps(
                {
                    "short_cooldown_ms": 0,
                    "long_cooldown_ms": 10000,
                    "piece_values": PIECE_VALUES,
                }
            ),
        )

        with pytest.raises(ValueError, match="short_cooldown_ms"):
            load_game_config(config_path)

    def test_negative_value_is_rejected(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps(
                {
                    "short_cooldown_ms": 2000,
                    "long_cooldown_ms": -10000,
                    "piece_values": PIECE_VALUES,
                }
            ),
        )

        with pytest.raises(ValueError, match="long_cooldown_ms"):
            load_game_config(config_path)

    def test_non_integer_value_is_rejected(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps(
                {
                    "short_cooldown_ms": 2000.5,
                    "long_cooldown_ms": 10000,
                    "piece_values": PIECE_VALUES,
                }
            ),
        )

        with pytest.raises(TypeError, match="short_cooldown_ms"):
            load_game_config(config_path)

    def test_boolean_value_is_rejected(self, config_path: Path) -> None:
        _write(
            config_path,
            json.dumps(
                {
                    "short_cooldown_ms": True,
                    "long_cooldown_ms": 10000,
                    "piece_values": PIECE_VALUES,
                }
            ),
        )

        with pytest.raises(TypeError, match="short_cooldown_ms"):
            load_game_config(config_path)

    def test_missing_file_raises_clear_error(self, config_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_game_config(config_path)
